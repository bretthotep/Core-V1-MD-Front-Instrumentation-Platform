"""Alert widget – surfaces warning and critical application events in amber/red."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter

from core.events import Event, EventBus, EventType
from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize


@dataclass(slots=True)
class ActiveAlert:
    key: str
    message: str
    severity: str  # "alert" (amber) or "critical" (red)
    raised_at: float


class AlertWidget(Widget):
    kind = "alert"
    title = "ALERT"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 62, WidgetSize.EXPANDED: 110}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ttl_s = float(self.config.get("ttl_s", 20.0))
        self.alerts: dict[str, ActiveAlert] = {}

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(None, self.on_event)

    def on_event(self, event: Event) -> None:
        t, data = event.type, event.payload
        if t is EventType.HIGH_TEMP:
            sensor = str(data.get("sensor", "sys")).upper()
            value = data.get("value")
            text = f"{sensor} TEMP {value:.0f}°C" if isinstance(value, int | float) else f"{sensor} TEMP HIGH"
            self._raise(f"temp:{sensor}", text, "critical", event.timestamp)
        elif t is EventType.LOW_FAN_SPEED:
            fan = str(data.get("fan", "FAN")).upper()
            self._raise(f"fan:{fan}", f"{fan} FAN LOW", "alert", event.timestamp)
        elif t is EventType.NETWORK_DISCONNECTED:
            self._raise("net", "NETWORK DOWN", "alert", event.timestamp)
        elif t is EventType.NETWORK_CONNECTED:
            self.alerts.pop("net", None)

    def _raise(self, key: str, message: str, severity: str, now: float) -> None:
        self.alerts[key] = ActiveAlert(key, message, severity, now)

    def expire(self, now: float) -> None:
        self.alerts = {k: a for k, a in self.alerts.items() if now - a.raised_at < self.ttl_s}

    def update(self, snapshot, now) -> None:
        self.expire(now)

    def _ordered(self) -> list[ActiveAlert]:
        return sorted(self.alerts.values(), key=lambda a: (a.severity != "critical", -a.raised_at))

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        if not self.alerts:
            return "NOMINAL", "dim"
        top = self._ordered()[0]
        return f"{len(self.alerts)} ACTIVE", top.severity

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        if not self.alerts:
            return "NOMINAL", "dim"
        top = self._ordered()[0]
        return top.message, top.severity

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme = ctx.theme
        if not self.alerts:
            p.draw_label(painter, QRectF(rect.left(), rect.top(), rect.width(), 16), "ALL SYSTEMS NOMINAL", theme, "dim", Qt.AlignmentFlag.AlignCenter)
            return
        limit = 4 if self.state.expanded else 2
        y = rect.top()
        blink = int(ctx.now * 3) % 2 == 0
        for alert in self._ordered()[:limit]:
            if y + 14 > rect.bottom() + 2:
                break
            marker = QRectF(rect.left(), y + 3, 6, 8)
            if alert.severity != "critical" or blink:
                painter.fillRect(marker, p.colour(theme, alert.severity))
            p.draw_text(painter, QRectF(rect.left() + 12, y, rect.width() - 12, 14), alert.message, p.display_font(theme, 12), p.colour(theme, alert.severity))
            y += 16
