import hashlib
import os


def make_id(name):
    raw = name.strip().lower().replace(" ", "_")
    if not raw:
        return "untitled"
    return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in raw)


class VideoEntry:
    def __init__(self, path="", duration=0.0):
        self.path = path
        self.duration = duration

    def to_dict(self):
        return {"path": self.path, "duration": self.duration}

    @staticmethod
    def from_dict(d):
        return VideoEntry(path=d.get("path", ""), duration=d.get("duration", 0.0))


class Collection:
    def __init__(self, name=""):
        self.id = make_id(name) if name else ""
        self.name = name
        self.name_bg = ""
        self.cover = ""
        self.description = ""
        self.genre = []
        self.year = 0
        self.videos = []
        self.tags = []
        self._loaded_path = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_bg": self.name_bg,
            "cover": self.cover,
            "description": self.description,
            "genre": self.genre,
            "year": self.year,
            "videos": [v.to_dict() for v in self.videos],
            "tags": self.tags,
        }

    @staticmethod
    def from_dict(d):
        c = Collection()
        c.id = d.get("id", "")
        c.name = d.get("name", "")
        c.name_bg = d.get("name_bg", "")
        c.cover = d.get("cover", "")
        c.description = d.get("description", "")
        c.genre = d.get("genre", [])
        c.year = d.get("year", 0)
        c.tags = d.get("tags", [])
        c.videos = [VideoEntry.from_dict(v) for v in d.get("videos", [])]
        return c

    def sync_id(self):
        if self.name:
            self.id = make_id(self.name)
