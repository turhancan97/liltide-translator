"""macOS GUI setup. Secrets only use the explicitly selected system Keychain."""

import json
import os

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel,
                              QLineEdit, QPushButton, QVBoxLayout)

from liltide.audio import AudioError
from liltide.provider import CloudConfig


class MacCredentials:
    SERVICE = 'org.liltide.translator.azure'
    ACCOUNT = 'speech'

    def __init__(self, backend_factory=None):
        self.backend_factory = backend_factory or self._system_backend

    @staticmethod
    def _system_backend():
        # Do not use backend discovery: third-party plaintext fallbacks are forbidden.
        from keyring.backends.macOS import Keyring
        return Keyring()

    def save(self, key, region):
        if not key.strip() or not region.strip():
            raise AudioError('Enter both your Azure Speech key and region before saving.')
        config = CloudConfig.from_values(key, region, True)
        try:
            self.backend_factory().set_password(self.SERVICE, self.ACCOUNT,
                json.dumps({'key': config.key, 'region': config.region}))
        except Exception:
            raise AudioError('Could not save credentials in macOS Keychain. Nothing was saved in a settings file.') from None

    def forget(self):
        try:
            self.backend_factory().delete_password(self.SERVICE, self.ACCOUNT)
        except Exception:
            raise AudioError('Could not remove the saved credential. It may be absent or Keychain access was denied.') from None

    def config(self, confirm_f0, segmentation_silence_ms=None):
        if not confirm_f0:
            return CloudConfig.from_values('', '', False)
        # An incomplete environment must fail, never silently mix two accounts.
        if os.environ.get('AZURE_SPEECH_KEY') or os.environ.get('AZURE_SPEECH_REGION'):
            return CloudConfig.from_environment(confirm_f0, segmentation_silence_ms)
        try:
            value = self.backend_factory().get_password(self.SERVICE, self.ACCOUNT)
            data = json.loads(value) if value else {}
            key, region = data.get('key', ''), data.get('region', '')
            if not isinstance(key, str) or not isinstance(region, str):
                raise ValueError('Invalid credential')
        except Exception:
            raise AudioError('Cannot read Azure credentials from macOS Keychain. Open Azure setup or allow Keychain access.') from None
        if not key or not region:
            raise AudioError('Open Azure setup to save your key and region in macOS Keychain.')
        return CloudConfig.from_values(key, region, confirm_f0, segmentation_silence_ms)


class Preferences:
    """Allowlisted UI settings only. Never save transcripts, export paths or F0 consent."""
    CHOICES = {'theme': ('system', 'light', 'dark'), 'source': ('system', 'microphone'),
               'view': ('bilingual', 'english'), 'caption_size': (12, 14, 16, 18, 22, 26)}

    def __init__(self, settings=None):
        self.settings = settings if settings is not None else QSettings('Liltide', 'Liltide')

    def load(self):
        result = {}
        for key, choices in self.CHOICES.items():
            value = self.settings.value(key)
            if key == 'caption_size':
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    continue
            if value in choices:
                result[key] = value
        return result

    def save(self, values):
        for key, choices in self.CHOICES.items():
            if values.get(key) in choices:
                self.settings.setValue(key, values[key])
        self.sync()

    def remembered_input(self):
        value = self.settings.value('input_uid', '')
        source = self.settings.value('input_source', '')
        return (source, value) if isinstance(value, str) and value and source in ('system', 'microphone') else None

    def remember_input(self, source=None, uid=None):
        for key in ('input_source', 'input_uid'):
            self.settings.remove(key)
        if source in ('system', 'microphone') and isinstance(uid, str) and uid:
            self.settings.setValue('input_source', source)
            self.settings.setValue('input_uid', uid)
        self.sync()

    def sync(self):
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            raise AudioError('Could not save display preferences. Your captions and credentials are unaffected.')


class AzureSetupDialog(QDialog):
    def __init__(self, credentials, parent=None):
        super().__init__(parent)
        self.credentials = credentials
        self.setWindowTitle('Liltide — Azure setup')
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        notice = QLabel('Enter the key and region of your Azure Speech F0 resource. '
                        'Save stores both in macOS Keychain, without contacting Azure. '
                        'Terminal environment credentials take precedence when present.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        form = QFormLayout()
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setAccessibleName('Azure Speech key')
        self.region = QLineEdit()
        self.region.setPlaceholderText('For example: westeurope')
        form.addRow('Speech &key', self.key)
        form.addRow('Azure &region', self.region)
        layout.addLayout(form)
        self.message = QLabel('Existing keys are never displayed. Keychain may ask for permission.')
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.save_button = QPushButton('Save in Keychain')
        self.save_button.clicked.connect(self.save)
        layout.addWidget(self.save_button)
        self.forget_button = QPushButton('Forget saved Azure credentials')
        self.forget_button.clicked.connect(self.forget)
        layout.addWidget(self.forget_button)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        try:
            self.credentials.save(self.key.text(), self.region.text())
        except AudioError as exc:
            self.message.setText(str(exc))
        else:
            self.key.clear()
            self.message.setText('Saved in macOS Keychain. Verify F0 in Azure, then check the F0 confirmation before Start.')

    def forget(self):
        try:
            self.credentials.forget()
        except AudioError as exc:
            self.message.setText(str(exc))
        else:
            self.key.clear()
            self.message.setText('Saved Azure credentials removed from Keychain. Environment credentials are unaffected.')

    def done(self, result):
        self.key.clear()
        super().done(result)
