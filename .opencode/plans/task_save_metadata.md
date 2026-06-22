# Fix InfoPanel metadata persistence and add Save Collection button

## Problem
1. Edits to name, description, genre, year, cover in InfoPanel are never persisted. `_on_info_changed` updates `self._collection` (a Python object) but not `self._loaded_collections` (raw dicts used by `_write_json`).
2. Switching videos discards unsaved edits because `_switch_to_collection_entry` reloads from `_loaded_collections`.
3. No quick way to save metadata — the Save button is in AddPanel and requires videos.

## Changes

### 1. Fix `_on_info_changed` — `src/window.py:504-511`

Sync name/cover/description/genre/year back to `_loaded_collections`:

```python
def _on_info_changed(self):
    data = self.info_panel.get_data()
    self._collection.name = data["name"]
    self._collection.cover = data["cover"]
    self._collection.description = data["description"]
    self._collection.genre = data["genre"]
    self._collection.year = data["year"]
    self._collection.sync_id()
    for col in self._loaded_collections:
        if col.get("id") == self._collection.id:
            col.update(data)
            return
```

### 2. Add Save Collection button to InfoPanel — `src/info_panel.py`

- Add signal `save_requested = Signal()` (line 11)
- Add `QPushButton("Save Collection")` before `layout.addStretch()` (line 68)
- Set tooltip `"Save all collection metadata to file"`
- Connect `clicked` -> `self.save_requested.emit()`

### 3. Connect and implement save — `src/window.py`

- Add connection (after line 167): `self.info_panel.save_requested.connect(self._save_metadata)`
- New method:

```python
def _save_metadata(self):
    if not self._current_file:
        self._save_as()
        return
    confirm = QMessageBox.question(
        self, "Confirm Save",
        f"Save collection metadata to {os.path.basename(self._current_file)}?",
        QMessageBox.Save | QMessageBox.Cancel,
        QMessageBox.Cancel,
    )
    if confirm != QMessageBox.Save:
        return
    self._status(f"Saving metadata to {os.path.basename(self._current_file)}...")
    json_handler.save_collection(self._current_file, {"collections": self._loaded_collections})
    self._update_status_file()
    self._refresh_collections_combo()
    self._status(f"Saved metadata to {os.path.basename(self._current_file)}")
    QMessageBox.information(self, "Saved", f"Metadata saved to:\n{self._current_file}")
```

## Files to modify
- `src/window.py` — `_on_info_changed`, new `_save_metadata` method, signal connection
- `src/info_panel.py` — add `save_requested` signal + Save Collection button
