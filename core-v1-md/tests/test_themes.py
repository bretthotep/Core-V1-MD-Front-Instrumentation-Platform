import pytest

from themes.theme import Theme, ThemeManager


def test_sony_minidisc_is_default_with_spec_colours():
    theme = ThemeManager().active
    assert theme.id == "sony_minidisc"
    assert theme.name == "Sony MiniDisc"
    assert theme.background == "#000000"
    assert theme.primary == "#00D8FF"
    assert theme.secondary == "#D8F8FF"
    assert theme.alert == "#FFD060"
    assert theme.critical == "#FF4040"


def test_switching_and_cycling_notifies_listeners():
    manager = ThemeManager()
    assert len(manager.ids) >= 2
    changes = []
    manager.on_change(lambda t: changes.append(t.id))
    manager.set_active("sony_es_mono")
    assert manager.active.id == "sony_es_mono"
    manager.cycle()
    assert changes == ["sony_es_mono", manager.active.id]
    with pytest.raises(KeyError):
        manager.set_active("does_not_exist")


def test_colour_fallback_and_validation():
    theme = Theme.from_dict(
        {"id": "t", "colours": {r: "#010203" for r in ("background", "primary", "secondary", "alert", "critical")}}
    )
    assert theme.colour("unknown_role") == theme.primary
    with pytest.raises(ValueError):
        Theme.from_dict({"id": "bad", "colours": {"background": "#000000"}})
    with pytest.raises(ValueError):
        Theme.from_dict({"id": "bad", "colours": {r: "cyan" for r in ("background", "primary", "secondary", "alert", "critical")}})
