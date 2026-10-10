"""«دوسية التأسيس» KG1 activities (Addendum 5 §3): coloring by area size and by color name (six colors), color
by code (letters and numbers), dot-to-dot to 5 and 10, the «me and my friends» drawing frame and the cut &
paste of pictures onto their shadows. Fewer, bigger items than KG2."""

from __future__ import annotations

import itertools
import math

from qamra_workbook.digits import DIGITS
from qamra_workbook.geometry import Stroke
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_activity2 import _inside
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    card,
    fit_lines,
    glyph,
    pic,
    ring_at,
    shape_of,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_pen import COLOR_WORDS, OUTLINES, crayon, dot_points
from qamra_workbook.render.registry import Built, PageContext, page_type

# the colors a KG1 child learns, each with things that are that color (drawn as line art to color)
COLOR_TABLE = {
    "أحمر": ("#E5604E", ("apple", "strawberry", "tomato")),
    "أزرق": ("#5E86D6", ("raindrop", "fish", "hat")),
    "أصفر": ("#F7C84A", ("sun", "banana", "corn")),
    "أخضر": ("#6FAE5F", ("leaf", "cucumber", "tree")),
    "برتقالي": ("#F28C28", ("orange", "carrot", "pumpkin")),
    "بنفسجي": ("#8E6BC0", ("grapes", "eggplant", "butterfly")),
}
AREA_POOL = ("butterfly", "house", "car", "fish", "flower", "cat", "duck", "kite", "umbrella", "rabbit")
CODE_COLORS: tuple[tuple[str, str], ...] = (
    ("#E5604E", "أحمر"),
    ("#5E86D6", "أزرق"),
    ("#F7C84A", "أصفر"),
    ("#6FAE5F", "أخضر"),
    ("#F28C28", "برتقالي"),
    ("#8E6BC0", "بنفسجي"),
)
HOUSE: list[tuple[float, float]] = [(93, 30), (160, 90), (160, 176), (26, 176), (26, 90)]  # a pointed roof
# ten dots: a fish facing left (nose, head, back, tail fin, belly), numbered round the outline; drawn a little
# smaller than the page so that the numbers at the tail stay inside the safe margin
_FISH = [(28, 100), (62, 62), (110, 52), (146, 72), (176, 44), (168, 100), (176, 156), (146, 128), (108, 148)]
_FISH.append((62, 138))
FISH = [(93 + (x - 93) * 0.88, 108 + (y - 108) * 0.95) for x, y in _FISH]
SHADOW = "#5B5E78"


def code_shape(char: str) -> Letter:
    """A legend code as a tracing shape: a digit in the page's numerals (Hindi digits are not letters), or
    a letter."""
    return DIGITS[char] if char in DIGITS else shape_of(char)


SHADOW_POOL = ("lion", "house", "car", "cow", "duck", "fish", "rabbit", "elephant")


@page_type("kg1-colors")
def kg1_colors(ctx: PageContext) -> Built:
    """A crayon and its color name, then three things of that color to color in (three rows a page)."""
    colors = [str(c) for c in ctx.page.params.get("colors", ["أحمر", "أصفر", "أزرق"])]
    problems = [f"no color row for «{c}»" for c in colors if c not in COLOR_TABLE]
    pitch = 204 / max(len(colors), 1)
    body, solved = [], []
    for i, name in enumerate([c for c in colors if c in COLOR_TABLE]):
        color, things = COLOR_TABLE[name]
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 5, r=7))
        body.append(crayon(W - 44, y + pitch / 2 - 10, color))
        body.append(text(COLOR_WORDS[name], W - 25, y + pitch / 2 + 9, 5.6, color=color))
        step = (W - 56) / len(things)  # the pictures share the card left of the crayon, inside its border
        size = min(pitch - 14, 50.0, step - 2)
        for k, thing in enumerate(things):
            x = W - 52 - (k + 1) * step + (step - size) / 2
            body.append(pic(thing, x, y + (pitch - 4) / 2 - size / 2, size, "line"))
            solved.append(pic(thing, x, y + (pitch - 4) / 2 - size / 2, size, "color", class_="key-ring"))
    answer = [
        f"{n}: " + "، ".join(PICTURES[t].word_ar for t in COLOR_TABLE[n][1])
        for n in colors
        if n in COLOR_TABLE
    ]
    return Built({"svg": svg(body + solved)}, answer, problems)


