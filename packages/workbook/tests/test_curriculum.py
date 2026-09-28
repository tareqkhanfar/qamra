from pathlib import Path
from typing import Any

import pytest
from qamra_workbook.curriculum import (
    Curriculum,
    Page,
    Unit,
    Volume,
    check_interleaving,
    check_numbering,
    check_numbers,
    check_one_sided,
    check_reviews,
    load,
    problems,
)

CURRICULUM = Path(__file__).resolve().parents[3] / "content" / "workbook" / "curriculum"


def page(n: int, subject: str = "arabic", kind: str = "letter-intro", unit: str = "u", **params: Any) -> Page:
    return Page(
        n=n, week=1, subject=subject, unit=unit, type=kind, skill="مهارة", difficulty=1, params=params
    )  # type: ignore[arg-type]


def volume(pages: list[Page], units: list[Unit] | None = None) -> Volume:
    units = units or [Unit(id="u", subject="arabic", title_ar="وحدة")]
    return Volume(volume=1, term=1, weeks=1, title_ar="الجزء الأول", objectives={}, units=units, pages=pages)


def test_subjects_rotate_in_short_blocks() -> None:
    four = [page(i) for i in range(1, 5)] + [page(5, "math")]
    assert check_interleaving(volume(four)) == []
    five = [page(i) for i in range(1, 6)]
    assert check_interleaving(volume(five)) == ["V1 p5: more than 4 arabic pages in a row"]


def test_page_numbers_and_even_count() -> None:
    pages = [page(i, "arabic" if i % 2 else "math") for i in range(1, 112)]
    found = check_numbering(volume(pages))
    assert any("even count" in p for p in found)
    gap = [page(1), page(3)]
    assert any("without gaps" in p for p in check_numbering(volume(gap)))


def test_cut_and_paste_needs_a_blank_back() -> None:
    cut = Page(
        n=3,
        week=1,
        subject="thinking",
        unit="t",
        type="cut-and-paste",
        skill="قص",
        difficulty=1,
        one_sided=True,
    )
    units = [Unit(id="t", subject="thinking", title_ar="ت")]
    ok = volume(
        [
            page(1, "thinking", "maze", "t"),
            page(2, "thinking", "maze", "t"),
            cut,
            page(4, "thinking", "blank", "t"),
        ],
        units,
    )
    assert check_one_sided(ok) == []
    bad = volume(
        [
            page(1, "thinking", "maze", "t"),
            page(2, "thinking", "maze", "t"),
            cut,
            page(4, "thinking", "maze", "t"),
        ],
        units,
    )
    assert check_one_sided(bad) == ["V1 p3: one-sided page; the other side of its sheet must be a blank page"]


def test_units_end_with_a_review_and_subjects_with_an_assessment() -> None:
    units = [Unit(id=s, subject=s, title_ar=s) for s in ("arabic", "math", "english", "thinking")]  # type: ignore[arg-type]
    pages = [page(1, "arabic", "letter-intro", "arabic"), page(2, "arabic", "unit-review", "arabic")]
    found = check_reviews(volume(pages, units))
    assert "V1: no arabic assessment after the last arabic page" in found
    assert "V1: no math pages" in found
    pages[1] = page(2, "arabic", "letter-trace", "arabic")
    assert any("unit arabic ends on p2" in p for p in check_reviews(volume(pages, units)))


@pytest.mark.parametrize("path", sorted(CURRICULUM.glob("*.yaml")), ids=lambda p: p.stem)
def test_curriculum_plans_keep_every_rule(path: Path) -> None:
    assert problems(load(path)) == []


def test_a_number_intro_without_a_number_is_reported_not_crashed() -> None:
    v = volume([page(1, "math", "number-intro", "m")], [Unit(id="m", subject="math", title_ar="أعداد")])
    plan = Curriculum(
        level="kg2",
        age="5–6",
        title_ar="x",
        title_en="x",
        letter_order=[],
        progression_notes="",
        interleaving_notes="",
        alignment_notes="",
        volumes=[v],
    )
    assert "V1 p1: number-intro needs params.number" in check_numbers(plan)
