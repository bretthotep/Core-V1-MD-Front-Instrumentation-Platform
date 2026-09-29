"""Keyboard bindings used by the simulator in place of the physical jog wheel."""

from __future__ import annotations

from PySide6.QtCore import Qt

from core.controls import ControlEvent

Key = Qt.Key

CONTROL_KEYS: dict[Qt.Key, ControlEvent] = {
    Key.Key_Left: ControlEvent.ROTATE_LEFT,
    Key.Key_Up: ControlEvent.ROTATE_LEFT,
    Key.Key_Right: ControlEvent.ROTATE_RIGHT,
    Key.Key_Down: ControlEvent.ROTATE_RIGHT,
    Key.Key_Return: ControlEvent.PRESS,
    Key.Key_Enter: ControlEvent.PRESS,
    Key.Key_D: ControlEvent.DOUBLE_PRESS,
    Key.Key_L: ControlEvent.LONG_PRESS,
    Key.Key_Home: ControlEvent.HOME,
    Key.Key_H: ControlEvent.HOME,
    Key.Key_Backspace: ControlEvent.HOME,
}

# Space (and the left mouse button) behave like the real jog-wheel push switch:
# tap = PRESS, double-tap = DOUBLE_PRESS, hold = LONG_PRESS.
JOG_BUTTON_KEY = Key.Key_Space

# Simulator-only commands (never available on hardware).
COMMAND_KEYS: dict[Qt.Key, str] = {
    Key.Key_F1: "toggle_debug",
    Key.Key_T: "cycle_theme",
    Key.Key_Delete: "hide_focused",
    Key.Key_F12: "screenshot",
    Key.Key_1: "launch:Cyberpunk2077.exe",
    Key.Key_2: "launch:Code.exe",
    Key.Key_3: "launch:Blender.exe",
    Key.Key_0: "close_app",
    Key.Key_4: "toggle_network",
    Key.Key_5: "inject_heat",
    Key.Key_6: "stall_fan",
    Key.Key_7: "restore_fan",
    Key.Key_B: "boot",
    Key.Key_S: "shutdown",
    Key.Key_V: "next_visualiser",
    Key.Key_Escape: "quit",
}

HELP_TEXT = """\
Core V1-MD simulator controls
  Jog wheel      ←/↑ rotate left, →/↓ rotate right, mouse wheel
  Push switch    Space / left click (tap, double-tap, hold)
  Direct         Enter=PRESS  D=DOUBLE_PRESS  L=LONG_PRESS  H/Home=HOME
  Simulator      F1 debug  T theme  Del hide  F12 screenshot  V visualiser mode
  Scenarios      1 Cyberpunk  2 VS Code  3 Blender  0 close app
                 4 network  5 overheat  6 stall fan  7 restore fan
                 B boot  S shutdown  Esc quit
"""
