import datetime as _dt

import pytest

from core.controls import ControlEvent
from core.events import EventBus, EventType
from display.device import OffscreenDisplay
from display.oled_display import FutureOledDisplay, NullTransport
from telemetry.audio import MockAudioSource
from telemetry.hub import TelemetryHub
from telemetry.mock_provider import MockTelemetryProvider
from ui.panel import FrontPanel


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def build(display):
    clock = FakeClock()
    bus = EventBus()
    mock = MockTelemetryProvider(seed=3)
    hub = TelemetryHub(bus, [mock], audio=MockAudioSource())
    panel = FrontPanel(display, hub, bus, clock=clock, wall_clock=lambda: _dt.datetime(2026, 1, 1, 12, 0))
    return panel, mock, clock


def run(panel, clock, seconds, fps=30):
    for _ in range(int(seconds * fps)):
        clock.now += 1 / fps
        panel.step()


@pytest.mark.parametrize("make_display", [lambda: OffscreenDisplay(240, 1000), lambda: FutureOledDisplay(240, 1000, NullTransport())])
def test_panel_is_display_agnostic(make_display):
    display = make_display()
    panel, _, clock = build(display)
    panel.start()
    run(panel, clock, 0.5)
    frame = panel.step()
    assert (frame.width(), frame.height()) == (240, 1000)
    panel.stop()


def test_boot_and_app_launch_trigger_profiles():
    panel, mock, clock = build(OffscreenDisplay())
    panel.start()
    assert panel.director.last_profile.name == "boot"
    assert panel.engine.busy
    run(panel, clock, 3.0)
    assert not panel.engine.busy
    mock.launch_app("Cyberpunk2077.exe")
    run(panel, clock, 0.6)
    assert panel.director.last_profile.name == "cinematic_reveal"
    assert "APP_LAUNCHED" in panel.debug_info.last_event


def test_controls_route_to_manager_and_debug_overlay_renders():
    panel, _, clock = build(OffscreenDisplay())
    panel.start()
    panel.compositor.debug = True
    action = panel.handle_control(ControlEvent.ROTATE_RIGHT)
    assert action.startswith("focus")
    run(panel, clock, 0.2)
    assert "ROTATE_RIGHT" in panel.debug_info.last_control
    events = []
    panel.bus.subscribe(EventType.SYSTEM_SHUTDOWN, events.append)
    panel.stop()
    assert len(events) == 1
