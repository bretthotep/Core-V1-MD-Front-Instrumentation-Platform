# Roadmap

## Milestone 0 — Simulator Framework

Establish the development environment and the display-agnostic core.

- [x] Repository structure, requirements, test harness
- [x] CI: lint, tests and headless render on Windows and Ubuntu
- [x] `DisplayDevice` abstraction with `SimulatorDisplay`, `OffscreenDisplay`, `FutureOledDisplay`
- [x] Resizable 240 × 1000 simulator window
- [x] Keyboard/mouse mapping to `ControlEvent`s
- [x] Debug overlay (F1)
- [x] Headless render + screenshot mode
- [ ] Record/replay of telemetry sessions for repeatable demos

**Done when:** the simulator runs on Windows, and the same `FrontPanel` renders to any
`DisplayDevice` without modification.

## Milestone 1 — Widget System

- [x] Widget base class, render context, EL drawing primitives
- [x] CPU, GPU, RAM, Clock, Network, Audio Visualiser, Application, System, Alert widgets
- [x] Pinned / rotating / hidden / expanded / collapsed states
- [x] Jog navigation, focus, auto-rotation, scroll-to-focus layout
- [x] JSON layout configuration
- [x] Persist user layout changes between sessions
- [ ] Storage and peripheral widgets

**Done when:** every widget renders in every state against real and missing data, and the
layout is fully navigable with the five control events plus HOME.

## Milestone 2 — Animation Engine

- [x] Engine with delays, targets (screen / widget) and theme-aware colours
- [x] Horizontal wipe, vertical wipe, sliding blocks, segment reveal, scan line, fade
- [x] Data-driven animation profiles with payload matching
- [x] Event-driven director (boot, shutdown, app launch/close, network, alerts)
- [ ] Widget-to-widget transitions on expand/collapse
- [ ] Profile hot-reload in the simulator

**Done when:** new application-specific animations can be added without code changes.

## Milestone 3 — Telemetry Integration

- [x] Provider interface, hub merging, threshold events, mock provider
- [x] Audio source interface and mock source
- [x] Live system provider (psutil): CPU load/clock/temperature, memory, uptime, fans
- [x] Network adapter statistics (auto-selected physical adapter, throughput, link state)
- [x] Configurable thresholds (`telemetry/thresholds.json`, `--thresholds`)
- [ ] LibreHardwareMonitor provider
- [ ] HWiNFO shared-memory provider
- [ ] Windows APIs: foreground window / process tracking
- [ ] WASAPI loopback audio + FFT

**Done when:** the simulator shows live data from the real PC with no widget changes.

## Milestone 4 — OLED Display Driver

- [x] `FutureOledDisplay` contract, RGB565 encoding, pixel-shift mitigation
- [ ] Select display module
- [ ] Implement a real `FrameTransport`
- [ ] Brightness schedule / ambient dimming
- [ ] Partial updates (dirty rectangles) if the link is bandwidth-limited

**Done when:** the panel shows the same frames as the simulator at a stable frame rate.

## Milestone 5 — ESP32 Front Panel Controller

- [x] Host-side protocol draft and parser
- [ ] Firmware: encoder, switch, HOME key, USB CDC reporting
- [ ] Serial transport and auto-reconnect on the host
- [ ] Optional: frame streaming through the ESP32

**Done when:** the jog wheel controls the simulator and panel with no perceptible latency.

## Milestone 6 — Physical Core V1 Integration

- [ ] Fascia mounting design for display, encoder and controller
- [ ] Airflow validation (before/after temperature comparison)
- [ ] Cable routing and power
- [ ] Windows service / tray app with auto-start
- [ ] Final industrial design polish

**Done when:** Core V1-MD runs on boot as an appliance with no measurable thermal penalty.
