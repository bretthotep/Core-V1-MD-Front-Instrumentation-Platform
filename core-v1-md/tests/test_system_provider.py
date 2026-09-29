import json
import socket
from types import SimpleNamespace as NS

import pytest

from core.events import EventBus, EventType
from display.device import OffscreenDisplay
from simulator.app import Simulator, build_providers, parse_args
from telemetry.hub import TelemetryHub, Thresholds
from telemetry.mock_provider import MockTelemetryProvider
from telemetry.provider import SectionFilter
from telemetry.system_provider import SystemTelemetryProvider

GIB = 1024**3


class FakePsutil:
    """Just enough of the psutil API for SystemTelemetryProvider."""

    def __init__(self):
        self.cpu_total = 37.5
        self.cores = [10.0, 65.0]
        self.nics = {"lo": [0, 0], "Ethernet": [1_000, 500], "vEthernet (WSL)": [9_000_000, 9_000_000]}
        self.up = {"lo": True, "Ethernet": True, "vEthernet (WSL)": True}
        self.temps = {"coretemp": [NS(label="Core 0", current=51.0), NS(label="Package id 0", current=55.0)]}
        self.fans = {"nct6798": [NS(label="", current=1200.0)]}

    def cpu_percent(self, interval=None, percpu=False):
        return list(self.cores) if percpu else self.cpu_total

    def cpu_freq(self):
        return NS(current=4321.4)

    def virtual_memory(self):
        return NS(total=32 * GIB, available=24 * GIB)

    def net_io_counters(self, pernic=False):
        return {n: NS(bytes_recv=r, bytes_sent=s) for n, (r, s) in self.nics.items()}

    def net_if_stats(self):
        return {n: NS(isup=u) for n, u in self.up.items()}

    def net_if_addrs(self):
        return {"Ethernet": [NS(family=socket.AF_INET6, address="fe80::1"), NS(family=socket.AF_INET, address="10.0.0.7")]}

    def boot_time(self):
        return 0.0

    def sensors_temperatures(self):
        return self.temps

    def sensors_fans(self):
        return self.fans


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def _provider(ps=None, **kw):
    clock = Clock()
    provider = SystemTelemetryProvider(psutil_module=ps or FakePsutil(), clock=clock, **kw)
    provider.start()
    return provider, clock


def test_cpu_memory_system_sections():
    provider, _ = _provider()
    snap = provider.poll(1.0)
    assert snap.cpu.load_percent == 37.5
    assert snap.cpu.core_loads == (10.0, 65.0)
    assert snap.cpu.clock_mhz == 4321
    assert snap.cpu.temperature_c == 55.0  # package sensor preferred over core 0
    assert snap.memory.used_gb == 8.0 and snap.memory.total_gb == 32.0
    assert snap.system.fans[0].name == "NCT67981" and snap.system.fans[0].rpm == 1200.0
    assert snap.system.uptime_s > 0
    # Sections the OS cannot supply are left for other providers.
    assert snap.gpu is None and snap.application is None and snap.audio is None


def test_network_rate_from_counter_deltas_and_virtual_adapters_ignored():
    ps = FakePsutil()
    provider, clock = _provider(ps)
    first = provider.poll(0.0)
    assert first.network.adapter == "Ethernet"  # WSL switch is busier but virtual
    assert first.network.down_bps == 0.0  # no baseline yet
    assert first.network.address == "10.0.0.7"
    ps.nics["Ethernet"] = [1_000 + 4_000, 500 + 1_000]
    clock.t += 2.0
    snap = provider.poll(0.0)  # panel clock is irrelevant for rates
    assert snap.network.down_bps == 2_000.0 and snap.network.up_bps == 500.0


def test_network_counter_reset_never_goes_negative():
    ps = FakePsutil()
    provider, clock = _provider(ps)
    provider.poll(0.0)
    ps.nics["Ethernet"] = [0, 0]
    clock.t += 1.0
    assert provider.poll(0.0).network.down_bps == 0.0


def test_adapter_going_down_reports_disconnect_edge():
    ps = FakePsutil()
    provider, _ = _provider(ps)
    bus = EventBus()
    seen = []
    bus.subscribe(None, seen.append)
    hub = TelemetryHub(bus, [provider])
    hub.poll(0.0)
    ps.up["Ethernet"] = False
    ps.up["vEthernet (WSL)"] = False
    snap = hub.poll(1.0)
    bus.dispatch_pending()
    assert snap.network.adapter == "Ethernet" and not snap.network.connected
    assert [e.type for e in seen] == [EventType.NETWORK_DISCONNECTED]


def test_pinned_adapter_and_missing_sensor_apis():
    ps = FakePsutil()
    ps.sensors_temperatures = None  # psutil on Windows has no sensors_temperatures()
    ps.sensors_fans = lambda: (_ for _ in ()).throw(OSError("no access"))
    provider, _ = _provider(ps, adapter="vEthernet (WSL)")
    snap = provider.poll(0.0)
    assert snap.network.adapter == "vEthernet (WSL)"
    assert snap.cpu.temperature_c is None
    assert snap.system.fans == ()


def test_section_filter_keeps_only_requested_sections():
    filtered = SectionFilter(MockTelemetryProvider(seed=1), ["application"])
    snap = filtered.poll(1.0)
    assert snap.application is not None
    assert snap.cpu is None and snap.gpu is None and snap.network is None
    with pytest.raises(ValueError):
        SectionFilter(MockTelemetryProvider(), ["gpus"])


def test_thresholds_from_json(tmp_path):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({"$comment": "x", "high_temp_c": 90, "low_fan_rpm": 150}))
    t = Thresholds.load(path)
    assert (t.high_temp_c, t.high_temp_clear_c, t.low_fan_rpm) == (90.0, 80.0, 150.0)


@pytest.mark.parametrize(
    "data",
    [{"high_temp": 90}, {"high_temp_c": "hot"}, {"low_fan_rpm": True}, {"high_temp_c": 70}, {"low_fan_rpm": -1}],
)
def test_thresholds_reject_invalid(data):
    with pytest.raises(ValueError):
        Thresholds.from_dict(data)


def test_bundled_thresholds_file_matches_defaults():
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "telemetry" / "thresholds.json"
    assert Thresholds.load(path) == Thresholds()


def test_custom_threshold_changes_high_temp_event():
    bus = EventBus()
    seen = []
    bus.subscribe(EventType.HIGH_TEMP, seen.append)
    mock = MockTelemetryProvider(seed=3)
    TelemetryHub(bus, [mock], thresholds=Thresholds(high_temp_c=30, high_temp_clear_c=25)).poll(1.0)
    bus.dispatch_pending()
    assert seen and seen[0].payload["sensor"] in {"cpu", "gpu"}


def test_simulator_system_mode_provider_stack(qapp, monkeypatch):
    args = parse_args(["--telemetry", "system"])
    mock = MockTelemetryProvider()
    providers = build_providers(args, mock)
    assert isinstance(providers[0], SectionFilter) and isinstance(providers[1], SystemTelemetryProvider)
    assert build_providers(parse_args([]), mock) == [mock]

    fake = FakePsutil()
    monkeypatch.setattr("telemetry.system_provider.load_psutil", lambda: fake)
    sim = Simulator(args, OffscreenDisplay(240, 1000), clock=lambda: 0.0)
    sim.panel.start()
    sim.panel.step()
    snap = sim.hub.snapshot
    assert snap.cpu.load_percent == 37.5 and snap.gpu is None
    sim.command("launch:Code.exe")
    assert sim.hub.poll(1.0).application.foreground == "Code.exe"
    sim.panel.stop()
