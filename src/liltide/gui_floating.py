"""Optional floating view of the existing session; never owns processing."""
import sys
from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit

from liltide.gui_controls import Dropdown
from liltide.formatting import timestamp


class FloatingCaptions(QWidget):
    hidden = Signal()
    view_changed = Signal(str)
    size_changed = Signal(int)

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowTitle('Liltide — Floating captions')
        self.resize(720, 380)
        self.setMinimumSize(480, 280)
        self.latest_final = self.provisional = None
        self.fullscreen_ready = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        row = QHBoxLayout()
        self.view = Dropdown()
        self.view.addItem('Polish + English', 'bilingual')
        self.view.addItem('English only', 'english')
        self.view.setAccessibleName('Floating caption language view')
        label = QLabel('&View')
        label.setBuddy(self.view)
        row.addWidget(label)
        row.addWidget(self.view, 1)
        self.caption_size = Dropdown()
        for size in (12, 14, 16, 18, 22, 26):
            self.caption_size.addItem(f'{size} pt', size)
        self.caption_size.setMinimumWidth(100)
        self.caption_size.setAccessibleName('Floating caption font size')
        size_label = QLabel('Caption si&ze')
        size_label.setBuddy(self.caption_size)
        row.addWidget(size_label)
        row.addWidget(self.caption_size)
        layout.addLayout(row)
        self.state = QLabel('State: Ready')
        self.state.setObjectName('state')
        self.state.setTextFormat(Qt.TextFormat.PlainText)
        self.state.setAccessibleName('Floating session state')
        layout.addWidget(self.state)
        self.final_text = QPlainTextEdit()
        self.final_text.setReadOnly(True)
        self.final_text.setAccessibleName('Latest finalized floating caption')
        self.final_text.setPlaceholderText('Waiting for a finalized caption in the current session.')
        layout.addWidget(self.final_text, 1)
        self.provisional_text = QPlainTextEdit()
        self.provisional_text.setReadOnly(True)
        self.provisional_text.setAccessibleName('Provisional floating caption')
        self.provisional_text.setMaximumHeight(110)
        self.provisional_text.setPlainText('Provisional: —')
        layout.addWidget(self.provisional_text)
        self.footer = QLabel()
        self.footer.setWordWrap(True)
        layout.addWidget(self.footer)
        self.update_footer()
        self.view.currentIndexChanged.connect(self.emit_view)
        self.caption_size.currentIndexChanged.connect(self.emit_size)

    def update_footer(self):
        text = 'Same session as the main window. Closing this view keeps translation running.'
        if self.fullscreen_ready is False:
            text += ' Fullscreen visibility could not be enabled on this Mac.'
        self.footer.setText(text)

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == 'darwin' and QApplication.platformName() == 'cocoa':
            try:
                from liltide.macos_window import enable_fullscreen_panel
                self.fullscreen_ready = enable_fullscreen_panel(int(self.winId()))
            except Exception:
                # Preserve ordinary floating captions; do not expose native
                # pointers/errors or alter global application/window policy.
                self.fullscreen_ready = False
            self.update_footer()

    def emit_view(self):
        self.view_changed.emit(self.view.currentData())

    def emit_size(self):
        self.size_changed.emit(self.caption_size.currentData())

    def configure(self, view, size, font):
        with QSignalBlocker(self.view), QSignalBlocker(self.caption_size):
            self.view.setCurrentIndex(self.view.findData(view))
            self.caption_size.setCurrentIndex(self.caption_size.findData(size))
        self.final_text.setFont(font)
        self.provisional_text.setFont(font)
        self.render()

    def reset_session(self):
        self.latest_final = self.provisional = None
        self.render()

    def finalized(self, event):
        self.latest_final = event
        self.render()

    def update_session(self, state, provisional):
        self.state.setText(state)
        if provisional != self.provisional:
            self.provisional = provisional
            self.render()

    def caption_text(self, event):
        text = ''
        if self.view.currentData() == 'bilingual':
            text += f'PL: {event.polish}\n'
        return text + f'EN: {event.english or "[translation unavailable]"}'

    def render(self):
        event = self.latest_final
        self.final_text.setPlainText('' if event is None else
            f'Finalized [{timestamp(event.start_ms)} → {timestamp(event.end_ms)}]\n{self.caption_text(event)}')
        event = self.provisional
        self.provisional_text.setPlainText('Provisional: —' if event is None else
            f'Provisional\n{self.caption_text(event)}')

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.hidden.emit()
