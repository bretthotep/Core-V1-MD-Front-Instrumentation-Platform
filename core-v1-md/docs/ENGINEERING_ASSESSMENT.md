# Engineering assessment

**Assessment date:** 2026-10-06  
**Scope:** Existing repository implementation under `core-v1-md/`; code, tests, and current documentation.  
**Status convention:** **IMPLEMENTED** is present in the repository; **PROTOTYPE** is software exercised only in simulation/tests; **DESIGNED** is documented architecture; **PLANNED** is future work; **TBD** requires a decision or measurement. This audit does not claim physical hardware validation.

## Executive summary

The repository is a functional Python/PySide6 simulator and instrumentation UI prototype. The host-side application is already separated into telemetry, widgets, composition, display sinks, and raw input handling. Mock telemetry, a live `psutil` provider, deterministic UI scenes, and an automated test suite exist.

The hardware-facing path is not yet a production display path: `FutureOledDisplay` supports optional RGB565 dirty-region dispatch, and host-side framing/reassembly and an in-memory simulated transport are software prototypes. The default transport only records full frames. The ESP32 module parses a small newline-delimited input-event draft; it does not negotiate capabilities or transport display data. The 240 × 1000 target is provisional. No ESP32-S3 firmware, selected panel, physical measurements, or custom PCB are present.

The requirements, protocol/performance assumptions, and host-side frame-region and protocol prototypes are now present. The next steps are to validate them against an endpoint implementation and hardware, while preserving the current simulator and `FrontPanel` contract.

## Findings

| ID | Severity | Finding |
|---|---|---|
| EA-001 | MEDIUM | `FutureOledDisplay` supports dirty-region dispatch when a transport opts in, but the default transport records full frames and no production USB/display transport exists. |
| EA-002 | HIGH | The theoretical bandwidth budget is documented in `PERFORMANCE.md`, but throughput has not been measured on selected hardware. Current code has no bandwidth guard or physical measurements. |
| EA-003 | HIGH | The ESP32 integration is only an input parser. `hardware/esp32.py` accepts ASCII `ROT`, `BTN`, `HOME`, and `HELLO` lines; it has no binary framing, capability negotiation, display updates, acknowledgements, reconnect state, or firmware. |
| EA-004 | HIGH | The physical architecture specifies a USB-connected ESP32-S3 endpoint, but the display module/interface, board/module, memory, power, cabling, mounting, and clearances are not selected or physically validated. |
| EA-005 | MEDIUM | The host prototype defines typed `FrameRegion` data and a region/protocol encoding boundary; interoperability and production transport behavior remain unvalidated. |
| EA-006 | MEDIUM | `SimulatedFrameTransport` exercises dirty regions, latency, dropped updates, disconnect/reconnect, brightness, and input in memory, but does not emulate a real endpoint or physical link. |
| EA-007 | MEDIUM | Telemetry polling is fault-tolerant during `poll()`, but lifecycle calls (`start()`/`stop()`) are not isolated per provider. The live `psutil` provider is polled by the frame-loop caller; providers requiring slow I/O must implement their own sampling/cache as the interface documentation requires. |
| EA-008 | MEDIUM | Automated tests cover host dirty regions, protocol framing/corruption/fragmentation, and simulated transport behavior; physical display reconnection and telemetry staleness remain untested. |
| EA-009 | LOW | Status wording is inconsistent. README and roadmap call physical output and ESP32 support “future”/draft, but mark parts of the contracts or parser complete; several documents do not consistently label implemented, prototype, designed, planned, and TBD work. |
| EA-010 | LOW | Performance, power, OLED lifetime/burn-in, airflow, latency, frame-rate, and physical dimensions are not measured. Existing notes include a sub-watt power target and zero/near-zero airflow impact without supporting measurements. |

## Current architecture

### Implemented host software

- `ui/panel.py` owns the frame loop and wires telemetry, event handling, widget state, animation, composition, and display presentation.
- `ui/compositor.py` produces a `QImage`; widgets consume a `TelemetrySnapshot` through their render context rather than reading hardware.
- `display/device.py` provides the `DisplayDevice` abstraction with offscreen and simulator sinks.
- `display/oled_display.py` provides prototype RGB565 conversion, optional dirty-region dispatch, a recording `NullTransport`, brightness forwarding, and optional pixel shifting.
- `telemetry/` provides immutable snapshot models, a provider interface, a mock provider, audio mocks, and a live `psutil` provider. The hub catches provider polling exceptions and merges successful sections.
- `hardware/` provides jog/press interpretation and a line-oriented host parser for the draft ESP32 input messages.
- `simulator/` supports the 240 × 1000 default geometry, alternate dimensions, mock/system telemetry modes, input mapping, and deterministic headless rendering.

