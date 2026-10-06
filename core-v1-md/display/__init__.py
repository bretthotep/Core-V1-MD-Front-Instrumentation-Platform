"""Display abstraction layer.

The compositor renders every frame into an off-screen ``QImage`` and hands it
to a :class:`DisplayDevice`. It never knows whether that device is a simulator
window, an off-screen buffer used by tests, or a physical OLED panel.
"""

from display.device import DisplayDevice, OffscreenDisplay
from display.dirty import DirtyRegionDetector
from display.frame import DirtyRegion, FrameRegion, PixelFormat
from display.oled_display import FrameTransport, FutureOledDisplay, NullTransport, to_rgb565
from display.protocol import MessageType, Packet, PacketStreamDecoder, ProtocolError
from display.simulator_display import SimulatorDisplay

__all__ = [
    "DirtyRegion",
    "DirtyRegionDetector",
    "DisplayDevice",
    "FrameTransport",
    "FrameRegion",
    "FutureOledDisplay",
    "MessageType",
    "NullTransport",
    "OffscreenDisplay",
    "Packet",
    "PacketStreamDecoder",
    "PixelFormat",
    "ProtocolError",
    "SimulatorDisplay",
    "to_rgb565",
]
