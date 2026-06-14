import os
from PySide6.QtWidgets import QLabel, QFileDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

COVER_WIDTH = 150
COVER_HEIGHT = 200


class CoverWidget(QLabel):
    cover_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(COVER_WIDTH, COVER_HEIGHT)
        self.setStyleSheet(
            "QLabel { border: 2px dashed #888; border-radius: 6px; background: #2a2a2a; }"
        )
        self.setText("Click to select\ncover image")
        self.setToolTip("Click to select a cover image")
        self.setScaledContents(False)
        self._path = ""

    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self.set_cover(path)

    def set_cover(self, path):
        if not path or not os.path.exists(path):
            return
        self._path = path
        pixmap = QPixmap(path)
        scaled = pixmap.scaled(
            COVER_WIDTH, COVER_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
        self.cover_changed.emit(path)

    def get_path(self):
        return self._path

    def clear_cover(self):
        self._path = ""
        self.clear()
        self.setText("Click to select\ncover image")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._path and os.path.exists(self._path):
            pixmap = QPixmap(self._path)
            scaled = pixmap.scaled(
                COVER_WIDTH, COVER_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled)
