"""
Diagnostic Dashboard

The primary central view for the application. Displays:
1. Automated Diagnosis
2. Linear Route Topology
3. Latency vs Hop charts
"""

from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from netscope.core.models import TraceSummary
from netscope.utils.formatters import latency_color


class LatencyChartWidget(FigureCanvasQTAgg):
    """Line chart showing RTT progression across hops."""

    hop_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        self._fig = Figure(figsize=(8, 3), facecolor="#0a0a1a")
        super().__init__(self._fig)
        self.setParent(parent)
        self._ax = self._fig.add_subplot(111)
        self._init_plot()
        self._fig.canvas.mpl_connect("pick_event", self._on_pick)

    def _on_pick(self, event):
        """Emit a signal with the index of the picked point."""
        if hasattr(event, "ind") and len(event.ind) > 0:
            index = int(event.ind[0])
            self.hop_selected.emit(index)

    def _init_plot(self):
        self._ax.set_facecolor("#0a0a1a")
        self._ax.tick_params(colors="#8a9abc")
        for spine in self._ax.spines.values():
            spine.set_color("#1a2040")
        self._fig.tight_layout()

    def update_data(self, summary: TraceSummary):
        self._ax.clear()
        self._init_plot()
        
        if not summary.hops:
            self.draw()
            return

        x_vals = []
        y_vals = []
        colors = []

        for hop in summary.hops:
            if hop.avg_rtt > 0:
                x_vals.append(hop.hop_number)
                y_vals.append(hop.avg_rtt)
                colors.append(latency_color(hop.avg_rtt))

        if not x_vals:
            self.draw()
            return

        # Plot line
        self._ax.plot(x_vals, y_vals, color="#334466", linestyle="-", marker="", zorder=1)
        
        # Plot scatter points on top, with picker=5 to enable picking with a tolerance of 5 pts
        self._ax.scatter(x_vals, y_vals, c=colors, s=100, zorder=2, edgecolors="#000000", linewidths=1.5, picker=5)

        # Baseline overlay
        if getattr(summary, "historical_average", None):
            self._ax.axhline(y=summary.historical_average, color="#FFBB00", linestyle="--", alpha=0.7, zorder=0)
            # Add a small text label for the baseline
            self._ax.text(x_vals[-1], summary.historical_average + 2, f"Historical Avg: {summary.historical_average:.1f}ms", 
                          color="#FFBB00", fontsize=8, ha="right", alpha=0.8)

        self._ax.set_ylabel("Latency (ms)", color="#8a9abc", fontsize=10, labelpad=10)
        self._ax.set_xlabel("Hop Number", color="#8a9abc", fontsize=10, labelpad=10)
        
        # Add a subtle grid
        self._ax.grid(True, linestyle="--", alpha=0.2, color="#00ffcc")
        
        # Adjust Y limit slightly above max
        max_y = max(y_vals) if y_vals else 0
        if max_y > 0:
            self._ax.set_ylim(bottom=0, top=max_y * 1.2)
        
        self._fig.tight_layout(pad=1.5)
        self.draw()


class DiagnosticDashboard(QWidget):
    """Primary central widget for trace analysis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("diagnosticDashboard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)



        # (Route Topology has been removed per feedback to reduce redundancy)

        # 3. Chart Panel
        chart_container = QWidget()
        chart_container.setObjectName("cardPanel")
        chart_layout = QVBoxLayout(chart_container)
        
        chart_title = QLabel("LATENCY ANALYSIS")
        chart_title.setObjectName("sidebarTitle")
        chart_layout.addWidget(chart_title)
        
        self._chart = LatencyChartWidget()
        chart_layout.addWidget(self._chart, stretch=1)
        
        layout.addWidget(chart_container, stretch=1)

    def update_info(self, summary: TraceSummary):
        """Update all panels with new trace data."""
        # Update Chart
        self._chart.update_data(summary)
