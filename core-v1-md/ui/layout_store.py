"""Persistence of the user's layout changes between sessions.

Pinning, hiding, expanding and collapsing with the jog wheel are stored in a
small JSON file in the per-user config directory, so the panel comes back the
way it was left. The layout definition (``default_layout.json``) is never
modified; HOME pressed twice restores it and the next save overwrites the
stored state with those defaults.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

APP_DIR_NAME = "CoreV1MD"
STATE_FILE_NAME = "layout_state.json"


def default_state_path() -> Path:
    """``%APPDATA%\\CoreV1MD`` on Windows, ``$XDG_CONFIG_HOME/core-v1-md`` elsewhere."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / APP_DIR_NAME / STATE_FILE_NAME
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "core-v1-md" / STATE_FILE_NAME


class LayoutStateStore:
    """Reads and atomically writes layout state JSON. Never raises on bad files."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any] | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            log.warning("Could not read layout state %s; using layout defaults", self.path, exc_info=True)
            return None
        if not isinstance(data, dict):
            log.warning("Layout state %s is not a JSON object; using layout defaults", self.path)
            return None
        return data

    def save(self, state: dict[str, Any]) -> bool:
        """Write via a temp file + rename so a crash never leaves a half-written file."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".layout_state.", suffix=".tmp", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(state, fh, indent=2)
                os.replace(tmp, self.path)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        except OSError:
            log.warning("Could not save layout state to %s", self.path, exc_info=True)
            return False
        return True
