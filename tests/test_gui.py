"""Offscreen GUI tests use synthetic inputs/providers only; never access audio or cloud."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from threading import Event
import time

import pytest
pytest.importorskip('PySide6')
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from liltide.audio import AudioError, Device
from liltide.gui_window import MainWindow, DiscoveryWorker, SessionWorker
from liltide.provider import Caption, CloudConfig, ProviderError


@pytest.fixture(scope='module')
def qt():
    return QApplication.instance() or QApplication([])


def until(qt, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate():
        qt.processEvents()
        if time.monotonic() > deadline:
            pytest.fail('GUI operation did not finish in time')
        time.sleep(.005)
    qt.processEvents()


class Backend:
    def devices(self):
        return [Device('system-id', 'Synthetic loopback', 2, 'system'),
                Device('mic-id', 'Synthetic microphone', 1, 'microphone')]
    def select(self, device, source):
        assert (device, source) in [('system-id', 'system'), ('mic-id', 'microphone')]


class Source:
    rate = 16000
    def __init__(self, *args):
        self.closed = False
    def resume(self):
        pass
    def read(self):
        return None
    def close(self):
        self.closed = True


class Provider:
    def __init__(self, config):
        self.sent = False
        self.aborted = False
    def start(self):
        pass
    def poll(self):
        if not self.sent:
            self.sent = True
            return [Caption('0', 0, 100, '<b>Zażółć</b>', 'Hello', False),
                    Caption('0', 0, 100, 'Zażółć gęślą jaźń', 'Hello', True)]
        return []
    def write(self, data):
        pass
    def finish(self):
        yield Caption('1', 100, 200, 'Koniec', 'End', True)
    def abort(self):
        self.aborted = True


def worker_factory(sources, providers, provider_class=Provider):
    def create(device, source, config):
        def make_source(*args):
            item = Source(*args)
            sources.append(item)
            return item
        def make_provider(config):
            item = provider_class(config)
            providers.append(item)
            return item
        return SessionWorker(device, source, config, backend_factory=Backend,
                             source_factory=make_source, provider_factory=make_provider)
    return create


@pytest.fixture
def window(qt, monkeypatch):
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'synthetic-not-a-real-key')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'westeurope')
    sources, providers = [], []
    window = MainWindow(discovery_factory=lambda: DiscoveryWorker(Backend),
                        worker_factory=worker_factory(sources, providers))
    window.show()
    yield window, sources, providers
    if window.worker:
        window.stop_session()
        until(qt, lambda: window.worker is None)
    window.close()
    qt.processEvents()


def discover(window, qt):
    window.refresh_devices()
    until(qt, lambda: window.discovery is None)


def test_f0_and_credentials_gate_no_start(window, qt, monkeypatch):
    win, sources, providers = window
    discover(win, qt)
    win.start_session()
    assert 'F0' in win.status.text() and not sources and not providers
    win.confirm.setChecked(True)
    monkeypatch.delenv('AZURE_SPEECH_KEY')
    win.start_session()
    assert 'AZURE_SPEECH_KEY' in win.status.text() and win.worker is None


def test_device_selection_filters_without_silent_fallback(window, qt):
    win, _, _ = window
    discover(win, qt)
    assert win.device.currentData() == 'system-id' and win.device.count() == 1
    win.source.setCurrentIndex(1)
    assert win.device.currentData() == 'mic-id' and win.device.count() == 1


def test_responsive_stop_drains_final_and_retains_prior_text(window, qt, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    win, sources, providers = window
    discover(win, qt)
    win.confirm.setChecked(True)
    win.start_session()
    ticks = []
    QTimer.singleShot(0, lambda: ticks.append(True))
    until(qt, lambda: 'Zażółć gęślą jaźń' in win.transcript.toPlainText())
    assert ticks and not win.start.isEnabled() and win.stop.isEnabled()
    win.start_session()  # A second click cannot create a concurrent session.
    assert len(sources) == len(providers) == 1
    win.stop_session()
    until(qt, lambda: win.worker is None)
    assert sources[0].closed and providers[0].aborted
    assert 'Koniec' in win.transcript.toPlainText() and win.start.isEnabled()
    win.start_session()
    until(qt, lambda: len(providers) == 2)
    win.stop_session()
    until(qt, lambda: win.worker is None)
    assert win.transcript.toPlainText().count('— New session') == 2
    assert list(tmp_path.iterdir()) == []


def test_window_close_waits_for_cleanup(window, qt):
    win, sources, providers = window
    discover(win, qt)
    win.confirm.setChecked(True)
    win.start_session()
    until(qt, lambda: bool(providers))
    win.close()
    assert win.closing
    until(qt, lambda: win.worker is None and not win.isVisible())
    assert sources[0].closed and providers[0].aborted


def test_provisional_coalesced_and_final_backlog_is_bounded(qt):
    worker = SessionWorker('system-id', 'system', CloudConfig('fake', 'westeurope'))
    for index in range(1000):
        worker.caption(Caption(str(index), 0, 1, str(index), None, False))
    assert worker.provisional.polish == '999' and worker.finals.empty()
    for index in range(256):
        worker.caption(Caption(str(index), 0, 1, 'Test', 'Test', True))
    with pytest.raises(AudioError, match='backlog'):
        worker.caption(Caption('overflow', 0, 1, 'Test', 'Test', True))


def test_error_is_visible_and_resources_released(qt):
    sources, providers = [], []
    class FailedProvider(Provider):
        def poll(self):
            raise ProviderError('Synthetic quota failure', reason='rate_or_quota_limit')
    worker = worker_factory(sources, providers, FailedProvider)('system-id', 'system', CloudConfig('fake', 'westeurope'))
    worker.start()
    until(qt, worker.isFinished)
    worker.wait()
    assert 'quota' in worker.error and sources[0].closed and providers[0].aborted
    assert worker.config is None


def test_stop_during_recovery_wait_does_not_reconnect(qt):
    sources, providers = [], []
    class OfflineProvider(Provider):
        def start(self):
            raise ProviderError('Synthetic connection failure', reason='connection_failure', retryable=True)
    worker = worker_factory(sources, providers, OfflineProvider)('system-id', 'system', CloudConfig('fake', 'westeurope'))
    worker.start()
    until(qt, lambda: 'Reconnecting' in worker.status)
    worker.stop_requested.set()
    until(qt, worker.isFinished)
    worker.wait()
    assert len(providers) == 1 and not worker.error and sources[0].closed


def test_discovery_error_can_be_retried(qt):
    class BrokenBackend:
        def devices(self):
            raise RuntimeError('private diagnostic')
    win = MainWindow(discovery_factory=lambda: DiscoveryWorker(BrokenBackend))
    win.refresh_devices()
    until(qt, lambda: win.discovery is None)
    assert 'Cannot list inputs' in win.status.text()
    assert 'private diagnostic' not in win.status.text() and win.refresh.isEnabled()
    win.close()


def test_cancel_before_start_never_constructs_source_or_provider(qt):
    sources, providers = [], []
    worker = worker_factory(sources, providers)('system-id', 'system', CloudConfig('fake', 'westeurope'))
    worker.stop_requested.set()
    worker.start()
    until(qt, worker.isFinished)
    worker.wait()
    assert not sources and not providers and not worker.error


def test_stop_while_provider_starts_waits_for_cleanup(qt):
    sources, providers = [], []
    entered, release = Event(), Event()
    class SlowProvider(Provider):
        def start(self):
            entered.set()
            assert release.wait(3)
    worker = worker_factory(sources, providers, SlowProvider)('system-id', 'system', CloudConfig('fake', 'westeurope'))
    worker.start()
    until(qt, entered.is_set)
    worker.stop_requested.set()
    assert worker.isRunning()
    release.set()
    until(qt, worker.isFinished)
    worker.wait()
    assert sources[0].closed and providers[0].aborted and not worker.error
