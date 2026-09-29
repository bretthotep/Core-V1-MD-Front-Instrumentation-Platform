import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter

from core.controls import ControlEvent
from core.events import EventBus, EventType
from telemetry.audio import MockAudioSource
from telemetry.models import TelemetrySnapshot
from widgets import primitives
from widgets.alert import AlertWidget
from widgets.application import display_name
from widgets.audio_visualiser import VISUALISER_MODES, AudioVisualiserWidget
from widgets.base import RenderContext, WidgetSize
from widgets.clock import ClockWidget
from widgets.registry import WIDGET_TYPES, create_widget

REQUIRED_WIDGETS = {"cpu", "gpu", "ram", "clock", "network", "audio_visualiser", "application", "system", "alert"}


def _render(widget, theme, snapshot, wall_time, width=240):
    height = int(widget.preferred_height(width))
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(0)
    painter = QPainter(image)
    widget.render(painter, QRectF(0, 0, width, height), RenderContext(theme, snapshot, 1.0, wall_time, focused=True))
    painter.end()
    return image


def _lit_pixels(image):
    return sum(1 for y in range(0, image.height(), 2) for x in range(0, image.width(), 2) if image.pixel(x, y) & 0xFFFFFF)


def test_required_widgets_registered():
    assert REQUIRED_WIDGETS <= set(WIDGET_TYPES)


@pytest.mark.parametrize("kind", sorted(REQUIRED_WIDGETS))
@pytest.mark.parametrize("size", list(WidgetSize))
def test_every_widget_renders_every_size_with_and_without_data(kind, size, theme, snapshot, wall_time):
    widget = create_widget({"kind": kind, "size": size.value})
    widget.update(snapshot, 10.0)
    full = snapshot.merged_with(TelemetrySnapshot(audio=MockAudioSource().read_frame(1.0)))
    assert _lit_pixels(_render(widget, theme, full, wall_time)) > 0
    _render(widget, theme, TelemetrySnapshot(), wall_time)  # missing telemetry must not crash


def test_create_widget_parses_state_and_config():
    widget = create_widget({"kind": "audio_visualiser", "id": "vis2", "pinned": True, "size": "expanded", "mode": "oscilloscope"})
    assert widget.id == "vis2"
    assert widget.state.pinned and widget.state.expanded
    assert widget.mode_id == "oscilloscope"
    with pytest.raises(ValueError):
        create_widget({"kind": "nope"})


def test_visualiser_modes_and_cycle(theme, snapshot, wall_time):
    assert {"classic_bars", "sony_el_bars", "oscilloscope", "network_activity"} == set(VISUALISER_MODES)
    widget = AudioVisualiserWidget()
    seen = {widget.mode_id}
    for _ in range(len(VISUALISER_MODES)):
        assert widget.handle_control(ControlEvent.DOUBLE_PRESS)
        seen.add(widget.mode_id)
        widget.update(snapshot, 1.0)
        _render(widget, theme, snapshot.merged_with(TelemetrySnapshot(audio=MockAudioSource().read_frame(2.0))), wall_time)
    assert seen == set(VISUALISER_MODES)


def test_alert_widget_tracks_and_expires_events():
    bus = EventBus()
    alert = AlertWidget(ttl_s=5)
    alert.attach(bus)
    bus.emit(EventType.HIGH_TEMP, sensor="cpu", value=93.0)
    bus.emit(EventType.NETWORK_DISCONNECTED, adapter="eth")
    assert set(alert.alerts) == {"temp:CPU", "net"}
    assert alert._ordered()[0].severity == "critical"
    bus.emit(EventType.NETWORK_CONNECTED, adapter="eth")
    assert set(alert.alerts) == {"temp:CPU"}
    alert.expire(alert.alerts["temp:CPU"].raised_at + 6)
    assert alert.alerts == {}


def test_clock_toggles_12_24h(theme, snapshot, wall_time):
    clock = ClockWidget()
    ctx = RenderContext(theme, snapshot, 0.0, wall_time)
    assert clock.summary(ctx)[0] == "13:05"
    clock.handle_control(ControlEvent.DOUBLE_PRESS)
    assert clock.summary(ctx)[0] == "1:05 PM"


def test_formatting_helpers():
    assert display_name("C:\\Games\\Cyberpunk2077.exe") == "CYBERPUNK2077"
    assert display_name(None) == "DESKTOP"
    assert primitives.fmt_rate(2_500_000) == ("2.5", "MB/s")
    assert primitives.fmt(None) == "--"
    assert primitives.fmt_duration(3 * 86400 + 3600) == "3d 01:00"
    assert WidgetSize.NORMAL.next() is WidgetSize.EXPANDED
    assert WidgetSize.EXPANDED.next() is WidgetSize.COLLAPSED
    assert WidgetSize.COLLAPSED.next() is WidgetSize.NORMAL
