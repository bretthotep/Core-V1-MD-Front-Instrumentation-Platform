"""Application widget – the 'track title' of the panel."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter

from core.events import Event, EventBus, EventType
from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize


def display_name(process: str | None) -> str:
    if not process:
        return "DESKTOP"
    name = process.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name.upper()


class ApplicationWidget(Widget):
    kind = "application"
    title = "APP"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 70, WidgetSize.EXPANDED: 130}

    SCROLL_PX_PER_S = 28.0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.launch_count = 0
        self.last_event: Event | None = None

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(EventType.APP_LAUNCHED, self._on_event)
        bus.subscribe(EventType.APP_CLOSED, self._on_event)

    def _on_event(self, event: Event) -> None:
        self.last_event = event
        if event.type is EventType.APP_LAUNCHED:
            self.launch_count += 1

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        app = ctx.snapshot.application
        count = len(app.running) if app else 0
        return f"{count:02d} RUN", "dim"

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        app = ctx.snapshot.application
        return display_name(app.foreground if app else None), "secondary"

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme, app = ctx.theme, ctx.snapshot.application
        name = display_name(app.foreground if app else None)
        font = p.display_font(theme, 20)
        width = p.text_width(font, name)
        line = QRectF(rect.left(), rect.top(), rect.width(), 26)
        painter.save()
        painter.setClipRect(line)
        if width <= rect.width():
            p.draw_text(painter, line, name, font, p.colour(theme, "secondary"))
        else:
            # MiniDisc-style title scroll with a gap between repeats.
            gap = 40.0
            offset = (ctx.now * self.SCROLL_PX_PER_S) % (width + gap)
            for start in (rect.left() - offset, rect.left() - offset + width + gap):
                p.draw_text(painter, QRectF(start, line.top(), width + 2, line.height()), name, font, p.colour(theme, "secondary"))
        painter.restore()
        if self.state.expanded and app:
            y = rect.top() + 32
            p.draw_label(painter, QRectF(rect.left(), y, rect.width(), 12), "RUNNING", theme, "primary")
            for i, proc in enumerate(reversed(app.running[-4:])):
                p.draw_label(painter, QRectF(rect.left() + 8, y + 14 + i * 13, rect.width() - 8, 12), display_name(proc), theme, "dim")
        else:
            p.draw_label(
                painter, QRectF(rect.left(), rect.top() + 28, rect.width(), 12),
                f"SESSION {self.launch_count:02d}", theme, "dim", Qt.AlignmentFlag.AlignLeft,
            )
