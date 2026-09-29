"""Shared pieces of the «دوسية التأسيس» pages: word → picture, letter shapes (with أ), letters drawn as solid,
hollow (to color) or dotted glyphs placed in boxes, and small SVG parts (cards, labels, answer lines).

Every page lays out its work area as one SVG in millimetres (`W` × `H`, scaled to the space left under the
header), so nothing can overflow and tests can read what a page shows from `data-*` attributes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from markupsafe import Markup, escape

from qamra_workbook.geometry import Point, Stroke
from qamra_workbook.letters import ARABIC
from qamra_workbook.letters.hamza import HAMZA
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures import PICTURES, Picture, Style, find_ar
from qamra_workbook.pictures.model import OUTLINE, strip_tashkeel
from qamra_workbook.pictures.workbook_words_2 import WORD_ALIASES_2
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import letter_extent, start_points
from qamra_workbook.strokes import letter as stroke_letter

W, H = 186.0, 204.0  # the work area drawing, mm
CARD, LINE, INK, MUTED = "#FFFFFF", "#E4D6BC", "#1C2140", "#676B83"
ANSWER = "#E0483A"
Number = Callable[[int], str]

# plan words whose picture has a different library word (the library word is printed under the picture)
WORD_ALIASES = {"خيار": "cucumber", "حقيبة": "bag", "دب": "bear", "ثوم": "garlic", "بيضة": "egg"}
WORD_ALIASES.update(WORD_ALIASES_2)  # volume 2's words


def picture_id(word: str) -> str:
    """The library picture for a plan word: an English id (`apple`), or an Arabic word with or without
    tashkeel (`أرنب`)."""
    if word in PICTURES:
        return word
    bare = strip_tashkeel(word)
    if bare in WORD_ALIASES:
        return WORD_ALIASES[bare]
    found = find_ar(bare)
    if found is None:
        raise KeyError(f"no picture for the word «{word}» in the library")
    return found.id


def picture_of(word: str) -> Picture:
    return PICTURES[picture_id(word)]


def arabic_shape(char: str, form: str = "isolated") -> Letter:
    """The letter's shape in Qamra's hand. أ إ آ are the alif with a small hamza (or madda) mark written after
    it: above the top line for أ and آ, under the base line for إ."""
    if char not in "أإآ":
        return ARABIC[(char, form)]
    # draft: educator review: the hamza's size and height above the alif
    alif = ARABIC[("ا", form)]
    if char == "آ":
        mark = Stroke("M6 -40 C12 -48 18 -48 24 -42 C30 -36 36 -36 44 -44")
    else:
        dy = -100 if char == "أ" else 82
        dx = alif.strokes[0].start[0] - 45 * 0.5
        mark = HAMZA_STROKE.scaled(0.5, dx, dy)
    return Letter(char, form, alif.width, alif.guides, (*alif.strokes, mark), (), 0.0, *_joins(alif))


HAMZA_STROKE = Stroke(HAMZA)


def _joins(shape: Letter) -> tuple[Point | None, Point | None]:
    return shape.join_right, shape.join_left


def shape_of(char: str) -> Letter:
    """An Arabic letter's isolated form, an English letter (capital or small) or a digit."""
    if "؀" <= char <= "ۿ":
        return arabic_shape(char)
    from qamra_workbook.digits import DIGITS

    if char in DIGITS:
        return DIGITS[char]
    return stroke_letter(char, "capital" if char.isupper() else "small")


def fit(
    shape: Letter, x: float, y: float, w: float, h: float, pad: float = 0.0
) -> tuple[float, float, float]:
    """(scale, dx, dy) that centre the letter's extent in the box x, y, w, h (mm)."""
    x0, y0, x1, y1 = letter_extent(shape)
    scale = min((w - 2 * pad) / max(x1 - x0, 1), (h - 2 * pad) / max(y1 - y0, 1))
    dx = x + (w - (x1 - x0) * scale) / 2 - x0 * scale
    dy = y + (h - (y1 - y0) * scale) / 2 - y0 * scale
    return scale, dx, dy


def fit_capped(
    shape: Letter, x: float, y: float, w: float, h: float, pad: float, most: float
) -> tuple[float, float, float]:
    """`fit`, but never larger than `most` mm per letter unit: a short letter (د) is not blown up to the
    height of a tall one, so its body keeps a child-sized stroke."""
    scale, dx, dy = fit(shape, x, y, w, h, pad)
    if scale <= most:
        return scale, dx, dy
    x0, y0, x1, y1 = letter_extent(shape)
    return most, x + (w - (x1 - x0) * most) / 2 - x0 * most, y + (h - (y1 - y0) * most) / 2 - y0 * most


def fit_lines(shape: Letter, x: float, y: float, w: float, h: float) -> tuple[float, float, float]:
    """(scale, dx, dy) that put the letter's writing band (top line, or its marks above it, down to the
    descender line or the base line) in the box, centred across: letters and numerals of one page get the
    same size and stroke weight, and sit on one base line (a small ٠ stays small, د is not blown up)."""
    g = shape.guides
    x0, y0, x1, y1 = letter_extent(shape)
    low = g.low if g.low is not None else g.base
    top, bottom = min(g.top, y0), max(low, y1)
    scale = min(h / (bottom - top), w / max(x1 - x0, 1))
    dx = x + (w - (x1 - x0) * scale) / 2 - x0 * scale
    dy = y + (h - (bottom - top) * scale) / 2 - top * scale
    return scale, dx, dy


