"""«ماذا يلبس؟» (owner, 2026-10-20): the outfit catalogue (content/outfits.yaml), the chosen outfit in
the sheet (`character_sheet.v8`) and portrait (`character_portrait.v4`) prompts, and in the books' style
bible. The default outfit renders exactly the prompts of before (v7 / v3) and leaves the books' clothes
alone."""

import re

import pytest
from tests_helpers import png

from qamra_ai import prompts
from qamra_ai.pipeline.bible import build_bible
from qamra_ai.pipeline.character import character_request, outfit_words, portrait_request
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.outfits import DEFAULT_OUTFIT, load_outfits
from qamra_ai.pipeline.theme import load_style, load_theme

PHOTO, PORTRAIT = png("tan"), png("navy")
NOTES = {"hair": "short, dark brown"}


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_six_outfits_each_for_girls_and_boys_with_the_classic_default() -> None:
    catalog = load_outfits()
    assert catalog.default == DEFAULT_OUTFIT == "classic"
    girls, boys = catalog.for_child("f"), catalog.for_child("m")
    assert len(girls) == 6 and len(boys) == 6 and girls[0].id == boys[0].id == "classic"
    default = catalog.get("classic")
    assert default is not None and default.name_ar == "الأساسي"
    assert (
        default.looks["f"].prompt
        == "a soft cream long-sleeved top, night-blue trousers and simple brown shoes"
    )
    for gender, offered in (("f", girls), ("m", boys)):
        tops = [o.looks[gender].swatch.top.upper() for o in offered]  # type: ignore[index]
        assert len(set(tops)) == len(tops), f"two {gender} swatches share a colour"
        for o in offered:
            look = o.looks[gender]  # type: ignore[index]
            assert "shoe" in look.prompt or "sneaker" in look.prompt or "boot" in look.prompt
            assert "classic" not in o.lines and o.lines  # Classic's art is fixed
    for o in girls:
        assert o.hijab and o.hijab_color, f"{o.id}: a girl's outfit names the hijab that goes with it"


def test_the_everyday_groups_exist_in_their_themes() -> None:
    for slug, groups in load_outfits().themes.items():
        theme = load_theme(slug)
        assert groups and set(groups) <= set(theme.outfits), slug
    assert load_outfits().everyday_groups("graduation") == ["school"]  # the gown day keeps the gown


@pytest.mark.parametrize("slug", ["watercolor", "3d", "cartoon", "semi-realistic"])
@pytest.mark.parametrize(
    "child", [Child(name="x", gender="m", age=5), Child(name="x", gender="f", age=6, hijab=True)]
)
def test_the_default_outfit_renders_the_prompts_of_before(slug: str, child: Child) -> None:
    style = load_style(slug)
    for outfit in (None, "classic", "rose-dress" if child.gender == "m" else "green-hoodie", "unknown"):
        dressed = child.model_copy(update={"outfit": outfit})  # one not offered to this child: the default
        # the outfits' versions (sheet v8, portrait v4) against the ones before them (v7, v3)
        sheet = character_request(dressed, [PHOTO], style, version=8, portrait=PORTRAIT, notes=NOTES)
        before = character_request(child, [PHOTO], style, version=7, portrait=PORTRAIT, notes=NOTES)
        assert sheet.prompt == before.prompt
        assert portrait_request(dressed, [PHOTO], style, version=4, notes=NOTES).prompt == (
            portrait_request(child, [PHOTO], style, version=3, notes=NOTES).prompt
        )
        # and today's (v10, v5): the default outfit is the reference outfit, as with no outfit at all
        now = character_request(dressed, [PHOTO], style, portrait=PORTRAIT, notes=NOTES).prompt
        assert now == character_request(child, [PHOTO], style, portrait=PORTRAIT, notes=NOTES).prompt
        assert "night-blue trousers" in now


