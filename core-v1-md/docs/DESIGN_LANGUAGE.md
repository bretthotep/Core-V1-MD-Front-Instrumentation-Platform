# Design language

Core V1-MD borrows from late-1990s Sony MiniDisc decks and portables (MDS-JE/JA series,
MZ-R portables) and the ES component line: disciplined typography, electroluminescent
and fluorescent displays, brushed-black industrial surfaces.

## Principles

1. **Instrument, not dashboard.** Show what a skilled operator needs at a glance. No
   gauges-for-the-sake-of-gauges, no RGB, no gamer iconography.
2. **Dark by default.** Pure black background. On AMOLED, black pixels are off – the strip
   should look like tinted glass until something lights up.
3. **Colour means something.**
   - Cyan `#00D8FF` – the display itself: labels, frames, meters, focus.
   - White `#D8F8FF` – the values you read.
   - Amber `#FFD060` – warnings and approaching limits.
   - Red `#FF4040` – critical only.
4. **Information dense, not cluttered.** Tight vertical rhythm, small letter-spaced labels,
   large tabular numerals, generous black between groups.
5. **Physical honesty.** Unlit segments remain faintly visible (`unlit_alpha`), just like
   real EL/VFD glass. Meters are segmented, not smooth gradients.
6. **Motion is mechanical.** Wipes, shutters, scan lines and segment reveals. Easing is
   decisive (`out_cubic`, `out_expo`, stepped) – never springy.
7. **Application-aware, not application-specific.** Behaviour per application is expressed
   as animation profiles, not code.

## Typography

| Role | Usage | Default |
|---|---|---|
| Display | Numerals, titles, readouts | Monospace (`DejaVu Sans Mono` fallback) |
| Label | Tags, units, captions – uppercase, letter-spaced | Sans (`DejaVu Sans` fallback) |

Drop licensed/OFL fonts into `assets/fonts/` and reference them in a theme's `fonts`
section; the simulator registers them automatically. Theme font entries may be
comma-separated fallback lists.

## Components

- **Tag** – outlined uppercase label introducing each widget (`CPU`, `TIME`, `LEVEL`).
  Cyan when focused, dim cyan otherwise.
- **Value** – large white numerals with a small cyan unit suffix.
- **Segment bar** – horizontal meter; segments beyond 80 % turn amber, beyond 95 % red.
- **Vertical segment bar** – spectrum / per-core meter with optional peak-hold marker.
- **Sparkline** – thin cyan trace over a faint fill for history.
- **Focus mark** – a 2 px cyan bar on the left edge of the focused widget.
- **Pin mark** – a small cyan square at the top-right corner of pinned widgets.
- **Rotation dots** – small dashes at the bottom-right of the rotation slot, one per member.

## Motion catalogue

| Moment | Default profile |
|---|---|
| Boot | Segment reveal with a sweeping scan line |
| Shutdown | Vertical wipe to black |
| Application launched | Horizontal wipe on the Application widget |
| Game (e.g. `cyberpunk*`) | Amber sliding shutters, then an amber scan line |
| Editor (e.g. `code*`) | Fast stepped segment reveal |
| Rotation slot change | Horizontal wipe on the new widget |
| Network down | Amber shutters on the Network widget |
| High temperature | Red flash + shutters on the Alert widget |

## Do / don't

| Do | Don't |
|---|---|
| Use amber/red only for real alerts | Colour-code normal values |
| Keep unused pixels black | Add background textures or gradients |
| Prefer text + segments | Use icons, emoji or skeuomorphic dials |
| Animate state changes | Animate continuously for decoration |

## Narrow-strip layout examples

The sketches below communicate hierarchy and interaction rather than exact pixel geometry.
They show the intended black OLED canvas, cyan structure/focus, white readouts, and amber
warnings. The existing simulator gallery contains rendered **PROTOTYPE** scenes; it is not a
physical-panel validation.

```text
┌────────────────────────┐
│ CORE V1        ● READY │  compact system status
├────────────────────────┤
│┌ CPU ────────────────┐ │
││ 46%       61°C      │ │  current focus: cyan edge/outline
││ ████████░░░░░░░░    │ │  segmented, not gradient fill
│└─────────────────────┘ │
│┌ GPU ────────────────┐ │
││ 72%       68°C      │ │
││ ████████████░░░░    │ │
│└─────────────────────┘ │
│┌ RAM ────────────────┐ │
││ 18.4 / 32 GB        │ │
││ █████████░░░░░░░    │ │
│└─────────────────────┘ │
│┌ SYSTEM ─────────────┐ │
││ CPU  61°C   FAN 920 │ │
││ NET  2.1 MB/s       │ │
│└─────────────────────┘ │
│  ◉  ◉  ○  ○   rotate  │  subtle jog-wheel/focus hint
└────────────────────────┘
```

Focused-widget and warning states reserve warm colors for actual thresholds:

```text
┌────────────────────────┐       ┌────────────────────────┐
│ CORE V1        ● READY │       │ CORE V1      ! WARNING │
├────────────────────────┤       ├────────────────────────┤
│┌ CPU ────────────────┐ │       │┌ CPU ────────────────┐ │
││ 46%       61°C      │ │       ││ 96%       91°C      │ │
││ ████████░░░░░░░░    │ │       ││ ████████████████   │ │
│└─────────────────────┘ │       │└─────────────────────┘ │
│                         │       │  HIGH TEMPERATURE      │
│   CPU DETAIL / HISTORY  │       │  Check cooling status  │
│   history • clock • W   │       │  amber; red only for   │
│                         │       │  critical conditions   │
│  ◉  ◉  ○  ○             │       │  ◉  ◉  ○  ○             │
└────────────────────────┘       └────────────────────────┘
     focused / expanded                 alert / glanceable
```

## Layout and interaction rules

- Use a single narrow vertical reading order; keep the most actionable system state at the top
  and group CPU/GPU/memory/network details into short cards.
- Use tabular digits and short labels. Values remain legible before optional history or
  secondary readings.
- Focus is persistent and visible (left marker plus a stronger frame); encoder rotation moves
  focus, press expands/collapses or selects, and host software interprets gestures.
- Scroll rather than compressing every widget below the minimum readable height. Keep status,
  focus, and warning states distinguishable at low brightness.
- Animation should be event-driven and localized where possible so it supports glanceability
  and can later limit dirty-region traffic. The host remains the animation authority.
- Simulator dimensions are configurable. The 240 × 1000 logical target is provisional; exact
  type sizes, card heights, safe areas, viewing angle, and brightness must be checked against
  the selected physical panel.

### Status and OLED notes

- **IMPLEMENTED:** theme, widget, layout, and animation rendering in the host simulator.
- **PROTOTYPE:** static mock telemetry and reproducible narrow-strip gallery scenes.
- **DESIGNED:** mostly-black content, host-owned navigation, and localized change updates.
- **PLANNED:** measured idle dimming/blanking, physical brightness mapping, and animation/update
  tuning on selected hardware.
- **TBD:** panel luminance, viewing distance, pixel pitch, color behavior, and acceptable
  brightness/retention thresholds. Black UI and pixel shifting do not eliminate burn-in.
