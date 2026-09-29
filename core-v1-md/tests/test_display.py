from PySide6.QtGui import QColor, QImage

from display.device import DisplayDevice, OffscreenDisplay
from display.oled_display import FutureOledDisplay, NullTransport, to_rgb565
from display.simulator_display import SimulatorDisplay


def test_all_displays_share_the_interface():
    for device in (OffscreenDisplay(), SimulatorDisplay(), FutureOledDisplay()):
        assert isinstance(device, DisplayDevice)
        frame = QImage(device.size, QImage.Format.Format_RGB32)
        frame.fill(QColor("#00D8FF"))
        device.present(frame)


def test_offscreen_display_keeps_last_frame():
    display = OffscreenDisplay(10, 20)
    assert (display.size.width(), display.size.height()) == (10, 20)
    frame = QImage(10, 20, QImage.Format.Format_RGB32)
    frame.fill(QColor("#FF0000"))
    display.present(frame)
    assert display.frames_presented == 1
    assert QColor(display.last_frame.pixel(0, 0)) == QColor("#FF0000")


def test_rgb565_encoding_is_big_endian():
    frame = QImage(2, 1, QImage.Format.Format_RGB32)
    frame.setPixelColor(0, 0, QColor("#FF0000"))
    frame.setPixelColor(1, 0, QColor("#0000FF"))
    assert to_rgb565(frame) == bytes([0xF8, 0x00, 0x00, 0x1F])


def test_oled_display_sends_through_transport_with_pixel_shift():
    transport = NullTransport()
    oled = FutureOledDisplay(4, 4, transport, pixel_shift=True, shift_interval=1)
    frame = QImage(4, 4, QImage.Format.Format_RGB32)
    frame.fill(QColor("#FFFFFF"))
    oled.present(frame)  # no shift on the first frame
    width, height, payload = transport.last
    assert (width, height, len(payload)) == (4, 4, 32)
    assert payload[:2] == b"\xff\xff"
    oled.present(frame)  # shifted one pixel right → first column black
    assert transport.last[2][:2] == b"\x00\x00"
    oled.set_brightness(3.0)
    assert transport.brightness == 1.0
