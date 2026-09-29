"""Data-driven animation profiles.

A *profile* is an ordered list of :class:`AnimationSpec` steps. A *rule*
maps an application event (optionally filtered by payload glob patterns) to a
profile. Rules are evaluated in file order; the first match wins.

Example rule – no game logic in code, only data::

    {"event": "APP_LAUNCHED", "match": {"app": "cyberpunk*"}, "profile": "cinematic_reveal"}
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from animations.engine import SCREEN
from animations.types import ANIMATION_TYPES, Animation, create_animation
from core.events import Event, EventType
from themes.theme import Theme

PROFILE_DIR = Path(__file__).resolve().parent / "profiles"


@dataclass(frozen=True, slots=True)
class AnimationSpec:
    type: str
    target: str = SCREEN
    duration_ms: float | None = None  # None → theme default
    easing: str | None = None  # None → theme default
    delay_ms: float = 0
    colour: str | None = None  # None → theme animation accent
    reverse: bool = False
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in ANIMATION_TYPES:
            raise ValueError(f"Unknown animation type {self.type!r}")

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AnimationSpec":
        known = {"type", "target", "duration_ms", "easing", "delay_ms", "colour", "reverse"}
        params = dict(data.get("params", {}))
        params.update({k: v for k, v in data.items() if k not in known and k != "params"})
        return AnimationSpec(
            type=data["type"],
            target=data.get("target", SCREEN),
            duration_ms=data.get("duration_ms"),
            easing=data.get("easing"),
            delay_ms=data.get("delay_ms", 0),
            colour=data.get("colour"),
            reverse=bool(data.get("reverse", False)),
            params=params,
        )

    def build(self, theme: Theme) -> Animation:
        """Instantiate the animation, filling unspecified values from the theme."""
        return create_animation(
            self.type,
            duration_ms=self.duration_ms if self.duration_ms is not None else theme.default_animation_ms,
            easing=self.easing or theme.default_easing,
            delay_ms=self.delay_ms,
            colour=self.colour or str(theme.animation.get("accent", "primary")),
            reverse=self.reverse,
            **self.params,
        )


@dataclass(frozen=True, slots=True)
class AnimationProfile:
    name: str
    steps: tuple[AnimationSpec, ...]


@dataclass(frozen=True, slots=True)
class ProfileRule:
    event: EventType
    profile: str
    match: dict[str, str] = field(default_factory=dict)

    def matches(self, event: Event) -> bool:
        if event.type is not self.event:
            return False
        for key, pattern in self.match.items():
            value = event.payload.get(key)
            if value is None or not fnmatchcase(str(value).lower(), pattern.lower()):
                return False
        return True


class ProfileLibrary:
    def __init__(self, profiles: Iterable[AnimationProfile] = (), rules: Iterable[ProfileRule] = ()) -> None:
        self.profiles: dict[str, AnimationProfile] = {p.name: p for p in profiles}
        self.rules: list[ProfileRule] = list(rules)
        self._validate()

    def _validate(self) -> None:
        for rule in self.rules:
            if rule.profile not in self.profiles:
                raise ValueError(f"Rule for {rule.event.name} references unknown profile {rule.profile!r}")

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ProfileLibrary":
        profiles = [
            AnimationProfile(name, tuple(AnimationSpec.from_dict(step) for step in steps))
            for name, steps in data.get("profiles", {}).items()
        ]
        rules = [
            ProfileRule(event=EventType[r["event"]], profile=r["profile"], match=dict(r.get("match", {})))
            for r in data.get("rules", [])
        ]
        return ProfileLibrary(profiles, rules)

    @staticmethod
    def load(path: Path | str = PROFILE_DIR / "default.json") -> "ProfileLibrary":
        with open(path, encoding="utf-8") as fh:
            return ProfileLibrary.from_dict(json.load(fh))

    def resolve(self, event: Event) -> AnimationProfile | None:
        for rule in self.rules:
            if rule.matches(event):
                return self.profiles[rule.profile]
        return None
