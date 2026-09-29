import json

from core.controls import ControlEvent
from core.events import EventBus
from display.device import OffscreenDisplay
from simulator.app import Simulator, parse_args
from telemetry.hub import TelemetryHub
from telemetry.mock_provider import MockTelemetryProvider
from tests.test_manager import make_manager
from ui.layout_store import LayoutStateStore, default_state_path
from ui.panel import FrontPanel
from widgets.base import WidgetSize


def test_export_apply_round_trip():
    a = make_manager()
    a.handle(ControlEvent.ROTATE_RIGHT)  # focus cpu
    a.handle(ControlEvent.PRESS)  # cpu expanded
    a.handle(ControlEvent.LONG_PRESS)  # cpu pinned
    a.hide("ram")
    state = json.loads(json.dumps(a.export_state()))

    b = make_manager()
    assert b.apply_state(state) == len(b.widgets)
    assert b.widget("cpu").state.pinned and b.widget("cpu").state.size is WidgetSize.EXPANDED
    assert b.widget("ram").state.hidden
    assert b.export_state() == state


def test_apply_ignores_unknown_invalid_and_unsupported():
    m = make_manager()
    state = {
        "version": 1,
        "widgets": {
            "gpu": {"size": "enormous"},  # invalid -> skipped
            "cpu": {"hidden": True},
            "storage": {"pinned": True},  # no longer in layout
            "ram": "nonsense",
        },
    }
    assert m.apply_state(state) == 1
    assert m.widget("cpu").state.hidden
    assert m.widget("gpu").state.size is WidgetSize.NORMAL
    assert make_manager().apply_state({"version": 99, "widgets": {}}) == 0


def test_focus_moves_off_a_restored_hidden_widget():
    m = make_manager()
    m.handle(ControlEvent.ROTATE_RIGHT)
    assert m.focused.id == "cpu"
    state = m.export_state()
    state["widgets"]["cpu"]["hidden"] = True
    m.apply_state(state)
    assert m.focused is not None and m.focused.id != "cpu"


def test_store_round_trip_and_bad_files(tmp_path):
    store = LayoutStateStore(tmp_path / "nested" / "state.json")
    assert store.load() is None
    assert store.save({"version": 1, "widgets": {}})
    assert store.load() == {"version": 1, "widgets": {}}
    assert [p.name for p in store.path.parent.iterdir()] == ["state.json"]  # no temp files left
    store.path.write_text("{not json")
    assert store.load() is None
    store.path.write_text("[1, 2]")
    assert store.load() is None


def test_store_save_failure_returns_false(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert LayoutStateStore(blocker / "state.json").save({"version": 1}) is False


def test_default_state_path_uses_config_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_state_path() == tmp_path / "CoreV1MD" / "layout_state.json"
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_state_path() == tmp_path / "core-v1-md" / "layout_state.json"


def _panel(store):
    bus = EventBus()
    hub = TelemetryHub(bus, [MockTelemetryProvider()])
    return FrontPanel(OffscreenDisplay(240, 1000), hub, bus, clock=lambda: 0.0, state_store=store)


def test_panel_saves_on_change_and_restores_next_session(tmp_path):
    store = LayoutStateStore(tmp_path / "state.json")
    panel = _panel(store)
    panel.start()
    panel.handle_control(ControlEvent.ROTATE_RIGHT)  # focus change only
    assert not store.path.exists()
    focused = panel.manager.focused.id
    default_size = panel.manager.widget(focused).state.size
    panel.handle_control(ControlEvent.PRESS)
    changed_size = panel.manager.widget(focused).state.size
    assert changed_size is not default_size
    assert store.path.exists()
    panel.stop()

    restored = _panel(store)
    assert restored.manager.widget(focused).state.size is changed_size

    # HOME twice restores defaults, and that is persisted too.
    restored.handle_control(ControlEvent.HOME)
    restored.handle_control(ControlEvent.HOME)
    assert _panel(store).manager.widget(focused).state.size is default_size


def test_simulator_persists_only_with_state_file(tmp_path):
    sim = Simulator(parse_args(["--headless"]), OffscreenDisplay(240, 1000), clock=lambda: 0.0)
    assert sim.panel.state_store is None
    path = tmp_path / "s.json"
    sim = Simulator(parse_args(["--state-file", str(path)]), OffscreenDisplay(240, 1000), clock=lambda: 0.0)
    sim.command("hide_focused")
    assert path.exists()
    sim = Simulator(
        parse_args(["--state-file", str(path), "--no-persist"]), OffscreenDisplay(240, 1000), clock=lambda: 0.0
    )
    assert sim.panel.state_store is None
