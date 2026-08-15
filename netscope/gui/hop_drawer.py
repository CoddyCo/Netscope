"""
Hop Detail Drawer

Shows detailed information about a selected hop.
Terminal-style monospaced display.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget, QLabel, QVBoxLayout, QWidget, QScrollArea,
)

from netscope.core.models import Hop
from netscope.utils.formatters import (
    country_flag, format_ip, format_latency, latency_color,
)


class HopDrawer(QDockWidget):
    """Hop detail panel with terminal-style display."""

    def __init__(self, parent=None):
        super().__init__("Hop Details", parent)
        self.setObjectName("hopDrawer")
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(2)

        title = QLabel("🔍 HOP DETAILS")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        self._detail_label = QLabel("Select a hop from the timeline")
        self._detail_label.setObjectName("hopDetailText")
        self._detail_label.setWordWrap(True)
        self._detail_label.setTextFormat(Qt.TextFormat.RichText)
        self._detail_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._detail_label)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(scroll)
        self.setWidget(container)

    def show_hop(self, hop: Hop):
        """Display detailed information about a hop."""
        color = latency_color(hop.avg_rtt)

        lines = []
        lines.append(f"<b style='color:{color}'>═══ Hop {hop.hop_number} ═══</b>")
        lines.append("")

        if hop.is_timeout:
            lines.append("<span style='color:#FF4444'>✕ All probes timed out (* * *)</span>")
        else:
            # IP and hostname
            lines.append(f"<b>IP:</b> {hop.ip}")
            if hop.hostname:
                lines.append(f"<b>Hostname:</b> {hop.hostname}")

            # Geographic info
            if hop.geo:
                flag = country_flag(hop.geo.country_code) if hop.geo.country_code else "🌍"
                location_parts = []
                if hop.geo.city:
                    location_parts.append(hop.geo.city)
                if hop.geo.country:
                    location_parts.append(hop.geo.country)
                if location_parts:
                    lines.append(f"<b>Location:</b> {flag} {', '.join(location_parts)}")
                if hop.geo.latitude != 0 or hop.geo.longitude != 0:
                    lines.append(
                        f"<b>Coords:</b> {hop.geo.latitude:.4f}, {hop.geo.longitude:.4f}"
                    )

            # Network info
            if hop.network:
                if hop.network.asn:
                    lines.append(f"<b>ASN:</b> AS{hop.network.asn}")
                if hop.network.isp:
                    lines.append(f"<b>ISP:</b> {hop.network.isp}")

            # Cloud info
            if hop.cloud:
                lines.append(f"<b>Cloud:</b> ☁️ {hop.cloud.provider}")
                if hop.cloud.region:
                    lines.append(f"<b>Region:</b> {hop.cloud.region}")
                if hop.cloud.service:
                    lines.append(f"<b>Service:</b> {hop.cloud.service}")

            lines.append("")
            lines.append(f"<b style='color:{color}'>── Latency ──</b>")

            # RTTs
            rtt_strs = []
            for rtt in hop.rtts:
                if rtt < 0:
                    rtt_strs.append("<span style='color:#FF4444'>*</span>")
                else:
                    rtt_strs.append(f"{rtt:.1f}ms")
            lines.append(f"<b>Probes:</b> {' / '.join(rtt_strs)}")

            lines.append(f"<b>Avg:</b> <span style='color:{color}'>{hop.avg_rtt:.1f}ms</span>")
            lines.append(f"<b>Min:</b> {hop.min_rtt:.1f}ms")
            lines.append(f"<b>Max:</b> {hop.max_rtt:.1f}ms")

            if hop.packet_loss > 0:
                lines.append(
                    f"<b>Loss:</b> <span style='color:#FF8800'>{hop.packet_loss:.0f}%</span>"
                )

        self._detail_label.setText("<br>".join(lines))

    def clear(self):
        self._detail_label.setText("Select a hop from the timeline")
