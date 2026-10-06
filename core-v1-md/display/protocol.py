"""Version-1 binary framing and bounded update reassembly."""

from __future__ import annotations

import binascii
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum

from display.frame import FrameRegion

MAGIC = b"\xC1\x4D"
PROTOCOL_VERSION = 1
MAX_PACKET_SIZE = 1024
HEADER = struct.Struct(">2sBBHIIH")
CRC = struct.Struct(">H")
FRAGMENT = struct.Struct(">IHHII")
REGION = struct.Struct(">HHHHBBH")
FLAG_FRAGMENT = 0x0001
MAX_REASSEMBLED_MESSAGE = 4 * 1024 * 1024
MAX_FRAGMENTS = 8192


class ProtocolError(ValueError):
    """A packet or logical update is malformed or unsupported."""


class MessageType(IntEnum):
    HELLO = 0x01
    CAPABILITIES = 0x02
    CONFIGURE = 0x03
    CONFIGURED = 0x04
    FULL_FRAME = 0x05
    DIRTY_REGION = 0x06
    BRIGHTNESS = 0x07
    INPUT_EVENT = 0x08
    HEARTBEAT = 0x09
    ACK = 0x0A
    ERROR = 0x0B


@dataclass(frozen=True, slots=True)
class Packet:
    message_type: MessageType
    sequence: int
    frame_id: int = 0
    payload: bytes = b""
    flags: int = 0
    version: int = PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if not 0 <= self.sequence <= 0xFFFFFFFF:
            raise ValueError("sequence must fit in 32 bits")
        if not 0 <= self.frame_id <= 0xFFFFFFFF:
            raise ValueError("frame_id must fit in 32 bits")
        if not 0 <= self.flags <= 0xFFFF:
            raise ValueError("flags must fit in 16 bits")
        if not isinstance(self.payload, bytes):
            raise TypeError("payload must be bytes")


def encode_packet(packet: Packet) -> bytes:
    if packet.version != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version {packet.version}")
    if not isinstance(packet.message_type, MessageType):
        raise ProtocolError(f"unsupported message type {packet.message_type!r}")
    if packet.flags & ~FLAG_FRAGMENT:
        raise ProtocolError(f"unsupported flags 0x{packet.flags:04x}")
    payload_size = len(packet.payload)
    if payload_size > MAX_PACKET_SIZE - HEADER.size - CRC.size:
        raise ProtocolError("packet exceeds maximum size")
    header = HEADER.pack(
        MAGIC,
        packet.version,
        int(packet.message_type),
        packet.flags,
        packet.sequence,
        packet.frame_id,
        payload_size,
    )
    checksum = binascii.crc_hqx(header[2:] + packet.payload, 0xFFFF)
    return header + packet.payload + CRC.pack(checksum)


def decode_packet(data: bytes) -> Packet:
    if len(data) < HEADER.size + CRC.size:
        raise ProtocolError("truncated packet")
    if len(data) > MAX_PACKET_SIZE:
        raise ProtocolError("packet exceeds maximum size")
    magic, version, raw_type, flags, sequence, frame_id, payload_size = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise ProtocolError("invalid packet magic")
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version {version}")
    if flags & ~FLAG_FRAGMENT:
        raise ProtocolError(f"unsupported flags 0x{flags:04x}")
    expected_size = HEADER.size + payload_size + CRC.size
    if len(data) != expected_size:
        if len(data) < expected_size:
            raise ProtocolError(f"truncated packet: received {len(data)} bytes; expected {expected_size}")
        raise ProtocolError(f"packet length is {len(data)} bytes; expected {expected_size}")
    payload = data[HEADER.size : HEADER.size + payload_size]
    expected_crc = CRC.unpack_from(data, HEADER.size + payload_size)[0]
    actual_crc = binascii.crc_hqx(data[2 : HEADER.size] + payload, 0xFFFF)
    if actual_crc != expected_crc:
        raise ProtocolError("CRC mismatch")
    try:
        message_type = MessageType(raw_type)
    except ValueError as exc:
        raise ProtocolError(f"unsupported message type {raw_type}") from exc
    return Packet(message_type, sequence, frame_id, payload, flags, version)


