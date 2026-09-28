import re

import pytest

from qamra_ai.pipeline.theme import (
    MAX_WORDS_YOUNG,
    Theme,
    load_style,
    load_theme,
    render_template,
    theme_problems,
    word_count,
)

MVP = ["first-day", "graduation", "new-sibling"]


def test_gender_variants() -> None:
    t = "{اسْتَيْقَظَ/اسْتَيْقَظَتْ} {name} و{companion} {معكَ/معكِ}"
    assert render_template(t, "m", "سليم", "بوبو") == "اسْتَيْقَظَ سليم وبوبو معكَ"
    assert render_template(t, "f", "سلمى", "بوبو") == "اسْتَيْقَظَتْ سلمى وبوبو معكِ"


@pytest.mark.parametrize("slug", MVP)
@pytest.mark.parametrize("lang", ["ar", "en"])
@pytest.mark.parametrize("gender", ["m", "f"])
def test_mvp_themes_render_cleanly(slug: str, lang: str, gender: str) -> None:
    theme = load_theme(slug)
    for page in theme.pages:
        text = theme.base_text(page, lang, gender, "X", "C")  # type: ignore[arg-type]
        assert not re.search(r"[{}]", text), f"{slug} page {page.index}: leftover template syntax: {text}"
    fp = theme.for_parents
    assert fp is not None
    for t in [
        fp.lesson_ar,
        fp.lesson_en,
        *fp.questions_ar,
        *fp.questions_en,
        theme.blurb_ar or "",
        theme.blurb_en or "",
    ]:
        assert not re.search(r"[{}]", render_template(t, gender, "X", "C"))  # type: ignore[arg-type]


@pytest.mark.parametrize("slug", MVP)
def test_mvp_themes_meet_addendum_3(slug: str) -> None:
    theme = load_theme(slug)
    assert theme_problems(theme) == []
    assert 16 <= theme.story_page_count <= 20
    assert 2 <= sum(p.layout == "spread" for p in theme.pages) <= 3
    assert any(p.no_child for p in theme.pages), "at least one cacheable plate"
    assert {p.layout for p in theme.pages} >= {"full", "split", "spread"}
    for p in theme.pages:
        for g in ("m", "f"):
            assert word_count(render_template(p.text_ar, g, "س", "ص")) <= MAX_WORDS_YOUNG  # type: ignore[arg-type]
        assert p.outfit in theme.outfits and (p.location is None or p.location in theme.locations)
        assert p.no_child or p.companion_action, "the companion has a role on every page with the hero"


def _theme_dict(**changes: object) -> dict[str, object]:
    base = load_theme("first-day").model_dump()
    base.update(changes)
    return base


def test_spread_on_odd_page_is_rejected() -> None:
    data = _theme_dict()
    pages = data["pages"]
    assert isinstance(pages, list)
    pages[1]["layout"] = "spread"  # beat 2 sits on page 3: a spread there would start on an odd page
    with pytest.raises(ValueError, match="even page"):
        Theme.model_validate(data)


def test_word_limit_and_references_are_checked() -> None:
    data = _theme_dict()
    pages = data["pages"]
    assert isinstance(pages, list)
    pages[0]["text_ar"] = " ".join(["كلمة"] * 40)
    pages[1]["outfit"] = "tuxedo"
    pages[4]["companion_action"] = "waves"  # page 5 is a plate
    with pytest.raises(ValueError) as e:
        Theme.model_validate(data)
    msg = str(e.value)
    assert "40 words" in msg and "unknown outfit 'tuxedo'" in msg and "plate cannot show the companion" in msg


def test_coming_soon_theme_needs_no_pages() -> None:
    assert load_theme("moon-trip").pages == []


def test_unknown_style() -> None:
    with pytest.raises(KeyError):
        load_style("superhero-comic")
