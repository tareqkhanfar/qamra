"""Portrait first (owner's decision, 2026-10-10, after the likeness trial): the child's portrait in the style
(`character_portrait.v2`), then the sheet painted from the photo and the portrait (`character_sheet.v6`), each
step on its own model; the portrait goes with the sheet on every picture of the hero. The trial's v5 and v1
stay for the record (scripts/likeness_trial.py)."""

import pytest
from tests_helpers import png

from qamra_ai.config import Settings
from qamra_ai.image import make_character_image_providers
from qamra_ai.image.base import ImageRequest
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.book import default_companion
from qamra_ai.pipeline.character import (
    LIKENESS_SHEET_VERSION,
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


def test_books_draw_portrait_first_with_v6() -> None:
    assert SHEET_PROMPT_VERSION == 6
    with pytest.raises(ValueError, match="no portrait"):
        character_request(BOY, [PHOTO], load_style("3d"), version=4, portrait=PORTRAIT)
    old = character_request(BOY, [PHOTO], load_style("3d"), version=4)
    assert "must look 5, not older" in old.prompt  # v4 stays for the record


@pytest.mark.parametrize("slug", ["3d", "semi-realistic", "cartoon", "watercolor"])
def test_v6_keeps_the_childs_own_face_hair_and_exact_age(slug: str) -> None:
    style = load_style(slug)
    req = character_request(BOY, [PHOTO], style, resolution="2K", portrait=PORTRAIT)
    flat = _flat(req)
    assert "not older" not in flat.replace("not an older child", "")  # v4's "must look N, not older" is gone
    assert "It never changes this child's face, head shape, features, hair or age." in flat
    assert "not a generic cute face" in flat and "Paint exactly his age, neither younger nor older" in flat
    assert "the same shape at the front (fringe, quiff" in flat and "Never curlier" in flat
    assert "Skin tone: exactly the photo's" in flat
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
    assert "in its full warm color: never a monochrome, sepia or ink sketch" in flat
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
