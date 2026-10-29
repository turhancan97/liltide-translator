"""Window-local brand themes; never override the OS appearance setting."""
from importlib.resources import files

from PySide6.QtGui import QColor, QPalette

BLUE = '#3a7eab'
RED = '#cf4832'
GRAY = '#d1d3d4'
INK = '#17212b'
WHITE = '#ffffff'


def colors(mode):
    return {'background': INK if mode == 'dark' else WHITE,
            'text': WHITE if mode == 'dark' else INK,
            'muted': GRAY if mode == 'dark' else INK,
            'border': GRAY if mode == 'dark' else INK,
            'selected': GRAY, 'selected_text': INK}


def palette(mode):
    c = colors(mode)
    result = QPalette()
    for role, value in ((QPalette.ColorRole.Window, c['background']),
                        (QPalette.ColorRole.Base, c['background']),
                        (QPalette.ColorRole.Button, c['background']),
                        (QPalette.ColorRole.WindowText, c['text']),
                        (QPalette.ColorRole.Text, c['text']),
                        (QPalette.ColorRole.ButtonText, c['text']),
                        (QPalette.ColorRole.PlaceholderText, c['muted']),
                        (QPalette.ColorRole.Highlight, GRAY),
                        (QPalette.ColorRole.HighlightedText, INK),
                        (QPalette.ColorRole.ToolTipBase, c['background']),
                        (QPalette.ColorRole.ToolTipText, c['text'])):
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
            result.setColor(group, role, QColor(value))
    return result


def stylesheet(mode):
    c = colors(mode)
    check = str(files("liltide").joinpath("resources/check.svg")).replace("\\", "/").replace('"', '\\"')
    return f'''
    QWidget {{ background-color: {c['background']}; color: {c['text']}; }}
    QGroupBox {{ border: 1px solid {c['border']}; border-radius: 8px;
                 margin-top: 14px; padding: 16px 12px 12px 12px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 5px; }}
    QLabel#brandTitle {{ font-size: 30px; font-weight: 700; }}
    QLabel#tagline {{ color: {c['muted']}; }}
    QLabel#state {{ border-left: 4px solid {BLUE}; padding: 8px 10px; font-weight: 600; }}
    QLabel#provisional {{ border-left: 4px solid {RED}; padding: 8px 10px; }}
    QPlainTextEdit, QLineEdit, QComboBox, QSpinBox {{ border: 1px solid {c['border']};
        border-radius: 5px; padding: 7px; placeholder-text-color: {c['muted']}; selection-background-color: {GRAY}; selection-color: {INK}; }}
    QComboBox QAbstractItemView {{ background-color: {c['background']}; color: {c['text']};
        selection-background-color: {GRAY}; selection-color: {INK}; }}
    QComboBox QAbstractItemView::item {{ min-height: 24px; padding: 6px 10px; }}
    QPushButton {{ border: 1px solid {c['border']}; border-radius: 5px; padding: 8px 12px; }}
    QPushButton#start {{ border: 2px solid {BLUE}; font-weight: 600; }}
    QPushButton#stop {{ border: 2px solid {RED}; }}
    QPushButton:hover {{ background-color: {GRAY}; color: {INK}; }}
    QPushButton:pressed {{ background-color: {GRAY}; color: {INK}; }}
    QPushButton:disabled, QLineEdit:disabled {{ border-style: dashed; color: {c['muted']}; }}
    QPushButton:focus, QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
        border: 2px solid {RED}; }}
    QCheckBox {{ spacing: 8px; padding: 3px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {c['border']}; border-radius: 3px; background-color: {c['background']}; }}
    QCheckBox::indicator:checked {{ image: url("{check}"); background-color: {GRAY}; border: 1px solid {INK}; }}
    QCheckBox:focus {{ border: 2px solid {RED}; border-radius: 4px; }}
    QPushButton#start:disabled, QPushButton#stop:disabled {{ border: 1px dashed {c['border']}; }}
    QPlainTextEdit {{ padding: 12px; }}
    QSplitter::handle {{ background-color: {GRAY}; width: 5px; }}
    QScrollArea {{ border: none; }}
    '''
