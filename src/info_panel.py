from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QSpinBox, QPushButton, QLabel,
)
from PySide6.QtCore import Qt, Signal
from src.cover_widget import CoverWidget


class InfoPanel(QWidget):
    info_changed = Signal()
    resolve_cover_requested = Signal()
    resolve_all_covers_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Collection Info")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        self.cover = CoverWidget()
        layout.addWidget(self.cover, alignment=Qt.AlignCenter)

        form = QFormLayout()

        self.id_label = QLabel("")
        self.id_label.setStyleSheet("color: #888;")
        form.addRow("ID:", self.id_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Collection name")
        self.name_edit.textChanged.connect(self._on_change)
        form.addRow("Name:", self.name_edit)

        self.name_bg_edit = QLineEdit()
        self.name_bg_edit.setPlaceholderText("Bulgarian name (auto-filled from Wikipedia)")
        self.name_bg_edit.setToolTip("Bulgarian translation of the title. Auto-filled from Wikipedia when fetching metadata, or editable manually.")
        self.name_bg_edit.textChanged.connect(self._on_change)
        form.addRow("Name (BG):", self.name_bg_edit)

        cover_path_layout = QHBoxLayout()
        self.cover_path_edit = QLineEdit()
        self.cover_path_edit.setPlaceholderText("Cover image path")
        self.cover_path_edit.setReadOnly(True)
        self.cover_path_edit.textChanged.connect(self._on_change)
        self.cover_resolve_btn = QPushButton("Resolve")
        self.cover_resolve_btn.setToolTip("Search for this cover in the covers directory")
        self.cover_resolve_btn.clicked.connect(self.resolve_cover_requested.emit)
        self.cover_resolve_all_btn = QPushButton("Resolve All")
        self.cover_resolve_all_btn.setToolTip("Search for all missing covers in the covers directory")
        self.cover_resolve_all_btn.clicked.connect(self.resolve_all_covers_requested.emit)
        cover_path_layout.addWidget(self.cover_path_edit)
        cover_path_layout.addWidget(self.cover_resolve_btn)
        cover_path_layout.addWidget(self.cover_resolve_all_btn)
        form.addRow("Cover:", cover_path_layout)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Description...")
        self.desc_edit.setMaximumHeight(60)
        self.desc_edit.textChanged.connect(self._on_change)
        form.addRow("Description:", self.desc_edit)

        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("Comma-separated: Action, Sci-Fi")
        self.genre_edit.textChanged.connect(self._on_change)
        form.addRow("Genre:", self.genre_edit)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(0, 2100)
        self.year_spin.setSpecialValueText("None")
        self.year_spin.valueChanged.connect(self._on_change)
        form.addRow("Year:", self.year_spin)

        self.tags_label = QLabel("")
        self.tags_label.setWordWrap(True)
        self.tags_label.setStyleSheet("color: #aaa;")
        form.addRow("Tags:", self.tags_label)

        layout.addLayout(form)
        layout.addStretch()

    def _on_change(self):
        self.info_changed.emit()

    def get_data(self):
        return {
            "id": self.id_label.text(),
            "name": self.name_edit.text(),
            "name_bg": self.name_bg_edit.text(),
            "cover": self.cover_path_edit.text(),
            "description": self.desc_edit.toPlainText(),
            "genre": [g.strip() for g in self.genre_edit.text().split(",") if g.strip()],
            "year": self.year_spin.value(),
        }

    def set_data(self, data, tags=None):
        cover = data.get("cover", "")
        self.id_label.setText(data.get("id", ""))
        self.name_edit.setText(data.get("name", ""))
        self.name_bg_edit.setText(data.get("name_bg", ""))
        self.cover_path_edit.setText(cover)
        if cover:
            self.cover.set_cover(cover)
        else:
            self.cover.clear_cover()
        self.desc_edit.setPlainText(data.get("description", ""))
        self.genre_edit.setText(", ".join(data.get("genre", [])))
        self.year_spin.setValue(data.get("year", 0) or 0)
        if tags is not None:
            self.set_tags(tags)
        elif data.get("tags"):
            self.set_tags(data["tags"])

    def set_tags(self, tags):
        self.tags_label.setText(", ".join(tags) if tags else "(none)")

    def clear(self):
        self.id_label.setText("")
        self.name_edit.clear()
        self.name_bg_edit.clear()
        self.cover_path_edit.clear()
        self.cover.clear_cover()
        self.desc_edit.clear()
        self.genre_edit.clear()
        self.year_spin.setValue(0)
        self.tags_label.setText("")
