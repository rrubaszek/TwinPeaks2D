#!/usr/bin/env python3
"""TwinPeaks2D map editor. Usage: .venv/bin/python editor/run_editor.py [maps/map.txt]"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from tpedit.main_window import MainWindow  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("TwinPeaks2D Map Editor")
    window = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
