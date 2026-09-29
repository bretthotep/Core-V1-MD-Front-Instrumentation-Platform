"""Telemetry acquisition layer.

Widgets never talk to sensors directly. They receive an immutable
:class:`TelemetrySnapshot` produced by the :class:`TelemetryHub`, which merges
the output of any number of :class:`TelemetryProvider` implementations.

Providers today: the mock provider and :class:`SystemTelemetryProvider`
(psutil: CPU, memory, network adapters, uptime). Planned: LibreHardwareMonitor,
HWiNFO shared memory, Windows APIs (foreground window) and WASAPI loopback audio.
``SystemTelemetryProvider`` lives in ``telemetry.system_provider`` and is not
imported here so that psutil stays optional.
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
from telemetry.provider import SectionFilter, TelemetryProvider

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
    "SectionFilter",
    "SystemTelemetry",
    "TelemetryHub",
    "TelemetryProvider",
    "TelemetrySnapshot",
    "Thresholds",
]
