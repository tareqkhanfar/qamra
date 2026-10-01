"""«دوسية التأسيس» Arabic letter pages, the fixed per-letter sequence of Addendum 5 §3: meet the letter with
two pictures to color (letter-intro), trace it big then smaller (letter-trace), write it guided then alone
(letter-write), find it and pick the right one (find-letter), and match letter ↔ picture ↔ word
(match-letter-picture). Every letter is drawn from Qamra's hand (`qamra_workbook.letters`), never a font.
"""

from __future__ import annotations

from markupsafe import Markup, escape

from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.foundation_text import letter_name
from qamra_workbook.render.pages.letters import HARAKAT, letter_extent, start_points, tracing_row
from qamra_workbook.render.pages.workbook_common import (
    INK,
    Number,
    W,
    card,
    fit_capped,
    fit_lines,
    glyph,
    pic,
    picture_id,
    picture_of,
    shape_of,
    start_marks,
    svg,
    text,
)
from qamra_workbook.render.registry import Built, PageContext, page_type

TRACK = "#F9DA8F"  # the wide band of a big letter to trace, as wide as a child's finger


def first_letter(word: str) -> str:
    """The letter a word starts with, as the child hears it: أ for words that start with أ or إ."""
    bare = strip_tashkeel(word)
    return "أ" if bare[:1] in "أإآا" else bare[:1]


def same_letter(a: str, b: str) -> bool:
    alif = "أإآا"
    return a == b or (a in alif and b in alif)


def word_markup(word: str, x: float, y: float, size: float, color: str, rtl: bool = True) -> str:
    """The word with its first letter (and that letter's harakat) in `color`: SVG text with a tspan."""
    head, rest = word[:1], word[1:]
    while rest and HARAKAT[0] <= rest[0] <= HARAKAT[1]:
        head, rest = head + rest[0], rest[1:]
    cls = "wb-word" if rtl else "wb-en"
    direction = ' direction="rtl"' if rtl else ""
    return (
        f'<text x="{draw.n(x)}" y="{draw.n(y)}" font-size="{draw.n(size)}" text-anchor="middle" fill="{INK}" '
        f'class="{cls}"{direction}><tspan fill="{color}">{escape(head)}</tspan>{escape(rest)}</text>'
    )


def big_track(
    shape: Letter,
    x: float,
    y: float,
    w: float,
    h: float,
    number: Number,
    color: str,
    most: float = 0.5,
    band_units: float = 24.0,
) -> str:
    """The letter as big as the box allows (at most `most` mm per letter unit): a wide pale band (`band_units`
    wide, narrower for a small letter so its loop stays open) with a dotted centre line to trace, numbered
    green start dots and arrows; its dots are rings to fill in."""
    scale, dx, dy = (
        fit_lines(shape, x + 6, y + 6, w - 12, h - 12)
        if shape.form == "digit"
        else fit_capped(shape, x, y, w, h, 6, most)
    )
    band = band_units * scale
    moved = [s.scaled(scale, dx, dy) for s in shape.strokes]
    marks = [
        band * 0.55 if i and shape.rtl and raw.length < 60 else band for i, raw in enumerate(shape.strokes)
    ]
    out = [draw.path(s.d, stroke=TRACK, width=w) for s, w in zip(moved, marks, strict=True)]
    for cx, cy in shape.dots:
        r = min(band * 0.45, 10 * scale)
        out.append(draw.el("circle", cx=dx + cx * scale, cy=dy + cy * scale, r=r, fill=TRACK))
    out += [draw.dotted(s, spacing=4.2, r=1.25) for s in moved]
    for cx, cy in shape.dots:
        out.append(
            draw.el(
                "circle",
                cx=dx + cx * scale,
                cy=dy + cy * scale,
                r=min(band * 0.3, 7 * scale),
                fill="none",
                stroke=draw.DOT,
                stroke_width=0.7,
                stroke_dasharray="1.2 1",
            )
        )
    for s in moved:
        for f in (0.3, 0.62, 0.9):
            if s.length * f > band * 1.2:
                point, angle = s.at(f)
                out.append(draw.arrow(point, angle, band * 0.26, color))
    for k, point in enumerate(start_points(moved, band * 0.3), start=1):
        out.append(draw.start_dot(point, band * 0.3, number(k)))
    for k, (cx, cy) in enumerate(shape.dots, start=len(moved) + 1):
        out.append(draw.start_dot((dx + cx * scale + band * 0.75, dy + cy * scale), band * 0.22, number(k)))
    return "".join(out)


def row_svg(row: Markup, x: float, y: float) -> tuple[str, float]:
    """A writing row (an `<svg>` in mm from `tracing_row`) placed at (x, y); returns it and its height."""
    raw = str(row)
    height = float(raw.split('viewBox="0 0 ')[1].split('"')[0].split()[1])
    width = float(raw.split('viewBox="0 0 ')[1].split('"')[0].split()[0])
    inner = raw.replace("<svg", f'<svg x="{draw.n(x)}" y="{draw.n(y)}"', 1)
    inner = inner.replace(
        f'width="{draw.n(width)}mm" height="{draw.n(height)}mm"',
        f'width="{draw.n(width)}" height="{draw.n(height)}"',
        1,
    )
    return inner, height


