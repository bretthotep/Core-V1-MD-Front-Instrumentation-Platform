"""GPU widget."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize
from widgets.cpu import _temp_role


class GpuWidget(Widget):
    kind = "gpu"
    title = "GPU"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 104, WidgetSize.EXPANDED: 170}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.history = self.make_history()

    def update(self, snapshot, now) -> None:
        if snapshot.gpu:
            self.history.append(snapshot.gpu.load_percent)

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        gpu = ctx.snapshot.gpu
        if not gpu or gpu.clock_mhz is None:
            return "", "dim"
        return f"{gpu.clock_mhz:.0f} MHz", "primary"

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        gpu = ctx.snapshot.gpu
        if not gpu:
            return p.NONE_TEXT, "dim"
        return f"{gpu.load_percent:3.0f}%  {p.fmt(gpu.temperature_c)}°C", _temp_role(gpu.temperature_c)

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme, gpu = ctx.theme, ctx.snapshot.gpu
        half = rect.width() / 2
        p.draw_value(painter, QRectF(rect.left(), rect.top(), half, 30), p.fmt(gpu.load_percent if gpu else None), "%", theme)
        temp = gpu.temperature_c if gpu else None
        p.draw_value(
            painter, QRectF(rect.left() + half, rect.top(), half, 30), p.fmt(temp), "°C", theme,
            role=_temp_role(temp), align_right=True,
        )
        p.draw_segment_bar(painter, QRectF(rect.left(), rect.top() + 38, rect.width(), 9), (gpu.load_percent / 100) if gpu else None, theme)
        y = rect.top() + 54
        vram = None
        if gpu and gpu.vram_used_mb is not None and gpu.vram_total_mb:
            vram = gpu.vram_used_mb / gpu.vram_total_mb
        p.draw_label(painter, QRectF(rect.left(), y, 40, 12), "VRAM", theme)
        p.draw_segment_bar(painter, QRectF(rect.left() + 42, y + 3, rect.width() - 42, 5), vram, theme, alert_at=0.9, critical_at=None)
        if not self.state.expanded:
            return
        y += 18
        fan = p.fmt(gpu.fan_rpm if gpu else None)
        power = p.fmt(gpu.power_w if gpu else None)
        p.draw_label(painter, QRectF(rect.left(), y, rect.width(), 12), f"FAN {fan} RPM   BOARD {power} W", theme)
        y += 18
        p.draw_sparkline(painter, QRectF(rect.left(), y, rect.width(), max(10.0, rect.bottom() - y)), list(self.history), theme, 100)
