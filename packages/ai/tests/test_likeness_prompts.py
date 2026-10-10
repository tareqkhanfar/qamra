"""The likeness trial's candidate prompts (2026-10-10): `character_sheet.v5` and `character_portrait.v1`.
Books still draw with v4: the trial (scripts/likeness_trial.py) uses these through the same request
builders."""

import pytest
from tests_helpers import png

from qamra_ai.pipeline.character import (
    LIKENESS_SHEET_VERSION,
    SHEET_PROMPT_VERSION,
    character_request,
    portrait_request,
)
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.theme import load_style

BOY = Child(name="x", gender="m", age=5)
GIRL = Child(name="x", gender="f", age=6, glasses=True)
PHOTO, PORTRAIT = png("tan"), png("navy")


def test_books_still_draw_with_v4() -> None:
    assert SHEET_PROMPT_VERSION == 4
    req = character_request(BOY, [PHOTO], load_style("3d"))
    assert "must look 5, not older" in req.prompt  # v3/v4 wording, unchanged
    with pytest.raises(ValueError, match="no portrait"):
        character_request(BOY, [PHOTO], load_style("3d"), portrait=PORTRAIT)


@pytest.mark.parametrize("slug", ["3d", "semi-realistic", "cartoon", "watercolor"])
def test_v5_keeps_the_childs_own_face_hair_and_age(slug: str) -> None:
    style = load_style(slug)
    req = character_request(BOY, [PHOTO], style, version=LIKENESS_SHEET_VERSION, resolution="2K")
    flat = " ".join(req.prompt.split())
    assert "not older" not in flat  # it pushed sheets toward a toddler
    assert "It never changes this child's face, head shape, features, hair or age." in flat
    assert "not a generic cute face" in flat and "a 5-year-old boy, never younger" in flat
    assert "the same shape at the front (fringe, quiff" in flat and "Never curlier" in flat
    assert "Skin tone: exactly the photo's" in flat
    assert style.guide.split()[0] in flat and req.resolution == "2K"
    assert [r.label for r in req.refs] == ["photo of the child (1)"]
    assert ("three views of the child, fully clothed" in flat) == (slug == "semi-realistic")


def test_portrait_first_sheet_takes_the_portrait_after_the_photos() -> None:
    req = character_request(
        GIRL, [PHOTO, PHOTO], load_style("watercolor"), version=LIKENESS_SHEET_VERSION, portrait=PORTRAIT
    )
    assert [r.label for r in req.refs][-1] == "the child's approved portrait in this book's style"
    assert len(req.refs) == 3
    flat = " ".join(req.prompt.split())
    assert (
        "Image 3 is the approved portrait of this same child" in flat and "her own face proportions" in flat
    )
    assert "she wears glasses" in flat


def test_the_portrait_is_a_large_face_in_the_style() -> None:
    req = portrait_request(BOY, [PHOTO], load_style("cartoon"))
    flat = " ".join(req.prompt.split())
    assert (req.aspect, req.resolution, req.step) == ("1:1", "1K", "portrait:1")
    assert "head-and-shoulders portrait" in flat and "about 60% of the picture's height" in flat
    assert "LIKENESS" in flat and "No hijab" in flat
    assert portrait_request(BOY, [PHOTO], load_style("cartoon"), attempt=2).seed != req.seed
