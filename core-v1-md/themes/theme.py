"""Theme model and manager (Qt-free)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

THEME_DIR = Path(__file__).resolve().parent
DEFAULT_THEME_ID = "sony_minidisc"

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

REQUIRED_COLOURS = ("background", "primary", "secondary", "alert", "critical")


@dataclass(frozen=True, slots=True)
class Theme:
    """An immutable visual theme.

    ``colours`` always contains at least the roles in :data:`REQUIRED_COLOURS`.
    Additional roles (``dim``, ``grid``...) are optional; use :meth:`colour`
    which falls back gracefully.
    """

    id: str
    name: str
    colours: dict[str, str]
    fonts: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    animation: dict[str, Any] = field(default_factory=dict)

    # ---- colour roles ---------------------------------------------------
    @property
    def background(self) -> str:
        return self.colours["background"]

    @property
    def primary(self) -> str:
        return self.colours["primary"]

    @property
    def secondary(self) -> str:
        return self.colours["secondary"]

    @property
    def alert(self) -> str:
        return self.colours["alert"]

    @property
    def critical(self) -> str:
        return self.colours["critical"]

    def colour(self, role: str, fallback: str = "primary") -> str:
        return self.colours.get(role) or self.colours[fallback]

    # ---- other properties -----------------------------------------------
    def font(self, role: str = "display") -> str:
        return self.fonts.get(role) or self.fonts.get("display") or "Monospace"

    def metric(self, key: str, default: float) -> float:
        return float(self.metrics.get(key, default))

    @property
    def unlit_alpha(self) -> float:
        """Opacity used to draw 'unlit' EL segments (the ghosting of a real VFD/EL panel)."""
        return self.metric("unlit_alpha", 0.14)

    @property
    def default_animation_ms(self) -> int:
        return int(self.animation.get("default_duration_ms", 450))

    @property
    def default_easing(self) -> str:
        return str(self.animation.get("easing", "out_cubic"))

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Theme":
        colours = dict(data.get("colours", {}))
        missing = [role for role in REQUIRED_COLOURS if role not in colours]
        if missing:
            raise ValueError(f"Theme {data.get('id')!r} missing colour roles: {missing}")
        for role, value in colours.items():
            if not _HEX.match(value):
                raise ValueError(f"Theme colour {role}={value!r} must be #RRGGBB")
        return Theme(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            colours=colours,
            fonts=dict(data.get("fonts", {})),
            metrics=dict(data.get("metrics", {})),
            animation=dict(data.get("animation", {})),
        )


def load_theme(path: Path | str) -> Theme:
    with open(path, encoding="utf-8") as fh:
        return Theme.from_dict(json.load(fh))


ThemeListener = Callable[[Theme], None]


class ThemeManager:
    """Holds the available themes and the active one."""

    def __init__(self, themes: Iterable[Theme] | None = None, active: str | None = None) -> None:
        self._themes: dict[str, Theme] = {}
        self._listeners: list[ThemeListener] = []
        for theme in themes if themes is not None else self.discover():
            self.register(theme)
        if not self._themes:
            raise ValueError("ThemeManager requires at least one theme")
        default = active or (DEFAULT_THEME_ID if DEFAULT_THEME_ID in self._themes else next(iter(self._themes)))
        self._active = self._themes[default]

    @staticmethod
    def discover(directory: Path = THEME_DIR) -> list[Theme]:
        return [load_theme(p) for p in sorted(directory.glob("*.json"))]

    def register(self, theme: Theme) -> None:
        self._themes[theme.id] = theme

    @property
    def ids(self) -> list[str]:
        return list(self._themes)

    @property
    def active(self) -> Theme:
        return self._active

    def get(self, theme_id: str) -> Theme:
        return self._themes[theme_id]

    def on_change(self, listener: ThemeListener) -> None:
        self._listeners.append(listener)

    def set_active(self, theme_id: str) -> Theme:
        if theme_id not in self._themes:
            raise KeyError(f"Unknown theme {theme_id!r}; available: {self.ids}")
        self._active = self._themes[theme_id]
        for listener in self._listeners:
            listener(self._active)
        return self._active

    def cycle(self) -> Theme:
        ids = self.ids
        return self.set_active(ids[(ids.index(self._active.id) + 1) % len(ids)])
