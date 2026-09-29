"""Telemetry provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from telemetry.models import TelemetrySnapshot


class TelemetryProvider(ABC):
    """A source of telemetry.

    Providers return a *partial* :class:`TelemetrySnapshot`: they fill in only
    the sections they know about and leave the rest as ``None``. The hub
    merges all providers in registration order (later providers win).

    Implementations must be cheap to :meth:`poll`. Providers that need slow
    I/O (WMI, shared memory, HTTP) should sample on their own thread and
    return the latest cached reading from :meth:`poll`.
    """

    name: str = "provider"

    def start(self) -> None:  # noqa: B027 - optional hook
        """Acquire resources. Called once before the first poll."""

    def stop(self) -> None:  # noqa: B027 - optional hook
        """Release resources."""

    @abstractmethod
    def poll(self, now: float) -> TelemetrySnapshot:
        """Return the latest reading. ``now`` is a monotonic timestamp in seconds."""
