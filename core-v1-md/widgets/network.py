"""Network widget."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize


class NetworkWidget(Widget):
    kind = "network"
    title = "NET"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 96, WidgetSize.EXPANDED: 150}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.down_history = self.make_history()
        self.up_history = self.make_history()

    def update(self, snapshot, now) -> None:
        if snapshot.network:
            self.down_history.append(snapshot.network.down_bps)
            self.up_history.append(snapshot.network.up_bps)

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        net = ctx.snapshot.network
        if not net:
            return "", "dim"
        return (net.adapter, "primary") if net.connected else ("NO LINK", "alert")

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        net = ctx.snapshot.network
        if not net or not net.connected:
            return "NO LINK", "alert"
        d, du = p.fmt_rate(net.down_bps)
        u, uu = p.fmt_rate(net.up_bps)
        return f"▼{d}{du[0]} ▲{u}{uu[0]}", "secondary"

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme, net = ctx.theme, ctx.snapshot.network
        half = rect.width() / 2
        down = p.fmt_rate(net.down_bps if net else None)
        up = p.fmt_rate(net.up_bps if net else None)
        role = "secondary" if net and net.connected else "alert"
        p.draw_label(painter, QRectF(rect.left(), rect.top(), half, 10), "▼ DOWN", theme)
        p.draw_label(painter, QRectF(rect.left() + half, rect.top(), half, 10), "▲ UP", theme)
        p.draw_value(painter, QRectF(rect.left(), rect.top() + 12, half, 22), down[0], down[1], theme, px=17, role=role)
        p.draw_value(painter, QRectF(rect.left() + half, rect.top() + 12, half, 22), up[0], up[1], theme, px=17, role=role)
        y = rect.top() + 40
        graph_h = rect.bottom() - y - (16 if self.state.expanded else 0)
        peak = max([*self.down_history, 1.0])
        p.draw_sparkline(painter, QRectF(rect.left(), y, rect.width(), max(8.0, graph_h)), list(self.down_history), theme, peak)
        if self.state.expanded and net:
            p.draw_label(painter, QRectF(rect.left(), rect.bottom() - 12, rect.width(), 12), net.address or "NO ADDRESS", theme)
