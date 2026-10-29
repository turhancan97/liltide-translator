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
        self.reads = 0
    def resume(self):
        pass
    def read(self):
        self.reads += 1
        return None
    def close(self):
        self.closed = True


class Provider:
    def __init__(self, config):
        self.sent = False
        self.aborted = False
        self.polls = 0
    def start(self):
        pass
    def poll(self):
        self.polls += 1
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
    def create(device, source, config, **kwargs):
        def make_source(*args):
            item = Source(*args)
            sources.append(item)
            return item
        def make_provider(config):
            item = provider_class(config)
            providers.append(item)
            return item
        return SessionWorker(device, source, config, backend_factory=Backend,
                             source_factory=make_source, provider_factory=make_provider, **kwargs)
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
    until(qt, lambda: worker.state == 'Reconnecting')
    assert 'Reconnecting' in worker.status and not worker.request_pause()
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


def start_running(win, qt):
    discover(win, qt)
    win.confirm.setChecked(True)
    win.start_session()
    until(qt, lambda: win.state_label.text() == 'State: Running')


def test_pause_resume_fresh_context_preserves_captions(window, qt):
    win, sources, providers = window
    start_running(win, qt)
    until(qt, lambda: 'Zażółć gęślą jaźń' in win.transcript.toPlainText())
    worker = win.worker
    win.pause_session()
    assert not win.pause.isEnabled()
    assert not worker.request_pause()  # Repeated clicks cannot queue extra toggles.
    until(qt, lambda: win.state_label.text() == 'State: Paused')
    assert sources[0].closed and providers[0].aborted
    assert 'Koniec' in win.transcript.toPlainText()  # Pause drains final results.
    assert win.provisional.text() == 'Provisional: —'
    assert win.pause.text() == 'Resume' and win.pause.isEnabled()
    assert 'Press p' not in win.status.text()
    activity = (sources[0].reads, providers[0].polls)
    idle = Event()
    QTimer.singleShot(75, idle.set)
    until(qt, idle.is_set)
    assert (sources[0].reads, providers[0].polls) == activity
    assert len(sources) == len(providers) == 1
    win.pause_session()
    until(qt, lambda: len(sources) == 2 and win.state_label.text() == 'State: Running')
    until(qt, lambda: win.transcript.toPlainText().count('Zażółć gęślą jaźń') == 2)
    assert win.worker is worker and len(providers) == 2
    assert win.pause.text() == 'Pause' and win.transcript.toPlainText().count('— New session') == 1
    assert len({event.segment_id for event in win.history if event is not None}) == 3


@pytest.mark.parametrize('close', [False, True])
def test_stop_or_close_while_paused_never_reopens_capture(window, qt, close):
    win, sources, providers = window
    start_running(win, qt)
    win.pause_session()
    until(qt, lambda: win.state_label.text() == 'State: Paused')
    if close:
        win.close()
    else:
        win.stop_session()
    until(qt, lambda: win.worker is None)
    assert len(sources) == len(providers) == 1
    assert sources[0].closed and providers[0].aborted
    assert win.state_label.text() == 'State: Stopped' and not win.pause.isEnabled()


def test_view_switch_reformats_history_and_provisional_without_restart(window, qt):
    win, sources, providers = window
    start_running(win, qt)
    until(qt, lambda: 'Zażółć gęślą jaźń' in win.transcript.toPlainText())
    worker = win.worker
    worker.caption(Caption('provisional', 0, 1, '<b>Polski</b>', '<i>English</i>', False))
    win.view.setCurrentIndex(1)
    assert 'PL:' not in win.transcript.toPlainText() and 'Zażółć' not in win.transcript.toPlainText()
    assert 'EN: Hello' in win.transcript.toPlainText()
    assert win.provisional.text() == 'Provisional · EN: <i>English</i>'
    assert win.worker is worker and len(sources) == len(providers) == 1
    win.view.setCurrentIndex(0)
    assert 'PL: Zażółć' in win.transcript.toPlainText()
    assert '<b>Polski</b>' in win.provisional.text()
    win.stop_session()
    until(qt, lambda: win.worker is None)
    history = list(win.history)
    win.view.setCurrentIndex(1)
    assert 'PL:' not in win.transcript.toPlainText() and 'EN: End' in win.transcript.toPlainText()
    win.view.setCurrentIndex(0)
    assert 'Koniec' in win.transcript.toPlainText() and win.history == history


