"""
Diagnosis Panel

Displays the auto-diagnosis results:
- Root cause
- Bottleneck list
- Recommendations
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget, QLabel, QVBoxLayout, QWidget, QScrollArea,
)

from netscope.core.models import Diagnosis


class DiagnosisPanel(QDockWidget):
    """Panel showing automated network diagnosis."""

    def __init__(self, parent=None):
        super().__init__("Diagnosis", parent)
        self.setObjectName("diagnosisPanel")
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(4)

        title = QLabel("🏥 DIAGNOSIS")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        self._content = QLabel("Run a trace to see diagnosis")
        self._content.setObjectName("diagnosisContent")
        self._content.setWordWrap(True)
        self._content.setTextFormat(Qt.TextFormat.RichText)
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._content)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(scroll)
        self.setWidget(container)

    def update_diagnosis(self, diagnosis: Diagnosis):
        """Display the diagnosis results."""
        lines = []

        # Severity indicator
        if diagnosis.severity == "critical":
            icon = "🔴"
            color = "#FF4444"
        elif diagnosis.severity == "warning":
            icon = "🟡"
            color = "#FFBB00"
        else:
            icon = "🟢"
            color = "#00FF88"

        lines.append(f"<b style='color:{color}'>{icon} {diagnosis.root_cause}</b>")
        lines.append("")
        lines.append(diagnosis.description)

        # Bottlenecks
        if diagnosis.bottlenecks:
            lines.append("")
            lines.append("<b style='color:#00CCFF'>── Bottlenecks ──</b>")
            for b in diagnosis.bottlenecks[:3]:  # Top 3
                lines.append(
                    f"  🔸 Hop {b.hop_number} "
                    f"({b.hop_location or b.hop_ip}): "
                    f"+{b.latency_jump_ms:.0f}ms "
                    f"({b.percentage_of_total:.0f}% of total)"
                )

        # Recommendations
        if diagnosis.recommendations:
            lines.append("")
            lines.append("<b style='color:#00CCFF'>── Recommendations ──</b>")
            for i, rec in enumerate(diagnosis.recommendations[:4], 1):
                lines.append(f"  💡 {rec}")

        self._content.setText("<br>".join(lines))

    def clear(self):
        self._content.setText("Run a trace to see diagnosis")
