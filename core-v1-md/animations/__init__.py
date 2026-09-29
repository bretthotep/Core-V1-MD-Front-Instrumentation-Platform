"""Animation engine.

* :mod:`animations.easing` – easing curves (pure Python)
* :mod:`animations.types` – the reveal/transition primitives
* :mod:`animations.engine` – runs active animations and paints their overlays
* :mod:`animations.profiles` – data-driven mapping from events to animations
* :mod:`animations.director` – glues the event bus to the engine

No application-specific behaviour lives in code: "Cyberpunk gets a cinematic
reveal" is a rule in ``animations/profiles/default.json``.
"""

from animations.director import AnimationDirector
from animations.engine import SCREEN, AnimationEngine
from animations.profiles import AnimationProfile, AnimationSpec, ProfileLibrary, ProfileRule
from animations.types import (
    ANIMATION_TYPES,
    Animation,
    Fade,
    HorizontalWipe,
    ScanLine,
    SegmentReveal,
    SlidingBlocks,
    VerticalWipe,
    create_animation,
)

__all__ = [
    "ANIMATION_TYPES",
    "Animation",
    "AnimationDirector",
    "AnimationEngine",
    "AnimationProfile",
    "AnimationSpec",
    "Fade",
    "HorizontalWipe",
    "ProfileLibrary",
    "ProfileRule",
    "SCREEN",
    "ScanLine",
    "SegmentReveal",
    "SlidingBlocks",
    "VerticalWipe",
    "create_animation",
]
