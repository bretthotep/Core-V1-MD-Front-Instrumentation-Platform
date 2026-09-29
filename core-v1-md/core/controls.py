"""Internal control events.

Every input source (simulator keyboard, future jog wheel, ESP32 front-panel
controller) is translated into one of these events. Nothing above the hardware
layer ever sees raw key codes or GPIO state.
"""

from __future__ import annotations

from enum import Enum


class ControlEvent(Enum):
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"
    PRESS = "press"
    DOUBLE_PRESS = "double_press"
    LONG_PRESS = "long_press"
    HOME = "home"
