# Host ↔ display-controller protocol

**Status:** **DESIGNED** version-1 proposal; no binary transport or ESP32-S3 firmware is implemented. `hardware/esp32.py` remains a separate **PROTOTYPE** ASCII input parser. The protocol is transport-independent and intended for USB between the Windows host and an ESP32-S3 hardware endpoint. It does not move UI composition or application state to the endpoint.

## Responsibilities

- **Host:** authoritative telemetry, widget state, layout, rendering, invalidation, region selection, RGB565 encoding, retransmission/recovery decisions, and interpretation of raw input into gestures/navigation.
- **ESP32-S3:** USB endpoint, message validation, capability/configuration response, small region/frame buffering, display-interface/DMA operations, brightness, raw encoder/button events, and hardware status.
- **Panel:** receives RGB565 pixels in negotiated coordinates. Exact panel interface, byte order, dimensions, and supported refresh behavior remain **TBD** until module selection.

## Packet framing (version 1 proposal)

All multibyte integer fields are unsigned big-endian network order. A transport read may return part of a packet or several packets; the receiver must buffer and parse by framing, not assume USB read boundaries equal message boundaries.

| Offset | Size | Field | Purpose |
|---:|---:|---|---|
| 0 | 2 | Magic `0xC1 0x4D` | Detect framing and reject unrelated/corrupt stream bytes. |
| 2 | 1 | Version | Selects packet/payload interpretation; initial value `1`. Unknown versions are rejected. |
| 3 | 1 | Message type | Identifies capability, configuration, pixel update, control, input, status, or error payload. |
| 4 | 2 | Flags | Reserved flags; unknown mandatory flags are rejected. Version 1 sends zero unless a defined flag applies. |
| 6 | 4 | Sequence | Monotonically increasing sender message identifier; correlates responses and detects duplicate/out-of-order commands. Wrap is modulo 2³². |
| 10 | 4 | Frame/update ID | Groups all packet fragments for one rendered update. Zero for messages unrelated to a frame. |
| 14 | 2 | Payload length | Exact number of payload bytes; receiver validates before allocation/dispatch. |
| 16 | variable | Payload | Message-type-specific data. |
| 16 + length | 2 | CRC-16/CCITT-FALSE | Covers bytes from Version through end of Payload; excludes Magic and CRC. Initial value `0xFFFF`, polynomial `0x1021`, no reflection, xor-out `0x0000`. |

The fixed header is 16 bytes; the CRC is 2 bytes. Version 1's proposed maximum complete packet is **1024 bytes**, giving at most 1006 payload bytes per packet. This is a conservative protocol/design limit, not a measured USB or controller limit; validate and revise before firmware interoperability is claimed. Reject packets over the maximum, impossible lengths, bad magic/version/type/CRC, and truncated packets after the configured receive timeout. Do not allocate based on unchecked lengths.

### Message types

| Value | Message | Direction | Payload (version 1 proposal) |
|---:|---|---|---|
| `0x01` | `HELLO` | Host → endpoint | Minimum/maximum supported protocol version and host capability bits. |
| `0x02` | `CAPABILITIES` | Endpoint → host | Selected protocol version, endpoint capability bits, maximum packet payload, supported resolutions, pixel formats, input features, and display status. |
| `0x03` | `CONFIGURE` | Host → endpoint | Width, height, selected pixel-format enum, and requested update mode. |
| `0x04` | `CONFIGURED` | Endpoint → host | Accepted dimensions/format/modes or a typed rejection reason. |
| `0x05` | `FULL_FRAME` | Host → endpoint | Region header for `(0,0,width,height)` followed by packed pixels, fragmented if required. |
| `0x06` | `DIRTY_REGION` | Host → endpoint | Region header and packed row-major pixels, fragmented if required. |
| `0x07` | `BRIGHTNESS` | Host → endpoint | Normalized 16-bit brightness value `0..65535`; mapping to physical panel output is hardware-specific. |
| `0x08` | `INPUT_EVENT` | Endpoint → host | Raw event kind and signed encoder delta or button identifier/state; no host navigation/gesture result. |
| `0x09` | `HEARTBEAT` | Bidirectional | Sender uptime/health flags and last accepted frame/update ID. |
| `0x0A` | `ACK` | Bidirectional | Acknowledged sequence and status (`accepted`, `duplicate`, `busy`, or `rejected`). |
| `0x0B` | `ERROR` | Bidirectional | Error code and rejected sequence/update ID when known. |

Version 1 pixel-format enum initially defines RGB565 only. Its byte order must be negotiated/documented for the selected panel; the host prototype currently creates big-endian RGB565. Capability negotiation prevents silently assuming unsupported formats, dimensions, or update modes.

## Region and fragmentation payloads

Unfragmented `FULL_FRAME` and `DIRTY_REGION` begin with this 12-byte region descriptor:

