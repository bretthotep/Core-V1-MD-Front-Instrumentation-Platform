# Host ↔ display-controller protocol

**Status:** Version-1 wire format is **DESIGNED**; host-side packet codec, stream decoder, region descriptor, bounded fragment reassembler, and capability/configuration/ACK session flow are **PROTOTYPE**. USB transport and ESP32-S3 firmware are not implemented. `hardware/esp32.py` remains a separate **PROTOTYPE** ASCII input parser. The protocol is transport-independent and intended for USB between the Windows host and an ESP32-S3 hardware endpoint. It does not move UI composition or application state to the endpoint.

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
| 4 | 2 | Flags | `0x0001` marks a fragment; all other bits are reserved and rejected in version 1. |
| 6 | 4 | Sequence | Monotonically increasing packet sequence; wrap is modulo 2³². For fragmented updates, the descriptor repeats the first fragment's sequence as the logical update ID used for ACK correlation. |
| 10 | 4 | Frame/update ID | Groups all packet fragments for one rendered update. Zero for messages unrelated to a frame. |
| 14 | 2 | Payload length | Exact number of payload bytes; receiver validates before allocation/dispatch. |
| 16 | variable | Payload | Message-type-specific data. |
| 16 + length | 2 | CRC-16/CCITT-FALSE | Covers bytes from Version through end of Payload; excludes Magic and CRC. Initial value `0xFFFF`, polynomial `0x1021`, no reflection, xor-out `0x0000`. |

The fixed header is 16 bytes; the CRC is 2 bytes. Version 1's proposed maximum complete packet is **1024 bytes**, giving at most 1006 payload bytes per packet. This is a conservative protocol/design limit, not a measured USB or controller limit; validate and revise before firmware interoperability is claimed. Reject packets over the maximum, impossible lengths, bad magic/version/type/CRC, and truncated packets after the configured receive timeout. Do not allocate based on unchecked lengths.

### Message types

| Value | Message | Direction | Payload (version 1 proposal) |
|---:|---|---|---|
| `0x01` | `HELLO` | Host → endpoint | Minimum/maximum supported protocol version and host capability bits. |
| `0x02` | `CAPABILITIES` | Endpoint → host | Selected protocol version, endpoint capability bits, maximum encoded packet size, native resolution, pixel formats, input features, and display status. |
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

### Version 1 payload layouts

Unless noted otherwise, fields use network byte order. Fixed-size messages reject both missing
and trailing bytes. Capability masks and enum values not listed below are reserved; unknown
mandatory requirements cause negotiation failure.

| Message | Payload layout |
|---|---|
| `HELLO` | `minimum_version:u8`, `maximum_version:u8`, `host_capabilities:u32`. |
| `CAPABILITIES` | `selected_version:u8`, `endpoint_capabilities:u32`, `maximum_packet_size:u16`, `native_width:u16`, `native_height:u16`, `pixel_format_mask:u32`, `input_mask:u16`, `display_status:u8`. `maximum_packet_size` is the complete encoded packet size, including header and CRC. Version 1 advertises the attached panel's native resolution; a future version may list modes. |
| `CONFIGURE` | `width:u16`, `height:u16`, `pixel_format:u8` (`1` = RGB565 big-endian), `update_mode:u8` (`0` = full + dirty regions). |
| `CONFIGURED` | `status:u8` (`0` accepted, `1` rejected), `width:u16`, `height:u16`, `pixel_format:u8`, `reason:u8` (`0` none; other values reserved for documented rejection reasons). |
| `FULL_FRAME` / `DIRTY_REGION` | 12-byte region descriptor followed by exactly `row_bytes × height` packed pixel bytes, or that logical payload fragmented across packets. |
| `BRIGHTNESS` | `level:u16`, inclusive range `0..65535`. |
| `INPUT_EVENT` | `kind:u8`, `source_id:u8`, `delta:i16`. Kinds: `1` encoder delta (signed detent/step delta), `2` encoder press, `3` encoder release, `4` button press, `5` button release. Button events require `delta=0`; IDs identify the physical input only. |
| `HEARTBEAT` | `uptime_ms:u32`, `health_flags:u16`, `last_applied_frame_id:u32`. |
| `ACK` | `acknowledged_sequence:u32`, `status:u8` (`0` accepted, `1` duplicate, `2` busy, `3` rejected). |
| `ERROR` | `rejected_sequence:u32`, `error_code:u16`. Error-code assignments are versioned and reserved for defined protocol/device errors. |

