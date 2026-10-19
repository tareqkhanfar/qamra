"""Portrait first (owner's decision, 2026-10-10, after the likeness trial): the child's portrait in the style
(`character_portrait.v3`), then the sheet painted from the photo and the portrait (`character_sheet.v7`),
each step on its own model; the portrait goes with the sheet on every picture of the hero. Since 2026-10-19
both ask for even, neutral daylight and the child's true colors, and carry the likeness notes. The trial's v5
and v1, and v6 and v2, stay for the record (scripts/likeness_trial.py)."""

import pytest
from tests_helpers import png

from qamra_ai.config import Settings
from qamra_ai.image import make_character_image_providers
from qamra_ai.image.base import ImageRequest
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.book import default_companion
from qamra_ai.pipeline.character import (
    LIKENESS_SHEET_VERSION,
    PORTRAIT_PROMPT_VERSION,
    SHEET_PROMPT_VERSION,
    character_request,
    generate_character,
    portrait_request,
)
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.pages import BookContext, page_request
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import load_style, load_theme

BOY = Child(name="x", gender="m", age=5)
GIRL = Child(name="x", gender="f", age=6, glasses=True)
PHOTO, PORTRAIT = png("tan"), png("navy")


def _flat(req: ImageRequest) -> str:
    return " ".join(req.prompt.split())


def test_books_draw_portrait_first_with_v7() -> None:
    assert (SHEET_PROMPT_VERSION, PORTRAIT_PROMPT_VERSION) == (7, 3)
    with pytest.raises(ValueError, match="no portrait"):
        character_request(BOY, [PHOTO], load_style("3d"), version=4, portrait=PORTRAIT)
    old = character_request(BOY, [PHOTO], load_style("3d"), version=4)
    assert "must look 5, not older" in old.prompt  # v4 stays for the record


@pytest.mark.parametrize("slug", ["3d", "semi-realistic", "cartoon", "watercolor"])
def test_v7_keeps_the_childs_own_face_hair_and_exact_age(slug: str) -> None:
    style = load_style(slug)
    req = character_request(BOY, [PHOTO], style, resolution="2K", portrait=PORTRAIT)
    flat = _flat(req)
    assert "not older" not in flat.replace("not an older child", "")  # v4's "must look N, not older" is gone
    assert "It never changes this child's face, head shape, features, hair or age." in flat
    assert "not a generic cute face" in flat and "Paint exactly his age, neither younger nor older" in flat
    assert "the same shape at the front (fringe, quiff" in flat and "Never curlier" in flat
    assert "Skin tone: exactly the child's own, as it looks in daylight" in flat
    assert "with its lighter and darker parts" in flat
    assert "simple brown shoes" in flat and "never barefoot" in flat and "no bare feet" in flat
    assert style.guide.split()[0] in flat and req.resolution == "2K"
    assert [r.label for r in req.refs] == [
        "photo of the child (1)",
        "the child's portrait in this book's style",
    ]
    assert "Image 2 is this same child's portrait in this book's style" in flat
    assert ("three views of the child, fully clothed" in flat) == (slug == "semi-realistic")


def test_the_portrait_is_a_large_face_in_full_color_at_the_exact_age() -> None:
    req = portrait_request(
        GIRL, [PHOTO, PHOTO], load_style("watercolor"), fixes=["hair"], note="Shorter fringe."
    )
    flat = _flat(req)
    assert (req.aspect, req.resolution, req.step) == ("1:1", "1K", "portrait:1")
    assert "head-and-shoulders portrait" in flat and "about 60% of the picture's height" in flat
    assert "in full, clear, natural color: never a monochrome, sepia or ink sketch" in flat
    assert "warm cream background" not in flat and "very light cream background" in flat
    assert "Paint exactly her age, neither younger nor older" in flat and "she wears glasses" in flat
    assert "- Hair: match the photo's hair color" in flat and "- Shorter fringe." in flat  # a redraw's fixes
    assert (
        len(req.refs) == 2 and portrait_request(GIRL, [PHOTO], load_style("3d"), attempt=2).seed != req.seed
    )


