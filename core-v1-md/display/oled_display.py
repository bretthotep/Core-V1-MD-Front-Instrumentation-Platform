"""Placeholder for the physical AMOLED/OLED strip.

The final panel is not chosen yet. This class fixes the *contract*:
frames are converted to the panel's native pixel format and pushed through a
:class:`FrameTransport` (SPI bridge, USB CDC to an ESP32, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage

from display.device import DisplayDevice


def to_rgb565(frame: QImage) -> bytes:
    """Convert ``frame`` to big-endian RGB565, the format most small OLED/AMOLED drivers accept."""
    converted = frame.convertToFormat(QImage.Format.Format_RGB16)
    out = bytearray()
    width_bytes = converted.width() * 2
    for y in range(converted.height()):
        row = bytes(converted.constScanLine(y))[:width_bytes]
        # Qt stores RGB16 in host (little-endian) order; panels expect big-endian.
        swapped = bytearray(width_bytes)
        swapped[0::2] = row[1::2]
        swapped[1::2] = row[0::2]
        out += swapped
    return bytes(out)


class FrameTransport(ABC):
    """Moves encoded frames to the panel controller."""

    @abstractmethod
    def send_frame(self, width: int, height: int, payload: bytes) -> None: ...

    def send_brightness(self, level: float) -> None:  # noqa: B027 - optional capability
        pass


class NullTransport(FrameTransport):
    """Discards frames but records the last one; used until real hardware exists."""

    def __init__(self) -> None:
        self.last: tuple[int, int, bytes] | None = None
        self.brightness: float | None = None

    def send_frame(self, width: int, height: int, payload: bytes) -> None:
        self.last = (width, height, payload)

    def send_brightness(self, level: float) -> None:
        self.brightness = level


class FutureOledDisplay(DisplayDevice):
    """Physical OLED/AMOLED strip (Milestone 4).

    ``pixel_shift`` enables a slow burn-in mitigation orbit: every
    ``shift_interval`` frames the whole image is offset by up to one pixel.
    """

    name = "oled"

    ORBIT = ((0, 0), (1, 0), (1, 1), (0, 1))

    def __init__(
        self,
        width: int = 240,
        height: int = 1000,
        transport: FrameTransport | None = None,
        pixel_shift: bool = True,
        shift_interval: int = 3600,
    ) -> None:
        self._size = QSize(width, height)
        self.transport = transport or NullTransport()
        self.pixel_shift = pixel_shift
        self.shift_interval = max(1, shift_interval)
        self._frame_count = 0

    @property
    def size(self) -> QSize:
        return QSize(self._size)

    @property
    def current_shift(self) -> tuple[int, int]:
        if not self.pixel_shift:
            return (0, 0)
        return self.ORBIT[(self._frame_count // self.shift_interval) % len(self.ORBIT)]

    def present(self, frame: QImage) -> None:
        dx, dy = self.current_shift
        if dx or dy:
            frame = frame.copy(-dx, -dy, frame.width(), frame.height())
        self.transport.send_frame(frame.width(), frame.height(), to_rgb565(frame))
        self._frame_count += 1

    def set_brightness(self, level: float) -> None:
        self.transport.send_brightness(min(1.0, max(0.0, level)))
