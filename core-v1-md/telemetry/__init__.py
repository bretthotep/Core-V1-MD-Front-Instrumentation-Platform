"""Telemetry acquisition layer.

Widgets never talk to sensors directly. They receive an immutable
:class:`TelemetrySnapshot` produced by the :class:`TelemetryHub`, which merges
the output of any number of :class:`TelemetryProvider` implementations.

Only mock providers exist today. Planned providers: LibreHardwareMonitor,
HWiNFO shared memory, Windows APIs (PDH / WMI / foreground window), network
adapters and WASAPI loopback audio.
"""

from telemetry.audio import AudioSource, MockAudioSource
from telemetry.hub import TelemetryHub, Thresholds
from telemetry.mock_provider import MockTelemetryProvider
from telemetry.models import (
    ApplicationTelemetry,
    AudioFrame,
    CpuTelemetry,
    FanReading,
    GpuTelemetry,
    MemoryTelemetry,
    NetworkTelemetry,
    SystemTelemetry,
    TelemetrySnapshot,
)
from telemetry.provider import TelemetryProvider

__all__ = [
    "ApplicationTelemetry",
    "AudioFrame",
    "AudioSource",
    "CpuTelemetry",
    "FanReading",
    "GpuTelemetry",
    "MemoryTelemetry",
    "MockAudioSource",
    "MockTelemetryProvider",
    "NetworkTelemetry",
    "SystemTelemetry",
    "TelemetryHub",
    "TelemetryProvider",
    "TelemetrySnapshot",
    "Thresholds",
]
