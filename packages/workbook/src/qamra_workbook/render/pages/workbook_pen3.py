"""«دوسية التأسيس» Volume 3 pen skills and tracing: the joining strokes between letters on the line, a long
path with sharp turns, and the shared tracing and writing pages of two or three letters."""

from __future__ import annotations

import math

from qamra_workbook.geometry import Stroke
from qamra_workbook.render import draw
from qamra_workbook.render.foundation_text import letters_head
from qamra_workbook.render.pages.letters import tracing_row
from qamra_workbook.render.pages.workbook_arabic import big_track, row_svg
from qamra_workbook.render.pages.workbook_arabic2 import alone_row
from qamra_workbook.render.pages.workbook_common import (
    W,
    card,
    fit_lines,
    glyph,
    pic,
    picture_id,
    shape_of,
    start_marks,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_pen import traced
from qamra_workbook.render.registry import Built, PageContext, page_type

# what joining letters on the line feels like, one pattern per row (the letter whose join it is): hills (ـبـ),
# bowls (ـنـ), small teeth (ـسـ), loops (ـمـ) and stems (ـلـ)
JOINS = ("hills", "bowls", "teeth", "loops", "stems")


def join_path(kind: str, x0: float, x1: float, base: float, cap: float) -> str:
    """One continuous stroke from `x0` (its start, on the right) to `x1` along the writing line at `base`, the
    way joins run between letters: it keeps to the line, then rises, dips, loops or climbs and comes back.
    Every curve is smooth (no sharp turns), so the tracing dots keep an even distance."""
    span = x0 - x1
    if kind == "loops":  # a prolate cycloid: the pen moves left while turning, so each turn closes a loop
        k, amp = max(1, round(span / 24)), cap * 0.48
        a = span / (2 * math.pi * k)
        centre, steps = base - amp * 0.85, 40 * k
        pts = [
            (x0 - (a * t + amp * math.sin(t)), centre + amp * 0.85 * math.cos(t))
            for t in (2 * math.pi * k * i / steps for i in range(steps + 1))
        ]
        return draw.polyline(pts)
    # (width of one bump, bumps in a group, flat join after a group, height, +1 below the line / -1 above it)
    bump, count, join, height, side = {
        "hills": (15.0, 1, 2.0, cap * 0.72, -1),
        "bowls": (15.0, 1, 2.0, cap * 0.55, 1),
        "teeth": (8.0, 3, 6.0, cap * 0.5, -1),
        "stems": (9.0, 1, 3.0, cap * 0.95, -1),
    }[kind]
    group = bump * count + join
    groups = max(1, round(span / group))
    scale = span / (groups * group)  # stretch the pattern so it ends exactly at x1
    pts = [(x0, base)]
    x = x0
    for _ in range(groups):
        for _ in range(count):
            for i in range(1, 25):
                u = i / 24
                pts.append((x - u * bump * scale, base + side * height * math.sin(math.pi * u) ** 2))
            x -= bump * scale
        x -= join * scale
        pts.append((x, base))
    return draw.polyline(pts)


@page_type("join-strokes")
def join_strokes(ctx: PageContext) -> Built:
    """Five rows, one joining pattern each, dotted along the whole line to trace from the right."""
    body = []
    cap = 14.0
    for i, kind in enumerate(JOINS):
        y = i * 41
        body.append(card(0, y + 1, W, 38, r=7))
        base = y + 12 + cap
        for color, yy in (("#9BB7E0", base - cap), ("#E27D63", base)):
            body.append(
                draw.el(
                    "path", d=draw.d_path(("M", (6, yy)), ("L", (W - 6, yy))), stroke=color, stroke_width=0.5
                )
            )
        body.append(traced(Stroke(join_path(kind, W - 12, 14, base, cap)), spacing=2.8, r=0.8, start=2.6))
    return Built({"svg": svg(body)}, None, [])


@page_type("complex-path")
def complex_path(ctx: PageContext) -> Built:
    """A long road with sharp corners and bends, from the cat to the ball."""
    words = [str(w) for w in ctx.page.params.get("words", ["cat", "ball"])]
    start, end = picture_id(words[0]), picture_id(words[-1])
    d = (
        "M154 30 L154 70 L110 70 L110 40 L70 40 L70 96 C70 116 100 110 120 116 "
        "C150 124 146 156 120 156 L60 156 "
        "L60 126 L30 126 L30 184 L100 184"
    )
    road = Stroke(d)
    body = [card(0, 0, W, 204, r=8, fill="#F4F9FD", stroke="none")]
    body.append(draw.path(road.d, stroke="#E5CD9E", width=12))
    body.append(draw.path(road.d, stroke="#FFFFFF", width=9.4))
    body.append(traced(road, spacing=5.0, r=0.95, start=2.8))
    body.append(pic(start, 134, 2, 40))
    body.append(pic(end, 104, 168, 34))
    return Built({"svg": svg(body)}, None, [])


@page_type("letters-trace")
def letters_trace(ctx: PageContext) -> Built:
    """Two or three letters share a page: a big track for each, then a row of each, as big as fits."""
    params = ctx.page.params
    chars = [str(c) for c in params.get("letters", ["ف", "ق"])]
    body = []
    n = len(chars)
    big_h = 88.0 if n == 2 else 70.0
    body.append(card(0, 0, W, big_h, r=7))
    tw = (W - 6) / n
    for k, char in enumerate(chars):
        shape = shape_of(char)
        body.append(big_track(shape, W - (k + 1) * tw + 2, 2, tw - 4, big_h - 4, ctx.num, ctx.style.color))
        if k:
            body.append(
                draw.path(
                    draw.d_path(("M", (W - k * tw, 8)), ("L", (W - k * tw, big_h - 8))),
                    stroke="#EFE5D2",
                    width=0.5,
                )
            )
    cap = 18.0 if n == 2 else 19.0
    while True:  # the biggest rows that keep the page inside its work area
        y, rows = big_h + 4, []
        for char in chars:
            row, height = row_svg(
                tracing_row(shape_of(char), width=W - 10, cap=cap, number=ctx.num), 5, y + 1.5
            )
            rows.append(card(0, y, W, height + 3, r=6) + row)
            y += height + 5
        if y <= 206 or cap <= 11:
            break
        cap -= 0.5
    body += rows
    problems = [] if y <= 208 else [f"the tracing rows need {y:.0f} mm"]
    return Built({"svg": svg(body)}, None, problems)


@page_type("letters-write-3")
def letters_write3(ctx: PageContext) -> Built:
    """Two or three letters to write: their shapes (and names) on top, then for each letter a dotted row and a
    row to write alone (two letters), or one row that is dotted first and free after (three)."""
    params = ctx.page.params
    chars = [str(c) for c in params.get("letters", ["ف", "ق"])]
    guided, alone = int(params.get("guided", 1)), int(params.get("independent", 1))
    n = len(chars)
    body = [card(0, 0, W, 36, r=7)]
    cw = (W - 12) / n
    for k, char in enumerate(chars):
        shape = shape_of(char)
        cx = W - 6 - (k + 0.5) * cw
        scale, dx, dy = fit_lines(shape, cx - 15, 2.5, 30, 24)
        body.append(glyph(shape, scale, dx, dy, color=ctx.style.color, width=15))
        body.append(start_marks(shape, scale, dx, dy, 2.0, ctx.num))
        body.append(text(letters_head([char]), cx, 33, 4.2, color=ctx.style.deep))
    cap = 14.0 if n == 2 else 24.0
    while True:  # the biggest rows that keep the page inside its work area
        y, parts = 41.0, []
        for char in chars:
            shape = shape_of(char)
            parts.append(card(W - 30, y - 1, 28, 10, r=5, fill=ctx.style.tint, stroke="none"))
            parts.append(text(letters_head([char]), W - 16, y + 6, 4.2, color=ctx.style.deep))
            if n >= 3:
                row = tracing_row(shape, width=W - 10, cap=cap, count=3, number=ctx.num)
                part, height = row_svg(row, 5, y + 10)
                parts += [card(0, y + 8, W, height + 3, r=6), part]
                y += height + 12
                continue
            for k in range(guided + alone):
                if k < guided:
                    part, height = row_svg(
                        tracing_row(shape, width=W - 10, cap=cap, number=ctx.num), 5, y + 10
                    )
                else:
                    part, height = alone_row(ctx, char, cap, y + 10)
                parts += [
                    card(0, y + 8, W, height + 3, r=6, fill="#FFFFFF" if k < guided else "#FFFDF6"),
                    part,
                ]
                y += height + 8
            y += 2
        if y <= 206 or cap <= 10:
            break
        cap -= 0.5
    body += parts
    problems = [] if y <= 210 else [f"the writing rows need {y:.0f} mm (max 204)"]
    return Built({"svg": svg(body)}, None, problems)
