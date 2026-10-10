"""«دوسية التأسيس» thinking and activity pages (Addendum 5 §3): connect matching pictures (or pictures with
the same first sound), sort into groups, look and remember, cut and paste a picture's pieces, and complete the
missing half of a drawing. Each page has an answer key and checks that the puzzle has exactly one answer."""

from __future__ import annotations

import random

from qamra_workbook.pictures import PICTURES
from qamra_workbook.puzzles.coloring import Shape, ShapeKind
from qamra_workbook.render import art, draw
from qamra_workbook.render.pages.workbook_arabic import first_letter, same_letter
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    answer_line,
    card,
    fit_lines,
    for_child,
    glyph,
    hook,
    pic,
    picture_id,
    ring_at,
    shape_of,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_find import words_starting
from qamra_workbook.render.pages.workbook_pen import COLOR_ROWS, COLOR_WORDS
from qamra_workbook.render.registry import Built, PageContext, page_type

POOL = (
    "apple",
    "duck",
    "cat",
    "car",
    "sun",
    "fish",
    "ball",
    "flower",
    "rabbit",
    "house",
    "star",
    "tree",
    "bee",
    "butterfly",
    "banana",
    "cow",
    "sheep",
    "umbrella",
)


def _deranged(r: random.Random, n: int) -> list[int]:
    order = list(range(n))
    for _ in range(60):
        r.shuffle(order)
        if all(i != j for i, j in enumerate(order)):
            break
    return order


def two_columns(right: list[str], left: list[str], order: list[int]) -> tuple[list[str], list[str]]:
    """Picture cards in two columns with hooks; `order[i]` is the left row that matches right row i."""
    n = len(right)
    pitch = 204 / n
    size = min(40.0, pitch - 8)
    body, key = [], []
    for i in range(n):
        y = i * pitch + pitch / 2
        body.append(card(W - size - 10, y - size / 2 - 2, size + 8, size + 4, r=6))
        body.append(pic(right[i], W - size - 6, y - size / 2, size))
        body.append(hook(W - size - 14, y))
        body.append(card(2, y - size / 2 - 2, size + 8, size + 4, r=6))
        body.append(pic(left[i], 6, y - size / 2, size))
        body.append(hook(size + 14, y))
    for i, j in enumerate(order):
        key.append(answer_line((W - size - 14, i * pitch + pitch / 2), (size + 14, j * pitch + pitch / 2)))
    return body, key


@page_type("connect")
def connect(ctx: PageContext) -> Built:
    params = ctx.page.params
    r = ctx.rng("connect")
    words = [picture_id(str(w)) for w in params.get("words", [])]
    problems = []
    if words:  # pairs of pictures with the same first sound: (سمكة، سيارة), (فيل، فراشة) …
        right, partners = words[0::2], words[1::2]
        for a, b in zip(right, partners, strict=True):
            if not same_letter(first_letter(PICTURES[a].word_ar), first_letter(PICTURES[b].word_ar)):
                problems.append(f"{a} and {b} do not start with the same sound")
    else:
        count = int(params.get("pairs", 4))
        right = r.sample(POOL, count)
        partners = list(right)
    order = _deranged(r, len(right))
    left = [""] * len(right)
    for i, j in enumerate(order):
        left[j] = partners[i]
    body, key = two_columns(right, left, order)
    answer = [f"{PICTURES[a].word_ar} ← {PICTURES[b].word_ar}" for a, b in zip(right, partners, strict=True)]
    return Built({"svg": svg(body + key)}, answer, problems)


