"""Front-panel widgets.

Each widget is an independent instrument. Widgets receive telemetry through
:class:`~widgets.base.RenderContext` and draw with the EL primitives in
:mod:`widgets.primitives`. They never access sensors or hardware directly.
"""

from widgets.alert import AlertWidget
from widgets.application import ApplicationWidget
from widgets.audio_visualiser import VISUALISER_MODES, AudioVisualiserWidget, VisualiserMode
from widgets.base import RenderContext, Widget, WidgetSize, WidgetState
from widgets.clock import ClockWidget
from widgets.cpu import CpuWidget
from widgets.gpu import GpuWidget
from widgets.network import NetworkWidget
from widgets.ram import RamWidget
from widgets.registry import WIDGET_TYPES, create_widget, register_widget
from widgets.system import SystemWidget

__all__ = [
    "VISUALISER_MODES",
    "WIDGET_TYPES",
    "AlertWidget",
    "ApplicationWidget",
    "AudioVisualiserWidget",
    "ClockWidget",
    "CpuWidget",
    "GpuWidget",
    "NetworkWidget",
    "RamWidget",
    "RenderContext",
    "SystemWidget",
    "VisualiserMode",
    "Widget",
    "WidgetSize",
    "WidgetState",
    "create_widget",
    "register_widget",
]
