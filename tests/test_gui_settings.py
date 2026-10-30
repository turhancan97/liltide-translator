"""Isolated settings and fake Keychain tests; never read the user's real Keychain."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import pytest
pytest.importorskip('PySide6')
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from liltide.audio import AudioError, Device, InputIdentity
from liltide.gui_settings import AzureSetupDialog, MacCredentials, Preferences
from liltide.gui_window import MainWindow


class Keychain:
    value = None
    def set_password(self, service, account, value):
        self.value = value
    def get_password(self, service, account):
        return self.value
    def delete_password(self, service, account):
        self.value = None


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.delenv('AZURE_SPEECH_KEY', raising=False)
    monkeypatch.delenv('AZURE_SPEECH_REGION', raising=False)
    backend = Keychain()
    return MacCredentials(lambda: backend), backend


def test_keychain_roundtrip_f0_and_forget(credentials):
    manager, backend = credentials
    manager.save('synthetic', 'westeurope')
    with pytest.raises(AudioError, match='F0'):
        manager.config(False)
    config = manager.config(True)
    assert config.key == 'synthetic' and config.region == 'westeurope'
    assert 'synthetic' not in repr(config)
    manager.forget()
    with pytest.raises(AudioError, match='Azure setup'):
        manager.config(True)


def test_partial_environment_never_mixes_with_keychain(credentials, monkeypatch):
    manager, backend = credentials
    manager.save('synthetic', 'westeurope')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'eastus')
    with pytest.raises(AudioError, match='AZURE_SPEECH_KEY'):
        manager.config(True)
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'environment-synthetic')
    assert manager.config(True).key == 'environment-synthetic'


@pytest.mark.parametrize('value', ['bad-json', '[]', '{"key": 42, "region": "eastus"}'])
def test_corrupt_keychain_fails_without_leaking_value(credentials, value):
    manager, backend = credentials
    backend.value = value
    with pytest.raises(AudioError, match='Cannot read Azure credentials'):
        manager.config(True)


def test_denied_keychain_no_fallback_or_exception_leak():
    def denied():
        raise RuntimeError('sensitive backend details')
    manager = MacCredentials(denied)
    for operation in (lambda: manager.save('synthetic', 'eastus'), manager.forget,
                      lambda: manager.config(True)):
        with pytest.raises(AudioError) as caught:
            operation()
        assert 'sensitive' not in str(caught.value)


def test_settings_allowlist_and_invalid_values(tmp_path):
    settings = QSettings(str(tmp_path/'prefs.ini'), QSettings.Format.IniFormat)
    prefs = Preferences(settings)
    prefs.save({'theme': 'dark', 'source': 'system', 'view': 'english', 'caption_size': 22,
                'key': 'do-not-save', 'confirm_f0': True, 'export_text': '/private/path'})
    assert Preferences(settings).load() == dict(theme='dark', source='system', view='english', caption_size=22)
    assert 'do-not-save' not in (tmp_path/'prefs.ini').read_text()
    assert set(settings.allKeys()) == set(Preferences.CHOICES)
    settings.setValue('caption_size', 'bad')
    settings.setValue('theme', 'arbitrary')
    assert 'caption_size' not in prefs.load() and 'theme' not in prefs.load()
    prefs.remember_input('system', 'private-synthetic-uid')
    assert prefs.remembered_input() == ('system', 'private-synthetic-uid')
    prefs.remember_input()
    assert prefs.remembered_input() is None


def test_dialog_masks_and_clears_key(credentials):
    app = QApplication.instance() or QApplication([])
    manager, backend = credentials
    dialog = AzureSetupDialog(manager)
    assert dialog.key.echoMode() == dialog.key.EchoMode.Password
    dialog.key.setText('synthetic')
    dialog.region.setText('westeurope')
    dialog.save()
    assert not dialog.key.text() and json.loads(backend.value)['key'] == 'synthetic'
    dialog.forget()
    assert backend.value is None
    dialog.key.setText('synthetic')
    dialog.reject()
    assert not dialog.key.text()
    dialog.close()
    app.processEvents()


@pytest.mark.parametrize('devices, expected', [
    ([Device('new', 'Selected', 2, 'routed input', 'chosen')], 0),
    ([Device('old', 'Reused', 2, 'routed input', 'other')], -1),
    ([Device('a', 'A', 2, 'routed input', 'chosen'), Device('b', 'B', 2, 'routed input', 'chosen')], -1),
])
def test_remembered_input_restores_only_unique_exact_uid(tmp_path, devices, expected):
    app = QApplication.instance() or QApplication([])
    prefs = Preferences(QSettings(str(tmp_path/'prefs.ini'), QSettings.Format.IniFormat))
    prefs.save({'source': 'system', 'theme': 'dark', 'caption_size': 22})
    prefs.remember_input('system', 'chosen')
    win = MainWindow(preferences=prefs)
    win.available_devices = devices
    win.populate_devices()
    assert win.device.currentIndex() == expected
    assert win.theme.currentData() == 'dark' and win.caption_size.currentData() == 22
    assert not win.confirm.isChecked()
    assert all(not controls[0].isChecked() for controls in win.export_controls.values())
    win.remember_input.setChecked(False)
    assert prefs.remembered_input() is None
    win.close()
    app.processEvents()


def test_saved_credentials_reach_start_only_after_f0_and_device_selection(credentials, tmp_path):
    app = QApplication.instance() or QApplication([])
    manager, backend = credentials
    manager.save('synthetic', 'westeurope')
    configs = []
    def stop_before_worker(*args, **kwargs):
        configs.append(args[2])
        raise AudioError('Synthetic stop before capture')
    win = MainWindow(credentials=manager, worker_factory=stop_before_worker)
    win.available_devices = [Device('one', 'Synthetic', 2, 'routed input', 'chosen')]
    win.populate_devices()
    win.device.setCurrentIndex(0)
    win.start_session()
    assert 'F0' in win.status.text() and not configs
    win.confirm.setChecked(True)
    win.start_session()
    assert len(configs) == 1 and configs[0].key == 'synthetic'
    assert win.worker is None
    manager.forget()
    win.start_session()
    assert len(configs) == 1 and 'Azure setup' in win.status.text()
    win.close()
    app.processEvents()
