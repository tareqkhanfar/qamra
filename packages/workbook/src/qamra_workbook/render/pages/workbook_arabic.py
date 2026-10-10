"""«دوسية التأسيس» Arabic letter pages, the fixed per-letter sequence of Addendum 5 §3: meet the letter with
two pictures to color (letter-intro), trace it big then smaller (letter-trace), write it guided then alone
(letter-write), find it and pick the right one (find-letter), and match letter ↔ picture ↔ word
(match-letter-picture). Every letter is drawn from Qamra's hand (`qamra_workbook.letters`), never a font.
"""

from __future__ import annotations

import math

from markupsafe import Markup, escape

from qamra_workbook.geometry import Stroke, bounds
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw, marks
from qamra_workbook.render.foundation_text import letters_head
from qamra_workbook.render.pages.letters import HARAKAT, letter_extent, row_room, tracing_row
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
# the chip on the big letter of a tracing page: it names the letter's size, and a letter's name is feminine
# («الأَلِفُ الكَبيرَةُ»), as in the plan's skill line «كبيرة ثم أصغر» (one rule for every size word)
BIG_CHIP = "كَبيرَةٌ"


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
    green start dots and arrows; its dots are round dots to fill in, numbered beside them. A small mark (the
    hamza of أ, the little hamza of ك) gets a narrow band, so its head stays an open curl, smaller dots, and
    its start dot and arrow beside it, never on it (`render.marks`)."""
    scale, dx, dy = (
        fit_lines(shape, x + 6, y + 6, w - 12, h - 12)
        if shape.form == "digit"
        else fit_capped(shape, x, y, w, h, 6, most)
    )
    band = band_units * scale
    moved = [s.scaled(scale, dx, dy) for s in shape.strokes]
    small = shape.small
    widths = [mark_band(s, band) if m else band for s, m in zip(moved, small, strict=True)]
    moved = clear_of_body(moved, shape.marks, widths)
    dots = [(dx + cx * scale, dy + cy * scale) for cx, cy in shape.dots]
    disc = min(band * 0.45, 10 * scale)
    out = [draw.path(s.d, stroke=TRACK, width=wd) for s, wd in zip(moved, widths, strict=True)]
    out += [draw.el("circle", cx=cx, cy=cy, r=disc, fill=TRACK) for cx, cy in dots]
    lines = iter(marks.dotted_once([s for s, m in zip(moved, small, strict=True) if not m], 4.2))
    out += [
        marks.mark_dots(s, 4.2, 1.0) if m else draw.dots(next(lines), 1.25)
        for s, m in zip(moved, small, strict=True)
    ]
    out += [marks.dot_to_fill(cx, cy, min(band * 0.3, 7 * scale), ring=0.7, fill="none") for cx, cy in dots]
    obstacles = [
        *(o for s, wd in zip(moved, widths, strict=True) for o in marks.outline([s], wd / 2, 1.0)),
        *((d, disc) for d in dots),
    ]
    badges = marks.badge_points(
        moved,
        small,
        band * 0.3,
        mark_radius=band * 0.22,
        reach=min(widths) / 2,
        obstacles=obstacles,
    )
    taken = [*obstacles, *((p, band * 0.3) for p in badges)]
    for s, m, wd in zip(moved, small, widths, strict=True):
        if m:
            arrow, centre = marks.side_arrow(s, band * 0.22, wd / 2, taken, color)
            taken.append((centre, band * 0.12))
            out.append(arrow)
            continue
        for f in (0.3, 0.62, 0.9):
            if s.length * f > band * 1.2:
                point, angle = s.at(f)
                out.append(draw.arrow(point, angle, band * 0.26, color))
    for k, (point, m) in enumerate(zip(badges, small, strict=True), start=1):
        out.append(draw.start_dot(point, band * 0.22 if m else band * 0.3, number(k)))
    spots = marks.dot_badges(dots, disc, band * 0.22, taken, moved)
    for k, point in enumerate(spots, start=len(moved) + 1):
        out.append(draw.start_dot(point, band * 0.22, number(k)))
    return "".join(out)


def clear_of_body(strokes: list[Stroke], marks_: tuple[bool, ...], widths: list[float]) -> list[Stroke]:
    """The strokes, a small mark moved just clear of the body's wide band where the two bands would touch
    (the hamza over the alif sits close to it in print, but the big letter's band is finger-wide)."""
    body = [p for s, m in zip(strokes, marks_, strict=True) if not m for p in s.dots(1.0)]
    wide = max((w for w, m in zip(widths, marks_, strict=True) if not m), default=0.0)
    out = []
    for s, m, w in zip(strokes, marks_, widths, strict=True):
        if m and body:
            need = wide / 2 + w / 2 + 1.0
            q, p = min(((q, p) for q in body for p in s.dots(1.0)), key=lambda qp: math.dist(*qp))
            d = math.dist(q, p)
            if 1e-6 < d < need:
                s = s.scaled(1, (p[0] - q[0]) / d * (need - d), (p[1] - q[1]) / d * (need - d))
        out.append(s)
    return out


def mark_band(stroke: Stroke, band: float) -> float:
    """The pale band of a small mark on a big letter: about a fifth of the mark's size, so the head of the
    hamza stays an open curl (never more than half the letter's band)."""
    x0, y0, x1, y1 = bounds([stroke])
    return min(band * 0.55, 0.2 * max(x1 - x0, y1 - y0))


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


def row_cap(shape: Letter, height: float) -> float:
    """The cap height at which a `tracing_row` of this letter is `height` mm tall."""
    above, below = row_room(shape, 1.0)
    cap = (height - 9) / (1 + above + below)
    return cap if below * cap + 4 >= 7 else (height - 12) / (1 + above)


def letter_grid(
    shapes: list[Letter],
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    rtl: bool,
    count: int | None,
    number: Number,
    most: float = 20.0,
) -> tuple[list[str], float]:
    """Writing rows for several letters in a box: one row a letter, or two or three side by side in a row
    (right to left on an Arabic page) when that draws them bigger, each cell holding at least two copies
    (`count` dotted ones and room to write one alone, when given), and every cell's lines at the same
    heights. A review's letters never shrink to a few scattered dots. Returns the rows and their cap."""
    gap = 4.0
    need = 2 if count is None else count + 1

    def layout(cols: int) -> tuple[float, int, float]:
        pitch = h / -(-len(shapes) // cols)
        cell = (w - gap * (cols - 1)) / cols
        caps = [row_cap(s, pitch - 1) for s in shapes]
        for s in shapes:  # 10 mm margins and 13 mm between two copies
            x0, _, x1, _ = letter_extent(s)
            caps.append(
                (cell - 20 - 13 * (need - 1)) / need / max(x1 - x0, 1) * (s.guides.base - s.guides.top)
            )
        return min(most, *caps), cols, pitch

    cap, cols, pitch = layout(1)
    for k in range(2, min(3, len(shapes)) + 1):
        other = layout(k)
        if other[0] > cap + 1:
            cap, cols, pitch = other
    cell = (w - gap * (cols - 1)) / cols
    rooms = [row_room(s, cap) for s in shapes]
    room = (max(a for a, _ in rooms), max(b for _, b in rooms))
    out = []
    for i, shape in enumerate(shapes):
        row, col = divmod(i, cols)
        cx = x + (w - (col + 1) * cell - col * gap if rtl else col * (cell + gap))
        drawn = tracing_row(shape, width=cell, cap=cap, count=count, number=number, room=room)
        _, height = row_svg(drawn, 0, 0)
        out.append(row_svg(drawn, cx, y + row * pitch + max(0.0, (pitch - height) / 2))[0])
    return out, cap


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
    body.append(text(letters_head([char]), W - 25, 15, 6.2, cls="wb-title", color=ctx.style.deep))
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
    body.append(text(BIG_CHIP, 20, 12, 5, color=ctx.style.deep))
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
    body.append(text("أَبْدَأُ مِنَ النُّقْطَةِ الخَضْراءِ وَأَتْبَعُ السَّهْمَ", 64, 15, 5.2, color=INK))
    body.append(text("ثُمَّ أَكْتُبُ عَلى النِّقاطِ، ثُمَّ وَحْدي", 64, 24, 4.6, color="#676B83"))
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