def test_the_trials_v5_and_v1_stay_for_the_record() -> None:
    sheet = character_request(
        BOY, [PHOTO], load_style("3d"), version=LIKENESS_SHEET_VERSION, portrait=PORTRAIT
    )
    assert "a 5-year-old boy, never younger" in _flat(sheet)
    portrait = portrait_request(BOY, [PHOTO], load_style("3d"), version=1)
    assert "full warm color" not in _flat(portrait)
    assert "in its full warm color" in _flat(portrait_request(BOY, [PHOTO], load_style("3d"), version=2))
    six = character_request(BOY, [PHOTO], load_style("3d"), version=6, portrait=PORTRAIT)
    assert "Skin tone: exactly the photo's" in _flat(six) and "COLOR" not in six.prompt


class _Recorder(FakeImageProvider):
    """A fake provider with its own model name (the fake records its requests)."""

    def __init__(self, model: str) -> None:
        super().__init__()
        self.model = model


async def test_the_portrait_then_the_sheet_each_on_its_own_model_and_resolution() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    page, portrait_model, sheet_model = _Recorder("page"), _Recorder("portrait"), _Recorder("sheet")
    rt = Runtime(
        settings=settings,
        text=None,  # type: ignore[arg-type]
        image=page,
        portrait_image=portrait_model,
        sheet_image=sheet_model,
    )
    drawn = await generate_character(
        rt, BOY, [PHOTO], load_style("cartoon"), attempt=2, fixes=["age"], note="x"
    )
    assert not page.requests
    [p], [s] = portrait_model.requests, sheet_model.requests
    assert (p.step, p.resolution, p.aspect) == ("portrait:2", "1K", "1:1")
    assert (s.step, s.resolution, s.aspect) == ("character:2", "2K", "3:2")
    assert s.refs[-1].data == drawn.portrait.data  # the sheet is painted from the portrait just drawn
    assert (
        "Age: the child looked older than 5" in p.prompt and "Age: the child looked older than 5" in s.prompt
    )
    assert [e.step for e in rt.ledger.entries] == ["portrait:2", "character:2"]


def test_character_models_come_from_the_settings_on_fal_only() -> None:
    fal = Settings(_env_file=None, image_provider="fal", fal_key="k")  # type: ignore[call-arg]
    portrait, sheet = make_character_image_providers(fal)
    assert portrait is not None and sheet is not None
    assert (portrait.model, sheet.model) == ("fal-ai/nano-banana-pro/edit", "fal-ai/nano-banana-pro/edit")
    assert portrait.fallback is not None and portrait.fallback.model == fal.fal_image_model
    same = fal.model_copy(
        update={"character_sheet_model": "", "character_portrait_model": "fal-ai/nano-banana-2"}
    )
    assert make_character_image_providers(same) == (None, None)  # empty or the page model: the page provider
    gemini = fal.model_copy(update={"image_provider": "gemini"})
    assert make_character_image_providers(gemini) == (None, None)  # same prompts on the page provider


@pytest.mark.parametrize("beat", [0, 1])
def test_every_picture_of_the_hero_gets_the_portrait_next_to_the_sheet(beat: int) -> None:
    theme = load_theme("new-sibling")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    rt = Runtime(settings=settings, text=None, image=FakeImageProvider())  # type: ignore[arg-type]

    def ctx(portrait: bytes | None) -> BookContext:
        return BookContext(
            child=BOY,
            lang="ar",
            theme=theme,
            style=load_style("3d"),
            house=house_style(),
            plan=plan_book(theme, "ar", companion_page=False),
            character_sheet=PHOTO,
            outfits={},
            seed=3,
            companion=default_companion(theme, "ar"),
            portrait=portrait,
        )

    with_portrait, without = page_request(rt, ctx(PORTRAIT), beat, 1), page_request(rt, ctx(None), beat, 1)
    labels = [r.label for r in with_portrait.refs]
    assert labels[:2] == [
        "THE HERO: character reference sheet of the child (likeness)",
        "THE HERO's portrait in this book's style: the face",
    ]
    assert "Image 2 is the hero's portrait in this book's style" in _flat(with_portrait)
    assert (
        "portrait" not in " ".join(r.label for r in without.refs) and "hero's portrait" not in without.prompt
    )


