"""Immutable telemetry data models.

Every field that a real provider might not be able to supply is optional.
Widgets must render gracefully (``--``) when a value is ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True, slots=True)
class CpuTelemetry:
    load_percent: float
    temperature_c: float | None = None
    clock_mhz: float | None = None
    power_w: float | None = None
    core_loads: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class GpuTelemetry:
    load_percent: float
    temperature_c: float | None = None
    clock_mhz: float | None = None
    power_w: float | None = None
    vram_used_mb: float | None = None
    vram_total_mb: float | None = None
    fan_rpm: float | None = None


@dataclass(frozen=True, slots=True)
class MemoryTelemetry:
    used_gb: float
    total_gb: float

    @property
    def percent(self) -> float:
        return 0.0 if self.total_gb <= 0 else 100.0 * self.used_gb / self.total_gb


@dataclass(frozen=True, slots=True)
class NetworkTelemetry:
    adapter: str
    connected: bool
    down_bps: float = 0.0
    up_bps: float = 0.0
    address: str | None = None


@dataclass(frozen=True, slots=True)
class FanReading:
    name: str
    rpm: float


@dataclass(frozen=True, slots=True)
class SystemTelemetry:
    hostname: str
    uptime_s: float
    fans: tuple[FanReading, ...] = ()
    board_temperature_c: float | None = None


@dataclass(frozen=True, slots=True)
class ApplicationTelemetry:
    foreground: str | None
    title: str | None = None
    running: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AudioFrame:
    """One frame of audio analysis.

    ``spectrum`` holds normalised band magnitudes (0..1, low → high).
    ``waveform`` holds normalised samples (-1..1).
    """

    spectrum: tuple[float, ...] = ()
    waveform: tuple[float, ...] = ()
    peak: float = 0.0


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    timestamp: float = 0.0
    cpu: CpuTelemetry | None = None
    gpu: GpuTelemetry | None = None
    memory: MemoryTelemetry | None = None
    network: NetworkTelemetry | None = None
    system: SystemTelemetry | None = None
    application: ApplicationTelemetry | None = None
    audio: AudioFrame | None = None
    extras: dict[str, float] = field(default_factory=dict)

    SECTIONS = ("cpu", "gpu", "memory", "network", "system", "application", "audio")

    def merged_with(self, other: "TelemetrySnapshot") -> "TelemetrySnapshot":
        """Return a copy where every non-``None`` section of ``other`` wins."""
        changes = {name: getattr(other, name) for name in self.SECTIONS if getattr(other, name) is not None}
        extras = {**self.extras, **other.extras}
        return replace(self, timestamp=max(self.timestamp, other.timestamp), extras=extras, **changes)
