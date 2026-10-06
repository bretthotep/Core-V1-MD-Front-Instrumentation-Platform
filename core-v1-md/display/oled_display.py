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
from display.dirty import DirtyRegionDetector
from display.frame import DirtyRegion, FrameRegion, to_rgb565


class FrameTransport(ABC):
    """Moves encoded frames to the panel controller."""

    supports_regions = False
    is_connected = True
    synchronization_generation = 0

    @abstractmethod
    def send_frame(self, width: int, height: int, payload: bytes) -> None: ...

    def send_full_frame(self, width: int, height: int, payload: bytes, frame_id: int) -> None:
        """Send a full frame while preserving compatibility with existing transports."""
        self.send_frame(width, height, payload)

    def send_region(self, region: FrameRegion) -> None:
        """Send one packed region; transports opt in through ``supports_regions``."""
        raise NotImplementedError("transport does not support dirty regions")

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
        partial_updates: bool = True,
        dirty_tile_size: int = 16,
        full_frame_ratio: float = 0.5,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("display dimensions must be positive")
        self._size = QSize(width, height)
        self.transport = transport or NullTransport()
        self.pixel_shift = pixel_shift
        self.shift_interval = max(1, shift_interval)
        self.partial_updates = partial_updates
        self._dirty_detector = DirtyRegionDetector(
            dirty_tile_size,
            dirty_tile_size,
            full_frame_ratio,
        )
        self._previous_frame: QImage | None = None
        self._frame_count = 0
        self._frame_id = 0
        self._transport_generation = self.transport.synchronization_generation

    @property
    def size(self) -> QSize:
        return QSize(self._size)

    @property
    def current_shift(self) -> tuple[int, int]:
        if not self.pixel_shift:
            return (0, 0)
        return self.ORBIT[(self._frame_count // self.shift_interval) % len(self.ORBIT)]

    def present(self, frame: QImage) -> None:
        if frame.isNull():
            raise ValueError("cannot present a null frame")
        generation = self.transport.synchronization_generation
        if generation != self._transport_generation:
            self._previous_frame = None
            self._transport_generation = generation
        if not self.transport.is_connected:
            self._frame_count += 1
            self._frame_id = (self._frame_id + 1) & 0xFFFFFFFF
            return

        dx, dy = self.current_shift
        if dx or dy:
            frame = frame.copy(-dx, -dy, frame.width(), frame.height())

        if self.partial_updates and self.transport.supports_regions:
            regions = self._dirty_detector.detect(self._previous_frame, frame)
            full = DirtyRegion(0, 0, frame.width(), frame.height())
            if len(regions) == 1 and regions[0] == full:
                self._send_full_frame(frame)
            else:
                for bounds in regions:
                    self.transport.send_region(FrameRegion.from_image(frame, bounds, self._frame_id))
        else:
            self._send_full_frame(frame)

        self._previous_frame = frame.copy()
        self._frame_count += 1
        self._frame_id = (self._frame_id + 1) & 0xFFFFFFFF

    def _send_full_frame(self, frame: QImage) -> None:
        self.transport.send_full_frame(frame.width(), frame.height(), to_rgb565(frame), self._frame_id)

    def force_full_refresh(self) -> None:
        """Forget the displayed baseline so the next frame is sent in full."""
        self._previous_frame = None

    def set_brightness(self, level: float) -> None:
        self.transport.send_brightness(min(1.0, max(0.0, level)))
