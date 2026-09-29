"""Widget base class and state model."""

from __future__ import annotations

import datetime as _dt
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter

from core.controls import ControlEvent
from core.events import EventBus
from telemetry.models import TelemetrySnapshot
from themes.theme import Theme
from widgets import primitives as p


class WidgetSize(Enum):
    COLLAPSED = "collapsed"
    NORMAL = "normal"
    EXPANDED = "expanded"

    def next(self) -> "WidgetSize":
        """MiniDisc DISPLAY-button style cycle: NORMAL → EXPANDED → COLLAPSED → NORMAL."""
        order = (WidgetSize.NORMAL, WidgetSize.EXPANDED, WidgetSize.COLLAPSED)
        return order[(order.index(self) + 1) % len(order)]


@dataclass(slots=True)
class WidgetState:
    """Layout state for one widget.

    * ``pinned``   – always shown in the fixed region at the top of the strip
    * ``rotating`` – shares a single rotation slot with other rotating widgets
    * ``hidden``   – not rendered and not focusable
    * ``size``     – collapsed / normal / expanded
    """

    pinned: bool = False
    rotating: bool = False
    hidden: bool = False
    size: WidgetSize = WidgetSize.NORMAL

    def copy(self) -> "WidgetState":
        return WidgetState(self.pinned, self.rotating, self.hidden, self.size)

    @property
    def expanded(self) -> bool:
        return self.size is WidgetSize.EXPANDED

    @property
    def collapsed(self) -> bool:
        return self.size is WidgetSize.COLLAPSED

    def to_dict(self) -> dict[str, Any]:
        return {"pinned": self.pinned, "rotating": self.rotating, "hidden": self.hidden, "size": self.size.value}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "WidgetState":
        return WidgetState(
            pinned=bool(data.get("pinned", False)),
            rotating=bool(data.get("rotating", False)),
            hidden=bool(data.get("hidden", False)),
            size=WidgetSize(data.get("size", "normal")),
        )


@dataclass(slots=True)
class RenderContext:
    theme: Theme
    snapshot: TelemetrySnapshot
    now: float
    wall_time: _dt.datetime
    focused: bool = False
    debug: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


HEADER_HEIGHT = 18.0


class Widget:
    """Base class for every front-panel widget.

    Subclasses implement :meth:`render_body` (normal/expanded) and
    :meth:`summary` (the single line shown when collapsed). They read data
    exclusively from ``ctx.snapshot`` – never from a sensor API.
    """

    kind: ClassVar[str] = "widget"
    title: ClassVar[str] = "WIDGET"
    heights: ClassVar[dict[WidgetSize, float]] = {
        WidgetSize.COLLAPSED: 30,
        WidgetSize.NORMAL: 96,
        WidgetSize.EXPANDED: 180,
    }
    history_length: ClassVar[int] = 120

    def __init__(self, widget_id: str | None = None, state: WidgetState | None = None, **config: Any) -> None:
        self.id = widget_id or self.kind
        self.state = state or WidgetState()
        self.config = config

    # ---- lifecycle -------------------------------------------------------
    def attach(self, bus: EventBus) -> None:  # noqa: B027 - optional hook
        """Subscribe to application events if the widget needs them."""

    def update(self, snapshot: TelemetrySnapshot, now: float) -> None:  # noqa: B027 - optional hook
        """Called once per telemetry poll; use it to accumulate history."""

    def handle_control(self, event: ControlEvent) -> bool:
        """Widget-specific reaction to a control event. Return True if consumed."""
        return False

    @staticmethod
    def make_history(length: int | None = None) -> deque[float]:
        return deque(maxlen=length or Widget.history_length)

    # ---- layout ------------------------------------------------------------
    def preferred_height(self, width: float) -> float:
        return self.heights[self.state.size]

    # ---- rendering -----------------------------------------------------------
    def status(self, ctx: RenderContext) -> tuple[str, str]:
        """Right-aligned header text and its colour role."""
        return "", "dim"

    def summary(self, ctx: RenderContext) -> tuple[str, str]:
        """Collapsed-mode summary text and colour role."""
        return p.NONE_TEXT, "secondary"

    def render(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        theme = ctx.theme
        pad = theme.metric("padding", 10)
        inner = rect.adjusted(pad, 4, -pad, -4)
        tag_role = "primary" if ctx.focused else "dim"
        tag = p.draw_tag(painter, QPointF(inner.left(), inner.top() + 1), self.title, theme, tag_role)
        if self.state.collapsed:
            text, role = self.summary(ctx)
            p.draw_text(
                painter,
                QRectF(tag.right() + 6, inner.top(), inner.right() - tag.right() - 6, tag.height() + 2),
                text,
                p.display_font(theme, 13),
                p.colour(theme, role),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
            return
        status, role = self.status(ctx)
        if status:
            p.draw_label(
                painter,
                QRectF(tag.right() + 4, inner.top(), inner.right() - tag.right() - 4, tag.height() + 2),
                status,
                theme,
                role,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
        body = QRectF(inner.left(), inner.top() + HEADER_HEIGHT + 4, inner.width(), inner.height() - HEADER_HEIGHT - 4)
        if body.height() > 4:
            self.render_body(painter, body, ctx)

    def render_body(self, painter: QPainter, rect: QRectF, ctx: RenderContext) -> None:
        raise NotImplementedError
