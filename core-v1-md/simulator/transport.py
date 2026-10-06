"""Deterministic display-endpoint simulation for transport and recovery tests."""

from __future__ import annotations

import heapq
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from display.frame import FrameRegion, PixelFormat
from display.oled_display import FrameTransport


@dataclass(order=True, slots=True)
class _QueuedUpdate:
    ready_at: float
    order: int
    width: int = field(compare=False)
    height: int = field(compare=False)
    payload: bytes = field(compare=False)
    region: FrameRegion | None = field(compare=False)


class SimulatedFrameTransport(FrameTransport):
    """In-memory endpoint with controllable latency, loss, and reconnect behavior."""

    supports_regions = True

    def __init__(
        self,
        width: int = 240,
        height: int = 1000,
        latency_s: float = 0.0,
        drop_every: int = 0,
        refresh_rate_hz: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("display dimensions must be positive")
        if latency_s < 0 or drop_every < 0:
            raise ValueError("latency_s and drop_every must be non-negative")
        if refresh_rate_hz is not None and refresh_rate_hz <= 0:
            raise ValueError("refresh_rate_hz must be positive when specified")
        self.width = width
        self.height = height
        self.latency_s = latency_s
        self.drop_every = drop_every
        self.refresh_interval_s = 1.0 / refresh_rate_hz if refresh_rate_hz is not None else 0.0
        self.clock = clock
        self.framebuffer = bytearray(width * height * PixelFormat.RGB565_BE.bytes_per_pixel)
        self.brightness: float | None = None
        self.input_events: list[tuple[int, int, int]] = []
        self.applied_updates = 0
        self.dropped_updates = 0
        self._connected = True
        self._generation = 0
        self._sent_updates = 0
        self._order = 0
        self._next_refresh_at = clock()
        self._pending: list[_QueuedUpdate] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def synchronization_generation(self) -> int:
        return self._generation

    def send_frame(self, width: int, height: int, payload: bytes) -> None:
        if (width, height) != (self.width, self.height):
            raise ValueError("full frame dimensions do not match simulated display")
        expected = width * height * PixelFormat.RGB565_BE.bytes_per_pixel
        if len(payload) != expected:
            raise ValueError(f"full frame payload is {len(payload)} bytes; expected {expected}")
        self._queue(width, height, payload, None)

    def send_region(self, region: FrameRegion) -> None:
        bounds = region.bounds
        if region.pixel_format is not PixelFormat.RGB565_BE:
            raise ValueError("simulated endpoint supports RGB565 big-endian only")
        if bounds.x + bounds.width > self.width or bounds.y + bounds.height > self.height:
            raise ValueError("region exceeds simulated display bounds")
        self._queue(bounds.width, bounds.height, region.payload, region)

    def send_brightness(self, level: float) -> None:
        if self._connected:
            self.brightness = min(1.0, max(0.0, level))

    def send_input_event(self, kind: int, source_id: int = 0, delta: int = 0) -> None:
        if not 0 <= kind <= 0xFF or not 0 <= source_id <= 0xFF or not -0x8000 <= delta <= 0x7FFF:
            raise ValueError("input event fields are out of range")
        if self._connected:
            self.input_events.append((kind, source_id, delta))

    def disconnect(self) -> None:
        if self._connected:
            self._connected = False
            self._pending.clear()
            self._generation += 1

    def reconnect(self) -> None:
        if not self._connected:
            self._connected = True
            self._generation += 1

    def advance(self, now: float | None = None) -> int:
        """Apply queued updates whose simulated transport latency has elapsed."""
        now = self.clock() if now is None else now
        applied = 0
        while self._pending and self._pending[0].ready_at <= now:
            update = heapq.heappop(self._pending)
            if update.region is None:
                self.framebuffer[:] = update.payload
            else:
                self._apply_region(update.region)
            self.applied_updates += 1
            applied += 1
        return applied

    def _queue(self, width: int, height: int, payload: bytes, region: FrameRegion | None) -> None:
        self._sent_updates += 1
        ready_at = self.clock() + self.latency_s
        if self.refresh_interval_s:
            ready_at = max(ready_at, self._next_refresh_at)
            self._next_refresh_at = ready_at + self.refresh_interval_s
        if not self._connected:
            self._drop()
            return
        if self.drop_every and self._sent_updates % self.drop_every == 0:
            self._drop()
            return
        self._order += 1
        heapq.heappush(
            self._pending,
            _QueuedUpdate(ready_at, self._order, width, height, payload, region),
        )

    def _drop(self) -> None:
        self.dropped_updates += 1
        self._generation += 1

    def _apply_region(self, region: FrameRegion) -> None:
        bounds = region.bounds
        bytes_per_pixel = region.pixel_format.bytes_per_pixel
        row_bytes = bounds.width * bytes_per_pixel
        for row in range(bounds.height):
            source_start = row * row_bytes
            target_start = ((bounds.y + row) * self.width + bounds.x) * bytes_per_pixel
            self.framebuffer[target_start : target_start + row_bytes] = region.payload[
                source_start : source_start + row_bytes
            ]
