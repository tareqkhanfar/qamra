"""«قلبي يعرف الله»: the told pages: a short story or dialogue of the cast (a picture, a few lines, and
optionally a quotation by source id, a lesson and a question), and the role-play with the family (the
situation, the parts and who plays them, a short script, a tip for the grown-up).

The people on these pages are the cast only (Addendum 10 §4.6): each line of a story shows its speaker's face
in a small round frame, drawn by `render.islamic_figures` (the reader is the child's own character)."""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_workbook.render.islamic_content import RolePlay, Story
from qamra_workbook.render.islamic_figures import cast_names
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
    scene_problems,
    source_ids,
)
from qamra_workbook.render.registry import Built, PageContext

MAX_LINES = 6
MAX_LINES_WITH_MORE = 4  # with a quotation or a question, the page holds fewer lines
NAMES = cast_names()


def _head(head_y: float, radius: float) -> tuple[float, float]:
    """(feet, height) that put a figure's head (centre `head_y`, radius `radius` in the people box) in the
    middle of a 24-unit round frame, filling about three quarters of it."""
    k = 18.0 / (2.8 * radius)
    return 13.0 - head_y * k + 118.0 * k, 120.0 * k


# who → (feet, height) of the figure in its face frame: the people box's heads (render/people.py), the cat
# whole, the reader's cut-out from the head down
FACES: dict[str, tuple[float, float]] = {
    "huda": _head(24.0, 11.0),
    "reem": _head(50.0, 12.5),
    "salem": _head(50.0, 12.5),
    "naanaa": (22.0, 18.0),
    "reader": (52.0, 56.0),
}


def face(ctx: PageContext, who: str) -> Markup:
    """The speaker's head and shoulders in a round frame (the cast only; `narrator` has none)."""
    if who == "narrator":
        return Markup("")
    clip = f"{ctx.page.id}-face-{who}"
    feet, height = FACES.get(who, (52.0, 56.0))
    figure = context_of(ctx).kit.figure(who, 12.0, feet, height)
    return Markup(  # nosec B704 (the kit's drawing of a cast member)
        f'<svg class="tl-face" viewBox="0 0 24 24" aria-hidden="true"><defs><clipPath id="{clip}">'
        f'<circle cx="12" cy="12" r="11.4"/></clipPath></defs>'
        f'<circle cx="12" cy="12" r="11.4" fill="#FFF3D4"/>'
        f'<g clip-path="url(#{clip})">{figure}</g></svg>'
    )


def speaker(ctx: PageContext, who: str) -> str:
    if who == "narrator":
        return ""
    return ctx.text("{child}" if who == "reader" else NAMES.get(who, who))


def _ask(ctx: PageContext, ask: Any, problems: list[str]) -> dict[str, Any]:
    if sum(c.ok for c in ask.choices) != 1:
        problems.append("the question needs exactly one right answer")
    return {
        "text": rich(ctx, ask.text, problems),
        "choices": [choice(ctx, c, problems) for c in ask.choices],
    }


@islamic_page("islamic-story")
def story(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Story)
    problems = scene_problems(page.scene)
    limit = MAX_LINES_WITH_MORE if (page.quote or page.question) else MAX_LINES
    if len(page.lines) > limit:
        problems.append(f"{len(page.lines)} lines: a story holds {limit} with a quote or a question")
    lines = [
        {
            "who": line.who,
            "face": face(ctx, line.who),
            "name": speaker(ctx, line.who),
            "text": rich(ctx, line.t, problems),
            "ai": line.ai_drafted,
        }
        for line in page.lines
    ]
    question = _ask(ctx, page.question, problems) if page.question else None
    ids = [s for line in page.lines for s in [*line.sources, *source_ids(line.t)]]
    if page.lesson:
        ids += source_ids(page.lesson)
    if page.question:
        ids += [*page.question.sources, *(s for c in page.question.choices for s in source_ids(c))]
    if page.quote:
        ids.append(page.quote.source)
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "scene": scene(ctx, page.scene, "tl-art") if not scene_problems(page.scene) else "",
        "lines": lines,
        "quote": sacred(ctx, page.quote, "quote", problems) if page.quote else None,
        "lesson": claim(ctx, page.lesson, problems) if page.lesson else None,
        "question": question,
        "compact": bool(page.quote or page.question or page.lesson) and len(lines) > 3,
        "refs": references(ctx, ids),
        "labels": {"lesson": "أَتَعَلَّمُ"},
    }
    answer = None
    if question is not None:
        answer = ["الجواب: " + "، ".join(str(c["text"]) for c in question["choices"] if c["ok"])]
    return Built(data, answer, problems)


@islamic_page("islamic-role-play")
def role_play(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, RolePlay)
    problems = scene_problems(page.scene)
    roles = [
        {"role": ctx.text(r.role), "by": ctx.text(r.by), "n": ctx.num(i)} for i, r in enumerate(page.roles, 1)
    ]
    order = {r.role: i for i, r in enumerate(page.roles)}
    script = [
        {"role": ctx.text(s.role), "n": order[s.role], "text": rich(ctx, s.t, problems)} for s in page.script
    ]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "scenario": rich(ctx, page.scenario, problems),
        "scene": scene(ctx, page.scene, "rp-art") if not scene_problems(page.scene) else "",
        "roles": roles,
        "script": script,
        "tip": rich(ctx, page.tip, problems),
        "stars": ctx.text(page.stars),
        "refs": references(ctx, [s for line in page.script for s in [*line.sources, *source_ids(line.t)]]),
        "labels": {"roles": "الْأَدْوَارُ", "script": "الْحِوَارُ", "parent": "لِلْأَهْلِ"},
    }
    return Built(data, None, problems)
