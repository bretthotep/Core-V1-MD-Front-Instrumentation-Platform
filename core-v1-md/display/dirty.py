"""Tile-based dirty-region detection for successive rendered images."""

from __future__ import annotations

from PySide6.QtGui import QImage

from display.frame import DirtyRegion


class DirtyRegionDetector:
    """Find changed tiles and coalesce horizontal spans across adjacent rows."""

    def __init__(self, tile_width: int = 16, tile_height: int = 16, full_frame_ratio: float = 0.5) -> None:
        if tile_width < 1 or tile_height < 1:
            raise ValueError("tile dimensions must be positive")
        if not 0 < full_frame_ratio <= 1:
            raise ValueError("full_frame_ratio must be in (0, 1]")
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.full_frame_ratio = full_frame_ratio

    def detect(self, previous: QImage | None, current: QImage) -> tuple[DirtyRegion, ...]:
        if current.isNull():
            return ()
        width, height = current.width(), current.height()
        full = DirtyRegion(0, 0, width, height)
        if previous is None or previous.isNull() or previous.size() != current.size():
            return (full,)

        before = previous.convertToFormat(QImage.Format.Format_RGBA8888)
        after = current.convertToFormat(QImage.Format.Format_RGBA8888)
        before_rows = [bytes(before.constScanLine(y))[: width * 4] for y in range(height)]
        after_rows = [bytes(after.constScanLine(y))[: width * 4] for y in range(height)]
        tiles_x = (width + self.tile_width - 1) // self.tile_width
        tiles_y = (height + self.tile_height - 1) // self.tile_height

        regions: list[DirtyRegion] = []
        active: dict[tuple[int, int], int] = {}
        dirty_area = 0

        for tile_y in range(tiles_y):
            y0 = tile_y * self.tile_height
            y1 = min(height, y0 + self.tile_height)
            changed = []
            for tile_x in range(tiles_x):
                x0 = tile_x * self.tile_width * 4
                x1 = min(width, (tile_x + 1) * self.tile_width) * 4
                if any(before_rows[y][x0:x1] != after_rows[y][x0:x1] for y in range(y0, y1)):
                    changed.append(tile_x)

            spans: list[tuple[int, int]] = []
            for tile_x in changed:
                if not spans or tile_x > spans[-1][1] + 1:
                    spans.append((tile_x, tile_x))
                else:
                    spans[-1] = (spans[-1][0], tile_x)

            current_spans = set(spans)
            for span, start_y in tuple(active.items()):
                if span not in current_spans:
                    x, y, w, h = self._span_rect(span, start_y, tile_y, width, height)
                    regions.append(DirtyRegion(x, y, w, h))
                    dirty_area += w * h
                    del active[span]
            for span in spans:
                active.setdefault(span, tile_y)

        for span, start_y in active.items():
            x, y, w, h = self._span_rect(span, start_y, tiles_y, width, height)
            regions.append(DirtyRegion(x, y, w, h))
            dirty_area += w * h

        if not regions:
            return ()
        if dirty_area / (width * height) >= self.full_frame_ratio:
            return (full,)
        return tuple(regions)

    def _span_rect(
        self,
        span: tuple[int, int],
        start_tile_y: int,
        end_tile_y: int,
        width: int,
        height: int,
    ) -> tuple[int, int, int, int]:
        x = span[0] * self.tile_width
        y = start_tile_y * self.tile_height
        right = min(width, (span[1] + 1) * self.tile_width)
        bottom = min(height, end_tile_y * self.tile_height)
        return x, y, right - x, bottom - y
