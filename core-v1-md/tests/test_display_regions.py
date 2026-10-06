from PySide6.QtGui import QColor, QImage

from display.dirty import DirtyRegionDetector
from display.frame import DirtyRegion, FrameRegion, PixelFormat
from display.oled_display import FrameTransport, FutureOledDisplay


def image(width=64, height=64, colour="#000000"):
    frame = QImage(width, height, QImage.Format.Format_RGB32)
    frame.fill(QColor(colour))
    return frame


def test_dirty_region_detector_handles_initial_no_change_and_single_pixel():
    detector = DirtyRegionDetector(tile_width=16, tile_height=16)
    first = image()
    assert detector.detect(None, first) == (DirtyRegion(0, 0, 64, 64),)
    assert detector.detect(first, first.copy()) == ()

    changed = first.copy()
    changed.setPixelColor(19, 21, QColor("#FFFFFF"))
    assert detector.detect(first, changed) == (DirtyRegion(16, 16, 16, 16),)


def test_dirty_region_detector_separates_distant_changes():
    detector = DirtyRegionDetector(tile_width=16, tile_height=16)
    first = image()
    changed = first.copy()
    changed.setPixelColor(1, 1, QColor("#FFFFFF"))
    changed.setPixelColor(50, 50, QColor("#FFFFFF"))
    assert detector.detect(first, changed) == (
        DirtyRegion(0, 0, 16, 16),
        DirtyRegion(48, 48, 16, 16),
    )


def test_dirty_region_detector_coalesces_adjacent_tiles():
    detector = DirtyRegionDetector(tile_width=16, tile_height=16, full_frame_ratio=1.0)
    first = image(width=64, height=64)
    changed = first.copy()
    for y in range(32):
        for x in range(32):
            changed.setPixelColor(x, y, QColor("#FFFFFF"))
    assert detector.detect(first, changed) == (DirtyRegion(0, 0, 32, 32),)


def test_dirty_region_detector_clips_partial_edge_tiles():
    detector = DirtyRegionDetector(tile_width=16, tile_height=16, full_frame_ratio=1.0)
    first = image(width=35, height=19)
    changed = first.copy()
    changed.setPixelColor(34, 18, QColor("#FFFFFF"))
    assert detector.detect(first, changed) == (DirtyRegion(32, 16, 3, 3),)


def test_dirty_region_detector_falls_back_to_full_frame_at_threshold():
    detector = DirtyRegionDetector(tile_width=16, tile_height=16, full_frame_ratio=0.5)
    first = image()
    changed = first.copy()
    for y in range(64):
        for x in range(32):
            changed.setPixelColor(x, y, QColor("#FFFFFF"))
    assert detector.detect(first, changed) == (DirtyRegion(0, 0, 64, 64),)


def test_frame_region_has_tightly_packed_rgb565_payload_and_valid_bounds():
    frame = image(4, 2)
    frame.setPixelColor(2, 1, QColor("#FF0000"))
    region = FrameRegion.from_image(frame, DirtyRegion(2, 1, 2, 1), frame_id=9)
    assert region.pixel_format is PixelFormat.RGB565_BE
    assert region.frame_id == 9
    assert region.payload_length == 4
    assert len(region.payload) == 4
    assert region.payload[:2] == b"\xF8\x00"

    try:
        FrameRegion.from_image(frame, DirtyRegion(3, 1, 2, 1), frame_id=9)
    except ValueError as exc:
        assert "exceeds image bounds" in str(exc)
    else:
        raise AssertionError("out-of-bounds region was accepted")


class RegionTransport(FrameTransport):
    supports_regions = True

    def __init__(self):
        self.full_frames = []
        self.regions = []

    def send_frame(self, width, height, payload):
        self.full_frames.append((width, height, payload))

    def send_region(self, region):
        self.regions.append(region)


def test_oled_display_sends_initial_full_frame_then_only_dirty_regions():
    transport = RegionTransport()
    display = FutureOledDisplay(64, 64, transport, pixel_shift=False)
    first = image()
    display.present(first)
    assert len(transport.full_frames) == 1
    assert transport.regions == []

    changed = first.copy()
    changed.setPixelColor(20, 20, QColor("#FFFFFF"))
    display.present(changed)
    assert len(transport.full_frames) == 1
    assert len(transport.regions) == 1
    assert transport.regions[0].bounds == DirtyRegion(16, 16, 16, 16)
    assert transport.regions[0].frame_id == 1

    display.present(changed.copy())
    assert len(transport.regions) == 1

    display.present(image(64, 64, "#FFFFFF"))
    assert len(transport.full_frames) == 2
