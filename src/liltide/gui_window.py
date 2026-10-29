"""Desktop PoC: Qt stays on the main thread; sessions run off-thread."""

from importlib.resources import files
from queue import Empty, Full, Queue
from threading import Event, Lock
import sys

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel,
                              QFileDialog, QLineEdit, QMainWindow, QPlainTextEdit,
                              QPushButton, QVBoxLayout, QWidget, QGroupBox, QScrollArea, QSplitter)

from liltide.audio import AudioError, SoundCardBackend
from liltide.formatting import timestamp
from liltide.exports import TranscriptExports
from liltide.metadata import RunMetadata
from liltide.provider import AzureProvider, CloudConfig
from liltide.session import TranslationSession
from liltide.sources import LiveSource
from liltide.timing import timing_summary
from liltide import gui_theme
from liltide.gui_controls import Dropdown


class DiscoveryWorker(QThread):
    def __init__(self, backend_factory=SoundCardBackend):
        super().__init__()
        self.backend_factory = backend_factory
        self.devices = []
        self.error = None

    def run(self):
        try:
            self.devices = self.backend_factory().devices()
        except Exception:
            self.error = 'Cannot list inputs. Check audio permissions/routing and try Refresh devices.'


class SessionWorker(QThread):
    def __init__(self, device, source, config, *, backend_factory=SoundCardBackend,
                 source_factory=LiveSource, provider_factory=AzureProvider,
                 export_text=None, export_jsonl=None):
        super().__init__()
        self.device, self.source, self.config = device, source, config
        self.backend_factory, self.source_factory, self.provider_factory = backend_factory, source_factory, provider_factory
        self.stop_requested = Event()
        self.pause_requested = Event()
        self.finals = Queue(maxsize=256)
        self.lock = Lock()
        self.provisional = None
        self.status = 'Connecting…'
        self.state = 'Connecting'
        self.error = None
        self.export_text, self.export_jsonl = export_text, export_jsonl
        self.summary = timing_summary([])

    def request_pause(self):
        with self.lock:
            if self.stop_requested.is_set() or self.state not in ('Running', 'Paused'):
                return False
            paused = self.state == 'Paused'
            self.state = 'Connecting' if paused else 'Pausing'
            self.status = 'Resuming with fresh context…' if paused else 'Pausing… Waiting for finalized captions and resource release.'
            self.provisional = None
            self.pause_requested.set()
            return True

    def control(self):
        if self.pause_requested.is_set():
            self.pause_requested.clear()
            return 'pause'
        return None

    def set_state(self, state):
        with self.lock:
            self.state = 'Stopping' if self.stop_requested.is_set() else state

    def caption(self, event):
        with self.lock:
            self.provisional = None if event.final else event
        if event.final:
            try:
                self.finals.put_nowait(event)
            except Full as exc:
                raise AudioError('Caption display backlog exceeded its limit. Session stopped; previously displayed text remains.') from exc

    def set_status(self, message):
        # The shared core's terminal keyboard hints do not apply to this window.
        message = message.replace('Press p to pause/resume in an interactive terminal; Ctrl+C stops.', 'Use Stop to finish.')
        message = message.replace('Ctrl+C cancels.', 'Stop cancels.')
        message = message.replace('Press p to resume.', 'Use Resume to continue with fresh context.')
        with self.lock:
            self.status = message
            self.provisional = None

    def run(self):
        try:
            if self.stop_requested.is_set():
                return
            metadata = RunMetadata(self.source, self.config.segmentation_silence_ms)
            with TranscriptExports(self.export_text, self.export_jsonl, metadata=metadata) as exports:
                self.backend_factory().select(self.device, self.source)
                session = TranslationSession(
                    lambda: self.source_factory(self.device, self.source, 48000),
                    lambda: self.provider_factory(self.config), self.caption, self.set_status, self.control,
                    should_stop=self.stop_requested.is_set, on_state=self.set_state,
                    on_finalized=exports.caption, on_gap=exports.gap)
                try:
                    session.run()
                finally:
                    self.summary = session.timing_summary()
        except AudioError as exc:
            self.error = str(exc)
        except Exception:
            # Never expose raw native exceptions or credentials in the window/log.
            self.error = 'Session failed unexpectedly. Check local setup before starting a new session.'
        finally:
            self.config = None  # Release the worker's reference to credentials after cleanup.
            with self.lock:
                self.provisional = None
                self.state = 'Error' if self.error else 'Stopped'


