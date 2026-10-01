"""«دوسية التأسيس» pen-skill pages (Addendum 5 §3): lines on dotted guides from a start picture to an end
picture (straight → diagonal → zigzag → curves → loops → the strokes letters are made of), tracing a road,
dot-to-dot, shapes and coloring. Every stroke has a green start dot and an arrow; Arabic pages move right to
left."""

from __future__ import annotations

import itertools
import math

from qamra_workbook.geometry import Stroke
from qamra_workbook.letters import ARABIC
from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_common import INK, W, card, pic, picture_id, picture_of, svg, text
from qamra_workbook.render.registry import Built, PageContext, page_type

PAIRS = (
    ("bee", "flower"),
    ("rabbit", "carrot"),
    ("bird", "nest"),
    ("car", "house"),
    ("cat", "ball"),
    ("butterfly", "rose"),
)


def traced(
    stroke: Stroke, *, spacing: float = 4.6, r: float = 1.15, start: float = 2.6, example: bool = False
) -> str:
    """A stroke in tracing dots with its green start dot and an arrow a little way along."""
    out = [draw.dotted(stroke, spacing=spacing, r=r)]
    if example:
        out.append(draw.path(stroke.d, stroke="#3D4262", width=1.6))
    point, angle = stroke.at(min(0.5, start * 3.4 / max(stroke.length, 1e-6)))
    out.append(draw.arrow(point, angle, start * 1.2))
    out.append(draw.start_dot(stroke.start, start))
    return "".join(out)


def _row_path(line: str, x0: float, x1: float, y: float, amp: float) -> Stroke:
    """A path from x0 (the start, on the right) to x1 along the row at height y."""
    n = draw.n
    span = x0 - x1
    if line == "zigzag":
        k = 8
        pts = [(x0 - span * i / k, y + (amp if i % 2 else -amp)) for i in range(k + 1)]
        pts[0], pts[-1] = (x0, y), (x1, y)
        return Stroke(draw.polyline(pts))
    if line == "curve":
        k = 4
        d = f"M{n(x0)} {n(y)}"
        for i in range(k):
            a, b = x0 - span * (i + 0.5) / k, x0 - span * (i + 1) / k
            d += f" Q{n(a)} {n(y - amp * 1.6 if i % 2 == 0 else y + amp * 1.6)} {n(b)} {n(y)}"
        return Stroke(d)
    if line == "loops":
        # a prolate cycloid: the pen moves left while turning, so each turn crosses itself into a loop
        k, b = 4, amp
        a = span / (2 * math.pi * k)
        steps = 36 * k
        pts = [
            (x0 - (a * t + b * math.sin(t)), y + b * 0.8 * math.cos(t))
            for t in (2 * math.pi * k * i / steps for i in range(steps + 1))
        ]
        return Stroke(draw.polyline(pts))
    return Stroke(draw.polyline([(x0, y), (x1, y)]))


def _letter_strokes() -> list[Stroke]:
    """The bodies letters are made of: the ب bowl, the ر hook, the ن bowl, the د corner."""
    return [ARABIC[(c, "isolated")].strokes[0] for c in ("ب", "ر", "ن", "د")]


@page_type("pen-lines")
def pen_lines(ctx: PageContext) -> Built:
    line = str(ctx.page.params.get("line", "horizontal"))
    body: list[str] = []
    if line == "vertical":
        cols = 5
        for i, (a, b) in enumerate(PAIRS[:cols]):
            cx = W - (i + 0.5) * W / cols
            body.append(pic(a, cx - 12, 0, 24))
            body.append(pic(b, cx - 12, 180, 24))
            body.append(traced(Stroke(draw.polyline([(cx, 32), (cx, 174)]))))
    elif line == "diagonal":
        for row in range(4):
            y = row * 51
            body.append(card(0, y + 1, W, 47, r=7))
            for k in range(6):
                x = W - 16 - k * 29
                top, bottom = (
                    ((x, y + 9), (x - 18, y + 41)) if row % 2 == 0 else ((x - 18, y + 9), (x, y + 41))
                )
                body.append(traced(Stroke(draw.polyline([top, bottom])), start=2.2))
    elif line == "letter-strokes":
        shapes = _letter_strokes()
        for row, stroke in enumerate(shapes):
            y = row * 51
            body.append(card(0, y + 1, W, 47, r=7))
            x0, y0, x1, y1 = (
                min(p[0] for p in stroke.polyline),
                min(p[1] for p in stroke.polyline),
                max(p[0] for p in stroke.polyline),
                max(p[1] for p in stroke.polyline),
            )
            scale = min(34 / (y1 - y0), 38 / (x1 - x0))
            for k in range(4):
                right = W - 8 - k * 45
                moved = stroke.scaled(scale, right - x1 * scale, y + 7 - y0 * scale)
                body.append(traced(moved, spacing=3.8, r=1.05, start=2.1))
    else:
        amp = {"zigzag": 8.0, "curve": 6.0, "loops": 11.0}.get(line, 0.0)
        for row, (a, b) in enumerate(PAIRS[:5]):
            y = row * 41
            body.append(card(0, y + 1, W, 38, r=7))
            body.append(pic(a, W - 30, y + 7, 26))
            body.append(pic(b, 4, y + 7, 26))
            body.append(
                traced(_row_path(line, W - 36, 34, y + 20, amp), spacing=3.4 if line == "loops" else 4.6)
            )
    return Built({"svg": svg(body)}, None, [])


