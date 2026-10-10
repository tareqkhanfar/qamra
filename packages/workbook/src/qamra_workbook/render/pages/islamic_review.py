"""«قلبي يعرف الله»: the review page «ماذا أتذكّر؟» (true or false, choose, stars) and the parent page
(Addendum 10 §4.8, §5).

The review is a game, not an exam: the child rings صح or خطأ, ticks one answer and colours the stars they
think they
earned. The answer key lists the right answers for the parent. The parent page is plain modern Arabic, not
vowelised.
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.render.islamic_content import ParentGuide, UnitReview
from qamra_workbook.render.pages.islamic_common import (
    choices,
    chrome,
    claim,
    context_of,
    islamic_page,
    page_of,
    references,
    rich,
    source_ids,
)
from qamra_workbook.render.registry import Built, PageContext

STARS_IN_REVIEW = 3


@islamic_page("islamic-unit-review")
def unit_review(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, UnitReview)
    problems: list[str] = []
    rows = [
        {"n": ctx.num(i), "text": rich(ctx, t.t, problems), "ok": t.ok}
        for i, t in enumerate(page.true_false, start=1)
    ]
    choose: dict[str, Any] = {
        "text": rich(ctx, page.choose.text, problems),
        "choices": choices(ctx, page.choose.choices, problems),
    }
    if sum(c.ok for c in page.choose.choices) != 1:
        problems.append("the choose question needs exactly one right answer")
    ids = [s for t in page.true_false for s in [*t.sources, *source_ids(t.t)]] + page.choose.sources
    ids += [s for c in page.choose.choices for s in source_ids(c)]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "subtitle": ctx.text(page.subtitle),
        "rows": rows,
        "choose": choose,
        "stars_text": ctx.text(page.stars),
        "star_count": STARS_IN_REVIEW,
        "refs": references(ctx, ids),
        "labels": {
            "tf": "صَحِيحٌ أَمْ خَطَأٌ؟",
            "true": "صَحِيحٌ",
            "false": "خَطَأٌ",
            "choose": ctx.text("{اخْتَرِ/اخْتَارِي} الْجَوَابَ الصَّحِيحَ"),
        },
    }
    answer = [f"{r['n']}: {'صحيح' if r['ok'] else 'خطأ'}" for r in rows]
    answer.append("الاختيار: " + "، ".join(c["text"] for c in choose["choices"] if c["ok"]))
    return Built(data, answer, problems)


# what the parent page's five sections are called, and the engine icon of each
PARENT_SECTIONS = (
    ("learned", "ما الذي تعلّمه طفلكم؟", "cap"),
    ("explain", "كيف نشرح الفكرة؟", "talk"),
    ("ask", "{سؤال نطرحه عليه/سؤال نطرحه عليها}", "bulb"),
    ("together", "نشاط نفعله معًا", "family"),
    ("habit", "كيف نجعلها عادة يومية؟", "clock"),
)


@islamic_page("parent-guide")
def parent_guide(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, ParentGuide)
    problems: list[str] = []
    sections: list[dict[str, Any]] = []
    for key, label, icon in PARENT_SECTIONS:
        value = getattr(page, key)
        sections.append({"label": ctx.text(label), "icon": icon, **claim(ctx, value, problems)})
    ids = [s for key, _, _ in PARENT_SECTIONS for s in source_ids(getattr(page, key))]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "sections": sections,
        "care": rich(ctx, page.care_note, problems),
        "refs": references(ctx, ids),
        "preview": context_of(ctx).mode == "preview",
    }
    return Built(data, None, problems)
