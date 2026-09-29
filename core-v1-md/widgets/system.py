"""System widget: host, uptime, fans and board temperature."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter

from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize

FAN_FULL_SCALE_RPM = 2000.0


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
        if not self.state.expanded:
            fans = fans[:2]
        for fan in fans:
            p.draw_label(painter, QRectF(rect.left(), y, 44, 10), fan.name, theme)
            role = "critical" if fan.rpm <= 0 else "primary"
            p.draw_segment_bar(painter, QRectF(rect.left() + 46, y + 2, rect.width() - 100, 6), fan.rpm / FAN_FULL_SCALE_RPM, theme, alert_at=None, critical_at=None, role=role)
            p.draw_label(painter, QRectF(rect.right() - 52, y, 52, 10), f"{fan.rpm:.0f}", theme, "secondary", Qt.AlignmentFlag.AlignRight)
            y += 14
        if self.state.expanded and sys_:
            p.draw_label(
                painter, QRectF(rect.left(), y + 4, rect.width(), 12),
                f"BOARD {p.fmt(sys_.board_temperature_c)} °C", theme, "dim",
            )
