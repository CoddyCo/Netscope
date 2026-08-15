"""
Search Bar Widget

Input field for entering domains/IPs with a Trace button.
Handles input validation, cancel during active trace, and keyboard shortcuts.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton, QWidget,
)


class SearchBar(QWidget):
    """Search bar with input validation and trace control."""

    trace_requested = pyqtSignal(str)   # Domain or IP entered
    cancel_requested = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_tracing = False
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Enter a website or IP  (e.g., leetcode.com, 8.8.8.8)")
        self._input.setMinimumHeight(44)
        self._input.setObjectName("searchInput")
        self._input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._input, stretch=1)

        self._button = QPushButton("⚡ Trace Route")
        self._button.setMinimumHeight(44)
        self._button.setMinimumWidth(140)
        self._button.setObjectName("traceButton")
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.clicked.connect(self._on_submit)
        layout.addWidget(self._button)
        
        self._export_btn = QPushButton("💾 Export")
        self._export_btn.setMinimumHeight(44)
        self._export_btn.setMinimumWidth(100)
        self._export_btn.setObjectName("exportButton")
        self._export_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a2040;
                color: #8a9abc;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2a3050; }
        """)
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.clicked.connect(self.export_requested.emit)
        self._export_btn.setEnabled(False)
        layout.addWidget(self._export_btn)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Escape"), self, self._on_cancel)

    def _on_submit(self):
        if self._is_tracing:
            self._on_cancel()
            return

        text = self._input.text().strip()
        if text:
            self.trace_requested.emit(text)

    def _on_cancel(self):
        self.cancel_requested.emit()

    def set_tracing(self, tracing: bool):
        """Update UI state for active/inactive trace."""
        self._is_tracing = tracing
        if tracing:
            self._button.setText("✕ Cancel")
            self._button.setObjectName("cancelButton")
            self._input.setEnabled(False)
        else:
            self._button.setText("⚡ Trace Route")
            self._button.setObjectName("traceButton")
            self._input.setEnabled(True)
            self._export_btn.setEnabled(True)
        # Force style refresh
        self._button.style().unpolish(self._button)
        self._button.style().polish(self._button)

    def set_text(self, text: str):
        """Set the input text programmatically."""
        self._input.setText(text)

    def text(self) -> str:
        return self._input.text().strip()
