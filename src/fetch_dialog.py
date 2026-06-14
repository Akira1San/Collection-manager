import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QProgressBar, QMessageBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, QThread, Signal

from src import config_handler
from src import metadata_fetcher


class FetchWorker(QThread):
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, source, title, api_keys, year=""):
        super().__init__()
        self._source = source
        self._title = title
        self._year = year
        self._api_keys = api_keys
        self._cancelled = False

    def run(self):
        try:
            self.progress.emit(10)
            if self._cancelled:
                return
            if self._source == "IMDb":
                result = metadata_fetcher.fetch_omdb(self._title, self._api_keys.get("omdb", ""), self._year)
            elif self._source == "OMDb":
                result = metadata_fetcher.fetch_omdb(self._title, self._api_keys.get("omdb", ""), self._year)
            elif self._source == "Wikipedia":
                result = metadata_fetcher.fetch_wikipedia(self._title, self._year)
            elif self._source == "TMDB":
                result = metadata_fetcher.fetch_tmdb(self._title, self._api_keys.get("tmdb", ""), self._year)
            else:
                self.error.emit("Unknown source.")
                return
            self.progress.emit(100)
            if not self._cancelled:
                self.finished.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True


class BatchWorker(QThread):
    progress = Signal(int)
    item_finished = Signal(int, int, object)
    item_error = Signal(int, int, str)
    finished = Signal(list)

    def __init__(self, items, source, api_keys):
        super().__init__()
        self._items = items
        self._source = source
        self._api_keys = api_keys
        self._cancelled = False
        self._results = []

    def run(self):
        total = len(self._items)
        for i, (vpath, title, year) in enumerate(self._items):
            if self._cancelled:
                break
            self.progress.emit(0)
            try:
                if self._source in ("IMDb", "OMDb"):
                    result = metadata_fetcher.fetch_omdb(title, self._api_keys.get("omdb", ""), year)
                elif self._source == "Wikipedia":
                    result = metadata_fetcher.fetch_wikipedia(title, year)
                elif self._source == "TMDB":
                    result = metadata_fetcher.fetch_tmdb(title, self._api_keys.get("tmdb", ""), year)
                else:
                    result = None
                self._results.append((vpath, result))
                self.item_finished.emit(i + 1, total, result)
            except Exception as e:
                if not self._cancelled:
                    self._results.append((vpath, None))
                    self.item_error.emit(i + 1, total, str(e))
            self.progress.emit(100)
        self.finished.emit(self._results)

    def cancel(self):
        self._cancelled = True