| Size | Field | Validation |
|---:|---|---|
| 2 | `x` | Region origin is within negotiated display. |
| 2 | `y` | Region origin is within negotiated display. |
| 2 | `width` | Non-zero; `x + width` does not exceed display width. |
| 2 | `height` | Non-zero; `y + height` does not exceed display height. |
| 1 | Pixel format | Must match negotiated format. |
| 1 | Region flags | Reserved; unknown mandatory flags are rejected. |
| 2 | Bytes per pixel row | Must equal `width × bytes_per_pixel` in version 1 (no implicit row padding). |
| remaining | Pixel bytes | Exact length must equal `row_bytes × height` when unfragmented. |

For fragmentation, each packet's payload starts with a 12-byte fragment descriptor: 2-byte fragment index, 2-byte fragment count, 4-byte total message bytes, and 4-byte byte offset. Bytes after the descriptor are a contiguous slice of the logical message (the region descriptor plus pixel bytes). The packet's frame/update ID identifies the reassembly set. With the proposed 1024-byte packet limit, a fragment has at most 994 data bytes. Receivers validate count, bounds, consistent metadata, non-overlapping offsets, complete coverage, and a bounded reassembly size before applying a region. Incomplete fragments expire on timeout and never partially update the visible panel.

Version 1 encodes packed RGB565 rows with no compression or implicit scaling. Dirty rectangles use coordinates in the negotiated logical display coordinate space.

## Acknowledgment, ordering, and duplicate behavior

- Each sender increments its sequence for every message. ACK references that sequence; frame/update ID groups pixel traffic across fragments.
- Endpoint ACKs accepted/rejected `CONFIGURE`, completed full-frame/dirty-region updates, and `BRIGHTNESS`; it may defer ACK until display transfer completion. Heartbeats and raw input events do not require per-message ACK.
- The host permits a bounded number of outstanding commands (initial proposal: one display update); exact timeout/window are **TBD** and measured on the selected transport.
- A duplicate sequence must not apply a pixel update twice. Cache a bounded recent response window and return `duplicate`/the prior result where possible. Sequence gaps alone do not imply a missing display update; update IDs and explicit ACK/timeouts govern recovery.
- Rejection, CRC failure, unsupported capability, malformed dimensions/length, reassembly failure, and endpoint busy conditions return an error or negative ACK where a valid header allows safe correlation. Invalid bytes are discarded/resynchronized at the next magic candidate without writing pixels.

## Startup, heartbeat, and recovery

```mermaid
sequenceDiagram
    participant H as Windows host
    participant U as USB link
    participant E as ESP32-S3 endpoint
    participant D as Display
    H->>U: HELLO (version range, host capabilities)
    U->>E: HELLO
    E-->>U: CAPABILITIES (protocol, resolution, format, limits, inputs)
    U-->>H: CAPABILITIES
    H->>U: CONFIGURE (resolution, RGB565, update mode)
    U->>E: CONFIGURE
    E->>D: initialize panel / display interface
    E-->>U: CONFIGURED (accepted or rejection)
    U-->>H: CONFIGURED
    H->>U: FULL_FRAME (initial synchronization; fragments as needed)
    U->>E: validated/reassembled full frame
    E->>D: DMA/display transfer
    E-->>H: ACK after accepted/display transfer
    loop UI invalidation
        H->>U: DIRTY_REGION (sequence + frame/update ID)
        U->>E: validate, reassemble, apply region
        E->>D: DMA/display transfer
        E-->>H: ACK
    end
    E-->>H: INPUT_EVENT (raw encoder/button event)
    loop connection monitoring
        H->>E: HEARTBEAT
        E-->>H: HEARTBEAT (health, last update)
    end
    Note over H,E: Timeout/disconnect: reopen USB, renegotiate, configure, then force a full-frame sync
```

- Heartbeat interval and timeout are configurable and **TBD** until transport tests; heartbeat contains no application/UI decision.
- After USB loss, heartbeat timeout, panel reset, CRC/reassembly failure that compromises frame state, or explicit recovery request, the host marks display state unsynchronized.
- Reconnect always restarts `HELLO → CAPABILITIES → CONFIGURE → FULL_FRAME`; do not resume dirty-only updates until the full frame is acknowledged.
- On unsupported version/capability, host reports a diagnosable error and does not send pixel payloads. Repeated failures use bounded retry/backoff; exact policy is **TBD**.

## Input event contract

Input event kinds are raw endpoint observations: encoder clockwise/counter-clockwise step delta, encoder press/release, and optional button press/release. The host may apply detent filtering, debounce/gesture timing, long/double press, menu behavior, focus, scrolling, and navigation. The firmware must not make UI navigation decisions.

## Verification without hardware

The protocol is designed to be tested with byte streams and fake endpoints. Tests should cover packet round trips; lengths, CRC, version/type validation; partial reads/multiple messages; duplicate sequences; capability/configuration rejection; region bounds and pixel byte counts; fragmentation/reassembly, timeout, overlaps and missing fragments; ACK/error behavior; disconnect/reconnect full resynchronization; and raw input event ordering. A passing fake-endpoint test is not physical USB/panel validation.

## Migration

Keep `hardware/esp32.py` as a legacy input prototype until a serial transport and binary endpoint are implemented and tested. Do not repurpose its line parser as a display protocol. Preserve `DisplayDevice` and `FrontPanel` contracts while a transport adapter incrementally adds region delivery.
