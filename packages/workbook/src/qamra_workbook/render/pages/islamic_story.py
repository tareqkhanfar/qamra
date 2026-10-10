"""«قلبي يعرف الله»: the story page of a prophet and the sira page (scenes of nature, places and objects only,
told by the grandmother), and the dhikr page (a picture of the situation, when we say it and why, with the
wording from the register).

Addendum 10 §3.5: a prophet is never depicted, nor an angel or a Companion: the narrator panel shows the
recurring characters listening, and the scenes show the sea, the ship, the whale, the shore, the cave, the
road, never a person. The builder refuses a scene that draws people (the no-depiction check does the same on
the file)."""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_workbook.render.islamic_content import Dhikr, ProphetStory, SiraStory
from qamra_workbook.render.islamic_figures import listeners
from qamra_workbook.render.pages.islamic_common import (
    SPEAKERS,
    answer_lines,
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
    scene_problems,
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


def told_story(ctx: PageContext, page: ProphetStory | SiraStory) -> Built:
    """A story the grandmother tells: the listeners, the scenes (never a person), the verse or quotation, the
    lesson and a question."""
    problems: list[str] = []
    if not 1 <= len(page.scenes) <= MAX_SCENES:
        problems.append(f"a story page shows 1–{MAX_SCENES} scenes, not {len(page.scenes)}")
    for who in page.narrator.figures:
        if who not in SPEAKERS:
            problems.append(f"narrator figure {who!r} is not one of the recurring characters")
    scenes: list[dict[str, Any]] = []
    for i, item in enumerate(page.scenes, start=1):
        found = scene_problems(item, people=False, where=f"scene {i}")
        if found:
            problems += found
            continue
        scenes.append(
            {
                "n": ctx.num(i),
                "svg": scene(ctx, item, "st-art", n=i),
                "text": rich(ctx, item.text, problems),
                "ai": item.ai_drafted,
            }
        )
    question: dict[str, Any] = {
        "text": rich(ctx, page.question.text, problems),
        "choices": [choice(ctx, c, problems) for c in page.question.choices],
    }
    if sum(c.ok for c in page.question.choices) != 1:
        problems.append("the question needs exactly one right answer")
    block = page.verse if isinstance(page, ProphetStory) else page.quote
    ids = [s for item in page.scenes for s in [*item.sources, *source_ids(item.text)]] + source_ids(
        page.lesson
    )
    ids += [*page.question.sources, *(s for c in page.question.choices for s in source_ids(c))]
    if block is not None:
        ids.append(block.source)
    kind = "verse" if isinstance(page, ProphetStory) else "quote"
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "cast": _cast_art(ctx, page.narrator.figures),
        "intro": ctx.text(page.narrator.intro),
        "scenes": scenes,
        "verse": sacred(ctx, block, kind, problems) if block is not None else None,
        "lesson": claim(ctx, page.lesson, problems),
        "question": question,
        "refs": references(ctx, ids),
        "labels": {"lesson": "أَتَعَلَّمُ", "question": ctx.text("{فَكِّرْ/فَكِّرِي}")},
    }
    return Built(data, answer_lines(ctx, page.question.text, question["choices"]), problems)


@islamic_page("prophet-story")
def prophet_story(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, ProphetStory)
    return told_story(ctx, page)


@islamic_page("sira-story", shared="prophet-story")
def sira_story(ctx: PageContext) -> Built:
    """A moment from the life of our Prophet ﷺ: the same page as a prophet's story, with a hadith (or a verse)
    in the quiet frame."""
    page = page_of(ctx)
    assert isinstance(page, SiraStory)
    return told_story(ctx, page)


@islamic_page("dhikr-situation")
def dhikr_situation(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Dhikr)
    problems: list[str] = []
    problems += scene_problems(page.scene)
    ids = [page.dhikr.source, *source_ids(page.why), *source_ids(page.manner), *source_ids(page.home)]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "when": rich(ctx, page.when, problems),
        "scene": scene(ctx, page.scene, "dk-art") if not problems else "",
        "dhikr": sacred(ctx, page.dhikr, "dhikr", problems),
        "why": claim(ctx, page.why, problems),
        "manner": claim(ctx, page.manner, problems),
        "home": rich(ctx, page.home, problems),
        "days": [ctx.num(i) for i in range(1, WEEK + 1)],
        "labels": {
            "when": "مَتَى؟",
            "say": ctx.text(page.heading) if page.heading else "أَقُولُ",
            "why": "لِمَاذَا؟",
            "manner": "وَهَكَذَا أَتَأَدَّبُ",
            "home": "فِي الْبَيْتِ",
            "listen": ctx.text("{اسْمَعْ وَكَرِّرْ/اسْمَعِي وَكَرِّرِي}"),
        },
        "refs": references(ctx, ids),
    }
    return Built(data, None, problems)
