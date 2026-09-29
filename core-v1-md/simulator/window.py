"""Simulator main window."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget

from display.simulator_display import SimulatorDisplay
from hardware.input import InputDevice
from hardware.jog import JogWheel, PressGestureDetector
from simulator.keymap import COMMAND_KEYS, CONTROL_KEYS, JOG_BUTTON_KEY


class _EventFilter(QObject):
    def __init__(self, handler: Callable[[QEvent], bool]) -> None:
        super().__init__()
        self._handler = handler

    def eventFilter(self, _obj: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        return self._handler(event)


class KeyboardJogInput(InputDevice):
    """Emulates the jog wheel with keyboard and mouse via a Qt event filter."""

    name = "keyboard"

    def __init__(self, on_command: Callable[[str], None], clock: Callable[[], float] = time.monotonic) -> None:
        super().__init__()
        self.event_filter = _EventFilter(self.handle_event)
        self.on_command = on_command
        self.clock = clock
        self.button = PressGestureDetector(self.emit)
        self.jog = JogWheel(self.emit)
        self._wheel_accum = 0

    def poll(self, now: float) -> None:
        self.button.poll(now)

    def handle_event(self, event: QEvent) -> bool:
        etype = event.type()
        if etype in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            return self._key(event, etype == QEvent.Type.KeyPress)  # type: ignore[arg-type]
        if etype == QEvent.Type.Wheel:
            self._wheel(event)  # type: ignore[arg-type]
            return True
        if etype in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick):
            mouse: QMouseEvent = event  # type: ignore[assignment]
            if mouse.button() == Qt.MouseButton.LeftButton:
                if etype == QEvent.Type.MouseButtonRelease:
                    self.button.release(self.clock())
                else:
                    self.button.press(self.clock())
                return True
        return False

    def _key(self, event: QKeyEvent, pressed: bool) -> bool:
        key = Qt.Key(event.key())
        if key == JOG_BUTTON_KEY:
            if not event.isAutoRepeat():
                (self.button.press if pressed else self.button.release)(self.clock())
            return True
        if not pressed:
            return key in CONTROL_KEYS or key in COMMAND_KEYS
        if key in CONTROL_KEYS:
            self.emit(CONTROL_KEYS[key])
            return True
        if key in COMMAND_KEYS and not event.isAutoRepeat():
            self.on_command(COMMAND_KEYS[key])
            return True
        return False

    def _wheel(self, event: QWheelEvent) -> None:
        self._wheel_accum += event.angleDelta().y()
        while abs(self._wheel_accum) >= 120:  # one notch
            step = 1 if self._wheel_accum < 0 else -1  # wheel down → rotate right
            self._wheel_accum += 120 * step
            self.jog.step(step)


class SimulatorWindow(QWidget):
    def __init__(self, width: int, height: int) -> None:
        super().__init__()
        self.setWindowTitle("Core V1-MD — Simulator")
        self.setStyleSheet("background: #000000;")
        self.display = SimulatorDisplay(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.display.widget)
        self.resize(width, height)

    def install_input(self, device: KeyboardJogInput) -> None:
        self.installEventFilter(device.event_filter)
        self.display.widget.installEventFilter(device.event_filter)
        self.display.widget.setFocus()