@page_type("trace-path")
def trace_path(ctx: PageContext) -> Built:
    """A road from the start picture to the end picture, with a dotted middle line to follow."""
    kind = str(ctx.page.params.get("path", "straight"))
    words = [str(w) for w in ctx.page.params.get("words", ["rabbit", "carrot"])]
    start, end = picture_id(words[0]), picture_id(words[-1])
    if kind == "curve":
        d = "M150 40 C150 90 40 60 40 110 C40 150 150 130 146 170 C144 186 110 188 60 186"
    else:
        d = "M150 40 L150 80 L40 80 L40 130 L146 130 L146 180 L64 180"
    road = Stroke(d)
    body = [card(0, 0, W, 204, r=8, fill="#F4F9FD", stroke="none")]
    body.append(draw.path(road.d, stroke="#E5CD9E", width=17))
    body.append(draw.path(road.d, stroke="#F6E7C8", width=14.4))
    body.append(traced(road, spacing=4.6, r=1.3, start=3))
    body.append(pic(start, 128, 0, 42))
    body.append(pic(end, 18, 160, 42))
    return Built({"svg": svg(body)}, None, [])


def star_points(cx: float, cy: float, outer: float, inner: float) -> list[tuple[float, float]]:
    """The 10 corners of a five-pointed star, from the top point, clockwise."""
    return [
        (
            cx + (outer if i % 2 == 0 else inner) * math.cos(math.radians(-90 + 36 * i)),
            cy + (outer if i % 2 == 0 else inner) * math.sin(math.radians(-90 + 36 * i)),
        )
        for i in range(10)
    ]


# closed outlines for longer dot-to-dots, sampled into evenly spaced numbered points
OUTLINES = {
    "fish": "M160 100 C140 60 90 50 60 80 L28 56 L36 100 L28 144 L60 120 C90 150 140 140 160 100",
    "heart": "M93 170 C60 140 30 118 30 84 C30 60 48 46 66 46 C80 46 90 56 93 66 C96 56 106 46 120 46 "
    "C138 46 156 60 156 84 C156 118 126 140 93 170",
}


def dot_points(to: int) -> list[tuple[float, float]]:
    if to == 10:
        return star_points(93, 108, 82, 34)
    outline = Stroke(OUTLINES["fish" if to <= 15 else "heart"])
    return [outline.at(i / to)[0] for i in range(to)]


@page_type("dot-to-dot")
def dot_to_dot(ctx: PageContext) -> Built:
    to = int(ctx.page.params.get("to", 10))
    points = dot_points(to)
    body = [card(0, 0, W, 204, r=8)]
    solved = draw.path(draw.polyline([*points, points[0]]), stroke="#E0483A", width=1.1, class_="key-line")
    body.append(
        draw.path(
            draw.polyline([points[-1], points[0]]), stroke="#B8B2A6", width=0.8, stroke_dasharray="1.5 1.5"
        )
    )
    for i, (x, y) in enumerate(points, start=1):
        cx, cy = 93, 108
        dx, dy = x - cx, y - cy
        norm = math.hypot(dx, dy) or 1
        lx, ly = x + dx / norm * 7, y + dy / norm * 7 + 1.8
        if i == 1:
            body.append(draw.start_dot((x, y), 2.4))
        else:
            body.append(draw.el("circle", cx=x, cy=y, r=1.6, fill=INK))
        body.append(text(ctx.num(i), lx, ly, 5.2, cls="wb-num", color=ctx.style.deep))
    body.append(solved)
    gaps = [math.dist(a, b) for a, b in itertools.pairwise(points)]
    problems = [] if min(gaps) >= 8 else [f"two numbered dots are only {min(gaps):.1f} mm apart"]
    answer = [
        f"الصورة: {'نجمة' if to == 10 else 'سمكة' if to <= 15 else 'قلب'}، "
        f"النقاط من {ctx.num(1)} إلى {ctx.num(to)}"
    ]
    return Built({"svg": svg(body)}, answer, problems)


SHAPE_AR = {"circle": "دائِرَة", "square": "مُرَبَّع", "triangle": "مُثَلَّث", "rectangle": "مُسْتَطيل"}


