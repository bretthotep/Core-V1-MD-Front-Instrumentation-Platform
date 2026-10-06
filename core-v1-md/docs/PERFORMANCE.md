# Display performance and bandwidth

**Status:** Calculations below are **THEORETICAL** unless explicitly marked otherwise. There are no **MEASURED** physical display, USB, SPI/QSPI, DMA, CPU, or latency results in this repository. Link efficiency, controller limits, and panel timing are **TBD** until components are selected and measured.

## Frame size and full-frame traffic

For the provisional 240 × 1000 logical display:

- Pixels per frame: `240 × 1000 = 240,000`
- RGB565: 16 bits/pixel = 2 bytes/pixel
- Uncompressed frame: `240,000 × 2 = 480,000 bytes` (about 469 KiB)
- No headers, checksums, USB framing, command bytes, retries, or padding are included below.

| Full-frame rate | Payload per second (decimal) | Payload bit rate (decimal) | Classification |
|---:|---:|---:|---|
| 1 FPS | 0.48 MB/s | 3.84 Mbit/s | THEORETICAL |
| 5 FPS | 2.40 MB/s | 19.20 Mbit/s | THEORETICAL |
| 10 FPS | 4.80 MB/s | 38.40 Mbit/s | THEORETICAL |
| 15 FPS | 7.20 MB/s | 57.60 Mbit/s | THEORETICAL |
| 20 FPS | 9.60 MB/s | 76.80 Mbit/s | THEORETICAL |
| 30 FPS | 14.40 MB/s | 115.20 Mbit/s | THEORETICAL |
| 60 FPS | 28.80 MB/s | 230.40 Mbit/s | THEORETICAL |

These are application payload requirements, not achieved USB or display rates. As reference link ceilings, USB 2.0 Full-Speed has a nominal raw line rate of 12 Mbit/s and High-Speed 480 Mbit/s; protocol and scheduling overhead make usable payload lower. Confirm the selected ESP32-S3 USB peripheral/mode and measured throughput rather than assuming High-Speed operation. The 5-FPS full-frame payload already exceeds a 12-Mbit/s raw line rate.

## Dirty-region examples

For one region covering fraction `p` of the display, uncompressed RGB565 payload is `480,000 × p` bytes. These sizes exclude packet headers, fragmentation overhead, checksums, and retransmission.

| Changed screen area | Pixels | Payload per update | At 10 updates/s | At 30 updates/s | Classification |
|---:|---:|---:|---:|---:|---|
| 5% | 12,000 | 24,000 bytes | 0.24 MB/s | 0.72 MB/s | THEORETICAL |
| 10% | 24,000 | 48,000 bytes | 0.48 MB/s | 1.44 MB/s | THEORETICAL |
| 25% | 60,000 | 120,000 bytes | 1.20 MB/s | 3.60 MB/s | THEORETICAL |
| 50% | 120,000 | 240,000 bytes | 2.40 MB/s | 7.20 MB/s | THEORETICAL |
| 100% | 240,000 | 480,000 bytes | 4.80 MB/s | 14.40 MB/s | THEORETICAL |

Illustrative rectangles, assuming tightly packed RGB565 rows:

| Example | Rectangle | Payload |
|---|---:|---:|
| Small value/readout change | 80 × 30 | 4,800 bytes |
| One narrow widget row | 240 × 100 | 48,000 bytes |
| Partial-height strip | 240 × 250 | 120,000 bytes |
| Full-screen synchronization | 240 × 1000 | 480,000 bytes |

These are examples, not measurements or claims about the application's typical changed area. Actual UI damage, coalescing, rectangle count, and packet overhead must be recorded from representative scenes. A mostly-static screen may be efficient if changed widgets are localized; full-screen animation can approach full-frame traffic and must be profiled.

## USB assumptions

