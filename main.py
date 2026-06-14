import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import App
from src.window import MainWindow


def main():
    app = App(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
