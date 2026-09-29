"""Live telemetry from the host operating system via ``psutil``.

This is the first real provider. It is cross-platform (Windows, Linux, macOS)
and supplies the sections the OS exposes directly:

* ``cpu``     – total and per-core load, current clock, package temperature
                (temperature only where the OS exposes it, e.g. Linux)
* ``memory``  – used / total physical memory
* ``network`` – the busiest active adapter, throughput derived from byte
                counter deltas, IPv4 address
* ``system``  – hostname, uptime, fans (where the OS exposes them)

GPU, application and audio sections are left as ``None`` so that a later
provider (LibreHardwareMonitor, foreground-window tracker, WASAPI) can fill
them without this one needing to change. Stack it *before* more specific
providers – the hub merges in order and later providers win.

All calls used here are non-blocking, so :meth:`poll` is cheap enough to run
on the telemetry interval without a worker thread.
"""

from __future__ import annotations

import logging
import socket
import time
from collections.abc import Callable
from types import ModuleType
from typing import Any

from telemetry.models import (
    CpuTelemetry,
    FanReading,
    MemoryTelemetry,
    NetworkTelemetry,
    SystemTelemetry,
    TelemetrySnapshot,
)
from telemetry.provider import TelemetryProvider

log = logging.getLogger(__name__)

GIB = 1024**3

# Sensor chip labels that report the CPU package temperature, in priority order.
_CPU_TEMP_CHIPS = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz")
# Adapters that never represent the machine's real uplink.
_IGNORED_ADAPTER_PREFIXES = ("lo", "loopback", "docker", "veth", "br-", "virbr", "vmnet", "vethernet")


def load_psutil() -> ModuleType:
    """Import psutil lazily so the rest of the package works without it."""
    try:
        import psutil
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("SystemTelemetryProvider requires psutil: pip install psutil") from exc
    return psutil


