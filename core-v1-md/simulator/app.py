"""Simulator entry point.

Interactive::

    python -m simulator                  # 240x1000 window, 60 fps
    python -m simulator --debug --theme sony_es_mono
    python -m simulator --telemetry system   # live CPU/RAM/network from this PC

Headless (CI, screenshots, quick layout checks)::

    python -m simulator --headless --frames 180 --screenshot out.png --launch Cyberpunk2077.exe
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import os
import sys
import time
from pathlib import Path

from PySide6.QtGui import QFontDatabase

from core.events import EventBus, EventType
from display.device import DisplayDevice, OffscreenDisplay
from telemetry.audio import MockAudioSource
from telemetry.hub import TelemetryHub, Thresholds
from telemetry.mock_provider import MockTelemetryProvider
from telemetry.provider import SectionFilter, TelemetryProvider
from themes.theme import ThemeManager
from ui.layout_store import LayoutStateStore, default_state_path
from ui.panel import FrontPanel, load_layout
from widgets.audio_visualiser import AudioVisualiserWidget

log = logging.getLogger("core_v1_md.simulator")

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
SCREENSHOT_DIR = ROOT / "screenshots"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m simulator", description="Core V1-MD front panel simulator")
    parser.add_argument("--width", type=int, default=240, help="initial display width (default 240)")
    parser.add_argument("--height", type=int, default=1000, help="initial display height (default 1000)")
    parser.add_argument("--fps", type=float, default=60.0, help="frame rate (default 60)")
    parser.add_argument("--theme", default=None, help="theme id (default sony_minidisc)")
    parser.add_argument("--layout", type=Path, default=None, help="widget layout JSON")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="layout state file (default: per-user config dir; headless runs do not persist unless set)",
    )
    parser.add_argument("--no-persist", action="store_true", help="do not load or save layout changes")
    parser.add_argument("--debug", action="store_true", help="start with the debug overlay enabled")
    parser.add_argument("--seed", type=int, default=1234, help="mock telemetry seed")
    parser.add_argument(
        "--telemetry",
        choices=("mock", "system"),
        default="mock",
        help="mock: simulated data only; system: live CPU/RAM/network from this PC over the mock (default mock)",
    )
    parser.add_argument("--adapter", default=None, help="system telemetry: network adapter to monitor (default auto)")
    parser.add_argument("--thresholds", type=Path, default=None, help="alert thresholds JSON")
    parser.add_argument("--headless", action="store_true", help="render off-screen without a window")
    parser.add_argument("--frames", type=int, default=120, help="frames to render in headless mode")
    parser.add_argument("--screenshot", type=Path, default=None, help="save the final headless frame to this PNG")
    parser.add_argument("--launch", default=None, help="headless: mock-launch this application after boot")
    return parser.parse_args(argv)


def register_fonts() -> None:
    """Load any bundled fonts (assets/fonts/*.ttf|*.otf) so themes can reference them."""
    if not FONT_DIR.is_dir():
        return
    for path in sorted(FONT_DIR.iterdir()):
        if path.suffix.lower() in {".ttf", ".otf"}:
            QFontDatabase.addApplicationFont(str(path))


def build_providers(args: argparse.Namespace, mock: MockTelemetryProvider) -> list[TelemetryProvider]:
    """Provider stack for the chosen telemetry mode (later providers win on merge).

    In ``system`` mode only live data is shown for hardware; GPU renders ``--``
    until a GPU provider exists. The mock still supplies the application
    section so the launch/close scenario keys keep driving app animations.
    """
    if getattr(args, "telemetry", "mock") == "system":
        from telemetry.system_provider import SystemTelemetryProvider

        return [SectionFilter(mock, ["application"]), SystemTelemetryProvider(adapter=getattr(args, "adapter", None))]
    return [mock]


class Simulator:
    """Owns the panel plus the simulator-only mock providers and scenario commands."""

    def __init__(self, args: argparse.Namespace, display: DisplayDevice, clock=time.monotonic) -> None:
        self.args = args
        self.clock = clock
        self.bus = EventBus()
        self.mock = MockTelemetryProvider(seed=args.seed)
        thresholds = Thresholds.load(args.thresholds) if args.thresholds else None
        self.hub = TelemetryHub(self.bus, build_providers(args, self.mock), audio=MockAudioSource(), thresholds=thresholds)
        themes = ThemeManager(active=args.theme)
        layout = load_layout(args.layout) if args.layout else None
        store = LayoutStateStore(args.state_file) if args.state_file and not args.no_persist else None
        self.panel = FrontPanel(display, self.hub, self.bus, themes, layout, clock=clock, state_store=store)
        self.panel.compositor.debug = args.debug

    def command(self, name: str) -> None:
        now = self.clock()
        panel = self.panel
        if name.startswith("launch:"):
            self.mock.launch_app(name.split(":", 1)[1])
        elif name == "close_app":
            self.mock.close_app()
        elif name == "toggle_network":
            self.mock.toggle_network()
        elif name == "inject_heat":
            self.mock.inject_heat(now)
        elif name == "stall_fan":
            self.mock.stall_fan("SYS1")
        elif name == "restore_fan":
            self.mock.stall_fan(None)
        elif name == "toggle_debug":
            panel.compositor.debug = not panel.compositor.debug
        elif name == "cycle_theme":
            panel.themes.cycle()
        elif name == "hide_focused":
            focused = panel.manager.focused
            if focused is not None:
                panel.manager.hide(focused.id)
                panel.persist_layout()
        elif name == "next_visualiser":
            for widget in panel.manager.widgets:
                if isinstance(widget, AudioVisualiserWidget):
                    widget.next_mode()
        elif name == "boot":
            self.bus.emit(EventType.SYSTEM_START)
        elif name == "shutdown":
            self.bus.emit(EventType.SYSTEM_SHUTDOWN)
        elif name == "screenshot":
            SCREENSHOT_DIR.mkdir(exist_ok=True)
            path = SCREENSHOT_DIR / f"core-v1-md-{_dt.datetime.now():%Y%m%d-%H%M%S}.png"
            panel.step().save(str(path))
            log.info("Saved %s", path)
        panel.debug_info.lines = [f"cmd {name}"]


def run_headless(args: argparse.Namespace) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841 - keeps Qt alive
    register_fonts()
    frame_time = 1.0 / args.fps
    clock_state = {"now": 0.0}
    display = OffscreenDisplay(args.width, args.height)
    sim = Simulator(args, display, clock=lambda: clock_state["now"])
    sim.panel.start()
    launch_at = args.frames // 2 if args.launch else -1
    for i in range(args.frames):
        clock_state["now"] = i * frame_time
        if i == launch_at:
            sim.mock.launch_app(args.launch)
        sim.panel.step()
    if args.screenshot and display.last_frame is not None:
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        display.last_frame.save(str(args.screenshot))
        print(f"Saved {args.screenshot} ({display.last_frame.width()}x{display.last_frame.height()})")
    print(f"Rendered {display.frames_presented} frames; last event: {sim.panel.debug_info.last_event}")
    sim.panel.stop()
    return 0


def run_interactive(args: argparse.Namespace) -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from simulator.keymap import HELP_TEXT
    from simulator.window import KeyboardJogInput, SimulatorWindow

    app = QApplication.instance() or QApplication(sys.argv[:1])
    register_fonts()
    if args.state_file is None and not args.no_persist:
        args.state_file = default_state_path()
    if args.state_file and not args.no_persist:
        log.info("Layout state: %s (HOME twice restores defaults; --no-persist disables)", args.state_file)
    window = SimulatorWindow(args.width, args.height)
    sim = Simulator(args, window.display)

    def on_command(name: str) -> None:
        if name == "quit":
            window.close()
        else:
            sim.command(name)

    jog = KeyboardJogInput(on_command)
    jog.connect(sim.panel.handle_control)
    window.install_input(jog)

    def tick() -> None:
        jog.poll(time.monotonic())
        sim.panel.step()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(max(1, int(1000 / args.fps)))
    app.aboutToQuit.connect(sim.panel.stop)

    print(HELP_TEXT)
    window.show()
    sim.panel.start()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    return run_headless(args) if args.headless else run_interactive(args)
