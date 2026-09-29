"""Base display device interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage


class DisplayDevice(ABC):
    """A sink for rendered frames.

    Implementations:

    * :class:`display.simulator_display.SimulatorDisplay` – a resizable Qt widget
    * :class:`OffscreenDisplay` – keeps the last frame in memory (tests, screenshots)
    * :class:`display.oled_display.FutureOledDisplay` – physical panel via a transport
    """

    name: str = "display"

    @property
    @abstractmethod
    def size(self) -> QSize:
        """Logical resolution in pixels. The compositor renders at exactly this size."""

    @abstractmethod
    def present(self, frame: QImage) -> None:
        """Show ``frame``. ``frame.size()`` equals :attr:`size` at render time."""

    def set_brightness(self, level: float) -> None:  # noqa: B027 - optional capability
        """Set panel brightness in the range 0..1 (ignored if unsupported)."""

    def open(self) -> None:  # noqa: B027 - optional hook
        pass

    def close(self) -> None:  # noqa: B027 - optional hook
        pass


class OffscreenDisplay(DisplayDevice):
    """Fixed-size in-memory display. Useful for tests and headless screenshots."""

    name = "offscreen"

    def __init__(self, width: int = 240, height: int = 1000) -> None:
        self._size = QSize(width, height)
        self.last_frame: QImage | None = None
        self.frames_presented = 0

    @property
    def size(self) -> QSize:
        return QSize(self._size)

    def present(self, frame: QImage) -> None:
        self.last_frame = frame.copy()
        self.frames_presented += 1
