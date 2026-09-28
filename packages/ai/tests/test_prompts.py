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