def test_english_view_preserves_unavailable_translation_and_future_sessions(window, qt):
    win, _, _ = window
    win.view.setCurrentIndex(1)
    win.history.extend([None, Caption('0', 0, 10, 'Źródło', None, True)])
    win.change_view()
    assert '[translation unavailable]' in win.transcript.toPlainText()
    assert 'Źródło' not in win.transcript.toPlainText()
    start_running(win, qt)
    until(qt, lambda: 'EN: Hello' in win.transcript.toPlainText())
    assert 'PL:' not in win.transcript.toPlainText()
    win.view.setCurrentIndex(0)
    assert 'Źródło' in win.transcript.toPlainText() and 'Zażółć' in win.transcript.toPlainText()


def test_fatal_resume_state_preserves_history(qt, monkeypatch):
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'synthetic-not-a-real-key')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'westeurope')
    sources, providers = [], []
    class FailingResume(Provider):
        def start(self):
            if len(providers) > 1:
                raise ProviderError('Synthetic quota failure', reason='rate_or_quota_limit')
    win = MainWindow(discovery_factory=lambda: DiscoveryWorker(Backend),
                     worker_factory=worker_factory(sources, providers, FailingResume))
    try:
        start_running(win, qt)
        win.pause_session()
        until(qt, lambda: win.state_label.text() == 'State: Paused')
        win.pause_session()
        until(qt, lambda: win.worker is None)
        assert win.state_label.text() == 'State: Error' and 'quota' in win.status.text()
        assert win.start.isEnabled() and not win.pause.isEnabled()
        assert all(source.closed for source in sources) and all(provider.aborted for provider in providers)
        assert 'Koniec' in win.transcript.toPlainText()
    finally:
        if win.worker:
            win.stop_session()
            until(qt, lambda: win.worker is None)
        win.close()


def enable_export(win, kind, path):
    enabled, field, _ = win.export_controls[kind]
    enabled.setChecked(True)
    field.setText(str(path))


@pytest.mark.parametrize('formats', [('text',), ('jsonl',), ('text', 'jsonl')])
def test_gui_optional_exports_durable_bilingual_header_and_pause(window, qt, tmp_path, formats):
    import json
    win, sources, providers = window
    win.view.setCurrentIndex(1)
    for kind in formats:
        enable_export(win, kind, tmp_path / f'session.{kind}')
    start_running(win, qt)
    until(qt, lambda: 'EN: Hello' in win.transcript.toPlainText())
    for enabled, field, browse in win.export_controls.values():
        assert not enabled.isEnabled() and not field.isEnabled() and not browse.isEnabled()
    if 'jsonl' in formats:
        rows = [json.loads(line) for line in (tmp_path / 'session.jsonl').read_text().splitlines()]
        assert [row['type'] for row in rows] == ['session', 'segment']
        assert rows[0]['input_type'] == 'system' and rows[0]['segmentation_mode'] == 'service_default'
        assert rows[1]['source_text'] == 'Zażółć gęślą jaźń'
    win.pause_session()
    until(qt, lambda: win.state_label.text() == 'State: Paused')
    win.pause_session()
    until(qt, lambda: len(providers) == 2 and win.state_label.text() == 'State: Running')
    win.stop_session()
    until(qt, lambda: win.worker is None)
    assert set(path.name for path in tmp_path.iterdir()) == {f'session.{kind}' for kind in formats}
    if 'text' in formats:
        content = (tmp_path / 'session.text').read_text()
        assert content.startswith('[session]') and 'PL: Zażółć' in content and 'EN: Hello' in content
    if 'jsonl' in formats:
        rows = [json.loads(line) for line in (tmp_path / 'session.jsonl').read_text().splitlines()]
        assert sum(row['type'] == 'session' for row in rows) == 1
        assert len({row['session_id'] for row in rows}) == 1
        assert len({row['segment_id'] for row in rows if row['type'] == 'segment'}) == len(rows) - 1
        assert 'synthetic-not-a-real-key' not in (tmp_path / 'session.jsonl').read_text()
    assert all(source.closed for source in sources)
    assert 'final captions received' in win.summary_label.text()


