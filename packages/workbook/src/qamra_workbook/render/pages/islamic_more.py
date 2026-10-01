"""«قلبي يعرف الله»: the thin page types the series lists (Addendum 10 §7) that the samples do not need:
true or false, a
pillar card, «يومي مع الله» (a day's timeline), the four endings of a unit, and the final assessment (stars
the parent gives
for what they observe, not an exam). Each is a small working builder on the shared chrome and blocks.
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.render.islamic_content import (
    DayWithAllah,
    FinalAssessment,
    PillarCard,
    TrueFalsePage,
    UnitClosing,
)
from qamra_workbook.render.pages.islamic_common import (
    choice,
    chrome,
    claim,
    islamic_page,
    page_of,
    references,
    rich,
    sacred,
    source_ids,
)
from qamra_workbook.render.registry import Built, PageContext

MAX_MOMENTS = 10
SKILL_STARS = 3


@islamic_page("true-false")
def true_false(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, TrueFalsePage)
    problems: list[str] = []
    rows = [
        {"n": ctx.num(i), "text": rich(ctx, t.t, problems), "ok": t.ok}
        for i, t in enumerate(page.statements, start=1)
    ]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "rows": rows,
        "labels": {"true": "صَحٌّ", "false": "خَطَأٌ"},
        "refs": references(ctx, [s for t in page.statements for s in [*t.sources, *source_ids(t.t)]]),
    }
    return Built(data, [f"{r['n']}: {'صح' if r['ok'] else 'خطأ'}" for r in rows], problems)


@islamic_page("pillar-card")
def pillar_card(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, PillarCard)
    problems: list[str] = []
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "pillar": rich(ctx, page.pillar, problems),
        "idea": claim(ctx, page.idea, problems),
        "question": {
            "text": rich(ctx, page.question.text, problems),
            "choices": [choice(ctx, c, problems) for c in page.question.choices],
        },
        "refs": references(ctx, [*source_ids(page.idea), *page.question.sources]),
    }
    return Built(
        data, ["الجواب: " + "، ".join(c["text"] for c in data["question"]["choices"] if c["ok"])], problems
    )


@islamic_page("my-day-with-allah")
def my_day_with_allah(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, DayWithAllah)
    problems: list[str] = []
    if not 2 <= len(page.moments) <= MAX_MOMENTS:
        problems.append(f"a day shows 2–{MAX_MOMENTS} moments, not {len(page.moments)}")
    moments = [
        {
            "n": ctx.num(i),
            "when": ctx.text(m.when),
            "text": rich(ctx, m.t, problems),
            "pic": ctx.pic(m.picture, "color", "dy-pic"),
        }
        for i, m in enumerate(page.moments, start=1)
    ]
    ids = [s for m in page.moments for s in [*m.sources, *source_ids(m.t)]]
    return Built(
        {"chrome": chrome(ctx, problems), "moments": moments, "refs": references(ctx, ids)}, None, problems
    )


@islamic_page("unit-closing")
def unit_closing(ctx: PageContext) -> Built:
    """The four endings of a unit: what I learned, what I will do this week, the unit's dhikr (from the
    register), a
    small challenge with mum and dad."""
    page = page_of(ctx)
    assert isinstance(page, UnitClosing)
    problems: list[str] = []
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "learned": [rich(ctx, t, problems) for t in page.learned],
        "apply": rich(ctx, page.apply, problems),
        "dhikr": sacred(ctx, page.dhikr, "dhikr", problems),
        "challenge": rich(ctx, page.challenge, problems),
        "days": [ctx.num(i) for i in range(1, 8)],
        "labels": {
            "learned": "مَاذَا تَعَلَّمْتُ؟",
            "apply": "مَاذَا سَأُطَبِّقُ هَذَا الْأُسْبُوعَ؟",
            "dhikr": "ذِكْرُ الْوَحْدَةِ",
            "challenge": "تَحَدٍّ صَغِيرٌ مَعَ أُمِّي وَأَبِي",
        },
        "refs": references(
            ctx,
            [
                page.dhikr.source,
                *(s for t in [*page.learned, page.apply, page.challenge] for s in source_ids(t)),
            ],
        ),
    }
    return Built(data, None, problems)


@islamic_page("final-assessment")
def final_assessment(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, FinalAssessment)
    problems: list[str] = []
    skills = [{"skill": ctx.text(s.skill), "text": rich(ctx, s.t, problems)} for s in page.skills]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "skills": skills,
        "stars": SKILL_STARS,
        "note": rich(ctx, page.note, problems),
        "labels": {"parent": "نُجُومُ مُلَاحَظَةِ الْأَهْلِ", "play": "لُعْبَةٌ لَا امْتِحَانٌ"},
        "refs": references(ctx, [s for k in page.skills for s in [*k.sources, *source_ids(k.t)]]),
    }
    return Built(data, None, problems)
