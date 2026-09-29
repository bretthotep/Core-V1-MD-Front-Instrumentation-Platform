import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter

from animations.director import AnimationDirector
from animations.easing import EASINGS
from animations.engine import SCREEN, AnimationEngine
from animations.profiles import AnimationSpec, ProfileLibrary
from animations.types import ANIMATION_TYPES, Fade, HorizontalWipe, create_animation
from core.events import Event, EventBus, EventType
from themes.theme import ThemeManager

REQUIRED_TYPES = {"horizontal_wipe", "vertical_wipe", "sliding_blocks", "segment_reveal", "scan_line", "fade"}


def _white_frame(w=60, h=60):
    image = QImage(w, h, QImage.Format.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    return image


def _paint(anim, theme, image):
    painter = QPainter(image)
    anim.paint(painter, QRectF(0, 0, image.width(), image.height()), theme)
    painter.end()
    return image


def test_all_required_animation_types_registered():
    assert REQUIRED_TYPES <= set(ANIMATION_TYPES)


@pytest.mark.parametrize("name", sorted(EASINGS))
def test_easings_hit_endpoints(name):
    ease = EASINGS[name]
    assert ease(0.0) == pytest.approx(0.0, abs=1e-9)
    assert ease(1.0) == pytest.approx(1.0, abs=1e-9)


def test_timing_delay_reverse_and_finish():
    anim = HorizontalWipe(duration_ms=100, easing="linear", delay_ms=50)
    assert not anim.started and anim.progress == 0
    anim.advance(100)
    assert anim.started and anim.progress == pytest.approx(0.5)
    anim.advance(60)
    assert anim.finished
    rev = Fade(duration_ms=100, easing="linear", reverse=True)
    rev.advance(25)
    assert rev.progress == pytest.approx(0.75)


@pytest.mark.parametrize("kind", sorted(REQUIRED_TYPES))
def test_each_type_conceals_at_start_and_reveals_at_end(kind, theme):
    start = create_animation(kind, duration_ms=100, easing="linear")
    image = _paint(start, theme, _white_frame())
    assert QColor(image.pixel(30, 45)) == QColor(theme.background)
    end = create_animation(kind, duration_ms=100, easing="linear")
    end.advance(100)
    image = _paint(end, theme, _white_frame())
    assert QColor(image.pixel(30, 45)) == QColor("#FFFFFF")


def test_engine_ticks_and_removes_finished(theme):
    engine = AnimationEngine()
    engine.play(HorizontalWipe(duration_ms=100), "cpu")
    engine.play(Fade(duration_ms=300))
    engine.tick(150)
    assert [a.target for a in engine.active] == [SCREEN]
    image = _white_frame()
    painter = QPainter(image)
    engine.paint(painter, QRectF(0, 0, 60, 60), {"cpu": QRectF(0, 0, 10, 10)}, theme)
    painter.end()
    engine.tick(200)
    assert not engine.busy


def test_profiles_resolve_by_payload_without_hardcoded_logic():
    library = ProfileLibrary.load()
    def resolve(app):
        return library.resolve(Event(EventType.APP_LAUNCHED, {"app": app})).name
    assert resolve("Cyberpunk2077.exe") == "cinematic_reveal"
    assert resolve("CODE.EXE") == "code_editor"
    assert resolve("notepad.exe") == "app_default"
    assert library.resolve(Event(EventType.SYSTEM_START)).name == "boot"


def test_custom_profile_library_and_validation():
    data = {
        "profiles": {"p": [{"type": "fade", "duration_ms": 10}]},
        "rules": [{"event": "APP_LAUNCHED", "match": {"app": "doom*"}, "profile": "p"}],
    }
    library = ProfileLibrary.from_dict(data)
    assert library.resolve(Event(EventType.APP_LAUNCHED, {"app": "doom.exe"})).name == "p"
    assert library.resolve(Event(EventType.APP_LAUNCHED, {"app": "quake.exe"})) is None
    with pytest.raises(ValueError):
        ProfileLibrary.from_dict({"profiles": {}, "rules": [{"event": "HIGH_TEMP", "profile": "missing"}]})
    with pytest.raises(ValueError):
        AnimationSpec(type="spin")


def test_director_uses_theme_defaults():
    bus, engine, themes = EventBus(), AnimationEngine(), ThemeManager()
    library = ProfileLibrary.from_dict(
        {"profiles": {"p": [{"type": "fade", "target": "application"}]}, "rules": [{"event": "APP_CLOSED", "profile": "p"}]}
    )
    AnimationDirector(bus, engine, library, lambda: themes.active)
    themes.set_active("sony_es_mono")
    bus.emit(EventType.APP_CLOSED, app="x")
    (active,) = engine.active
    assert active.target == "application"
    assert active.animation.duration_ms == themes.active.default_animation_ms
    assert active.animation.colour_role == themes.active.animation["accent"]