@pytest.mark.parametrize('failure', ['existing', 'same', 'missing_parent', 'blank'])
def test_gui_export_preflight_stops_before_capture(window, qt, tmp_path, failure):
    win, sources, providers = window
    path = tmp_path / 'session.jsonl'
    if failure == 'existing':
        path.write_text('keep existing content')
    elif failure == 'missing_parent':
        path = tmp_path / 'absent' / 'session.jsonl'
    enable_export(win, 'jsonl', '' if failure == 'blank' else path)
    if failure == 'same':
        enable_export(win, 'text', path)
    discover(win, qt)
    win.confirm.setChecked(True)
    win.start_session()
    until(qt, lambda: win.worker is None)
    assert win.state_label.text() == 'State: Error' and not sources and not providers
    assert win.start.isEnabled()
    if failure == 'existing':
        assert path.read_text() == 'keep existing content'
    else:
        assert list(tmp_path.iterdir()) == []


def test_gui_header_failure_prevents_capture_and_closes_destinations(window, qt, tmp_path, monkeypatch):
    from liltide.exports import TranscriptExports
    win, sources, providers = window
    enable_export(win, 'jsonl', tmp_path / 'session.jsonl')
    handles = []
    def fail_header(sink, *args):
        handles.extend(file for _, _, file in sink.files)
        raise AudioError('Synthetic header write failure')
    monkeypatch.setattr(TranscriptExports, '_write', fail_header)
    discover(win, qt)
    win.confirm.setChecked(True)
    win.start_session()
    until(qt, lambda: win.worker is None)
    assert not sources and not providers and handles and all(file.closed for file in handles)
    assert 'header write failure' in win.status.text()
    assert '0 final captions received' in win.summary_label.text()


def test_gui_export_error_retains_saved_data_and_reports_received_counts(window, qt, tmp_path, monkeypatch):
    import json
    from liltide.exports import TranscriptExports
    win, sources, providers = window
    path = tmp_path / 'session.jsonl'
    enable_export(win, 'jsonl', path)
    original = TranscriptExports.caption
    def fail_second(sink, event):
        if event.polish == 'Koniec':
            raise AudioError('Synthetic export write failure')
        original(sink, event)
    monkeypatch.setattr(TranscriptExports, 'caption', fail_second)
    start_running(win, qt)
    until(qt, lambda: 'Zażółć' in win.transcript.toPlainText())
    win.stop_session()
    until(qt, lambda: win.worker is None)
    assert win.state_label.text() == 'State: Error' and 'export write failure' in win.status.text()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row['type'] for row in rows] == ['session', 'segment']
    assert 'Zażółć' in win.transcript.toPlainText()
    assert win.last_summary['final_captions'] == 2  # Received, not necessarily persisted/displayed.
    assert 'do not guarantee successful persistence' in win.summary_label.text()
    assert sources[0].closed and providers[0].aborted


def test_gui_recovery_exports_gap_and_one_header(qt, tmp_path, monkeypatch):
    import json
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'synthetic-not-a-real-key')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'westeurope')
    sources, providers = [], []
    class FirstOffline(Provider):
        def start(self):
            if len(providers) == 1:
                raise ProviderError('Synthetic offline', reason='connection_failure', retryable=True)
    win = MainWindow(discovery_factory=lambda: DiscoveryWorker(Backend),
                     worker_factory=worker_factory(sources, providers, FirstOffline))
    path = tmp_path / 'session.jsonl'
    enable_export(win, 'jsonl', path)
    try:
        discover(win, qt)
        win.confirm.setChecked(True)
        win.start_session()
        until(qt, lambda: 'Zażółć' in win.transcript.toPlainText())
        win.stop_session()
        until(qt, lambda: win.worker is None)
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        types = [row['type'] for row in rows]
        assert types[0] == 'session' and types.count('session') == 1 and 'gap' in types and 'segment' in types
        assert len({row['session_id'] for row in rows}) == 1
        assert all(source.closed for source in sources)
    finally:
        if win.worker:
            win.stop_session()
            until(qt, lambda: win.worker is None)
        win.close()


