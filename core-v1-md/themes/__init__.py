"""Theme engine.

Themes are plain JSON documents stored alongside this module (``*.json``).
They are loaded into immutable :class:`Theme` objects and managed by a
:class:`ThemeManager`, which supports switching the active theme at runtime and
notifies listeners (compositor, animation engine) when it changes.
"""

from themes.theme import Theme, ThemeManager, load_theme

__all__ = ["Theme", "ThemeManager", "load_theme"]
