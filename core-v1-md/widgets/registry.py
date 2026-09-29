"""Widget registry: maps widget ``kind`` strings to classes."""

from __future__ import annotations

from typing import Any

from widgets.alert import AlertWidget
from widgets.application import ApplicationWidget
from widgets.audio_visualiser import AudioVisualiserWidget
from widgets.base import Widget, WidgetState
from widgets.clock import ClockWidget
from widgets.cpu import CpuWidget
from widgets.gpu import GpuWidget
from widgets.network import NetworkWidget
from widgets.ram import RamWidget
from widgets.system import SystemWidget

WIDGET_TYPES: dict[str, type[Widget]] = {
    cls.kind: cls
    for cls in (
        CpuWidget,
        GpuWidget,
        RamWidget,
        ClockWidget,
        NetworkWidget,
        AudioVisualiserWidget,
        ApplicationWidget,
        SystemWidget,
        AlertWidget,
    )
}


def register_widget(cls: type[Widget]) -> type[Widget]:
    """Class decorator for third-party widgets."""
    WIDGET_TYPES[cls.kind] = cls
    return cls


def create_widget(spec: dict[str, Any]) -> Widget:
    """Build a widget from a layout entry such as ``{"kind": "cpu", "pinned": true}``."""
    spec = dict(spec)
    kind = spec.pop("kind")
    try:
        cls = WIDGET_TYPES[kind]
    except KeyError as exc:
        raise ValueError(f"Unknown widget kind {kind!r}; available: {sorted(WIDGET_TYPES)}") from exc
    state = WidgetState.from_dict(spec)
    widget_id = spec.pop("id", None)
    config = {k: v for k, v in spec.items() if k not in {"pinned", "rotating", "hidden", "size"}}
    return cls(widget_id, state, **config)
