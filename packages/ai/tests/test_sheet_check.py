"""The character sheet's automatic check (2026-10-21): a figure whose head faces the other way from its body
and feet, or a shoe cut off, gets one automatic redraw before the parent sees the sheet."""

from collections.abc import Callable

from pydantic import BaseModel
from tests_helpers import png

from qamra_ai.config import Settings
from qamra_ai.image.base import GeneratedImage, ImageRequest
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.character import generate_character
from qamra_ai.pipeline.fakes import fake_sheet_check
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.sheet_check import FigureCheck, SheetCheck, problems
from qamra_ai.pipeline.theme import load_style
from qamra_ai.text.fake import FakeTextProvider

BOY = Child(name="x", gender="m", age=5)
PHOTO = png("tan")
GOOD = FigureCheck(head="left", body="left", feet="left", shoes_whole=True)
FRONT = FigureCheck(head="viewer", body="viewer", feet="viewer", shoes_whole=True)
TWISTED = FigureCheck(head="right", body="left", feet="left", shoes_whole=True)  # the owner's sheets


def _sheet(*figures: FigureCheck) -> SheetCheck:
    return SheetCheck(figures=list(figures))


def test_a_sheet_drawn_as_asked_has_no_problems() -> None:
    assert problems(_sheet(FRONT, GOOD, GOOD)) == []
    # a three-quarter head turned toward the viewer on a body turned left is one way, not two
    assert (
        problems(_sheet(FRONT, FigureCheck(head="viewer", body="left", feet="left", shoes_whole=True), GOOD))
        == []
    )
    assert problems(fake_sheet_check("", "", [])) == []  # type: ignore[arg-type]


def test_a_head_turned_the_other_way_a_cut_shoe_and_a_missing_figure_are_problems() -> None:
    [twisted] = problems(_sheet(FRONT, GOOD, TWISTED))
    assert twisted.startswith(
        "Figure 3 (side view) faced two ways (the head right, the body left, the feet left)"
    )
    [mixed] = problems(
        _sheet(FRONT, FigureCheck(head="left", body="left", feet="mixed", shoes_whole=True), GOOD)
    )
    assert mixed.startswith("Figure 2 (three-quarter view) faced two ways")
    [cut] = problems(
        _sheet(FigureCheck(head="viewer", body="viewer", feet="viewer", shoes_whole=False), GOOD, GOOD)
    )
    assert cut.startswith("Figure 1 (front view) had a bare foot or a shoe cut off")
    assert problems(_sheet(FRONT, GOOD)) == ["The sheet showed 2 figures: draw exactly three, side by side."]


class _Keeper(FakeImageProvider):
    """The fake, keeping what it drew."""

    def __init__(self) -> None:
        super().__init__()
        self.drawn: list[GeneratedImage] = []

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        image = await super().generate(req)
        self.drawn.append(image)
        return image


def _rt(answers: list[SheetCheck] | None, **settings: object) -> tuple[Runtime, _Keeper, FakeTextProvider]:
    queue = list(answers or [])

    def answer(step: str, system: str, user: list[object]) -> BaseModel:
        return queue.pop(0)

    responders: dict[str, Callable[..., BaseModel]] = {"SheetCheck": answer} if answers is not None else {}
    text = FakeTextProvider(responders)
    image = _Keeper()
    rt = Runtime(settings=Settings(_env_file=None, **settings), text=text, image=image)  # type: ignore[call-arg]
    return rt, image, text


async def test_a_good_sheet_is_checked_once_and_kept() -> None:
    rt, image, text = _rt([_sheet(FRONT, GOOD, GOOD)])
    drawn = await generate_character(rt, BOY, [PHOTO], load_style("cartoon"))
    assert drawn.check.outcome == "ok" and drawn.check.to_params() == {"outcome": "ok"}
    assert [r.step for r in image.requests] == ["portrait:1", "character:1"]
    assert [c["step"] for c in text.calls] == ["character:sheet-check"]


async def test_a_twisted_sheet_is_redrawn_once_with_what_was_wrong() -> None:
    rt, image, text = _rt([_sheet(FRONT, GOOD, TWISTED), _sheet(FRONT, GOOD, GOOD)])
    drawn = await generate_character(rt, BOY, [PHOTO], load_style("3d"), attempt=2)
    _, first, second = image.requests
    assert (first.step, second.step) == ("character:2", "character:2:redraw") and first.seed != second.seed
    assert (
        "A first try of this sheet was drawn wrong" in second.prompt
        and "Figure 3 (side view)" in second.prompt
    )
    assert second.refs[-1].data == drawn.portrait.data  # painted from the same portrait
    assert drawn.check.outcome == "redrawn" and drawn.check.found and not drawn.check.left
    assert [e.step for e in rt.ledger.entries if not e.step.startswith("character:sheet")] == [
        "portrait:2",
        "character:2",
        "character:2:redraw",  # the redraw is its own cost row
    ]
    assert len(text.calls) == 2  # the redraw is checked too, and never redrawn again


async def test_a_redraw_that_is_worse_keeps_the_first_sheet() -> None:
    rt, image, _ = _rt([_sheet(FRONT, GOOD, TWISTED), _sheet(FRONT, TWISTED, TWISTED)])
    drawn = await generate_character(rt, BOY, [PHOTO], load_style("cartoon"))
    assert len(image.requests) == 3 and drawn.check.outcome == "kept_flawed"
    assert drawn.sheet.data == image.drawn[1].data != image.drawn[2].data  # the first sheet, not the redraw


async def test_a_failed_check_or_the_setting_off_never_blocks_the_drawing() -> None:
    rt, image, _ = _rt(None)  # no responder: the check raises
    drawn = await generate_character(rt, BOY, [PHOTO], load_style("cartoon"))
    assert drawn.check.outcome == "failed" and drawn.check.error == "KeyError" and len(image.requests) == 2
    rt, image, text = _rt([], character_sheet_check=False)
    drawn = await generate_character(rt, BOY, [PHOTO], load_style("cartoon"))
    assert drawn.check.outcome == "off" and not text.calls and len(image.requests) == 2
