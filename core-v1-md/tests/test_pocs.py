from simulator.pocs import SCENES, contact_sheet, main, render_scene


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
