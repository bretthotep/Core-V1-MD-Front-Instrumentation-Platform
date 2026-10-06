# Requirements

**Status:** Requirements baseline; hardware selection and physical acceptance remain **TBD**.  
**Architecture:** Windows host owns telemetry, application state, rendering, interaction semantics, and UI. The ESP32-S3 is a USB-connected hardware endpoint.

Status terms: **IMPLEMENTED** = present in host software; **PROTOTYPE** = exercised in simulator or tests only; **DESIGNED** = specified but not implemented/verified; **PLANNED** = future work; **TBD** = unresolved. None of the software prototype statuses imply that physical hardware has been tested.

## Functional requirements

| ID | Requirement | Status / implementation | Verification / acceptance |
|---|---|---|---|
| REQ-DISP-001 | Host shall compose the complete UI independently of a physical display. | **IMPLEMENTED** — `ui/` and `display/` abstractions. | Run `FrontPanel` with `OffscreenDisplay`; all existing panel tests pass. |
| REQ-DISP-002 | Display output shall support an initial/recovery full-frame synchronization. | **PROTOTYPE** — `FutureOledDisplay` sends full RGB565 frames to a recording transport. | Fake transport receives dimensions and exactly `width × height × 2` bytes; hardware sync remains **PLANNED**. |
| REQ-DISP-003 | Production updates shall support host-detected dirty rectangles as well as full frames. | **PROTOTYPE** — `DirtyRegionDetector` and opt-in region-capable `FutureOledDisplay`; no USB transport. | Tests cover no change, pixel, grouped/overlapping regions, and full-screen invalidation; measured physical update is a later gate. |
| REQ-DISP-004 | Each region update shall identify its position, dimensions, pixel format, payload length, and update/frame identity. | **PROTOTYPE/DESIGNED** — `FrameRegion` and packet codec implement host metadata; endpoint handling is designed. | Tests validate region bounds/length/format and packet framing; endpoint write validation is still required. |
| REQ-DISP-005 | Host shall negotiate display resolution and supported pixel formats before sending pixels. | **PROTOTYPE** — `display/session.py` negotiates the endpoint's native resolution and RGB565 big-endian. | Fake endpoint rejects unsupported capabilities/configurations; selected panel dimensions remain **TBD**. |
| REQ-DISP-006 | Host shall control display brightness and provide configurable idle dimming/blanking behavior. | Brightness forwarding is **PROTOTYPE**; schedule and blanking are **PLANNED**. | Fake display verifies level clamping and transitions; panel brightness response is hardware acceptance. |
| REQ-DISP-007 | OLED protection shall minimize unnecessary redraws and support configurable pixel shifting, dimming, and blanking without claiming to eliminate burn-in. | Pixel shift and mostly-black styling are **PROTOTYPE**; idle policy is **PLANNED**. | Deterministic policy tests plus long-duration physical retention testing; software cannot guarantee no burn-in. |
| REQ-TELEM-001 | Host shall collect CPU, GPU, memory, storage, fan, system temperature, network, and application/system status where providers expose them. | CPU, memory, network, partial system and mock GPU/application data are **IMPLEMENTED/PROTOTYPE**; storage and real GPU/application providers are **PLANNED**. | Independent provider tests; missing sections render safely as unavailable. |
| REQ-TELEM-002 | Telemetry providers shall be independently mockable, and one provider failure shall not crash display composition. | Poll exceptions are isolated by `TelemetryHub`; lifecycle fault isolation and cached stale-data policy are **PLANNED**. | Fake provider failure, timeout, missing-data, and recovery tests. |
| REQ-TELEM-003 | Slow providers shall perform slow acquisition asynchronously or return cached samples. | Interface contract is **DESIGNED**; existing `psutil` polling is synchronous and documented as non-blocking. | Delayed-provider test confirms frame loop remains responsive once asynchronous provider support is added. |
| REQ-UI-001 | Widgets shall consume host-provided snapshots and never access sensors or display transport directly. | **IMPLEMENTED** — `RenderContext` supplies `TelemetrySnapshot`. | Widget tests use snapshots/mocks without hardware dependencies. |
| REQ-UI-002 | Host shall own widget state, layout, composition, animation, navigation, and gesture interpretation. | **IMPLEMENTED** in host code; physical input is **PROTOTYPE**. | Same UI behavior is exercised by keyboard input and injected hardware events. |
| REQ-INPUT-001 | ESP32-S3 shall report raw encoder direction/steps and button edges; host shall interpret gestures and navigation. | Host jog/gesture logic and draft ASCII parser are **PROTOTYPE**; binary endpoint is **DESIGNED**. | Input tests verify event order and that host owns long/double-press semantics. |
| REQ-INPUT-002 | Host shall support encoder press, optional buttons, and a home action without embedding application navigation in firmware. | **PROTOTYPE/DESIGNED**. | Fake endpoint input sequence drives the same `ControlEvent` path as simulator controls. |
| REQ-SIM-001 | Simulator shall represent the target strip and permit alternate dimensions. | **IMPLEMENTED** — 240 × 1000 default and size options. | Headless renders and tests cover target and arbitrary resolutions. |
| REQ-SIM-002 | Simulator shall model update type, latency, refresh rate, loss, disconnection/reconnection, brightness, and input events. | **PROTOTYPE** — `SimulatedFrameTransport` models frame/region updates, latency, refresh limits, deterministic drops, reconnect, brightness, and raw input in memory. It is not yet exposed as interactive simulator controls. | Deterministic fake-transport tests reproduce faults and verify full resynchronization without hardware. |
| REQ-REC-001 | Host shall detect endpoint loss, reconnect, renegotiate capabilities, and force a full-frame resynchronization before resuming dirty updates. | **PROTOTYPE** — session state gates dirty updates on an acknowledged full frame and provides an explicit renegotiation entry point; transport loss detection is not implemented. | Fake session verifies renegotiation and full-sync gating; physical USB recovery remains acceptance testing. |
| REQ-UI-003 | Each visible fan shall have a consistent vector fan icon, stable name/identity, and adjacent measured speed with explicit RPM units; unavailable, stale, and stalled readings shall be distinct. | Icon/name/RPM rendering is **PROTOTYPE**; stale-state indication is **DESIGNED**. | Render zero, missing, long-name, and multiple-fan cases at supported sizes/themes; no overlap. Collapsed/limited views identify omitted fans rather than implying all are shown. |
| REQ-INPUT-003 | Dial navigation shall support view paging as well as jogging through visible, actionable elements within a view, with an explicit mode and persistent focus. | **DESIGNED**; current runtime navigates widget slots on a continuous strip, not pages or sub-elements. | Verify view → element → edit transitions, wrapping, back/home, hidden/disabled elements, and focus retention after refresh. |
| REQ-INPUT-004 | Click shall select a focused control; rotation shall stage increases/decreases or choose an action; a second click shall confirm. Back/long-press shall cancel the draft without a write. | **DESIGNED**; gallery interaction previews are not executable controls. | Verify both directions, bounded increments, cancel, timeout, double-click suppression, confirmation exactly once, and rejection feedback. |
| REQ-CTRL-001 | Fan controls shall expose only backend-supported modes (automatic curve, duty percentage, or RPM target), separately displaying measured RPM and requested target. Unsupported/read-only fans shall remain visible but non-editable. | **DESIGNED**; no fan-write backend exists. | Stable fan identity and units; min/max/step, minimum safe duty, unavailable control, stopped fan, mode switching, acknowledgment/readback, and failed-write tests. |
| REQ-MEDIA-001 | Supported media sessions shall expose meaningful jog actions: play/pause, previous/next, volume, and seek only when the session supports them. | **DESIGNED**; audio visualisation exists, media transport does not. | Verify active-session identity, supported action discovery, staged selection/confirmation, volume bounds, seek bounds, no-session/unsupported states, and session changes during editing. |
| REQ-SET-001 | Desktop app settings and a settings view on the device shall edit one host-owned, versioned settings model with independent switches for view paging, element jogging, fan control, media control, and advanced tuning. | **DESIGNED**; current layout persistence is not a feature-settings implementation. | Changing either surface updates the other; validate persistence/schema migration, defaults, corrupted state, concurrent edits, disconnected device, and reconnect resync. |
| REQ-SET-002 | Monitoring shall remain available when writes are disabled. Fan/media/tuning writes shall default off; enabling a feature shall not bypass missing capability, permission, or safety gates. Disabling shall cancel drafts and prevent queued writes. | **DESIGNED**. | Exercise each switch on both surfaces, restart, disabled control visibility, revocation during edit/commit, and the continued availability of settings/home. |
| REQ-TUNE-001 | Voltage and clock adjustments shall be an explicitly opted-in advanced feature, locked unless a supported, authorized backend supplies validated component-specific operating limits and live health data. | **DESIGNED**; backend and validated limits **TBD**. No hardware writes or universal safe voltage values are supplied. | Unknown hardware/limits, missing permissions, stale sensors, and unsupported settings must reject every write; validate voltage/clock coupling against an approved hardware profile. |
| REQ-TUNE-002 | All hardware writes shall pass host-side capability, settings, limit, health, and concurrency checks at confirmation, not just at draft creation; firmware and widgets shall not bypass that policy. | **DESIGNED**. | Reject non-finite/out-of-range values and excessive steps; test thermal/power/current/cooling interlocks, changed limits, concurrent app/device drafts, duplicate commands, and timeout/disconnect. |
| REQ-TUNE-003 | Tuning shall use conservative backend-approved increments, show current/requested values and units, require explicit risk acknowledgment and per-change confirmation, and verify acknowledgment plus readback before showing success. | **DESIGNED**. | Test cancel/no write, rejected writes, readback mismatch, instability, and bounded transaction timing; no silent retry or automatic replay after reconnect/reboot. |
| REQ-TUNE-004 | On unsafe health, failed verification, or instability, abort pending changes, lock further tuning, and attempt a verified backend-supported known-good rollback; show recovery failure and operator/firmware recovery guidance if rollback is unavailable. | **DESIGNED**; recovery support is a hardware acceptance gate. | Fault-injected backend tests plus supervised hardware tests; persist an audit of target, old/requested/readback values, limit-profile identity, and result. Never promise software can prevent all overclocking damage. |
| REQ-SIM-003 | The gallery shall cover fan presentation, element focus/edit/confirm/cancel, media navigation, app/device settings, disabled/read-only states, and locked tuning; design mockups shall be clearly distinguished from operational screens. | Fan visuals are **PROTOTYPE**; interaction/settings/tuning previews are **DESIGNED**. | Regenerate all existing scenes plus concept previews and contact sheet; screenshots are visual evidence only, not control or hardware acceptance. |

