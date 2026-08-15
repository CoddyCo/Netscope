"""
NetScope Application Entry Point

Configures the QApplication, loads the cyberpunk theme,
and launches the main window.
"""

import sys
from pathlib import Path

from PyQt6.QtGui import QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication

from netscope.gui.main_window import MainWindow


class NetScopeApp:
    def __init__(self, demo_mode: bool = False):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("NetScope")
        self.app.setOrganizationName("NetScope")

        self._load_fonts()
        self._load_theme()

        self.window = MainWindow(demo_mode=demo_mode)

    def _load_fonts(self):
        """Load custom fonts if available."""
        # We try to use system Consolas/Monaco, but could load TTF here
        pass

    def _load_theme(self):
        """Load the cyberpunk QSS stylesheet."""
        theme_path = Path(__file__).parent / "themes" / "cyberpunk.qss"
        if theme_path.exists():
            with open(theme_path) as f:
                self.app.setStyleSheet(f.read())
        else:
            print(f"Warning: Theme not found at {theme_path}")

    def run(self) -> int:
        """Show window and start event loop."""
        self.window.show()
        return self.app.exec()
