"""
Main Window

The central application window that:
- Arranges all widgets (search bar, map, sidebars, timeline, diagnosis)
- Wires TraceController signals to GUI update slots
- Manages trace state (idle → tracing → complete)
"""

from __future__ import annotations

from typing import Optional

import json
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget, QFileDialog, QLabel, QMainWindow, QStatusBar,
    QVBoxLayout, QWidget, QTabWidget, QMessageBox
)

from netscope.core.database import NetScopeDB
from netscope.core.models import Hop, TraceSummary
from netscope.core.trace_controller import TraceController
from netscope.gui.diagnosis_panel import DiagnosisPanel
from netscope.gui.diagnostic_dashboard import DiagnosticDashboard
from netscope.gui.hop_drawer import HopDrawer
from netscope.gui.hop_timeline import HopTimeline
from netscope.gui.left_sidebar import LeftSidebar
from netscope.gui.right_sidebar import RightSidebar
from netscope.gui.search_bar import SearchBar


class MainWindow(QMainWindow):
    """NetScope main application window."""

    def __init__(self, demo_mode: bool = False):
        super().__init__()
        self._demo_mode = demo_mode
        self._hops: list[Hop] = []
        self._summary: Optional[TraceSummary] = None

        self._setup_window()
        self._setup_widgets()
        self._setup_controller()
        self._load_recent_searches()

    def _setup_window(self):
        """Configure the main window properties."""
        self.setWindowTitle("🌍 NetScope — Network Diagnostic Platform")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Dark window background
        self.setStyleSheet("QMainWindow { background-color: #0a0a1a; }")

    def _setup_widgets(self):
        """Create and arrange all widgets."""
        # Central widget: search bar + map
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Search bar at top
        self._search_bar = SearchBar()
        central_layout.addWidget(self._search_bar)

        # Dashboard replaces map
        self._dashboard = DiagnosticDashboard(self)
        central_layout.addWidget(self._dashboard, stretch=1)

        self.setCentralWidget(central)

        # Left sidebar (Route Info + Recent Searches)
        self._left_sidebar = LeftSidebar(self)
        self._left_sidebar.setMinimumWidth(320)
        self._left_sidebar.setMaximumWidth(400)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._left_sidebar)

        # Right sidebar (Health Score + Statistics)
        self._right_sidebar = RightSidebar(self)
        self._right_sidebar.setMinimumWidth(380)
        self._right_sidebar.setMaximumWidth(500)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._right_sidebar)

        # Bottom dock: hop timeline
        self._timeline = HopTimeline(self)
        timeline_dock = QDockWidget("Hop Timeline", self)
        timeline_dock.setObjectName("timelineDock")
        timeline_dock.setWidget(self._timeline)
        timeline_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        timeline_dock.setMinimumHeight(150)
        timeline_dock.setMaximumHeight(220)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, timeline_dock)

        # Hop detail drawer (bottom right)
        self._hop_drawer = HopDrawer(self)
        self._hop_drawer.setMaximumWidth(380)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._hop_drawer)

        # Diagnosis panel (below right sidebar)
        self._diagnosis_panel = DiagnosisPanel(self)
        self._diagnosis_panel.setMaximumWidth(500)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._diagnosis_panel)

        # Tabify the right panels to save space
        self.tabifyDockWidget(self._right_sidebar, self._diagnosis_panel)
        self.tabifyDockWidget(self._diagnosis_panel, self._hop_drawer)
        
        # Set tabs to North
        self.setTabPosition(Qt.DockWidgetArea.RightDockWidgetArea, QTabWidget.TabPosition.North)
        
        # Raise Right Sidebar so it's the active tab initially
        self._right_sidebar.raise_()


        # Status bar
        self._status_bar = QStatusBar()
        self._status_bar.setObjectName("statusBar")
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statusLabel")
        self._status_bar.addPermanentWidget(self._status_label)
        self.setStatusBar(self._status_bar)

    def _setup_controller(self):
        """Initialize the trace controller and connect signals."""
        self._controller = TraceController(demo_mode=self._demo_mode)

        # Search bar → controller
        self._search_bar.trace_requested.connect(self._start_trace)
        self._search_bar.cancel_requested.connect(self._cancel_trace)
        self._search_bar.export_requested.connect(self._export_trace)

        # Controller → GUI
        self._controller.hop_received.connect(self._on_hop)
        self._controller.trace_complete.connect(self._on_trace_complete)
        self._controller.trace_error.connect(self._on_trace_error)
        self._controller.status_update.connect(self._on_status)
        self._controller.connection_ready.connect(self._right_sidebar.update_connection)

        # Timeline → hop drawer
        self._timeline.hop_selected.connect(self._on_hop_selected)
        self._dashboard._chart.hop_selected.connect(self._on_hop_selected)

        # Recent searches → re-trace
        self._left_sidebar.search_clicked.connect(self._on_recent_search)

    def _start_trace(self, target: str):
        """Start a new diagnostic trace."""
        # Reset UI
        self._hops = []
        self._timeline.clear()
        self._hop_drawer.clear()
        self._left_sidebar.clear()
        self._right_sidebar.clear()
        self._diagnosis_panel.clear()

        # Raise the right sidebar to show new stats
        self._right_sidebar.raise_()

        self._search_bar.set_tracing(True)
        self._controller.start_trace(target)

    def _cancel_trace(self):
        """Cancel the running trace."""
        self._controller.cancel()
        self._search_bar.set_tracing(False)
        self._status_label.setText("Cancelled")

    def _on_hop(self, hop: Hop):
        """Handle a new hop discovered by the engine."""
        self._hops.append(hop)
        
        # Update timeline
        self._timeline.add_hop(hop)

        # Update status
        location = ""
        if hop.geo and hop.geo.city:
            location = f" ({hop.geo.city}, {hop.geo.country_code})"
        elif hop.geo and hop.geo.country:
            location = f" ({hop.geo.country})"

        if hop.is_timeout:
            self._status_label.setText(f"Hop {hop.hop_number}: * * *{location}")
        else:
            self._status_label.setText(
                f"Hop {hop.hop_number}: {hop.ip} — {hop.avg_rtt:.1f}ms{location}"
            )

    def _on_trace_complete(self, summary: TraceSummary):
        """Handle trace completion."""
        self._summary = summary
        self._search_bar.set_tracing(False)

        # Update all panels
        self._dashboard.update_info(summary)
        self._left_sidebar.update_info(summary)
        self._right_sidebar.update_stats(summary)

        if summary.diagnosis:
            self._diagnosis_panel.update_diagnosis(summary.diagnosis)

        score = summary.health.score if summary.health else 0
        rating = summary.health.rating if summary.health else ""
        
        self._status_label.setText(
            f"✅ Complete — {summary.total_hops} hops, "
            f"{summary.avg_latency:.0f}ms avg, "
            f"Score: {score}/100 {rating}"
        )

        # Refresh recent searches
        self._load_recent_searches()

    def _on_trace_error(self, error: str):
        """Handle trace error."""
        self._search_bar.set_tracing(False)
        self._status_label.setText(f"❌ Error: {error}")

    def _on_status(self, text: str):
        """Update status bar."""
        self._status_label.setText(text)

    def _export_trace(self):
        """Export the current trace summary to JSON."""
        if not self._summary:
            QMessageBox.warning(self, "No Data", "There is no trace data to export yet.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Trace", f"{self._summary.target}_trace.json", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self._summary.to_json(indent=4))
                self.show_status(f"Exported trace to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export trace: {e}")

    def _on_hop_selected(self, index: int):
        """Handle hop selection from timeline or chart."""
        if 0 <= index < len(self._hops):
            self._hop_drawer.show_hop(self._hops[index])
            # Interactively raise the tab
            self._hop_drawer.raise_()
            # Pop the tab to the front
            self._hop_drawer.raise_()

    def _on_recent_search(self, target: str):
        """Re-trace a target from recent searches."""
        self._search_bar.set_text(target)
        self._start_trace(target)

    def _load_recent_searches(self):
        """Load recent searches from the database."""
        try:
            db = NetScopeDB()
            searches = db.get_recent_searches(limit=8)
            db.close()
            self._left_sidebar.set_recent_searches(searches)
        except Exception:
            pass

    def closeEvent(self, event):
        """Handle window close event to ensure background threads are terminated."""
        if hasattr(self, '_controller') and self._controller:
            self._controller.cancel()
        super().closeEvent(event)
