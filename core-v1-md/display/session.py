"""Host-side capability negotiation and acknowledgment-gated display session."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum, IntEnum, auto

from display.frame import DirtyRegion, FrameRegion, PixelFormat
from display.protocol import (
    CRC,
    FRAGMENT,
    HEADER,
    MAX_FRAGMENTS,
    MAX_PACKET_SIZE,
    MAX_REASSEMBLED_MESSAGE,
    MessageType,
    Packet,
    ProtocolError,
    REGION,
    encode_region,
    fragment_message,
)

HELLO_PAYLOAD = struct.Struct(">BBI")
CAPABILITIES_PAYLOAD = struct.Struct(">BIHHHIHB")
CONFIGURE_PAYLOAD = struct.Struct(">HHBB")
CONFIGURED_PAYLOAD = struct.Struct(">BHHBB")
ACK_PAYLOAD = struct.Struct(">IB")
HOST_MINIMUM_VERSION = 1
HOST_MAXIMUM_VERSION = 1
HOST_CAPABILITIES = 0
UPDATE_MODE_FULL_AND_DIRTY = 0


class SessionState(Enum):
    DISCONNECTED = auto()
    WAITING_FOR_CAPABILITIES = auto()
    WAITING_FOR_CONFIGURATION = auto()
    CONFIGURED = auto()
    WAITING_FOR_FULL_FRAME_ACK = auto()
    READY = auto()
    FAILED = auto()


class AckStatus(IntEnum):
    ACCEPTED = 0
    DUPLICATE = 1
    BUSY = 2
    REJECTED = 3


@dataclass(frozen=True, slots=True)
class EndpointCapabilities:
    selected_version: int
    endpoint_capabilities: int
    maximum_packet_size: int
    native_width: int
    native_height: int
    pixel_format_mask: int
    input_mask: int
    display_status: int

    @classmethod
    def decode(cls, payload: bytes) -> EndpointCapabilities:
        if len(payload) != CAPABILITIES_PAYLOAD.size:
            raise ProtocolError("invalid CAPABILITIES payload length")
        return cls(*CAPABILITIES_PAYLOAD.unpack(payload))


def encode_capabilities(capabilities: EndpointCapabilities) -> bytes:
    return CAPABILITIES_PAYLOAD.pack(
        capabilities.selected_version,
        capabilities.endpoint_capabilities,
        capabilities.maximum_packet_size,
        capabilities.native_width,
        capabilities.native_height,
        capabilities.pixel_format_mask,
        capabilities.input_mask,
        capabilities.display_status,
    )


def encode_configured(
    status: int,
    width: int,
    height: int,
    pixel_format: int,
    reason: int = 0,
) -> bytes:
    return CONFIGURED_PAYLOAD.pack(status, width, height, pixel_format, reason)


class DisplaySession:
    """Track host negotiation and prevent dirty updates before full-sync ACK."""

    def __init__(self, width: int, height: int) -> None:
        if not 0 < width <= 0xFFFF or not 0 < height <= 0xFFFF:
            raise ValueError("display dimensions must fit in 16 bits and be positive")
        if width * PixelFormat.RGB565_BE.bytes_per_pixel > 0xFFFF:
            raise ValueError("RGB565 row byte count must fit in 16 bits")
        self.width = width
        self.height = height
        self.state = SessionState.DISCONNECTED
        self.capabilities: EndpointCapabilities | None = None
        self.error: str | None = None
        self._sequence = 0
        self._pending: tuple[Packet, ...] = ()
        self._pending_sequence: int | None = None
        self._pending_is_full_sync = False

    def begin(self) -> Packet:
        if self.state is not SessionState.DISCONNECTED:
            raise ProtocolError("session can only begin while disconnected")
        payload = HELLO_PAYLOAD.pack(HOST_MINIMUM_VERSION, HOST_MAXIMUM_VERSION, HOST_CAPABILITIES)
        self.state = SessionState.WAITING_FOR_CAPABILITIES
        return self._packet(MessageType.HELLO, payload)

    def reconnect(self) -> Packet:
        self.state = SessionState.DISCONNECTED
        self.capabilities = None
        self.error = None
        self._pending = ()
        self._pending_sequence = None
        self._pending_is_full_sync = False
        return self.begin()

    def receive(self, packet: Packet) -> tuple[Packet, ...]:
        if self.state is SessionState.WAITING_FOR_CAPABILITIES:
            return self._receive_capabilities(packet)
        if self.state is SessionState.WAITING_FOR_CONFIGURATION:
            return self._receive_configured(packet)
        if self.state in (SessionState.WAITING_FOR_FULL_FRAME_ACK, SessionState.READY):
            return self._receive_ack(packet)
        raise ProtocolError(f"unexpected packet in session state {self.state.name}")

    def send_full_frame(self, payload: bytes, frame_id: int) -> tuple[Packet, ...]:
        if self.state not in (SessionState.CONFIGURED, SessionState.READY) or self._pending:
            raise ProtocolError("full-frame synchronization requires a configured session")
        region = FrameRegion(
            DirtyRegion(0, 0, self.width, self.height),
            PixelFormat.RGB565_BE,
            payload,
            frame_id,
        )
        return self._send_update(MessageType.FULL_FRAME, encode_region(region), frame_id, full_sync=True)

    def send_dirty_region(self, region: FrameRegion) -> tuple[Packet, ...]:
        if self.state is not SessionState.READY:
            raise ProtocolError("dirty updates require an acknowledged full-frame synchronization")
        if self._pending:
            raise ProtocolError("only one display update may be outstanding")
        if (
            region.pixel_format is not PixelFormat.RGB565_BE
            or region.bounds.x + region.bounds.width > self.width
            or region.bounds.y + region.bounds.height > self.height
        ):
            raise ProtocolError("dirty region is outside the negotiated display")
        return self._send_update(MessageType.DIRTY_REGION, encode_region(region), region.frame_id)

    def retry_pending(self) -> tuple[Packet, ...]:
        if not self._pending:
            raise ProtocolError("there is no outstanding update to retry")
        return self._pending

    def _receive_capabilities(self, packet: Packet) -> tuple[Packet, ...]:
        if packet.message_type is not MessageType.CAPABILITIES:
            raise ProtocolError("expected CAPABILITIES")
        capabilities = EndpointCapabilities.decode(packet.payload)
        if capabilities.selected_version != 1:
            return self._fail("endpoint selected an unsupported protocol version")
        if capabilities.native_width != self.width or capabilities.native_height != self.height:
            return self._fail("endpoint native resolution does not match the requested display")
        if not capabilities.pixel_format_mask & (1 << (PixelFormat.RGB565_BE - 1)):
            return self._fail("endpoint does not support RGB565 big-endian")
        minimum_packet_size = HEADER.size + CRC.size + FRAGMENT.size + 1
        if not minimum_packet_size <= capabilities.maximum_packet_size <= MAX_PACKET_SIZE:
            return self._fail("endpoint maximum packet size is unsupported")
        full_frame_size = REGION.size + self.width * self.height * PixelFormat.RGB565_BE.bytes_per_pixel
        max_payload = capabilities.maximum_packet_size - HEADER.size - CRC.size
        if full_frame_size <= max_payload:
            fragment_count = 1
        else:
            if full_frame_size > MAX_REASSEMBLED_MESSAGE:
                return self._fail("endpoint packet size cannot carry the requested full frame")
            fragment_payload = max_payload - FRAGMENT.size
            fragment_count = (full_frame_size + fragment_payload - 1) // fragment_payload
        if fragment_count > MAX_FRAGMENTS:
            return self._fail("endpoint packet size cannot carry the requested full frame")

        self.capabilities = capabilities
        payload = CONFIGURE_PAYLOAD.pack(
            self.width,
            self.height,
            int(PixelFormat.RGB565_BE),
            UPDATE_MODE_FULL_AND_DIRTY,
        )
        self.state = SessionState.WAITING_FOR_CONFIGURATION
        return (self._packet(MessageType.CONFIGURE, payload),)

    def _receive_configured(self, packet: Packet) -> tuple[Packet, ...]:
        if packet.message_type is not MessageType.CONFIGURED:
            raise ProtocolError("expected CONFIGURED")
        if len(packet.payload) != CONFIGURED_PAYLOAD.size:
            raise ProtocolError("invalid CONFIGURED payload length")
        status, width, height, pixel_format, reason = CONFIGURED_PAYLOAD.unpack(packet.payload)
        if status == 1:
            self.error = f"endpoint rejected display configuration (reason {reason})"
            self.state = SessionState.FAILED
            return ()
        if status != 0 or reason != 0:
            raise ProtocolError("invalid CONFIGURED status or reason")
        if (width, height, pixel_format) != (self.width, self.height, int(PixelFormat.RGB565_BE)):
            return self._fail("endpoint accepted a different display configuration")
        self.state = SessionState.CONFIGURED
        return ()

    def _receive_ack(self, packet: Packet) -> tuple[Packet, ...]:
        if packet.message_type is not MessageType.ACK:
            raise ProtocolError("expected ACK")
        if len(packet.payload) != ACK_PAYLOAD.size:
            raise ProtocolError("invalid ACK payload length")
        acknowledged_sequence, raw_status = ACK_PAYLOAD.unpack(packet.payload)
        try:
            status = AckStatus(raw_status)
        except ValueError as exc:
            raise ProtocolError(f"unsupported ACK status {raw_status}") from exc
        if self._pending_sequence is None or acknowledged_sequence != self._pending_sequence:
            raise ProtocolError("ACK does not match the outstanding display update")
        if status is AckStatus.BUSY:
            return ()
        if status is AckStatus.REJECTED:
            self.error = f"endpoint rejected display update {acknowledged_sequence}"
            self.state = SessionState.FAILED
            self._clear_pending()
            return ()
        if self._pending_is_full_sync:
            self.state = SessionState.READY
        self._clear_pending()
        return ()

    def _send_update(
        self,
        message_type: MessageType,
        payload: bytes,
        frame_id: int,
        full_sync: bool = False,
    ) -> tuple[Packet, ...]:
        if self.capabilities is None:
            raise ProtocolError("endpoint capabilities are unavailable")
        sequence = self._sequence
        packets = fragment_message(
            message_type,
            sequence,
            frame_id,
            payload,
            max_packet_size=self.capabilities.maximum_packet_size,
        )
        self._sequence = (self._sequence + len(packets)) & 0xFFFFFFFF
        self._pending = packets
        self._pending_sequence = sequence
        self._pending_is_full_sync = full_sync
        if full_sync:
            self.state = SessionState.WAITING_FOR_FULL_FRAME_ACK
        return packets

    def _packet(self, message_type: MessageType, payload: bytes) -> Packet:
        packet = Packet(message_type, self._sequence, payload=payload)
        self._sequence = (self._sequence + 1) & 0xFFFFFFFF
        return packet

    def _fail(self, reason: str) -> tuple[Packet, ...]:
        self.error = reason
        self.state = SessionState.FAILED
        raise ProtocolError(reason)

    def _clear_pending(self) -> None:
        self._pending = ()
        self._pending_sequence = None
        self._pending_is_full_sync = False