## Non-functional requirements

| ID | Requirement | Status | Verification / acceptance |
|---|---|---|---|
| REQ-PERF-001 | Implementation shall avoid assuming that full-frame streaming at the requested UI refresh rate fits USB or the display link. | **DESIGNED** — calculations in `PERFORMANCE.md`; no physical measurements. | Record link, display, CPU, memory, and update-rate measurements on selected hardware. |
| REQ-PERF-002 | Dirty-region transport shall avoid transmitting unchanged pixels in normal operation, with periodic/forced full-frame resynchronization available. | **PROTOTYPE** — `FutureOledDisplay` omits unchanged updates and supports forced full refresh; periodic resynchronization and physical transport validation remain **PLANNED**. | Tests verify unchanged updates are omitted and full refresh can be forced; validate periodic synchronization and performance on hardware. |
| REQ-PERF-003 | Host-to-visible-update and input-to-host latency shall be measured and reported separately. | **PLANNED**; target thresholds **TBD** until panel/transport selection. | Instrument timestamps at render, transport, display acknowledgment, input receive, and host dispatch. |
| REQ-REL-001 | Malformed, truncated, unsupported, or corrupt protocol messages shall not cause an invalid framebuffer write. | **DESIGNED** in `DISPLAY_PROTOCOL.md`. | Fuzz/negative packet tests; endpoint must reject out-of-bounds regions and invalid lengths. |
| REQ-REL-002 | Dropped/corrupt transfers shall be detectable, recoverable, and must not silently leave the host and display permanently divergent. | **DESIGNED**; ACK, sequence, CRC, timeout, and full-sync behavior are specified. | Deterministic packet-loss and reconnect tests; hardware recovery test after implementation. |
| REQ-MAINT-001 | Rendering, frame/region representation, detection, encoding, transport, and device responsibilities shall be independently testable. | Existing display boundary is **IMPLEMENTED**; region/protocol boundaries are **PROTOTYPE**. | Unit tests exercise region/protocol boundaries with fake transports; UI tests need no physical hardware. |
| REQ-EXT-001 | Protocol shall be versioned and permit capability negotiation and future message additions. | Versioned packet framing and host-side capability negotiation are **PROTOTYPE**; endpoint interoperability is not implemented. | Tests cover version validation and host negotiation against fake endpoint packets; physical endpoint compatibility remains planned. |
| REQ-TEST-001 | Most automated tests shall run without physical hardware using fakes for transport, display, telemetry, and input. | **PROTOTYPE** for region transport, protocol framing/reassembly/session state, simulator, and telemetry fakes; endpoint/device state simulation is **PLANNED**. | CI runs all software tests on Windows and Ubuntu without hardware. |
| REQ-PWR-001 | Display brightness and idle policy shall allow reduction of power during inactivity. | **PLANNED**; power target **TBD** until parts are selected and measured. | Measure endpoint, display, and total current at defined brightness/idle states. |
| REQ-THERM-001 | Integration shall not materially obstruct the Core V1 front intake or create unacceptable local heating. | **DESIGNED** constraint; thermal impact **TBD**. | Compare ambient and component temperatures with/without installed hardware under repeatable load. |
| REQ-USB-001 | USB shall provide host-to-controller display data and controller-to-host raw input/status, with reconnect recovery. | **DESIGNED**; data rate and physical implementation **TBD**. | Validate sustained payload and bidirectional operation on the selected board/cable. |
| REQ-SVC-001 | Hardware shall be serviceable: accessible programming/debug, replaceable modules/connectors where practical, and documented mounting/cabling. | **PLANNED** in `PCB_ARCHITECTURE.md`. | Review board layout and service procedure before PCB release. |

