"""EL-display drawing primitives shared by all widgets.

The look is modelled on Sony MiniDisc / ES-series fluorescent and EL
displays: tiny letter-spaced labels, boxed tags, segmented level meters with
faintly visible *unlit* segments, and tabular digits.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen

from themes.theme import Theme

NONE_TEXT = "--"


# ---- colours & fonts ------------------------------------------------------
def colour(theme: Theme, role: str, alpha: float = 1.0) -> QColor:
    c = QColor(theme.colour(role))
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def unlit(theme: Theme, role: str = "primary") -> QColor:
    return colour(theme, role, theme.unlit_alpha)


@lru_cache(maxsize=256)
def _font(families: str, px: int, bold: bool, spacing: float, mono: bool) -> QFont:
    f = QFont()
    f.setFamilies([name.strip() for name in families.split(",") if name.strip()])
    f.setPixelSize(max(6, px))
    f.setBold(bold)
    f.setStyleHint(QFont.StyleHint.Monospace if mono else QFont.StyleHint.SansSerif)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


def display_font(theme: Theme, px: float, bold: bool = False) -> QFont:
    return _font(theme.font("display"), int(px), bold, 0.0, True)


def label_font(theme: Theme, px: float | None = None, bold: bool = True) -> QFont:
    size = int(px if px is not None else theme.metric("label_size", 9))
    return _font(theme.font("label"), size, bold, max(0.8, size * 0.14), False)


# ---- formatting -----------------------------------------------------------
def fmt(value: float | None, pattern: str = "{:.0f}") -> str:
    return NONE_TEXT if value is None else pattern.format(value)


def fmt_rate(bps: float | None) -> tuple[str, str]:
    """Format a bytes/second rate as (number, unit)."""
    if bps is None:
        return NONE_TEXT, "B/s"
    for unit, scale in (("GB/s", 1e9), ("MB/s", 1e6), ("KB/s", 1e3)):
        if bps >= scale:
            value = bps / scale
            return (f"{value:.1f}" if value < 100 else f"{value:.0f}"), unit
    return f"{bps:.0f}", "B/s"


def fmt_duration(seconds: float) -> str:
    seconds = int(max(0, seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days}d {hours:02d}:{minutes:02d}" if days else f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ---- text -------------------------------------------------------------------
def draw_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    font: QFont,
    pen: QColor,
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
) -> None:
    painter.setFont(font)
    painter.setPen(pen)
    painter.drawText(rect, int(align), text)


def text_width(font: QFont, text: str) -> float:
    return QFontMetricsF(font).horizontalAdvance(text)


def draw_label(
    painter: QPainter,
    rect: QRectF,
    text: str,
    theme: Theme,
    role: str = "dim",
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    px: float | None = None,
) -> None:
    draw_text(painter, rect, text.upper(), label_font(theme, px), colour(theme, role), align)


def draw_tag(painter: QPainter, pos: QPointF, text: str, theme: Theme, role: str = "primary", px: float | None = None) -> QRectF:
    """A boxed label ("DISC", "TRACK") – the signature MiniDisc indicator."""
    font = label_font(theme, px)
    metrics = QFontMetricsF(font)
    w = metrics.horizontalAdvance(text.upper()) + 8
    h = metrics.height() + 2
    rect = QRectF(pos.x(), pos.y(), w, h)
    painter.setPen(QPen(colour(theme, role), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))
    draw_text(painter, rect, text.upper(), font, colour(theme, role), Qt.AlignmentFlag.AlignCenter)
    return rect


def draw_value(
    painter: QPainter,
    rect: QRectF,
    value: str,
    unit: str,
    theme: Theme,
    px: float | None = None,
    role: str = "secondary",
    align_right: bool = False,
) -> None:
    """Large tabular value with a small unit suffix, baseline aligned."""
    size = px if px is not None else theme.metric("value_size", 22)
    vfont = display_font(theme, size)
    ufont = label_font(theme, max(7, size * 0.38))
    vw = text_width(vfont, value)
    uw = text_width(ufont, unit.upper()) + (3 if unit else 0)
    x = rect.right() - vw - uw if align_right else rect.left()
    baseline = rect.top() + (rect.height() + QFontMetricsF(vfont).capHeight()) / 2
    painter.setFont(vfont)
    painter.setPen(colour(theme, role))
    painter.drawText(QPointF(x, baseline), value)
    if unit:
        painter.setFont(ufont)
        painter.setPen(colour(theme, "primary"))
        painter.drawText(QPointF(x + vw + 3, baseline), unit.upper())


# ---- meters -------------------------------------------------------------------
def level_role(fraction: float, alert_at: float | None, critical_at: float | None) -> str:
    if critical_at is not None and fraction >= critical_at:
        return "critical"
    if alert_at is not None and fraction >= alert_at:
        return "alert"
    return "primary"


def draw_segment_bar(
    painter: QPainter,
    rect: QRectF,
    fraction: float | None,
    theme: Theme,
    segments: int | None = None,
    alert_at: float | None = 0.8,
    critical_at: float | None = 0.95,
    role: str = "primary",
) -> None:
    """Horizontal segmented level meter with unlit ghost segments."""
    gap = theme.metric("segment_gap", 2)
    if segments is None:
        segments = max(4, int(rect.width() // 6))
    seg_w = (rect.width() - gap * (segments - 1)) / segments
    lit = 0 if fraction is None else round(max(0.0, min(1.0, fraction)) * segments)
    for i in range(segments):
        seg = QRectF(rect.left() + i * (seg_w + gap), rect.top(), seg_w, rect.height())
        pos = (i + 1) / segments
        seg_role = role if role != "primary" else level_role(pos, alert_at, critical_at)
        painter.fillRect(seg, colour(theme, seg_role) if i < lit else unlit(theme, seg_role))


def draw_vertical_segment_bar(
    painter: QPainter,
    rect: QRectF,
    fraction: float,
    theme: Theme,
    segments: int,
    peak: float | None = None,
    alert_at: float | None = 0.75,
    critical_at: float | None = 0.92,
) -> None:
    gap = max(1.0, theme.metric("segment_gap", 2) - 0.5)
    seg_h = (rect.height() - gap * (segments - 1)) / segments
    lit = round(max(0.0, min(1.0, fraction)) * segments)
    peak_idx = None if peak is None else min(segments - 1, max(0, round(peak * segments) - 1))
    for i in range(segments):
        y = rect.bottom() - (i + 1) * seg_h - i * gap
        seg = QRectF(rect.left(), y, rect.width(), seg_h)
        role = level_role((i + 1) / segments, alert_at, critical_at)
        if i < lit or i == peak_idx:
            painter.fillRect(seg, colour(theme, role))
        else:
            painter.fillRect(seg, unlit(theme, role))


def draw_sparkline(
    painter: QPainter,
    rect: QRectF,
    values: Sequence[float],
    theme: Theme,
    maximum: float | None = None,
    role: str = "primary",
    fill: bool = True,
) -> None:
    painter.fillRect(QRectF(rect.left(), rect.bottom() - 0.5, rect.width(), 1), unlit(theme))
    if len(values) < 2:
        return
    top = maximum if maximum else max(max(values), 1e-9)
    step = rect.width() / (len(values) - 1)
    path = QPainterPath()
    for i, v in enumerate(values):
        pt = QPointF(rect.left() + i * step, rect.bottom() - rect.height() * max(0.0, min(1.0, v / top)))
        path.lineTo(pt) if i else path.moveTo(pt)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if fill:
        area = QPainterPath(path)
        area.lineTo(rect.right(), rect.bottom())
        area.lineTo(rect.left(), rect.bottom())
        area.closeSubpath()
        painter.fillPath(area, colour(theme, role, 0.18))
    painter.setPen(QPen(colour(theme, role), 1.2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    painter.restore()


def draw_rule(painter: QPainter, x1: float, x2: float, y: float, theme: Theme, role: str = "grid") -> None:
    painter.fillRect(QRectF(x1, y, x2 - x1, 1), colour(theme, role))


def draw_fan_icon(painter: QPainter, rect: QRectF, theme: Theme, role: str = "primary") -> None:
    """Four curved vector blades and a hub; no assets or animation required."""
    if rect.width() <= 0 or rect.height() <= 0:
        return
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.translate(rect.center())
    scale = min(rect.width(), rect.height()) / 20
    painter.scale(scale, scale)
    painter.setPen(QPen(colour(theme, role, 0.65), 0.8))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(-9, -9, 18, 18))
    blade = QPainterPath(QPointF(1, -2))
    blade.cubicTo(8, -9, 10, -2, 5, 1)
    blade.cubicTo(3, 2, 2, 0, 1, -2)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(colour(theme, role))
    for _ in range(4):
        painter.drawPath(blade)
        painter.rotate(90)
    painter.drawEllipse(QRectF(-1.7, -1.7, 3.4, 3.4))
    painter.restore()
