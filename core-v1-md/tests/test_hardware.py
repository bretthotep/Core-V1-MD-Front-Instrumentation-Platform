from core.controls import ControlEvent
from hardware.esp32 import Esp32FrontPanel
from hardware.jog import JogWheel, PressGestureDetector


def detector():
    events = []
    return PressGestureDetector(events.append, long_press_s=0.5, double_press_s=0.3), events


def test_single_press_fires_after_double_press_window():
    d, events = detector()
    d.press(0.0)
    d.release(0.1)
    d.poll(0.2)
    assert events == []
    d.poll(0.5)
    assert events == [ControlEvent.PRESS]


def test_double_press():
    d, events = detector()
    d.press(0.0)
    d.release(0.05)
    d.press(0.15)
    d.release(0.2)
    d.poll(1.0)
    assert events == [ControlEvent.DOUBLE_PRESS]


def test_long_press_fires_while_held_and_suppresses_press():
    d, events = detector()
    d.press(0.0)
    d.poll(0.6)
    d.press(0.7)  # auto-repeat ignored
    d.release(1.0)
    d.poll(2.0)
    assert events == [ControlEvent.LONG_PRESS]


def test_jog_wheel_detents():
    events = []
    jog = JogWheel(events.append, steps_per_detent=2)
    jog.step(1)
    assert events == []
    jog.step(3)
    jog.step(-2)
    assert events == [ControlEvent.ROTATE_RIGHT, ControlEvent.ROTATE_RIGHT, ControlEvent.ROTATE_LEFT]


def test_esp32_protocol():
    panel = Esp32FrontPanel()
    events = []
    panel.connect(events.append)
    for line in ("HELLO 0.1.0", "ROT 2", "ROT -1", "HOME", "BTN DOWN", "garbage", "ROT x"):
        panel.feed_line(line, 0.0)
    panel.feed_line("BTN UP", 0.05)
    panel.poll(1.0)
    assert panel.firmware == "0.1.0"
    assert events == [
        ControlEvent.ROTATE_RIGHT, ControlEvent.ROTATE_RIGHT, ControlEvent.ROTATE_LEFT, ControlEvent.HOME, ControlEvent.PRESS,
    ]