## Hardware requirements

| ID | Requirement | Status | Verification / acceptance |
|---|---|---|---|
| REQ-HW-001 | Preferred endpoint is an ESP32-S3 development board for the initial proof of concept; the host remains authoritative. | **DESIGNED**. | USB input/output, memory capacity, and display-interface proof of concept works before any custom PCB decision. |
| REQ-HW-002 | The chosen controller/module shall provide USB connectivity, sufficient flash, and PSRAM suitable for buffering the selected display/update strategy. | **TBD** — exact board/module and memory configuration not selected. | Verify datasheet, memory headroom under full/partial updates, and protocol throughput on the development board. |
| REQ-HW-003 | Controller-to-display interface shall support the selected panel's resolution, pixel format, brightness control, and required transfer rate. | **TBD** — panel/interface not selected. | Demonstrate full-frame sync and partial updates at measured target rates. |
| REQ-HW-004 | Hardware shall expose GPIO for a rotary encoder, push button(s), and future sensor expansion. | **DESIGNED**; pin assignment **TBD**. | Development-board input test; later schematic pin/function review. |
| REQ-HW-005 | Power regulation, USB protection, connectors, and thermal behavior shall suit the final display/controller combination. | **TBD**. | Electrical review and physical power/thermal measurements. |
| REQ-HW-006 | Custom PCB work shall start only after the development-board display/protocol proof of concept succeeds. | **PLANNED**. | Explicit POC acceptance review before schematic/layout work. |
| REQ-HW-007 | Display, board, and cabling shall fit the Core V1 fascia without entering the 200 mm fan's swept/intake path. | **TBD** — no dimensions or mount have been validated. | Measure case/fascia clearances and validate installed airflow and service access. |
| REQ-HW-008 | Physical module, FPC/connector, cable routing, and mounting shall be documented and replaceable/serviceable where possible. | **PLANNED**. | Mechanical inspection against the selected case and display drawings. |

