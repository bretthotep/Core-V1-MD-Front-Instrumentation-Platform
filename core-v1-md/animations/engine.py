"""Runs animations and paints their overlays onto a frame."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter

from animations.types import Animation
from themes.theme import Theme

SCREEN = "screen"


@dataclass(slots=True)
class ActiveAnimation:
    animation: Animation
    target: str  # SCREEN or a widget id


class AnimationEngine:
    """Owns the set of running animations.

    The compositor calls :meth:`tick` once per frame and :meth:`paint` after the
    widgets have been drawn, passing the rectangles of the visible widgets so
    targeted animations land on the right region.
    """

    def __init__(self) -> None:
        self._active: list[ActiveAnimation] = []

    @property
    def active(self) -> list[ActiveAnimation]:
        return list(self._active)

    @property
    def busy(self) -> bool:
        return bool(self._active)

    def play(self, animation: Animation, target: str = SCREEN) -> Animation:
        self._active.append(ActiveAnimation(animation, target))
        return animation

    def cancel(self, target: str | None = None) -> None:
        self._active = [a for a in self._active if target is not None and a.target != target]

    def tick(self, dt_ms: float) -> None:
        for item in self._active:
            item.animation.advance(dt_ms)
        self._active = [a for a in self._active if not a.animation.finished]

    def paint(self, painter: QPainter, screen: QRectF, widget_rects: Mapping[str, QRectF], theme: Theme) -> None:
        def rect_for(item: ActiveAnimation) -> QRectF | None:
            return screen if item.target == SCREEN else widget_rects.get(item.target)

        # Pending (delayed) reveals keep their target dark until they start;
        # painted first so running effects remain visible on top.
        for item in self._active:
            anim = item.animation
            if not anim.started and anim.conceals and not anim.reverse:
                rect = rect_for(item)
                if rect is not None:
                    painter.fillRect(rect, QColor(theme.background))
        for item in self._active:
            if item.animation.started:
                rect = rect_for(item)
                if rect is not None:
                    item.animation.paint(painter, rect, theme)
