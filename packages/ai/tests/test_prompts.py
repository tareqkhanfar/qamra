import pytest
from jinja2 import UndefinedError

from qamra_ai import prompts
from qamra_ai.pipeline.style import SECTIONS, house_style, parse_style


def test_missing_variable_fails_loudly() -> None:
    with pytest.raises(UndefinedError):
        prompts.render("character_sheet", version=2, n_photos=1)


def test_no_glued_lines() -> None:
    text = prompts.render(
        "story_adapt_user",
        version=2,
        child={"name": "س", "gender": "f", "age": 5, "interests": []},
        lang="ar",
        companion={"name": "ب", "type_label": "x", "traits": None, "description_en": "d"},
        max_words=35,
        vowelize=True,
        theme_title="T",
        pages_json="[]",
        lesson="L",
        questions=["q1", "q2"],
        blurb="B",
    )
    assert "\nTitle template: T\n" in text
    assert "Word limit per page: 35" in text
    assert "- q1\n- q2" in text


def test_story_system_is_the_same_for_every_child() -> None:
    """The cacheable system prompt must not contain per-child data."""
    base = {"brand_name_en": "Qamra", "brand_name_ar": "قمرة", "theme_bible": "Beats: 1. x"}
    ar = prompts.render("story_adapt", version=2, lang="ar", **base)
    assert "تشكيل" in ar and "Beats: 1. x" in ar
    assert prompts.render("story_adapt", version=2, lang="ar", **base) == ar


def test_house_style_has_every_section() -> None:
    h = house_style()
    for s in SECTIONS:
        assert getattr(h, s).strip()
    assert "limestone" in h.setting and "cypress" in h.setting
    assert "No text of any kind" in h.negative
    assert h.prompt_id.startswith("qamra_style.v")


def test_house_style_missing_section_is_an_error() -> None:
    with pytest.raises(ValueError, match="missing"):
        parse_style("version: 1\n## Style\nsoft\n")


def test_a_redraw_carries_what_the_parent_said() -> None:
    from qamra_ai.pipeline.character import character_request
    from qamra_ai.pipeline.models import Child
    from qamra_ai.pipeline.theme import ArtStyle

    child = Child(name="ليان", gender="f", age=5, hijab=True)
    style = ArtStyle(slug="watercolor", title_ar="مائي", title_en="Watercolor", guide="soft watercolor")
    first = character_request(child, [b"x"], style)
    assert "did not look like" not in first.prompt  # the first drawing is the v2 prompt, unchanged
    redraw = character_request(child, [b"x"], style, attempt=2, fixes=["age", "hair", "skin"])
    assert "Skin tone:" in redraw.prompt and "Hijab: keep" in redraw.prompt
    assert "older than 5" in redraw.prompt
    assert redraw.seed != first.seed


def test_every_style_guide_parses_and_names_known_lines() -> None:
    from qamra_ai.pipeline.style import style_guides

    lines = {"magic", "classic", "workbook", "journey", "family", "islamic", "coloring"}
    guides = {g.slug: g for g in style_guides()}
    assert {"3d", "watercolor", "cartoon", "semi-realistic", "coloring"} <= set(guides)
    for g in guides.values():
        assert g.name_ar and g.name_en and g.look and g.negative
        assert set(g.lines) <= lines, g.slug
        assert 0 < g.qa_threshold <= 1 and 0 <= g.likeness_min <= 10


def test_semi_realistic_is_a_likeness_first_painting_for_stories_and_activity_books() -> None:
    """«شبه حقيقي» (Tareq, 2026-10-09): Magic and the four activity lines, never Classic (no templates in
    it)."""
    from qamra_ai.pipeline.style import style_guides
    from qamra_ai.pipeline.theme import load_style

    guides = {g.slug: g for g in style_guides()}
    semi = guides["semi-realistic"]
    assert (semi.name_ar, semi.name_en, semi.version) == ("شبه حقيقي", "Semi-realistic", 2)
    assert semi.lines == ("magic", "workbook", "journey", "family", "islamic")
    assert "classic" not in semi.lines
    others = [g for slug, g in guides.items() if slug in ("3d", "watercolor", "cartoon")]
    assert all(semi.likeness_min > g.likeness_min for g in others)  # likeness first
    assert semi.qa_threshold >= max(g.qa_threshold for g in others)
    look = " ".join(semi.look.split())
    assert "never a photograph" in look and "cuts out cleanly" in look  # the activity books' sticker cut-out
    assert "No photograph" in semi.negative and "uncanny" in semi.negative and "fingers" in semi.negative
    assert "No photorealism" in house_style().negative  # shared by every style
    assert load_style("semi-realistic").guide == semi.look  # what the page and sheet prompts paint with
