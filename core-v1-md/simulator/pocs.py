"""Render the UI proof-of-concept gallery (``docs/images/poc``).

Every scene is fully deterministic: seeded mock telemetry, a virtual frame
clock and a fixed wall-clock time, so re-running this after a design change
produces a clean visual diff of exactly what changed::

    python -m simulator.pocs                    # all scenes + contact sheet
    python -m simulator.pocs --only 03 06       # scenes whose slug starts with 03 / 06
    python -m simulator.pocs --out /tmp/pocs    # somewhere else
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from core.controls import ControlEvent
from core.events import EventType

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "images" / "poc"
FPS = 30
WALL_TIME = _dt.datetime(2026, 9, 29, 21, 47, 13)

Action = Callable[["Simulator"], None]  # noqa: F821 - resolved lazily (Qt import)


@dataclass(frozen=True)
class Scene:
    slug: str
    title: str
    caption: str
    capture_s: float
    actions: tuple[tuple[float, Action], ...] = ()
    argv: tuple[str, ...] = ()
    tags: tuple[str, ...] = field(default=())


def _control(*events: ControlEvent) -> Action:
    def run(sim) -> None:
        for event in events:
            sim.panel.handle_control(event)

    return run


def _command(name: str) -> Action:
    return lambda sim: sim.command(name)


def _visualiser(mode: str) -> Action:
    def run(sim) -> None:
        from widgets.audio_visualiser import AudioVisualiserWidget

        for widget in sim.panel.manager.widgets:
            if isinstance(widget, AudioVisualiserWidget):
                widget.set_mode(mode)

    return run


def _emit(event_type: EventType) -> Action:
    return lambda sim: sim.bus.emit(event_type)


SCENES: tuple[Scene, ...] = (
    Scene("01-idle", "Idle", "Default layout at rest: pinned clock and alert, instruments, Sony EL bar visualiser.", 5.0),
    Scene("02-boot", "Boot reveal", "SYSTEM_START: segment reveal with a scan-line sweep.", 0.6),
    Scene(
        "03-launch-cyberpunk",
        "App launch · Cyberpunk",
        "APP_LAUNCHED cyberpunk* → cinematic_reveal profile (amber sliding blocks).",
        4.3,
        ((4.0, _command("launch:Cyberpunk2077.exe")),),
    ),
    Scene(
        "04-launch-vscode",
        "App launch · VS Code",
        "APP_LAUNCHED code* → code_editor profile (stepped segment reveal).",
        4.25,
        ((4.0, _command("launch:Code.exe")),),
    ),
    Scene(
        "05-gaming-load",
        "Gaming load",
        "Cyberpunk running: GPU and CPU under load after the reveal has settled.",
        11.0,
        ((2.0, _command("launch:Cyberpunk2077.exe")),),
    ),
    Scene(
        "06-high-temp",
        "Critical · high temperature",
        "HIGH_TEMP → critical profile: red flash over the strip, alert widget in red.",
        7.75,
        ((3.0, _command("inject_heat")),),
    ),
    Scene(
        "07-network-down",
        "Network disconnected",
        "NETWORK_DISCONNECTED: link state and zero throughput.",
        5.0,
        ((4.0, _command("toggle_network")),),
    ),
    Scene(
        "08-fan-stall",
        "Warning · fan stalled",
        "LOW_FAN_SPEED → warning profile: amber blocks on the alert widget.",
        4.2,
        ((4.0, _command("stall_fan")),),
    ),
    Scene(
        "09-cpu-expanded",
        "Focus · CPU expanded",
        "Jog: rotate to CPU, PRESS to expand (per-core bars).",
        5.0,
        ((3.0, _control(ControlEvent.ROTATE_RIGHT, ControlEvent.ROTATE_RIGHT, ControlEvent.ROTATE_RIGHT)),
         (3.1, _control(ControlEvent.PRESS))),
    ),
    Scene(
        "10-collapsed",
        "Dense · collapsed",
        "Instruments collapsed to single lines for maximum density.",
        5.0,
        ((3.0, _control(ControlEvent.ROTATE_RIGHT, ControlEvent.ROTATE_RIGHT, ControlEvent.ROTATE_RIGHT,
                        ControlEvent.PRESS, ControlEvent.PRESS, ControlEvent.ROTATE_RIGHT,
                        ControlEvent.PRESS, ControlEvent.PRESS)),),
    ),
    Scene("11-debug-overlay", "Debug overlay", "F1: widget bounds, fps, last control and event.", 5.0, argv=("--debug",)),
    Scene("12-theme-es-mono", "Theme · Sony ES Mono", "Alternative theme, same widgets.", 5.0,
          argv=("--theme", "sony_es_mono")),
    Scene("13-vis-classic-bars", "Visualiser · Classic bars", "Classic spectrum bars.", 5.0,
          ((0.0, _visualiser("classic_bars")),)),
    Scene("14-vis-oscilloscope", "Visualiser · Oscilloscope", "Waveform trace.", 5.0,
          ((0.0, _visualiser("oscilloscope")),)),
    Scene("15-vis-network", "Visualiser · Network activity", "Throughput history in the visualiser slot.", 5.0,
          ((0.0, _visualiser("network_activity")),)),
    Scene(
        "16-shutdown",
        "Shutdown",
        "SYSTEM_SHUTDOWN: reverse vertical wipe.",
        5.45,
        ((5.0, _emit(EventType.SYSTEM_SHUTDOWN)),),
    ),
)


def render_scene(scene: Scene, width: int = 240, height: int = 1000):
    """Render ``scene`` and return the captured ``QImage``."""
    from display.device import OffscreenDisplay
    from simulator.app import Simulator, parse_args

    args = parse_args(["--headless", "--width", str(width), "--height", str(height), *scene.argv])
    clock = {"now": 0.0}
    sim = Simulator(args, OffscreenDisplay(width, height), clock=lambda: clock["now"])
    sim.panel.wall_clock = lambda: WALL_TIME + _dt.timedelta(seconds=clock["now"])
    sim.panel.perf_clock = lambda: 0.0  # debug overlay frame time would otherwise vary run to run
    pending = sorted(scene.actions, key=lambda a: a[0])
    sim.panel.start()
    frame = None
    total = round(scene.capture_s * FPS)
    for i in range(total + 1):
        clock["now"] = i / FPS
        while pending and pending[0][0] <= clock["now"] + 1e-9:
            pending.pop(0)[1](sim)
        frame = sim.panel.step()
    sim.panel.running = False  # skip the shutdown event; nothing is persisted in headless mode
    return frame.copy()


def contact_sheet(images: list, titles: list[str], columns: int = 6):
    """Lay the scenes out in a labelled grid on the theme background."""
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter

    from themes.theme import ThemeManager

    theme = ThemeManager().active
    w, h = images[0].width(), images[0].height()
    gap, label = 24, 34
    rows = (len(images) + columns - 1) // columns
    sheet = QImage(gap + columns * (w + gap), gap + rows * (h + label + gap), QImage.Format.Format_RGB32)
    sheet.fill(QColor(theme.colour("background")))
    painter = QPainter(sheet)
    font = QFont()
    font.setPixelSize(13)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    painter.setFont(font)
    for i, (image, title) in enumerate(zip(images, titles, strict=True)):
        x = gap + (i % columns) * (w + gap)
        y = gap + (i // columns) * (h + label + gap)
        painter.setPen(QColor(theme.colour("primary")))
        painter.drawText(QRect(x, y, w, label - 8), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         title.upper())
        painter.drawImage(x, y + label, image)
        painter.setPen(QColor(theme.colour("dim")))
        painter.drawRect(x - 1, y + label - 1, w + 1, h + 1)
    painter.end()
    return sheet


def write_gallery_readme(out: Path, scenes: list[Scene]) -> None:
    lines = [
        "# UI proof-of-concept renders",
        "",
        "Test designs rendered by the real simulator pipeline (`FrontPanel` → `OffscreenDisplay`),",
        "240 × 1000, with seeded mock telemetry and a fixed clock. Regenerate after any design change:",
        "",
        "```bash",
        "cd core-v1-md",
        "python -m simulator.pocs",
        "```",
        "",
        "Scenes are defined in `simulator/pocs.py`. Because rendering is deterministic, a git diff",
        "of this folder shows exactly which screens a change affected.",
        "",
        "![Contact sheet](contact-sheet.png)",
        "",
        "| Scene | Shows |",
        "|---|---|",
    ]
    lines += [f"| [{s.title}]({s.slug}.png) | {s.caption} |" for s in scenes]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m simulator.pocs", description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output folder (default {DEFAULT_OUT})")
    parser.add_argument("--only", nargs="*", default=None, help="render only scenes whose slug starts with these")
    args = parser.parse_args(argv)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841 - keeps Qt alive
    from simulator.app import register_fonts

    register_fonts()
    scenes = [s for s in SCENES if not args.only or any(s.slug.startswith(p) for p in args.only)]
    args.out.mkdir(parents=True, exist_ok=True)
    images = []
    for scene in scenes:
        image = render_scene(scene)
        image.save(str(args.out / f"{scene.slug}.png"))
        images.append(image)
        print(f"{scene.slug}.png  {scene.title}")
    if args.only is None:
        contact_sheet(images, [s.title for s in scenes]).save(str(args.out / "contact-sheet.png"))
        write_gallery_readme(args.out, scenes)
        print("contact-sheet.png, README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
