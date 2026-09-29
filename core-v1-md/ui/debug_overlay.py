"""Optional debug overlay (toggle with F1 in the simulator)."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from themes.theme import Theme
from ui.layout import Layout
from widgets import primitives as p

DEBUG_COLOUR = "#FF00FF"


@dataclass(slots=True)
class DebugInfo:
    fps: float = 0.0
    frame_ms: float = 0.0
    display: str = ""
    last_control: str = ""
    last_event: str = ""
    animations: int = 0
    lines: list[str] = field(default_factory=list)


def draw_debug_overlay(painter: QPainter, screen: QRectF, layout: Layout, theme: Theme, info: DebugInfo) -> None:
    painter.save()
    pen = QPen(QColor(DEBUG_COLOUR))
    pen.setWidthF(1)
    pen.setStyle(Qt.PenStyle.DashLine)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    font = p.display_font(theme, 9)
    for item in layout.items:
        painter.drawRect(item.rect.adjusted(0.5, 0.5, -0.5, -0.5))
        painter.setFont(font)
        painter.drawText(
            item.rect.adjusted(4, 0, -4, -2),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom),
            f"{item.slot.widget.id} {item.slot.widget.state.size.value} {item.rect.height():.0f}px",
        )
    painter.setPen(QPen(QColor(DEBUG_COLOUR), 1))
    painter.drawLine(0, int(layout.flow_region.top()), int(screen.width()), int(layout.flow_region.top()))

    lines = [
        f"{screen.width():.0f}x{screen.height():.0f} {info.display}",
        f"{info.fps:5.1f} fps  {info.frame_ms:4.1f} ms",
        f"theme {theme.id}",
        f"anim {info.animations}",
        f"ctl {info.last_control}",
        f"evt {info.last_event}",
        *info.lines,
    ]
    box = QRectF(4, screen.height() - 14 * len(lines) - 8, screen.width() - 8, 14 * len(lines) + 4)
    painter.fillRect(box, QColor(0, 0, 0, 200))
    painter.setFont(font)
    for i, line in enumerate(lines):
        painter.drawText(QRectF(box.left() + 4, box.top() + 2 + i * 14, box.width() - 8, 14), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), line)
    painter.restore()