@page_type("letter-intro")
def letter_intro(ctx: PageContext) -> Built:
    params = ctx.page.params
    char = str(params.get("letter", "ب"))
    words = [str(w) for w in params.get("words", [])][:2]
    shape = shape_of(char)
    problems = [f"«{w}» does not start with {char}" for w in words if not same_letter(first_letter(w), char)]
    if not 1 <= len(words) <= 2:
        problems.append("a letter is met with 1–2 pictures")
    color = ctx.style.color
    body = [card(0, 0, W, 118, r=7)]
    scale, dx, dy = fit_capped(shape, 30, 8, 126, 104, 10, 0.62)
    body.append(glyph(shape, scale, dx, dy, width=24, edge=INK, fill="#FFFFFF"))
    body.append(card(W - 44, 6, 38, 13, r=6.5, fill=ctx.style.tint, stroke="none"))
    body.append(text(f"حرف {letter_name(char)}", W - 25, 15, 6.2, cls="wb-title", color=ctx.style.deep))
    body.append(draw.el("circle", cx=16, cy=16, r=9, fill=ctx.style.tint))
    body.append(glyph(shape, *fit_lines(shape, 9, 8.5, 14, 15), color=ctx.style.deep, width=15))
    gap = 6.0
    cw = (W - gap * (len(words) - 1)) / max(len(words), 1)
    for i, w in enumerate(words):
        x = W - (i + 1) * cw - i * gap
        body.append(card(x, 124, cw, 80, r=7))
        body.append(pic(picture_id(w), x + cw / 2 - 29, 128, 58, "line"))
        body.append(word_markup(picture_of(w).word_ar, x + cw / 2, 198, 11, color))
    return Built({"svg": svg(body)}, None, problems)


@page_type("letter-trace")
def letter_trace(ctx: PageContext) -> Built:
    params = ctx.page.params
    char = str(params.get("letter", "ب"))
    sizes = [str(s) for s in params.get("sizes", ["xl", "l", "m"])]
    shape = shape_of(char)
    body = [card(0, 0, W, 84, r=7)]
    body.append(big_track(shape, 20, 2, 146, 80, ctx.num, ctx.style.color))
    body.append(card(5, 5, 30, 10, r=5, fill=ctx.style.tint, stroke="none"))
    body.append(text("كبير", 20, 12, 5, color=ctx.style.deep))
    y = 90.0
    caps = {"l": 24.0, "m": 17.0, "s": 13.0}
    rows = [s for s in sizes if s in caps]
    for size in rows:
        row, height = row_svg(tracing_row(shape, width=W - 10, cap=caps[size], number=ctx.num), 5, y + 1)
        body.append(card(0, y - 2, W, height + 5, r=6))
        body.append(row)
        y += height + 7
    problems = [] if y <= 206 else [f"the tracing rows need {y:.0f} mm (max 204)"]
    if sizes[:1] != ["xl"]:
        problems.append("letter-trace starts with the big letter (xl)")
    return Built({"svg": svg(body)}, None, problems)


def empty_row(shape: Letter, width: float, cap: float) -> tuple[str, float]:
    """Writing lines without letters, for writing alone: a green dot marks where the first letter starts."""
    row = str(tracing_row(shape, width=width, cap=cap, count=0, number=str))
    height = float(row.split('viewBox="0 0 ')[1].split('"')[0].split()[1])
    return row, height


@page_type("letter-write")
def letter_write(ctx: PageContext) -> Built:
    """A model with start dots and arrows, guided rows (all dotted, then two dotted and room to go on) and
    rows to write alone (only a start marker)."""
    params = ctx.page.params
    char = str(params.get("letter", "ب"))
    guided, alone = int(params.get("guided", 2)), int(params.get("independent", 1))
    shape = shape_of(char)
    cap = 20.0 if guided + alone <= 3 else 16.0
    body = [card(0, 0, W, 34, r=7)]
    scale, dx, dy = fit_lines(shape, W - 64, 2, 58, 30)
    body.append(glyph(shape, scale, dx, dy, color=ctx.style.color, width=15))
    body.append(start_marks(shape, scale, dx, dy, 2.2, ctx.num))
    body.append(text("أبدأ من النقطة الخضراء وأتبع السهم", 64, 15, 5.2, color=INK))
    body.append(text("ثم أكتب على النقاط، ثم وحدي", 64, 24, 4.6, color="#676B83"))
    y = 39.0
    for k in range(guided + alone):
        if k < guided:
            row = tracing_row(shape, width=W - 10, cap=cap, count=None if k == 0 else 2, number=ctx.num)
            part, height = row_svg(row, 5, y + 2)
        else:
            part, height = row_svg(Markup(empty_row(shape, W - 10, cap)[0]), 5, y + 2)  # nosec B704: SVG built from the letter path, no user input
            _, _, x1, _ = letter_extent(shape)
            g = shape.guides
            s = cap / (g.base - g.top)
            start = shape.strokes[0].start
            sx = 5 + (W - 10) - 10 - (x1 - start[0]) * s
            above = max(0.0, (g.top - letter_extent(shape)[1]) * s)
            sy = y + 2 + 5 + above + (start[1] - g.top) * s
            part += draw.start_dot((sx, sy), 1.9)
        body.append(card(0, y, W, height + 3, r=6, fill="#FFFFFF" if k < guided else "#FFFDF6"))
        body.append(part)
        y += height + 6
    problems = [] if y <= 208 else [f"the writing rows need {y:.0f} mm (max 204)"]
    if guided < 1 or alone < 1:
        problems.append("letter-write has guided rows, then rows to write alone")
    return Built({"svg": svg(body)}, None, problems)