@page_type("kg1-coloring-area")
def kg1_coloring_area(ctx: PageContext) -> Built:
    """Color inside the borders: one big picture (large), four (small) or six (detailed), each with a small
    colored model to look at."""
    area = str(ctx.page.params.get("area", "large"))
    r = ctx.rng("area")
    count = {"large": 1, "small": 4, "detailed": 6}.get(area, 1)
    things = r.sample(AREA_POOL, count)
    cols = 1 if count == 1 else 2
    rows = (count + cols - 1) // cols
    cw, ch = W / cols, 204 / rows
    body = []
    for k, thing in enumerate(things):
        row, col = divmod(k, cols)
        x, y = W - (col + 1) * cw, row * ch
        body.append(card(x + 1, y + 1, cw - 3, ch - 3, r=7))
        size = min(cw - 10, ch - 10)
        body.append(pic(thing, x + (cw - size) / 2, y + (ch - size) / 2 + 2, size, "line"))
        model = 30.0 if count == 1 else 16.0
        body.append(card(x + cw - model - 6, y + 4, model + 3, model + 3, r=4, fill="#FFF6F2", stroke="none"))
        body.append(pic(thing, x + cw - model - 5, y + 5, model, "color"))
    return Built({"svg": svg(body)}, None, [])


OUTLINE_FIT = {  # outline → (scale, left, top) that put it in the picture area under the legend
    "heart": (1.4, 5.0, 28.0, 30.0, 46.0),
    "fish": (1.38, 2.0, 62.0, 28.0, 56.0),
}


def coded_picture(
    ctx: PageContext, codes: list[str], outline_key: str, cell: float, salt: str
) -> tuple[list[str], dict[str, int]]:
    """A picture (heart or fish) made of whole cells, each with one of the `codes`; the codes come round in
    turn so that every one has about the same number of cells. Only cells that fit entirely inside the outline
    are drawn: the edge never cuts a letter."""
    scale, left, top, x0, y0 = OUTLINE_FIT[outline_key]
    outline = Stroke(OUTLINES[outline_key])
    poly = [((x - x0) * scale + left, (y - y0) * scale + top) for x, y in outline.polyline]
    body = [draw.el("path", d=draw.polyline(poly) + " Z", fill="#FFFFFF", stroke=INK, stroke_width=1.2)]
    half = cell / 2
    sample = [(dx, dy) for dx in (-half, 0, half) for dy in (-half, 0, half)]
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    middle = (min(xs) + max(xs)) / 2
    spots = []
    for row in range(int((max(ys) - min(ys)) / cell) + 1):
        for k in range(-5, 6):
            cx, cy = middle + k * cell, min(ys) + half + row * cell
            if all(_inside(cx + dx, cy + dy, poly) for dx, dy in sample):
                spots.append((cx, cy))
    assigned = [codes[i % len(codes)] for i in range(len(spots))]
    ctx.rng(salt).shuffle(assigned)
    counts = dict.fromkeys(codes, 0)
    for (cx, cy), code in zip(spots, assigned, strict=True):
        counts[code] += 1
        body.append(
            draw.el(
                "rect",
                x=cx - half,
                y=cy - half,
                width=cell,
                height=cell,
                fill="none",
                stroke="#B8B2A6",
                stroke_width=0.35,
            )
        )
        shape = code_shape(code)
        body.append(glyph(shape, *fit_lines(shape, cx - 6.5, cy - 7, 13, 14), color=INK, width=13))
    body.append(draw.el("path", d=draw.polyline(poly) + " Z", fill="none", stroke=INK, stroke_width=1.2))
    return body, counts


def code_legend(ctx: PageContext, codes: list[str]) -> list[str]:
    """The legend band: each code, then its color, in its own slot (right to left)."""
    body = [card(0, 0, W, 24, r=7, fill=ctx.style.tint, stroke="none")]
    pitch = W / len(codes)
    for k, code in enumerate(codes):
        color, _ = CODE_COLORS[k]
        right = W - k * pitch
        shape = code_shape(code)
        body.append(glyph(shape, *fit_lines(shape, right - 19, 4, 14, 16), color=INK, width=14))
        body.append(draw.el("circle", cx=right - 26, cy=12, r=5, fill=color))
    return body


def code_answer(ctx: PageContext, codes: list[str], counts: dict[str, int]) -> list[str]:
    return ["، ".join(f"{c} {CODE_COLORS[k][1]} ({ctx.num(counts[c])})" for k, c in enumerate(codes))]


@page_type("kg1-color-by-code")
def kg1_color_by_code(ctx: PageContext) -> Built:
    """A heart made of big cells, each with a letter or a number; the legend gives each code a color."""
    letters = [str(c) for c in ctx.page.params.get("letters", ["أ", "ب", "ت"])][:3]
    numbers = [ctx.num(int(n)) for n in ctx.page.params.get("numbers", [1, 2, 3])][:3]
    codes = letters + numbers
    picture, counts = coded_picture(ctx, codes, "heart", 22.0, "code")
    problems = [] if all(counts.values()) else ["a code of the legend has no cell"]
    return Built({"svg": svg(code_legend(ctx, codes) + picture)}, code_answer(ctx, codes, counts), problems)


