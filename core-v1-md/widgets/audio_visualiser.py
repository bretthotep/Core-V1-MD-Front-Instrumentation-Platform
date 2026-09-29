"""Audio visualiser widget and its pluggable render modes.

The widget reads ``snapshot.audio`` (an :class:`~telemetry.models.AudioFrame`)
which today comes from :class:`~telemetry.audio.MockAudioSource`. Swapping in
a real WASAPI loopback source requires no change here.

New modes: subclass :class:`VisualiserMode` and add it to :data:`VISUALISER_MODES`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QLinearGradient, QPainter, QPainterPath, QPen

from core.controls import ControlEvent
from widgets import primitives as p
from widgets.base import RenderContext, Widget, WidgetSize

if TYPE_CHECKING:
    from telemetry.models import AudioFrame


def _resample(values: tuple[float, ...], count: int) -> list[float]:
    if not values:
        return [0.0] * count
    n = len(values)
    return [values[min(n - 1, int(i * n / count))] for i in range(count)]


class VisualiserMode(ABC):
    id: ClassVar[str]
    label: ClassVar[str]

    @abstractmethod
    def render(self, painter: QPainter, rect: QRectF, ctx: RenderContext, widget: "AudioVisualiserWidget") -> None: ...


class ClassicBars(VisualiserMode):
    id = "classic_bars"
    label = "BARS"

    def render(self, painter, rect, ctx, widget) -> None:
        theme = ctx.theme
        frame = ctx.snapshot.audio
        bands = _resample(frame.spectrum if frame else (), widget.bands)
        w = rect.width() / len(bands)
        grad = QLinearGradient(QPointF(0, rect.bottom()), QPointF(0, rect.top()))
        grad.setColorAt(0.0, p.colour(theme, "primary", 0.55))
        grad.setColorAt(1.0, p.colour(theme, "secondary"))
        for i, v in enumerate(bands):
            h = rect.height() * max(0.02, v)
            painter.fillRect(QRectF(rect.left() + i * w + 1, rect.bottom() - h, w - 2, h), grad)


class SonyElBars(VisualiserMode):
    """Segmented spectrum with falling peak-hold markers, as on MDS-JA / ES decks."""

    id = "sony_el_bars"
    label = "EL"

    def __init__(self) -> None:
        self.peaks: list[float] = []
        self._last: float | None = None

    def render(self, painter, rect, ctx, widget) -> None:
        frame = ctx.snapshot.audio
        bands = _resample(frame.spectrum if frame else (), widget.bands)
        if len(self.peaks) != len(bands):
            self.peaks = [0.0] * len(bands)
        dt = 0.0 if self._last is None else max(0.0, ctx.now - self._last)
        self._last = ctx.now
        for i, v in enumerate(bands):
            self.peaks[i] = max(v, self.peaks[i] - 0.45 * dt)
        segments = max(6, int(rect.height() // 6))
        w = rect.width() / len(bands)
        for i, v in enumerate(bands):
            p.draw_vertical_segment_bar(
                painter, QRectF(rect.left() + i * w + 1, rect.top(), w - 2, rect.height()), v, ctx.theme, segments, peak=self.peaks[i]
            )


class Oscilloscope(VisualiserMode):
    id = "oscilloscope"
    label = "SCOPE"

    def render(self, painter, rect, ctx, widget) -> None:
        theme = ctx.theme
        for k in range(1, 4):
            p.draw_rule(painter, rect.left(), rect.right(), rect.top() + rect.height() * k / 4, theme)
        frame: AudioFrame | None = ctx.snapshot.audio
        samples = frame.waveform if frame else ()
        if len(samples) < 2:
            return
        mid, amp = rect.center().y(), rect.height() / 2 * 0.9
        step = rect.width() / (len(samples) - 1)
        path = QPainterPath(QPointF(rect.left(), mid - samples[0] * amp))
        for i, s in enumerate(samples[1:], start=1):
            path.lineTo(rect.left() + i * step, mid - max(-1.0, min(1.0, s)) * amp)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(p.colour(theme, "primary", 0.25), 5))  # phosphor bloom
        painter.drawPath(path)
        painter.setPen(QPen(p.colour(theme, "secondary"), 1.3))
        painter.drawPath(path)
        painter.restore()


class NetworkActivity(VisualiserMode):
    """Scrolling bar field: downstream throughput above the midline, upstream below it."""

    id = "network_activity"
    label = "NET"

    def render(self, painter, rect, ctx, widget) -> None:
        theme = ctx.theme
        down, up = list(widget.net_down), list(widget.net_up)
        mid = rect.center().y()
        p.draw_rule(painter, rect.left(), rect.right(), mid, theme, "dim")
        if not down:
            return
        peak = max(max(down), max(up), 1.0)
        count = min(len(down), widget.bands * 2)
        w = rect.width() / (widget.bands * 2)
        for i in range(count):
            d, u = down[-count + i], up[-count + i]
            x = rect.right() - (count - i) * w
            hd = (rect.height() / 2 - 2) * d / peak
            hu = (rect.height() / 2 - 2) * u / peak
            painter.fillRect(QRectF(x + 0.5, mid - 1 - hd, w - 1, hd), p.colour(theme, "primary"))
            painter.fillRect(QRectF(x + 0.5, mid + 1, w - 1, hu), p.colour(theme, "secondary", 0.7))


VISUALISER_MODES: dict[str, type[VisualiserMode]] = {
    cls.id: cls for cls in (ClassicBars, SonyElBars, Oscilloscope, NetworkActivity)
}


class AudioVisualiserWidget(Widget):
    kind = "audio_visualiser"
    title = "LEVEL"
    heights = {WidgetSize.COLLAPSED: 30, WidgetSize.NORMAL: 120, WidgetSize.EXPANDED: 220}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bands = int(self.config.get("bands", 24))
        self._modes = {mode_id: cls() for mode_id, cls in VISUALISER_MODES.items()}
        self.mode_id = str(self.config.get("mode", SonyElBars.id))
        if self.mode_id not in self._modes:
            raise ValueError(f"Unknown visualiser mode {self.mode_id!r}; available: {list(self._modes)}")
        self.net_down = self.make_history()
        self.net_up = self.make_history()

    @property
    def mode(self) -> VisualiserMode:
        return self._modes[self.mode_id]

    def set_mode(self, mode_id: str) -> None:
        if mode_id not in self._modes:
            raise KeyError(mode_id)
        self.mode_id = mode_id

    def next_mode(self) -> str:
        ids = list(self._modes)
        self.mode_id = ids[(ids.index(self.mode_id) + 1) % len(ids)]
        return self.mode_id

    def handle_control(self, event: ControlEvent) -> bool:
        if event is ControlEvent.DOUBLE_PRESS:
            self.next_mode()
            return True
        return False

    def update(self, snapshot, now) -> None:
        if snapshot.network:
            self.net_down.append(snapshot.network.down_bps)
            self.net_up.append(snapshot.network.up_bps)

    def status(self, ctx: RenderContext) -> tuple[str, str]:
        return self.mode.label, "primary"

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        frame = ctx.snapshot.audio
        level = frame.peak if frame else 0.0
        segments = 12
        lit = round(level * segments)
        return "▮" * lit + "▯" * (segments - lit), "primary"

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        self.mode.render(painter, rect, ctx, self)
