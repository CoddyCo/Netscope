"""
Right Sidebar — Health Score & Statistics Panel

Displays network health score, latency statistics,
packet loss, and connection breakdown.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget, QLabel, QProgressBar, QVBoxLayout, QWidget, QGridLayout
)

from netscope.core.models import ConnectionBreakdown, TraceSummary
from netscope.utils.formatters import format_mbps


class RightSidebar(QDockWidget):
    """Right panel showing health score and diagnostic metrics."""

    def __init__(self, parent=None):
        super().__init__("Diagnostics", parent)
        self.setObjectName("rightSidebar")
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 16, 12, 16)

        # Health Score Section
        health_container = QWidget()
        health_container.setObjectName("cardPanel")
        health_layout = QVBoxLayout(health_container)
        
        title = QLabel("🏥 HEALTH SCORE")
        title.setObjectName("sidebarTitle")
        health_layout.addWidget(title)

        self._score_label = QLabel("—")
        self._score_label.setObjectName("healthScore")
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        health_layout.addWidget(self._score_label)

        self._rating_label = QLabel("")
        self._rating_label.setObjectName("healthRating")
        self._rating_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        health_layout.addWidget(self._rating_label)

        self._score_bar = QProgressBar()
        self._score_bar.setObjectName("healthBar")
        self._score_bar.setRange(0, 100)
        self._score_bar.setValue(0)
        self._score_bar.setTextVisible(False)
        self._score_bar.setMaximumHeight(8)
        health_layout.addWidget(self._score_bar)
        
        self._breakdown_label = QLabel("")
        self._breakdown_label.setStyleSheet("color: #8892b0; font-size: 11px;")
        self._breakdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._breakdown_label.setWordWrap(True)
        health_layout.addWidget(self._breakdown_label)
        
        layout.addWidget(health_container)

        # Statistics Section
        stats_container = QWidget()
        stats_container.setObjectName("cardPanel")
        stats_layout = QVBoxLayout(stats_container)
        
        stats_title = QLabel("📊 STATISTICS")
        stats_title.setObjectName("sidebarTitle")
        stats_layout.addWidget(stats_title)

        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(16)
        grid_layout.setVerticalSpacing(8)
        
        self._stat_labels = {}
        stats = [
            ("avg_latency", "⏱️ Avg Latency"),
            ("max_latency", "📈 Max Latency"),
            ("min_latency", "📉 Min Latency"),
            ("packet_loss", "📦 Packet Loss"),
            ("bandwidth", "🚀 Bandwidth"),
        ]

        row = 0
        col = 0
        for key, label_text in stats:
            header = QLabel(label_text)
            header.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setObjectName("fieldValue")
            
            grid_layout.addWidget(header, row, col * 2)
            grid_layout.addWidget(value, row, col * 2 + 1)
            
            self._stat_labels[key] = value
            
            col += 1
            if col > 1:
                col = 0
                row += 1

        stats_layout.addLayout(grid_layout)
        layout.addWidget(stats_container)

        # Connection Breakdown Section
        conn_container = QWidget()
        conn_container.setObjectName("cardPanel")
        conn_layout = QVBoxLayout(conn_container)
        
        conn_title = QLabel("📡 CONNECTION PROFILING")
        conn_title.setObjectName("sidebarTitle")
        conn_layout.addWidget(conn_title)

        conn_grid = QGridLayout()
        conn_grid.setHorizontalSpacing(16)
        conn_grid.setVerticalSpacing(8)
        
        self._conn_labels = {}
        conn_fields = [
            ("dns", "🌐 DNS Lookup"),
            ("tcp", "🤝 TCP Connect"),
            ("tls", "🔐 TLS Handshake"),
            ("ttfb", "⏱️ Time to First Byte"),
            ("total", "🏁 Total Time"),
        ]

        row = 0
        for key, label_text in conn_fields:
            header = QLabel(label_text)
            header.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setObjectName("connValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            conn_grid.addWidget(header, row, 0)
            conn_grid.addWidget(value, row, 1)
            
            self._conn_labels[key] = value
            row += 1

        conn_layout.addLayout(conn_grid)
        layout.addWidget(conn_container)

        layout.addStretch()
        self.setWidget(container)

    def update_stats(self, summary: TraceSummary):
        """Update all metrics from a completed trace."""
        # Health score
        health = summary.health
        if not health:
            return

        score = health.score
        self._score_label.setText(f"{score}/100")
        self._rating_label.setText(health.rating)
        self._score_bar.setValue(score)

        # Build breakdown string
        breakdown = []
        if health.packet_loss_penalty < 0:
            breakdown.append(f"Loss {health.packet_loss_penalty}")
        if health.latency_penalty < 0:
            breakdown.append(f"Latency {health.latency_penalty}")
        if health.jitter_penalty < 0:
            breakdown.append(f"Jitter {health.jitter_penalty}")
        if health.timeout_penalty < 0:
            breakdown.append(f"Timeouts {health.timeout_penalty}")
        if health.hop_loss_penalty < 0:
            breakdown.append(f"Hop Loss {health.hop_loss_penalty}")
            
        if not breakdown:
            self._breakdown_label.setText("Perfect connection")
        else:
            self._breakdown_label.setText("Deductions: " + ", ".join(breakdown))

        # Color the score
        if score >= 80:
            color = "#00FF88"
        elif score >= 60:
            color = "#FFBB00"
        else:
            color = "#FF4444"
        self._score_label.setStyleSheet(f"color: {color}; font-size: 42px; font-weight: bold; margin: 10px 0;")

        # Statistics
        self._stat_labels["avg_latency"].setText(f"{summary.avg_latency:.0f} ms")
        self._stat_labels["max_latency"].setText(f"{summary.max_latency:.0f} ms")
        self._stat_labels["min_latency"].setText(f"{summary.min_latency:.0f} ms")
        self._stat_labels["packet_loss"].setText(f"{summary.packet_loss:.1f}%")

        if summary.bandwidth:
            self._stat_labels["bandwidth"].setText(
                format_mbps(summary.bandwidth.download_mbps)
            )

    def update_connection(self, conn: ConnectionBreakdown):
        """Update connection breakdown."""
        def fmt(ms: float) -> str:
            if ms < 0:
                return "❌ Failed"
            if ms < 30:
                return f"<span style='color:#00ff88'>{ms:.0f}ms</span>"
            if ms < 100:
                return f"<span style='color:#ffbb00'>{ms:.0f}ms</span>"
            return f"<span style='color:#ff4444'>{ms:.0f}ms</span>"

        self._conn_labels["dns"].setText(fmt(conn.dns_ms))
        self._conn_labels["tcp"].setText(fmt(conn.tcp_ms))
        
        tls_text = fmt(conn.tls_ms)
        if conn.tls_version:
            tls_text += f" <span style='color:#8892b0; font-size:10px'>({conn.tls_version})</span>"
        self._conn_labels["tls"].setText(tls_text)
        
        self._conn_labels["ttfb"].setText(fmt(conn.ttfb_ms))
        self._conn_labels["total"].setText(f"<b>{conn.total_ms:.0f}ms</b>")

    def clear(self):
        """Reset all fields."""
        self._score_label.setText("—")
        self._rating_label.setText("")
        self._score_bar.setValue(0)
        self._breakdown_label.setText("")
        self._score_label.setStyleSheet("")
        for label in self._stat_labels.values():
            label.setText("—")
        for label in self._conn_labels.values():
            label.setText("—")
