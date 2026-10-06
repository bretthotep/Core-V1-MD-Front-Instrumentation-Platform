"""System widget: host, uptime, fans and board temperature."""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFontMetricsF, QPainter

from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize

FAN_FULL_SCALE_RPM = 2000.0
FAN_ROW_HEIGHT = 18


class SystemWidget(Widget):
    kind = "system"
    title = "SYS"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 96, WidgetSize.EXPANDED: 140}

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        sys_ = ctx.snapshot.system
        return (sys_.hostname, "primary") if sys_ else ("", "dim")

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        sys_ = ctx.snapshot.system
        return ("UP " + p.fmt_duration(sys_.uptime_s), "secondary") if sys_ else (p.NONE_TEXT, "dim")

    def render(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        painter.save()
        painter.setClipRect(rect, Qt.ClipOperation.IntersectClip)
        if self.state.collapsed:
            pad = ctx.theme.metric("padding", 10)
            inner = rect.adjusted(pad, 5, -pad, -5)
            fans = ctx.snapshot.system.fans if ctx.snapshot.system else ()
            extra = len(fans) - 1
            if extra > 0:
                p.draw_label(painter, QRectF(inner.right() - 30, inner.top(), 30, 18),
                             f"+{extra}", ctx.theme, "dim", Qt.AlignmentFlag.AlignRight, px=8)
                inner.adjust(0, 0, -34, 0)
            self._fan_row(painter, inner, fans[0] if fans else None, ctx, meter=False)
        else:
            super().render(painter, rect, ctx)
        painter.restore()

    @staticmethod
    def _fan_row(painter: QPainter, rect: QRectF, fan, ctx: RenderContext, *, meter: bool = True) -> None:
        theme = ctx.theme
        rpm = fan.rpm if fan else None
        valid = rpm is not None and math.isfinite(rpm) and rpm >= 0
        role = "critical" if valid and rpm == 0 else "primary" if valid else "dim"
        p.draw_fan_icon(painter, QRectF(rect.left(), rect.top(), 14, 14), theme, role)
        value = f"{rpm:.0f} RPM" if valid else "-- RPM"
        font = p.label_font(theme, 8)
        value_width = min(rect.width() * 0.55, p.text_width(font, value) + 2)
        name_rect = QRectF(rect.left() + 19, rect.top(), max(0, rect.width() - value_width - 23), 12)
        value_rect = QRectF(rect.right() - value_width, rect.top(), value_width, 12)
        value_font = font
        if rect.width() < 100:
            name_rect = QRectF(rect.left() + 19, rect.top(), max(0, rect.width() - 19), 9)
            value_rect = QRectF(name_rect.left(), rect.top() + 9, name_rect.width(), 9)
            value_font = p.display_font(theme, 8)
        name = QFontMetricsF(font).elidedText(fan.name if fan else "FANS", Qt.TextElideMode.ElideRight,
                                            name_rect.width())
        p.draw_text(painter, name_rect, name.upper(), font, p.colour(theme, role))
        painter.save()
        painter.setClipRect(value_rect, Qt.ClipOperation.IntersectClip)
        p.draw_text(painter, value_rect, value, value_font, p.colour(theme, "secondary" if valid else "dim"),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        painter.restore()
        if meter and rect.width() >= 100:
            p.draw_segment_bar(painter, QRectF(rect.left() + 19, rect.top() + 14, rect.width() - 19, 2),
                               rpm / FAN_FULL_SCALE_RPM if valid else None, theme,
                               alert_at=None, critical_at=None, role=role)

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme, sys_ = ctx.theme, ctx.snapshot.system
        p.draw_label(painter, QRectF(rect.left(), rect.top(), 40, 18), "UPTIME", theme)
        p.draw_text(
            painter, QRectF(rect.left(), rect.top(), rect.width(), 18),
            p.fmt_duration(sys_.uptime_s) if sys_ else p.NONE_TEXT, p.display_font(theme, 15),
            p.colour(theme, "secondary"), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        y = rect.top() + 24
        fans = sys_.fans if sys_ else ()
        board_height = 16 if self.state.expanded else 0
        available = max(0, rect.bottom() - y - board_height)
        capacity = int(available // FAN_ROW_HEIGHT)
        if len(fans) > capacity:
            capacity = max(0, int((available - 12) // FAN_ROW_HEIGHT))
        shown = fans[:capacity]
        for fan in shown:
            self._fan_row(painter, QRectF(rect.left(), y, rect.width(), FAN_ROW_HEIGHT), fan, ctx)
            y += FAN_ROW_HEIGHT
        if not fans and capacity:
            self._fan_row(painter, QRectF(rect.left(), y, rect.width(), FAN_ROW_HEIGHT), None, ctx)
        if len(fans) > len(shown):
            p.draw_label(painter, QRectF(rect.left(), y, rect.width(), 12),
                         f"+{len(fans) - len(shown)} MORE FANS", theme, "dim", px=8)
        if self.state.expanded:
            p.draw_label(
                painter, QRectF(rect.left(), rect.bottom() - 12, rect.width(), 12),
                f"BOARD {p.fmt(sys_.board_temperature_c if sys_ else None)} °C", theme, "dim",
            )