## Traceability and acceptance gates

- Software behavior maps to source paths above and tests in `tests/`; exact test identifiers will be assigned as protocol and region tests are implemented.
- **POC gate:** development board plus selected display; USB negotiation, full-frame sync, dirty update, brightness, raw input, reconnect, and telemetry-independent host rendering all pass automated/fake tests and are demonstrated on hardware.
- **PCB gate:** only after the POC gate; schematic, layout, power, connector, and mechanical reviews are complete.
- **Core V1 gate:** physical mounting, airflow, thermal behavior, USB reliability, 24/72-hour operation, and OLED static-content behavior are measured. Simulator evidence does not satisfy these gates.
- Numeric refresh, latency, brightness, power, temperature, and physical-clearance thresholds remain **TBD** pending selected components and measured baselines.

## Dial interaction contract — DESIGNED

The current simulator retains its existing widget focus/size/pin controls. The following
replaces neither those controls nor the wire protocol until the host interaction controller
is implemented. The gallery depicts intended states only.

| State | Turn dial | Click | Back / long-press |
|---|---|---|---|
| View navigation | Previous/next view when paging is enabled | Enter element navigation | Home |
| Element navigation | Previous/next visible actionable element | Select editable control or enter its action chooser | Return to view navigation |
| Edit / action chooser | Stage a bounded value or choose a supported action; no write | Confirm one transaction after revalidation | Discard draft, return to element navigation |
| Pending confirmation | No additional edits or duplicate submissions | No duplicate write | Request cancellation only if backend supports it; never imply an applied write was undone |
| Result | Resume navigation after result is acknowledged | Dismiss success/error and return to element | Return to element navigation |

- Press handling must not reinterpret a confirmation as expand/pin or a second media action.
  Retain size/pin actions through an explicit layout menu outside an edit session.
- Auto-rotation/page changes pause during selection/edit/pending states. Focus uses stable
  element identities, not row indices; loss/hiding of the selected element cancels its draft.
- Drafts display original and requested values, units, bounds and a clear cancel hint.
  Inactivity before submission, host/device disconnect, capability loss, and settings
  revocation discard unsubmitted drafts; reconnect never submits them.
- Display visibility is not authorization. In-flight writes with unknown outcomes require
  readback/reconciliation, not blind retry. Safety monitoring continues when controls are off.
- Device settings are host-rendered and entered via the same dial. Without the host the
  device cannot authorize tuning or claim settings have been saved; resync on reconnect.
- There are no universally safe voltage/clock limits. Vendor/component-specific validated
  limits, cooling and recovery capability are prerequisites, not user-overridable warnings.
  Do not enable tuning merely because a fan slider works.
