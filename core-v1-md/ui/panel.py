"""FrontPanel – the display-agnostic application core.

Wires together every layer::

    TelemetryProviders ─► TelemetryHub ─► snapshot ─► Widgets ─┐
            │                               │                   ├─► Compositor ─► QImage ─► DisplayDevice
            └── events ─► EventBus ─► AnimationDirector ─► AnimationEngine ┘
    InputDevice ─► ControlEvent ─► WidgetManager

The same object drives the simulator window today and the physical OLED
strip later; only the :class:`~display.device.DisplayDevice` and input
source differ.
"""

from __future__ import annotations

import datetime as _dt
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtGui import QImage

from animations.director import AnimationDirector
from animations.engine import AnimationEngine
from animations.profiles import ProfileLibrary
from animations.types import HorizontalWipe
from core.controls import ControlEvent
from core.events import Event, EventBus, EventType
from display.device import DisplayDevice
from telemetry.hub import TelemetryHub
from themes.theme import ThemeManager
from ui.compositor import Compositor
from ui.debug_overlay import DebugInfo
from ui.layout_store import LayoutStateStore
from ui.manager import WidgetManager
from widgets.base import Widget
from widgets.registry import create_widgets

DEFAULT_LAYOUT = Path(__file__).resolve().parent / "default_layout.json"


def load_layout(path: Path | str = DEFAULT_LAYOUT) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class FrontPanel:
    def __init__(
        self,
        display: DisplayDevice,
        hub: TelemetryHub,
        bus: EventBus | None = None,
        themes: ThemeManager | None = None,
        layout: dict[str, Any] | None = None,
        profiles: ProfileLibrary | None = None,
        telemetry_interval_s: float = 0.5,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], _dt.datetime] = _dt.datetime.now,
        state_store: LayoutStateStore | None = None,
    ) -> None:
        self.display = display
        self.hub = hub
        self.bus = bus or hub.bus
        self.themes = themes or ThemeManager()
        self.clock = clock
        self.wall_clock = wall_clock
        self.perf_clock: Callable[[], float] = time.perf_counter  # render timing for the debug overlay
        self.telemetry_interval_s = telemetry_interval_s

        layout = layout or load_layout()
        widgets: list[Widget] = create_widgets(layout["widgets"])
        for widget in widgets:
            widget.attach(self.bus)
        self.engine = AnimationEngine()
        self.manager = WidgetManager(
            widgets, float(layout.get("rotation_interval_s", 6.0)), on_rotate=self._on_rotate
        )
        self.state_store = state_store
        if state_store is not None:
            saved = state_store.load()
            if saved is not None:
                self.manager.apply_state(saved)
        self._saved_state = self.manager.export_state()
        self.director = AnimationDirector(self.bus, self.engine, profiles or ProfileLibrary.load(), lambda: self.themes.active)
        self.compositor = Compositor(self.manager, self.themes, self.engine)

        self.debug_info = DebugInfo(display=display.name)
        self.bus.subscribe(None, self._record_event)
        self._last_frame: float | None = None
        self._last_poll: float | None = None
        self._fps = 0.0
        self.running = False

    # ---- lifecycle -------------------------------------------------------------
    def start(self) -> None:
        self.display.open()
        self.hub.start()
        self._poll(self.clock())
        self.bus.dispatch_pending()  # swallow baseline state; nothing should animate before boot
        self.running = True
        self.bus.emit(EventType.SYSTEM_START)

    def stop(self) -> None:
        if not self.running:
            return
        self.bus.emit(EventType.SYSTEM_SHUTDOWN)
        self.running = False
        self.persist_layout()
        self.hub.stop()
        self.display.close()

    # ---- input ----------------------------------------------------------------
    def handle_control(self, event: ControlEvent) -> str:
        action = self.manager.handle(event)
        self.debug_info.last_control = f"{event.name} → {action}"
        self.persist_layout()
        return action

    def persist_layout(self) -> bool:
        """Save layout state if a store is configured and the state changed."""
        if self.state_store is None:
            return False
        state = self.manager.export_state()
        if state == self._saved_state:
            return False
        if self.state_store.save(state):
            self._saved_state = state
            return True
        return False

    # ---- frame loop ---------------------------------------------------------------
    def step(self, now: float | None = None) -> QImage:
        """Advance one frame and present it. Returns the rendered frame."""
        now = self.clock() if now is None else now
        dt = 0.0 if self._last_frame is None else max(0.0, now - self._last_frame)
        self._last_frame = now
        if dt > 0:
            self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt) if self._fps else 1.0 / dt

        if self._last_poll is None or now - self._last_poll >= self.telemetry_interval_s:
            self._poll(now)
        else:
            self.hub.poll_audio(now)
        self.bus.dispatch_pending()
        self.manager.tick(now, dt)
        self.engine.tick(dt * 1000.0)

        started = self.perf_clock()
        self.debug_info.fps = self._fps
        self.debug_info.animations = len(self.engine.active)
        frame = self.compositor.render(self.display.size, self.hub.snapshot, now, self.wall_clock(), self.debug_info)
        self.debug_info.frame_ms = (self.perf_clock() - started) * 1000.0
        self.display.present(frame)
        return frame

    def _poll(self, now: float) -> None:
        snapshot = self.hub.poll(now)
        for widget in self.manager.widgets:
            widget.update(snapshot, now)
        self._last_poll = now

    # ---- internals -----------------------------------------------------------------
    def _on_rotate(self, old: Widget, new: Widget) -> None:
        theme = self.themes.active
        self.engine.play(HorizontalWipe(duration_ms=theme.default_animation_ms, easing=theme.default_easing), new.id)

    def _record_event(self, event: Event) -> None:
        detail = " ".join(f"{k}={v}" for k, v in event.payload.items())
        self.debug_info.last_event = f"{event.type.name} {detail}".strip()