class SystemTelemetryProvider(TelemetryProvider):
    """Reads CPU, memory, network and system data from the running OS.

    ``adapter`` pins a specific network interface by name; by default the
    busiest active, non-virtual adapter is chosen on each poll (sticky while
    it stays up, so the widget does not flicker between adapters).
    """

    name = "system"

    def __init__(
        self,
        adapter: str | None = None,
        psutil_module: ModuleType | Any | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ps = psutil_module
        # Throughput is measured against a real clock: the panel's ``now`` may be
        # virtual (headless rendering) while the OS byte counters are not.
        self._clock = clock
        self._pinned_adapter = adapter
        self._adapter: str | None = adapter
        self._hostname = socket.gethostname() or "CORE-V1"
        self._last_net: dict[str, tuple[float, int, int]] = {}
        self._rates: dict[str, tuple[float, float]] = {}

    # ---- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if self._ps is None:
            self._ps = load_psutil()
        # Prime the CPU counters: the first non-blocking call always returns 0.
        self._ps.cpu_percent(interval=None)
        self._ps.cpu_percent(interval=None, percpu=True)

    # ---- provider --------------------------------------------------------
    def poll(self, now: float) -> TelemetrySnapshot:
        if self._ps is None:
            self.start()
        temps = self._sensor_readings("sensors_temperatures")
        return TelemetrySnapshot(
            timestamp=now,
            cpu=self._cpu(temps),
            memory=self._memory(),
            network=self._network(self._clock()),
            system=self._system(),
        )

    # ---- sections --------------------------------------------------------
    def _cpu(self, temps: dict[str, list[Any]]) -> CpuTelemetry:
        ps = self._ps
        cores = tuple(round(float(c), 1) for c in ps.cpu_percent(interval=None, percpu=True))
        freq = None
        try:
            f = ps.cpu_freq()
            freq = round(float(f.current)) if f and f.current else None
        except (AttributeError, NotImplementedError, OSError):
            pass
        return CpuTelemetry(
            load_percent=round(float(ps.cpu_percent(interval=None)), 1),
            temperature_c=_cpu_temperature(temps),
            clock_mhz=freq,
            core_loads=cores,
        )

    def _memory(self) -> MemoryTelemetry:
        vm = self._ps.virtual_memory()
        return MemoryTelemetry(used_gb=round((vm.total - vm.available) / GIB, 2), total_gb=round(vm.total / GIB, 2))

    def _network(self, now: float) -> NetworkTelemetry | None:
        ps = self._ps
        try:
            counters = ps.net_io_counters(pernic=True)
            stats = ps.net_if_stats()
        except OSError:
            log.debug("network counters unavailable", exc_info=True)
            return None

        for nic, c in counters.items():
            prev = self._last_net.get(nic)
            if prev is not None and now > prev[0]:
                dt = now - prev[0]
                # Counters can wrap or reset (adapter restart); never report negative rates.
                self._rates[nic] = (max(0, c.bytes_recv - prev[1]) / dt, max(0, c.bytes_sent - prev[2]) / dt)
            self._last_net[nic] = (now, c.bytes_recv, c.bytes_sent)

        adapter = self._choose_adapter(counters, stats)
        if adapter is None:
            return NetworkTelemetry(adapter="--", connected=False)
        down, up = self._rates.get(adapter, (0.0, 0.0))
        connected = bool(stats.get(adapter) and stats[adapter].isup)
        return NetworkTelemetry(
            adapter=adapter,
            connected=connected,
            down_bps=down if connected else 0.0,
            up_bps=up if connected else 0.0,
            address=self._ipv4(adapter) if connected else None,
        )

    def _choose_adapter(self, counters: dict[str, Any], stats: dict[str, Any]) -> str | None:
        if self._pinned_adapter:
            return self._pinned_adapter

        def is_candidate(nic: str) -> bool:
            st = stats.get(nic)
            return bool(st and st.isup) and not nic.lower().startswith(_IGNORED_ADAPTER_PREFIXES)

        if self._adapter and is_candidate(self._adapter):
            return self._adapter
        candidates = [nic for nic in counters if is_candidate(nic)]
        if not candidates:
            # Keep reporting the last adapter as disconnected so the UI can show the edge.
            return self._adapter
        self._adapter = max(candidates, key=lambda nic: counters[nic].bytes_recv + counters[nic].bytes_sent)
        return self._adapter

    def _ipv4(self, adapter: str) -> str | None:
        try:
            addrs = self._ps.net_if_addrs().get(adapter, ())
        except OSError:
            return None
        for addr in addrs:
            if addr.family == socket.AF_INET:
                return addr.address
        return None

    def _system(self) -> SystemTelemetry:
        ps = self._ps
        uptime = max(0.0, time.time() - float(ps.boot_time()))
        fans = tuple(
            FanReading(entry.label or f"{chip.upper()}{i + 1}", float(entry.current))
            for chip, entries in self._sensor_readings("sensors_fans").items()
            for i, entry in enumerate(entries)
        )
        return SystemTelemetry(hostname=self._hostname, uptime_s=uptime, fans=fans)

    def _sensor_readings(self, fn_name: str) -> dict[str, list[Any]]:
        """Call an optional psutil sensor API (absent on Windows) and never raise."""
        fn = getattr(self._ps, fn_name, None)
        if fn is None:
            return {}
        try:
            return fn() or {}
        except (OSError, NotImplementedError, RuntimeError):
            log.debug("%s unavailable", fn_name, exc_info=True)
            return {}


def _cpu_temperature(temps: dict[str, list[Any]]) -> float | None:
    for chip in _CPU_TEMP_CHIPS:
        entries = temps.get(chip)
        if not entries:
            continue
        package = next((e for e in entries if (e.label or "").lower().startswith(("package", "tctl", "tdie"))), None)
        reading = package or entries[0]
        if reading.current is not None:
            return round(float(reading.current), 1)
    return None
