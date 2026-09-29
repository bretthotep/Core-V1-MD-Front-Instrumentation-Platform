"""Widget manager: ordering, focus navigation, rotation and layout state.

Navigation model (no pages – one continuous strip of instruments):

=================  ==========================================================
Control            Action on the focused widget
=================  ==========================================================
ROTATE_LEFT/RIGHT  Move focus to the previous / next widget (wraps)
PRESS              Cycle size NORMAL → EXPANDED → COLLAPSED (MD "DISPLAY" key)
DOUBLE_PRESS       Widget-specific action (visualiser mode, 12/24h clock, ...)
LONG_PRESS         Toggle pinned
HOME               Focus the first widget; pressed again, restore default layout
=================  ==========================================================
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from core.controls import ControlEvent
from widgets.base import Widget, WidgetState

log = logging.getLogger(__name__)

ROTATION_SLOT = "__rotation__"
STATE_VERSION = 1


@dataclass(frozen=True, slots=True)
class Slot:
    """A focusable position in the strip: a single widget or the rotation group."""

    key: str
    widget: Widget
    pinned: bool
    rotating: bool


class WidgetManager:
    def __init__(
        self,
        widgets: Iterable[Widget],
        rotation_interval_s: float = 6.0,
        on_rotate: Callable[[Widget, Widget], None] | None = None,
    ) -> None:
        self.widgets: list[Widget] = list(widgets)
        ids = [w.id for w in self.widgets]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate widget ids: {ids}")
        self._defaults = {w.id: w.state.copy() for w in self.widgets}
        self.rotation_interval_s = rotation_interval_s
        self.on_rotate = on_rotate
        self.rotation_index = 0
        self._last_rotation: float | None = None
        slots = self.slots()
        self.focus_key: str | None = slots[0].key if slots else None
        self.scroll = 0.0
        self.scroll_target = 0.0
        self.last_action = ""

    # ---- lookup ------------------------------------------------------------
    def widget(self, widget_id: str) -> Widget:
        for w in self.widgets:
            if w.id == widget_id:
                return w
        raise KeyError(widget_id)

    def rotating_members(self) -> list[Widget]:
        return [w for w in self.widgets if w.state.rotating and not w.state.pinned and not w.state.hidden]

    def current_rotating(self) -> Widget | None:
        members = self.rotating_members()
        return members[self.rotation_index % len(members)] if members else None

    def slots(self) -> list[Slot]:
        visible = [w for w in self.widgets if not w.state.hidden]
        pinned = [Slot(w.id, w, True, False) for w in visible if w.state.pinned]
        flow: list[Slot] = []
        current = self.current_rotating()
        for w in visible:
            if w.state.pinned:
                continue
            if w.state.rotating:
                if current is not None and not any(s.key == ROTATION_SLOT for s in flow):
                    flow.append(Slot(ROTATION_SLOT, current, False, True))
                continue
            flow.append(Slot(w.id, w, False, False))
        return pinned + flow

    def _focus_index(self, slots: list[Slot]) -> int:
        for i, slot in enumerate(slots):
            if slot.key == self.focus_key:
                return i
        return 0

    @property
    def focused_slot(self) -> Slot | None:
        slots = self.slots()
        return slots[self._focus_index(slots)] if slots else None

    @property
    def focused(self) -> Widget | None:
        slot = self.focused_slot
        return slot.widget if slot else None

    # ---- controls ------------------------------------------------------------
    def handle(self, event: ControlEvent) -> str:
        slots = self.slots()
        if not slots:
            self.last_action = "no widgets"
            return self.last_action
        index = self._focus_index(slots)
        slot = slots[index]
        widget = slot.widget
        if event in (ControlEvent.ROTATE_LEFT, ControlEvent.ROTATE_RIGHT):
            step = -1 if event is ControlEvent.ROTATE_LEFT else 1
            self.focus_key = slots[(index + step) % len(slots)].key
            action = f"focus {self.focused.id}"
        elif event is ControlEvent.PRESS:
            if widget.handle_control(event):
                action = f"{widget.id} action"
            else:
                widget.state.size = widget.state.size.next()
                action = f"{widget.id} {widget.state.size.value}"
        elif event is ControlEvent.DOUBLE_PRESS:
            action = f"{widget.id} action" if widget.handle_control(event) else f"{widget.id} no action"
        elif event is ControlEvent.LONG_PRESS:
            if widget.handle_control(event):
                action = f"{widget.id} action"
            else:
                members_before = self.rotating_members()
                widget.state.pinned = not widget.state.pinned
                if widget.state.pinned and widget in members_before:
                    # Keep the rotation slot on the member that followed the pinned one.
                    remaining = self.rotating_members()
                    if remaining:
                        self.rotation_index = members_before.index(widget) % len(remaining)
                self.focus_key = widget.id if widget.state.pinned or not widget.state.rotating else ROTATION_SLOT
                if widget.state.pinned is False and widget.state.rotating:
                    members = self.rotating_members()
                    self.rotation_index = members.index(widget)
                action = f"{widget.id} {'pinned' if widget.state.pinned else 'unpinned'}"
        elif event is ControlEvent.HOME:
            if index == 0:
                self.restore_defaults()
                action = "layout restored"
            else:
                self.focus_key = slots[0].key
                action = "home"
        else:  # pragma: no cover - exhaustive enum
            action = "ignored"
        self.last_action = action
        return action

    # ---- state changes -------------------------------------------------------
    def hide(self, widget_id: str) -> None:
        widget = self.widget(widget_id)
        slots_before = self.slots()
        index = self._focus_index(slots_before)
        widget.state.hidden = True
        slots = self.slots()
        if slots and all(s.key != self.focus_key for s in slots):
            self.focus_key = slots[min(index, len(slots) - 1)].key

    def show(self, widget_id: str) -> None:
        self.widget(widget_id).state.hidden = False

    def restore_defaults(self) -> None:
        for w in self.widgets:
            w.state = self._defaults[w.id].copy()
        self.rotation_index = 0
        slots = self.slots()
        self.focus_key = slots[0].key if slots else None

    # ---- persistence -----------------------------------------------------------
    def export_state(self) -> dict[str, Any]:
        """User-changeable layout state (pin / rotate / hide / size) as JSON-safe data."""
        return {
            "version": STATE_VERSION,
            "widgets": {w.id: w.state.to_dict() for w in self.widgets},
        }

    def apply_state(self, data: Mapping[str, Any]) -> int:
        """Restore state saved by :meth:`export_state`. Returns the number of widgets restored.

        Unknown widget ids (the layout changed since saving) are ignored, widgets
        missing from the saved data keep their layout defaults, and any invalid
        entry is skipped rather than failing startup.
        """
        if data.get("version") != STATE_VERSION or not isinstance(data.get("widgets"), Mapping):
            log.warning("Ignoring saved layout state with unsupported format")
            return 0
        restored = 0
        for widget in self.widgets:
            entry = data["widgets"].get(widget.id)
            if not isinstance(entry, Mapping):
                continue
            try:
                widget.state = WidgetState.from_dict(dict(entry))
            except (ValueError, TypeError):
                log.warning("Ignoring invalid saved state for widget %s", widget.id)
                continue
            restored += 1
        self.rotation_index = 0
        slots = self.slots()
        if slots and all(s.key != self.focus_key for s in slots):
            self.focus_key = slots[0].key
        return restored

    def rotate(self) -> Widget | None:
        members = self.rotating_members()
        if len(members) < 2:
            return None
        old = members[self.rotation_index % len(members)]
        self.rotation_index = (self.rotation_index + 1) % len(members)
        new = members[self.rotation_index]
        if self.on_rotate:
            self.on_rotate(old, new)
        return new

    def tick(self, now: float, dt_s: float = 0.0) -> Widget | None:
        """Advance auto-rotation and smooth scrolling."""
        rotated = None
        if self._last_rotation is None:
            self._last_rotation = now
        elif now - self._last_rotation >= self.rotation_interval_s:
            self._last_rotation = now
            # Never rotate the slot out from under the user.
            if self.focus_key != ROTATION_SLOT:
                rotated = self.rotate()
        if dt_s > 0:
            k = min(1.0, dt_s * 12.0)
            self.scroll += (self.scroll_target - self.scroll) * k
            if abs(self.scroll_target - self.scroll) < 0.5:
                self.scroll = self.scroll_target
        return rotated
