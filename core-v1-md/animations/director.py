"""Connects application events to animation profiles."""

from __future__ import annotations

from collections.abc import Callable

from animations.engine import AnimationEngine
from animations.profiles import AnimationProfile, ProfileLibrary
from core.events import Event, EventBus
from themes.theme import Theme


class AnimationDirector:
    """Listens to every event and plays the matching profile (if any)."""

    def __init__(
        self,
        bus: EventBus,
        engine: AnimationEngine,
        library: ProfileLibrary,
        theme: Callable[[], Theme],
    ) -> None:
        self.engine = engine
        self.library = library
        self._theme = theme
        self.last_profile: AnimationProfile | None = None
        self._unsubscribe = bus.subscribe(None, self.handle)

    def handle(self, event: Event) -> AnimationProfile | None:
        profile = self.library.resolve(event)
        if profile is None:
            return None
        theme = self._theme()
        for step in profile.steps:
            self.engine.play(step.build(theme), step.target)
        self.last_profile = profile
        return profile

    def detach(self) -> None:
        self._unsubscribe()