@page_type("classify")
def classify(ctx: PageContext) -> Built:
    """Pictures on top, groups below (a basket per color, or a house per letter); a line from each picture to
    its group."""
    params = ctx.page.params
    r = ctx.rng("classify")
    letters = [str(x) for x in params.get("letters", [])]
    items: list[tuple[str, int]] = []
    groups: list[str] = []
    if letters:
        for g, t in enumerate(letters):
            planned = [
                picture_id(str(w)) for w in params.get("words", []) if same_letter(first_letter(str(w)), t)
            ]
            extra = [w for w in words_starting(t) if w not in planned]
            items += [(w, g) for w in (planned + extra)[:2]]
        groups = letters
    else:
        names = ["أحمر", "أصفر"]
        for g, name in enumerate(names):
            items += [(w, g) for w in r.sample(COLOR_ROWS[name][1], 3)]
        groups = names
    r.shuffle(items)
    body, key = [], []
    per_row = (len(items) + 1) // 2
    step = W / per_row
    for k, (thing, _) in enumerate(items):
        row, col = divmod(k, per_row)
        cx, cy = W - (col + 0.5) * step, 24 + row * 50
        body.append(card(cx - 21, cy - 21, 42, 42, r=6))
        body.append(pic(thing, cx - 18, cy - 18, 36))
        body.append(hook(cx, cy + 24))
    gw = W / len(groups)
    anchors = []
    for g, name in enumerate(groups):
        cx = W - (g + 0.5) * gw
        body.append(card(cx - gw / 2 + 5, 150, gw - 10, 52, r=8, fill="#FFF6F2"))
        if letters:
            shape = shape_of(name)
            body.append(glyph(shape, *fit_lines(shape, cx - 14, 160, 28, 34), color=ctx.style.deep, width=15))
        else:
            color = COLOR_ROWS[name][0]
            body.append(
                draw.el(
                    "path",
                    d=draw.d_path(
                        ("M", (cx - 26, 168)),
                        ("L", (cx + 26, 168)),
                        ("L", (cx + 20, 196)),
                        ("L", (cx - 20, 196)),
                    )
                    + " Z",
                    fill=color,
                    stroke=INK,
                    stroke_width=0.8,
                    stroke_linejoin="round",
                )
            )
            body.append(text(COLOR_WORDS[name], cx, 186, 6, color=INK if name == "أصفر" else "#FFFFFF"))
        anchors.append((cx, 152))
        body.append(hook(cx, 150))
    for k, (_, g) in enumerate(items):
        row, col = divmod(k, per_row)
        key.append(answer_line((W - (col + 0.5) * step, 24 + row * 50 + 24), anchors[g]))
    answer = [
        f"{groups[g]}: " + "، ".join(PICTURES[w].word_ar for w, h in items if h == g)
        for g in range(len(groups))
    ]
    problems = [
        f"group {name} has no picture" for g, name in enumerate(groups) if all(h != g for _, h in items)
    ]
    return Built({"svg": svg(body + key)}, answer, problems)


@page_type("memory")
def memory(ctx: PageContext) -> Built:
    """Look at the pictures, cover them (fold along the line), then circle the ones you saw below."""
    count = int(ctx.page.params.get("items", 4))
    r = ctx.rng("memory")
    seen = r.sample(POOL, count)
    shown = seen + r.sample([p for p in POOL if p not in seen], count)
    r.shuffle(shown)
    body = [card(0, 0, W, 78, r=8, fill="#FFF6F2")]
    body.append(text("أَنْظُرُ جَيِّدًا وَأَتَذَكَّرُ", W - 8, 10, 5, anchor="end", color=ctx.style.deep))
    step = (W - 20) / count
    for k, thing in enumerate(seen):
        body.append(pic(thing, W - 10 - (k + 1) * step + (step - 42) / 2, 20, 42))
    body.append(
        draw.path(
            draw.d_path(("M", (2, 86)), ("L", (W - 2, 86))),
            stroke="#B8B2A6",
            width=0.7,
            stroke_dasharray="3 2",
        )
    )
    body.append(text("أُغَطّي الصُّوَرَ بِوَرَقَةٍ، ثُمَّ أُحَوِّطُ ما رَأَيْتُ", W - 8, 98, 5, anchor="end", color=ctx.style.deep))
    per_row = count
    step = W / per_row
    for k, thing in enumerate(shown):
        row, col = divmod(k, per_row)
        cx, cy = W - (col + 0.5) * step, 128 + row * 50
        body.append(card(cx - 21, cy - 21, 42, 42, r=6))
        body.append(pic(thing, cx - 18, cy - 18, 36))
        if thing in seen:
            body.append(ring_at(cx, cy, 24, 24))
    problems = [] if sorted(set(shown)) == sorted(shown) else ["a picture repeats among the choices"]
    return Built(
        {"svg": svg(body)},
        [for_child(ctx, "{رأى الطفل/رأت الطفلة}: ") + "، ".join(PICTURES[t].word_ar for t in seen)],
        problems,
    )


