import pytest

from simulator.pocs import SCENES, contact_sheet, main, render_scene, write_gallery_readme


def test_scene_slugs_unique_and_ordered():
    slugs = [s.slug for s in SCENES]
    assert len(set(slugs)) == len(slugs) and slugs == sorted(slugs)


def test_render_is_deterministic():
    scene = next(s for s in SCENES if s.slug.startswith("03"))
    a, b = render_scene(scene), render_scene(scene)
    assert (a.width(), a.height()) == (240, 1000)
    assert a == b


def test_contact_sheet_and_cli(tmp_path):
    images = [render_scene(s) for s in SCENES[:2]]
    sheet = contact_sheet(images, ["a", "b"], columns=2)
    assert sheet.width() > 2 * 240 and sheet.height() > 1000
    assert main(["--out", str(tmp_path), "--only", "01"]) == 0
    assert [p.name for p in tmp_path.iterdir()] == ["01-idle.png"]


CONCEPT_SCENES = [s for s in SCENES if s.concept]


@pytest.mark.parametrize("scene", CONCEPT_SCENES, ids=lambda scene: scene.slug)
def test_concepts_are_static_deterministic_and_not_runtime(scene, monkeypatch):
    from simulator.app import Simulator

    def forbidden(*args, **kwargs):
        pytest.fail("Concepts must not instantiate the simulator or send controls")

    monkeypatch.setattr(Simulator, "__init__", forbidden)
    a, b = render_scene(scene), render_scene(scene)
    assert a == b
    assert (a.width(), a.height()) == (240, 1000)
    assert scene.capture_s == 0 and not scene.actions and not scene.argv
    assert scene.image_label.startswith("DESIGN")


def test_concept_contracts_and_gallery_disclosures(tmp_path):
    assert len(CONCEPT_SCENES) == 11
    by_slug = {s.slug: s.concept for s in CONCEPT_SCENES}
    voltage = by_slug["23-designed-voltage-locked"]
    assert "LOCKED" in voltage.heading
    text = " ".join(row for _, rows in voltage.cards for row in rows)
    assert "TUNING WRITE SWITCH / OFF" in text
    assert not any(char.isdigit() for char in text)
    confirm = by_slug["20-designed-fan-confirm"]
    assert any("UNAVAILABLE" in title for title, _ in confirm.cards)
    edit = by_slug["19-designed-fan-edit"]
    edit_rows = [row for _, rows in edit.cards for row in rows]
    assert "DUTY / 50 % -> 55 % (MOCK)" in edit_rows
    assert "ILLUSTRATIVE / NOT APPLIED" in edit_rows
    assert "PRESS  /  confirm (gated)" in edit.gestures
    assert "BACKEND BOUNDS / TBD" in edit_rows
    assert "No safe limits claimed." in edit_rows
    assert any("UNAVAILABLE" in title for title, _ in edit.cards)
    settings = by_slug["21-designed-settings"]
    assert settings.cards[0][1] == settings.cards[1][1]
    assert settings.cards[0][0].startswith("COMPANION APP")
    assert settings.cards[1][0].startswith("DEVICE JOG")
    defaults = settings.cards[0][1]
    assert {"VIEW PAGING  /  ON", "ELEMENT JOG  /  ON", "FAN CONTROL  /  OFF",
            "MEDIA CONTROL  /  OFF", "ADV TUNING  /  OFF", "CAPABILITY / VALIDATION REQUIRED"} == set(defaults)
    music = by_slug["22-designed-music-jog"]
    music_rows = [row for _, rows in music.cards for row in rows]
    assert "DOUBLE PRESS / NO MEDIA ACTION" in music_rows
    assert "MUSIC / VOLUME SELECTED" in music_rows and "VOLUME / ONE DRAFT STEP" in music_rows
    assert "SECOND CLICK / CONFIRM GATED" in music_rows
    assert any("CONFIRM DISABLED" in title for title, _ in music.cards)
    cancel = by_slug["24-designed-fan-cancel"]
    assert any("LONG PRESS -> discard" in row for _, rows in cancel.cards for row in rows)
    assert any("No applied-value readback" in row for _, rows in cancel.cards for row in rows)
    selection = by_slug["18-designed-fan-select"]
    assert any("STALE" in row for _, rows in selection.cards for row in rows)
    assert any("UNSUPPORTED" in row for _, rows in selection.cards for row in rows)
    assert "PAGE 02 / 03" in by_slug["25-designed-view-paging"].subtitle
    navigation = by_slug["26-designed-media-navigation"]
    assert navigation.cards[0][1][:2] == ("> PREVIOUS TRACK", "NEXT TRACK")
    assert any("DISABLED" in title for title, _ in navigation.cards)
    assert "PREVIOUS TRACK / DRAFT ONLY" in navigation.cards[1][1]
    assert "SECOND CLICK / CONFIRM GATED" in navigation.cards[2][1]
    read_only = by_slug["27-designed-fan-read-only"]
    assert read_only.fan_names == ("REAR",)
    assert any("EDIT + CONFIRM / DISABLED" in title for title, _ in read_only.cards)
    for scene in CONCEPT_SCENES:
        # Static card regions must end before the proposed gesture footer.
        bottom = 184 + sum(48 + len(rows) * 29 + 18 for _, rows in scene.concept.cards) - 18
        assert bottom < 772
    write_gallery_readme(tmp_path, list(SCENES))
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "standalone static QImages" in readme and "bypass FrontPanel" in readme
    assert "no safe voltage numbers" in readme
    assert "first click SELECT → turn STAGE → second click" in readme
    assert "review then confirm" not in readme
    assert readme.count("| DESIGNED / MOCK |") == 11
