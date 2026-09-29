from core.events import EventBus, EventType
from telemetry.audio import MockAudioSource
from telemetry.hub import TelemetryHub, Thresholds
from telemetry.mock_provider import MockTelemetryProvider
from telemetry.models import CpuTelemetry, TelemetrySnapshot
from telemetry.provider import TelemetryProvider


def _events(bus):
    seen = []
    bus.subscribe(None, seen.append)
    return seen


def test_mock_provider_is_deterministic_and_complete():
    a = MockTelemetryProvider(seed=5, hostname="X").poll(1.0)
    b = MockTelemetryProvider(seed=5, hostname="X").poll(1.0)
    assert a == b
    for section in TelemetrySnapshot.SECTIONS:
        if section != "audio":
            assert getattr(a, section) is not None
    assert 0 <= a.cpu.load_percent <= 100
    assert 0 <= a.memory.percent <= 100


def test_hub_merges_partial_providers_later_wins():
    class CpuOnly(TelemetryProvider):
        name = "cpu-only"

        def poll(self, now):
            return TelemetrySnapshot(timestamp=now, cpu=CpuTelemetry(load_percent=99.0))

    hub = TelemetryHub(EventBus(), [MockTelemetryProvider(), CpuOnly()])
    snap = hub.poll(1.0)
    assert snap.cpu.load_percent == 99.0
    assert snap.gpu is not None  # from the mock provider


def test_hub_survives_failing_provider():
    class Broken(TelemetryProvider):
        def poll(self, now):
            raise OSError("sensor gone")

    hub = TelemetryHub(EventBus(), [Broken(), MockTelemetryProvider()])
    assert hub.poll(1.0).cpu is not None


def test_hub_derives_app_and_network_events():
    bus = EventBus()
    mock = MockTelemetryProvider()
    hub = TelemetryHub(bus, [mock])
    seen = _events(bus)
    hub.poll(0.0)
    bus.dispatch_pending()
    assert seen == []  # first poll is a baseline
    mock.launch_app("Cyberpunk2077.exe")
    mock.set_network(False)
    hub.poll(1.0)
    bus.dispatch_pending()
    assert (EventType.APP_LAUNCHED, "Cyberpunk2077.exe") in [(e.type, e.payload.get("app")) for e in seen]
    assert EventType.NETWORK_DISCONNECTED in [e.type for e in seen]
    seen.clear()
    mock.close_app()
    mock.set_network(True)
    hub.poll(2.0)
    bus.dispatch_pending()
    assert {e.type for e in seen} == {EventType.APP_CLOSED, EventType.NETWORK_CONNECTED}


def test_high_temp_has_hysteresis_and_low_fan_fires_once():
    bus = EventBus()
    mock = MockTelemetryProvider()
    hub = TelemetryHub(bus, [mock], thresholds=Thresholds(high_temp_c=85, high_temp_clear_c=80, low_fan_rpm=300))
    seen = _events(bus)
    mock.inject_heat(0.0, seconds=30)
    mock.stall_fan("SYS1")
    for i in range(40):
        hub.poll(i * 0.5)
    bus.dispatch_pending()
    types = [e.type for e in seen]
    assert types.count(EventType.HIGH_TEMP) == 1
    assert [e.payload["fan"] for e in seen if e.type is EventType.LOW_FAN_SPEED] == ["SYS1"]


def test_audio_source_ranges_and_hub_audio_refresh():
    source = MockAudioSource(bands=16, samples=64)
    frame = source.read_frame(1.23)
    assert len(frame.spectrum) == 16 and len(frame.waveform) == 64
    assert all(0.0 <= v <= 1.0 for v in frame.spectrum)
    hub = TelemetryHub(EventBus(), [MockTelemetryProvider()], audio=source)
    hub.poll(0.0)
    before = hub.snapshot.audio
    assert hub.poll_audio(0.5).audio != before
