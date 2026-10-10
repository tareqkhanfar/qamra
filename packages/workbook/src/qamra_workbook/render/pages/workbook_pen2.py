"""«دوسية التأسيس» Volume 2 pen skills (Addendum 5 §3): spirals from the outside in, small shapes between two
lines (getting ready to write on the line), a narrow winding path, and dot-to-dot in alphabet order. Every
stroke has a green start dot and an arrow; rows run right to left."""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable

from qamra_workbook.geometry import Stroke
from qamra_workbook.letters import ALPHABET
from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    arabic_shape,
    card,
    fit_lines,
    glyph,
    pic,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_pen import OUTLINES, traced
from qamra_workbook.render.registry import Built, PageContext, page_type


def spiral(cx: float, cy: float, radius: float, turns: float = 2.5) -> Stroke:
    """An Archimedean spiral from the outside (the start) to the centre, turning clockwise."""
    steps = int(turns * 36)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = 2 * math.pi * turns * t
        r = radius * (1 - t) + 1.2
        pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
    return Stroke(draw.polyline(pts))


@page_type("spiral-lines")
def spiral_lines(ctx: PageContext) -> Built:
    body = []
    radii = (30.0, 30.0, 30.0, 24.0, 24.0, 24.0)
    for k, radius in enumerate(radii):
        row, col = divmod(k, 3)
        cx = W - (col + 0.5) * W / 3
        cy = 40 + row * 108 - (0 if row == 0 else 6)
        body.append(
            card(cx - W / 6 + 2, cy - 48 if row == 0 else cy - 42, W / 3 - 4, 96 if row == 0 else 84, r=7)
        )
        body.append(traced(spiral(cx, cy, radius), spacing=4.4, r=1.15, start=2.6))
    return Built({"svg": svg(body)}, None, [])


BETWEEN: dict[str, Callable[[float, float, float], str]] = {
    "zigzag": lambda x, y, h: draw.polyline(
        [(x, y + h), (x - 5, y), (x - 10, y + h), (x - 15, y), (x - 20, y + h)]
    ),
    "wave": lambda x, y, h: (
        f"M{x} {y + h / 2} Q{x - 5} {y - 2} {x - 10} {y + h / 2} Q{x - 15} {y + h + 2} {x - 20} {y + h / 2}"
    ),
    "loops": lambda x, y, h: (
        f"M{x} {y + h} C{x + 2} {y - 2} {x - 12} {y - 2} {x - 10} {y + h} "
        f"C{x - 8} {y - 2} {x - 22} {y - 2} {x - 20} {y + h}"
    ),
    "hills": lambda x, y, h: (
        f"M{x} {y + h} Q{x - 5} {y - 2} {x - 10} {y + h} Q{x - 15} {y - 2} {x - 20} {y + h}"
    ),
    "teeth": lambda x, y, h: draw.polyline(
        [
            (x, y + h),
            (x, y),
            (x - 6, y),
            (x - 6, y + h),
            (x - 12, y + h),
            (x - 12, y),
            (x - 18, y),
            (x - 18, y + h),
        ]
    ),
}


@page_type("between-lines")
def between_lines(ctx: PageContext) -> Built:
    """Five rows of two lines, 10 mm apart: three dotted models of a small shape, then room to go on alone."""
    body = []
    for i, shape in enumerate(BETWEEN.values()):
        y = i * 41
        body.append(card(0, y + 1, W, 38, r=7))
        top, h = y + 13, 12.0
        for yy, color in ((top, "#9BB7E0"), (top + h, "#E27D63")):
            body.append(
                draw.el(
                    "path", d=draw.d_path(("M", (6, yy)), ("L", (W - 6, yy))), stroke=color, stroke_width=0.5
                )
            )
        for k in range(3):
            x = W - 12 - k * 30
            body.append(traced(Stroke(shape(x, top, h)), spacing=3.2, r=0.9, start=1.9))
        body.append(draw.start_dot((W - 12 - 3 * 30, top + h), 1.9))
    return Built({"svg": svg(body)}, None, [])