def test_timing_toggle_reformats_history_and_summary_without_restart(window, qt):
    from dataclasses import replace
    from liltide.timing import timing_summary
    win, _, providers = window
    start_running(win, qt)
    until(qt, lambda: 'Zażółć' in win.transcript.toPlainText())
    timed = replace(win.history[-1], arrival_ms=1000, handled_ms=1040,
        timing_source='provider_callback', dispatch_delay_ms=40,
        first_provisional_arrival_ms=500, provisional_to_final_ms=500, estimated_final_delay_ms=-10)
    win.history[-1] = timed
    win.worker.caption(replace(timed, final=False))
    win.show_timing.setChecked(True)
    assert 'Arrival: 00:00:01.000 (provider_callback)' in win.transcript.toPlainText()
    assert 'estimated final delay: -10 ms (not benchmark latency)' in win.transcript.toPlainText()
    assert 'Arrival: 00:00:01.000' in win.provisional.text()
    assert len(providers) == 1
    win.stop_session()
    until(qt, lambda: win.worker is None)
    assert win.last_summary['final_captions'] == 2 and win.last_summary['handler_only_captions'] == 2
    win.last_summary = timing_summary([timed])
    win.render_summary()
    text = win.summary_label.text()
    assert 'median=-10 ms, p95=-10 ms, max=-10 ms' in text
    assert '1 negative estimates retained' in text and 'not benchmark latency' in text
    win.view.setCurrentIndex(1)
    assert 'PL:' not in win.transcript.toPlainText() and 'Arrival:' in win.transcript.toPlainText()
    win.show_timing.setChecked(False)
    assert 'Arrival:' not in win.transcript.toPlainText() and 'median=' not in win.summary_label.text()


def test_summary_zero_samples_after_early_failure(window, qt):
    from liltide.timing import timing_summary
    win, _, _ = window
    win.last_summary = timing_summary([])
    win.show_timing.setChecked(True)
    assert '0 final captions received' in win.summary_label.text()
    assert win.summary_label.text().count('no samples.') == 3


def test_export_browse_cancel_and_selected_filename(window, qt, tmp_path, monkeypatch):
    from liltide.gui_window import QFileDialog
    win, _, _ = window
    enabled, field, browse = win.export_controls['text']
    assert not enabled.isChecked() and not field.isEnabled() and not browse.isEnabled()
    enabled.setChecked(True)
    field.setText(str(tmp_path / 'original.txt'))
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **kw: ('', ''))
    browse.click()
    assert field.text().endswith('original.txt')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **kw: (str(tmp_path / 'selected.txt'), ''))
    browse.click()
    assert field.text().endswith('selected.txt') and list(tmp_path.iterdir()) == []


