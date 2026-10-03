"""«قلبي يعرف الله»: the play pages: find the things on a board, match two columns, choose the right answer, a
maze, a drawing page and a cut-and-paste sheet. The pictures are the picture library's (or the series' icons,
`isl:<icon>`), never a person: people are only the cast (Addendum 10 §3.5).

Maze, drawing and cut-and-paste pages carry no verse, hadith or dhikr (they are drawn on, cut and thrown away,
§3.6); the checks refuse any source on them. Find, match and choose are puzzles in the bound book: a match
side or an option may be a dhikr's wording, by source id."""

from __future__ import annotations

import math
from typing import Any

from markupsafe import Markup

from qamra_workbook.pictures import get as library_picture
from qamra_workbook.pictures.islamic_backdrops import GLYPH_PREFIX, prop_svg
from qamra_workbook.puzzles import generate_maze
from qamra_workbook.render import draw
from qamra_workbook.render.islamic_content import (
    Choose,
    CutPaste,
    DrawPage,
    FindObjects,
    Match,
    MazePage,
    Quote,
)
from qamra_workbook.render.pages.islamic_activity import shuffled
from qamra_workbook.render.pages.islamic_common import (
    choice,
    chrome,
    claim,
    context_of,
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

LETTERS = ("أ", "ب", "ج", "د", "هـ", "و")
BOARD = (186.0, 120.0)
MAZE_SIZES = {"small": (4, 4), "medium": (5, 5), "large": (6, 6)}


def word_of(picture_id: str) -> str:
    if picture_id.startswith(GLYPH_PREFIX):
        return picture_id[len(GLYPH_PREFIX) :]
    return library_picture(picture_id).word_ar


# ---- find the things --------------------------------------------------------------------------------------


def board(ctx: PageContext, targets: list[str], others: list[str]) -> tuple[Markup, Markup, list[str]]:
    """The things scattered on a board (seeded: the same page draws the same board), and the answer rings."""
    rng = ctx.rng("board")
    items = [(p, True) for p in targets] + [(p, False) for p in others]
    rng.shuffle(items)
    count = len(items)
    w, h = BOARD
    cols = max(2, math.ceil(math.sqrt(count * w / h)))
    rows = math.ceil(count / cols)
    cw, ch = w / cols, h / rows
    size = min(cw, ch) * 0.78
    body, rings = [draw.el("rect", x=0, y=0, width=w, height=h, rx=6, fill="#FFF9EC")], []
    for i, (pid, target) in enumerate(items):
        col, row = i % cols, i // cols
        k = size * rng.uniform(0.86, 1.04)
        x = (col + 0.5) * cw - k / 2 + rng.uniform(-0.12, 0.12) * cw
        y = (row + 0.5) * ch - k / 2 + rng.uniform(-0.1, 0.1) * ch
        turn = rng.uniform(-14, 14)
        body.append(
            f'<g transform="rotate({turn:.1f} {x + k / 2:.2f} {y + k / 2:.2f})">'
            f"{prop_svg(pid, x, y, k, i)}</g>"
        )
        if target:
            rings.append(
                f'<ellipse class="answer-ring" cx="{x + k / 2:.2f}" cy="{y + k / 2:.2f}" '
                f'rx="{k * 0.62:.2f}" ry="{k * 0.58:.2f}"/>'
            )
    svg = Markup(  # nosec B704 (library art at computed places)
        f'<svg class="fo-svg" viewBox="0 0 {w:g} {h:g}" aria-hidden="true">{"".join(body)}</svg>'
    )
    ring_svg = Markup(  # nosec B704 (numbers only)
        f'<svg class="fo-rings" viewBox="0 0 {w:g} {h:g}" aria-hidden="true">{"".join(rings)}</svg>'
    )
    return svg, ring_svg, [p for p, _ in items]


@islamic_page("islamic-find-objects")
def find_objects(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, FindObjects)
    problems = picture_problems([t.pic for t in page.find] + page.others, "find")
    targets = [t.pic for t in page.find]
    if len(set(targets)) != len(targets) or set(targets) & set(page.others):
        problems.append("every thing on the board appears once (the things to find are not among the others)")
    svg = rings = Markup("")
    if not problems:
        svg, rings, _ = board(ctx, targets, page.others)
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "board": svg,
        "rings": rings,
        "finds": [
            {"word": ctx.text(t.word), "art": picture(t.pic, css_class="fo-pic", i=i) if not problems else ""}
            for i, t in enumerate(page.find)
        ],
        "closing": claim(ctx, page.closing, problems) if page.closing else None,
        "refs": references(ctx, source_ids(page.closing) if page.closing else []),
    }
    return Built(data, [ctx.text(t.word) for t in page.find], problems)


