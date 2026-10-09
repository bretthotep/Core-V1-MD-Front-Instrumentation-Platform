# Roadmap

Status legend: `[ ] PLANNED`, `[~] IN PROGRESS`, `[x] COMPLETE`. Completion means the listed software/documentation acceptance has been met; it does not imply physical hardware validation. Hardware milestones require explicit hardware evidence.

## M0 — Repository audit [x] COMPLETE

- **Objective:** Understand existing architecture, behavior, test coverage, and risks before refactoring.
- **Dependencies:** Existing source, docs, and tests.
- **Deliverables:** `docs/ENGINEERING_ASSESSMENT.md` with implementation status, risks, inconsistencies, and staged recommendations.
- **Tests:** No code changes in this milestone; record existing CI/test commands.
- **Acceptance:** Audit distinguishes implemented software from prototype, planned hardware, and unknowns; no speculative refactor precedes assessment.
- **Known risks:** Audit may miss runtime behavior not covered by current tests.

## M1 — Requirements baseline [x] COMPLETE

- **Objective:** Establish uniquely identified functional, quality, and hardware requirements.
- **Dependencies:** M0.
- **Deliverables:** `docs/REQUIREMENTS.md`, traceability hints, POC/PCB/Core V1 acceptance gates.
- **Tests:** Documentation review; future protocol/test IDs to be mapped as implementation lands.
- **Acceptance:** Requirements state host-authoritative UI, dirty updates, recovery, simulator coverage, ESP32-S3 preference, and unverified physical constraints.
- **Known risks:** Numeric latency, refresh, power, thermal, and mechanical thresholds remain TBD until selection/measurement.

## M2 — Architecture and documentation alignment [x] COMPLETE

- **Objective:** Make all architecture/hardware/UI docs describe the same host-rendered USB-to-ESP32-S3 direction and clearly label status.
- **Dependencies:** M0 and M1.
- **Deliverables:** Align `README.md`, `ARCHITECTURE.md`, `HARDWARE.md`, `DESIGN_LANGUAGE.md`, `ROADMAP.md`; add `DISPLAY_PROTOCOL.md`, `PERFORMANCE.md`, and `PCB_ARCHITECTURE.md`.
- **Tests:** Review diagrams, links, status wording, and theoretical calculations; no physical acceptance.
- **Acceptance:** Diagrams distinguish host rendering from endpoint hardware, planned PCB is gated on POC, and no simulated behavior is called physical validation.
- **Known risks:** Performance assumptions and selected hardware remain provisional.

## M3 — Display boundary and frame representation [~] IN PROGRESS

- **Objective:** Separate rendering, composition, frame representation, region extraction, encoding, transport, and device concerns while preserving existing `FrontPanel`/`DisplayDevice` use.
- **Dependencies:** M1/M2 and baseline display tests.
- **Deliverables:** `PixelFormat`, `DirtyRegion`, `FrameRegion`, tile-based `DirtyRegionDetector`, optional region transport while retaining the full-frame transport contract.
- **Tests:** Resolution, image size, RGB565 byte order, region crops/bounds/length, no change, pixel, grouped/edge/full changes, full-frame compatibility, and offscreen regression.
- **Acceptance:** Existing simulator behavior is unchanged; a capable fake transport observes full synchronization followed by dirty updates; USB remains unimplemented.
- **Known risks:** QImage row stride, Qt conversion semantics, and panel-specific byte order must not be conflated.

## M4 — Versioned host/endpoint protocol [~] IN PROGRESS

- **Objective:** Implement deterministic framing and validation for capability/configuration, full/dirty updates, brightness, raw input, acknowledgements, heartbeat, and errors.
- **Dependencies:** M2 protocol design and M3 frame/region representation.
- **Deliverables:** Versioned host-side packet codec/stream decoder, CRC validation, pixel-update fragmentation/reassembly, and a documented wire contract. No endpoint or USB transport.
- **Tests:** Round trips, CRC, truncation, lengths, versions/types, partial stream reads, fragmentation/reassembly, invalid regions, reassembly bounds, capability/configuration negotiation, ACK correlation, busy retry, and full-frame-before-dirty gating.
- **Acceptance:** Malformed/corrupt messages cannot cause framebuffer writes; tests need no physical hardware.
- **Known risks:** Packet size, timeouts, and transport semantics must be checked against selected USB implementation.