def test_unchecked_export_paths_and_timing_do_not_create_files(window, qt, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    win, _, _ = window
    for kind, (enabled, field, _) in win.export_controls.items():
        field.setText(str(tmp_path / f'not-enabled.{kind}'))
        assert not enabled.isChecked()
    win.show_timing.setChecked(True)
    start_running(win, qt)
    until(qt, lambda: 'Zażółć' in win.transcript.toPlainText())
    win.stop_session()
    until(qt, lambda: win.worker is None)
    assert list(tmp_path.iterdir()) == []
    assert '2 final captions received' in win.summary_label.text()
    assert win.summary_label.text().count('no samples.') == 3


def test_appearance_changes_preserve_worker_history_and_export_configuration(window, qt, tmp_path):
    win, sources, providers = window
    enable_export(win, 'jsonl', tmp_path / 'appearance.jsonl')
    start_running(win, qt)
    until(qt, lambda: 'Zażółć' in win.transcript.toPlainText())
    worker, history = win.worker, list(win.history)
    for mode in ('dark', 'light', 'system'):
        win.theme.setCurrentIndex(win.theme.findData(mode))
        for size in (12, 26, 16):
            win.caption_size.setCurrentIndex(win.caption_size.findData(size))
            assert win.transcript.font().pointSize() == size
            assert win.provisional.font().pointSize() == size
        assert win.worker is worker and win.history == history
        assert len(sources) == len(providers) == 1
        assert win.export_controls['jsonl'][0].isChecked()
        assert not win.export_controls['jsonl'][1].isEnabled()
    win.stop_session()
    until(qt, lambda: win.worker is None)
    assert win.last_summary['final_captions'] == 2


def test_system_theme_follows_notifications_and_manual_override_is_stable(window, qt, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPalette
    win, _, _ = window
    assert win.theme.currentData() == 'system'
    monkeypatch.setattr(win, 'system_theme', lambda: 'dark')
    win.system_theme_changed(Qt.ColorScheme.Dark)
    assert win.effective_theme == 'dark'
    assert win.palette().color(QPalette.ColorRole.Window).name() == '#17212b'
    win.theme.setCurrentIndex(win.theme.findData('light'))
    win.system_theme_changed(Qt.ColorScheme.Dark)
    assert win.effective_theme == 'light'
    win.theme.setCurrentIndex(win.theme.findData('system'))
    assert win.effective_theme == 'dark'
    monkeypatch.setattr(win, 'system_theme', lambda: 'light')
    win.system_theme_changed(Qt.ColorScheme.Light)
    assert win.effective_theme == 'light'


def test_small_window_keeps_setup_scrollable_and_caption_size_selection(window, qt):
    win, _, _ = window
    win.resize(760, 600)
    win.show_timing.setChecked(True)
    qt.processEvents()
    assert win.setup_scroll.verticalScrollBar().maximum() > 0
    assert win.transcript.width() > 200 and win.transcript.height() > 50
    win.caption_size.setCurrentIndex(win.caption_size.findData(22))
    assert win.transcript.font().pointSize() == 22
    assert win.transcript.isReadOnly()


def test_keyboard_controls_use_session_guards_and_skip_disabled_widgets(window, qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    win, sources, providers = window
    discover(win, qt)
    win.confirm.setChecked(True)
    win.activateWindow()
    win.raise_()
    until(qt, win.isActiveWindow)
    QTest.keyClick(win, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    until(qt, lambda: win.state_label.text() == 'State: Running')
    QTest.keyClick(win, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert len(providers) == 1
    QTest.keyClick(win, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier)
    until(qt, lambda: win.state_label.text() == 'State: Paused')
    QTest.keyClick(win, Qt.Key.Key_Period, Qt.KeyboardModifier.ControlModifier)
    until(qt, lambda: win.worker is None)
    assert sources[0].closed and providers[0].aborted
    win.theme.setFocus()
    QTest.keyClick(win.theme, Qt.Key.Key_Tab)
    assert QApplication.focusWidget() is win.floating_button
    QTest.keyClick(win.floating_button, Qt.Key.Key_Tab)
    assert QApplication.focusWidget() is win.source


@pytest.mark.parametrize('mode', ['light', 'dark'])
def test_theme_text_and_selection_meet_normal_text_contrast(window, qt, mode):
    from PySide6.QtGui import QPalette
    win, _, _ = window
    win.theme.setCurrentIndex(win.theme.findData(mode))
    qt.processEvents()
    def luminance(color):
        values = [color.redF(), color.greenF(), color.blueF()]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))
    for text, background in [(QPalette.ColorRole.Text, QPalette.ColorRole.Base),
                             (QPalette.ColorRole.HighlightedText, QPalette.ColorRole.Highlight)]:
        palette = win.transcript.palette()
        a, b = sorted([luminance(palette.color(text)), luminance(palette.color(background))])
        assert (b + .05) / (a + .05) >= 4.5


@pytest.mark.parametrize('mode', ['light', 'dark'])
@pytest.mark.parametrize('name', ['theme', 'caption_size', 'view', 'source', 'device'])
def test_dropdown_popup_fits_text_and_allows_selection(window, qt, mode, name):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtTest import QTest
    win, _, _ = window
    win.resize(760, 600)
    win.theme.setCurrentIndex(win.theme.findData(mode))
    combo = getattr(win, name)
    if name == 'device':
        combo.addItem('Synthetic capture endpoint with a longer device name', 'synthetic-id')
    font = QFont(combo.font())
    font.setPointSize(18)
    combo.setFont(font)
    qt.processEvents()
    combo.showPopup()
    qt.processEvents()
    try:
        view = combo.view()
        assert view.isVisible()
        for row in range(combo.count()):
            index = combo.model().index(row, 0)
            rect = view.visualRect(index)
            assert rect.width() <= view.viewport().width()
            assert rect.width() >= combo.fontMetrics().horizontalAdvance(combo.itemText(row)) + 20
            assert rect.height() >= combo.fontMetrics().height() + 12
        last = combo.count() - 1
        index = combo.model().index(last, 0)
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.visualRect(index).center())
        assert combo.currentIndex() == last
        if name == 'caption_size':
            assert win.transcript.font().pointSize() == 26
    finally:
        combo.hidePopup()


def test_floating_view_is_opt_in_and_close_only_hides_it(window, qt, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    monkeypatch.chdir(tmp_path)
    win, sources, providers = window
    floating = win.floating
    assert not floating.isVisible() and not win.floating_button.isChecked()
    win.floating_button.click()
    qt.processEvents()
    assert floating.isVisible()
    assert floating.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert floating.testAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
    assert not sources and not providers and list(tmp_path.iterdir()) == []
    floating.close()
    assert not floating.isVisible() and not win.floating_button.isChecked()
    win.floating_button.click()
    assert win.floating is floating and floating.isVisible()


def test_floating_mirrors_session_and_language_size_controls(window, qt):
    from PySide6.QtGui import QPalette
    win, sources, providers = window
    start_running(win, qt)
    win.floating_button.click()
    floating, worker = win.floating, win.worker
    until(qt, lambda: 'Zażółć' in floating.final_text.toPlainText())
    provisional = Caption('draft', 100, 200, '<b>Wstępny napis</b>', '<i>Draft caption</i>', False)
    worker.caption(provisional)
    until(qt, lambda: '<i>Draft caption</i>' in floating.provisional_text.toPlainText())
    assert floating.provisional_text.toPlainText().startswith('Provisional\n')
    assert floating.final_text.toPlainText().startswith('Finalized [')
    floating.view.setCurrentIndex(floating.view.findData('english'))
    assert win.view.currentData() == 'english'
    assert 'PL:' not in floating.final_text.toPlainText() and 'EN: Hello' in floating.final_text.toPlainText()
    assert 'PL:' not in floating.provisional_text.toPlainText()
    floating.caption_size.setCurrentIndex(floating.caption_size.findData(26))
    assert win.transcript.font().pointSize() == floating.final_text.font().pointSize() == 26
    assert floating.provisional_text.font().pointSize() == 26
    win.view.setCurrentIndex(0)
    win.caption_size.setCurrentIndex(win.caption_size.findData(14))
    assert 'PL: Zażółć' in floating.final_text.toPlainText() and floating.caption_size.currentData() == 14
    for mode in ('dark', 'light'):
        win.theme.setCurrentIndex(win.theme.findData(mode))
        assert floating.palette().color(QPalette.ColorRole.Window) == win.palette().color(QPalette.ColorRole.Window)
    assert win.worker is worker and len(sources) == len(providers) == 1


def test_floating_hide_keeps_session_running_and_reopens_with_latest(window, qt):
    win, sources, providers = window
    start_running(win, qt)
    win.floating_button.click()
    until(qt, lambda: 'Zażółć' in win.floating.final_text.toPlainText())
    worker = win.worker
    win.floating.close()
    assert not worker.stop_requested.is_set() and not sources[0].closed and not providers[0].aborted
    worker.caption(Caption('extra', 200, 300, 'Najnowszy', 'Latest', True))
    until(qt, lambda: 'Latest' in win.floating.final_text.toPlainText())
    win.floating_button.click()
    assert win.floating.isVisible() and 'Latest' in win.floating.final_text.toPlainText()
    assert win.worker is worker and len(providers) == 1


def test_floating_pause_stop_and_new_session_reset(window, qt):
    win, _, _ = window
    start_running(win, qt)
    win.floating_button.click()
    until(qt, lambda: 'Hello' in win.floating.final_text.toPlainText())
    win.pause_session()
    until(qt, lambda: win.floating.state.text() == 'State: Paused')
    assert 'EN: End' in win.floating.final_text.toPlainText()
    assert win.floating.provisional_text.toPlainText() == 'Provisional: —'
    win.stop_session()
    until(qt, lambda: win.worker is None)
    assert win.floating.state.text() == 'State: Stopped'
    assert 'EN: End' in win.floating.final_text.toPlainText()
    win.start_session()
    assert win.floating.latest_final is None and not win.floating.final_text.toPlainText()
    until(qt, lambda: 'Hello' in win.floating.final_text.toPlainText())


def test_main_close_waits_for_worker_then_hides_floating(window, qt):
    win, sources, providers = window
    start_running(win, qt)
    win.floating_button.click()
    win.close()
    until(qt, lambda: win.worker is None and not win.isVisible())
    assert not win.floating.isVisible()
    assert sources[0].closed and providers[0].aborted


def test_floating_unicode_missing_translation_and_bounded_display(window, qt):
    win, _, _ = window
    win.floating.finalized(Caption('0', 0, 100, 'Zażółć <b>gęślą</b> jaźń', None, True))
    assert 'Zażółć <b>gęślą</b> jaźń' in win.floating.final_text.toPlainText()
    assert '[translation unavailable]' in win.floating.final_text.toPlainText()
    win.floating.finalized(Caption('1', 100, 200, 'Kolejny', 'Next', True))
    assert 'Kolejny' in win.floating.final_text.toPlainText()
    assert 'Zażółć' not in win.floating.final_text.toPlainText()
    assert not win.history  # Opening/rendering the secondary view never invents history.
