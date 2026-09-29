"""Memory widget."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize


class RamWidget(Widget):
    kind = "ram"
    title = "RAM"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 70, WidgetSize.EXPANDED: 120}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.history = self.make_history()

    def update(self, snapshot, now) -> None:
        if snapshot.memory:
            self.history.append(snapshot.memory.percent)

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        mem = ctx.snapshot.memory
        return (f"{mem.total_gb:.0f} GB", "dim") if mem else ("", "dim")

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        mem = ctx.snapshot.memory
        return (f"{mem.used_gb:.1f} GB  {mem.percent:.0f}%", "secondary") if mem else (p.NONE_TEXT, "dim")

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme, mem = ctx.theme, ctx.snapshot.memory
        p.draw_value(painter, QRectF(rect.left(), rect.top(), rect.width() * 0.6, 24), p.fmt(mem.used_gb if mem else None, "{:.1f}"), "GB", theme, px=18)
        p.draw_value(
            painter, QRectF(rect.left() + rect.width() * 0.6, rect.top(), rect.width() * 0.4, 24),
            p.fmt(mem.percent if mem else None), "%", theme, px=14, role="primary", align_right=True,
        )
        p.draw_segment_bar(painter, QRectF(rect.left(), rect.top() + 28, rect.width(), 6), (mem.percent / 100) if mem else None, theme, alert_at=0.85)
        if self.state.expanded:
            y = rect.top() + 42
            p.draw_sparkline(painter, QRectF(rect.left(), y, rect.width(), max(10.0, rect.bottom() - y)), list(self.history), theme, 100)
