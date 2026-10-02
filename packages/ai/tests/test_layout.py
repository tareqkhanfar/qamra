import io
import itertools

import pytest
from PIL import Image
from tests_helpers import png

from qamra_ai.pipeline.layout import PrintSpec, plan_book, side_of
from qamra_ai.pipeline.models import Lang
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


# ---- Addendum 11: spine from the page count, the layout library and its rotation


def test_spine_from_the_page_count_with_admin_override() -> None:
    spec = PrintSpec()
    assert spec.spine_for(24) == pytest.approx(0.15 * 12 + 6.0)  # caliper × sheets + board allowance
    assert spec.spine_for(25) == spec.spine_for(26)  # a half sheet is still a sheet
    assert spec.spine_for(40) > spec.spine_for(24)
    thick = PrintSpec(paper_caliper_mm=0.2, board_allowance_mm=5.0)
    assert thick.spine_for(32) == pytest.approx(0.2 * 16 + 5.0)
    assert PrintSpec(spine_mm=9.5).spine_for(24) == 9.5  # the admin's fixed width wins
    plan = plan_book(load_theme("graduation"), "ar", companion_page=True)
    assert plan.spine_mm == spec.spine_for(plan.page_count)


@pytest.mark.parametrize("slug", ["first-day", "graduation", "new-sibling"])
@pytest.mark.parametrize("lang", ["ar", "en"])
def test_layouts_rotate_and_keep_the_text_area(slug: str, lang: Lang) -> None:
    from qamra_pdf.page_layouts import GEOMETRY, LAYOUTS, has_dialogue

    theme = load_theme(slug)
    plan = plan_book(theme, lang, companion_page=False)
    designs = [plan.beats[p.index].design for p in theme.pages]
    assert all(d in LAYOUTS for d in designs)
    assert all(a != b for a, b in itertools.pairwise(designs)), designs  # no repeats
    assert len(set(designs)) >= 5  # a designed book, not one template
    for page in theme.pages:
        beat = plan.beats[page.index]
        assert beat.design is not None and GEOMETRY[beat.design] == page.layout  # same image geometry
        # the calm area the prompt asks for does not depend on the rotation
        if page.layout == "full":
            expected = side_of(beat.pages[0], lang == "ar") if page.text_pos == "side" else page.text_pos
            assert beat.text_area == expected
        if beat.design == "dialogue":
            assert has_dialogue(page.text_ar if lang == "ar" else page.text_en)


def test_theme_layout_names_and_legacy_values() -> None:
    from qamra_ai.pipeline.theme import ThemePage

    base = {"index": 1, "scene": "s", "beat": "b", "text_ar": "نص", "text_en": "text"}
    fade = ThemePage.model_validate({**base, "layout": "full-bleed-fade", "text_pos": "bottom"})
    assert (fade.layout, fade.design) == ("full", "full-bleed-fade")
    pano = ThemePage.model_validate({**base, "layout": "spread-panorama"})
    assert (pano.layout, pano.design, pano.physical_pages) == ("spread", "spread-panorama", 2)
    legacy = ThemePage.model_validate({**base, "layout": "split"})
    assert (legacy.layout, legacy.design) == ("split", None)
    with pytest.raises(ValueError):
        ThemePage.model_validate({**base, "layout": "white-box"})


def test_theme_layout_choice_is_kept_unless_it_repeats() -> None:
    theme = load_theme("graduation")
    pages = [
        p.model_copy(update={"design": "ornament-text"}) if p.index in (1, 2) else p for p in theme.pages
    ]
    plan = plan_book(theme.model_copy(update={"pages": pages}), "ar", companion_page=False)
    assert plan.beats[1].design == "ornament-text"  # the theme's choice
    assert plan.beats[2].design != "ornament-text"  # the same layout twice in a row is rotated away
    assert plan.title_style == "gold-magic" and plan.memories == "school"


def test_dialogue_and_big_moment_rules() -> None:
    from qamra_pdf.page_layouts import PageLayout, choose, split_dialogue

    quote_end = "هَمَسَ قَمّور: «أَنْتِ جَاهِزَةٌ!»"
    quote_mid = "نَادَتِ الْمُعَلِّمَةُ: «سلمى!» فَمَشَتْ سلمى بِثِقَةٍ وَرَفَعَتِ الشَّهَادَةَ."
    assert split_dialogue(quote_end) == ("هَمَسَ قَمّور:", ["أَنْتِ جَاهِزَةٌ!"])
    assert split_dialogue(quote_mid) == (quote_mid, [])  # a bubble would be read out of order
    used: dict[PageLayout, int] = {"full-bleed-cloud": 1, "full-bleed-fade": 1}
    assert (
        choose("full", "top", quote_end, wanted=None, previous=["full-bleed-cloud"], used=used) == "dialogue"
    )
    long_text = " ".join(["كَلِمَةٌ"] * 20)
    for _ in range(3):
        got = choose("full", "top", long_text, wanted=None, previous=[], used={})
        assert got not in ("big-moment", "dialogue")
    # a side text area only takes layouts that can sit on a side
    assert (
        choose("full", "left", long_text, wanted=None, previous=["full-bleed-cloud"], used={})
        == "full-bleed-fade"
    )
