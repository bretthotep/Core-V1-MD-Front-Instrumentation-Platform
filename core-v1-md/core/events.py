"""Application event framework.

A small publish/subscribe bus. Producers (telemetry hub, OS integration,
simulator key bindings) publish :class:`Event` objects; consumers (animation
profiles, alert widget, application widget) subscribe to the event types they
care about.

Events may be published from any thread with :meth:`EventBus.post`; they are
queued and delivered on the UI thread when :meth:`EventBus.dispatch_pending`
is called by the main loop. :meth:`EventBus.publish` delivers synchronously.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

log = logging.getLogger(__name__)


class EventType(Enum):
    APP_LAUNCHED = "app_launched"
    APP_CLOSED = "app_closed"
    SYSTEM_START = "system_start"
    SYSTEM_SHUTDOWN = "system_shutdown"
    NETWORK_CONNECTED = "network_connected"
    NETWORK_DISCONNECTED = "network_disconnected"
    HIGH_TEMP = "high_temp"
    LOW_FAN_SPEED = "low_fan_speed"


@dataclass(frozen=True, slots=True)
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)


Handler = Callable[[Event], None]


class EventBus:
    """Synchronous pub/sub bus with a thread-safe queue for cross-thread posts."""

    def __init__(self) -> None:
        self._handlers: dict[EventType | None, list[Handler]] = {}
        self._queue: deque[Event] = deque()
        self._lock = threading.Lock()

    def subscribe(self, event_type: EventType | None, handler: Handler) -> Callable[[], None]:
        """Subscribe ``handler`` to ``event_type`` (``None`` = every event).

        Returns a callable that removes the subscription.
        """
        self._handlers.setdefault(event_type, []).append(handler)

        def unsubscribe() -> None:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

        return unsubscribe

    def publish(self, event: Event) -> None:
        """Deliver ``event`` immediately on the calling thread."""
        for handler in (*self._handlers.get(event.type, ()), *self._handlers.get(None, ())):
            try:
                handler(event)
            except Exception:  # a faulty widget must never take the panel down
                log.exception("Event handler failed for %s", event.type)

    def emit(self, event_type: EventType, **payload: Any) -> Event:
        """Convenience wrapper: build and publish an event."""
        event = Event(event_type, payload)
        self.publish(event)
        return event

    def post(self, event: Event) -> None:
        """Queue ``event`` for delivery on the next :meth:`dispatch_pending`. Thread-safe."""
        with self._lock:
            self._queue.append(event)

    def dispatch_pending(self) -> int:
        """Deliver all queued events. Returns the number delivered."""
        with self._lock:
            pending = list(self._queue)
            self._queue.clear()
        for event in pending:
            self.publish(event)
        return len(pending)
