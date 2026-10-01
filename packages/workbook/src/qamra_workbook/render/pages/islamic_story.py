"""«قلبي يعرف الله»: the story page of a prophet (scenes of nature, places and objects only, told by the
grandmother) and the
dhikr page (a picture of the situation, when we say it and why, with the wording from the register).

Addendum 10 §3.5: a prophet is never depicted, nor an angel or a Companion: the narrator panel shows the
recurring
characters listening, and the four scenes show the sea, the ship, the whale, the shore, never a person. The
builder
refuses a scene whose art draws people (the no-depiction check does the same on the file).
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_workbook.pictures.islamic import SCENES
from qamra_workbook.render.islamic_content import Dhikr, ProphetStory
from qamra_workbook.render.islamic_figures import CAST, listeners
from qamra_workbook.render.pages.islamic_common import (
    choice,
    chrome,
    claim,
    context_of,
    islamic_page,
    page_of,
    references,
    rich,
    sacred,
    scene,
    source_ids,
)
from qamra_workbook.render.registry import Built, PageContext

MAX_SCENES = 6
WEEK = 7  # the days of the home challenge: a star to colour for each


def _cast_art(ctx: PageContext, who: list[str]) -> Markup:
    width, height = 62.0, 30.0
    inner = listeners(context_of(ctx).kit, who, width, height)
    # nosec B704
    return Markup(f'<svg class="st-cast" viewBox="0 0 {width:g} {height:g}" aria-hidden="true">{inner}</svg>')


@islamic_page("prophet-story")
def prophet_story(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, ProphetStory)
    problems: list[str] = []
    if not 1 <= len(page.scenes) <= MAX_SCENES:
        problems.append(f"a story page shows 1–{MAX_SCENES} scenes, not {len(page.scenes)}")
    for who in page.narrator.figures:
        if who not in CAST:
            problems.append(f"narrator figure {who!r} is not one of the recurring characters")
    scenes: list[dict[str, Any]] = []
    for i, item in enumerate(page.scenes, start=1):
        art = SCENES.get(item.art)
        if art is None:
            problems.append(f"scene {i}: no art {item.art!r}")
            continue
        if art.figures or item.figures:
            problems.append(f"scene {i}: {item.art!r} draws people, and a prophet's story shows none")
            continue
        scenes.append(
            {
                "n": ctx.num(i),
                "svg": scene(ctx, item.art, "st-art"),
                "text": rich(ctx, item.text, problems),
                "ai": item.ai_drafted,
            }
        )
    question: dict[str, Any] = {
        "text": rich(ctx, page.question.text, problems),
        "choices": [choice(ctx, c, problems) for c in page.question.choices],
    }
    ids = [s for item in page.scenes for s in [*item.sources, *source_ids(item.text)]] + source_ids(
        page.lesson
    )
    ids += [
        *page.question.sources,
        page.verse.source,
        *(s for c in page.question.choices for s in source_ids(c)),
    ]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "cast": _cast_art(ctx, page.narrator.figures),
        "intro": ctx.text(page.narrator.intro),
        "scenes": scenes,
        "verse": sacred(ctx, page.verse, "verse", problems),
        "lesson": claim(ctx, page.lesson, problems),
        "question": question,
        "refs": references(ctx, ids),
        "labels": {"lesson": "أَتَعَلَّمُ", "question": ctx.text("{فَكِّرْ/فَكِّرِي}")},
    }
    answer = ["الجواب: " + "، ".join(c["text"] for c in question["choices"] if c["ok"])]
    return Built(data, answer, problems)


@islamic_page("dhikr-situation")
def dhikr_situation(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Dhikr)
    problems: list[str] = []
    for who in page.scene.figures:
        if who != "reader" and who not in CAST:
            problems.append(f"scene figure {who!r} is not one of the cast")
    ids = [page.dhikr.source, *source_ids(page.why), *source_ids(page.manner), *source_ids(page.home)]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "when": rich(ctx, page.when, problems),
        "scene": scene(ctx, page.scene.art, "dk-art"),
        "dhikr": sacred(ctx, page.dhikr, "dhikr", problems),
        "why": claim(ctx, page.why, problems),
        "manner": claim(ctx, page.manner, problems),
        "home": rich(ctx, page.home, problems),
        "days": [ctx.num(i) for i in range(1, WEEK + 1)],
        "labels": {
            "when": "مَتَى؟",
            "say": "أَقُولُ",
            "why": "لِمَاذَا؟",
            "manner": "وَهَكَذَا أَتَأَدَّبُ",
            "home": "فِي الْبَيْتِ",
            "listen": "اسْمَعْ وَكَرِّرْ",
        },
        "refs": references(ctx, ids),
    }
    return Built(data, None, problems)