### Existing validation

- Tests are in `core-v1-md/tests/`, run with `python -m pytest` from `core-v1-md/`; `tests/conftest.py` configures Qt offscreen mode.
- CI runs Ruff, pytest, headless rendering, and the proof-of-concept gallery on Windows and Ubuntu.
- UI proof-of-concept images are reproducible through `python -m simulator.pocs`.
- Passing repository tests establish software behavior only; they do not verify USB, ESP32-S3 firmware, panel timing, thermals, or burn-in behavior.

## Documentation and design inconsistencies

1. `README.md` describes an “ESP32-class” controller and an ASCII input protocol, and says frame streaming may be a later milestone. The target direction now requires ESP32-S3 as the preferred endpoint and host-rendered full/partial frame delivery.
2. `docs/HARDWARE.md` leaves direct PC display and a generic ESP32 as options. The selected design direction is USB between the Windows host and ESP32-S3; the actual module and display remain **TBD**.
3. `docs/ROADMAP.md` calls the host-side parser a protocol draft and partial-update support optional, but has no milestones for protocol negotiation, dirty updates, simulator link faults, or proof-of-concept gates before PCB design.
4. `docs/ARCHITECTURE.md` presents a clean rendering separation but stops at `QImage → DisplayDevice`; it does not describe composition-to-region detection-to-encoding-to-transport.
5. Existing documentation does not consistently distinguish a functioning simulator/prototype from a design intention or a physically tested result.

## Technical debt and risks

- Full-frame conversion allocates and copies the complete frame. At the provisional dimensions, a single RGB565 buffer is 480,000 bytes before Qt images, transport copies, or controller-side storage.
- RGB565 byte order is explicitly converted to big-endian in `to_rgb565()`, but the target controller/display byte-order contract remains **TBD** until an actual module is selected and validated.
- The host-side protocol prototype defines payload limits, region bounds, sequencing, fragmentation/reassembly, recovery, and acknowledgements; interoperability with an endpoint and physical transport remains unvalidated.
- `FutureOledDisplay` applies pixel shifting by copying a whole image; its interaction with partial updates needs validation before hardware use.
- The host-side update prototype avoids retransmitting unchanged regions, but animation invalidation and performance gains need validation on representative workloads.
- Error handling around telemetry polling is stronger than lifecycle handling; a provider raising from `start()` can interrupt startup before the display is usable.
- Hardware requirements such as power, heat, physical fit, connector selection, and airflow cannot be completed by simulator tests.

## Recommended incremental sequence

1. **M0 — Audit:** Preserve this assessment as the baseline; make no broad refactor before requirements and risks are captured.
2. **M1–M2 — Requirements and architecture:** Specify unique requirements, distinguish state/status, document the host-authoritative ESP32-S3 endpoint, and align README, architecture, hardware, design, and roadmap.
3. **M3–M5 — Host display boundary:** Host-side frame/region and protocol prototypes are implemented and tested; validate their contracts against a real endpoint while preserving `DisplayDevice` and `FrontPanel` behavior.
4. **Simulator:** Use fake transports/devices to exercise update selection, latency, loss, disconnect/reconnect, brightness, and input without hardware.
5. **M6–M9 — Hardware proof of concept and measurement:** Select a development board and display module, implement the endpoint, and measure throughput, latency, memory, CPU, and thermal behavior before optimizing.
6. **M10+ — Physical integration:** Design a custom PCB only after the board/display/protocol POC works; then validate mounting, airflow, power, long-duration operation, and OLED aging mitigations.

## Unverified items

- No physical display, ESP32-S3 development board, USB display transport, firmware, or custom PCB has been tested in this repository.
- The 240 × 1000 RGB565 display is a provisional target; interface, supported refresh rate, and panel-specific constraints are **TBD**.
- Bandwidth calculations in later documentation must be labeled as theoretical unless measured on selected hardware.
- Pixel shifting and mostly-black UI may reduce static exposure but do not eliminate OLED burn-in or establish panel lifetime.
