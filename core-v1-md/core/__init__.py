"""Core primitives shared by every layer: application events and control events.

This package is deliberately free of any Qt dependency so that it can be reused
by headless services (telemetry collectors, hardware bridges) and unit tests.
"""

from core.controls import ControlEvent
from core.events import Event, EventBus, EventType

__all__ = ["ControlEvent", "Event", "EventBus", "EventType"]