# ---- match ------------------------------------------------------------------------------------------------


def side(ctx: PageContext, value: Any, problems: list[str], i: int) -> dict[str, Any]:
    out: dict[str, Any] = {"pic": "", "text": "", "sacred": None}
    if value.pic:
        found = picture_problems([value.pic], "match")
        problems += found
        out["pic"] = picture(value.pic, css_class="mt-pic", i=i) if not found else ""
    if value.t:
        out["text"] = rich(ctx, value.t, problems)
    if value.source:
        out["sacred"] = sacred(ctx, Quote(source=value.source, span=value.span), "choice", problems)
    return out


def _describe(ctx: PageContext, value: Any) -> str:
    """A side in words, for the answer key: its text, its source's title, or its picture's word."""
    if value.t:
        return ctx.text(value.t)
    if value.source:
        src = context_of(ctx).resolver.register.by_id.get(value.source)
        return src.title_ar if src else value.source
    return word_of(value.pic)


@islamic_page("islamic-match")
def match(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Match)
    problems: list[str] = []
    order = shuffled(len(page.pairs), ctx.rng("match"))
    rights = [{"n": ctx.num(i + 1), **side(ctx, pair.a, problems, i)} for i, pair in enumerate(page.pairs)]
    lefts = [
        {"n": LETTERS[j], "k": k, **side(ctx, page.pairs[k].b, problems, k + 3)} for j, k in enumerate(order)
    ]
    ids = [s for pair in page.pairs for s in pair.sources]
    ids += [x.source for pair in page.pairs for x in (pair.a, pair.b) if x.source]
    ids += [s for pair in page.pairs for x in (pair.a, pair.b) for s in source_ids(x.t)]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "rows": [{"a": rights[i], "b": lefts[i]} for i in range(len(page.pairs))],
        "refs": references(ctx, ids),
    }
    letter_of = {left["k"]: left["n"] for left in lefts}
    answer = [
        f"{rights[i]['n']} ← {letter_of[i]}: {_describe(ctx, p.a)} — {_describe(ctx, p.b)}"
        for i, p in enumerate(page.pairs)
    ]
    return Built(data, answer, problems)


# ---- choose -----------------------------------------------------------------------------------------------


@islamic_page("islamic-choose")
def choose(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Choose)
    problems = scene_problems(page.scene) if page.scene else []
    questions: list[dict[str, Any]] = []
    for i, q in enumerate(page.questions, start=1):
        if sum(c.ok for c in q.choices) != 1:
            problems.append(f"question {i} needs exactly one right answer")
        found = picture_problems([q.pic], f"question {i}") if q.pic else []
        problems += found
        questions.append(
            {
                "n": ctx.num(i),
                "text": rich(ctx, q.text, problems),
                "pic": picture(q.pic, css_class="ch-pic") if q.pic and not found else "",
                "choices": [choice(ctx, c, problems) for c in q.choices],
            }
        )
    ids = [s for q in page.questions for s in [*q.sources, *(x for c in q.choices for x in source_ids(c))]]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "scene": scene(ctx, page.scene, "ch-art") if page.scene and not scene_problems(page.scene) else "",
        "questions": questions,
        "refs": references(ctx, ids),
    }
    answer = [f"{q['n']}: " + "، ".join(str(c["text"]) for c in q["choices"] if c["ok"]) for q in questions]
    return Built(data, answer, problems)


# ---- maze -------------------------------------------------------------------------------------------------


def runner_art(ctx: PageContext, runner: str, x: float, y_feet: float, height: float, i: int = 0) -> str:
    if runner == "reader":
        return context_of(ctx).kit.figure("reader", x, y_feet, height)
    size = height * 0.62
    return prop_svg(runner, x - size / 2, y_feet - size, size, i)


