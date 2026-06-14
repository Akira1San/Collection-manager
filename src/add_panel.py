import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush


class AddPanel(QWidget):
    save_requested = Signal()
    save_as_requested = Signal()
    remove_requested = Signal()
    remove_all_requested = Signal()
    video_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Added Videos")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        self.count_label = QLabel("0 videos")
        self.count_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.count_label)

        btn_layout = QHBoxLayout()
        self.remove_btn = QPushButton("<< Remove")
        self.remove_btn.setToolTip("Remove selected videos from the added list")
        self.remove_all_btn = QPushButton("Remove All")
        self.remove_all_btn.setToolTip("Remove all videos from the added list")
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.remove_all_btn)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        save_btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save the current collection to the loaded file")
        self.save_as_btn = QPushButton("Save As")
        self.save_as_btn.setToolTip("Save the collection to a new JSON file")
        save_btn_layout.addWidget(self.save_btn)
        save_btn_layout.addWidget(self.save_as_btn)

        layout.addLayout(btn_layout)
        layout.addWidget(self.list_widget)
        layout.addLayout(save_btn_layout)

        self.remove_btn.clicked.connect(self.remove_requested)
        self.remove_all_btn.clicked.connect(self.remove_all_requested)
        self.save_btn.clicked.connect(self.save_requested)
        self.save_as_btn.clicked.connect(self.save_as_requested)

    def _on_item_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.video_clicked.emit(path)

    def _update_count(self):
        count = self.list_widget.count()
        self.count_label.setText(f"{count} video{'s' if count != 1 else ''}")

    def add_videos(self, paths):
        existing = set()
        for i in range(self.list_widget.count()):
            existing.add(self.list_widget.item(i).data(Qt.UserRole))

        for p in paths:
            if p not in existing:
                item = QListWidgetItem(p.split("/")[-1] if "/" in p else p)
                item.setData(Qt.UserRole, p)
                item.setToolTip(p)
                if not os.path.exists(p):
                    item.setForeground(Qt.red)
                self.list_widget.addItem(item)
                existing.add(p)
        self._update_count()

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self._update_count()

    def get_selected_paths(self):
        return [item.data(Qt.UserRole) for item in self.list_widget.selectedItems()]

    def get_video_paths(self):
        return [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]

    def set_video_paths(self, paths):
        self.list_widget.clear()
        for p in paths:
            item = QListWidgetItem(p.split("/")[-1] if "/" in p else p)
            item.setData(Qt.UserRole, p)
            item.setToolTip(p)
            if not os.path.exists(p):
                item.setForeground(Qt.red)
            self.list_widget.addItem(item)
        self._update_count()

    def get_all_paths(self):
        return [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]

    def replace_path(self, old_path, new_path):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == old_path:
                item.setData(Qt.UserRole, new_path)
                item.setText(new_path.split("/")[-1] if "/" in new_path else new_path)
                item.setToolTip(new_path)
                if os.path.exists(new_path):
                    item.setForeground(QBrush())
                else:
                    item.setForeground(Qt.red)
                return

    def clear(self):
        self.list_widget.clear()
        self._update_count()

    def rename_item(self, path, new_text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                item.setText(new_text)
                return
