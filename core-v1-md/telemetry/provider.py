"""Telemetry provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

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


class SectionFilter(TelemetryProvider):
    """Expose only some sections of another provider.

    Lets a mock fill gaps that no real provider covers yet (for example
    application tracking) without leaking simulated values into sections that
    real hardware already reports.
    """

    def __init__(self, inner: TelemetryProvider, sections: Iterable[str]) -> None:
        self.inner = inner
        self.sections = frozenset(sections)
        unknown = self.sections - set(TelemetrySnapshot.SECTIONS)
        if unknown:
            raise ValueError(f"unknown telemetry sections: {', '.join(sorted(unknown))}")
        self.name = f"{inner.name}[{','.join(sorted(self.sections))}]"

    def start(self) -> None:
        self.inner.start()

    def stop(self) -> None:
        self.inner.stop()

    def poll(self, now: float) -> TelemetrySnapshot:
        snap = self.inner.poll(now)
        kept = {name: getattr(snap, name) for name in self.sections}
        return TelemetrySnapshot(timestamp=snap.timestamp, **kept)
