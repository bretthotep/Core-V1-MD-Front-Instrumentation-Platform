import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime as _dt  # noqa: E402

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from telemetry.mock_provider import MockTelemetryProvider  # noqa: E402
from themes.theme import ThemeManager  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def theme():
    return ThemeManager().active


@pytest.fixture
def snapshot():
    return MockTelemetryProvider(seed=1).poll(10.0)


@pytest.fixture
def wall_time():
    return _dt.datetime(2026, 9, 29, 13, 5, 42)
