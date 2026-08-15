"""
Left Sidebar — Route Information Panel

Displays destination info, ISP, cloud provider, and route summary.
Also contains the recent searches list.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget, QLabel, QListWidget, QListWidgetItem,
    QVBoxLayout, QWidget, QGridLayout
)

from netscope.core.models import TraceSummary
from netscope.utils.formatters import country_flag, format_route_countries


class LeftSidebar(QDockWidget):
    """Left panel showing route info and recent searches."""

    search_clicked = pyqtSignal(str)  # Re-trace a recent search

    def __init__(self, parent=None):
        super().__init__("Route Info", parent)
        self.setObjectName("leftSidebar")
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 16, 12, 16)

        # Route Info Section
        info_container = QWidget()
        info_container.setObjectName("cardPanel")
        info_layout = QVBoxLayout(info_container)
        
        title = QLabel("🌍 ROUTE INFO")
        title.setObjectName("sidebarTitle")
        info_layout.addWidget(title)

        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(16)
        grid_layout.setVerticalSpacing(8)
        
        self._labels = {}
        fields = [
            ("target", "📍 Target"),
            ("ip", "🔗 IP"),
            ("dns", "📡 DNS"),
            ("hops", "📊 Hops"),
            ("avg_rtt", "⏱️ Avg Latency"),
            ("cloud", "☁️ Cloud"),
        ]

        row = 0
        col = 0
        for key, label_text in fields:
            header = QLabel(label_text)
            header.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            
            grid_layout.addWidget(header, row, col * 2)
            grid_layout.addWidget(value, row, col * 2 + 1)
            
            self._labels[key] = value
            
            col += 1
            if col > 1:
                col = 0
                row += 1

        info_layout.addLayout(grid_layout)
        
        # Add full-width rows for longer text
        full_width_fields = [
            ("isp", "🏢 ISP"),
            ("countries", "🌐 Countries"),
        ]
        
        for key, label_text in full_width_fields:
            row += 1
            header = QLabel(label_text)
            header.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            
            grid_layout.addWidget(header, row, 0)
            grid_layout.addWidget(value, row, 1, 1, 3)  # span across columns
            self._labels[key] = value

        layout.addWidget(info_container)

        # Recent searches Section
        recent_container = QWidget()
        recent_container.setObjectName("cardPanel")
        recent_layout = QVBoxLayout(recent_container)
        
        recent_title = QLabel("🕐 RECENT SEARCHES")
        recent_title.setObjectName("sidebarTitle")
        recent_layout.addWidget(recent_title)

        self._recent_list = QListWidget()
        self._recent_list.setObjectName("recentSearches")
        self._recent_list.setMaximumHeight(200)
        self._recent_list.itemClicked.connect(self._on_search_click)
        recent_layout.addWidget(self._recent_list)

        layout.addWidget(recent_container)
        
        layout.addStretch()
        self.setWidget(container)

    def update_info(self, summary: TraceSummary):
        """Update the sidebar with trace results."""
        self._labels["target"].setText(summary.target)
        self._labels["ip"].setText(summary.resolved_ip)
        self._labels["dns"].setText("<span style='color:#00ff88'>Resolved</span>")
        self._labels["hops"].setText(str(summary.total_hops))
        self._labels["avg_rtt"].setText(f"{summary.avg_latency:.0f} ms")
        self._labels["countries"].setText(
            format_route_countries(summary.countries)
        )

        # Cloud providers
        if summary.cloud_providers:
            self._labels["cloud"].setText(", ".join(summary.cloud_providers))
        else:
            self._labels["cloud"].setText("None")

        # ISP (from first non-timeout hop's network info)
        isp = "Unknown"
        for hop in summary.hops:
            if hop.network and hop.network.isp:
                isp = hop.network.isp
                break
        self._labels["isp"].setText(isp)

    def set_recent_searches(self, searches: list[dict]):
        """Populate the recent searches list."""
        self._recent_list.clear()
        for s in searches:
            item = QListWidgetItem(
                f"  {s['target']}  —  {s.get('avg_latency', 0):.0f}ms"
            )
            item.setData(Qt.ItemDataRole.UserRole, s["target"])
            self._recent_list.addItem(item)

    def _on_search_click(self, item: QListWidgetItem):
        target = item.data(Qt.ItemDataRole.UserRole)
        if target:
            self.search_clicked.emit(target)

    def clear(self):
        """Reset all fields."""
        for label in self._labels.values():
            label.setText("—")
