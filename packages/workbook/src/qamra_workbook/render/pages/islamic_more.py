"""«قلبي يعرف الله»: the thin page types the series lists (Addendum 10 §7) that the samples do not need: true
or false, a pillar card, «يومي مع الله» (a day's timeline), the four endings of a unit, and the final
assessment (stars the parent gives for what they observe, not an exam). Each is a small working builder on the
shared chrome and blocks."""

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
    answer_lines,
    choices,
    chrome,
    claim,
    islamic_page,
    page_of,
    picture,
    picture_problems,
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
        "labels": {"true": "صَحِيحٌ", "false": "خَطَأٌ"},
        "refs": references(ctx, [s for t in page.statements for s in [*t.sources, *source_ids(t.t)]]),
    }
    return Built(data, [f"{r['n']}: {'صحيح' if r['ok'] else 'خطأ'}" for r in rows], problems)


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
            "choices": choices(ctx, page.question.choices, problems),
        },
        "refs": references(ctx, [*source_ids(page.idea), *page.question.sources]),
    }
    return Built(data, answer_lines(ctx, page.question.text, data["question"]["choices"]), problems)


@islamic_page("my-day-with-allah")
def my_day_with_allah(ctx: PageContext) -> Built:
    """«يومي مع الله»: the moments of a day in order, each with its picture and a circle the child ticks."""
    page = page_of(ctx)
    assert isinstance(page, DayWithAllah)
    problems: list[str] = []
    if not 2 <= len(page.moments) <= MAX_MOMENTS:
        problems.append(f"a day shows 2–{MAX_MOMENTS} moments, not {len(page.moments)}")
    problems += picture_problems([m.picture for m in page.moments], "moments")
    moments = [
        {
            "n": ctx.num(i),
            "when": ctx.text(m.when),
            "text": rich(ctx, m.t, problems),
            "pic": picture(m.picture, css_class="dy-pic", i=i) if not problems else "",
        }
        for i, m in enumerate(page.moments, start=1)
    ]
    ids = [s for m in page.moments for s in [*m.sources, *source_ids(m.t)]]
    if page.closing:
        ids += source_ids(page.closing)
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "moments": moments,
        "tick": page.tick,
        "closing": claim(ctx, page.closing, problems) if page.closing else None,
        "dense": len(moments) > 6,
        "refs": references(ctx, ids),
    }
    return Built(data, None, problems)


@islamic_page("unit-closing")
def unit_closing(ctx: PageContext) -> Built:
    """The endings of a unit (Addendum 10 §5): what I learned (a star to colour by each), what I will do this
    week (options to tick), the unit's dhikr (from the register) and a small challenge with mum and dad (a
    week of stars). A closing page shows the endings it carries; the unit's two closing pages carry all four.
    """
    page = page_of(ctx)
    assert isinstance(page, UnitClosing)
    problems: list[str] = []
    ids = [s for t in [*page.learned, page.apply, *page.apply_choices, page.challenge] for s in source_ids(t)]
    if page.dhikr is not None:
        ids.append(page.dhikr.source)
    verse = page.dhikr is not None and page.dhikr.source.startswith("q-")
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "learned": [rich(ctx, t, problems) for t in page.learned],
        "apply": rich(ctx, page.apply, problems) if page.apply else "",
        "apply_choices": [rich(ctx, t, problems) for t in page.apply_choices],
        "dhikr": sacred(ctx, page.dhikr, "dhikr", problems) if page.dhikr is not None else None,
        "dhikr_when": rich(ctx, page.dhikr_when, problems) if page.dhikr_when else "",
        "challenge": rich(ctx, page.challenge, problems) if page.challenge else "",
        "days": [ctx.num(i) for i in range(1, 8)],
        "parts": sum(bool(x) for x in (page.learned, page.apply, page.dhikr, page.challenge)),
        "labels": {
            "learned": "مَاذَا تَعَلَّمْتُ؟",
            "apply": "مَاذَا سَأُطَبِّقُ هَذَا الْأُسْبُوعَ؟",
            # a verse is not called a dhikr: the tab over a Quran frame says «آيَةُ الْوَحْدَةِ»
            "dhikr": "آيَةُ الْوَحْدَةِ" if verse else "ذِكْرُ الْوَحْدَةِ",
            # the stars are the week's days, not things to count («خَمْسَةَ أَشْيَاءَ» over stars ١–٧ misled)
            "week": "نَجْمَةٌ لِكُلِّ يَوْمٍ مِنْ أَيَّامِ الْأُسْبُوعِ",
            "challenge": "تَحَدٍّ صَغِيرٌ مَعَ أُمِّي وَأَبِي",
        },
        "refs": references(ctx, ids),
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
        "labels": {"parent": "نُجُومٌ يُلَوِّنُهَا الْأَهْلُ", "play": "لُعْبَةٌ لَا امْتِحَانٌ"},
        "refs": references(ctx, [s for k in page.skills for s in [*k.sources, *source_ids(k.t)]]),
    }
    return Built(data, None, problems)
