"""Vertical strip layout.

Pinned widgets occupy a fixed region at the top. The remaining widgets flow
beneath it inside a scrollable region; the scroll offset is chosen so the
focused widget is always fully visible.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF

from ui.manager import Slot, WidgetManager


@dataclass(frozen=True, slots=True)
class LayoutItem:
    slot: Slot
    rect: QRectF
    focused: bool


@dataclass(frozen=True, slots=True)
class Layout:
    items: tuple[LayoutItem, ...]
    pinned_region: QRectF
    flow_region: QRectF
    content_height: float

    def rects(self) -> dict[str, QRectF]:
        """Map widget id → rect (animation targets address widgets by id)."""
        return {item.slot.widget.id: item.rect for item in self.items}


def compute_layout(manager: WidgetManager, width: float, height: float, gap: float) -> Layout:
    slots = manager.slots()
    focus = manager.focused_slot
    items: list[LayoutItem] = []

    y = 0.0
    for slot in (s for s in slots if s.pinned):
        h = slot.widget.preferred_height(width)
        items.append(LayoutItem(slot, QRectF(0, y, width, h), slot == focus))
        y += h + gap
    pinned_region = QRectF(0, 0, width, max(0.0, y - gap) if y else 0.0)
    flow_top = y
    flow_region = QRectF(0, flow_top, width, max(0.0, height - flow_top))

    # Content coordinates for the flow region.
    offsets: list[tuple[Slot, float, float]] = []
    cy = 0.0
    for slot in (s for s in slots if not s.pinned):
        h = slot.widget.preferred_height(width)
        offsets.append((slot, cy, h))
        cy += h + gap
    content_height = max(0.0, cy - gap)

    # Keep the focused flow widget in view.
    max_scroll = max(0.0, content_height - flow_region.height())
    target = min(max(manager.scroll_target, 0.0), max_scroll)
    for slot, top, h in offsets:
        if slot == focus:
            if top < target:
                target = top
            elif top + h > target + flow_region.height():
                target = min(max_scroll, top + h - flow_region.height())
    manager.scroll_target = target
    manager.scroll = min(max(manager.scroll, 0.0), max_scroll)

    for slot, top, h in offsets:
        rect = QRectF(0, flow_top + top - manager.scroll, width, h)
        if rect.bottom() >= flow_top and rect.top() <= height:
            items.append(LayoutItem(slot, rect, slot == focus))
    return Layout(tuple(items), pinned_region, flow_region, content_height)
