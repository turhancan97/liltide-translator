"""Stage-one desktop PoC: Qt stays on the main thread; sessions run off-thread."""

from queue import Empty, Full, Queue
from threading import Event, Lock
import sys

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel,
                              QMainWindow, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from liltide.audio import AudioError, SoundCardBackend
from liltide.formatting import timestamp
from liltide.provider import AzureProvider, CloudConfig
from liltide.session import TranslationSession
from liltide.sources import LiveSource


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
                 source_factory=LiveSource, provider_factory=AzureProvider):
        super().__init__()
        self.device, self.source, self.config = device, source, config
        self.backend_factory, self.source_factory, self.provider_factory = backend_factory, source_factory, provider_factory
        self.stop_requested = Event()
        self.finals = Queue(maxsize=256)
        self.lock = Lock()
        self.provisional = None
        self.status = 'Connecting…'
        self.error = None

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
        with self.lock:
            self.status = message
            self.provisional = None

    def run(self):
        try:
            if self.stop_requested.is_set():
                return
            self.backend_factory().select(self.device, self.source)
            session = TranslationSession(
                lambda: self.source_factory(self.device, self.source, 48000),
                lambda: self.provider_factory(self.config), self.caption, self.set_status,
                should_stop=self.stop_requested.is_set)
            session.run()
        except AudioError as exc:
            self.error = str(exc)
        except Exception:
            # Never expose raw native exceptions or credentials in the window/log.
            self.error = 'Session failed unexpectedly. Check local setup before starting a new session.'
        finally:
            self.config = None  # Release the worker's reference to credentials after cleanup.
            with self.lock:
                self.provisional = None


class MainWindow(QMainWindow):
    def __init__(self, *, discovery_factory=DiscoveryWorker, worker_factory=SessionWorker):
        super().__init__()
        self.discovery_factory, self.worker_factory = discovery_factory, worker_factory
        self.discovery = self.worker = None
        self.closing = False
        self.available_devices = []
        self.setWindowTitle('Liltide — Live captions across languages')
        self.resize(860, 640)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        title = QLabel('Liltide · Polish → English')
        title.setStyleSheet('font-size: 22px; font-weight: 600;')
        layout.addWidget(title)
        notice = QLabel('Selected audio is sent to Azure when you start. No audio recording or transcript files are saved.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.source = QComboBox()
        self.source.addItem('System audio', 'system')
        self.source.addItem('Microphone', 'microphone')
        self.source.setAccessibleName('Audio source type')
        self.device = QComboBox()
        self.device.setAccessibleName('Capture device')
        self.refresh = QPushButton('Refresh devices')
        self.refresh.clicked.connect(self.refresh_devices)
        row = QHBoxLayout()
        for widget in (self.source, self.device, self.refresh):
            row.addWidget(widget)
        layout.addLayout(row)
        routing = QLabel('macOS: choose your routed virtual input for system audio; keep playback audible through your multi-output device.')
        routing.setWordWrap(True)
        layout.addWidget(routing)
        self.confirm = QCheckBox('I verified this Azure resource uses the free F0 tier (no automatic paid fallback).')
        layout.addWidget(self.confirm)
        self.start = QPushButton('Start translation')
        self.stop = QPushButton('Stop')
        self.stop.setEnabled(False)
        self.start.clicked.connect(self.start_session)
        self.stop.clicked.connect(self.stop_session)
        buttons = QHBoxLayout()
        buttons.addWidget(self.start)
        buttons.addWidget(self.stop)
        layout.addLayout(buttons)
        self.status = QLabel('Ready. Refresh devices to select an input. Credentials are read from your environment on Start.')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        self.status.setAccessibleName('Session status')
        layout.addWidget(self.status)
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setAccessibleName('Finalized Polish and English captions')
        self.transcript.setPlaceholderText('Finalized bilingual captions appear here. Prior runs remain visible until you close this window.')
        layout.addWidget(self.transcript)
        self.provisional = QLabel('Provisional: —')
        self.provisional.setTextFormat(Qt.TextFormat.PlainText)
        self.provisional.setWordWrap(True)
        layout.addWidget(self.provisional)
        self.source.currentIndexChanged.connect(self.populate_devices)
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def refresh_devices(self):
        if self.worker or self.discovery:
            return
        self.discovery = self.discovery_factory()
        self.refresh.setEnabled(False)
        self.start.setEnabled(False)
        self.status.setText('Listing devices… No audio is captured.')
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
            worker = self.worker_factory(device, self.source.currentData(), config)
        except AudioError as exc:
            self.status.setText('Error: ' + str(exc).replace('then pass --confirm-f0', 'then check the F0 confirmation'))
            return
        self.worker = worker
        self.transcript.appendPlainText('— New session · Polish → English —')
        self.set_running(True)
        self.status.setText('Connecting…')
        worker.start()

    def set_running(self, running):
        for widget in (self.start, self.source, self.device, self.refresh, self.confirm):
            widget.setEnabled(not running)
        self.stop.setEnabled(running)

    def stop_session(self):
        if self.worker:
            self.worker.stop_requested.set()
            self.stop.setEnabled(False)
            self.status.setText('Stopping… Waiting for capture/cloud cleanup and finalized captions.')

    def poll(self):
        if self.discovery and self.discovery.isFinished():
            discovery, self.discovery = self.discovery, None
            discovery.wait()
            self.available_devices = discovery.devices
            self.populate_devices()
            self.status.setText(discovery.error or f'{len(self.available_devices)} input(s) found. Select a device before starting.')
            self.refresh.setEnabled(True)
            self.start.setEnabled(True)
            discovery.deleteLater()
        if self.worker:
            worker = self.worker
            self.drain_captions(worker)
            with worker.lock:
                provisional, status = worker.provisional, worker.status
            self.provisional.setText('Provisional: —' if provisional is None else
                f'Provisional · PL: {provisional.polish}\nEN: {provisional.english or "[translation unavailable]"}')
            if not worker.stop_requested.is_set():
                self.status.setText(status)
            if worker.isFinished():
                worker.wait()
                self.drain_captions(worker)  # Include finals queued between the first drain and thread exit.
                self.status.setText('Error: ' + worker.error if worker.error else 'Stopped. Capture and cloud resources released.')
                self.provisional.setText('Provisional: —')
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
            self.transcript.appendPlainText(
                f'[{timestamp(event.start_ms)} → {timestamp(event.end_ms)}] Final\n'
                f'PL: {event.polish}\nEN: {event.english or "[translation unavailable]"}\n')

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
