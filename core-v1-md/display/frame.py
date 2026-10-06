"""Typed pixel and region representations for display output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from PySide6.QtGui import QImage


class PixelFormat(IntEnum):
    RGB565_BE = 1

    @property
    def bytes_per_pixel(self) -> int:
        return 2


@dataclass(frozen=True, slots=True)
class DirtyRegion:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("region origin must be non-negative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("region dimensions must be positive")
        if max(self.x, self.y, self.width, self.height) > 0xFFFF:
            raise ValueError("region coordinates and dimensions must fit in 16 bits")
        if self.width * PixelFormat.RGB565_BE.bytes_per_pixel > 0xFFFF:
            raise ValueError("RGB565 row byte count must fit in 16 bits")

    @property
    def area(self) -> int:
        return self.width * self.height

@dataclass(frozen=True, slots=True)
class FrameRegion:
    """A tightly packed pixel region in host-to-display byte order."""

    bounds: DirtyRegion
    pixel_format: PixelFormat
    payload: bytes
    frame_id: int

    def __post_init__(self) -> None:
        if not isinstance(self.pixel_format, PixelFormat):
            raise ValueError("unsupported pixel format")
        if not isinstance(self.payload, bytes):
            raise TypeError("region payload must be bytes")
        expected = self.bounds.area * self.pixel_format.bytes_per_pixel
        if len(self.payload) != expected:
            raise ValueError(f"region payload is {len(self.payload)} bytes; expected {expected}")
        if not 0 <= self.frame_id <= 0xFFFFFFFF:
            raise ValueError("frame_id must fit in 32 bits")

    @property
    def payload_length(self) -> int:
        return len(self.payload)

    @classmethod
    def from_image(cls, image: QImage, bounds: DirtyRegion, frame_id: int) -> FrameRegion:
        if image.isNull():
            raise ValueError("cannot encode a null image")
        if bounds.x + bounds.width > image.width() or bounds.y + bounds.height > image.height():
            raise ValueError("region exceeds image bounds")
        cropped = image.copy(bounds.x, bounds.y, bounds.width, bounds.height)
        return cls(bounds, PixelFormat.RGB565_BE, to_rgb565(cropped), frame_id)


def to_rgb565(frame: QImage) -> bytes:
    """Convert an image to tightly packed, big-endian RGB565 rows."""
    converted = frame.convertToFormat(QImage.Format.Format_RGB16)
    width_bytes = converted.width() * PixelFormat.RGB565_BE.bytes_per_pixel
    out = bytearray()
    for y in range(converted.height()):
        row = bytes(converted.constScanLine(y))[:width_bytes]
        swapped = bytearray(width_bytes)
        swapped[0::2] = row[1::2]
        swapped[1::2] = row[0::2]
        out.extend(swapped)
    return bytes(out)
