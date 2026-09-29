"""Jog wheel primitives shared by the simulator and real hardware."""

from __future__ import annotations

from collections.abc import Callable

from core.controls import ControlEvent

Emit = Callable[[ControlEvent], None]


class PressGestureDetector:
    """Classifies raw push-button edges into PRESS, DOUBLE_PRESS and LONG_PRESS.

    * LONG_PRESS fires *while held* once ``long_press_s`` elapses.
    * DOUBLE_PRESS fires on the second release within ``double_press_s``.
    * PRESS fires once the double-press window closes without a second press
      (so :meth:`poll` must be called regularly).
    """

    def __init__(self, emit: Emit, long_press_s: float = 0.6, double_press_s: float = 0.3) -> None:
        self.emit = emit
        self.long_press_s = long_press_s
        self.double_press_s = double_press_s
        self._down_at: float | None = None
        self._long_fired = False
        self._pending_release: float | None = None

    def press(self, now: float) -> None:
        if self._down_at is not None:
            return  # ignore auto-repeat / bounce
        self._down_at = now
        self._long_fired = False

    def release(self, now: float) -> None:
        if self._down_at is None:
            return
        self._down_at = None
        if self._long_fired:
            return
        if self._pending_release is not None and now - self._pending_release <= self.double_press_s:
            self._pending_release = None
            self.emit(ControlEvent.DOUBLE_PRESS)
        else:
            self._pending_release = now

    def poll(self, now: float) -> None:
        if self._down_at is not None and not self._long_fired and now - self._down_at >= self.long_press_s:
            self._long_fired = True
            self._pending_release = None
            self.emit(ControlEvent.LONG_PRESS)
        if self._pending_release is not None and self._down_at is None and now - self._pending_release > self.double_press_s:
            self._pending_release = None
            self.emit(ControlEvent.PRESS)


class JogWheel:
    """Converts encoder steps into ROTATE events.

    Many encoders produce several quadrature steps per mechanical detent;
    ``steps_per_detent`` groups them so one click = one event.
    """

    def __init__(self, emit: Emit, steps_per_detent: int = 1) -> None:
        self.emit = emit
        self.steps_per_detent = max(1, steps_per_detent)
        self._accumulator = 0

    def step(self, delta: int) -> None:
        self._accumulator += delta
        while abs(self._accumulator) >= self.steps_per_detent:
            if self._accumulator > 0:
                self._accumulator -= self.steps_per_detent
                self.emit(ControlEvent.ROTATE_RIGHT)
            else:
                self._accumulator += self.steps_per_detent
                self.emit(ControlEvent.ROTATE_LEFT)
