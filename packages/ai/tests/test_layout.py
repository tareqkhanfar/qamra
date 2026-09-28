import io

import pytest
from PIL import Image
from tests_helpers import png

from qamra_ai.pipeline.layout import PrintSpec, plan_book, side_of
from qamra_ai.pipeline.printimg import fit_exact, split_spread
from qamra_ai.pipeline.theme import load_theme


def test_print_sizes() -> None:
    spec = PrintSpec()
    assert spec.page_px == (2551, 2551)  # 216 mm at 300 DPI = 2480 px trim + 3 mm bleed each side
    assert spec.spread_px == (5031, 2551)  # 426 mm × 216 mm
    assert spec.split_px == (2551, 1524)


def test_rtl_binding_sides() -> None:
    assert side_of(1, rtl=True) == "left" and side_of(2, rtl=True) == "right"
    assert side_of(1, rtl=False) == "right" and side_of(2, rtl=False) == "left"


@pytest.mark.parametrize("companion", [True, False])
def test_arabic_book_plan(companion: bool) -> None:
    plan = plan_book(load_theme("first-day"), "ar", companion_page=companion)
    assert plan.page_count == 24 and plan.page_count % 4 == 0
    assert [s.number for s in plan.slots] == list(range(1, 25))
    assert plan.slots[0].kind == "title" and plan.slots[0].side == "left"
    kinds = [s.kind for s in plan.slots[21:]]
    assert kinds == (
        ["companion", "parents", "activity"] if companion else ["parents", "activity", "memories"]
    )
    for beat in plan.beats.values():
        if beat.layout == "spread":
            first, second = beat.pages
            assert first % 2 == 0 and second == first + 1
            first_slot = plan.slots[first - 1]
            assert first_slot.side == "right" and first_slot.spread_half == "first"  # read first in RTL
            assert beat.text_area.endswith("-right") and beat.aspect == "16:9"


def test_side_text_goes_to_the_outer_edge() -> None:
    theme = load_theme("first-day")
    plan = plan_book(theme, "ar", companion_page=False)
    for page in theme.pages:
        beat = plan.beats[page.index]
        if page.layout == "full" and page.text_pos == "side":
            assert beat.text_area == plan.slots[beat.pages[0] - 1].side


def test_english_book_mirrors_the_binding() -> None:
    plan = plan_book(load_theme("first-day"), "en", companion_page=False)
    assert plan.slots[0].side == "right"
    spread = next(b for b in plan.beats.values() if b.layout == "spread")
    assert plan.slots[spread.pages[0] - 1].side == "left" and spread.text_area.endswith("-left")


def test_open_book_views() -> None:
    plan = plan_book(load_theme("first-day"), "ar", companion_page=False)
    views = plan.spreads()
    assert views[0][0] is None and views[0][1] is not None and views[0][1].number == 1
    right, left = views[1]
    assert right is not None and left is not None and (right.number, left.number) == (2, 3)
    assert views[-1][0] is not None and views[-1][0].number == 24 and views[-1][1] is None


def test_fit_exact_and_spread_halves() -> None:
    data = fit_exact(png("red", (1376, 768)), (5031, 2551))
    img = Image.open(io.BytesIO(data))
    assert img.size == (5031, 2551) and img.info.get("dpi", (0, 0))[0] == pytest.approx(300, abs=1)
    left, right = split_spread(data, 2551)
    assert Image.open(io.BytesIO(left)).size == (2551, 2551)
    assert Image.open(io.BytesIO(right)).size == (2551, 2551)