## M5 — Dirty-region updates and simulated transport faults [~] IN PROGRESS

- **Objective:** Make host invalidation and region transport the normal update path; retain full-frame sync for boot, recovery, reset, and forced refresh.
- **Dependencies:** M3/M4.
- **Deliverables:** Deterministic tile-based dirty tracking/coalescing and opt-in region dispatch; in-memory `SimulatedFrameTransport` for latency, refresh-rate limits, drops, disconnect/reconnect, brightness, and raw input. Interactive simulator controls remain planned.
- **Tests:** No change, pixel, separated/adjacent/edge/full changes, initial sync, transport latency/rate, drop recovery, reconnect/full sync, brightness, and input are covered. Animation invalidation remains planned.
- **Acceptance:** Unchanged areas are not sent through a region-capable transport; simulated loss/reconnect returns the framebuffer to a full-frame baseline. Physical endpoint recovery remains planned.
- **Known risks:** Full-screen animation can approach full-frame traffic; region merging can increase transmitted pixels and needs measurement.

## M6 — ESP32-S3 development-board POC [ ] PLANNED

- **Objective:** Prove host USB protocol to a real ESP32-S3 board without designing custom PCB.
- **Dependencies:** M3–M5, selected ESP32-S3 board, and host tooling.
- **Deliverables:** Endpoint firmware for negotiation, packet handling, bounded buffering, display transfer stub/driver integration, status, and raw input.
- **Tests:** Host protocol suite, board-level input/loopback, malformed packet rejection, recovery and sustained-transfer tests.
- **Acceptance:** Board reports capabilities and raw inputs; receives and validates full/partial pixel updates; host can reconnect and resynchronize.
- **Known risks:** Exact USB mode, memory/DMA support, toolchain, display interface, and board availability are TBD.

## M7 — Physical display module validation [ ] PLANNED

- **Objective:** Select and operate a suitable narrow OLED/AMOLED with the POC board.
- **Dependencies:** M6 and a candidate panel/module.
- **Deliverables:** Measured resolution/format/byte order, interface timing, brightness behavior, update modes, power, and visible latency.
- **Tests:** Full-frame/dirty-region equivalence, all region edges, reset/recovery, brightness and static/animated scenes.
- **Acceptance:** Panel displays host-composed frames reliably at an agreed, measured workload; result is documented as MEASURED.
- **Known risks:** Datasheet assumptions, driver support, panel scan timing, burn-in, and module availability.

## M8 — Physical input integration [ ] PLANNED

- **Objective:** Integrate encoder and buttons as raw endpoint events, retaining host interpretation.
- **Dependencies:** M6 and input hardware.
- **Deliverables:** Debounced/raw event reporting, host transport connection, documented pin/electrical behavior.
- **Tests:** Direction, press/release ordering, bounce, malformed input, disconnect/reconnect, gesture classification on host.
- **Acceptance:** Host simulator/application navigation uses physical controls while firmware contains no menu/navigation policy.
- **Known risks:** Encoder wiring/noise, GPIO allocation, cable length, and event rate.

## M9 — Measured performance and OLED care [ ] PLANNED

- **Objective:** Optimize from measurements and establish brightness/idle/static-content behavior.
- **Dependencies:** M7 and M8.
- **Deliverables:** Workload measurements, dirty-region policy, refresh limits, brightness/dimming/blanking policy, long-run telemetry.
- **Tests:** Static UI, numeric updates, localized/full-screen animation, full sync, repeated loss/recovery; record throughput, latency, CPU, memory, power, and temperature.
- **Acceptance:** Agreed performance/power/thermal limits pass on selected hardware; values and test conditions reported as MEASURED.
- **Known risks:** No software strategy eliminates OLED burn-in; lifetime depends on panel and usage.

## M10 — Custom PCB [ ] PLANNED

- **Objective:** Design a serviceable endpoint PCB only after the development-board and panel POC is proven.
- **Dependencies:** M6–M9 and an approved component/interface/power/mechanical baseline.
- **Deliverables:** Schematic/layout, USB protection, regulation, display/encoder/button/sensor connectors, test points, programming/debug, status, mounting.
- **Tests:** Design-rule/electrical review; prototype bring-up and repeat of POC tests.
- **Acceptance:** PCB demonstrably reproduces validated POC behavior; schematic/layout and manufacturing files reviewed.
- **Known risks:** Component choices, signal integrity, power, thermal design, connectors, and mechanical fit.