@page_type("narrow-path")
def narrow_path(ctx: PageContext) -> Built:
    """A winding road 9 mm wide with a dotted middle: stay between the edges."""
    words = [str(w) for w in ctx.page.params.get("words", ["cat", "ball"])]
    from qamra_workbook.render.pages.workbook_common import picture_id

    start, end = picture_id(words[0]), picture_id(words[-1])
    d = (
        "M154 34 C154 70 120 60 112 84 C104 108 150 112 148 140 C146 168 100 150 84 168 "
        "C70 184 40 176 40 150 "
        "C40 122 80 126 72 96 C66 74 30 80 30 110 C30 140 44 152 40 182"
    )
    road = Stroke(d)
    body = [card(0, 0, W, 204, r=8, fill="#F4F9FD", stroke="none")]
    body.append(draw.path(road.d, stroke="#E5CD9E", width=11))
    body.append(draw.path(road.d, stroke="#FFFFFF", width=8.6))
    body.append(traced(road, spacing=5.2, r=0.9, start=2.6))
    body.append(pic(start, 132, 2, 40))
    body.append(pic(end, 6, 168, 34))
    return Built({"svg": svg(body)}, None, [])


@page_type("letter-dot-to-dot")
def letter_dot_to_dot(ctx: PageContext) -> Built:
    """Dot-to-dot in alphabet order (أ … to the letter in `to`) around an outline: the fish."""
    to = str(ctx.page.params.get("to", "ش"))
    letters = [c for c in ALPHABET if len(c) == 1 and c in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"]
    count = letters.index("ا" if to in "أا" else to) + 1
    outline = Stroke(OUTLINES["fish"])
    points = [outline.at(i / count)[0] for i in range(count)]
    body = [card(0, 0, W, 204, r=8)]
    body.append(
        draw.path(draw.polyline([*points, points[0]]), stroke="#E0483A", width=1.1, class_="key-line")
    )
    for i, (x, y) in enumerate(points):
        dx, dy = x - 93, y - 108
        norm = math.hypot(dx, dy) or 1
        lx, ly = x + dx / norm * 9, y + dy / norm * 9
        body.append(draw.start_dot((x, y), 2.4) if i == 0 else draw.el("circle", cx=x, cy=y, r=1.6, fill=INK))
        shape = arabic_shape("أ" if i == 0 else letters[i])
        body.append(glyph(shape, *fit_lines(shape, lx - 5, ly - 5, 10, 10), color=ctx.style.deep, width=14))
    gaps = [math.dist(a, b) for a, b in itertools.pairwise(points)]
    problems = [] if min(gaps) >= 8 else [f"two dots are only {min(gaps):.1f} mm apart"]
    return Built({"svg": svg(body)}, [f"الصورة: سمكة، الحروف من الألف إلى {to}"], problems)


SHAPE_AR4 = {"circle": "دائِرَة", "square": "مُرَبَّع", "triangle": "مُثَلَّث", "rectangle": "مُسْتَطيل"}
SHAPE_COLORS4 = {"circle": "#EE8A6E", "square": "#7DB46C", "triangle": "#5E86D6", "rectangle": "#F2B33D"}


@page_type("shapes-four")
def shapes_four(ctx: PageContext) -> Built:
    """The circle, square, triangle and rectangle: a coloured model with its name, then three to trace and
    colour the same (a rectangle is drawn wider than it is tall)."""
    from qamra_workbook.render.pages.workbook_pen import shape_stroke

    kinds = [str(k) for k in ctx.page.params.get("shapes", list(SHAPE_AR4))]
    pitch = 204 / len(kinds)
    body = []
    for i, kind in enumerate(kinds):
        y = i * pitch
        color = SHAPE_COLORS4.get(kind, "#F7C84A")
        body.append(card(0, y + 1, W, pitch - 5, r=7))
        body.append(card(W - 36, y + 5, 30, pitch - 13, r=5, fill=ctx.style.tint, stroke="none"))
        model = shape_stroke(kind, W - 21, y + (pitch - 18) / 2 + 3, 14)
        body.append(draw.path(model.d, stroke=INK, width=1.4, fill=color))
        body.append(text(SHAPE_AR4.get(kind, kind), W - 21, y + pitch - 13, 4.8, color=ctx.style.deep))
        wide = 1.5 if kind == "rectangle" else 1.0
        x = W - 44
        for size in (28.0, 23.0, 18.0) if kind == "rectangle" else (34.0, 28.0, 22.0):
            x -= size * wide / 2 + 6
            body.append(
                traced(shape_stroke(kind, x, y + (pitch - 4) / 2, size), spacing=4.2, r=1.1, start=2.3)
            )
            x -= size * wide / 2 + 4
    return Built({"svg": svg(body)}, ["، ".join(SHAPE_AR4.get(k, k) for k in kinds)], [])
