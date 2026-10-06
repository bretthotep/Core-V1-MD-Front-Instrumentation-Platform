"""Render the UI proof-of-concept gallery (``docs/images/poc``).

Every scene is fully deterministic: seeded mock telemetry, a virtual frame
clock and a fixed wall-clock time, so re-running this after a design change
produces a clean visual diff of exactly what changed::

    python -m simulator.pocs                    # all scenes + contact sheet
    python -m simulator.pocs --only 03 06       # scenes whose slug starts with 03 / 06
    python -m simulator.pocs --out gallery     # somewhere else
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
class Concept:
    heading: str
    subtitle: str
    cards: tuple[tuple[str, tuple[str, ...]], ...]
    gestures: tuple[str, ...]
    fan_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class Scene:
    slug: str
    title: str
    caption: str
    capture_s: float
    actions: tuple[tuple[float, Action], ...] = ()
    argv: tuple[str, ...] = ()
    tags: tuple[str, ...] = field(default=())
    concept: Concept | None = None

    @property
    def image_label(self) -> str:
        return f"{'DESIGN' if self.concept else 'RENDER'} · {self.title}"


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
    Scene(
        "17-designed-fan-focus", "Fan · focus",
        "DESIGNED/MOCK: focus SYS fan group; mock named RPM readings. No fan write capability.", 0,
        concept=Concept("FAN FOCUS", "01 / FOCUS GROUP",
                        (("FOCUSED / SYSTEM", ("CPU · 1180 RPM", "CHASSIS · 860 RPM", "REAR · -- RPM")),
                         ("READ ONLY TODAY", ("Telemetry is not a control.", "PRESS proposes fan selection."))),
                        ("ROTATE  /  focus widget", "PRESS  /  enter fan list", "HOLD  /  leave focus"),
                        ("CPU", "CHASSIS", "REAR")),
    ),
    Scene(
        "18-designed-fan-select", "Fan · select",
        "DESIGNED/MOCK: jog chooses one named fan, PRESS proposes editing; missing readings remain -- RPM.", 0,
        concept=Concept("SELECT FAN", "02 / CHOOSE TARGET",
                        (("FAN LIST / CPU SELECTED", ("> CPU · 1180 RPM", "CHASSIS · 860 RPM", "REAR · -- RPM")),
                         ("READ ONLY / DESIGNED", ("UNSUPPORTED / no write capability.", "STALE / refresh before editing.", "Unavailable target stays read-only."))),
                        ("ROTATE  /  choose fan", "PRESS  /  edit selected fan", "HOLD  /  back to group"),
                        ("CPU", "CHASSIS", "REAR")),
    ),
    Scene(
        "19-designed-fan-edit", "Fan · edit",
        "DESIGNED/MOCK: turn stages an illustrative CPU duty draft from 50 % to 55 %, not a safe range or applied "
        "setting. Second click confirms (gated); chosen backend bounds TBD, so confirmation unavailable. "
        "Jog changes draft only; no control backend.", 0,
        concept=Concept("EDIT FAN", "03 / TURN STAGES DRAFT",
                        (("TARGET / CPU", ("CPU · 1180 RPM",)),
                         ("DRAFT POLICY", ("MODE  /  MANUAL (MOCK)", "DUTY / 50 % -> 55 % (MOCK)", "ILLUSTRATIVE / NOT APPLIED")),
                         ("CONFIRM / UNAVAILABLE", ("BACKEND BOUNDS / TBD", "No safe limits claimed.", "Validated capability required."))),
                        ("ROTATE  /  stage draft", "PRESS  /  confirm (gated)", "HOLD  /  discard draft"),
                        ("CPU",)),
    ),
    Scene(
        "20-designed-fan-confirm", "Fan · confirm",
        "DESIGNED/MOCK: confirmation-gate visual state for the second click, not an extra mandatory review click. "
        "Illustrative 50 % to 55 % duty draft is not a safe range; confirm unavailable pending validated bounds/"
        "capability/backend. Cancel discards draft; no write or success claim.", 0,
        concept=Concept("CONFIRM FAN DRAFT", "04 / SECOND CLICK GATED",
                        (("TARGET / CPU", ("CPU · 1180 RPM",)),
                         ("CHANGE SUMMARY", ("AUTO -> MANUAL (DRAFT)", "DUTY / 50 % -> 55 % (MOCK)")),
                         ("CONFIRM / UNAVAILABLE", ("FAN CONTROL / OFF", "BACKEND BOUNDS / TBD", "No safe limits claimed.", "CANCEL / discard the draft"))),
                        ("ROTATE  /  review choices", "PRESS  /  confirm gated", "HOLD  /  cancel draft"),
                        ("CPU",)),
    ),
    Scene(
        "21-designed-settings", "Shared settings",
        "DESIGNED/MOCK: separate COMPANION APP and DEVICE JOG panels share the same settings keys and draft model. "
        "VIEW PAGING and ELEMENT JOG default ON; FAN CONTROL, MEDIA CONTROL and ADV TUNING default OFF. "
        "Capability gates require validation, regardless of switch state. "
        "Static surfaces only; back/long press discards unsubmitted edits; no persistence/synchronization.", 0,
        concept=Concept("SHARED SETTINGS", "APP + DEVICE / ONE MODEL",
                        (("COMPANION APP / MOCK", ("VIEW PAGING  /  ON", "ELEMENT JOG  /  ON", "FAN CONTROL  /  OFF",
                                                   "MEDIA CONTROL  /  OFF", "ADV TUNING  /  OFF", "CAPABILITY / VALIDATION REQUIRED")),
                         ("DEVICE JOG / MOCK", ("VIEW PAGING  /  ON", "ELEMENT JOG  /  ON", "FAN CONTROL  /  OFF",
                                               "MEDIA CONTROL  /  OFF", "ADV TUNING  /  OFF", "CAPABILITY / VALIDATION REQUIRED"))),
                        ("ROTATE  /  choose setting", "PRESS  /  edit draft only", "BACK / HOLD  /  discard draft")),
    ),
    Scene(
        "22-designed-music-jog", "Music · jog",
        "DESIGNED/MOCK: first click selects the music volume element, turn stages a draft, second click confirms "
        "(gated), without a third review click. "
        "Confirm remains disabled with media writes OFF/no backend. Double press never fires media during edit; "
        "back/hold discards the unsubmitted draft. No playback, success or readback.", 0,
        concept=Concept("MUSIC / DRAFT", "SELECT -> TURN -> CONFIRM",
                        (("01 / SELECT ELEMENT", ("MUSIC / VOLUME SELECTED", "CLICK / enter draft editor")),
                         ("02 / TURN TO STAGE DRAFT", ("VOLUME / ONE DRAFT STEP", "Not sent to a media backend.", "DOUBLE PRESS / NO MEDIA ACTION")),
                         ("03 / CONFIRM DISABLED", ("SECOND CLICK / CONFIRM GATED", "MEDIA WRITE SWITCH / OFF", "BACK / HOLD discards the draft."))),
                        ("TURN  /  adjust draft only", "CLICK  /  confirm stays gated", "BACK / HOLD  /  discard draft")),
    ),
    Scene(
        "23-designed-voltage-locked", "Voltage · LOCKED",
        "DESIGNED/MOCK: voltage tuning LOCKED. No numeric voltage or safe range asserted; no editing, confirm, or "
        "write until per-device limits and a backend are validated.", 0,
        concept=Concept("VOLTAGE / LOCKED", "NO VALIDATED LIMITS / BACKEND",
                        (("LOCKED / READ ONLY", ("VOLTAGE  /  NOT ASSERTED", "SAFE RANGE  /  UNKNOWN",
                                               "TUNING WRITE SWITCH / OFF", "WRITE  /  DISABLED")),
                         ("UNLOCK REQUIREMENTS", ("Validated per-device bounds.", "Validated capability + backend.", "Explicit review and confirmation.")),
                         ("SAFETY CONTRACT / DESIGN", ("Reject unknown or stale limits.", "Error / rollback policy required.", "No safe numbers claimed here."))),
                        ("ROTATE  /  inspect requirements", "PRESS  /  no edit; stays locked", "HOLD  /  back")),
    ),
    Scene(
        "24-designed-fan-cancel", "Fan · CANCEL",
        "DESIGNED/MOCK: explicit CANCEL/back/long-press transition discards an unsubmitted fan draft and returns "
        "to fan selection. No command, success acknowledgement or applied-value readback.", 0,
        concept=Concept("CANCEL FAN DRAFT", "05 / BACK WITHOUT SUBMIT",
                        (("UNSUBMITTED / MOCK DRAFT", ("CPU · 1180 RPM", "MANUAL POLICY / DRAFT ONLY")),
                         ("CANCEL TRANSITION / DESIGN", ("BACK or LONG PRESS -> discard.", "RETURN / fan selection.", "DRAFT / cleared in this concept.")),
                         ("NO OPERATIONAL CLAIM", ("No command sent.", "No success acknowledgement.", "No applied-value readback."))),
                        ("BACK  /  discard draft", "LONG PRESS  /  discard draft", "RETURN  /  select a fan"),
                        ("CPU",)),
    ),
    Scene(
        "25-designed-view-paging", "View · paging",
        "DESIGNED/MOCK: jog pages instrument views rather than changing a value; visible page count and omitted "
        "fan count. Paging/jogging ON by default; no writes, layout persistence or runtime paging added.", 0,
        concept=Concept("VIEW PAGING", "PAGE 02 / 03  /  MOCK",
                        (("INSTRUMENT VIEW / SYSTEM", ("CPU · 1180 RPM", "CHASSIS · 860 RPM", "+ 4 MORE FANS / OTHER VIEW")),
                         ("NAVIGATION MODE / DESIGN", ("PAGING / ON; JOGGING / ON", "ROTATE / previous or next page.", "PRESS / focus, not edit a value.")),
                         ("NO WRITE SIDE EFFECT", ("Navigation never submits drafts.", "Back exits to instrument view."))),
                        ("ROTATE  /  previous / next", "PRESS  /  focus visible widget", "BACK / HOLD  /  exit paging"),
                        ("CPU", "CHASSIS")),
    ),
    Scene(
        "26-designed-media-navigation", "Media · navigate",
        "DESIGNED/MOCK: first click selects the music transport element, turn in the action chooser stages "
        "previous/next track or play/pause, second click confirms (gated), without a third review click. "
        "Confirm is disabled with media writes OFF/no backend. "
        "No double-press shortcut during edit; back/hold cancels without playback, success or readback.", 0,
        concept=Concept("MEDIA NAVIGATION", "ELEMENT -> ACTION -> CONFIRM",
                        (("TRANSPORT ACTION LIST", ("> PREVIOUS TRACK", "NEXT TRACK", "PLAY / PAUSE")),
                         ("STAGED ACTION / DESIGN", ("SELECT / transport element", "TURN / choose; never dispatch.", "PREVIOUS TRACK / DRAFT ONLY")),
                         ("CONFIRM / DISABLED", ("SECOND CLICK / CONFIRM GATED", "MEDIA WRITE SWITCH / OFF", "No playback change or readback."))),
                        ("TURN  /  choose draft action", "CLICK  /  confirm stays gated", "BACK / HOLD  /  discard draft")),
    ),
    Scene(
        "27-designed-fan-read-only", "Fan · read only",
        "DESIGNED/MOCK: selected REAR fan has unavailable RPM, UNSUPPORTED capability and STALE telemetry. "
        "The fan preview visibly disables EDIT/CONFIRM; fan writes OFF. Inspection/back only, with no backend "
        "action or applied-value claim. These availability states are designed, not runtime detection.", 0,
        concept=Concept("FAN / READ ONLY", "UNSUPPORTED + STALE / DESIGN",
                        (("SELECTED FAN / UNAVAILABLE", ("REAR · -- RPM",)),
                         ("READ ONLY / DESIGNED STATE", ("UNSUPPORTED / no capability.", "STALE / reading not validated.", "FAN WRITE SWITCH / OFF")),
                         ("EDIT + CONFIRM / DISABLED", ("CLICK / inspect reason only", "Refresh + validated limits needed.", "No draft submitted or readback."))),
                        ("TURN  /  inspect status", "CLICK  /  edit remains disabled", "BACK / HOLD  /  return to list"),
                        ("REAR",)),
    ),
)


def render_concept(concept: Concept, width: int = 240, height: int = 1000):
    """Standalone static design image, deliberately disconnected from FrontPanel."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage, QPainter, QPen

    from themes.theme import ThemeManager
    from widgets import primitives as p

    theme = ThemeManager().active
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(p.colour(theme, "background"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(width / 240, height / 1000)

    def label(y, text, role="primary", px=9):
        p.draw_label(painter, QRectF(14, y, 212, 20), text, theme, role, px=px)

    painter.fillRect(QRectF(0, 0, 240, 5), p.colour(theme, "alert"))
    label(18, "DESIGNED / MOCK", "alert", 12)
    label(45, "STATIC CONCEPT / NOT RUNTIME", "dim", 8)
    p.draw_rule(painter, 14, 226, 82, theme)
    label(101, concept.heading, "secondary", 13)
    label(134, concept.subtitle, "primary", 8)
    y = 184
    for title, rows in concept.cards:
        card_height = 48 + len(rows) * 29
        box = QRectF(10, y, 220, card_height)
        painter.setPen(QPen(p.colour(theme, "grid"), 1))
        painter.setBrush(p.colour(theme, "primary", 0.035))
        painter.drawRoundedRect(box, 6, 6)
        label(y + 10, title, "alert" if "LOCKED" in title or "UNAVAILABLE" in title else "primary", 8)
        for i, row in enumerate(rows):
            row_y = y + 40 + i * 29
            is_fan = any(row.lstrip("> ").startswith(f"{name} ·") for name in concept.fan_names)
            if is_fan:
                p.draw_fan_icon(painter, QRectF(16, row_y + 2, 16, 16), theme,
                                "dim" if "-- RPM" in row else "primary")
            p.draw_text(painter, QRectF(39 if is_fan else 16, row_y, 187 if is_fan else 210, 20),
                        row, p.display_font(theme, 11), p.colour(theme, "secondary"))
            if concept.heading == "SHARED SETTINGS" and row.endswith(("/  ON", "/  OFF")):
                enabled = row.endswith("/  ON")
                role = "primary" if enabled else "dim"
                painter.save()
                painter.setPen(QPen(p.colour(theme, role), 1))
                painter.setBrush(p.unlit(theme, role))
                painter.drawRoundedRect(QRectF(202, row_y + 5, 20, 10), 5, 5)
                painter.setBrush(p.colour(theme, role))
                painter.drawEllipse(QRectF(214 if enabled else 204, row_y + 7, 6, 6))
                painter.restore()
        y += card_height + 18
    p.draw_rule(painter, 14, 226, 772, theme)
    label(790, "JOG CONTRACT / PROPOSED", "primary", 9)
    for i, gesture in enumerate(concept.gestures):
        label(821 + i * 27, gesture, "secondary", 8)
    label(926, "NO DEVICE WRITES", "alert", 10)
    label(955, "DESIGN PREVIEW / NOT IMPLEMENTED", "dim", 8)
    painter.end()
    return image


def render_scene(scene: Scene, width: int = 240, height: int = 1000):
    """Render ``scene`` and return the captured ``QImage``."""
    if scene.concept is not None:
        return render_concept(scene.concept, width, height)

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
        "**RENDER** scenes use the real simulator pipeline (`FrontPanel` → `OffscreenDisplay`),",
        "with seeded mock telemetry and a fixed clock, not a live hardware connection.",
        "**DESIGN** scenes are standalone static QImages labelled **DESIGNED / MOCK** inside each image.",
        "They bypass FrontPanel and are proposed interaction contracts, not working controls.",
        "All images are 240 × 1000. Regenerate after any design change:",
        "",
        "```bash",
        "cd core-v1-md",
        "python -m simulator.pocs",
        "```",
        "",
        "Scenes are defined in `simulator/pocs.py`. Because rendering is deterministic, a git diff",
        "of this folder shows exactly which screens a change affected.",
        "Fan RPM bars are relative display meters, not validated control limits. Overflow fans are",
        "summarised as `+N` / `+N MORE FANS`; every visible fan has an icon, name and RPM units.",
        "Concept fan edits never send a command; confirm is unavailable. Settings do not persist",
        "or synchronize. Separate app and device panels show identical keys; fan/media/tuning",
        "write switches default OFF, while paging/jogging default ON (design only).",
        "Explicit CANCEL/back/long press discards unsubmitted drafts, with no success or applied",
        "readback claim. Unsupported/stale indications, view paging and media navigation are",
        "designed only. Shared editing contract: first click SELECT → turn STAGE → second click",
        "CONFIRM (gated). The confirmation-gate preview is not a third mandatory review click.",
        "Fan duty draft numbers are illustrative only, not safe limits; backend bounds remain TBD.",
        "Music gestures have no media backend. Voltage stays **LOCKED** until",
        "per-device bounds/capability and a write backend are validated; no safe voltage numbers",
        "are asserted. There is no implemented unlock, tuning, or rollback path in these previews.",
        "",
        "![Contact sheet](contact-sheet.png)",
        "",
        "| Scene | Type | Shows |",
        "|---|---|---|",
    ]
    lines += [f"| [{s.title}]({s.slug}.png) | {'DESIGNED / MOCK' if s.concept else 'FrontPanel render'} "
              f"| {s.caption} |" for s in scenes]
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
        contact_sheet(images, [s.image_label for s in scenes]).save(str(args.out / "contact-sheet.png"))
        write_gallery_readme(args.out, scenes)
        print("contact-sheet.png, README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