@page_type("kg1-color-by-letter")
def kg1_color_by_letter(ctx: PageContext) -> Built:
    """A fish made of big cells, each with one of the week's letters (four or five): a color for each."""
    letters = [str(c) for c in ctx.page.params.get("letters", ["ر", "ز", "س", "ش"])][:5]
    picture, counts = coded_picture(ctx, letters, "fish", 21.0, "letters")
    problems = [] if all(n >= 2 for n in counts.values()) else ["each letter needs at least two cells"]
    return Built(
        {"svg": svg(code_legend(ctx, letters) + picture)}, code_answer(ctx, letters, counts), problems
    )


# the six big pictures of the star-hunt scene (centre x, centre y) and the eight small spots between them
SCENE_BIG: tuple[tuple[float, float], ...] = ((30, 74), (93, 74), (156, 74), (30, 154), (93, 154), (156, 154))
SCENE_SPOTS: tuple[tuple[float, float, float], ...] = (
    (61.5, 74, 16),
    (124.5, 74, 16),
    (61.5, 154, 16),
    (124.5, 154, 16),
    (93, 114, 20),
    (30, 114, 15),
    (156, 114, 15),
    (93, 192, 17),
)
SCENE_THINGS = ("house", "tree", "car", "cat", "rabbit", "flower", "duck", "fish", "umbrella", "butterfly")
SCENE_SMALL = ("heart", "moon", "ball")


@page_type("kg1-hidden-stars")
def kg1_hidden_stars(ctx: PageContext) -> Built:
    """«أبحث عن النجوم المختبئة»: six big line-art pictures and, in the gaps between them, five small stars
    among a few hearts, moons and balls: find the stars and color them."""
    count = min(int(ctx.page.params.get("count", 5)), len(SCENE_SPOTS) - 2)
    r = ctx.rng("stars")
    body = [card(0, 0, W, 30, r=7, fill=ctx.style.tint, stroke="none")]
    body.append(pic("star", W - 28, 3, 24))
    body.append(
        text(f"أَبْحَثُ عَنْ {ctx.num(count)} نُجومٍ وَأُلَوِّنُها", W - 34, 18, 5.6, anchor="end", color=ctx.style.deep)
    )
    body.append(card(0, 34, W, 170, r=8))
    for (cx, cy), thing in zip(SCENE_BIG, r.sample(SCENE_THINGS, len(SCENE_BIG)), strict=True):
        body.append(pic(thing, cx - 20, cy - 20, 40, "line"))
    spots = list(SCENE_SPOTS)
    r.shuffle(spots)
    solved = []
    for k, (cx, cy, spot) in enumerate(spots):
        star = k < count
        body.append(
            pic(
                "star" if star else SCENE_SMALL[k % len(SCENE_SMALL)],
                cx - spot / 2,
                cy - spot / 2,
                spot,
                "line",
            )
        )
        if star:
            solved.append(ring_at(cx, cy, spot / 2 + 2, spot / 2 + 2))
    answer = [f"{ctx.num(count)} نجوم مخفية بين الصور الكبيرة"]
    return Built({"svg": svg(body + solved)}, answer, [])


@page_type("kg1-dot-to-dot")
def kg1_dot_to_dot(ctx: PageContext) -> Built:
    """Big numbered dots that draw a house (1–5), a star (1–10) or a fish (1–10, level 2); the picture they
    make is shown small in the corner, and the last dot joins the first."""
    to = int(ctx.page.params.get("to", 5))
    raw = str(ctx.page.params.get("level", 1))  # the plan's difficulty level, not the book's level (kg1)
    level = int(raw) if raw.isdigit() else 1
    if to <= 5:
        points, name, thing = HOUSE, "بيت", "house"
    elif level >= 2:
        points, name, thing = FISH, "سمكة", "fish"
    else:
        points, name, thing = dot_points(10), "نجمة", "star"
    body = [card(0, 0, W, 204, r=8)]
    body.append(card(6, 6, 34, 34, r=5, fill="#FFF6F2", stroke="none"))
    body.append(pic(thing, 7, 7, 32))
    for i, (x, y) in enumerate(points, start=1):
        dx, dy = x - 93, y - 108
        norm = math.hypot(dx, dy) or 1
        body.append(draw.start_dot((x, y), 3.6) if i == 1 else draw.el("circle", cx=x, cy=y, r=2.6, fill=INK))
        body.append(
            text(
                ctx.num(i),
                x + dx / norm * 10,
                y + dy / norm * 10 + 3.2,
                9,
                cls="wb-num",
                color=ctx.style.deep,
            )
        )
    body.append(text(f"ثُمَّ أَصِلُ {ctx.num(to)} بِالنُّقْطَةِ {ctx.num(1)}", W / 2, 196, 5, color="#676B83"))
    body.append(
        draw.path(draw.polyline([*points, points[0]]), stroke="#E0483A", width=1.1, class_="key-line")
    )
    gaps = [math.dist(a, b) for a, b in itertools.pairwise(points)]
    problems = [] if min(gaps) >= 8 else [f"two numbered dots are only {min(gaps):.1f} mm apart"]
    return Built({"svg": svg(body)}, [f"الصورة: {name}، النقاط من {ctx.num(1)} إلى {ctx.num(to)}"], problems)


