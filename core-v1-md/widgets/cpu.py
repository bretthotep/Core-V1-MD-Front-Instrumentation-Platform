"""CPU widget."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize


class CpuWidget(Widget):
    kind = "cpu"
    title = "CPU"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 104, WidgetSize.EXPANDED: 200}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.history = self.make_history()

    def update(self, snapshot, now) -> None:
        if snapshot.cpu:
            self.history.append(snapshot.cpu.load_percent)

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        cpu = ctx.snapshot.cpu
        if not cpu or cpu.clock_mhz is None:
            return "", "dim"
        return f"{cpu.clock_mhz / 1000:.2f} GHz", "primary"

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        cpu = ctx.snapshot.cpu
        if not cpu:
            return p.NONE_TEXT, "dim"
        return f"{cpu.load_percent:3.0f}%  {p.fmt(cpu.temperature_c)}°C", _temp_role(cpu.temperature_c)

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme, cpu = ctx.theme, ctx.snapshot.cpu
        half = rect.width() / 2
        p.draw_value(painter, QRectF(rect.left(), rect.top(), half, 30), p.fmt(cpu.load_percent if cpu else None), "%", theme)
        temp = cpu.temperature_c if cpu else None
        p.draw_value(
            painter, QRectF(rect.left() + half, rect.top(), half, 30), p.fmt(temp), "°C", theme,
            role=_temp_role(temp), align_right=True,
        )
        p.draw_segment_bar(painter, QRectF(rect.left(), rect.top() + 38, rect.width(), 9), (cpu.load_percent / 100) if cpu else None, theme)
        y = rect.top() + 54
        p.draw_label(painter, QRectF(rect.left(), y, half, 12), "PKG " + p.fmt(cpu.power_w if cpu else None) + " W", theme)
        if not self.state.expanded:
            return
        cores = cpu.core_loads if cpu else ()
        y += 18
        if cores:
            col_w = rect.width() / len(cores)
            for i, load in enumerate(cores):
                p.draw_vertical_segment_bar(
                    painter, QRectF(rect.left() + i * col_w + 1, y, col_w - 3, 44), load / 100, theme, 10
                )
            y += 50
        p.draw_sparkline(painter, QRectF(rect.left(), y, rect.width(), max(10.0, rect.bottom() - y)), list(self.history), theme, 100)


def _temp_role(temp: float | None) -> str:
    if temp is None:
        return "dim"
    if temp >= 90:
        return "critical"
    if temp >= 80:
        return "alert"
    return "secondary"
