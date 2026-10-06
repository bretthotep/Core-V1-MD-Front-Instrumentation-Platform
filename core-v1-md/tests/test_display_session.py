import pytest

from display.frame import DirtyRegion, FrameRegion, PixelFormat
from display.protocol import MessageType, Packet, ProtocolError, decode_packet, encode_packet
from display.session import (
    ACK_PAYLOAD,
    AckStatus,
    DisplaySession,
    EndpointCapabilities,
    SessionState,
    encode_capabilities,
    encode_configured,
)


def capabilities(width=4, height=3, packet_size=40, pixel_format_mask=1):
    return EndpointCapabilities(1, 0, packet_size, width, height, pixel_format_mask, 0, 0)


def establish_configured_session():
    session = DisplaySession(4, 3)
    hello = session.begin()
    assert hello.message_type is MessageType.HELLO
    configure, = session.receive(
        Packet(MessageType.CAPABILITIES, 0, payload=encode_capabilities(capabilities()))
    )
    assert configure.message_type is MessageType.CONFIGURE
    assert session.receive(
        Packet(MessageType.CONFIGURED, 1, payload=encode_configured(0, 4, 3, int(PixelFormat.RGB565_BE)))
    ) == ()
    assert session.state is SessionState.CONFIGURED
    return session


def ack(sequence, status=AckStatus.ACCEPTED):
    return Packet(MessageType.ACK, 0, payload=ACK_PAYLOAD.pack(sequence, int(status)))


def test_capability_negotiation_and_configuration_rejection():
    session = DisplaySession(4, 3)
    session.begin()
    session.receive(Packet(MessageType.CAPABILITIES, 1, payload=encode_capabilities(capabilities())))
    session.receive(Packet(MessageType.CONFIGURED, 2, payload=encode_configured(1, 0, 0, 0, reason=2)))
    assert session.state is SessionState.FAILED
    assert "reason 2" in session.error


@pytest.mark.parametrize(
    ("endpoint_capabilities", "message"),
    [
        (capabilities(width=5), "resolution"),
        (capabilities(pixel_format_mask=0), "RGB565"),
        (capabilities(packet_size=32), "packet size"),
    ],
)
def test_negotiation_rejects_incompatible_endpoint(endpoint_capabilities, message):
    session = DisplaySession(4, 3)
    session.begin()
    with pytest.raises(ProtocolError, match=message):
        session.receive(
            Packet(MessageType.CAPABILITIES, 1, payload=encode_capabilities(endpoint_capabilities))
        )
    assert session.state is SessionState.FAILED


def test_full_frame_ack_gates_dirty_updates_and_busy_can_be_retried():
    session = establish_configured_session()
    payload = bytes(range(24))
    full_packets = session.send_full_frame(payload, frame_id=10)
    assert len(full_packets) > 1
    assert all(len(encode_packet(packet)) <= 40 for packet in full_packets)
    with pytest.raises(ProtocolError, match="acknowledged full-frame"):
        session.send_dirty_region(
            FrameRegion(DirtyRegion(0, 0, 1, 1), PixelFormat.RGB565_BE, b"\x00\x00", 11)
        )

    logical_sequence = full_packets[0].sequence
    session.receive(ack(logical_sequence, AckStatus.BUSY))
    assert session.retry_pending() == full_packets
    session.receive(ack(logical_sequence, AckStatus.ACCEPTED))
    assert session.state is SessionState.READY

    dirty = FrameRegion(DirtyRegion(1, 1, 1, 1), PixelFormat.RGB565_BE, b"\x12\x34", 11)
    dirty_packets = session.send_dirty_region(dirty)
    assert decode_packet(encode_packet(dirty_packets[0])).message_type is MessageType.DIRTY_REGION
    session.receive(ack(dirty_packets[0].sequence, AckStatus.DUPLICATE))
    assert session.state is SessionState.READY
    with pytest.raises(ProtocolError, match="no outstanding"):
        session.retry_pending()


def test_ack_must_match_outstanding_update_and_rejection_fails_session():
    session = establish_configured_session()
    packets = session.send_full_frame(bytes(24), frame_id=1)
    with pytest.raises(ProtocolError, match="does not match"):
        session.receive(ack(packets[0].sequence + 1))

    session.receive(ack(packets[0].sequence, AckStatus.REJECTED))
    assert session.state is SessionState.FAILED
    assert "rejected display update" in session.error


def test_reconnect_restarts_negotiation_before_full_sync():
    session = establish_configured_session()
    hello = session.reconnect()
    assert hello.message_type is MessageType.HELLO
    assert session.state is SessionState.WAITING_FOR_CAPABILITIES
    with pytest.raises(ProtocolError, match="full-frame synchronization"):
        session.send_full_frame(bytes(24), frame_id=2)
