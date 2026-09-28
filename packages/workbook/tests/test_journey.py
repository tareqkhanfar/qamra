from pathlib import Path
from typing import Any

import pytest
from qamra_workbook.journey import (
    JourneyPage,
    Section,
    Stage,
    check_memory_pairs,
    check_sections,
    check_stage_pages,
    check_stage_scope,
    check_variety,
    load,
    problems,
)

PLAN = Path(__file__).resolve().parents[3] / "content" / "journey" / "plan.yaml"
SECTIONS = [Section(id="think", title_ar="أدرّب عقلي", icon="🧠", journey_step="أفكر")]


def page(
    n: int, kind: str, section: str = "think", instruction: str = "لوّن الدوائر", **params: Any
) -> JourneyPage:
    return JourneyPage(
        n=n,
        section=section,
        type=kind,
        title="مهمة",
        instruction=instruction,
        skill="x",
        difficulty=1,
        params=params,
    )


def stage(pages: list[JourneyPage], number: int = 1) -> Stage:
    return Stage(stage=number, age="3–4", title_ar="المحطة", objectives={}, pages=pages)


def test_instructions_stay_short() -> None:
    long = page(1, "odd-one-out", instruction="ابحث عن الصورة المختلفة بين كل هذه الصور الجميلة هنا")
    assert any("instruction has 10 words" in p for p in check_stage_pages(stage([long])))


def test_sections_open_on_the_map_and_close_with_a_review() -> None:
    pages = [
        page(1, "journey-map", "intro"),
        page(2, "section-opener"),
        page(3, "odd-one-out"),
        page(4, "mini-certificate"),
    ]
    assert check_sections(stage(pages), SECTIONS) == []
    pages[1] = page(2, "odd-one-out")
    assert any("starts with a section-opener" in p for p in check_sections(stage(pages), SECTIONS))


def test_the_same_format_is_not_repeated() -> None:
    pages = [page(i, "maze") for i in range(1, 4)]
    assert check_variety(stage(pages)) == ["S1 p3: more than 2 maze pages in a row"]


def test_memory_pages_are_the_two_sides_of_one_sheet() -> None:
    assert check_memory_pairs(stage([page(1, "memory-look"), page(2, "memory-recall")])) == []
    wrong = stage([page(1, "odd-one-out"), page(2, "memory-look"), page(3, "memory-recall")])
    assert any("odd page" in p for p in check_memory_pairs(wrong))


def test_stage_one_has_no_letters_and_small_quantities() -> None:
    pages = [page(1, "letter-intro", letter="ب"), page(2, "quantity-first", numbers=[7])]
    found = check_stage_scope(stage(pages))
    assert any("no letters in stage 1" in p for p in found)
    assert any("quantities 1–5" in p for p in found)


@pytest.mark.skipif(not PLAN.exists(), reason="the journey plan is not written yet")
def test_journey_plan_keeps_every_rule() -> None:
    assert problems(load(PLAN)) == []
