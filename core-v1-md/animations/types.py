"""Animation primitives.

Every animation is a *reveal* overlay painted on top of already-rendered
content: at eased progress 0 the target is concealed (black), at 1 it is fully
visible. ``reverse=True`` plays the same motion as a conceal.

Colours are resolved against the active theme at paint time, so animations
automatically follow theme switches.
"""

from __future__ import annotations

import random
from typing import Any, ClassVar

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter

from animations.easing import get_easing
from themes.theme import Theme


def _clamp(value: float) -> float:
    return 0.0 if value < 0 else 1.0 if value > 1 else value


class Animation:
    kind: ClassVar[str] = "base"

    def __init__(
        self,
        duration_ms: float = 450,
        easing: str | None = "out_cubic",
        delay_ms: float = 0,
        colour: str = "primary",
        reverse: bool = False,
        **params: Any,
    ) -> None:
        self.duration_ms = max(1.0, float(duration_ms))
        self.easing_name = easing
        self._easing = get_easing(easing)
        self.delay_ms = max(0.0, float(delay_ms))
        self.colour_role = colour
        self.reverse = reverse
        self.params = params
        self.elapsed_ms = 0.0

    # ---- timing ---------------------------------------------------------
    def advance(self, dt_ms: float) -> None:
        self.elapsed_ms += dt_ms

    @property
    def started(self) -> bool:
        return self.elapsed_ms >= self.delay_ms

    @property
    def raw_progress(self) -> float:
        return _clamp((self.elapsed_ms - self.delay_ms) / self.duration_ms)

    @property
    def progress(self) -> float:
        """Eased reveal fraction (0 = concealed, 1 = revealed)."""
        p = self._easing(self.raw_progress)
        return 1.0 - p if self.reverse else p

    @property
    def conceals(self) -> bool:
        """Whether this animation hides its target until revealed (False for pure sweep effects)."""
        return not self.params.get("sweep_only", False)

    @property
    def finished(self) -> bool:
        return self.elapsed_ms >= self.delay_ms + self.duration_ms

    # ---- painting -------------------------------------------------------
    def accent(self, theme: Theme, alpha: float = 1.0) -> QColor:
        colour = QColor(theme.colour(self.colour_role))
        colour.setAlphaF(_clamp(alpha))
        return colour

    def paint(self, painter: QPainter, rect: QRectF, theme: Theme) -> None:
        """Paint the overlay for the current progress. Subclasses override :meth:`draw`."""
        if self.finished and not self.reverse:
            return
        painter.save()
        painter.setClipRect(rect)
        self.draw(painter, rect, theme, self.progress)
        painter.restore()

    def draw(self, painter: QPainter, rect: QRectF, theme: Theme, p: float) -> None:
        raise NotImplementedError


class HorizontalWipe(Animation):
    """Left→right reveal with a bright leading edge."""

    kind = "horizontal_wipe"

    def draw(self, painter: QPainter, rect: QRectF, theme: Theme, p: float) -> None:
        edge = rect.left() + rect.width() * p
        painter.fillRect(QRectF(edge, rect.top(), rect.right() - edge, rect.height()), QColor(theme.background))
        if 0 < p < 1:
            glow = QLinearGradient(QPointF(edge - 18, 0), QPointF(edge, 0))
            glow.setColorAt(0, self.accent(theme, 0))
            glow.setColorAt(1, self.accent(theme, 0.45))
            painter.fillRect(QRectF(edge - 18, rect.top(), 18, rect.height()), glow)
            painter.fillRect(QRectF(edge - 1, rect.top(), 2, rect.height()), self.accent(theme))


class VerticalWipe(Animation):
    """Top→bottom reveal with a bright leading edge."""

    kind = "vertical_wipe"

    def draw(self, painter: QPainter, rect: QRectF, theme: Theme, p: float) -> None:
        edge = rect.top() + rect.height() * p
        painter.fillRect(QRectF(rect.left(), edge, rect.width(), rect.bottom() - edge), QColor(theme.background))
        if 0 < p < 1:
            painter.fillRect(QRectF(rect.left(), edge - 1, rect.width(), 2), self.accent(theme))


