"""Letter pages: finger tracing (a big solid letter with arrows) and English letters (model + dotted rows).

Letter shapes come from `qamra_workbook.strokes`; the pages never use a font for a traced letter, so the
model the child sees and the path they trace are the same drawing.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from markupsafe import Markup, escape

from qamra_workbook.geometry import Stroke, bounds
from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.strokes import Letter, letter

ARROW_AT = (0.16, 0.37, 0.58, 0.78, 0.94)
HARAKAT = ("\u064b", "\u0652")  # tanwin … sukun: they stay with the letter they sit on
Number = Callable[[int], str]  # writes a start dot's number in the page's numerals (PageContext.num)


def start_points(strokes: tuple[Stroke, ...] | list[Stroke], radius: float) -> list[tuple[float, float]]:
    """Where each stroke's numbered start dot goes: its start, or a little along the stroke when an earlier
    dot already sits there (both slants of A start at the apex)."""
    placed: list[tuple[float, float]] = []
    for s in strokes:
        point = s.start
        if any(math.dist(point, q) < radius * 1.9 for q in placed):
            point = s.at(min(0.45, radius * 2.9 / max(s.length, 1e-6)))[0]
        placed.append(point)
    return placed


def solid_letter(
    shape: Letter,
    *,
    fill: str,
    edge: str,
    width: float,
    arrows: tuple[float, ...] = ARROW_AT,
    number: Number,
) -> str:
    """A thick letter body (in the letter's own units) with white direction arrows and numbered start dots."""
    out = []
    for s in shape.strokes:
        out.append(draw.path(s.d, stroke=edge, width=width + width * 0.22))
    for x, y in shape.dots:
        out.append(
            draw.el("circle", cx=x, cy=y, r=width * 0.62, fill=fill, stroke=edge, stroke_width=width * 0.11)
        )
    for s in shape.strokes:
        out.append(draw.path(s.d, stroke=fill, width=width))
    for s in shape.strokes:
        for f in arrows:
            if s.length * f > width * 0.9:  # keep arrows clear of the start dot
                point, angle = s.at(f)
                out.append(draw.chevron(point, angle, width * 0.42, "#FFFFFF", width * 0.12))
    for k, point in enumerate(start_points(shape.strokes, width * 0.42), start=1):
        out.append(draw.start_dot(point, width * 0.42, number(k)))
    for k, (x, y) in enumerate(shape.dots, start=len(shape.strokes) + 1):
        out.append(draw.start_dot((x + width * 0.95, y), width * 0.3, number(k)))
    return "".join(out)


def letter_view(shape: Letter, pad: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = bounds(list(shape.strokes))
    for x, y in shape.dots:
        x0, y0, x1, y1 = (
            min(x0, x - shape.dot_r),
            min(y0, y - shape.dot_r),
            max(x1, x + shape.dot_r),
            max(y1, y + shape.dot_r),
        )
    return x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad


def highlight_first(word: str, color: str) -> Markup:
    """The word with its first letter (and that letter's harakat) in color."""
    head, rest = word[:1], word[1:]
    while rest and HARAKAT[0] <= rest[0] <= HARAKAT[1]:
        head, rest = head + rest[0], rest[1:]
    return Markup('<span style="color: {}">{}</span>{}').format(color, escape(head), escape(rest))


@page_type("finger-trace")
def finger_trace(ctx: PageContext) -> Built:
    params = ctx.page.params
    shape = letter(str(params.get("letter", "ب")), str(params.get("form", "isolated")))
    word = str(params.get("word", "duck"))
    pic = picture(word)
    problems = []
    if strip_tashkeel(pic.word_ar)[:1] != shape.char:
        problems.append(f"{pic.word_ar} does not start with {shape.char}")
    vx, vy, vw, vh = letter_view(shape, 22)
    body = solid_letter(shape, fill="#F7C84A", edge=ctx.style.deep, width=22, number=ctx.num)
    view = " ".join(draw.n(v) for v in (vx, vy, vw, vh))
    svg = Markup(  # nosec B704 (numbers and stroke data)
        f'<svg class="finger" viewBox="{view}" aria-hidden="true">{body}</svg>'
    )
    data = {
        "letter": svg,
        "char": shape.char,
        "pic": ctx.pic(word),
        "word": highlight_first(pic.word_ar, ctx.style.color),
    }
    return Built(data, None, problems)


def dotted_letter(shape: Letter, *, scale: float, x: float, y: float, first: bool, number: Number) -> str:
    """A letter in bold tracing dots at (x, y) (its design box's top-left), in mm."""
    moved = [s.scaled(scale, x, y) for s in shape.strokes]
    radius = 1.9 if first else 1.5
    out = [draw.dotted(s, spacing=3.5, r=0.95) for s in moved]
    if first:
        for s in moved:
            point, angle = s.at(min(0.55, 8.5 / max(s.length, 1)))
            out.append(draw.arrow(point, angle, 2.6))
    for k, point in enumerate(start_points(moved, radius), start=1):
        out.append(draw.start_dot(point, radius, number(k) if first else "", font_size=2.6))
    return "".join(out)


def tracing_row(
    shape: Letter, *, width: float, cap: float, count: int | None = None, number: Number
) -> Markup:
    """One writing row: guide lines, then `count` dotted letters (as many as fit when None); the first has
    numbered start dots and arrows, and the rest of the row is left for writing alone."""
    scale = cap / (shape.guides.base - shape.guides.top)
    height = cap + 12
    top = 5.0

    def gy(units: float) -> float:
        return top + (units - shape.guides.top) * scale

    def guide(units: float, color: str, stroke: float, dash: str = "none") -> str:
        y = gy(units)
        d = draw.d_path(("M", (2, y)), ("L", (width - 2, y)))
        return draw.el("path", d=d, stroke=color, stroke_width=stroke, stroke_dasharray=dash)

    body = [guide(shape.guides.top, "#9BB7E0", 0.5), guide(shape.guides.base, "#E27D63", 0.6)]
    if shape.guides.mid is not None:
        body.append(guide(shape.guides.mid, "#9BB7E0", 0.45, "2 1.6"))
    x0, _, x1, _ = bounds(list(shape.strokes))
    glyph = (x1 - x0) * scale
    step = glyph + 13
    fits = int((width - 16 - glyph) // step) + 1
    for i in range(fits if count is None else min(count, fits)):
        x = 10 + i * step - x0 * scale
        body.append(
            dotted_letter(
                shape, scale=scale, x=x, y=top - shape.guides.top * scale, first=i == 0, number=number
            )
        )
    return draw.svg(width, height, "".join(body), "trace-row")


@page_type("en-letter")
def en_letter(ctx: PageContext) -> Built:
    params = ctx.page.params
    char = str(params.get("letter", "A")).upper()
    capital, small = letter(char, "capital"), letter(char.lower(), "small")
    word = str(params.get("word", "apple"))
    pic = picture(word)
    problems = []
    if pic.first_letter_en != char:
        problems.append(f"{pic.word_en} does not start with {char}")
    if ctx.page.lang != "en" or not ctx.page.instruction_en:
        problems.append("English pages are LTR and carry the instruction in English too")
    model = (
        solid_letter(
            capital, fill=ctx.style.color, edge=ctx.style.deep, width=12.5, arrows=(0.55,), number=ctx.num
        )
        + f'<g transform="translate({draw.n(capital.width + 6)} 0)">'
        + solid_letter(
            small, fill=ctx.style.color, edge=ctx.style.deep, width=12.5, arrows=(0.4,), number=ctx.num
        )
        + "</g>"
    )
    total_w = capital.width + 6 + small.width
    data = {
        "model": Markup(  # nosec B704 (numbers and stroke data)
            f'<svg class="en-model" viewBox="0 -2 {draw.n(total_w)} 124" aria-hidden="true">{model}</svg>'
        ),
        "pic": ctx.pic(word),
        "word": Markup('<span style="color: {}">{}</span>{}').format(
            ctx.style.color, pic.word_en[:1].upper(), pic.word_en[1:]
        ),
        "word_ar": pic.word_ar,
        "rows": [
            tracing_row(capital, width=176, cap=33, number=ctx.num),
            tracing_row(small, width=176, cap=33, number=ctx.num),
            tracing_row(capital, width=176, cap=33, count=2, number=ctx.num),  # then on their own
        ],
    }
    return Built(data, None, problems)