@pytest.mark.parametrize("outfit", ["red-jeans", "school", "yellow-cardigan", "rose-dress", "tatreez"])
def test_the_sheet_and_portrait_wear_the_chosen_outfit_and_its_hijab(outfit: str) -> None:
    girl = Child(name="x", gender="f", age=5, hijab=True, outfit=outfit)
    chosen = load_outfits().get(outfit)
    assert chosen is not None
    look = chosen.looks["f"]
    sheet = _flat(character_request(girl, [PHOTO], load_style("3d"), portrait=PORTRAIT).prompt)
    assert f"The parent chose this outfit, modest and simple: {look.prompt}." in sheet
    assert "Paint exactly these garments, colors and pattern, the same in all three views." in sheet
    assert (
        "night-blue trousers" not in sheet and "sage-green hijab" not in sheet and "never barefoot" in sheet
    )
    assert f"The parent chose a hijab: {chosen.hijab} neatly covering the hair" in sheet
    portrait = _flat(portrait_request(girl, [PHOTO], load_style("watercolor")).prompt)
    assert f"very light cream background and {look.top}." in portrait and "plain cream top" not in portrait
    assert f"The parent chose a hijab: {chosen.hijab} neatly covering the hair" in portrait


def test_a_boys_outfit_and_no_hijab() -> None:
    boy = Child(name="x", gender="m", age=5, outfit="tatreez")
    words = outfit_words(boy, sheet=True)
    assert words["outfit"] and "black vest" in words["outfit"]
    sheet = _flat(character_request(boy, [PHOTO], load_style("cartoon")).prompt)
    assert "black vest with deep-red cross-stitch tatreez" in sheet and "No hijab or head covering." in sheet


def test_older_templates_take_no_outfit() -> None:
    girl = Child(name="x", gender="f", age=5, outfit="rose-dress")
    with pytest.raises(ValueError, match="takes no outfit"):
        character_request(girl, [PHOTO], load_style("3d"), version=7)
    with pytest.raises(ValueError, match="takes no outfit"):
        portrait_request(girl, [PHOTO], load_style("3d"), version=3)
    assert prompts.prompt_id("character_sheet", 8) == "character_sheet.v8"


def test_books_wear_the_chosen_outfit_on_everyday_groups_and_keep_costumes() -> None:
    first_day, graduation = load_theme("first-day"), load_theme("graduation")
    girl = Child(name="x", gender="f", age=5, hijab=True)
    plain = build_bible(first_day, girl, 3, style="3d")
    assert build_bible(first_day, girl.model_copy(update={"outfit": "classic"}), 3, style="3d") == plain
    dressed = build_bible(first_day, girl.model_copy(update={"outfit": "red-jeans"}), 3, style="3d")
    red = load_outfits().get("red-jeans")
    assert red is not None
    assert dressed.outfits["day"] == red.looks["f"].prompt
    assert dressed.outfits["sleep"] == plain.outfits["sleep"]  # pyjamas stay pyjamas
    assert dressed.hijab == f"{red.hijab} neatly covering the hair"  # the cover's group wears it: one hijab
    grad_plain = build_bible(graduation, girl, 3, style="3d")
    grad = build_bible(graduation, girl.model_copy(update={"outfit": "red-jeans"}), 3, style="3d")
    assert grad.outfits["day"] == grad_plain.outfits["day"] and "graduation gown" in grad.outfits["day"]
    assert grad.outfits["school"] == red.looks["f"].prompt and grad.hijab == grad_plain.hijab
    star = load_theme("star-keeper")  # not listed: its own clothes on every page
    assert build_bible(star, girl.model_copy(update={"outfit": "tatreez"}), 3, style="3d") == build_bible(
        star, girl, 3, style="3d"
    )


def test_prompt_words_are_print_safe_colours() -> None:
    for o in load_outfits().outfits:
        for look in o.looks.values():
            assert not re.search(r"\bneon\b|fluorescent", look.prompt)
