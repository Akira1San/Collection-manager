import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush


SORT_NAME = 0
SORT_DATE_NEWEST = 1
SORT_DATE_OLDEST = 2


class CollectionPanel(QWidget):
    add_requested = Signal(list)
    video_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paths = []
        self._sort_mode = SORT_NAME
        self._name_filter = ""
        self._folder_filter = ""
        layout = QVBoxLayout(self)

        title = QLabel("Available Videos")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name...")
        self.search_edit.setClearButtonEnabled(True)
        layout.addWidget(self.search_edit)

        top_row = QHBoxLayout()
        self.count_label = QLabel("0 videos")
        self.count_label.setStyleSheet("color: #888; font-size: 11px;")
        top_row.addWidget(self.count_label)
        top_row.addStretch()
        self.folder_combo = QComboBox()
        self.folder_combo.addItem("All Folders", "")
        self.folder_combo.setToolTip("Filter by folder")
        self.folder_combo.setMinimumWidth(120)
        top_row.addWidget(self.folder_combo)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name (A-Z)", "Date (newest)", "Date (oldest)"])
        self.sort_combo.setToolTip("Sort order")
        top_row.addWidget(self.sort_combo)
        layout.addLayout(top_row)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add >>")
        self.add_btn.setToolTip("Add selected videos to the collection")
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setToolTip("Remove selected videos from the list")
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setToolTip("Toggle select all / deselect all")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.select_all_btn)
        layout.addLayout(btn_layout)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.list_widget)

        self.add_btn.clicked.connect(self._on_add)
        self.remove_btn.clicked.connect(self._on_remove)
        self.select_all_btn.clicked.connect(self._toggle_select_all)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.folder_combo.currentIndexChanged.connect(self._on_folder_changed)
        self.search_edit.textChanged.connect(self._on_search_changed)

    def _on_add(self):
        paths = self.get_selected_paths()
        if paths:
            self.add_requested.emit(paths)

    def _on_remove(self):
        items = self.list_widget.selectedItems()
        removed = {item.data(Qt.UserRole) for item in items}
        for item in items:
            self.list_widget.takeItem(self.list_widget.row(item))
        self._paths = [p for p in self._paths if p not in removed]
        self._update_count()

    def _on_item_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.video_clicked.emit(path)

    def _toggle_select_all(self):
        all_selected = len(self.list_widget.selectedItems()) == self.list_widget.count()
        if all_selected:
            self.list_widget.clearSelection()
        else:
            self.list_widget.selectAll()

    def _update_count(self):
        count = self.list_widget.count()
        self.count_label.setText(f"{count} video{'s' if count != 1 else ''}")

    def set_videos(self, paths):
        self._paths = list(paths)
        self._rebuild_folder_combo()
        self._populate()

    def _on_sort_changed(self, index):
        self._sort_mode = index
        self._populate()

    def _on_folder_changed(self, index):
        self._folder_filter = self.folder_combo.itemData(index) or ""
        self._populate()

    def _on_search_changed(self, text):
        self._name_filter = text.strip().lower()
        self._populate()

    def _rebuild_folder_combo(self):
        current = self.folder_combo.currentData() or ""
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItem("All Folders", "")
        dirs = sorted(set(os.path.dirname(p) for p in self._paths))
        for d in dirs:
            label = os.path.basename(d) if d else d
            self.folder_combo.addItem(label, d)
        idx = self.folder_combo.findData(current)
        if idx >= 0:
            self.folder_combo.setCurrentIndex(idx)
        self.folder_combo.blockSignals(False)

    def _sort_key(self, p):
        if self._sort_mode == SORT_NAME:
            return (os.path.basename(p).lower(), p)
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            mtime = 0
        if self._sort_mode == SORT_DATE_NEWEST:
            return (-mtime, os.path.basename(p).lower())
        return (mtime, os.path.basename(p).lower())

    def _visible_paths(self):
        paths = self._paths
        if self._folder_filter:
            paths = [p for p in paths if p.startswith(self._folder_filter)]
        if self._name_filter:
            paths = [p for p in paths if self._name_filter in os.path.basename(p).lower()]
        return paths

    def _populate(self):
        self.list_widget.clear()
        sorted_paths = sorted(self._visible_paths(), key=self._sort_key)
        for p in sorted_paths:
            item = QListWidgetItem(os.path.basename(p))
            item.setData(Qt.UserRole, p)
            item.setToolTip(p)
            if not os.path.exists(p):
                item.setForeground(Qt.red)
            self.list_widget.addItem(item)
        self._update_count()

    def add_videos(self, paths, mark_new=False):
        existing = set(self._paths)
        added = []
        for p in paths:
            if p not in existing:
                added.append(p)
                existing.add(p)
        self._paths.extend(added)
        self._rebuild_folder_combo()
        self._populate()

    def get_selected_paths(self):
        return [item.data(Qt.UserRole) for item in self.list_widget.selectedItems()]

    def get_all_paths(self):
        return [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]

    def replace_path(self, old_path, new_path):
        for i, p in enumerate(self._paths):
            if p == old_path:
                self._paths[i] = new_path
                break
        self._populate()

    def clear(self):
        self._paths.clear()
        self.list_widget.clear()
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItem("All Folders", "")
        self.folder_combo.blockSignals(False)
        self.search_edit.clear()
        self._name_filter = ""
        self._folder_filter = ""
        self._update_count()

    def rename_item(self, path, new_text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == path:
                item.setText(new_text)
                return
