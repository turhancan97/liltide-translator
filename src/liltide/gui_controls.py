"""Styled selectors with consistent popup metrics across native Qt styles."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QListView, QStyledItemDelegate


class Dropdown(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        view = QListView(self)
        view.setTextElideMode(Qt.TextElideMode.ElideNone)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setUniformItemSizes(True)
        self.setView(view)
        # Native combo-menu delegates can reserve a checkmark gutter without
        # including it in the styled popup width. Use ordinary list metrics.
        self.setItemDelegate(QStyledItemDelegate(view))

    def showPopup(self):
        self.view().setFont(self.font())
        width = max((self.fontMetrics().horizontalAdvance(self.itemText(i))
                     for i in range(self.count())), default=0) + 40
        available = self.screen().availableGeometry().width() - 32
        self.view().setMinimumWidth(min(max(self.width(), width), max(100, available)))
        super().showPopup()
