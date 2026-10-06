import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter

from core.controls import ControlEvent
from core.events import EventBus, EventType
from telemetry.audio import MockAudioSource
from telemetry.models import FanReading, SystemTelemetry, TelemetrySnapshot
from widgets import primitives
from widgets.alert import AlertWidget
from widgets.application import display_name
from widgets.audio_visualiser import VISUALISER_MODES, AudioVisualiserWidget
from widgets.base import RenderContext, WidgetSize
from widgets.clock import ClockWidget
from widgets.registry import WIDGET_TYPES, create_widget
from widgets.system import SystemWidget

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


def test_vector_fan_icon_is_bounded_and_preserves_painter(theme):
    image = QImage(40, 40, QImage.Format.Format_RGB32)
    image.fill(0)
    painter = QPainter(image)
    pen, transform = painter.pen(), painter.transform()
    primitives.draw_fan_icon(painter, QRectF(10, 10, 20, 20), theme)
    assert painter.pen() == pen and painter.transform() == transform
    painter.end()
    assert _lit_pixels(image) > 0
    assert all(not (image.pixel(x, y) & 0xFFFFFF)
               for y in range(40) for x in range(40) if not (10 <= x < 30 and 10 <= y < 30))


@pytest.mark.parametrize("size", list(WidgetSize))
@pytest.mark.parametrize("count", [0, 1, 2, 4, 20])
@pytest.mark.parametrize("width", [120, 240, 320])
def test_fan_rows_have_icons_names_units_and_no_overlap(size, count, width, theme, wall_time, monkeypatch):
    fans = tuple(FanReading(f"CHASSIS FAN WITH LONG NAME {i}", 1180) for i in range(count))
    snapshot = TelemetrySnapshot(system=SystemTelemetry("host", 42, fans))
    widget = create_widget({"kind": "system", "size": size.value})
    icons, names, values, rows, footers, omissions = [], [], [], [], [], []
    draw_icon, draw_text, fan_row = primitives.draw_fan_icon, primitives.draw_text, SystemWidget._fan_row

    def icon(painter, rect, *args, **kwargs):
        icons.append(QRectF(rect))
        return draw_icon(painter, rect, *args, **kwargs)

    def text(painter, rect, value, *args, **kwargs):
        if value.startswith("+"):
            omissions.append(value)
        if value.endswith(" RPM"):
            values.append((QRectF(rect), value))
        elif value.startswith("C"):
            names.append((QRectF(rect), value))
        elif "MORE FANS" in value or value.startswith("BOARD"):
            footers.append(QRectF(rect))
        return draw_text(painter, rect, value, *args, **kwargs)

    def row(painter, rect, *args, **kwargs):
        rows.append(QRectF(rect))
        return fan_row(painter, rect, *args, **kwargs)

    monkeypatch.setattr(primitives, "draw_fan_icon", icon)
    monkeypatch.setattr(primitives, "draw_text", text)
    monkeypatch.setattr(SystemWidget, "_fan_row", staticmethod(row))
    image = _render(widget, theme, snapshot, wall_time, width)
    assert len(icons) == len(values) == len(rows)
    if count:
        assert len(names) == len(icons) > 0
    else:
        assert values[0][1] == "-- RPM"
    hidden_count = count - len(names)
    if hidden_count > 0:
        assert omissions == [f"+{hidden_count}" if widget.state.collapsed else f"+{hidden_count} MORE FANS"]
    else:
        assert not omissions
    for i, rect in enumerate(rows):
        assert rect.top() >= 0 and rect.bottom() <= image.height()
        if i:
            assert rows[i - 1].bottom() <= rect.top()
        if count:
            assert not names[i][0].intersects(values[i][0])
        assert icons[i].right() < values[i][0].left()
    if not widget.state.collapsed:
        assert all(rows[-1].bottom() <= footer.top() for footer in footers)
        if len(footers) > 1:
            assert footers[0].bottom() <= footers[1].top()


@pytest.mark.parametrize("rpm", [None, float("nan"), float("inf"), -1, 0])
@pytest.mark.parametrize("size", list(WidgetSize))
def test_unavailable_or_stalled_fan_readings_render(rpm, size, theme, wall_time, monkeypatch):
    widget = create_widget({"kind": "system", "size": size.value})
    snapshot = TelemetrySnapshot(system=SystemTelemetry("host", 42, (FanReading("CPU", rpm),)))
    labels = []
    draw_text = primitives.draw_text

    def record(painter, rect, text, *args, **kwargs):
        labels.append(text)
        return draw_text(painter, rect, text, *args, **kwargs)

    monkeypatch.setattr(primitives, "draw_text", record)
    _render(widget, theme, snapshot, wall_time)
    assert ("0 RPM" if rpm == 0 else "-- RPM") in labels