NOTES = {
    "skin": "light olive",
    "hair": "medium brown with lighter golden-brown tips, swept up at the front into a small quiff",
    "eyes": "dark brown, narrowing into crescents when smiling",
    "unknown": "never shown",
}


@pytest.mark.parametrize("slug", ["3d", "semi-realistic", "cartoon", "watercolor"])
def test_both_steps_ask_for_daylight_colors_and_carry_the_likeness_notes(slug: str) -> None:
    style = load_style(slug)
    for req in (
        portrait_request(BOY, [PHOTO], style, notes=NOTES),
        character_request(BOY, [PHOTO], style, portrait=PORTRAIT, notes=NOTES),
    ):
        flat = _flat(req)
        assert "Ignore the photo's light, its color cast and its background" in flat
        assert "never tinted brown, amber, yellow, sepia or gray" in flat
        assert (
            "paint it in even, neutral daylight, whatever the palette says about the light of scenes" in flat
        )
        assert "color cast" in flat.split("NEGATIVE")[-1]
        notes = flat.split("WHAT THIS CHILD LOOKS LIKE")[1].split("COLOR")[0]
        # a fixed order (hair before eyes before skin), labelled, and unknown keys ignored
        assert (
            notes.index("- Hair: medium brown with lighter golden-brown tips")
            < notes.index("- Eyes: dark brown, narrowing")
            < notes.index("- Skin tone: light olive")
        )
        assert "never shown" not in flat
    without = _flat(portrait_request(BOY, [PHOTO], style))
    assert "WHAT THIS CHILD LOOKS LIKE" not in without and "COLOR" in without


def test_only_watercolor_has_its_own_character_line_in_both_steps() -> None:
    line = "clean, bright, transparent watercolor washes, in even, neutral daylight"
    for slug in ("3d", "semi-realistic", "cartoon", "watercolor"):
        style = load_style(slug)
        assert (style.character != "") == (slug == "watercolor")
        portrait = _flat(portrait_request(BOY, [PHOTO], style))
        sheet = _flat(character_request(BOY, [PHOTO], style, portrait=PORTRAIT))
        assert (line in portrait, line in sheet) == ((slug == "watercolor"),) * 2


def test_watercolor_v4_drops_the_amber_wording() -> None:
    look = " ".join(load_style("watercolor").guide.split())
    assert "white textured paper" in look and "clean, bright, transparent washes" in look
    for amber in ("warm textured paper", "honey-gold", "golden-hour"):
        assert amber not in look
    assert "No sepia, brown, amber or yellow cast over the whole picture" in load_style("watercolor").negative


def test_older_templates_refuse_likeness_notes() -> None:
    with pytest.raises(ValueError, match="no likeness notes"):
        portrait_request(BOY, [PHOTO], load_style("3d"), version=2, notes=NOTES)
    with pytest.raises(ValueError, match="no likeness notes"):
        character_request(BOY, [PHOTO], load_style("3d"), version=6, portrait=PORTRAIT, notes=NOTES)
    assert portrait_request(
        BOY, [PHOTO], load_style("3d"), version=2, notes={}
    ).prompt  # empty: nothing to add


async def test_the_notes_reach_both_steps() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    image = _Recorder("page")
    rt = Runtime(settings=settings, text=None, image=image)  # type: ignore[arg-type]
    await generate_character(rt, BOY, [PHOTO], load_style("cartoon"), notes={"face": "oval, a little long"})
    assert all("- Face shape: oval, a little long" in r.prompt for r in image.requests)
    assert len(image.requests) == 2


def test_under_a_hijab_the_likeness_block_asks_for_no_hair() -> None:
    girl = Child(name="x", gender="f", age=6, hijab=True)
    for req in (
        portrait_request(girl, [PHOTO], load_style("cartoon")),
        character_request(girl, [PHOTO], load_style("cartoon"), portrait=PORTRAIT),
    ):
        assert "- Hair: exactly as in the photo" not in req.prompt and "sage-green hijab" in req.prompt
    assert "- Hair: exactly as in the photo" in portrait_request(BOY, [PHOTO], load_style("cartoon")).prompt
