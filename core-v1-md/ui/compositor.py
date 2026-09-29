"""Frame compositor: widgets + animations + debug overlay → QImage."""

from __future__ import annotations

import datetime as _dt
import logging

from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QColor, QImage, QPainter

from animations.engine import AnimationEngine
from telemetry.models import TelemetrySnapshot
from themes.theme import ThemeManager
from ui.debug_overlay import DebugInfo, draw_debug_overlay
from ui.layout import Layout, compute_layout
from ui.manager import WidgetManager
from widgets import primitives as p
from widgets.base import RenderContext

log = logging.getLogger(__name__)


class Compositor:
    def __init__(self, manager: WidgetManager, themes: ThemeManager, animations: AnimationEngine) -> None:
        self.manager = manager
        self.themes = themes
        self.animations = animations
        self.debug = False
        self.last_layout: Layout | None = None

    def render(
        self,
        size: QSize,
        snapshot: TelemetrySnapshot,
        now: float,
        wall_time: _dt.datetime,
        debug_info: DebugInfo | None = None,
    ) -> QImage:
        theme = self.themes.active
        width, height = max(1, size.width()), max(1, size.height())
        image = QImage(width, height, QImage.Format.Format_RGB32)
        image.fill(QColor(theme.background))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        try:
            layout = compute_layout(self.manager, width, height, theme.metric("widget_gap", 6))
            self.last_layout = layout
            screen = QRectF(0, 0, width, height)
            for item in layout.items:
                region = layout.pinned_region if item.slot.pinned else layout.flow_region
                clip = item.rect.intersected(region)
                if clip.isEmpty():
                    continue
                painter.save()
                painter.setClipRect(clip)
                ctx = RenderContext(theme, snapshot, now, wall_time, focused=item.focused, debug=self.debug)
                try:
                    item.slot.widget.render(painter, item.rect, ctx)
                except Exception:
                    log.exception("Widget %s failed to render", item.slot.widget.id)
                    painter.fillRect(item.rect, p.colour(theme, "critical", 0.2))
                self._decorate(painter, item, now)
                painter.restore()
            self._separators(painter, layout, width)
            self.animations.paint(painter, screen, layout.rects(), theme)
            if self.debug:
                draw_debug_overlay(painter, screen, layout, theme, debug_info or DebugInfo())
        finally:
            painter.end()
        return image

    def _decorate(self, painter: QPainter, item, now: float) -> None:
        theme = self.themes.active
        rect = item.rect
        if item.focused:
            painter.fillRect(QRectF(rect.left(), rect.top() + 4, 2, rect.height() - 8), p.colour(theme, "primary"))
        if item.slot.pinned:
            painter.fillRect(QRectF(rect.right() - 5, rect.top() + 4, 3, 3), p.colour(theme, "primary"))
        if item.slot.rotating:
            members = self.manager.rotating_members()
            current = self.manager.rotation_index % max(1, len(members))
            for i in range(len(members)):
                dot = QRectF(rect.right() - 8 - (len(members) - 1 - i) * 7, rect.bottom() - 6, 4, 2)
                painter.fillRect(dot, p.colour(theme, "primary") if i == current else p.unlit(theme))

    def _separators(self, painter: QPainter, layout: Layout, width: float) -> None:
        theme = self.themes.active
        if layout.pinned_region.height() > 0:
            y = layout.pinned_region.bottom() + theme.metric("widget_gap", 6) / 2
            p.draw_rule(painter, 8, width - 8, y, theme, "dim")
        for item in layout.items[:-1]:
            if not item.slot.pinned and item.rect.bottom() < layout.flow_region.bottom():
                gap = theme.metric("widget_gap", 6)
                p.draw_rule(painter, 16, width - 16, item.rect.bottom() + gap / 2, theme)
