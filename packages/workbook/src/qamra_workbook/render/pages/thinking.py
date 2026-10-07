"""Thinking pages: odd one out, patterns, smart coloring, spot the difference."""

from __future__ import annotations

from typing import cast, get_args

from markupsafe import Markup

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.puzzles import (
    Box,
    ColoringScene,
    Shape,
    generate_coloring,
    generate_odd_rows,
    generate_pattern_rows,
    generate_spot,
)
from qamra_workbook.puzzles.coloring import SHAPE_AR, ShapeKind
from qamra_workbook.puzzles.spot import Scene
from qamra_workbook.render import draw
from qamra_workbook.render.registry import Built, PageContext, page_type

SHAPE_COLORS = {"circle": "#EE8A6E", "triangle": "#5E86D6", "square": "#7DB46C", "heart": "#E97A98"}


def ring(kind: str = "answer") -> Markup:
    """A hand-drawn circle around an answer: pencil gray on solved examples, red in the answer key."""
    color = "#3D4262" if kind == "example" else "#E0483A"
    return Markup(  # nosec B704 (static art)
        f'<svg class="ring {kind}" viewBox="0 0 100 100" aria-hidden="true"><path d="M52 5 C80 4 97 22 96 50 '
        'C95 79 73 97 47 96 C19 95 3 76 4 49 C5 23 25 6 57 9" fill="none" '
        f'stroke="{color}" stroke-width="4.2" stroke-linecap="round"/></svg>'
    )


def _word(picture_id: str) -> str:
    return strip_tashkeel(picture(picture_id).word_ar)


@page_type("odd-one-out")
def odd_one_out(ctx: PageContext) -> Built:
    rules = list(ctx.page.params.get("rules", ["same", "same", "category"]))
    sizes = list(ctx.page.params.get("sizes", [4] * len(rules)))
    groups = ctx.page.params.get("groups")
    rows = generate_odd_rows(ctx.page.seed, rules, sizes, tuple(groups) if groups else None)
    data = [
        {
            "pics": [ctx.pic(i) for i in row.items],
            "odd": row.odd,
            "example": row.example,
            "n": k,
            "hint": row.hint,
        }
        for k, row in enumerate(rows)
    ]
    answer = [f"الصف {ctx.num(k)}: {row.answer}" for k, row in enumerate(rows) if not row.example]
    return Built({"rows": data, "ring": ring}, answer, [p for row in rows for p in row.problems()])


def shape_kind(name: str) -> ShapeKind:
    if name not in get_args(ShapeKind):
        raise ValueError(f"unknown shape {name!r}")
    return cast(ShapeKind, name)


def _element(ctx: PageContext, item: str) -> Markup:
    """A pattern element: `shape:<kind>` draws a flat shape, anything else is a library picture."""
    if item.startswith("shape:"):
        kind = shape_kind(item.removeprefix("shape:"))
        body = draw.shape(Shape(kind, 50, 50, 78, 78), fill=SHAPE_COLORS.get(kind, "#F7C84A"), width=5)
        return Markup(f'<svg class="pic" viewBox="0 0 100 100" aria-hidden="true">{body}</svg>')  # nosec B704
    return ctx.pic(item)


def _element_name(item: str) -> str:
    names = {"circle": "دائرة", "triangle": "مثلث", "square": "مربع", "heart": "قلب"}
    return names[item.removeprefix("shape:")] if item.startswith("shape:") else _word(item)


@page_type("pattern-complete")
def pattern_complete(ctx: PageContext) -> Built:
    units = list(ctx.page.params.get("units", ["AB", "AB", "ABB"]))
    shown = list(ctx.page.params.get("shown", [4, 5, 6]))
    rows = generate_pattern_rows(ctx.page.seed, units, shown)
    data = [
        {
            "shown": [_element(ctx, i) for i in row.shown],
            "answers": [_element(ctx, i) for i in row.answer],
            "example": row.example,
            "n": k,
            "slots": len(row.shown) + row.blanks,
        }
        for k, row in enumerate(rows)
    ]
    answer = [
        f"الصف {ctx.num(k)}: {' ثم '.join(_element_name(i) for i in row.answer)}"
        for k, row in enumerate(rows)
        if not row.example
    ]
    return Built({"rows": data}, answer, [p for row in rows for p in row.problems()])


