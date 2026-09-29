"""Input device base class."""

from __future__ import annotations

from collections.abc import Callable

from core.controls import ControlEvent

ControlSink = Callable[[ControlEvent], None]


class InputDevice:
    """Emits control events to registered sinks.

    Devices that need time-based processing (long-press detection, serial
    polling) implement :meth:`poll`, which the main loop calls every frame.
    """

    name = "input"

    def __init__(self) -> None:
        self._sinks: list[ControlSink] = []

    def connect(self, sink: ControlSink) -> None:
        self._sinks.append(sink)

    def emit(self, event: ControlEvent) -> None:
        for sink in self._sinks:
            sink(event)

    def poll(self, now: float) -> None:  # noqa: B027 - optional hook
        pass