class MainWindow(QMainWindow):
    def __init__(self, *, discovery_factory=DiscoveryWorker, worker_factory=SessionWorker):
        super().__init__()
        self.discovery_factory, self.worker_factory = discovery_factory, worker_factory
        self.discovery = self.worker = None
        self.closing = False
        self.available_devices = []
        self.history = []  # Caption objects / None session separators, kept only in memory.
        self.last_summary = None
        self.setWindowTitle('Liltide — Live captions across languages')
        self.resize(1100, 820)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        self.logo = QSvgWidget()
        self.logo.load(files('liltide').joinpath('resources/symbol.svg').read_bytes())
        self.logo.setFixedSize(60, 48)
        self.logo.setAccessibleName('Liltide waveform symbol')
        header.addWidget(self.logo)
        identity = QVBoxLayout()
        title = QLabel('Liltide')
        title.setObjectName('brandTitle')
        tagline = QLabel('Live captions across languages. · Polish → English')
        tagline.setObjectName('tagline')
        identity.addWidget(title)
        identity.addWidget(tagline)
        header.addLayout(identity, 1)
        self.theme = Dropdown()
        for name in ('System', 'Light', 'Dark'):
            self.theme.addItem(name, name.lower())
        self.theme.setAccessibleName('Appearance theme')
        self.theme.setMinimumWidth(110)
        theme_label = QLabel('&Theme')
        theme_label.setBuddy(self.theme)
        header.addWidget(theme_label)
        header.addWidget(self.theme)
        layout.addLayout(header)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter, 1)
        self.setup_scroll = QScrollArea()
        self.setup_scroll.setWidgetResizable(True)
        self.setup_scroll.setMinimumWidth(310)
        setup = QWidget()
        setup_layout = QVBoxLayout(setup)
        setup_layout.setContentsMargins(0, 0, 8, 0)
        setup_layout.setSpacing(12)
        self.setup_scroll.setWidget(setup)
        self.splitter.addWidget(self.setup_scroll)
        audio_group = QGroupBox('Audio setup')
        audio = QVBoxLayout(audio_group)
        self.source = Dropdown()
        self.source.addItem('System audio', 'system')
        self.source.addItem('Microphone', 'microphone')
        self.source.setAccessibleName('Audio source type')
        source_label = QLabel('Audio &source')
        source_label.setBuddy(self.source)
        audio.addWidget(source_label)
        audio.addWidget(self.source)
        self.device = Dropdown()
        self.device.setAccessibleName('Capture device')
        self.device.setMinimumWidth(0)
        self.device.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.device.setMinimumContentsLength(12)
        device_label = QLabel('Capture &device')
        device_label.setBuddy(self.device)
        audio.addWidget(device_label)
        audio.addWidget(self.device)
        self.refresh = QPushButton('Refresh devices')
        self.refresh.clicked.connect(self.refresh_devices)
        audio.addWidget(self.refresh)
        routing = QLabel('macOS system audio: choose your routed virtual input and keep playback audible through the multi-output device.')
        routing.setWordWrap(True)
        audio.addWidget(routing)
        notice = QLabel('Start sends selected audio to Azure. No audio recording. F0 confirmation is your assertion, not a billing-tier check.')
        notice.setWordWrap(True)
        audio.addWidget(notice)
        self.confirm = QCheckBox('I verified this resource uses free F0')
        self.confirm.setAccessibleName('Confirm Azure resource uses the free F0 tier')
        audio.addWidget(self.confirm)
        setup_layout.addWidget(audio_group)
        export_group = QGroupBox('Optional exports')
        exports = QVBoxLayout(export_group)
        self.export_controls = {}
        for kind, label, suffix in (('text', 'Save text', 'txt'), ('jsonl', 'Save JSONL', 'jsonl')):
            enabled = QCheckBox(label)
            path = QLineEdit()
            path.setPlaceholderText(f'New .{suffix} file in an existing folder')
            path.setAccessibleName(f'{label} destination')
            browse = QPushButton('Browse…')
            browse.setAccessibleName(f'Browse {kind} export destination')
            row = QHBoxLayout()
            row.addWidget(enabled, 1)
            row.addWidget(browse)
            exports.addLayout(row)
            exports.addWidget(path)
            self.export_controls[kind] = (enabled, path, browse)
            enabled.toggled.connect(self.update_export_controls)
            browse.setProperty('export_kind', kind)
            browse.clicked.connect(self.browse_clicked)
        self.update_export_controls()
        export_hint = QLabel('Save the next run in Polish + English, including settings and audio gaps. Choose fresh filenames; existing files are refused.')
        export_hint.setWordWrap(True)
        exports.addWidget(export_hint)
        setup_layout.addWidget(export_group)
        setup_layout.addStretch()
        reader = QWidget()
        reader.setMinimumWidth(320)
        reading = QVBoxLayout(reader)
        reading.setContentsMargins(12, 0, 0, 0)
        reading.setSpacing(10)
        self.reader_scroll = QScrollArea()
        self.reader_scroll.setWidgetResizable(True)
        self.reader_scroll.setWidget(reader)
        self.splitter.addWidget(self.reader_scroll)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([330, 730])
        controls = QHBoxLayout()
        self.start = QPushButton('Start translation')
        self.start.setObjectName('start')
        self.pause = QPushButton('Pause')
        self.stop = QPushButton('Stop')
        self.stop.setObjectName('stop')
        self.pause.setEnabled(False)
        self.stop.setEnabled(False)
        self.start.clicked.connect(self.start_session)
        self.pause.clicked.connect(self.pause_session)
        self.stop.clicked.connect(self.stop_session)
        for widget in (self.start, self.pause, self.stop):
            controls.addWidget(widget)
        reading.addLayout(controls)
        display_row = QHBoxLayout()
        self.view = Dropdown()
        self.view.addItem('Polish + English', 'bilingual')
        self.view.addItem('English only', 'english')
        self.view.setAccessibleName('Caption display language')
        self.view.currentIndexChanged.connect(self.change_view)
        view_label = QLabel('&View')
        view_label.setBuddy(self.view)
        display_row.addWidget(view_label)
        display_row.addWidget(self.view, 1)
        self.caption_size = Dropdown()
        for size in (12, 14, 16, 18, 22, 26):
            self.caption_size.addItem(f'{size} pt', size)
        self.caption_size.setCurrentIndex(2)
        self.caption_size.setAccessibleName('Caption font size')
        self.caption_size.setMinimumWidth(100)
        size_label = QLabel('Caption si&ze')
        size_label.setBuddy(self.caption_size)
        display_row.addWidget(size_label)
        display_row.addWidget(self.caption_size)
        reading.addLayout(display_row)
        self.show_timing = QCheckBox('Show timing (delay is estimated)')
        self.show_timing.setToolTip('Display arrival details and the session timing summary. This does not enable exports.')
        self.show_timing.toggled.connect(self.change_view)
        reading.addWidget(self.show_timing)
        self.state_label = QLabel('State: Ready')
        self.state_label.setObjectName('state')
        self.state_label.setAccessibleName('Session state')
        reading.addWidget(self.state_label)
        self.status = QLabel('Refresh devices to select an input. Credentials are read from your environment on Start.')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        self.status.setAccessibleName('Session status')
        reading.addWidget(self.status)
        captions_label = QLabel('Finalized &captions')
        reading.addWidget(captions_label)
        self.transcript = QPlainTextEdit()
        self.transcript.setMinimumHeight(180)
        self.transcript.setReadOnly(True)
        self.transcript.setAccessibleName('Finalized Polish and English captions')
        self.transcript.setPlaceholderText('Finalized captions appear here. Prior runs remain visible until you close this window.')
        captions_label.setBuddy(self.transcript)
        reading.addWidget(self.transcript, 1)
        self.provisional = QLabel('Provisional: —')
        self.provisional.setObjectName('provisional')
        self.provisional.setTextFormat(Qt.TextFormat.PlainText)
        self.provisional.setWordWrap(True)
        self.provisional.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.provisional.setAccessibleName('Provisional captions')
        reading.addWidget(self.provisional)
        self.details = QGroupBox('Session details')
        details_layout = QVBoxLayout(self.details)
        self.summary_label = QLabel('Session summary: no completed run yet.')
        self.summary_label.setTextFormat(Qt.TextFormat.PlainText)
        self.summary_label.setWordWrap(True)
        self.summary_label.setAccessibleName('Last session summary')
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        details_layout.addWidget(self.summary_label)
        reading.addWidget(self.details)
        self.caption_size.currentIndexChanged.connect(self.update_caption_size)
        self.update_caption_size()
        self.theme.currentIndexChanged.connect(self.update_theme)
        QApplication.styleHints().colorSchemeChanged.connect(self.system_theme_changed)
        self.update_theme()
        self.shortcuts = []
        for key, button, hint in (('Ctrl+Return', self.start, 'Start translation'),
                                  ('Ctrl+Space', self.pause, 'Pause or resume'),
                                  ('Ctrl+.', self.stop, 'Stop')):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(button.click)
            self.shortcuts.append(shortcut)
            button.setToolTip(f'{hint} ({QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText)})')
        focus_order = [self.theme, self.source, self.device, self.refresh, self.confirm]
        for enabled, path, browse in self.export_controls.values():
            focus_order.extend((enabled, path, browse))
        focus_order.extend((self.start, self.pause, self.stop, self.view, self.caption_size,
                            self.show_timing, self.transcript, self.provisional, self.summary_label))
        for first, second in zip(focus_order, focus_order[1:]):
            QWidget.setTabOrder(first, second)
        self.source.currentIndexChanged.connect(self.populate_devices)
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def system_theme(self):
        scheme = QApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Unknown:
            return 'dark' if QApplication.palette().color(QApplication.palette().ColorRole.Window).lightness() < 128 else 'light'
        return 'dark' if scheme == Qt.ColorScheme.Dark else 'light'

    def update_theme(self):
        mode = self.theme.currentData()
        self.effective_theme = self.system_theme() if mode == 'system' else mode
        self.setPalette(gui_theme.palette(self.effective_theme))
        self.setStyleSheet(gui_theme.stylesheet(self.effective_theme))

    def system_theme_changed(self, scheme):
        if self.theme.currentData() == 'system':
            self.update_theme()

    def update_caption_size(self):
        font = QFont(QApplication.font())
        font.setPointSize(self.caption_size.currentData())
        self.transcript.setFont(font)
        self.provisional.setFont(font)

    def refresh_devices(self):
        if self.worker or self.discovery:
            return
        self.discovery = self.discovery_factory()
        self.refresh.setEnabled(False)
        self.start.setEnabled(False)
        self.status.setText('Listing devices… No audio is captured.')
        self.state_label.setText('State: Discovering')
        self.discovery.start()

    def populate_devices(self):
        old = self.device.currentData()
        self.device.clear()
        source = self.source.currentData()
        for device in self.available_devices:
            if device.kind in ('routed input', source):
                self.device.addItem(f'{device.name} ({device.channels} channels)', device.id)
        index = self.device.findData(old)
        if index >= 0:
            self.device.setCurrentIndex(index)

    def start_session(self):
        if self.worker or self.discovery or self.closing:
            return
        try:
            config = CloudConfig.from_environment(self.confirm.isChecked())
            device = self.device.currentData()
            if not device:
                raise AudioError('Select a capture device first. Use Refresh devices if the list is empty.')
            paths = {}
            for kind, (enabled, path, _) in self.export_controls.items():
                if enabled.isChecked():
                    value = path.text().strip()
                    if not value:
                        raise AudioError(f'Choose a {kind} export filename or turn off that export.')
                    paths[f'export_{kind}'] = value
            worker = self.worker_factory(device, self.source.currentData(), config, **paths)
        except AudioError as exc:
            self.state_label.setText('State: Error')
            self.status.setText('Error: ' + str(exc).replace('then pass --confirm-f0', 'then check the F0 confirmation'))
            return
        self.worker = worker
        self.last_summary = None
        self.summary_label.setText('Session summary: available after Stop or session completion.')
        self.history.append(None)
        self.transcript.appendPlainText(self.format_entry(None))
        self.set_running(True)
        self.status.setText('Connecting…')
        self.state_label.setText('State: Connecting')
        worker.start()

    def set_running(self, running):
        for widget in (self.start, self.source, self.device, self.refresh, self.confirm):
            widget.setEnabled(not running)
        self.stop.setEnabled(running)
        self.pause.setEnabled(False)
        self.pause.setText('Pause')
        self.update_export_controls()

    def update_export_controls(self):
        for enabled, path, browse in self.export_controls.values():
            enabled.setEnabled(self.worker is None)
            path.setEnabled(self.worker is None and enabled.isChecked())
            browse.setEnabled(self.worker is None and enabled.isChecked())

    def browse_export(self, kind):
        if self.worker:
            return
        suffix = 'txt' if kind == 'text' else 'jsonl'
        _, path, _ = self.export_controls[kind]
        filename, _ = QFileDialog.getSaveFileName(self, f'Choose a new {kind} export file',
            path.text(), f'{kind.upper()} files (*.{suffix});;All files (*)',
            options=QFileDialog.Option.DontConfirmOverwrite | QFileDialog.Option.DontUseNativeDialog)
        if filename:
            path.setText(filename)

    def browse_clicked(self):
        self.browse_export(self.sender().property('export_kind'))

    def pause_session(self):
        if self.worker and self.worker.request_pause():
            self.pause.setEnabled(False)
            self.poll()

    def stop_session(self):
        if self.worker:
            self.worker.stop_requested.set()
            self.stop.setEnabled(False)
            self.pause.setEnabled(False)
            self.state_label.setText('State: Stopping')
            self.status.setText('Stopping… Waiting for capture/cloud cleanup and finalized captions.')

    def poll(self):
        if self.discovery and self.discovery.isFinished():
            discovery, self.discovery = self.discovery, None
            discovery.wait()
            self.available_devices = discovery.devices
            self.populate_devices()
            self.status.setText(discovery.error or f'{len(self.available_devices)} input(s) found. Select a device before starting.')
            self.state_label.setText('State: Error' if discovery.error else 'State: Ready')
            self.refresh.setEnabled(True)
            self.start.setEnabled(True)
            discovery.deleteLater()
        if self.worker:
            worker = self.worker
            self.drain_captions(worker)
            with worker.lock:
                provisional, status, state = worker.provisional, worker.status, worker.state
            self.render_provisional(provisional)
            stopping = worker.stop_requested.is_set()
            self.state_label.setText('State: Stopping' if stopping else f'State: {state}')
            self.pause.setText('Resume' if state == 'Paused' else 'Pause')
            self.pause.setEnabled(not stopping and state in ('Running', 'Paused'))
            if not worker.stop_requested.is_set():
                self.status.setText(status)
            if worker.isFinished():
                worker.wait()
                self.drain_captions(worker)  # Include finals queued between the first drain and thread exit.
                self.status.setText('Error: ' + worker.error if worker.error else 'Stopped. Capture and cloud resources released.')
                self.state_label.setText('State: Error' if worker.error else 'State: Stopped')
                self.provisional.setText('Provisional: —')
                self.last_summary = worker.summary
                self.render_summary()
                self.worker = None
                self.set_running(False)
                worker.deleteLater()
        if self.closing and self.worker is None and self.discovery is None:
            self.close()

    def drain_captions(self, worker):
        for _ in range(256):
            try:
                event = worker.finals.get_nowait()
            except Empty:
                break
            self.history.append(event)
            self.transcript.appendPlainText(self.format_entry(event))

    def format_entry(self, event):
        if event is None:
            return '— New session · English —' if self.view.currentData() == 'english' else '— New session · Polish → English —'
        text = f'[{timestamp(event.start_ms)} → {timestamp(event.end_ms)}] Final\n'
        if self.view.currentData() == 'bilingual':
            text += f'PL: {event.polish}\n'
        text += f'EN: {event.english or "[translation unavailable]"}\n'
        if self.show_timing.isChecked() and event.arrival_ms is not None:
            text += f'Arrival: {timestamp(event.arrival_ms)} ({event.timing_source})'
            if event.estimated_final_delay_ms is not None:
                text += f'; estimated final delay: {event.estimated_final_delay_ms:+d} ms (not benchmark latency)'
            text += '\n'
        return text

    def render_provisional(self, event):
        if event is None:
            self.provisional.setText('Provisional: —')
            return
        text = 'Provisional · '
        if self.view.currentData() == 'bilingual':
            text += f'PL: {event.polish}\n'
        text += f'EN: {event.english or "[translation unavailable]"}'
        if self.show_timing.isChecked() and event.arrival_ms is not None:
            text += f'\nArrival: {timestamp(event.arrival_ms)} ({event.timing_source})'
        self.provisional.setText(text)

    def change_view(self):
        scroll = self.transcript.verticalScrollBar()
        at_end = scroll.value() == scroll.maximum()
        position = scroll.value()
        self.transcript.setPlainText('\n'.join(self.format_entry(event) for event in self.history))
        scroll.setValue(scroll.maximum() if at_end else min(position, scroll.maximum()))
        event = None
        if self.worker:
            with self.worker.lock:
                event = self.worker.provisional
        self.render_provisional(event)
        self.render_summary()

    def render_summary(self):
        summary = self.last_summary
        if summary is None:
            return
        text = (f"Session summary: {summary['final_captions']} final captions received; "
                f"{summary['translated_final_captions']} with English. Counts do not guarantee successful persistence.")
        if self.show_timing.isChecked():
            text += (f"\n{summary['provider_callback_captions']} SDK callback-timed; "
                     f"{summary['handler_only_captions']} handler-only. Delay is estimated, not benchmark latency.")
            for key, label in (('estimated_final_delay', 'Estimated final-caption delay'),
                               ('dispatch_delay', 'Callback to session handler'),
                               ('provisional_to_final', 'First provisional to final')):
                stats = summary[key]
                text += f'\n{label}: '
                text += ('no samples.' if not stats['count'] else
                    f"n={stats['count']}, median={stats['median_ms']:g} ms, p95={stats['p95_ms']:g} ms, max={stats['max_ms']:g} ms.")
            if summary['negative_estimates']:
                text += f"\nWarning: {summary['negative_estimates']} negative estimates retained; source alignment needs review."
        self.summary_label.setText(text)

    def closeEvent(self, event):
        if self.worker or self.discovery:
            self.closing = True
            self.stop_session()
            self.setEnabled(False)
            event.ignore()  # Never destroy/terminate a running native worker.
        else:
            event.accept()


def launch():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