class FetchDialog(QDialog):
    def __init__(self, parent=None, collection_name="", items=None):
        super().__init__(parent)
        self.setWindowTitle("Fetch Metadata")
        self.setMinimumWidth(600)
        self._result = None
        self._results = []

        if items is not None and len(items) > 1:
            self._items = items
            self._batch_mode = True
        else:
            self._batch_mode = False
            if items:
                self._items = items
                collection_name = items[0][1]
                collection_year = items[0][2] if len(items[0]) > 2 else ""
            else:
                self._items = [(None, collection_name, "")]

        layout = QVBoxLayout(self)

        form = QFormLayout()
        if self._batch_mode:
            self.items_table = QTableWidget(len(self._items), 3)
            self.items_table.setHorizontalHeaderLabels(["Video File", "Title", "Year"])
            self.items_table.horizontalHeader().setStretchLastSection(False)
            self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
            self.items_table.setColumnWidth(2, 80)
            self.items_table.setSelectionMode(QAbstractItemView.NoSelection)
            self.items_table.setMinimumHeight(150)
            self.items_table.verticalHeader().setVisible(False)
            for row, item in enumerate(self._items):
                vpath = item[0]
                title = item[1]
                year = item[2] if len(item) > 2 else ""
                video_item = QTableWidgetItem(os.path.basename(vpath))
                video_item.setFlags(video_item.flags() & ~Qt.ItemIsEditable)
                self.items_table.setItem(row, 0, video_item)
                title_item = QTableWidgetItem(title)
                self.items_table.setItem(row, 1, title_item)
                year_item = QTableWidgetItem(year)
                self.items_table.setItem(row, 2, year_item)
            form.addRow("Videos:", self.items_table)
        else:
            self.title_edit = QLineEdit(collection_name)
            self.title_edit.setPlaceholderText("Movie title...")
            form.addRow("Title:", self.title_edit)
            self.year_edit = QLineEdit(collection_year)
            self.year_edit.setPlaceholderText("Year (optional)...")
            form.addRow("Year:", self.year_edit)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["IMDb", "OMDb", "Wikipedia", "TMDB"])
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        form.addRow("Source:", self.source_combo)

        self.api_key_label = QLabel("API Key:")
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("API key for this source...")
        form.addRow(self.api_key_label, self.api_key_edit)

        layout.addLayout(form)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.fetch_btn = QPushButton("Fetch All" if self._batch_mode else "Fetch")
        self.fetch_btn.setToolTip("Start fetching metadata from the selected source")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setToolTip("Cancel the ongoing metadata fetch")
        self.cancel_btn.setVisible(False)
        btn_layout.addWidget(self.fetch_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.fetch_btn.clicked.connect(self._start_fetch)
        self.cancel_btn.clicked.connect(self._cancel_fetch)

        self._worker = None
        self._on_source_changed(self.source_combo.currentText())

    def _on_source_changed(self, source):
        key = config_handler.get_api_key(source.lower())
        self.api_key_edit.setText(key)
        visible = source in ("OMDb", "TMDB")
        self.api_key_label.setVisible(visible)
        self.api_key_edit.setVisible(visible)

    def _start_fetch(self):
        source = self.source_combo.currentText()
        api_key = self.api_key_edit.text().strip()

        if source in ("OMDb", "TMDB") and not api_key:
            QMessageBox.warning(self, "Warning", f"API key required for {source}.")
            return

        if api_key:
            config_handler.set_api_key(source.lower(), api_key)

        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)

        api_keys = {
            "omdb": config_handler.get_api_key("omdb"),
            "tmdb": config_handler.get_api_key("tmdb"),
        }

        if self._batch_mode:
            updated_items = []
            for row in range(self.items_table.rowCount()):
                vpath = self._items[row][0]
                title = self.items_table.item(row, 1).text().strip()
                year = self.items_table.item(row, 2).text().strip()
                if not title:
                    QMessageBox.warning(
                        self, "Warning",
                        f"Row {row + 1}: title cannot be empty."
                    )
                    self._reset_ui()
                    return
                updated_items.append((vpath, title, year))
            self._items = updated_items
            self.status_label.setText(f"Fetching 1/{len(self._items)}...")
            self._worker = BatchWorker(self._items, source, api_keys)
            self._worker.progress.connect(self.progress_bar.setValue)
            self._worker.item_finished.connect(self._on_item_finished)
            self._worker.item_error.connect(self._on_item_error)
            self._worker.finished.connect(self._on_batch_finished)
            self._worker.start()
        else:
            title = self.title_edit.text().strip()
            year = self.year_edit.text().strip()
            if not title:
                QMessageBox.warning(self, "Warning", "Enter a title.")
                return
            self.status_label.setText("Fetching...")
            self._worker = FetchWorker(source, title, api_keys, year)
            self._worker.progress.connect(self.progress_bar.setValue)
            self._worker.finished.connect(self._on_finished)
            self._worker.error.connect(self._on_error)
            self._worker.start()

    def _cancel_fetch(self):
        if self._worker:
            self._worker.cancel()
            self._worker.quit()
            self._worker.wait()
        if not self._batch_mode:
            self._reset_ui()

    def _on_finished(self, result):
        self._result = result
        self._reset_ui()
        self.accept()

    def _on_error(self, msg):
        QMessageBox.warning(self, "Error", msg)
        self._reset_ui()

    def _on_item_finished(self, index, total, result):
        self.status_label.setText(f"Fetched {index}/{total}")

    def _on_item_error(self, index, total, msg):
        self.status_label.setText(f"Error {index}/{total}: {msg}")

    def _on_batch_finished(self, results):
        self._results = results
        self._reset_ui()
        successes = []
        failures = []
        for (vpath, title, year), (_, result) in zip(self._items, results):
            if result:
                successes.append(title)
            else:
                failures.append(title)
        if failures:
            msg = f"Fetched {len(successes)}/{len(results)} video(s)."
            msg += "\n\nNot found:\n" + "\n".join(f"  • {t}" for t in failures)
            QMessageBox.information(self, "Fetch Results", msg)
        self.accept()

    def _reset_ui(self):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self._worker = None

    def get_result(self):
        return self._result

    def get_results(self):
        if self._results:
            return self._results
        if self._result is not None and self._items:
            return [(self._items[0][0], self._result)]
        return []
