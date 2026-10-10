"""«قلبي يعرف الله»: the two situation pages: «ماذا كنت ستفعل؟» (a short scene, three choices, a gentle word
about each) and
«ماذا أفعل لو…؟» (calm steps, one with its dua, the hadith behind it, a star to colour each day of the week).

Love before fear (Addendum 10 §3.8): a wrong choice is met with «جرّب مرّة أخرى», never a warning, and the
steps end with an
apology and a new try.
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.render.islamic_content import Quote, Wdif, Wwyd
from qamra_workbook.render.pages.islamic_common import (
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
    scene,
    scene_problems,
    source_ids,
)
from qamra_workbook.render.registry import Built, PageContext

WEEK = 7


@islamic_page("what-would-you-do")
def what_would_you_do(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Wwyd)
    problems: list[str] = []
    problems += scene_problems(page.scene)
    if len(page.choices) != 3 or sum(c.ok for c in page.choices) != 1:
        problems.append("three choices with exactly one right answer")
    ticks = [{"n": ctx.num(i), **c} for i, c in enumerate(choices(ctx, page.choices, problems), start=1)]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "scenario": rich(ctx, page.scenario, problems),
        "scene": scene(ctx, page.scene, "wy-art") if not problems else "",
        "choices": ticks,
        "quote": sacred(ctx, page.quote, "quote", problems),
        "role_play": rich(ctx, page.role_play, problems),
        "refs": references(
            ctx, [*page.sources, page.quote.source, *(s for c in page.choices for s in source_ids(c))]
        ),
        "labels": {"role": "تَمْثِيلٌ"},
    }
    answer = ["الأجمل: " + "، ".join(c["text"] for c in ticks if c["ok"])]
    return Built(data, answer, problems)


@islamic_page("what-do-i-do-if")
def what_do_i_do_if(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Wdif)
    problems: list[str] = []
    steps: list[dict[str, Any]] = []
    for step in page.steps:
        # each step names its own picture (`art`: a library picture or isl:<icon>); they used to be given by
        # position (wind, mouth, chair, heart), which only fitted the anger page
        found = picture_problems([step.art], f"step {step.n}") if step.art else []
        problems += found
        block = None
        if step.dua:
            block = sacred(ctx, Quote(source=step.dua), "dhikr", problems)
        steps.append(
            {
                "n": ctx.num(step.n),
                "text": rich(ctx, step.t, problems),
                "picture": picture(step.art, css_class="wd-pic") if step.art and not found else "",
                "dua": block,
            }
        )
    ids = [s for step in page.steps for s in [*step.sources, *source_ids(step.t)]] + [
        step.dua for step in page.steps if step.dua
    ]
    ids += [page.quote.source, *source_ids(page.meaning), *source_ids(page.intro)]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "intro": claim(ctx, page.intro, problems),
        "steps": steps,
        "quote": sacred(ctx, page.quote, "quote", problems),
        "meaning": claim(ctx, page.meaning, problems),
        "tracker": rich(ctx, page.tracker, problems),
        "days": [ctx.num(i) for i in range(1, WEEK + 1)],
        "refs": references(ctx, ids),
    }
    return Built(data, None, problems)