@islamic_page("islamic-maze")
def maze(ctx: PageContext) -> Built:
    """In at the top right (the runner stands above the entrance), out at the bottom left into the goal; the
    pictures to collect lie on the one right path."""
    page = page_of(ctx)
    assert isinstance(page, MazePage)
    problems = picture_problems([page.goal, *page.collect], "maze")
    if page.runner != "reader":
        problems += picture_problems([page.runner], "runner")
    cols, rows = MAZE_SIZES[page.size]
    m = generate_maze(cols, rows, ctx.page.seed, start_side="top", end_side="left")
    problems += m.problems()
    w, h, figure = 186.0, 168.0, 44.0
    goal_room, head_room = 40.0, figure + 4
    cell = min((w - goal_room - 6) / cols, (h - head_room - 4) / rows)
    mw, mh = cell * cols, cell * rows
    x0, y0 = w - 5 - mw, h - mh - 4
    color = ctx.style.color
    walls = " ".join(
        draw.d_path(("M", (x0 + a[0] * cell, y0 + a[1] * cell)), ("L", (x0 + b[0] * cell, y0 + b[1] * cell)))
        for a, b in m.walls()
    )
    path = m.solve() or []
    centers = [(x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell) for c, r in path]
    entry_x = x0 + (m.start[0] + 0.5) * cell
    exit_y = y0 + (m.end[1] + 0.5) * cell
    body = [
        draw.el("rect", x=x0 - 4, y=y0 - 4, width=mw + 8, height=mh + 8, rx=7, fill=ctx.style.tint),
        draw.el("rect", x=x0, y=y0, width=mw, height=mh, rx=2, fill="#FFFFFF"),
        draw.path(walls, stroke=ctx.style.deep, width=3.6),
        draw.path(walls, stroke=color, width=1.4),
    ]
    if not problems:
        body.append(prop_svg(page.goal, x0 - 39, exit_y - 18, 34))
        spots = [
            centers[round((k + 1) * len(centers) / (len(page.collect) + 1))] for k in range(len(page.collect))
        ]
        size = cell * 0.62
        for k, (pid, (cx, cy)) in enumerate(zip(page.collect, spots, strict=True)):
            body.append(prop_svg(pid, cx - size / 2, cy - size / 2, size, k))
        body.append(runner_art(ctx, page.runner, entry_x, y0 - 1.5, figure))
    body += [draw.start_dot((entry_x, y0 + 6), 3.0), draw.arrow((entry_x, y0 + 12), 90, 4.0, "#2FA36B")]
    route = [(entry_x, y0 - 3), *centers, (x0 - 3, exit_y)]
    solution = draw.path(
        draw.polyline(route), stroke="#E0483A", width=1.8, stroke_dasharray="3.2 2.6", opacity=0.9
    )
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "svg": draw.svg(w, h, "".join(body), "mz-svg"),
        "svg_solved": draw.svg(w, h, "".join(body) + solution, "mz-svg"),
        "goal_word": ctx.text(page.goal_word),
    }
    goal = ctx.text(page.goal_word) or word_of(page.goal)
    return Built(data, [f"الهدف: {goal}. الطريق الوحيد إليه مرسوم بالخط الأحمر."], problems)


# ---- draw -------------------------------------------------------------------------------------------------


@islamic_page("islamic-draw")
def draw_page(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, DrawPage)
    problems = picture_problems(page.hints, "hints")
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "prompt": rich(ctx, page.prompt, problems),
        "boxes": [ctx.text(b) for b in page.boxes] or [""],
        "hints": [picture(h, css_class="dr-pic", i=i) for i, h in enumerate(page.hints)]
        if not problems
        else [],
        "lines": list(range(page.lines)),
        "labels": {"hints": "أَفْكَارٌ لِلرَّسْمِ"},
    }
    return Built(data, None, problems)


# ---- cut and paste ----------------------------------------------------------------------------------------


def piece(ctx: PageContext, value: Any, i: int) -> dict[str, Any]:
    return {
        "pic": picture(value.pic, css_class="cp-pic", i=i) if value.pic else "",
        "text": ctx.text(value.t),
    }


@islamic_page("islamic-cut-paste")
def cut_paste(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, CutPaste)
    problems = picture_problems([p.pic for p in page.pieces if p.pic], "pieces")
    order = shuffled(len(page.pieces), ctx.rng("cut"))
    slots = [ctx.text(s) for s in page.slots] or [ctx.num(i) for i in range(1, len(page.pieces) + 1)]
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "slots": slots,
        "pieces": [piece(ctx, page.pieces[k], k) for k in order] if not problems else [],
        "count": len(page.pieces),
        "cols": 2 if len(page.pieces) == 4 else 3,
        "labels": {"paste": "أُلْصِقُ هُنَا", "cut": "أَقُصُّ عَلَى الْخَطِّ"},
    }
    answer = [f"{slots[i]}: {ctx.text(p.t) or word_of(p.pic)}" for i, p in enumerate(page.pieces)]
    return Built(data, answer, problems)
