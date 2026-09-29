"""Hardware integration layer.

Translates physical inputs into :class:`~core.controls.ControlEvent` values.
Nothing here renders; nothing elsewhere reads hardware.

* :class:`InputDevice` – base class for any control source
* :class:`PressGestureDetector` – raw button down/up → PRESS / DOUBLE_PRESS / LONG_PRESS
* :class:`JogWheel` – detent counting → ROTATE_LEFT / ROTATE_RIGHT
* :class:`Esp32FrontPanel` – line protocol for the future ESP32 controller
"""

from hardware.esp32 import Esp32FrontPanel
from hardware.input import InputDevice
from hardware.jog import JogWheel, PressGestureDetector

__all__ = ["Esp32FrontPanel", "InputDevice", "JogWheel", "PressGestureDetector"]
