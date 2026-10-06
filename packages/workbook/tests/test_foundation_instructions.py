"""«دوسية التأسيس»: the one-line instruction at the top of every exercise (the brief of 6 October 2026):
short, resolved for a boy and a girl, never opening like the page before it, and no wording over and over."""

from __future__ import annotations

import collections
import itertools
from pathlib import Path

import pytest
from qamra_workbook.curriculum import load
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render.foundation import from_curriculum, volume_of
from qamra_workbook.render.foundation_text import pick, stars
from qamra_workbook.render.spec import Child, PageSpec

CURRICULUM = Path(__file__).resolve().parents[3] / "content/workbook/curriculum"
BOY, GIRL = Child("سليم", "m"), Child("ليان", "f")
NOT_PRINTED = {"owner-page", "blank"}  # full-page layouts without the guide's bubble
VOLUMES = [(level, n) for level in ("kg1", "kg2") for n in (1, 2, 3)]
SUKUN = "ْ"


def volume_pages(level: str, number: int) -> list[PageSpec]:
    plan = load(CURRICULUM / f"{level}.yaml")
    volume = volume_of(plan, number)
    return [from_curriculum(p, plan, volume, "Layan") for p in volume.pages]


def opening(text: str) -> str:
    """The first word without its marks and a leading «وَ»: what a neighbour must not repeat."""
    word = strip_tashkeel(text.split()[0]).strip("،:!؟")
    return word[1:] if word.startswith("و") and len(word) > 2 else word


@pytest.mark.parametrize(("level", "number"), VOLUMES)
def test_every_instruction_is_short_and_resolved_for_both_genders(level: str, number: int) -> None:
    for page in volume_pages(level, number):
        said = [BOY.personalize(page.instruction), GIRL.personalize(page.instruction), page.instruction_en]
        for text in said:
            assert len(text.split()) <= 7, f"{page.id}: {text}"
            assert not set("{}/") & set(text), f"{page.id}: {text}"
        boy = said[0].split()
        for word, after in itertools.pairwise(boy):  # «لَوِّنِ الحَرْفَ», never «لَوِّنْ الحَرْفَ»
            assert not (word.endswith(SUKUN) and after.startswith("ال")), f"{page.id}: {said[0]}"


@pytest.mark.parametrize(("level", "number"), VOLUMES)
def test_neighbouring_exercises_open_differently_and_no_wording_runs_through_the_volume(
    level: str, number: int
) -> None:
    previous: PageSpec | None = None
    seen: collections.Counter[str] = collections.Counter()
    for page in volume_pages(level, number):
        if page.type in NOT_PRINTED:
            previous = None
            continue
        text = BOY.personalize(page.instruction)
        if previous is not None:
            assert opening(text) != opening(BOY.personalize(previous.instruction)), (previous.id, page.id)
        previous = page
        seen[page.instruction] += 1
    assert max(seen.values()) <= 3, seen.most_common(3)


def test_a_recurring_exercise_turns_through_its_wordings() -> None:
    pages = [p for p in volume_pages("kg2", 1) if p.type == "letter-trace"]
    assert len({p.instruction for p in pages}) >= 3
    assert all(a.instruction != b.instruction for a, b in itertools.pairwise(pages))
    assert pick(("a", "b", "c"), 4) == "b"
    assert stars(1) == "نَجْمَةً واحِدَةً" and stars(2) == "نَجْمَتَيْنِ" and stars(5) == "5 نُجومٍ"


def test_the_instruction_follows_the_page() -> None:
    kg1 = {p.number: p for p in volume_pages("kg1", 1)}
    assert "الصّورَةَ" in kg1[101].instruction and "الصّورَتَيْنِ" not in kg1[101].instruction  # ذ: one picture
    assert (
        "Write" not in kg1[40].instruction_en and "Trace" in kg1[40].instruction_en
    )  # V1 English: traced only
    assert "حَوِّط" in kg1[14].instruction  # big and small: the answer key rings the big one
    kg2 = {p.number: p for p in volume_pages("kg2", 1)}
    assert "العُصْفورَ" in kg2[22].instruction  # the maze's own walker
    assert "الأَرْنَبَ" in kg2[10].instruction or "الأَرْنَبِ" in kg2[10].instruction  # the path's walker
