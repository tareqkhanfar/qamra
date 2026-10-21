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
    assert "did not look like" not in first.prompt  # the first drawing has no "fix this" part
    redraw = character_request(child, [b"x"], style, attempt=2, fixes=["age", "hair", "skin"])
    assert "Skin tone:" in redraw.prompt and "Hijab: keep" in redraw.prompt
    assert "older than 5" in redraw.prompt
    assert redraw.seed != first.seed


def test_every_style_guide_parses_and_names_known_lines() -> None:
    from qamra_ai.pipeline.style import style_guides

    lines = {"magic", "classic", "workbook", "journey", "family", "islamic", "colorbook", "coloring"}
    guides = {g.slug: g for g in style_guides()}
    assert {"3d", "watercolor", "cartoon", "semi-realistic", "coloring"} <= set(guides)
    for g in guides.values():
        assert g.name_ar and g.name_en and g.look and g.negative
        assert set(g.lines) <= lines, g.slug
        assert 0 < g.qa_threshold <= 1 and 0 <= g.likeness_min <= 10


def test_semi_realistic_is_a_likeness_first_painting_for_stories_and_activity_books() -> None:
    """«شبه حقيقي» (Tareq, 2026-10-09): Magic and the four activity lines, never Classic (no templates in
    it). v3 (2026-10-10): a realistic painted portrait, still never a photograph."""
    from qamra_ai.pipeline.style import style_guides
    from qamra_ai.pipeline.theme import load_style

    guides = {g.slug: g for g in style_guides()}
    semi = guides["semi-realistic"]
    assert (semi.name_ar, semi.name_en, semi.version) == ("شبه حقيقي", "Semi-realistic", 3)
    assert semi.lines == ("magic", "workbook", "journey", "family", "islamic", "colorbook")
    assert "classic" not in semi.lines
    others = [g for slug, g in guides.items() if slug in ("3d", "watercolor", "cartoon")]
    assert all(semi.likeness_min > g.likeness_min for g in others)  # likeness first
    assert semi.qa_threshold >= max(g.qa_threshold for g in others)
    look = " ".join(semi.look.split())
    assert "never a photograph" in look and "natural-size eyes" in look and "fine strands" in look
    assert "cuts out cleanly" in " ".join(semi.sheet.split())  # the activity books' sticker cut-out
    assert "No photograph" in semi.negative and "uncanny" in semi.negative and "fingers" in semi.negative
    assert "No photorealism" in house_style().negative  # still shared by every other style
    style = load_style("semi-realistic")
    assert (style.guide, style.version, style.sheet) == (semi.look, 3, semi.sheet)


SEMI_CARTOON_CUES = (
    "picture-book illustration",  # the house Style's first line
    "slightly large heads",  # the house Style, even with its "unless" clause
    "friendly and rounded",  # the house Style's characters
    "No photorealism",  # the house Negative
    "Not photorealistic",
    "storybook",  # v2: "classic hand-painted storybook portrait"
    "clumps",  # v2: "hair painted in soft, glossy clumps"
    "larger than life",  # v2: "a head only slightly larger than life"
    "photographic detail",  # v2's negative forbade the very detail that reads as real
)
# words that made the image model refuse a child's sheet (2026-10-09), and life-drawing words
SEMI_REFUSAL_WORDS = ("skin texture", "pores", "glamor", "glamour", "figure study", "from life", "anatomy")


def test_semi_realistic_v3_drops_every_cartoon_cue_from_its_own_prompts() -> None:
    """v2 looked like a cartoon: the house style's picture-book words came first in every prompt, and v2's
    own words allowed a big head and clumped hair. v3 replaces the house Style and Negative for this style
    only and adds a sheet line; every prompt it sends is free of those cues and of refusal words."""
    from prompt_snapshot import assembled_prompts

    from qamra_ai.pipeline.style import house_for
    from qamra_ai.pipeline.theme import load_style

    style = load_style("semi-realistic")
    # «قمرة كلاسيك» is not sold in this style (no templates): its portrait prompt keeps its own wording
    texts = {n: t for n, t in assembled_prompts(style).items() if not n.startswith("classic-")}
    for name, text in texts.items():
        flat = " ".join(text.split())
        image_prompt = not name.startswith("qa:")  # the page QA goes to the text model, not the painter
        for cue in (*SEMI_CARTOON_CUES, *(SEMI_REFUSAL_WORDS if image_prompt else ())):
            assert cue.lower() not in flat.lower(), (name, cue)
        assert "never a photograph" in flat, name
        # the sheet line goes to the child's character sheet only
        assert ("three views of the child, fully clothed" in flat) == name.startswith("character:"), name
    h = house_for(style)
    assert h.version == f"{house_style().version}+semi-realistic.v3"
    assert h.prompt_id == f"qamra_style.v{h.version}"
    assert (h.setting, h.people, h.composition, h.safety) == (
        house_style().setting,
        house_style().people,
        house_style().composition,
        house_style().safety,
    )


def test_semi_realistic_keeps_every_other_house_negative_line() -> None:
    """Its house Negative is the house's own list without "No photorealism": a later edit of the house list
    must be copied into the guide too (this test fails until it is)."""
    from qamra_ai.pipeline.style import house_for
    from qamra_ai.pipeline.theme import load_style

    def bullets(text: str) -> list[str]:
        return [" ".join(b.split()) for b in ("\n" + text).split("\n- ") if b.strip()]

    house = bullets(house_style().negative)
    semi = bullets(house_for(load_style("semi-realistic")).negative)
    assert [b.replace("No photorealism, no", "No") for b in house] == semi


def test_other_styles_get_the_house_style_unchanged() -> None:
    from qamra_ai.pipeline.style import house_for
    from qamra_ai.pipeline.theme import load_style

    for slug in ("3d", "watercolor", "cartoon", "coloring", "crayon", "papercut"):
        style = load_style(slug)
        assert house_for(style) is house_style()
        assert not (style.house_style or style.house_negative or style.sheet)


def test_the_merged_house_style_never_shares_a_cached_companion_sheet_with_v2() -> None:
    from qamra_ai.pipeline.bible import companion_sheet_key
    from qamra_ai.pipeline.style import history_guide, house_for
    from qamra_ai.pipeline.theme import art_style, load_style

    v2, v3 = art_style(history_guide("semi-realistic", 2)), load_style("semi-realistic")
    assert house_for(v2) is house_style()  # v2 had no house sections of its own
    assert house_style().for_style(v3).for_style(v3) == house_for(v3)  # merging twice changes nothing

    def key(style_house_version: str) -> str:
        return companion_sheet_key(
            model="fal-ai/nano-banana-2",
            style="semi-realistic",
            house_version=style_house_version,
            description="a moon",
            prompt="companion_default_sheet.v1",
        )

    assert key(house_for(v2).version) != key(house_for(v3).version)


def test_a_history_guide_must_name_its_own_version() -> None:
    from qamra_ai.pipeline.style import history_guide

    assert history_guide("semi-realistic", 2).version == 2
    with pytest.raises(FileNotFoundError):
        history_guide("semi-realistic", 1)