## M11 — Core V1 physical integration [ ] PLANNED

- **Objective:** Integrate display, board, controls, cabling, and mounting into the case fascia.
- **Dependencies:** M10 and measured case/display dimensions.
- **Deliverables:** Mechanical mounting and service procedure, cable routing, airflow/power/thermal/noise/visibility assessment.
- **Tests:** Repeatable before/after load and temperature tests, cable/service inspection, USB and display recovery, visibility assessment.
- **Acceptance:** Assembly clears the fan's swept/intake path, meets agreed thermal/power constraints, remains serviceable, and operates reliably.
- **Known risks:** Fascia clearances, airflow restriction, local heat, vibration, viewing angle, cable strain.

## M12 — Long-duration, recovery, and burn-in observation [ ] PLANNED

- **Objective:** Establish reliability and observe static-content behavior over extended operation.
- **Dependencies:** M11.
- **Deliverables:** 24-hour and 72-hour test logs, repeated reconnect/failure results, OLED retention observations, unresolved-risk report.
- **Tests:** Telemetry/provider failure, USB/display failure, reboot, packet corruption/loss, repeated reconnection, brightness/blanking, static UI.
- **Acceptance:** Agreed reliability/recovery criteria pass; observations distinguish mitigation from guaranteed prevention of burn-in.
- **Known risks:** Long-term OLED aging cannot be conclusively established by short testing; panel-specific limits apply.

## M13 — View/element interaction and shared settings [ ] PLANNED

- **Objective:** Add optional view paging and dial selection/edit/confirmation without
  conflating control actions with current widget sizing/pinning.
- **Dependencies:** Host interaction contract in `REQUIREMENTS.md`; existing input abstractions.
- **Deliverables:** View/element/edit/pending/result controller, stable identities, paused
  auto-rotation during edits, explicit layout actions, and one versioned settings store used
  by desktop and device surfaces. Feature write switches default off.
- **Tests:** Both turn directions, bounded drafts, exactly-once confirmation, cancel/timeout,
  gesture conflicts, changed/hidden targets, settings revocation/concurrent updates,
  corrupted persistence and disconnect/reconnect without draft replay.
- **Acceptance:** REQ-INPUT-003/004 and REQ-SET-001/002 pass automated host tests.
  Gallery concept scenes are design evidence only and do not complete this milestone.
- **Known risks:** Conflicting input semantics and settings that appear to grant capabilities.

## M14 — Capability-gated fan and media adapters [ ] PLANNED

- **Objective:** Make supported displayed fan/media elements meaningfully actionable.
- **Dependencies:** M13; approved backend capability/permission discovery.
- **Deliverables:** Fan automatic/duty/RPM modes where supported, target versus measured
  readouts, read-only reasons, and supported active-session media actions.
- **Tests:** Safe fan minimum/maximum/steps, unsupported modes, stale sensors, stalls,
  acknowledgments/readback/failures; media session changes, volume/seek bounds and no session.
- **Acceptance:** REQ-CTRL-001 and REQ-MEDIA-001 pass fake tests and supervised integration
  tests before any write capability is enabled; monitoring works with all controls off.
- **Known risks:** Provider coverage varies by motherboard/fan controller and media session.

## M15 — Advanced tuning safety gate [ ] PLANNED

- **Objective:** Permit explicitly opted-in voltage/clock tuning only on validated hardware.
- **Dependencies:** M13/M14, component-specific validated profiles, authorized backend,
  fresh health telemetry and independently verified recovery support.
- **Deliverables:** Locked-by-default controls, risk acknowledgment, conservative increments,
  coupled voltage/clock validation, thermal/power/current/cooling interlocks, serialized
  transactions, verified readback, audit and known-good recovery workflow.
- **Tests:** Unknown limits/hardware, non-finite values, changed limits, stale/missing health,
  privilege loss, duplicate confirmation, revocation, disconnect, mismatch, instability,
  successful and failed rollback; supervised hardware tests using approved limits only.
- **Acceptance:** REQ-TUNE-001–004 pass an explicit safety review and hardware acceptance.
  Never substitute a universal voltage range or a screenshot for that gate.
- **Known risks:** Firmware/backend recovery may be unavailable; software cannot eliminate
  overclocking damage or recover every unstable machine.