def glyph(
    shape: Letter,
    scale: float,
    dx: float,
    dy: float,
    *,
    color: str = INK,
    width: float = 13.0,
    edge: str | None = None,
    fill: str | None = None,
) -> str:
    """The letter as a thick marker line (`width` in the letter's units), or hollow for coloring when `edge`
    and `fill` are given (an outline of `edge` around a `fill` body)."""
    moved = [s.scaled(scale, dx, dy) for s in shape.strokes]
    wmm = width * scale
    # Arabic marks (the hamza of أ, the head of ك) are small: drawn thinner so they stay open shapes
    widths = [
        wmm * 0.5 if i and shape.rtl and raw.length < 60 else wmm for i, raw in enumerate(shape.strokes)
    ]
    dots = [(dx + x * scale, dy + y * scale) for x, y in shape.dots]
    out = []
    if edge is not None and fill is not None:
        r = min(width * 0.45, 10.0) * scale  # clear of the body, even under a wide outline
        body = [(s, w) for s, w in zip(moved, widths, strict=True) if w == wmm]
        marks = [s for s, w in zip(moved, widths, strict=True) if w != wmm]  # small marks stay solid lines
        out += [draw.path(s.d, stroke=edge, width=w * 1.28) for s, w in body]
        out += [draw.el("circle", cx=x, cy=y, r=r * 1.14, fill=edge) for x, y in dots]
        out += [draw.path(s.d, stroke=fill, width=w) for s, w in body]
        out += [draw.el("circle", cx=x, cy=y, r=r * 0.86, fill=fill) for x, y in dots]
        out += [draw.path(s.d, stroke=edge, width=wmm * 0.34) for s in marks]
    else:
        r = max(shape.dot_r * scale * 1.05, min(wmm * 0.62, 11.0 * scale))
        out += [draw.path(s.d, stroke=color, width=w) for s, w in zip(moved, widths, strict=True)]
        out += [draw.el("circle", cx=x, cy=y, r=r, fill=color) for x, y in dots]
    return f'<g data-glyph="{escape(shape.char)}">{"".join(out)}</g>'


def start_marks(shape: Letter, scale: float, dx: float, dy: float, r: float, number: Number) -> str:
    """Numbered green start dots and one arrow per stroke on a glyph drawn at (scale, dx, dy)."""
    moved = [s.scaled(scale, dx, dy) for s in shape.strokes]
    out = []
    for s in moved:
        point, angle = s.at(min(0.5, r * 3.2 / max(s.length, 1e-6)))
        out.append(draw.arrow(point, angle, r * 1.3))
    for k, point in enumerate(start_points(moved, r), start=1):
        out.append(draw.start_dot(point, r, number(k)))
    return "".join(out)


def text(
    value: str,
    x: float,
    y: float,
    size: float,
    *,
    cls: str = "wb-label",
    anchor: str = "middle",
    color: str = INK,
    rtl: bool = True,
) -> str:
    """A line of text in the SVG (size in mm); Arabic runs right to left. `anchor` is physical: "end" puts the
    text's right end at x, "start" its left end, in either direction."""
    direction = ' direction="rtl"' if rtl else ""
    if rtl:
        anchor = {"end": "start", "start": "end"}.get(anchor, anchor)
    return (
        f'<text x="{draw.n(x)}" y="{draw.n(y)}" font-size="{draw.n(size)}" text-anchor="{anchor}" '
        f'fill="{color}" class="{cls}"{direction}>{escape(value)}</text>'
    )


def card(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    r: float = 5.0,
    fill: str = CARD,
    stroke: str = LINE,
    dash: str = "none",
    width: float = 0.5,
) -> str:
    return draw.el(
        "rect",
        x=x,
        y=y,
        width=w,
        height=h,
        rx=r,
        fill=fill,
        stroke=stroke,
        stroke_width=width,
        stroke_dasharray=dash,
    )


def pic(picture_id_: str, x: float, y: float, size: float, style: Style = "color", **attrs: str) -> str:
    """A library picture in a size × size box at (x, y)."""
    inner = PICTURES[picture_id_].inner(style)
    return draw.el("svg", inner, x=x, y=y, width=size, height=size, viewBox="0 0 100 100", **attrs)


def hook(x: float, y: float, r: float = 1.8, color: str = OUTLINE) -> str:
    """A connection dot the child draws a line from (matching pages)."""
    return draw.el("circle", cx=x, cy=y, r=r, fill="#FFFFFF", stroke=color, stroke_width=0.7)


def answer_line(a: Point, b: Point) -> str:
    return draw.path(draw.polyline([a, b]), stroke=ANSWER, width=1.1, opacity=0.9, class_="key-line")


def ring_at(cx: float, cy: float, rx: float, ry: float, color: str = ANSWER, width: float = 1.0) -> str:
    return draw.el(
        "ellipse",
        cx=cx,
        cy=cy,
        rx=rx,
        ry=ry,
        fill="none",
        stroke=color,
        stroke_width=width,
        class_="key-ring",
    )


def svg(body: Sequence[str] | str, w: float = W, h: float = H, css: str = "wb") -> Markup:
    return draw.svg(w, h, body if isinstance(body, str) else "".join(body), css)