@page_type("kg1-self-portrait")
def kg1_self_portrait(ctx: PageContext) -> Built:
    """A big frame to draw «me and my friends at kindergarten», with a sun and the ground already there."""
    body = [card(0, 0, W, 176, r=8, fill="#FFFFFF")]
    body.append(draw.el("circle", cx=W - 22, cy=22, r=11, fill="#FFF3B0", stroke="#E2A32A", stroke_width=0.8))
    body.append(draw.path(draw.d_path(("M", (6, 150)), ("L", (W - 6, 150))), stroke="#B8D9A0", width=1.2))
    body.append(text("أَنا وَأَصْدِقائي في الرَّوْضَةِ", W / 2, 168, 5.6, cls="wb-title", color=ctx.style.deep))
    body.append(card(0, 182, W, 22, r=6, fill="#FFFDF6", stroke="#D8C9AC", dash="2.4 1.6"))
    body.append(
        text(
            "أَصْدِقائي في الرَّسْمِ: ..............................................",
            W - 6,
            196,
            4.4,
            anchor="end",
            color="#676B83",
        )
    )
    return Built({"svg": svg(body)}, None, [])


def shadow(picture_id: str, x: float, y: float, size: float) -> str:
    picture = PICTURES[picture_id]
    dark = {part.fill: SHADOW for part in picture.parts}
    inner = picture.inner("color", dark).replace('fill="#FFFFFF"', f'fill="{SHADOW}"')
    return draw.el("svg", inner, x=x, y=y, width=size, height=size, viewBox="0 0 100 100")


@page_type("kg1-cut-shadows")
def kg1_cut_shadows(ctx: PageContext) -> Built:
    """The shadows on top in a shuffled order, two by two; the four pictures below, big enough for small
    hands to cut along the dashed lines and paste each over its shadow (one-sided: the back is blank)."""
    pieces = int(ctx.page.params.get("pieces", 4))
    r = ctx.rng("shadows")
    things = r.sample(SHADOW_POOL, pieces)
    order = list(range(pieces))
    while order == list(range(pieces)):
        r.shuffle(order)
    cw, ch, gap = 84.0, 38.0, 6.0
    size = ch - 6

    def cell(k: int, top: float) -> tuple[float, float]:
        row, col = divmod(k, 2)
        return W - 5 - (col + 1) * cw - col * gap, top + row * (ch + gap)

    rows = (pieces + 1) // 2
    cut_top = 12 + rows * (ch + gap) + 14
    body = [text("أُلْصِقُ كُلَّ صورَةٍ فَوْقَ ظِلِّها", W - 4, 8, 5, anchor="end", color=ctx.style.deep)]
    for k in range(pieces):
        x, y = cell(k, 12)
        body.append(card(x, y, cw, ch, r=5, fill="#FFF6F2", stroke="#D8C9AC", dash="2.4 1.6"))
        body.append(shadow(things[order[k]], x + (cw - size) / 2, y + 3, size))
        body.append(text(ctx.num(k + 1), x + cw - 8, y + 9, 6, cls="wb-num", color="#676B83"))
    body.append(text("أَقُصُّ عَلى الخَطِّ المُنَقَّطِ", W - 4, cut_top - 4, 5, anchor="end", color=ctx.style.deep))
    for k, thing in enumerate(things):
        x, y = cell(k, cut_top)
        body.append(card(x, y, cw, ch, r=0, fill="#FFFFFF", stroke=INK, dash="2 1.6", width=0.6))
        body.append(pic(thing, x + (cw - size) / 2, y + 3, size))
        body.append(ring_at(x + cw / 2, y + ch / 2, size / 2 + 3, size / 2 + 3))
    answer = [
        "، ".join(f"{PICTURES[t].word_ar} ← الظل {ctx.num(order.index(i) + 1)}" for i, t in enumerate(things))
    ]
    return Built({"svg": svg(body)}, answer, [] if cut_top + rows * (ch + gap) <= 206 else ["too tall"])
