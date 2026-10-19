"""Likeness notes (2026-10-19): the text model describes how the child looks, from the framed photo, before
the character is drawn; appearance only, the family's choices first, nothing kept on a failure."""

from tests_helpers import png

from qamra_ai.config import Settings
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.likeness_notes import (
    FIELD_MAX,
    STEP,
    LikenessNotes,
    clean_notes,
    likeness_notes,
    note_lines,
)
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.text.base import ImagePart, system_text
from qamra_ai.text.fake import FakeTextProvider

BOY = Child(name="x", gender="m", age=5)
HIJAB = Child(name="x", gender="f", age=6, hijab=True, glasses=True)
PHOTO = png("tan")


def _rt(text: FakeTextProvider) -> Runtime:
    return Runtime(settings=Settings(_env_file=None), text=text, image=FakeImageProvider())  # type: ignore[call-arg]


def _notes(**kw: object) -> LikenessNotes:
    base: dict[str, object] = {
        "clear": True,
        "hair": "dark brown, short, swept up at the front",
        "face": "oval",
        "skin": "light olive",
        "glasses": "round frames",
    }
    return LikenessNotes.model_validate({**base, **kw})


async def test_the_photo_goes_to_the_main_model_with_the_familys_choices_and_the_cost_is_logged() -> None:
    text = default_fake_text_provider()
    rt = _rt(text)
    result = await likeness_notes(rt, BOY, [PHOTO])
    assert result.outcome == "used" and result.notes is not None
    assert result.notes["hair"].startswith("dark brown") and "glasses" not in result.notes
    [call] = text.calls
    assert (
        call["step"] == STEP and call["model"] == rt.settings.text_model and call["schema"] == "LikenessNotes"
    )
    images = [p for p in call["user"] if isinstance(p, ImagePart)]
    assert len(images) == 1 and images[0].data == PHOTO
    prompt = "\n".join(p for p in call["user"] if isinstance(p, str))
    assert "5 years old, a boy" in prompt and "Hijab (the family's choice): no" in prompt
    system = system_text(call["system"])
    for rule in ("ethnicity, race, nationality", "an age guess", "a name", "neutral daylight"):
        assert rule in system
    assert [e.step for e in rt.ledger.entries] == [STEP]


def test_the_familys_choices_win_over_the_notes() -> None:
    kept = clean_notes(_notes(), HIJAB)
    assert "hair" not in kept and kept["glasses"] == "round frames"  # hijab: no hair; glasses chosen
    assert "glasses" not in clean_notes(_notes(), BOY)  # no glasses chosen: none described


def test_notes_are_squashed_cut_and_ordered() -> None:
    kept = clean_notes(_notes(face="  oval \n with   full cheeks " + "x" * 400, marks="   "), BOY)
    assert kept["face"].startswith("oval with full cheeks") and len(kept["face"]) == FIELD_MAX
    assert "marks" not in kept
    assert note_lines(kept)[0].startswith("Hair: ") and note_lines(kept)[-1].startswith("Skin tone: ")
    assert note_lines(None) == [] and note_lines({"other": "x"}) == []


async def test_an_unclear_photo_gives_no_notes() -> None:
    text = FakeTextProvider({"LikenessNotes": lambda *_: LikenessNotes(clear=False)})
    result = await likeness_notes(_rt(text), BOY, [PHOTO])
    assert (result.notes, result.outcome) == (None, "unclear")


async def test_a_failure_draws_without_notes() -> None:
    def boom(*_: object) -> LikenessNotes:
        raise RuntimeError("provider down")

    result = await likeness_notes(_rt(FakeTextProvider({"LikenessNotes": boom})), BOY, [PHOTO])
    assert (result.notes, result.outcome, result.reasons) == (None, "failed", ["RuntimeError"])


async def test_notes_with_a_link_or_a_phone_number_are_dropped() -> None:
    text = FakeTextProvider({"LikenessNotes": lambda *_: _notes(marks="see www.example.com 0599123456")})
    result = await likeness_notes(_rt(text), BOY, [PHOTO])
    assert result.notes is None and result.outcome == "screened" and "link" in result.reasons


async def test_no_photo_no_call() -> None:
    text = default_fake_text_provider()
    assert (await likeness_notes(_rt(text), BOY, [])).outcome == "unclear" and not text.calls