Capability bit assignments other than the version-1 pixel-format mask, input/source ID
assignments, health flags, and detailed error codes remain **TBD** before firmware
interoperability. Pixel-format mask bit 0 represents enum value 1 (RGB565 big-endian).
The host session supports only that format and the negotiated native resolution. It rejects
an endpoint packet limit below what is needed to carry fragmented pixel data.

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

For fragmentation, each packet's payload starts with a 16-byte fragment descriptor: 4-byte logical update sequence (the first packet's sequence), 2-byte fragment index, 2-byte fragment count, 4-byte total message bytes, and 4-byte byte offset. Bytes after the descriptor are a contiguous slice of the logical message (the region descriptor plus pixel bytes). The logical update sequence and frame/update ID together identify the reassembly set; the logical update sequence is also retained for ACK correlation. With the proposed 1024-byte packet limit, a fragment has at most 990 data bytes. Receivers validate count, bounds, consistent metadata, non-overlapping offsets, complete coverage, and a bounded reassembly size before applying a region. Incomplete fragments expire on timeout and never partially update the visible panel.

Version 1 encodes packed RGB565 rows with no compression or implicit scaling. Dirty rectangles use coordinates in the negotiated logical display coordinate space. The host prototype bounds a reassembled logical message to 4 MiB, permits at most 8192 fragments and four in-flight assemblies, and expires incomplete sets after a default two seconds. These are software limits, not measured hardware timing/capacity.

## Acknowledgment, ordering, and duplicate behavior

- Each sender increments its packet sequence for every packet. ACK references the message sequence; for a fragmented update this is the first fragment's sequence, carried in every fragment descriptor. Frame/update ID groups pixel traffic across fragments.
- Endpoint ACKs accepted/rejected `CONFIGURE`, completed full-frame/dirty-region updates, and `BRIGHTNESS`; it may defer ACK until display transfer completion. Heartbeats and raw input events do not require per-message ACK.
- The host permits a bounded number of outstanding commands (initial proposal: one display update); exact timeout/window are **TBD** and measured on the selected transport.
- The host session permits one outstanding pixel update. It retains the exact packet set after a `busy` ACK for an explicit retry; ACKs for another sequence are rejected. Accepted/duplicate ACK of the initial full frame is required before dirty updates are permitted. Timeout scheduling and automatic retry/backoff are not implemented.
- A duplicate logical update sequence must not apply a pixel update twice. Cache a bounded recent response window and return `duplicate`/the prior result where possible. Sequence gaps alone do not imply a missing display update; update IDs and explicit ACK/timeouts govern recovery.
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

The protocol is designed to be tested with byte streams and fake endpoints. Host tests cover packet round trips, lengths, CRC, version/type validation, partial reads/multiple messages, bounded fragmentation/reassembly, capability/configuration negotiation, ACK correlation, busy retry, and full-frame gating of dirty updates. Endpoint tests should cover duplicate sequences, region application bounds/pixel byte counts, ACK/error behavior, disconnect/reconnect full resynchronization, and raw input event ordering. A passing fake-session test is not physical USB/panel validation.

## Migration

Keep `hardware/esp32.py` as a legacy input prototype until a serial transport and binary endpoint are implemented and tested. Do not repurpose its line parser as a display protocol. Preserve `DisplayDevice` and `FrontPanel` contracts while a transport adapter incrementally adds region delivery.
