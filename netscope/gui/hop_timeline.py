"""
Hop Timeline Widget

Custom-painted horizontal timeline showing hops as connected circles.
Each hop displays latency with color-coded bars.
Clicking a hop selects it and emits a signal for the detail drawer.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PyQt6.QtWidgets import QScrollArea, QWidget

from netscope.core.models import Hop
from netscope.utils.formatters import latency_color


class HopTimelineCanvas(QWidget):
    """Custom-painted canvas for the hop timeline."""

    hop_selected = pyqtSignal(int)  # Emits hop index

    HOP_RADIUS = 16
    HOP_SPACING = 120
    MARGIN = 40
    HEIGHT = 120

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hops: list[Hop] = []
        self._selected_index = -1
        self.setMinimumHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_hops(self, hops: list[Hop]):
        """Set the hops to display."""
        self._hops = hops
        self._selected_index = -1
        width = max(
            self.MARGIN * 2 + len(hops) * self.HOP_SPACING,
            self.parent().width() if self.parent() else 400,
        )
        self.setMinimumWidth(width)
        self.update()

    def add_hop(self, hop: Hop):
        """Add a single hop (for real-time updates)."""
        self._hops.append(hop)
        width = self.MARGIN * 2 + len(self._hops) * self.HOP_SPACING
        self.setMinimumWidth(width)
        self.update()

    def clear(self):
        self._hops = []
        self._selected_index = -1
        self.update()

    def mousePressEvent(self, event):
        """Handle click to select a hop."""
        x = event.position().x()
        for i, _ in enumerate(self._hops):
            cx = self.MARGIN + i * self.HOP_SPACING
            if abs(x - cx) < self.HOP_RADIUS + 5:
                self._selected_index = i
                self.hop_selected.emit(i)
                self.update()
                return

    def paintEvent(self, event):
        """Paint the timeline."""
        if not self._hops:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cy = self.HEIGHT // 2  # Vertical center

        # Draw connecting lines first
        for i in range(len(self._hops) - 1):
            x1 = self.MARGIN + i * self.HOP_SPACING
            x2 = self.MARGIN + (i + 1) * self.HOP_SPACING
            color = QColor(latency_color(self._hops[i + 1].avg_rtt))
            color.setAlpha(100)
            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.drawLine(int(x1), int(cy), int(x2), int(cy))

        # Draw hops
        for i, hop in enumerate(self._hops):
            cx = self.MARGIN + i * self.HOP_SPACING
            color = QColor(latency_color(hop.avg_rtt))
            is_selected = (i == self._selected_index)

            # Glow for selected hop
            if is_selected:
                glow_color = QColor(color)
                glow_color.setAlpha(60)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow_color)
                painter.drawEllipse(
                    int(cx - self.HOP_RADIUS - 6), int(cy - self.HOP_RADIUS - 6),
                    int((self.HOP_RADIUS + 6) * 2), int((self.HOP_RADIUS + 6) * 2),
                )

            # Main circle
            painter.setPen(QPen(QColor("#ffffff"), 1.5 if is_selected else 0.5))
            painter.setBrush(color)
            painter.drawEllipse(
                int(cx - self.HOP_RADIUS), int(cy - self.HOP_RADIUS),
                int(self.HOP_RADIUS * 2), int(self.HOP_RADIUS * 2),
            )

            # Hop number inside circle
            painter.setPen(QColor("#ffffff"))
            font = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - self.HOP_RADIUS, cy - self.HOP_RADIUS,
                       self.HOP_RADIUS * 2, self.HOP_RADIUS * 2),
                Qt.AlignmentFlag.AlignCenter,
                str(hop.hop_number),
            )

            if not hop.is_timeout and hop.avg_rtt >= 0:
                latency_text = f"{hop.avg_rtt:.0f}ms"
                painter.setPen(QColor(latency_color(hop.avg_rtt)))
            else:
                latency_text = "TIMEOUT"
                painter.setPen(QColor("#FF6666"))

            font = QFont("Consolas", 8)
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - 40, cy + self.HOP_RADIUS + 4, 80, 16),
                Qt.AlignmentFlag.AlignCenter,
                latency_text,
            )

            # Location above the circle (if available)
            location = ""
            if hop.geo and hop.geo.city:
                location = hop.geo.city
            elif hop.geo and hop.geo.country_code:
                location = hop.geo.country_code

            if location:
                font = QFont("Consolas", 8)
                painter.setFont(font)
                painter.setPen(QColor("#888888"))
                painter.drawText(
                    QRectF(cx - 50, cy - self.HOP_RADIUS - 20, 100, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    location,
                )

        painter.end()


class HopTimeline(QScrollArea):
    """Scrollable hop timeline widget."""

    hop_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hopTimeline")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMaximumHeight(130)
        self.setWidgetResizable(True)

        self._canvas = HopTimelineCanvas(self)
        self._canvas.hop_selected.connect(self.hop_selected)
        self.setWidget(self._canvas)

    def set_hops(self, hops: list[Hop]):
        self._canvas.set_hops(hops)

    def add_hop(self, hop: Hop):
        self._canvas.add_hop(hop)
        # Auto-scroll to latest hop
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().maximum()
        )

    def clear(self):
        self._canvas.clear()
