from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from src.tag_widget import TagWidget

BUILTIN_TAGS = [
    "Trailers", "Music", "Standby Video",
]

BUILTIN_ACTORS = [
    "Robert Downey Jr.", "Steven Seagal", "Leonardo DiCaprio",
    "Tom Hanks", "Brad Pitt", "Morgan Freeman", "Denzel Washington",
    "Meryl Streep", "Jennifer Lawrence", "Christian Bale",
    "Heath Ledger", "Cillian Murphy", "Florence Pugh",
    "Timothée Chalamet", "Zendaya", "Oscar Isaac", "Adam Driver",
    "Margot Robbie", "Ryan Gosling", "Emma Stone", "Joaquin Phoenix",
    "Pedro Pascal", "Bella Ramsey", "Keanu Reeves", "Natalie Portman",
    "Samuel L. Jackson", "Uma Thurman", "Harrison Ford",
]


class TagsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Tags")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        self.tag_widget = TagWidget()
        layout.addWidget(self.tag_widget)

        builtin_title = QLabel("Built-in Tags")
        builtin_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 8px;")
        layout.addWidget(builtin_title)

        actors_title = QLabel("Actors:")
        actors_title.setStyleSheet("font-size: 11px; color: #aaa;")
        layout.addWidget(actors_title)

        self.actors_list = QListWidget()
        self.actors_list.setMaximumHeight(150)
        for name in BUILTIN_ACTORS:
            QListWidgetItem(name.strip(), self.actors_list)
        self.actors_list.itemClicked.connect(self._on_tag_clicked)
        layout.addWidget(self.actors_list)

        categories_title = QLabel("Categories:")
        categories_title.setStyleSheet("font-size: 11px; color: #aaa; margin-top: 4px;")
        layout.addWidget(categories_title)

        self.categories_list = QListWidget()
        self.categories_list.setMaximumHeight(80)
        for name in BUILTIN_TAGS:
            QListWidgetItem(name, self.categories_list)
        self.categories_list.itemClicked.connect(self._on_tag_clicked)
        layout.addWidget(self.categories_list)

    def _on_tag_clicked(self, item):
        self.tag_widget.add_tag_text(item.text())

    def get_tags(self):
        return self.tag_widget.get_tags()

    def set_tags(self, tags):
        self.tag_widget.set_tags(tags)

    def clear(self):
        self.tag_widget.set_tags([])

    @property
    def tags_changed(self):
        return self.tag_widget.tags_changed
