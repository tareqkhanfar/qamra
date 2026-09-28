from pathlib import Path
from typing import Any

import pytest
from qamra_workbook.family import (
    Activity,
    FamilyPlan,
    Levels,
    Page,
    Proposal,
    Section,
    book_pages,
    check_activities,
    check_pages,
    check_structure,
    check_variety,
    load,
    problems,
)

PLAN = Path(__file__).resolve().parents[3] / "content" / "family-book" / "plan.yaml"


def page(kind: str, instruction: str = "ابحث عن ثلاثة أشياء دائرية", **params: Any) -> Page:
    return Page(type=kind, title="مغامرة", instruction=instruction, params=params)


def activity(pages: list[Page], **extra: Any) -> Activity:
    fields: dict[str, Any] = {
        "id": "a1",
        "section": "home",
        "title": "صيد الدوائر",
        "goal": "الملاحظة",
        "skills": ["observation"],
        "child_part": "يبحث",
        "minutes": 10,
        "levels": Levels(simple="3 أشياء", challenge="5 أشياء"),
        "pages": pages,
    } | extra
    return Activity(**fields)


def plan(
    activities: list[Activity], front: list[Page] | None = None, back: list[Page] | None = None
) -> FamilyPlan:
    return FamilyPlan(
        title_ar="مغامراتي مع عائلتي",
        title_en="My Adventures",
        proposal=Proposal(concept="", size="", paper="", binding=""),
        front=front if front is not None else [page("title-page"), page("passport")],
        sections=[Section(id="home", title_ar="بيتي مدرسة", icon="🏠", hook="حكاية", badge="مستكشف البيت")],
        activities=activities,
        back=back if back is not None else [page("seven-day-challenge"), page("certificate-family")],
        inserts=[],
        samples=[],
    )


def test_pages_are_numbered_with_the_opening_spread() -> None:
    pages = book_pages(plan([activity([page("scavenger-hunt"), page("memory-page")])]))
    assert [p.page.type for p in pages] == [
        "title-page", "passport", "section-opener", "section-opener", "scavenger-hunt", "memory-page",
        "seven-day-challenge", "certificate-family",
    ]  # fmt: skip
    assert pages[2].n == 3 and check_structure(plan([activity([page("memory-page")])]), pages) == [
        "home: the opening spread starts on p3; a spread starts on an even page"
    ]


def test_missions_never_assume_a_mother_and_a_father() -> None:
    bad = page("recipe-steps", instruction="حضّر الطبق مع ماما")
    found = check_pages(plan([]), [p for p in book_pages(plan([activity([bad])])) if p.page is bad])
    assert any("{adult}" in f for f in found)
    ok = page("recipe-steps", instruction="حضّر الطبق مع {adult}")
    found = check_pages(plan([]), [p for p in book_pages(plan([activity([ok])])) if p.page is ok])
    assert not any("{adult}" in f or "placeholders" in f for f in found)
    for text, assumed in (("وماما تساعد", True), ("لون أبيض", False), ("تاج الأميرة", False)):
        tricky = page("drawing", instruction=text)
        found = check_pages(plan([]), [p for p in book_pages(plan([activity([tricky])])) if p.page is tricky])
        assert any("{adult}" in f for f in found) is assumed, text


def test_recipes_are_safe_by_default() -> None:
    nuts = activity([page("recipe-steps", ingredients=["تمر", "جوز"])], safety="الكبير يمسك السكين")
    found = check_activities(plan([nuts]))
    assert any("allergies" in f for f in found) and any("nuts" in f for f in found)


def test_outdoor_activities_need_supervision_and_the_same_format_does_not_repeat() -> None:
    outside = activity([page("nature-bingo")], where="outside")
    assert any("outdoor activities need a safety note" in f for f in check_activities(plan([outside])))
    repeated = book_pages(plan([activity([page("drawing"), page("drawing"), page("memory-page")])]))
    assert any("drawing again" in f for f in check_variety(repeated))


@pytest.mark.skipif(not PLAN.exists(), reason="the family plan is not written yet")
def test_family_plan_keeps_every_rule() -> None:
    assert problems(load(PLAN)) == []
