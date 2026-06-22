import os
import re
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QComboBox, QLineEdit, QPushButton, QFileDialog, QLabel,
    QMessageBox, QFrame, QDialog,
)
from PySide6.QtCore import Qt

from src.info_panel import InfoPanel
from src.collection_panel import CollectionPanel
from src.add_panel import AddPanel
from src.tags_panel import TagsPanel
from src.collection_model import Collection, make_id
from src.fetch_dialog import FetchDialog
from src import config_handler, json_handler, video_scanner, metadata_fetcher


def find_cover_in_dir(covers_dir, collection_name, stored_path):
    if not covers_dir or not os.path.isdir(covers_dir):
        return ""

    if stored_path and os.path.exists(stored_path):
        return stored_path

    candidates = []
    bn = os.path.basename(stored_path) if stored_path else ""
    if bn:
        candidates.append(os.path.join(covers_dir, bn))

    names = [collection_name, collection_name.replace(" ", "_")]
    names += [n.lower() for n in names]
    names = list(set(names))

    for n in names:
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            candidates.append(os.path.join(covers_dir, f"{n}{ext}"))

    for c in candidates:
        if os.path.exists(c):
            return os.path.normpath(c)

    for fname in os.listdir(covers_dir):
        stem, _ = os.path.splitext(fname)
        if stem.lower() in (n.lower() for n in names):
            return os.path.join(covers_dir, fname)

    return ""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Collection Manager")
        self.resize(1500, 800)

        self._current_file = None
        self._loaded_file = None
        self._collection = Collection()
        self._video_collection_map = {}
        self._loaded_collections = []
        self._collections_dir = ""

        self._setup_status_bar()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self._build_toolbar(main_layout)
        self._build_name_bar(main_layout)
        self._build_panels(main_layout)
        self._connect_signals()
        self._load_collections_dir()

    def _setup_status_bar(self):
        self.status_file_label = QLabel("")
        self.status_file_label.setStyleSheet("color: #888; padding-right: 8px;")
        self.statusBar().addPermanentWidget(self.status_file_label)
        self._status("Ready")

    def _status(self, message, timeout=5000):
        self.statusBar().showMessage(message, timeout)

    def _update_status_file(self):
        path = self._current_file or self._loaded_file or ""
        self.status_file_label.setText(f"  {path}" if path else "")
        self.file_name_label.setText(os.path.basename(path) if path else "")

    def _build_name_bar(self, parent_layout):
        bar = QWidget()
        bar.setMaximumHeight(26)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.addWidget(QLabel("Name:"))
        self.file_name_label = QLabel("")
        self.file_name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.file_name_label)
        layout.addStretch()
        parent_layout.addWidget(bar)

    def _build_toolbar(self, parent_layout):
        toolbar = QWidget()
        toolbar.setMaximumHeight(32)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(2, 0, 2, 0)
        tb_layout.setSpacing(4)

        tb_layout.addWidget(QLabel("Collections:"))
        self.collections_combo = QComboBox()
        self.collections_combo.setMinimumWidth(150)
        self.collections_combo.setMaximumHeight(24)
        self.collections_combo.activated.connect(self._on_collection_selected)
        tb_layout.addWidget(self.collections_combo)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setToolTip("Reload the current collection from disk")
        self.refresh_btn.setMaximumHeight(24)
        self.refresh_btn.setMaximumWidth(28)
        self.refresh_btn.clicked.connect(self._refresh_current_collection)
        tb_layout.addWidget(self.refresh_btn)

        self.config_btn = QPushButton("Config")
        self.config_btn.setToolTip("Configure directories (collections, covers)")
        self.config_btn.setMaximumHeight(24)
        self.config_btn.clicked.connect(self._config_dir)
        tb_layout.addWidget(self.config_btn)

        self.fetch_btn = QPushButton("Fetch")
        self.fetch_btn.setToolTip("Fetch metadata for the selected or current collection")
        self.fetch_btn.setMaximumHeight(24)
        self.fetch_btn.clicked.connect(self._fetch_metadata)
        tb_layout.addWidget(self.fetch_btn)

        self.load_btn = QPushButton("Load")
        self.load_btn.setToolTip("Load a collection from a JSON file")
        self.load_btn.setMaximumHeight(24)
        self.load_btn.clicked.connect(self._load_json)
        tb_layout.addWidget(self.load_btn)

        tb_layout.addStretch()

        tb_layout.addWidget(QLabel("Folder:"))
        self.video_folder_edit = QLineEdit()
        self.video_folder_edit.setPlaceholderText("Path to video folder...")
        self.video_folder_edit.setMinimumWidth(150)
        self.video_folder_edit.setMaximumHeight(24)
        tb_layout.addWidget(self.video_folder_edit)
        self.video_browse_btn = QPushButton("Browse")
        self.video_browse_btn.setToolTip("Browse for a video folder")
        self.video_browse_btn.setMaximumHeight(24)
        self.video_browse_btn.clicked.connect(self._browse_video_folder)
        tb_layout.addWidget(self.video_browse_btn)
        self.update_btn = QPushButton("Update")
        self.update_btn.setToolTip("Scan the collection folders and add new videos")
        self.update_btn.setMaximumHeight(24)
        self.update_btn.clicked.connect(self._update_collection)
        tb_layout.addWidget(self.update_btn)
        self.rescan_btn = QPushButton("Rescan")
        self.rescan_btn.setToolTip("Re-scan the video folder and refresh the full list")
        self.rescan_btn.setMaximumHeight(24)
        self.rescan_btn.clicked.connect(self._rescan_folder)
        tb_layout.addWidget(self.rescan_btn)
        self.fix_path_btn = QPushButton("Fix Path")
        self.fix_path_btn.setToolTip("Fix missing video paths by selecting a new directory")
        self.fix_path_btn.setMaximumHeight(24)
        self.fix_path_btn.clicked.connect(self._fix_paths)
        tb_layout.addWidget(self.fix_path_btn)

        parent_layout.addWidget(toolbar)

    def _build_panels(self, parent_layout):
        splitter = QSplitter(Qt.Horizontal)

        self.info_panel = InfoPanel()
        splitter.addWidget(self.info_panel)

        self.collection_panel = CollectionPanel()
        splitter.addWidget(self.collection_panel)

        self.add_panel = AddPanel()
        splitter.addWidget(self.add_panel)

        self.tags_panel = TagsPanel()
        splitter.addWidget(self.tags_panel)

        splitter.setSizes([400, 350, 350, 300])
        parent_layout.addWidget(splitter)

    def _connect_signals(self):
        self.collection_panel.add_requested.connect(self._add_videos)
        self.collection_panel.video_clicked.connect(self._on_video_clicked)
        self.add_panel.video_clicked.connect(self._on_video_clicked)
        self.add_panel.remove_requested.connect(self._remove_videos)
        self.add_panel.remove_all_requested.connect(self._remove_all_videos)
        self.add_panel.save_requested.connect(self._save)
        self.add_panel.save_as_requested.connect(self._save_as)

        self.tags_panel.tags_changed.connect(self._on_tags_changed)
        self.info_panel.info_changed.connect(self._on_info_changed)
        self.info_panel.resolve_cover_requested.connect(self._resolve_current_cover)
        self.info_panel.resolve_all_covers_requested.connect(self._resolve_all_covers)

        self.video_folder_edit.textChanged.connect(self._on_video_folder_changed)

    def _load_collections_dir(self):
        self._collections_dir = config_handler.get_collections_dir()
        self._refresh_collections_combo()
        self._update_status_file()

    def _refresh_collections_combo(self):
        self.collections_combo.blockSignals(True)
        self.collections_combo.clear()
        files = config_handler.scan_collection_files()
        for name, path in files.items():
            self.collections_combo.addItem(name, path)
        if self._current_file:
            for i in range(self.collections_combo.count()):
                if self.collections_combo.itemData(i) == self._current_file:
                    self.collections_combo.setCurrentIndex(i)
                    break
        self.collections_combo.blockSignals(False)

    def _on_collection_selected(self, index):
        path = self.collections_combo.itemData(index)
        if path and os.path.exists(path):
            self._load_collection_from_path(path)

    def _refresh_current_collection(self):
        if self._current_file and os.path.exists(self._current_file):
            self._load_collection_from_path(self._current_file)
            self._status(f"Reloaded {os.path.basename(self._current_file)}")

    def _config_dir(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Configuration")
        layout = QVBoxLayout(dialog)

        collections_btn = QPushButton("Config Collections")
        collections_btn.setToolTip("Set the collections directory")
        covers_btn = QPushButton("Config Cover Images")
        covers_btn.setToolTip("Set the cover images directory")
        cancel_btn = QPushButton("Cancel")

        layout.addWidget(collections_btn)
        layout.addWidget(covers_btn)
        layout.addWidget(cancel_btn)

        collections_btn.clicked.connect(lambda: self._choose_collections_dir(dialog))
        covers_btn.clicked.connect(lambda: self._choose_covers_dir(dialog))
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()

    def _choose_collections_dir(self, dialog):
        path = QFileDialog.getExistingDirectory(dialog, "Select Collections Directory", self._collections_dir or "")
        if path:
            self._collections_dir = path
            config_handler.set_collections_dir(path)
            self._refresh_collections_combo()
            self._status("Collections directory updated")
        dialog.accept()

    def _choose_covers_dir(self, dialog):
        current = config_handler.get_covers_dir()
        path = QFileDialog.getExistingDirectory(self, "Select Cover Images Directory", current or "")
        if path:
            config_handler.set_covers_dir(path)
        dialog.accept()

    def _browse_video_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Video Folder")
        if path:
            self.video_folder_edit.setText(path)
            self._status("Video folder set")

    def _update_collection(self):
        if not self._loaded_collections:
            QMessageBox.warning(self, "Warning", "Load a collection first.")
            return

        root_dirs = set()
        existing_paths = set()
        for col in self._loaded_collections:
            for v in col.get("videos", []):
                vp = v["path"]
                existing_paths.add(vp)
                root_dirs.add(os.path.dirname(vp))

        if not root_dirs:
            QMessageBox.warning(self, "Warning", "No video paths found in the loaded collections.")
            return

        self._status("Scanning for new videos...")
        all_videos = set()
        for root_dir in sorted(root_dirs):
            if os.path.isdir(root_dir):
                for vpath in video_scanner.scan_videos(root_dir):
                    all_videos.add(vpath)

        if not all_videos:
            QMessageBox.information(self, "Info", "No videos found in the collection folders.")
            self._status("No videos found", 3000)
            return

        all_videos = sorted(all_videos)
        new_videos = [v for v in all_videos if v not in existing_paths]

        if not new_videos:
            QMessageBox.information(self, "Update Collection", "No new videos found.")
            self._status("No new videos found", 3000)
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Update Collection")
        msg.setText(f"Found {len(new_videos)} new video(s):")
        msg.setDetailedText("\n".join(new_videos))
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Ok)
        if msg.exec() != QMessageBox.Ok:
            return

        self.collection_panel.set_videos(all_videos)

    def _rescan_folder(self):
        folder = self.video_folder_edit.text()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Warning", "Set a video folder first.")
            return
        self._status(f"Scanning {folder}...")
        self._video_collection_map = {}
        videos = video_scanner.scan_videos(folder)
        self.collection_panel.set_videos(videos)
        self.info_panel.clear()
        self.tags_panel.clear()
        self.add_panel.clear()
        self._status(f"Found {len(videos)} videos")

    def _fix_paths(self):
        new_dir = QFileDialog.getExistingDirectory(self, "Select New Video Directory")
        if not new_dir:
            return

        self._status("Scanning for matching files...")
        new_paths = video_scanner.scan_videos(new_dir)
        basename_map = {}
        for np in new_paths:
            basename_map[os.path.basename(np)] = np

        missing = set()
        for path in self.collection_panel.get_all_paths():
            if not os.path.exists(path):
                missing.add(path)
        for path in self.add_panel.get_all_paths():
            if not os.path.exists(path):
                missing.add(path)

        if not missing:
            QMessageBox.information(self, "Info", "No missing videos to fix.")
            self._status("No missing videos to fix", 3000)
            return

        fix_map = {}
        for old_path in missing:
            bn = os.path.basename(old_path)
            if bn in basename_map:
                fix_map[old_path] = basename_map[bn]

        if not fix_map:
            QMessageBox.information(self, "Info", "No matching files found in the selected directory.")
            self._status("No matching files found", 3000)
            return

        for old_path, new_path in fix_map.items():
            self.collection_panel.replace_path(old_path, new_path)
            self.add_panel.replace_path(old_path, new_path)

            for col in self._loaded_collections:
                for v in col.get("videos", []):
                    if v["path"] == old_path:
                        v["path"] = new_path

            if old_path in self._video_collection_map:
                self._video_collection_map[new_path] = self._video_collection_map.pop(old_path)

            for ve in self._collection.videos:
                if ve.path == old_path:
                    ve.path = new_path

        QMessageBox.information(
            self, "Fixed",
            f"Fixed {len(fix_map)} video path(s).\nUnmatched missing videos: {len(missing) - len(fix_map)}"
        )
        self._status(f"Fixed {len(fix_map)} video path(s)", 5000)

    def _fetch_metadata(self):
        selected = self.collection_panel.get_selected_paths()

        def _extract_year(stem):
            m = re.search(r'[\(\[\{](19\d{2}|20\d{2})[\)\]\}]', stem)
            if m:
                return m.group(1)
            m = re.search(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)', stem)
            return m.group(1) if m else ""

        def _clean_title(stem, year):
            if not year:
                return stem.strip()
            title = re.sub(r'[\(\[\{](?:19\d{2}|20\d{2})[\)\]\}]', '', stem)
            title = re.sub(r'(?<!\d)' + year + r'(?!\d)', '', title)
            return re.sub(r'[\s.\-_]+', ' ', title).strip()

        if not selected:
            name = self.info_panel.name_edit.text()
            year = _extract_year(name)
            title = _clean_title(name, year)
            dialog = FetchDialog(self, "", [(None, title, year)])
            if dialog.exec() == FetchDialog.Accepted:
                result = dialog.get_result()
                if result:
                    self._apply_fetched_metadata(result, "")
                    self._status("Metadata applied")
            return
        items = []
        for vpath in selected:
            stem = os.path.splitext(os.path.basename(vpath))[0]
            year = _extract_year(stem)
            title = _clean_title(stem, year)
            items.append((vpath, title, year))
        dialog = FetchDialog(self, items=items)
        if dialog.exec() == FetchDialog.Accepted:
            results = dialog.get_results()
            count = sum(1 for _, r in results if r)
            for vpath, result in results:
                if result:
                    self._apply_fetched_metadata(result, vpath)
            self._status(f"Applied metadata for {count} video(s)")

    def _apply_fetched_metadata(self, result, vpath):
        title = result.get("title", "")
        cover_url = result.get("cover", "")

        local_cover = ""
        if cover_url and cover_url.startswith("http"):
            save_dir = config_handler.get_covers_dir()
            if not save_dir:
                base = os.path.dirname(os.path.abspath(self._current_file)) if self._current_file else os.getcwd()
                save_dir = os.path.join(base, "covers")
            local_cover = metadata_fetcher.download_cover(cover_url, save_dir, title, force=True)
            if local_cover:
                local_cover = self._relativize_cover_path(local_cover)

        cover_path = local_cover or cover_url

        found = False
        for col in self._loaded_collections:
            col_id = col.get("id", "")
            if col_id and col_id == make_id(title):
                found = True
            elif vpath and any(v.get("path") == vpath for v in col.get("videos", [])):
                found = True
            if found:
                col["name"] = title
                col["cover"] = cover_path
                col["id"] = make_id(title)
                col["description"] = result.get("description", "")
                col["genre"] = result.get("genre", [])
                col["year"] = result.get("year", 0)
                break

        if not found:
            if vpath:
                self._loaded_collections.append({
                    "id": "",
                    "name": title,
                    "cover": cover_path,
                    "description": result.get("description", ""),
                    "genre": result.get("genre", []),
                    "year": result.get("year", 0),
                    "videos": [{"path": vpath, "duration": 0.0}],
                    "tags": [],
                })
            else:
                for col in self._loaded_collections:
                    if col.get("name") == title:
                        col["name"] = title
                        col["cover"] = cover_path
                        col["id"] = make_id(title)
                        col["description"] = result.get("description", "")
                        col["genre"] = result.get("genre", [])
                        col["year"] = result.get("year", 0)
                        found = True
                        break
                if not found and self._loaded_collections:
                    col = self._loaded_collections[0]
                    col["name"] = title
                    col["cover"] = cover_path
                    col["id"] = make_id(title)
                    col["description"] = result.get("description", "")
                    col["genre"] = result.get("genre", [])
                    col["year"] = result.get("year", 0)

        self._rebuild_video_map()

        if vpath:
            self.collection_panel.rename_item(vpath, title)
            self.add_panel.rename_item(vpath, title)

        data = {
            "id": make_id(title),
            "name": title,
            "cover": cover_path,
            "description": result.get("description", ""),
            "genre": result.get("genre", []),
            "year": result.get("year", 0),
        }
        self.info_panel.set_data(data)
        resolved = self._resolve_cover_path(cover_path)
        if resolved and os.path.exists(resolved):
            self.info_panel.cover.set_cover(resolved)
        self._on_info_changed()

    def _on_video_folder_changed(self, path):
        if os.path.isdir(path):
            videos = video_scanner.scan_videos(path)
            self.collection_panel.set_videos(videos)
            self._status(f"Found {len(videos)} videos in folder")

    def _on_video_clicked(self, video_path):
        col = self._video_collection_map.get(video_path)
        if col:
            self._switch_to_collection_entry(col)

    def _add_videos(self, paths):
        if not paths:
            QMessageBox.information(self, "Info", "Check videos in the Available list first.")
            return
        self.add_panel.add_videos(paths)
        self._status(f"Added {len(paths)} video(s)")

    def _remove_videos(self):
        self.add_panel.remove_selected()
        self._status("Removed selected video(s)")

    def _remove_all_videos(self):
        self.add_panel.clear()
        self._status("Cleared all videos")

    def _on_tags_changed(self, tags):
        self.info_panel.set_tags(tags)
        self._collection.tags = tags

        selected_paths = set()
        selected_paths.update(self.collection_panel.get_selected_paths())
        selected_paths.update(self.add_panel.get_selected_paths())

        if not selected_paths:
            for col in self._loaded_collections:
                if col.get("id") == self._collection.id:
                    col["tags"] = tags
                    return
            for col in self._loaded_collections:
                col_vids = [v["path"] for v in col.get("videos", [])]
                for v in self._collection.videos:
                    if v.path in col_vids:
                        col["tags"] = tags
                        return
            return

        updated = set()
        for path in selected_paths:
            col = self._video_collection_map.get(path)
            if col is not None and id(col) not in updated:
                col["tags"] = tags
                updated.add(id(col))

    def _on_info_changed(self):
        data = self.info_panel.get_data()
        self._collection.name = data["name"]
        self._collection.cover = data["cover"]
        self._collection.description = data["description"]
        self._collection.genre = data["genre"]
        self._collection.year = data["year"]
        self._collection.sync_id()

    def _load_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Collection JSON", "", "JSON Files (*.json)"
        )
        if path:
            self._load_collection_from_path(path)

    def _load_collection_from_path(self, path):
        self._status(f"Loading {os.path.basename(path)}...")
        data = json_handler.load_collection(path)
        if data is None:
            QMessageBox.warning(self, "Error", f"Could not load: {path}")
            self._status("Failed to load", 3000)
            return

        collections_list = data.get("collections", [])
        if not collections_list:
            QMessageBox.warning(self, "Error", "No collections found in file.")
            self._status("No collections found", 3000)
            return

        self._video_collection_map = {}
        all_video_paths = set()
        for col in collections_list:
            for v in col.get("videos", []):
                vp = v["path"]
                all_video_paths.add(vp)
                if vp not in self._video_collection_map:
                    self._video_collection_map[vp] = col
        self.collection_panel.set_videos(sorted(all_video_paths))

        self._loaded_collections = collections_list
        self._loaded_file = path
        self.add_panel.clear()

        entry = collections_list[0]
        self._switch_to_collection_entry(entry)
        self._current_file = path
        self._update_status_file()
        self._status(f"Loaded {len(collections_list)} collection(s), {len(all_video_paths)} video(s)")

    def _switch_to_collection_entry(self, entry):
        self._collection = Collection.from_dict(entry)

        cover_original = entry.get("cover", "")
        resolved_cover = self._resolve_cover_path(cover_original)

        entry_copy = dict(entry)
        entry_copy["cover"] = cover_original

        entry_tags = entry_copy.get("tags", [])

        self.info_panel.set_data(entry_copy, tags=entry_tags)
        if resolved_cover and os.path.exists(resolved_cover):
            self.info_panel.cover.set_cover(resolved_cover)
        else:
            self.info_panel.cover.clear_cover()
        self.tags_panel.set_tags(entry_tags)

    def _resolve_cover_path(self, cover_path):
        if not cover_path:
            return ""
        if os.path.exists(cover_path):
            return cover_path
        fname = os.path.basename(cover_path)
        candidates = []

        def walk_up_and_try(base_dir, depth=5):
            if not base_dir or not os.path.isdir(base_dir):
                return
            level = os.path.abspath(base_dir)
            for _ in range(depth):
                candidates.append(os.path.join(level, cover_path))
                candidates.append(os.path.join(level, fname))
                for sub in ["covers", "user/covers", "cover"]:
                    candidates.append(os.path.join(level, sub, fname))
                parent = os.path.dirname(level)
                if parent == level:
                    break
                level = parent

        if self._current_file:
            base = os.path.dirname(os.path.abspath(self._current_file))
            walk_up_and_try(base)
        if self._loaded_file and self._loaded_file != self._current_file:
            base = os.path.dirname(os.path.abspath(self._loaded_file))
            walk_up_and_try(base)
        folder = self.video_folder_edit.text()
        if folder and os.path.isdir(folder):
            walk_up_and_try(folder)
        for c in candidates:
            if os.path.exists(c):
                return os.path.normpath(c)
        covers_dir = config_handler.get_covers_dir()
        if covers_dir and os.path.isdir(covers_dir):
            direct = os.path.join(covers_dir, fname)
            if os.path.exists(direct):
                return os.path.normpath(direct)
        return cover_path

    def _relativize_cover_path(self, cover_path):
        if not cover_path or not os.path.isabs(cover_path):
            return cover_path
        collections_dir = config_handler.get_collections_dir()
        if collections_dir:
            base = os.path.dirname(os.path.dirname(collections_dir.rstrip("/")))
            if cover_path.startswith(base.rstrip("/") + "/"):
                return os.path.relpath(cover_path, base)
        return os.path.relpath(cover_path, os.path.dirname(os.path.abspath(self._current_file))) if self._current_file else cover_path

    def _save(self):
        if not self.add_panel.get_video_paths():
            QMessageBox.warning(self, "No Videos", "Add videos before saving.")
            return
        if not self._current_file:
            self._save_as()
            return
        confirm = QMessageBox.question(
            self, "Confirm Save",
            f"Save to {os.path.basename(self._current_file)}?",
            QMessageBox.Save | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if confirm != QMessageBox.Save:
            return
        self._status(f"Saving to {os.path.basename(self._current_file)}...")
        self._write_json(self._current_file)

    def _save_as(self):
        if not self.add_panel.get_video_paths():
            QMessageBox.warning(self, "No Videos", "Add videos before saving.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Collection JSON", "", "JSON Files (*.json)"
        )
        if path:
            if not path.endswith(".json"):
                path += ".json"
            self._write_json(path)

    def _write_json(self, path):
        collections = []
        video_meta = {}
        for col in self._loaded_collections:
            for v in col.get("videos", []):
                vp = v["path"]
                if vp not in video_meta:
                    video_meta[vp] = {
                        "id": col.get("id", ""),
                        "name": col.get("name", ""),
                        "cover": col.get("cover", ""),
                        "description": col.get("description", ""),
                        "genre": col.get("genre", []),
                        "year": col.get("year", 0),
                        "tags": col.get("tags", []),
                        "duration": v.get("duration", 0.0),
                    }
        for vpath in self.add_panel.get_video_paths():
            meta = video_meta.get(vpath, {})
            fname = os.path.splitext(os.path.basename(vpath))[0]
            vid = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in fname.lower().replace(" ", "_")).strip("_")
            if not vid:
                vid = "video"
            duration = meta.get("duration", 0.0)
            if duration == 0.0 and os.path.exists(vpath):
                duration = video_scanner.get_video_duration(vpath)
            cover_val = self._resolve_cover_path(meta.get("cover", "")) or meta.get("cover", "")
            if cover_val and os.path.isabs(cover_val):
                cover_val = self._relativize_cover_path(cover_val)
            entry = {
                "id": vid,
                "name": meta.get("name") or fname,
                "cover": cover_val,
                "description": meta.get("description", ""),
                "genre": meta.get("genre", []),
                "year": meta.get("year", 0),
                "videos": [{"path": vpath, "duration": duration}],
                "tags": meta.get("tags", []),
            }
            collections.append(entry)

        json_handler.save_collection(path, {"collections": collections})
        self._loaded_collections = collections
        self._rebuild_video_map()
        self.collection_panel.set_videos(sorted(self._video_collection_map.keys()))

        self._current_file = path
        self._update_status_file()
        self._refresh_collections_combo()

        self._status(f"Saved {len(collections)} collections to {os.path.basename(path)}")
        QMessageBox.information(self, "Saved", f"Saved to:\n{path}")

    def _resolve_current_cover(self):
        covers_dir = config_handler.get_covers_dir()
        if not covers_dir or not os.path.isdir(covers_dir):
            QMessageBox.information(self, "Cannot Resolve", "Covers directory is not configured or does not exist.")
            return

        entry = None
        idx = -1
        for i, col in enumerate(self._loaded_collections):
            if col.get("id") == self.info_panel.get_data().get("id"):
                entry = col
                idx = i
                break
        if entry is None:
            return

        name = entry.get("name", "")
        stored = entry.get("cover", "")
        resolved = find_cover_in_dir(covers_dir, name, stored)
        if resolved and resolved != stored:
            entry["cover"] = resolved
            self._switch_to_collection_entry(entry)
            self._status(f"Resolved cover for '{name}'")
        elif resolved:
            self._status(f"Cover for '{name}' is already valid")
        else:
            self._status(f"Could not resolve cover for '{name}'", 3000)

    def _resolve_all_covers(self):
        covers_dir = config_handler.get_covers_dir()
        if not covers_dir or not os.path.isdir(covers_dir):
            QMessageBox.information(self, "Cannot Resolve", "Covers directory is not configured or does not exist.")
            return

        reply = QMessageBox.question(
            self, "Resolve All Covers",
            "Search for all missing covers in the covers directory?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        count = 0
        for entry in self._loaded_collections:
            name = entry.get("name", "")
            stored = entry.get("cover", "")
            resolved = find_cover_in_dir(covers_dir, name, stored)
            if resolved and resolved != stored:
                entry["cover"] = resolved
                count += 1

        if count == 0:
            QMessageBox.information(self, "Resolve All", "No missing covers were resolved.")
        else:
            QMessageBox.information(self, "Resolve All", f"Resolved {count} missing cover(s).")

        current_id = self.info_panel.get_data().get("id")
        for entry in self._loaded_collections:
            if entry.get("id") == current_id:
                self._switch_to_collection_entry(entry)
                break
        self._status(f"Resolved {count} cover(s)")

    def _rebuild_video_map(self):
        self._video_collection_map = {}
        for col in self._loaded_collections:
            for v in col.get("videos", []):
                vp = v["path"]
                if vp not in self._video_collection_map:
                    self._video_collection_map[vp] = col


