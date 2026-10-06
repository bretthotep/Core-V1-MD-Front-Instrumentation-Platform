from PySide6.QtGui import QColor, QImage

from display.frame import to_rgb565
from display.oled_display import FutureOledDisplay
from simulator.transport import SimulatedFrameTransport


def image(width, height, colour):
    frame = QImage(width, height, QImage.Format.Format_RGB32)
    frame.fill(QColor(colour))
    return frame


def test_simulated_transport_models_latency_regions_brightness_and_input():
    now = [0.0]
    transport = SimulatedFrameTransport(32, 32, latency_s=0.5, clock=lambda: now[0])
    display = FutureOledDisplay(32, 32, transport, pixel_shift=False)
    first = image(32, 32, "#000000")
    display.present(first)

    assert transport.advance(0.49) == 0
    assert transport.advance(0.5) == 1
    assert transport.framebuffer == to_rgb565(first)

    changed = first.copy()
    changed.setPixelColor(17, 17, QColor("#FFFFFF"))
    now[0] = 1.0
    display.present(changed)
    assert transport.advance(1.49) == 0
    assert transport.advance(1.5) == 1
    assert transport.framebuffer == to_rgb565(changed)

    display.set_brightness(0.4)
    transport.send_input_event(kind=1, source_id=0, delta=-2)
    assert transport.brightness == 0.4
    assert transport.input_events == [(1, 0, -2)]


def test_dropped_update_forces_full_frame_resynchronization():
    now = [0.0]
    transport = SimulatedFrameTransport(32, 32, drop_every=2, clock=lambda: now[0])
    display = FutureOledDisplay(32, 32, transport, pixel_shift=False)
    baseline = image(32, 32, "#000000")
    display.present(baseline)
    transport.advance(0.0)

    changed = baseline.copy()
    changed.setPixelColor(1, 1, QColor("#FFFFFF"))
    now[0] = 1.0
    display.present(changed)  # second transport update is dropped
    assert transport.dropped_updates == 1

    now[0] = 2.0
    display.present(changed.copy())  # drop generation invalidates the baseline
    assert transport.advance(2.0) == 1
    assert transport.framebuffer == to_rgb565(changed)


def test_disconnect_reconnect_forces_full_sync_after_downtime():
    now = [0.0]
    transport = SimulatedFrameTransport(32, 32, clock=lambda: now[0])
    display = FutureOledDisplay(32, 32, transport, pixel_shift=False)
    baseline = image(32, 32, "#000000")
    display.present(baseline)
    transport.advance(0.0)

    changed = baseline.copy()
    changed.setPixelColor(20, 20, QColor("#FFFFFF"))
    transport.disconnect()
    now[0] = 1.0
    display.present(changed)
    assert transport.dropped_updates == 0

    transport.reconnect()
    now[0] = 2.0
    display.present(changed)
    assert transport.advance(2.0) == 1
    assert transport.framebuffer == to_rgb565(changed)


def test_simulated_transport_enforces_configured_refresh_rate():
    now = [0.0]
    transport = SimulatedFrameTransport(2, 1, refresh_rate_hz=10, clock=lambda: now[0])
    transport.send_frame(2, 1, b"\x00\x00\x00\x00")
    transport.send_frame(2, 1, b"\xFF\xFF\xFF\xFF")

    assert transport.advance(0.0) == 1
    assert transport.advance(0.099) == 0
    assert transport.advance(0.1) == 1
    assert transport.framebuffer == b"\xFF\xFF\xFF\xFF"
