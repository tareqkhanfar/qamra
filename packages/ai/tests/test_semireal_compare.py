"""scripts/semireal_compare.py (the «شبه حقيقي» v2/v3 grid): its reference, plan, prices and cap, offline. It
never calls fal here: the dry run's client raises on any request."""

import importlib.util
import io
import sys
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image, ImageDraw

from qamra_ai.pipeline.character import character_request
from qamra_ai.pipeline.photo_check import check_photo
from qamra_ai.pipeline.style import history_guide
from qamra_ai.pipeline.theme import art_style

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "semireal_compare.py"


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("semireal_compare", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclasses look their module up while being defined
    spec.loader.exec_module(module)
    return module


def _sheet(tmp_path: Path) -> Path:
    """Three plain figures on cream paper, like a character sheet."""
    img = Image.new("RGB", (900, 600), (240, 232, 214))
    pen = ImageDraw.Draw(img)
    for x in (150, 450, 750):
        pen.ellipse((x - 45, 80, x + 45, 180), fill=(120, 80, 60))
        pen.rectangle((x - 60, 180, x + 60, 520), fill=(40, 60, 110))
    path = tmp_path / "sheet.png"
    img.save(path)
    return path


def test_the_reference_is_the_photo_as_an_order_stores_it() -> None:
    """The invented girl of the site's AI-made photo, cropped to her head and shoulders: re-encoded like an
    upload, and it passes the upload's photo check (one face, big enough, sharp, well lit)."""
    m = _script()
    ref, check = m.photo_reference(m.PHOTO, m.PHOTO_BOX)
    assert check.ok and check.metrics["faces"] == 1
    with Image.open(io.BytesIO(ref)) as im:
        assert (im.format, im.size) == ("JPEG", (512, 512)) and not im.info.get("exif")
    assert check_photo(ref).ok
    # a crop under the upload minimum (512 px) is refused, as the site would refuse it
    with pytest.raises(SystemExit, match="too_small"):
        m.photo_reference(m.PHOTO, (1175, 560, 1625, 1060))
    assert m.parse_args([]).ref == "photo"


def test_the_grid_is_nine_calls_for_one_dollar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    m = _script()
    monkeypatch.setattr(m, "BASE", tmp_path / "out")  # no cell exists: nothing is reused
    ref, _ = m.photo_reference(m.PHOTO, m.PHOTO_BOX)
    calls = m.plan(list(m.ROWS), ref, "photo")
    rows = ("A:sheet", "A:page", "B:sheet", "B:page", "C:sheet", "C:page", "D:sheet", "D:page", "E:page")
    assert [c.id for c in calls] == [f"semireal-v3:photo:{r}" for r in rows]
    assert round(sum(c.usd for c in calls), 2) == 1.00
    by_id = {c.id.removeprefix("semireal-v3:photo:"): c for c in calls}
    assert (by_id["C:sheet"].endpoint, by_id["C:sheet"].resolution) == ("fal-ai/nano-banana-pro/edit", "2K")
    assert by_id["E:page"].endpoint == "fal-ai/nano-banana-2/edit"
    # v2 rows send exactly the v2 production prompt; v3 rows the new guide and its sheet line
    v2 = art_style(history_guide("semi-realistic", 2))
    assert by_id["A:sheet"].prompt == character_request(m.GIRL, [ref], v2, version=4).prompt  # as drawn
    assert by_id["A:sheet"].refs == ["photo of the child (1)"]
    assert "full-length character sheet" in by_id["B:sheet"].prompt
    assert "Realistic painting in the manner" in by_id["E:page"].prompt
    assert "picture-book illustration" in by_id["A:page"].prompt
    assert all(len(c.refs) == 1 for c in calls)  # the photo, or the row's own sheet


def test_the_tala_reference_is_still_there(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    m = _script()
    monkeypatch.setattr(m, "BASE", tmp_path / "out")
    ref = m.tala_reference(_sheet(tmp_path))
    with Image.open(io.BytesIO(ref)) as im:
        assert im.width == im.height  # a head-and-shoulders crop
    calls = m.plan(list(m.ROWS), ref, "tala")
    assert len(calls) == 9 and calls[0].id == "semireal-v3:tala:A:sheet"
    assert round(sum(c.usd for c in calls), 2) == 1.00


def test_prices_are_fals_and_unknown_ones_stop_the_script() -> None:
    m = _script()
    assert m.price("fal-ai/nano-banana-2/edit", "1K") == 0.08
    assert m.price("fal-ai/nano-banana-pro/edit", "2K") == 0.15
    with pytest.raises(SystemExit):
        m.price("fal-ai/some-new-model/edit", "1K")


def test_drawing_needs_a_cap() -> None:
    m = _script()
    with pytest.raises(SystemExit):
        m.parse_args(["--run"])
    assert m.parse_args([]).run is False  # a dry run by default