def coloring_svg(scene: ColoringScene, fill: str | None = None) -> Markup:
    """The shapes scene in line art; `fill` colors the rule's shapes (the answer key)."""
    w, h, ground = scene.w, scene.h, scene.ground
    line = draw.d_path(("M", (4, ground)), ("L", (w - 4, ground)))
    body = [draw.path(line, stroke="#B9A77F", width=1, stroke_dasharray="0.1 3.2")]
    for thing in scene.things:
        body += [draw.path(d, stroke="#2B2E4A", width=0.85) for d in thing.lines]
        for s in thing.shapes:
            hit = s.kind == scene.target
            body.append(draw.shape(s, fill=fill if hit and fill else "#FFFFFF", width=1.05))
    return draw.svg(w, h, "".join(body), "coloring-scene")


@page_type("smart-coloring")
def smart_coloring(ctx: PageContext) -> Built:
    target = shape_kind(str(ctx.page.params.get("target", "circle")))
    color = str(ctx.page.params.get("color", "#EE8A6E"))
    scene = generate_coloring(150.0, 128.0, ctx.page.seed, target)  # drawn about 1.2× on the page
    check = draw.path("M6 23 L9 26 L15 19.5", stroke="#2FA36B", width=1.6)
    cross = (
        '<path d="M{0} 20 L{1} 26 M{1} 20 L{0} 26" fill="none" stroke="#B8B2A6" stroke-width="1.3" '
        'stroke-linecap="round"/>'
    )
    model = [
        draw.shape(Shape(target, 10.5, 9.5, 15, 15), fill=color, width=0.9),
        check,
        draw.shape(Shape("triangle", 33, 9.5, 14, 13), width=0.9),
        cross.format(30, 36),
        draw.shape(Shape("square", 55, 9.5, 12.5, 12.5), width=0.9),
        cross.format(52, 58),
    ]
    data = {
        "scene": coloring_svg(scene),
        "scene_solved": coloring_svg(scene, color),
        "model": draw.svg(64, 28, "".join(model), "model-shapes"),
        "color": color,
        "target_ar": SHAPE_AR[target],
        "count": scene.count,
    }
    answer = [f"عدد {SHAPE_AR[target]}: {ctx.num(scene.count)}"]
    return Built(data, answer, scene.problems())


def _grass(w: float, h: float, horizon: float) -> str:
    """Rolling grass from the horizon down, with the scene's rounded bottom corners."""
    return (
        draw.d_path(
            ("M", (0, horizon + 4)),
            ("C", (w * 0.25, horizon - 5, w * 0.55, horizon + 6, w, horizon - 2)),
            ("L", (w, h - 4)),
            ("C", (w, h - 1.8, w - 1.8, h, w - 4, h)),
            ("L", (4, h)),
            ("C", (1.8, h, 0, h - 1.8, 0, h - 4)),
        )
        + " Z"
    )


def scene_svg(scene: Scene, rings: list[Box] | None = None) -> Markup:
    """A composed picture-library scene (sky, grass, objects), with red answer rings for the answer key."""
    w, h = scene.w, scene.h
    body = [
        draw.el("rect", x=0, y=0, width=w, height=h, rx=4, fill="#EAF4FC"),
        draw.el("path", d=_grass(w, h, scene.horizon), fill="#DDEFD6"),
    ]
    for o in scene.objects:
        inner = picture(o.picture).inner("color", o.colors)
        if o.flip:
            inner = f'<g transform="translate(100 0) scale(-1 1)">{inner}</g>'
        b = o.box
        body.append(
            draw.el(
                "svg", inner, x=b.x, y=b.y, width=b.w, height=b.h, viewBox="0 0 100 100", data_object=o.key
            )
        )
    for r in rings or []:
        cx, cy = r.center
        body.append(
            draw.el(
                "ellipse",
                cx=cx,
                cy=cy,
                rx=r.w / 2 + 1,
                ry=r.h / 2 + 1,
                fill="none",
                stroke="#E0483A",
                stroke_width=1.1,
            )
        )
    body.append(
        draw.el("rect", x=0, y=0, width=w, height=h, rx=4, fill="none", stroke="#2B2E4A", stroke_width=0.8)
    )
    return draw.svg(w, h, "".join(body), "scene")


@page_type("spot-difference")
def spot_difference(ctx: PageContext) -> Built:
    count = int(ctx.page.params.get("count", 5))
    puzzle = generate_spot(176.0, 92.0, ctx.page.seed, count)
    data = {
        "a": scene_svg(puzzle.a),
        "b": scene_svg(puzzle.b),
        "b_solved": scene_svg(puzzle.b, [d.region for d in puzzle.differences]),
        "count": count,
    }
    answer = [f"{ctx.num(k)}. {d.text}" for k, d in enumerate(puzzle.differences, start=1)]
    return Built(data, answer, puzzle.problems())