@page_type("cut-and-paste")
def cut_and_paste(ctx: PageContext) -> Built:
    """A picture cut into pieces along printed cut lines; the frame above shows where each piece goes (a faint
    outline and a matching shape in each corner). One-sided: the back of the sheet is blank."""
    pieces = int(ctx.page.params.get("pieces", 4))
    r = ctx.rng("cut")
    thing = str(ctx.page.params.get("picture", r.choice(("lion", "house", "car", "cow"))))
    grid = 2 if pieces == 4 else 3
    marks: tuple[ShapeKind, ...] = (
        "circle",
        "triangle",
        "square",
        "heart",
        "star",
        "diamond",
        "circle",
        "triangle",
        "square",
    )
    size, x0, y0 = 104.0, (W - 104) / 2, 4.0
    cell = size / grid
    body = [card(x0 - 4, y0 - 2, size + 8, size + 6, r=6, fill="#FFFFFF")]
    faint = PICTURES[thing].inner("line")
    body.append(
        f'<svg x="{x0}" y="{y0}" width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'opacity="0.18">{faint}</svg>'
    )

    def mark(kind: ShapeKind, cx: float, cy: float, fill: str) -> str:
        return draw.shape(Shape(kind, cx, cy, 5, 5), fill=fill, width=0.5)

    colors = (
        "#EE8A6E",
        "#5E86D6",
        "#7DB46C",
        "#F2B33D",
        "#E97A98",
        "#A99BD6",
        "#EE8A6E",
        "#5E86D6",
        "#7DB46C",
    )
    for i in range(grid * grid):
        row, col = divmod(i, grid)
        x, y = x0 + col * cell, y0 + row * cell
        body.append(
            draw.el(
                "rect",
                x=x,
                y=y,
                width=cell,
                height=cell,
                fill="none",
                stroke="#B8B2A6",
                stroke_width=0.5,
                stroke_dasharray="2 1.5",
            )
        )
        body.append(mark(marks[i], x + 5, y + 5, colors[i]))
    order = _deranged(r, grid * grid)
    body.append(text("أَقُصُّ عَلى الخَطِّ المُتَقَطِّعِ", W - 8, 124, 4.8, anchor="end", color=ctx.style.deep))
    per_row = 4 if grid == 2 else 5
    pw = min(38.0, (W - 8) / per_row - 8)
    unit = 100 / grid
    inner = PICTURES[thing].inner("color")
    for k, i in enumerate(order):
        row, col = divmod(i, grid)
        line, slot = divmod(k, per_row)
        x = W - (slot + 1) * (pw + 8) + 4
        y = 134.0 + line * (pw + 10)
        body.append(
            draw.el(
                "rect",
                x=x - 3,
                y=y - 3,
                width=pw + 6,
                height=pw + 6,
                fill="none",
                stroke=INK,
                stroke_width=0.6,
                stroke_dasharray="2.4 1.6",
            )
        )
        view = f"{col * unit} {row * unit} {unit} {unit}"
        body.append(
            f'<svg x="{draw.n(x)}" y="{draw.n(y)}" width="{draw.n(pw)}" height="{draw.n(pw)}" '
            f'viewBox="{view}" '
            f'style="overflow: hidden" data-piece="{i}">{inner}</svg>'
        )
        body.append(mark(marks[i], x + 4, y + 4, colors[i]))
    body.append(
        draw.el("svg", art.glyph("scissors", INK, 1.8), x=4, y=117, width=9, height=9, viewBox="0 0 24 24")
    )
    problems = (
        [] if sorted(order) == list(range(grid * grid)) else ["the pieces do not make the whole picture"]
    )
    answer = [f"الصورة: {PICTURES[thing].word_ar}؛ كل قطعة في المربّع الذي يحمل الشكل نفسه"]
    return Built({"svg": svg(body)}, answer, problems)


# symmetric drawings on a dot grid (columns 0–8, rows 0–10; the mirror line is column 4): the right half
SYMMETRY = {
    "house": [
        [(4, 1), (8, 5), (7, 5), (7, 10), (4, 10)],
        [(5, 10), (5, 7), (6, 7), (6, 10)],
        [(6, 6), (6, 5)],
    ],
    "tree": [[(4, 0), (7, 3), (6, 3), (8, 6), (5, 6), (5, 9), (4, 9)]],
    "rocket": [[(4, 0), (6, 3), (6, 8), (8, 10), (4, 10)], [(5, 4), (5, 5)]],
}


@page_type("symmetry-drawing")
def symmetry_drawing(ctx: PageContext) -> Built:
    """Half a drawing on a dot grid; the child draws the other half the same, across the mirror line."""
    name = str(ctx.page.params.get("shape", "house"))
    halves = SYMMETRY[name]
    gap, x0, y0 = 16.0, W / 2 - 4 * 16.0, 16.0

    def at(c: float, r: float) -> tuple[float, float]:
        return x0 + c * gap, y0 + r * gap

    body = [card(0, 0, W, 204, r=8)]
    for c in range(9):
        for r in range(11):
            x, y = at(c, r)
            body.append(draw.el("circle", cx=x, cy=y, r=0.9, fill="#9A94A8"))
    axis = draw.d_path(("M", at(4, -0.6)), ("L", at(4, 10.6)))
    body.append(draw.path(axis, stroke=ctx.style.color, width=0.8, stroke_dasharray="3 2"))
    key = []
    for line in halves:
        body.append(draw.path(draw.polyline([at(c, r) for c, r in line]), stroke=INK, width=1.6))
        key.append(
            draw.path(
                draw.polyline([at(8 - c, r) for c, r in line]),
                stroke="#E0483A",
                width=1.3,
                stroke_dasharray="2 1.4",
                class_="key-line",
            )
        )
    body.append(draw.start_dot(at(*halves[0][0]), 2.2))
    problems = (
        [] if all(0 <= c <= 8 and 0 <= r <= 10 for line in halves for c, r in line) else ["off the grid"]
    )
    return Built({"svg": svg(body + key)}, ["النصف الأيسر مثل الأيمن تمامًا، كأنه في مرآة"], problems)