def shape_stroke(kind: str, cx: float, cy: float, s: float) -> Stroke:
    """A shape to trace, starting at its top (the circle goes round to the left, as Arabic letters loop)."""
    h = s / 2
    if kind == "circle":
        k = 0.5523 * h
        return Stroke(
            f"M{cx} {cy - h} C{cx - k} {cy - h} {cx - h} {cy - k} {cx - h} {cy} "
            f"C{cx - h} {cy + k} {cx - k} {cy + h} {cx} {cy + h} "
            f"C{cx + k} {cy + h} {cx + h} {cy + k} {cx + h} {cy} "
            f"C{cx + h} {cy - k} {cx + k} {cy - h} "
            f"{cx} {cy - h}"
        )
    if kind == "triangle":
        return Stroke(draw.polyline([(cx, cy - h), (cx - h, cy + h), (cx + h, cy + h), (cx, cy - h)]))
    w = h * 1.5 if kind == "rectangle" else h
    return Stroke(
        draw.polyline(
            [(cx - w, cy - h), (cx - w, cy + h), (cx + w, cy + h), (cx + w, cy - h), (cx - w, cy - h)]
        )
    )


@page_type("shapes")
def shapes(ctx: PageContext) -> Built:
    kinds = [str(k) for k in ctx.page.params.get("shapes", ["circle", "square", "triangle"])]
    pitch = 204 / len(kinds)
    body = []
    for i, kind in enumerate(kinds):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 5, r=7))
        body.append(card(W - 34, y + 6, 28, pitch - 15, r=5, fill=ctx.style.tint, stroke="none"))
        body.append(text(SHAPE_AR.get(kind, kind), W - 20, y + pitch - 14, 4.8, color=ctx.style.deep))
        model = shape_stroke(kind, W - 20, y + (pitch - 18) / 2 + 4, 16)
        body.append(draw.path(model.d, stroke=ctx.style.color, width=2.2, fill=ctx.style.tint))
        for k, size in enumerate((40.0, 32.0, 24.0)):
            cx = W - 62 - k * 50 + (40 - size) / 2
            body.append(
                traced(shape_stroke(kind, cx, y + (pitch - 4) / 2, size), spacing=4.2, r=1.1, start=2.3)
            )
    return Built({"svg": svg(body)}, None, [])


# the colors a child learns first, each with things that are that color
COLOR_ROWS = {
    "أحمر": ("#E5604E", ("apple", "strawberry", "tomato")),
    "أزرق": ("#5E86D6", ("raindrop", "fish", "hat")),
    "أصفر": ("#F7C84A", ("sun", "banana", "corn")),
    "أخضر": ("#6FAE5F", ("leaf", "cucumber", "tree")),
}
# the color names as printed under the crayon
COLOR_WORDS = {"أحمر": "أَحْمَر", "أزرق": "أَزْرَق", "أصفر": "أَصْفَر", "أخضر": "أَخْضَر"}
COLOR_WORDS |= {"برتقالي": "بُرْتُقالِيّ", "بنفسجي": "بَنَفْسَجِيّ"}


def crayon(x: float, y: float, color: str) -> str:
    """A crayon (in the color to use), drawn pointing left."""
    body = draw.el(
        "rect", x=x + 8, y=y, width=26, height=10, rx=2.5, fill=color, stroke=INK, stroke_width=0.6
    )
    tip = draw.el(
        "path",
        d=draw.polyline([(x + 8, y), (x, y + 5), (x + 8, y + 10)]) + " Z",
        fill=color,
        stroke=INK,
        stroke_width=0.6,
        stroke_linejoin="round",
    )
    band = draw.el("rect", x=x + 14, y=y, width=4, height=10, fill="#FFFFFF", opacity=0.6)
    return tip + body + band


@page_type("coloring")
def coloring(ctx: PageContext) -> Built:
    params = ctx.page.params
    colors = [str(c) for c in params.get("colors", [])]
    body: list[str] = []
    if colors:
        pitch = 204 / len(colors)
        solved = []
        for i, name in enumerate(colors):
            color, things = COLOR_ROWS[name]
            y = i * pitch
            body.append(card(0, y + 1, W, pitch - 5, r=7))
            body.append(crayon(W - 44, y + pitch / 2 - 8, color))
            body.append(text(COLOR_WORDS[name], W - 25, y + pitch / 2 + 10, 5.2, color=color))
            for k, thing in enumerate(things):
                x = W - 92 - k * 46
                body.append(pic(thing, x, y + 4, pitch - 13, "line"))
                solved.append(pic(thing, x, y + 4, pitch - 13, "color", class_="key-ring"))
        answer = [
            f"{name}: " + "، ".join(picture_of(t).word_ar for t in COLOR_ROWS[name][1]) for name in colors
        ]
        return Built({"svg": svg(body + solved)}, answer, [])
    words = [str(w) for w in params.get("words", ["butterfly"])]
    thing = picture_id(words[0])
    body.append(card(0, 0, W, 204, r=8))
    body.append(pic(thing, 18, 22, 150, "line"))
    body.append(card(W - 42, 6, 36, 36, r=6, fill="#FFF6F2", stroke="none"))
    body.append(pic(thing, W - 40, 8, 32, "color"))
    return Built({"svg": svg(body)}, None, [])
