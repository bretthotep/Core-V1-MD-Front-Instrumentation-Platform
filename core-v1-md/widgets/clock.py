"""Clock widget – the MiniDisc 'time' readout."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFontMetricsF, QPainter

from core.controls import ControlEvent
from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize


class ClockWidget(Widget):
    kind = "clock"
    title = "TIME"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 92, WidgetSize.EXPANDED: 130}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.use_24h = bool(self.config.get("use_24h", True))

    def handle_control(self, event: ControlEvent) -> bool:
        if event is ControlEvent.DOUBLE_PRESS:
            self.use_24h = not self.use_24h
            return True
        return False

    def _hhmm(self, ctx: RenderContext) -> tuple[str, str]:
        t = ctx.wall_time
        if self.use_24h:
            return t.strftime("%H:%M"), ""
        return t.strftime("%I:%M").lstrip("0").rjust(5), t.strftime("%p")

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        return ctx.wall_time.strftime("%a %d %b"), "primary"

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        hhmm, ampm = self._hhmm(ctx)
        return f"{hhmm} {ampm}".strip(), "secondary"

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme = ctx.theme
        hhmm, ampm = self._hhmm(ctx)
        big = p.display_font(theme, min(44.0, rect.width() / 4.2))
        small = p.display_font(theme, 16)
        secs = ctx.wall_time.strftime("%S")
        width = p.text_width(big, hhmm) + 4 + p.text_width(small, secs)
        x = rect.left() + (rect.width() - width) / 2
        baseline = rect.top() + QFontMetricsF(big).capHeight() + 6
        painter.setFont(big)
        painter.setPen(p.colour(theme, "secondary"))
        # Blink the colon like a real deck display.
        colon_on = int(ctx.now * 2) % 2 == 0
        text = hhmm if colon_on else hhmm.replace(":", " ")
        painter.drawText(QPointF(x, baseline), text)
        painter.setFont(small)
        painter.setPen(p.colour(theme, "primary"))
        painter.drawText(QPointF(x + p.text_width(big, hhmm) + 4, baseline), secs)
        if ampm:
            p.draw_label(painter, QRectF(rect.left(), rect.top(), rect.width(), 12), ampm, theme, "primary", Qt.AlignmentFlag.AlignRight)
        if self.state.expanded:
            y = baseline + 14
            p.draw_label(painter, QRectF(rect.left(), y, rect.width(), 14), ctx.wall_time.strftime("%A"), theme, "primary", Qt.AlignmentFlag.AlignCenter)
            p.draw_label(
                painter, QRectF(rect.left(), y + 16, rect.width(), 14),
                ctx.wall_time.strftime("WEEK %V  ·  DAY %j"), theme, "dim", Qt.AlignmentFlag.AlignCenter,
            )
