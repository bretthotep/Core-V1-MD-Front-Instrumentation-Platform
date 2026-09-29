# UI proof-of-concept renders

Test designs rendered by the real simulator pipeline (`FrontPanel` → `OffscreenDisplay`),
240 × 1000, with seeded mock telemetry and a fixed clock. Regenerate after any design change:

```bash
cd core-v1-md
python -m simulator.pocs
```

Scenes are defined in `simulator/pocs.py`. Because rendering is deterministic, a git diff
of this folder shows exactly which screens a change affected.

![Contact sheet](contact-sheet.png)

| Scene | Shows |
|---|---|
| [Idle](01-idle.png) | Default layout at rest: pinned clock and alert, instruments, Sony EL bar visualiser. |
| [Boot reveal](02-boot.png) | SYSTEM_START: segment reveal with a scan-line sweep. |
| [App launch · Cyberpunk](03-launch-cyberpunk.png) | APP_LAUNCHED cyberpunk* → cinematic_reveal profile (amber sliding blocks). |
| [App launch · VS Code](04-launch-vscode.png) | APP_LAUNCHED code* → code_editor profile (stepped segment reveal). |
| [Gaming load](05-gaming-load.png) | Cyberpunk running: GPU and CPU under load after the reveal has settled. |
| [Critical · high temperature](06-high-temp.png) | HIGH_TEMP → critical profile: red flash over the strip, alert widget in red. |
| [Network disconnected](07-network-down.png) | NETWORK_DISCONNECTED: link state and zero throughput. |
| [Warning · fan stalled](08-fan-stall.png) | LOW_FAN_SPEED → warning profile: amber blocks on the alert widget. |
| [Focus · CPU expanded](09-cpu-expanded.png) | Jog: rotate to CPU, PRESS to expand (per-core bars). |
| [Dense · collapsed](10-collapsed.png) | Instruments collapsed to single lines for maximum density. |
| [Debug overlay](11-debug-overlay.png) | F1: widget bounds, fps, last control and event. |
| [Theme · Sony ES Mono](12-theme-es-mono.png) | Alternative theme, same widgets. |
| [Visualiser · Classic bars](13-vis-classic-bars.png) | Classic spectrum bars. |
| [Visualiser · Oscilloscope](14-vis-oscilloscope.png) | Waveform trace. |
| [Visualiser · Network activity](15-vis-network.png) | Throughput history in the visualiser slot. |
| [Shutdown](16-shutdown.png) | SYSTEM_SHUTDOWN: reverse vertical wipe. |