class PacketStreamDecoder:
    """Buffer partial reads and emit complete packets from an arbitrary byte stream."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> tuple[Packet, ...]:
        self._buffer.extend(data)
        packets: list[Packet] = []
        while True:
            start = self._buffer.find(MAGIC)
            if start < 0:
                keep = 1 if self._buffer.endswith(MAGIC[:1]) else 0
                if keep:
                    self._buffer[:] = self._buffer[-1:]
                else:
                    self._buffer.clear()
                break
            if start:
                del self._buffer[:start]
            if len(self._buffer) < HEADER.size:
                break
            payload_size = HEADER.unpack_from(self._buffer)[-1]
            packet_size = HEADER.size + payload_size + CRC.size
            if packet_size > MAX_PACKET_SIZE:
                del self._buffer[0]
                continue
            if len(self._buffer) < packet_size:
                break
            raw = bytes(self._buffer[:packet_size])
            try:
                packet = decode_packet(raw)
            except ProtocolError:
                del self._buffer[0]
                continue
            del self._buffer[:packet_size]
            packets.append(packet)
        return tuple(packets)


def encode_region(region: FrameRegion) -> bytes:
    bounds = region.bounds
    row_bytes = bounds.width * region.pixel_format.bytes_per_pixel
    descriptor = REGION.pack(
        bounds.x,
        bounds.y,
        bounds.width,
        bounds.height,
        int(region.pixel_format),
        0,
        row_bytes,
    )
    return descriptor + region.payload


def fragment_message(
    message_type: MessageType,
    sequence: int,
    frame_id: int,
    payload: bytes,
) -> tuple[Packet, ...]:
    max_payload = MAX_PACKET_SIZE - HEADER.size - CRC.size
    if len(payload) <= max_payload:
        return (Packet(message_type, sequence, frame_id, payload),)
    if message_type not in (MessageType.FULL_FRAME, MessageType.DIRTY_REGION):
        raise ProtocolError("only pixel-update messages may be fragmented")
    if len(payload) > MAX_REASSEMBLED_MESSAGE:
        raise ProtocolError("logical message exceeds reassembly limit")
    chunk_size = max_payload - FRAGMENT.size
    count = (len(payload) + chunk_size - 1) // chunk_size
    if count > MAX_FRAGMENTS:
        raise ProtocolError("logical message requires too many fragments")
    message_sequence = sequence & 0xFFFFFFFF
    packets = []
    for index in range(count):
        offset = index * chunk_size
        chunk = payload[offset : offset + chunk_size]
        descriptor = FRAGMENT.pack(message_sequence, index, count, len(payload), offset)
        packets.append(
            Packet(
                message_type,
                (sequence + index) & 0xFFFFFFFF,
                frame_id,
                descriptor + chunk,
                FLAG_FRAGMENT,
            )
        )
    return tuple(packets)


@dataclass(frozen=True, slots=True)
class ReassembledMessage:
    message_type: MessageType
    frame_id: int
    sequence: int
    payload: bytes


@dataclass(slots=True)
class _Assembly:
    message_type: MessageType
    frame_id: int
    sequence: int
    fragment_count: int
    total_size: int
    updated_at: float
    fragments: dict[int, tuple[int, bytes]] = field(default_factory=dict)


class FragmentReassembler:
    """Reassemble bounded pixel updates and discard incomplete sets after a timeout."""

    def __init__(self, timeout_s: float = 2.0, max_inflight: int = 4) -> None:
        if timeout_s <= 0 or max_inflight < 1:
            raise ValueError("timeout_s and max_inflight must be positive")
        self.timeout_s = timeout_s
        self.max_inflight = max_inflight
        self._assemblies: dict[tuple[MessageType, int, int], _Assembly] = {}

    def add(self, packet: Packet, now: float | None = None) -> ReassembledMessage | None:
        now = time.monotonic() if now is None else now
        for key, assembly in tuple(self._assemblies.items()):
            if now - assembly.updated_at > self.timeout_s:
                del self._assemblies[key]

        if packet.flags & ~FLAG_FRAGMENT:
            raise ProtocolError(f"unsupported flags 0x{packet.flags:04x}")
        if not packet.flags & FLAG_FRAGMENT:
            if len(packet.payload) > MAX_PACKET_SIZE - HEADER.size - CRC.size:
                raise ProtocolError("packet exceeds maximum size")
            return ReassembledMessage(packet.message_type, packet.frame_id, packet.sequence, packet.payload)
        if packet.message_type not in (MessageType.FULL_FRAME, MessageType.DIRTY_REGION):
            raise ProtocolError("only pixel-update messages may be fragmented")
        if len(packet.payload) <= FRAGMENT.size:
            raise ProtocolError("fragment has no data")

        message_sequence, index, count, total_size, offset = FRAGMENT.unpack_from(packet.payload)
        chunk = packet.payload[FRAGMENT.size :]
        if (
            count == 0
            or count > MAX_FRAGMENTS
            or index >= count
            or total_size == 0
            or total_size > MAX_REASSEMBLED_MESSAGE
            or offset + len(chunk) > total_size
        ):
            raise ProtocolError("invalid fragment bounds")

        key = (packet.message_type, packet.frame_id, message_sequence)
        assembly = self._assemblies.get(key)
        if assembly is None:
            if len(self._assemblies) >= self.max_inflight:
                raise ProtocolError("too many fragmented updates in flight")
            assembly = _Assembly(packet.message_type, packet.frame_id, message_sequence, count, total_size, now)
            self._assemblies[key] = assembly
        elif assembly.fragment_count != count or assembly.total_size != total_size:
            del self._assemblies[key]
            raise ProtocolError("fragment metadata changed during reassembly")
        assembly.updated_at = now

        previous = assembly.fragments.get(index)
        if previous is not None:
            if previous != (offset, chunk):
                del self._assemblies[key]
                raise ProtocolError("conflicting duplicate fragment")
            return None
        for other_offset, other_chunk in assembly.fragments.values():
            if offset < other_offset + len(other_chunk) and other_offset < offset + len(chunk):
                del self._assemblies[key]
                raise ProtocolError("overlapping fragments")
        assembly.fragments[index] = (offset, chunk)
        if len(assembly.fragments) != assembly.fragment_count:
            return None

        ordered = sorted(assembly.fragments.values())
        cursor = 0
        output = bytearray()
        for fragment_offset, fragment in ordered:
            if fragment_offset != cursor:
                del self._assemblies[key]
                raise ProtocolError("fragment set has a gap or invalid coverage")
            output.extend(fragment)
            cursor += len(fragment)
        del self._assemblies[key]
        if cursor != assembly.total_size:
            raise ProtocolError("reassembled length does not match declared size")
        return ReassembledMessage(packet.message_type, packet.frame_id, assembly.sequence, bytes(output))
