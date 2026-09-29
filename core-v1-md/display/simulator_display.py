"""Simulated display strip rendered inside a Qt widget."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget

from display.device import DisplayDevice


class _DisplaySurface(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.frame: QImage | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(120, 240)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        if self.frame is not None:
            painter.drawImage(0, 0, self.frame)
        painter.end()


class SimulatorDisplay(DisplayDevice):
    """A resizable on-screen emulation of the front-panel strip.

    The logical resolution follows the widget size, so resizing the simulator
    window lets you prototype layouts for different candidate panels.
    """

    name = "simulator"

    def __init__(self, parent: QWidget | None = None) -> None:
        self.widget = _DisplaySurface(parent)

    @property
    def size(self) -> QSize:
        return self.widget.size()

    def present(self, frame: QImage) -> None:
        self.widget.frame = frame
        self.widget.update()
