import binascii

import pytest
from PySide6.QtGui import QColor, QImage

from display.frame import DirtyRegion, FrameRegion
from display.protocol import (
    CRC,
    FLAG_FRAGMENT,
    FRAGMENT,
    HEADER,
    FragmentReassembler,
    MessageType,
    Packet,
    PacketStreamDecoder,
    ProtocolError,
    decode_packet,
    encode_packet,
    encode_region,
    fragment_message,
)


def packet(message_type=MessageType.HELLO, payload=b"test"):
    return Packet(message_type, sequence=7, frame_id=12, payload=payload)


def test_packet_round_trip_and_checksum_validation():
    encoded = encode_packet(packet())
    assert decode_packet(encoded) == packet()

    corrupt = bytearray(encoded)
    corrupt[-3] ^= 0x01
    with pytest.raises(ProtocolError, match="CRC"):
        decode_packet(bytes(corrupt))


def test_packet_rejects_truncation_length_version_type_and_size():
    encoded = encode_packet(packet())
    with pytest.raises(ProtocolError, match="truncated"):
        decode_packet(encoded[:-1])
    with pytest.raises(ProtocolError, match="length"):
        decode_packet(encoded + b"\x00")

    unsupported_version = bytearray(encoded)
    unsupported_version[2] = 2
    with pytest.raises(ProtocolError, match="version"):
        decode_packet(bytes(unsupported_version))

    unsupported_type = bytearray(encoded)
    unsupported_type[3] = 0xFF
    header = bytes(unsupported_type[: HEADER.size])
    payload = bytes(unsupported_type[HEADER.size : -CRC.size])
    checksum = binascii.crc_hqx(header[2:HEADER.size] + payload, 0xFFFF)
    unsupported_type[-CRC.size :] = CRC.pack(checksum)
    with pytest.raises(ProtocolError, match="message type"):
        decode_packet(bytes(unsupported_type))

    with pytest.raises(ProtocolError, match="maximum"):
        decode_packet(b"\x00" * 1025)


def test_stream_decoder_accepts_partial_reads_and_multiple_packets():
    first, second = encode_packet(packet()), encode_packet(packet(MessageType.ACK, b"ack"))
    decoder = PacketStreamDecoder()
    assert decoder.feed(b"noise" + first[:5]) == ()
    assert decoder.feed(first[5:] + second) == (packet(), packet(MessageType.ACK, b"ack"))


def test_stream_decoder_retains_partial_magic_prefix():
    decoder = PacketStreamDecoder()
    encoded = encode_packet(packet())
    assert decoder.feed(b"\x00\xC1") == ()
    assert decoder.feed(encoded[1:]) == (packet(),)


def test_region_descriptor_contains_coordinates_format_and_row_length():
    image = QImage(3, 2, QImage.Format.Format_RGB32)
    image.fill(QColor("#000000"))
    region = FrameRegion.from_image(image, DirtyRegion(1, 1, 2, 1), frame_id=4)
    payload = encode_region(region)
    assert payload[:12] == bytes.fromhex("000100010002000101000004")
    assert len(payload) == 12 + 4


def test_fragmented_frame_reassembles_out_of_order_and_ignores_exact_duplicate():
    payload = bytes(range(251)) * 20
    fragments = fragment_message(MessageType.DIRTY_REGION, 100, 4, payload)
    assert len(fragments) > 1
    assert all(len(encode_packet(fragment)) <= 1024 for fragment in fragments)
    assert all(fragment.flags == FLAG_FRAGMENT for fragment in fragments)

    reassembler = FragmentReassembler()
    assert reassembler.add(fragments[-1], now=0.0) is None
    assert reassembler.add(fragments[-1], now=0.1) is None
    result = None
    for fragment in reversed(fragments[:-1]):
        result = reassembler.add(fragment, now=0.2)
    assert result is not None
    assert result.message_type is MessageType.DIRTY_REGION
    assert result.frame_id == 4
    assert result.payload == payload


def test_fragment_reassembler_rejects_overlap_and_expires_incomplete_updates():
    def fragment(index, offset, data):
        descriptor = FRAGMENT.pack(index, 2, 6, offset)
        return Packet(
            MessageType.FULL_FRAME,
            sequence=index,
            frame_id=1,
            payload=descriptor + data,
            flags=FLAG_FRAGMENT,
        )

    reassembler = FragmentReassembler(timeout_s=1.0)
    assert reassembler.add(fragment(0, 0, b"abcd"), now=0) is None
    with pytest.raises(ProtocolError, match="overlapping"):
        reassembler.add(fragment(1, 3, b"def"), now=0.1)

    reassembler.add(fragment(0, 0, b"abc"), now=0)
    assert reassembler.add(fragment(1, 3, b"def"), now=2.0) is None


def test_fragmentation_is_restricted_to_pixel_updates():
    with pytest.raises(ProtocolError, match="pixel-update"):
        fragment_message(MessageType.HELLO, 0, 0, b"x" * 2000)
    with pytest.raises(ProtocolError, match="reassembly limit"):
        fragment_message(MessageType.FULL_FRAME, 0, 0, b"x" * (4 * 1024 * 1024 + 1))
