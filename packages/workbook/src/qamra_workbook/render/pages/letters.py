"""Letter pages: finger tracing (a big solid letter with arrows) and English letters (model + dotted rows).

Letter shapes come from `qamra_workbook.strokes`; the pages never use a font for a traced letter, so the
model the child sees and the path they trace are the same drawing.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from markupsafe import Markup, escape

from qamra_workbook.geometry import bounds
from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw, marks
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.strokes import Letter, letter

ARROW_AT = (0.16, 0.37, 0.58, 0.78, 0.94)
HARAKAT = ("\u064b", "\u0652")  # tanwin … sukun: they stay with the letter they sit on
Number = Callable[[int], str]  # writes a start dot's number in the page's numerals (PageContext.num)


def solid_letter(
    shape: Letter,
    *,
    fill: str,
    edge: str,
    width: float,
    arrows: tuple[float, ...] = ARROW_AT,
    number: Number,
) -> str:
    """A thick letter body (in the letter's own units) with white direction arrows and numbered start dots. A
    small mark (the little hamza of ك) is half as thick, with no arrows and its start dot beside it."""
    widths = [width * 0.5 if m else width for m in shape.marks]
    out = []
    for s, w in zip(shape.strokes, widths, strict=True):
        out.append(draw.path(s.d, stroke=edge, width=w + width * 0.22))
    for x, y in shape.dots:
        out.append(
            draw.el("circle", cx=x, cy=y, r=width * 0.62, fill=fill, stroke=edge, stroke_width=width * 0.11)
        )
    for s, w in zip(shape.strokes, widths, strict=True):
        out.append(draw.path(s.d, stroke=fill, width=w))
    for s, w in zip(shape.strokes, widths, strict=True):
        for f in arrows if w == width else ():
            if s.length * f > width * 0.9:  # keep arrows clear of the start dot
                point, angle = s.at(f)
                out.append(draw.chevron(point, angle, width * 0.42, "#FFFFFF", width * 0.12))
    body = [o for s, w in zip(shape.strokes, widths, strict=True) for o in marks.outline([s], w * 0.61, 2.0)]
    dots = [((x, y), width * 0.62) for x, y in shape.dots]
    badges = marks.badge_points(
        shape.strokes,
        shape.marks,
        width * 0.42,
        mark_radius=width * 0.3,
        reach=width * 0.36,
        obstacles=[*body, *dots],
    )
    for k, (point, w) in enumerate(zip(badges, widths, strict=True), start=1):
        out.append(draw.start_dot(point, width * 0.42 if w == width else width * 0.3, number(k)))
    taken = [*body, *((p, width * 0.42) for p in badges)]
    spots = marks.dot_badges(list(shape.dots), width * 0.62, width * 0.3, taken, shape.strokes)
    for k, point in enumerate(spots, start=len(shape.strokes) + 1):
        out.append(draw.start_dot(point, width * 0.3, number(k)))
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


def letter_extent(shape: Letter) -> tuple[float, float, float, float]:
    """The letter's bounds in its own units, its dots included."""
    x0, y0, x1, y1 = bounds(list(shape.strokes))
    for x, y in shape.dots:
        r = shape.dot_r
        x0, y0, x1, y1 = min(x0, x - r), min(y0, y - r), max(x1, x + r), max(y1, y + r)
    return x0, y0, x1, y1


DOT_R, MARK_R = 0.95, 0.7  # tracing dots on a writing row: the body's, and a small mark's (mm)


def dotted_letter(
    shape: Letter,
    *,
    scale: float,
    x: float,
    y: float,
    first: bool,
    number: Number,
    spacing: float = 3.5,
    dot: float = DOT_R,
    mark: float = MARK_R,
    number_dots: bool = True,
    labels: Sequence[str] | None = None,
    joined: bool = False,
) -> str:
    """A letter in bold tracing dots (`dot` mm, about `spacing` apart) at (x, y) (its design box's top-left),
    in mm. Where the pen comes back along its own line (a tooth, the head of ـد) the dots are drawn once. A
    small mark (the hamza of أ, the little hamza of ك) gets a thin pale ghost of its shape under smaller
    (`mark`), evenly spaced dots, and its start dot beside it (`render.marks`). The letter's own dots are
    round dots to fill in. On the first letter of a row the start dots (and, with `number_dots`, the letter's
    dots) are numbered in writing order, and each stroke has an arrow (a small mark's sits outside its
    shape). In a word, `labels` are the numbers of its start dots (`pen_lifts`) and a `joined` letter has
    none on its first stroke: the pen arrives from the letter before."""
    moved = [s.scaled(scale, x, y) for s in shape.strokes]
    small = shape.small
    radius = 1.9 if first or any(labels or ()) else 1.5
    dots = [(x + cx * scale, y + cy * scale) for cx, cy in shape.dots]
    dot_r = max(shape.dot_r * scale, 1.3)
    mark = marks.dot_size(moved, small, mark)
    out = [marks.ghost(s, mark) for s, m in zip(moved, small, strict=True) if m]
    body = [s for s, m in zip(moved, small, strict=True) if not m]
    lines = iter(marks.dotted_once(body, spacing))
    for s, m in zip(moved, small, strict=True):
        out.append(marks.mark_dots(s, spacing, mark) if m else draw.dots(next(lines), dot))
    dot_r = marks.dot_radius(dots, moved, dot_r, dot)
    out += [marks.dot_to_fill(cx, cy, dot_r, ring=0.45) for cx, cy in dots]
    obstacles = [*marks.outline(moved, dot), *((d, dot_r) for d in dots)]
    badges = marks.badge_points(
        moved, small, radius, mark_radius=radius * 0.8, reach=mark, obstacles=obstacles
    )
    shown = [k for k in range(len(moved)) if not (joined and k == 0)]
    default = [number(n) if first else "" for n in range(1, len(shown) + 1)]
    names = list(labels) if labels is not None else default
    taken = [*obstacles, *((badges[k], radius) for k in shown)]
    if first:
        for s, m in zip(moved, small, strict=True):
            if m:
                arrow, centre = marks.side_arrow(s, 1.7, mark, taken)
                taken.append((centre, 0.9))
                out.append(arrow)
            else:
                point, angle = s.at(min(0.55, 8.5 / max(s.length, 1)))
                out.append(draw.arrow(point, angle, 2.6))
    for k, name in zip(shown, names, strict=True):
        r = radius * 0.8 if small[k] else radius
        out.append(draw.start_dot(badges[k], r, name, font_size=2.2 if small[k] else 2.6))
    if first and number_dots:
        spots = marks.dot_badges(dots, dot_r, 1.5, taken, moved)
        for k, point in enumerate(spots, start=len(shown) + 1):
            out.append(draw.start_dot(point, 1.5, number(k), font_size=2.1))
    return "".join(out)


def pen_lifts(letters: Sequence[Letter], first: bool, number: Number) -> list[tuple[list[str], bool]]:
    """For each letter of a word: the labels of its start dots, and whether the pen arrives from the letter
    before (then its first stroke has no start dot). The start dots are numbered across the whole word in
    writing order («أسد»: ١ the alif, ٢ its hamza, ٣ the س, and the د goes on from the س) on the `first`
    row, and carry no number on the others."""
    out, n = [], 1
    for shape in letters:
        joined = shape.join_right is not None
        count = len(shape.strokes) - joined
        out.append(([number(n + k) if first else "" for k in range(count)], joined))
        n += count
    return out


def row_room(shape: Letter, cap: float) -> tuple[float, float]:
    """Room (mm) a writing row keeps above its top line and below its base line: marks above the top line
    (the hamza of أ), and for Arabic the whole band down to the descender line, where tails and bowls go."""
    g = shape.guides
    scale = cap / (g.base - g.top)
    _, y0, _, y1 = letter_extent(shape)
    low = g.low if g.low is not None and shape.rtl else g.base
    return max(0.0, (g.top - y0) * scale), max(0.0, (max(y1, low) - g.base) * scale)


def tracing_row(
    shape: Letter,
    *,
    width: float,
    cap: float,
    count: int | None = None,
    number: Number,
    room: tuple[float, float] | None = None,
) -> Markup:
    """One writing row: guide lines, then `count` dotted letters (as many as fit when None); the first has
    numbered start dots and arrows, and the rest of the row is left for writing alone. Arabic rows run right
    to left and keep room below the base line for tails (down to the descender line, drawn dashed). `room`
    (mm above the top line and below the base line) overrides the letter's own (`row_room`), so rows of
    different letters side by side have their lines at the same heights."""
    g = shape.guides
    scale = cap / (g.base - g.top)
    above, below = room if room is not None else row_room(shape, cap)
    top = 5.0 + above
    height = top + cap + max(7.0, below + 4.0)

    def gy(units: float) -> float:
        return top + (units - g.top) * scale

    def guide(units: float, color: str, stroke: float, dash: str = "none") -> str:
        y = gy(units)
        d = draw.d_path(("M", (2, y)), ("L", (width - 2, y)))
        return draw.el("path", d=d, stroke=color, stroke_width=stroke, stroke_dasharray=dash)

    body = [guide(g.top, "#9BB7E0", 0.5), guide(g.base, "#E27D63", 0.6)]
    if g.mid is not None:
        body.append(guide(g.mid, "#9BB7E0", 0.45, "2 1.6"))
    if shape.rtl and g.low is not None:
        body.append(guide(g.low, "#C9D6EA", 0.4, "1 1.6"))
    x0, _, x1, _ = letter_extent(shape)
    glyph = (x1 - x0) * scale
    step = glyph + 13
    fits = int((width - 16 - glyph) // step) + 1
    # a smaller row has its dots closer and smaller, so a short letter on it (م ه و) still shows its shape
    spacing = min(3.5, max(2.4, cap * 0.175))
    for i in range(fits if count is None else min(count, fits)):
        x = width - 10 - i * step - x1 * scale if shape.rtl else 10 + i * step - x0 * scale
        body.append(
            dotted_letter(
                shape,
                scale=scale,
                x=x,
                y=top - g.top * scale,
                first=i == 0,
                number=number,
                spacing=spacing,
                dot=DOT_R * spacing / 3.5,
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
    depth = max(124.0, letter_extent(small)[3] + 12)  # room for a tail (g, j, p, q, y)
    cap = (
        28.0 if row_room(small, 33)[1] > 0 else 33.0
    )  # a small letter with a tail (g, j, p, q, y) needs room
    data = {
        "model": Markup(  # nosec B704 (numbers and stroke data)
            f'<svg class="en-model" viewBox="0 -2 {draw.n(total_w)} {draw.n(depth)}" aria-hidden="true">'
            f"{model}</svg>"
        ),
        "pic": ctx.pic(word, "line" if params.get("color_in") else "color"),
        "word": Markup('<span style="color: {}">{}</span>{}').format(
            ctx.style.color, pic.word_en[:1].upper(), pic.word_en[1:]
        ),
        "word_ar": pic.word_ar,
        "rows": [
            tracing_row(capital, width=176, cap=cap, number=ctx.num),
            tracing_row(small, width=176, cap=cap, number=ctx.num),
            tracing_row(capital, width=176, cap=cap, count=2, number=ctx.num),  # then on their own
        ],
    }
    return Built(data, None, problems)
