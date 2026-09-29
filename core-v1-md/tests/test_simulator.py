from PySide6.QtGui import QImage

from simulator.app import main


def test_headless_simulator_renders_screenshot(tmp_path):
    out = tmp_path / "frame.png"
    assert main(["--headless", "--frames", "30", "--screenshot", str(out), "--launch", "Code.exe", "--debug"]) == 0
    image = QImage(str(out))
    assert (image.width(), image.height()) == (240, 1000)


def test_simulator_window_constructs():
    from simulator.window import KeyboardJogInput, SimulatorWindow

    window = SimulatorWindow(240, 1000)
    jog = KeyboardJogInput(lambda _cmd: None)
    window.install_input(jog)
    assert window.width() == 240


def test_keyboard_input_maps_keys_to_controls_and_commands():
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    from core.controls import ControlEvent
    from simulator.window import KeyboardJogInput

    now = [0.0]
    commands, controls = [], []
    jog = KeyboardJogInput(commands.append, clock=lambda: now[0])
    jog.connect(controls.append)

    def key(k, pressed=True):
        etype = QEvent.Type.KeyPress if pressed else QEvent.Type.KeyRelease
        return jog.handle_event(QKeyEvent(etype, k, Qt.KeyboardModifier.NoModifier))

    assert key(Qt.Key.Key_Right)
    assert key(Qt.Key.Key_Return)
    assert key(Qt.Key.Key_1)
    key(Qt.Key.Key_Space)
    now[0] = 1.0
    jog.poll(now[0])  # held past the long-press threshold
    key(Qt.Key.Key_Space, pressed=False)
    assert controls == [ControlEvent.ROTATE_RIGHT, ControlEvent.PRESS, ControlEvent.LONG_PRESS]
    assert commands == ["launch:Cyberpunk2077.exe"]
    assert not key(Qt.Key.Key_Z)
