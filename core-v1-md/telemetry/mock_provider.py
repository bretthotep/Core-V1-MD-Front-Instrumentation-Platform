"""Deterministic mock telemetry for simulator development.

Values follow smooth bounded random walks so that widgets animate plausibly.
The simulator can also *inject scenarios* (launch an application, overheat
the CPU, stall a fan, drop the network) to exercise the event pipeline
end-to-end without real hardware.
"""

from __future__ import annotations

import math
import random
import socket

from telemetry.models import (
    ApplicationTelemetry,
    CpuTelemetry,
    FanReading,
    GpuTelemetry,
    MemoryTelemetry,
    NetworkTelemetry,
    SystemTelemetry,
    TelemetrySnapshot,
)
from telemetry.provider import TelemetryProvider


class _Walk:
    """Bounded, mean-reverting random walk."""

    def __init__(self, rng: random.Random, value: float, low: float, high: float, step: float) -> None:
        self.rng, self.value, self.low, self.high, self.step = rng, value, low, high, step
        self.mean = value

    def next(self) -> float:
        pull = (self.mean - self.value) * 0.05
        self.value = min(self.high, max(self.low, self.value + pull + self.rng.uniform(-self.step, self.step)))
        return self.value


class MockTelemetryProvider(TelemetryProvider):
    name = "mock"

    CORES = 8

    def __init__(self, seed: int | None = 1234, hostname: str | None = None) -> None:
        rng = random.Random(seed)
        self._rng = rng
        self._cpu = _Walk(rng, 18, 1, 100, 6)
        self._cores = [_Walk(rng, 15, 0, 100, 10) for _ in range(self.CORES)]
        self._cpu_temp = _Walk(rng, 46, 30, 80, 0.8)
        self._gpu = _Walk(rng, 12, 0, 100, 5)
        self._gpu_temp = _Walk(rng, 41, 28, 78, 0.6)
        self._ram = _Walk(rng, 13.5, 6, 30, 0.15)
        self._down = _Walk(rng, 2.5e6, 0, 60e6, 1.2e6)
        self._up = _Walk(rng, 3.0e5, 0, 8e6, 1.5e5)
        self._fans = {"CPU": _Walk(rng, 1150, 700, 1800, 25), "SYS1": _Walk(rng, 900, 600, 1400, 20)}
        self._hostname = hostname or socket.gethostname() or "CORE-V1"
        self._start: float | None = None
        # scenario state
        self._running: list[str] = ["explorer.exe"]
        self._network_up = True
        self._heat_until = 0.0
        self._stalled_fan: str | None = None

    # ---- scenario injection (simulator only) ---------------------------
    def launch_app(self, name: str) -> None:
        if name in self._running:
            self._running.remove(name)
        self._running.append(name)

    def close_app(self, name: str | None = None) -> str | None:
        """Close ``name`` (or the foreground app). Returns the closed app name."""
        target = name or (self._running[-1] if len(self._running) > 1 else None)
        if target and target in self._running:
            self._running.remove(target)
            return target
        return None

    def set_network(self, connected: bool) -> None:
        self._network_up = connected

    def toggle_network(self) -> bool:
        self._network_up = not self._network_up
        return self._network_up

    def inject_heat(self, now: float, seconds: float = 8.0) -> None:
        self._heat_until = now + seconds

    def stall_fan(self, name: str | None = "SYS1") -> None:
        self._stalled_fan = name

    # ---- provider --------------------------------------------------------
    def poll(self, now: float) -> TelemetrySnapshot:
        if self._start is None:
            self._start = now
        heating = now < self._heat_until
        gaming = any(n.lower() not in {"explorer.exe", "code.exe"} for n in self._running[1:])

        self._cpu.mean = 70 if heating else (45 if gaming else 18)
        self._gpu.mean = 92 if gaming else 12
        self._cpu_temp.mean = 91 if heating else (68 if gaming else 46)
        self._gpu_temp.mean = 74 if gaming else 41
        if heating:
            self._cpu_temp.high = 98
            self._cpu_temp.value = min(98.0, self._cpu_temp.value + 3.0)
        else:
            self._cpu_temp.high = 80

        cores = tuple(round(c.next(), 1) for c in self._cores)
        cpu_load = self._cpu.next()
        cpu = CpuTelemetry(
            load_percent=round(cpu_load, 1),
            temperature_c=round(self._cpu_temp.next(), 1),
            clock_mhz=round(3600 + 16 * cpu_load + self._rng.uniform(-40, 40)),
            power_w=round(18 + cpu_load * 1.1, 1),
            core_loads=cores,
        )
        gpu_load = self._gpu.next()
        gpu = GpuTelemetry(
            load_percent=round(gpu_load, 1),
            temperature_c=round(self._gpu_temp.next(), 1),
            clock_mhz=round(420 + 22 * gpu_load),
            power_w=round(14 + gpu_load * 2.6, 1),
            vram_used_mb=round(900 + gpu_load * 90),
            vram_total_mb=12288,
            fan_rpm=round(0 if gpu_load < 30 else 800 + gpu_load * 12),
        )
        memory = MemoryTelemetry(used_gb=round(self._ram.next(), 2), total_gb=32.0)
        network = NetworkTelemetry(
            adapter="Ethernet",
            connected=self._network_up,
            down_bps=self._down.next() if self._network_up else 0.0,
            up_bps=self._up.next() if self._network_up else 0.0,
            address="192.168.1.42" if self._network_up else None,
        )
        fans = tuple(
            FanReading(name, 0.0 if name == self._stalled_fan else round(walk.next()))
            for name, walk in self._fans.items()
        )
        system = SystemTelemetry(
            hostname=self._hostname,
            uptime_s=now - self._start + 3 * 3600 + 17 * 60,
            fans=fans,
            board_temperature_c=round(34 + 3 * math.sin(now / 60), 1),
        )
        foreground = self._running[-1] if self._running else None
        application = ApplicationTelemetry(foreground=foreground, title=foreground, running=tuple(self._running))
        return TelemetrySnapshot(
            timestamp=now,
            cpu=cpu,
            gpu=gpu,
            memory=memory,
            network=network,
            system=system,
            application=application,
        )
