from core.controls import ControlEvent
from ui.layout import compute_layout
from ui.manager import ROTATION_SLOT, WidgetManager
from widgets.base import WidgetSize
from widgets.registry import create_widget


def make_manager(**kwargs):
    specs = [
        {"kind": "clock", "pinned": True},
        {"kind": "cpu"},
        {"kind": "gpu"},
        {"kind": "network", "rotating": True},
        {"kind": "system", "rotating": True},
        {"kind": "ram"},
    ]
    return WidgetManager([create_widget(s) for s in specs], **kwargs)


def keys(manager):
    return [s.key for s in manager.slots()]


def test_slots_put_pinned_first_and_group_rotating_widgets():
    manager = make_manager()
    assert keys(manager) == ["clock", "cpu", "gpu", ROTATION_SLOT, "ram"]
    assert manager.focused.id == "clock"


def test_rotate_focus_wraps_both_ways():
    manager = make_manager()
    manager.handle(ControlEvent.ROTATE_LEFT)
    assert manager.focused.id == "ram"
    manager.handle(ControlEvent.ROTATE_RIGHT)
    manager.handle(ControlEvent.ROTATE_RIGHT)
    assert manager.focused.id == "cpu"


def test_press_cycles_size_and_long_press_pins():
    manager = make_manager()
    manager.handle(ControlEvent.ROTATE_RIGHT)  # cpu
    cpu = manager.focused
    manager.handle(ControlEvent.PRESS)
    assert cpu.state.size is WidgetSize.EXPANDED
    manager.handle(ControlEvent.PRESS)
    assert cpu.state.size is WidgetSize.COLLAPSED
    manager.handle(ControlEvent.LONG_PRESS)
    assert cpu.state.pinned
    assert keys(manager)[:2] == ["clock", "cpu"]
    assert manager.focused is cpu  # focus follows the widget


def test_double_press_triggers_widget_action():
    manager = make_manager()
    clock = manager.focused
    manager.handle(ControlEvent.DOUBLE_PRESS)
    assert clock.use_24h is False


def test_auto_rotation_and_no_rotation_while_focused():
    manager = make_manager(rotation_interval_s=5)
    rotated = []
    manager.on_rotate = lambda old, new: rotated.append((old.id, new.id))
    manager.tick(0.0)
    manager.tick(5.0)
    assert rotated == [("network", "system")]
    manager.focus_key = ROTATION_SLOT
    manager.tick(10.0)
    assert len(rotated) == 1


def test_hide_moves_focus_and_home_restores_defaults():
    manager = make_manager()
    manager.handle(ControlEvent.ROTATE_RIGHT)
    manager.handle(ControlEvent.PRESS)
    manager.hide("cpu")
    assert "cpu" not in keys(manager)
    assert manager.focused.id == "gpu"
    manager.handle(ControlEvent.HOME)
    assert manager.focused.id == "clock"
    manager.handle(ControlEvent.HOME)  # second HOME restores the layout
    cpu = manager.widget("cpu")
    assert not cpu.state.hidden and cpu.state.size is WidgetSize.NORMAL


def test_layout_keeps_focused_widget_visible():
    manager = make_manager()
    for w in manager.widgets:
        w.state.size = WidgetSize.EXPANDED
    height = 400
    for _ in range(len(manager.slots())):
        manager.handle(ControlEvent.ROTATE_RIGHT)
        compute_layout(manager, 240, height, 6)  # updates the scroll target
        manager.scroll = manager.scroll_target  # as if smooth scrolling has settled
        layout = compute_layout(manager, 240, height, 6)
        focused = next(i for i in layout.items if i.focused)
        assert focused.rect.top() >= 0 and focused.rect.bottom() <= height + 0.5