class ScanLine(Animation):
    """A CRT/EL-style scan line sweeping down, leaving a fading phosphor trail.

    With ``sweep_only=True`` the line passes over the content without concealing it.
    """

    kind = "scan_line"

    def draw(self, painter: QPainter, rect: QRectF, theme: Theme, p: float) -> None:
        y = rect.top() + rect.height() * p
        if self.conceals:
            painter.fillRect(QRectF(rect.left(), y, rect.width(), rect.bottom() - y), QColor(theme.background))
        if 0 < p < 1:
            trail = float(self.params.get("trail", 60))
            grad = QLinearGradient(QPointF(0, y - trail), QPointF(0, y))
            grad.setColorAt(0, self.accent(theme, 0))
            grad.setColorAt(1, self.accent(theme, 0.35))
            painter.fillRect(QRectF(rect.left(), y - trail, rect.width(), trail), grad)
            painter.fillRect(QRectF(rect.left(), y - 1, rect.width(), 2), QColor(theme.secondary))


class Fade(Animation):
    """Fade from black, or – with ``flash=True`` – a decaying wash of the accent colour."""

    kind = "fade"

    def draw(self, painter: QPainter, rect: QRectF, theme: Theme, p: float) -> None:
        if self.params.get("flash"):
            painter.fillRect(rect, self.accent(theme, 0.5 * (1.0 - p)))
            return
        colour = QColor(theme.background)
        colour.setAlphaF(1.0 - p)
        painter.fillRect(rect, colour)


class SlidingBlocks(Animation):
    """Horizontal shutters slide away one after another, like an MD title scroll."""

    kind = "sliding_blocks"

    def draw(self, painter: QPainter, rect: QRectF, theme: Theme, p: float) -> None:
        blocks = max(1, int(self.params.get("blocks", 8)))
        stagger = float(self.params.get("stagger", 0.08))
        stagger = min(stagger, 0.9 / blocks)
        span = 1.0 - stagger * (blocks - 1)
        height = rect.height() / blocks
        for i in range(blocks):
            local = _clamp((p - i * stagger) / span)
            x = rect.left() + rect.width() * local
            top = rect.top() + i * height
            painter.fillRect(QRectF(x, top, rect.right() - x, height + 0.5), QColor(theme.background))
            if 0 < local < 1:
                painter.fillRect(QRectF(x, top + 1, 6, height - 2), self.accent(theme, 0.9))


class SegmentReveal(Animation):
    """The target lights up segment by segment, top-weighted with jitter."""

    kind = "segment_reveal"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._thresholds: dict[tuple[int, int], list[float]] = {}

    def _grid(self, cols: int, rows: int) -> list[float]:
        key = (cols, rows)
        if key not in self._thresholds:
            rng = random.Random(int(self.params.get("seed", 42)))
            self._thresholds[key] = [
                0.65 * (r / max(1, rows - 1)) + 0.3 * rng.random() for r in range(rows) for _ in range(cols)
            ]
        return self._thresholds[key]

    def draw(self, painter: QPainter, rect: QRectF, theme: Theme, p: float) -> None:
        seg = max(2.0, float(self.params.get("segment", 12)))
        cols = max(1, int(rect.width() // seg) + 1)
        rows = max(1, int(rect.height() // seg) + 1)
        thresholds = self._grid(cols, rows)
        background = QColor(theme.background)
        flash = self.accent(theme, 0.8)
        for r in range(rows):
            for c in range(cols):
                t = thresholds[r * cols + c]
                cell = QRectF(rect.left() + c * seg, rect.top() + r * seg, seg, seg)
                if p < t:
                    painter.fillRect(cell, background)
                elif p < t + 0.04:
                    painter.fillRect(cell.adjusted(1, 1, -1, -1), flash)


ANIMATION_TYPES: dict[str, type[Animation]] = {
    cls.kind: cls for cls in (HorizontalWipe, VerticalWipe, SlidingBlocks, SegmentReveal, ScanLine, Fade)
}


def create_animation(kind: str, **kwargs: Any) -> Animation:
    try:
        cls = ANIMATION_TYPES[kind]
    except KeyError as exc:
        raise ValueError(f"Unknown animation type {kind!r}; available: {sorted(ANIMATION_TYPES)}") from exc
    return cls(**kwargs)
