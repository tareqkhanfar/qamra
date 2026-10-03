"""«قلبي يعرف الله»: the review pages: «اختبر نفسك» (a cumulative review: true or false, questions, stars) and
the final fun assessment (Addendum 10 §6): a game, not an exam: true or false, questions, short situations,
and the parents' observation stars for each skill. The answer key lists every right answer for the parent."""

from __future__ import annotations

from typing import Any

from qamra_workbook.render.islamic_content import Ask, Assessment, Choice, Quiz, TrueFalse
from qamra_workbook.render.pages.islamic_common import (
    choice,
    chrome,
    islamic_page,
    page_of,
    references,
    rich,
    source_ids,
)
from qamra_workbook.render.registry import Built, PageContext

STARS = 3


def statements(ctx: PageContext, rows: list[TrueFalse], problems: list[str]) -> list[dict[str, Any]]:
    return [
        {"n": ctx.num(i), "text": rich(ctx, t.t, problems), "ok": t.ok} for i, t in enumerate(rows, start=1)
    ]


def asks(ctx: PageContext, items: list[Ask], problems: list[str], first: int = 1) -> list[dict[str, Any]]:
    out = []
    for i, q in enumerate(items, start=first):
        if sum(c.ok for c in q.choices) != 1:
            problems.append(f"question {i} needs exactly one right answer")
        out.append(
            {
                "n": ctx.num(i),
                "text": rich(ctx, q.text, problems),
                "choices": [choice(ctx, c, problems) for c in q.choices],
            }
        )
    return out


def _ids(rows: list[TrueFalse], items: list[Any]) -> list[str]:
    ids = [s for t in rows for s in [*t.sources, *source_ids(t.t)]]
    for q in items:
        ids += q.sources
        ids += [s for c in q.choices for s in source_ids(c)]
        ids += source_ids(getattr(q, "text", "") or getattr(q, "t", ""))
    return ids


def _right(choices: list[dict[str, Any]]) -> str:
    return "، ".join(str(c["text"]) for c in choices if c["ok"])


LABELS = {
    "tf": "صَحِيحٌ أَمْ خَطَأٌ؟",
    "true": "صَحِيحٌ",
    "false": "خَطَأٌ",
    "choose": "{اخْتَرِ/اخْتَارِي} الْجَوَابَ الصَّحِيحَ",
    "situations": "مَاذَا {تَفْعَلُ/تَفْعَلِينَ}؟",
    "parent": "نُجُومٌ يُلَوِّنُهَا الْأَهْلُ",
    "play": "لُعْبَةٌ لَا امْتِحَانٌ",
}


def labels(ctx: PageContext) -> dict[str, str]:
    return {k: ctx.text(v) for k, v in LABELS.items()}


@islamic_page("islamic-self-test")
def self_test(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Quiz)
    problems: list[str] = []
    rows = statements(ctx, page.true_false, problems)
    questions = asks(ctx, page.questions, problems)
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "subtitle": ctx.text(page.subtitle),
        "rows": rows,
        "questions": questions,
        "stars_text": ctx.text(page.stars),
        "star_count": STARS,
        "refs": references(ctx, _ids(page.true_false, page.questions)),
        "labels": labels(ctx),
    }
    answer = [f"{r['n']}: {'صحيح' if r['ok'] else 'خطأ'}" for r in rows]
    answer += [f"س{q['n']}: {_right(q['choices'])}" for q in questions]
    return Built(data, answer, problems)


@islamic_page("islamic-assessment")
def assessment(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Assessment)
    problems: list[str] = []
    rows = statements(ctx, page.true_false, problems)
    questions = asks(ctx, page.questions, problems)
    situations: list[dict[str, Any]] = []
    for i, s in enumerate(page.situations, start=1):
        if sum(c.ok for c in s.choices) != 1:
            problems.append(f"situation {i} needs exactly one right answer")
        options: list[Choice] = s.choices
        situations.append(
            {
                "n": ctx.num(i),
                "text": rich(ctx, s.t, problems),
                "choices": [choice(ctx, c, problems) for c in options],
            }
        )
    skills = [{"skill": ctx.text(k.skill), "text": rich(ctx, k.t, problems)} for k in page.skills]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "intro": rich(ctx, page.intro, problems) if page.intro else "",
        "rows": rows,
        "questions": questions,
        "situations": situations,
        "skills": skills,
        "stars": STARS,
        "note": rich(ctx, page.note, problems) if page.note else "",
        "refs": references(
            ctx,
            _ids(page.true_false, [*page.questions, *page.situations])
            + [s for k in page.skills for s in k.sources],
        ),
        "labels": labels(ctx),
    }
    answer = [f"{r['n']}: {'صحيح' if r['ok'] else 'خطأ'}" for r in rows]
    answer += [f"س{q['n']}: {_right(q['choices'])}" for q in questions]
    answer += [f"موقف {s['n']}: {_right(s['choices'])}" for s in situations]
    return Built(data, answer or None, problems)
