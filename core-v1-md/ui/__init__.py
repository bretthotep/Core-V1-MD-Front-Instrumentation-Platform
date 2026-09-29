"""UI composition layer: widget management, layout, compositing and the FrontPanel core."""

from ui.compositor import Compositor
from ui.debug_overlay import DebugInfo
from ui.layout import Layout, compute_layout
from ui.manager import ROTATION_SLOT, Slot, WidgetManager
from ui.panel import FrontPanel, load_layout

__all__ = [
    "ROTATION_SLOT",
    "Compositor",
    "DebugInfo",
    "FrontPanel",
    "Layout",
    "Slot",
    "WidgetManager",
    "compute_layout",
    "load_layout",
]
