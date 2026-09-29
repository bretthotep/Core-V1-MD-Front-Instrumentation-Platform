"""ESP32 front-panel controller protocol (Milestone 5 – draft).

The ESP32 reads the jog wheel and its push switch and reports over USB CDC
serial using newline-terminated ASCII messages::

    ROT <signed int>     encoder steps since last report, e.g. "ROT -2"
    BTN DOWN | BTN UP    push-switch edges (gestures are classified on the host)
    HOME                 dedicated home key
    HELLO <fw-version>   sent once on connect

Classifying gestures on the host keeps the firmware trivial and lets timing
be tuned without reflashing. Transport (pyserial etc.) is intentionally left
out; feed received lines into :meth:`Esp32FrontPanel.feed_line`.
"""

from __future__ import annotations

import logging

from core.controls import ControlEvent
from hardware.input import InputDevice
from hardware.jog import JogWheel, PressGestureDetector

log = logging.getLogger(__name__)


class Esp32FrontPanel(InputDevice):
    name = "esp32"

    def __init__(self, steps_per_detent: int = 1, long_press_s: float = 0.6, double_press_s: float = 0.3) -> None:
        super().__init__()
        self.jog = JogWheel(self.emit, steps_per_detent)
        self.button = PressGestureDetector(self.emit, long_press_s, double_press_s)
        self.firmware: str | None = None

    def feed_line(self, line: str, now: float) -> None:
        parts = line.strip().split()
        if not parts:
            return
        cmd, args = parts[0].upper(), parts[1:]
        try:
            if cmd == "ROT" and args:
                self.jog.step(int(args[0]))
            elif cmd == "BTN" and args and args[0].upper() == "DOWN":
                self.button.press(now)
            elif cmd == "BTN" and args and args[0].upper() == "UP":
                self.button.release(now)
            elif cmd == "HOME":
                self.emit(ControlEvent.HOME)
            elif cmd == "HELLO":
                self.firmware = args[0] if args else "unknown"
            else:
                log.warning("Unknown front-panel message: %r", line)
        except ValueError:
            log.warning("Malformed front-panel message: %r", line)

    def poll(self, now: float) -> None:
        self.button.poll(now)
