"""scripts/semireal_compare.py (the «شبه حقيقي» v2/v3 grid): its plan, prices and cap, offline. It never calls
fal here: the dry run's client raises on any request."""

import importlib.util
import io
import sys
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image, ImageDraw

from qamra_ai.pipeline.character import character_request
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


def test_the_grid_is_nine_calls_for_one_dollar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    m = _script()
    monkeypatch.setattr(m, "OUT", tmp_path / "out")  # no cell exists: nothing is reused
    ref = m.reference(_sheet(tmp_path))
    with Image.open(io.BytesIO(ref)) as im:
        assert im.width == im.height  # a head-and-shoulders crop
    calls = m.plan(list(m.ROWS), ref)
    assert [c.id for c in calls] == [
        f"semireal-v3:{k}" for k in ("A:sheet", "A:page", "B:sheet", "B:page", "C:sheet", "C:page")
    ] + ["semireal-v3:D:sheet", "semireal-v3:D:page", "semireal-v3:E:page"]
    assert round(sum(c.usd for c in calls), 2) == 1.00
    by_id = {c.id: c for c in calls}
    assert (by_id["semireal-v3:C:sheet"].endpoint, by_id["semireal-v3:C:sheet"].resolution) == (
        "fal-ai/nano-banana-pro/edit",
        "2K",
    )
    assert by_id["semireal-v3:E:page"].endpoint == "fal-ai/nano-banana-2/edit"
    # v2 rows send exactly the v2 production prompt; v3 rows the new guide and its sheet line
    v2 = art_style(history_guide("semi-realistic", 2))
    assert by_id["semireal-v3:A:sheet"].prompt == character_request(m.TALA, [ref], v2).prompt
    assert "full-length character sheet" in by_id["semireal-v3:B:sheet"].prompt
    assert "Realistic painting in the manner" in by_id["semireal-v3:E:page"].prompt
    assert "picture-book illustration" in by_id["semireal-v3:A:page"].prompt
    assert all(len(c.refs) == 1 for c in calls)  # the reference crop, or the row's own sheet


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
