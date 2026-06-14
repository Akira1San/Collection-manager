from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog
)
from PySide6.QtCore import Signal


class TagWidget(QWidget):
    tags_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        input_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter a tag...")
        self.add_btn = QPushButton("Add Tag")
        self.add_btn.setToolTip("Add the entered tag to the list")
        input_layout.addWidget(self.input)
        input_layout.addWidget(self.add_btn)

        self.list_widget = QListWidget()
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.setToolTip("Edit the selected tag name")
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.setToolTip("Remove the selected tag from the list")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.remove_btn)

        layout.addLayout(input_layout)
        layout.addWidget(self.list_widget)
        layout.addLayout(button_layout)

        self.add_btn.clicked.connect(self.add_tag)
        self.edit_btn.clicked.connect(self.edit_tag)
        self.remove_btn.clicked.connect(self.remove_tag)
        self.input.returnPressed.connect(self.add_tag)

    def add_tag(self):
        self.add_tag_text(self.input.text())
        self.input.clear()

    def add_tag_text(self, text):
        text = text.strip()
        if text and not self._tag_exists(text):
            item = QListWidgetItem(text)
            self.list_widget.addItem(item)
            self._emit_tags()

    def remove_tag(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)
            self._emit_tags()

    def edit_tag(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        item = self.list_widget.item(row)
        old_text = item.text()
        new_text, ok = QInputDialog.getText(
            self, "Edit Tag", "New name:", text=old_text
        )
        if ok and new_text:
            new_text = new_text.strip()
            if new_text != old_text and not self._tag_exists(new_text):
                item.setText(new_text)
                self._emit_tags()

    def _tag_exists(self, text):
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).text() == text:
                return True
        return False

    def get_tags(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

    def set_tags(self, tags):
        self.list_widget.clear()
        for t in tags:
            self.list_widget.addItem(t)

    def _emit_tags(self):
        self.tags_changed.emit(self.get_tags())