- The intended topology is Windows host ↔ USB ↔ ESP32-S3 endpoint. The host retains rendered UI state; the endpoint receives pixel updates and sends raw input/status.
- USB nominal raw rates are not equivalent to bulk payload throughput. Driver scheduling, framing, endpoint configuration, implementation, retries, and shared bus activity affect actual transfer time.
- Do not assume continuous full-frame transfer at 30 or 60 FPS. Negotiate the link, use dirty regions for normal updates, and reserve full frames for initial sync, recovery, reset, and forced refresh.
- **TBD:** Confirm actual USB device mode on the selected development board; measure sustained bidirectional throughput and disconnect behavior with the intended host transport.

## SPI/QSPI display-interface requirements

The controller-to-panel side has a separate bandwidth budget from USB. For a serialized RGB565 pixel payload at frame rate `f`:

- Required payload bit rate: `480,000 × f × 8` bits/s.
- Ideal single-data-line SPI clock floor: payload bit rate divided by 1 data bit per clock.
- Ideal four-data-line QSPI clock floor: payload bit rate divided by 4 data bits per clock during quad data phases.
- These are theoretical lower bounds only; command/address phases, controller setup, panel windowing, transfer gaps, DMA descriptors, and bus/protocol timing increase the required time/clock. Actual module support and memory-write behavior are **TBD**.

The controller must use its supported DMA path for large display transfers where available. DMA reduces CPU copying/servicing during I/O but does not increase the USB link or panel's physical bandwidth. Measure both transfer completion and visible panel update time.

## Memory, PSRAM, and CPU

- A 240 × 1000 RGB565 full-frame buffer requires at least 480,000 bytes. Double buffering requires 960,000 bytes before alignment, protocol buffers, application state, stacks, and other firmware allocations.
- PSRAM is strongly preferred for controller-side framebuffer/region assembly, but usable capacity, bandwidth, cache constraints, and DMA accessibility depend on the selected module/board and must be verified. Do not assume all PSRAM can be used directly by a DMA engine.
- Host-side QImage storage and RGB565 conversion add allocations and copies beyond the wire payload. Region encoding should avoid converting unchanged pixels; benchmark before choosing copy/coalescing strategy.
- No CPU utilization estimate is asserted. Capture host and endpoint CPU utilization under static UI, animation, full sync, and reconnect workloads on the selected hardware.

## Latency and frame-rate expectations

- At `f` updates/s, the nominal update interval is `1/f` seconds; this is not end-to-end latency.
- A serial payload-only lower bound is `payload_bytes × 8 / measured_payload_bits_per_second`. Add render/encode time, protocol scheduling, endpoint processing, DMA queueing, panel scan/update behavior, and retries.
- The host simulator currently renders at a configurable nominal frame cadence. That does not prove the physical endpoint can accept or display at that rate.
- Candidate production behavior: send updates on UI invalidation, coalesce nearby rectangles, and cap animation update cadence according to measured headroom. The specific cap, acceptable latency, and refresh target are **TBD**.

## Workload classification

| Workload | Expected update path | Payload character | Evidence/status |
|---|---|---|---|
| Startup, reset, reconnect | Full-frame sync | Worst case: 480,000 bytes for provisional target | THEORETICAL size; transport time unmeasured |
| Mostly-static UI | Dirty rectangles | Potentially low if change is localized | ESTIMATED behavior; changed-area distribution not measured |
| Numeric telemetry changes | Dirty rectangles, coalesced by area | Small rectangles may dominate | ESTIMATED; application invalidation behavior not yet implemented |
| Localized widget reveal | Dirty rectangles | Depends on animation region and cadence | ESTIMATED; no physical animation throughput measurement |
| Full-screen animation / forced refresh | Full frame or many regions | Can approach worst-case frame rate table | THEORETICAL; measure before enabling at high rates |

## Measurement plan

After selecting the ESP32-S3 development board and panel, log separately: resolution/pixel format; bytes and rectangle count per update; USB payload rate; SPI/QSPI clock and utilization; encode/render time; ACK and visible-update latency; dropped/retried updates; host/endpoint CPU; peak internal/PSRAM use; brightness/current; and temperatures. Record each result as **MEASURED**, with board/module, firmware, host, workload, and test duration. No measured results are currently available.
