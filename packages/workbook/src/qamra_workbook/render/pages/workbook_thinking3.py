"""«دوسية التأسيس» Volume 3 thinking pages: growing patterns, a picture grid with no repeats in a row or
column, sorting by two attributes in a table, remembering an order, cause and effect, the year's mixed
matching page, and drawing a solution to a problem."""

from __future__ import annotations

from qamra_workbook.pictures import PICTURES
from qamra_workbook.puzzles.coloring import Shape
from qamra_workbook.render import draw
from qamra_workbook.render.pages.thinking import SHAPE_COLORS, shape_kind
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    answer_line,
    card,
    fit_lines,
    glyph,
    hook,
    pic,
    shape_of,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_math2 import numeral_any
from qamra_workbook.render.pages.workbook_math3 import group_pics, key_wrap
from qamra_workbook.render.pages.workbook_thinking import POOL, _deranged
from qamra_workbook.render.registry import Built, PageContext, page_type

CAUSES = (
    ("raindrop", "umbrella"),
    ("sun", "hat"),
    ("bee", "honey"),
    ("hen", "egg"),
    ("seed", "tree"),
)  # no picture appears twice, so every link has one answer


@page_type("growing-pattern")
def growing_pattern(ctx: PageContext) -> Built:
    """Rows where each step adds one: dots, then stars, then blocks; the child draws the next two steps."""
    r = ctx.rng("growing")
    body, answer = [], []
    kinds = ("circle", "star", "square", "triangle")
    for i in range(4):
        y = i * 51
        start = 1 + (i % 2)
        body.append(card(0, y + 1, W, 47, r=7))
        for k in range(5):
            n = start + k
            cx = W - (k + 0.5) * W / 5
            if k < 3:
                for j in range(n):
                    body.append(
                        draw.shape(
                            Shape(shape_kind(kinds[i]), cx, y + 40 - j * 8, 6, 6),
                            fill=SHAPE_COLORS.get(kinds[i], "#F7C84A"),
                            width=0.6,
                        )
                    )
            else:
                body.append(
                    card(cx - 14, y + 6, 28, 38, r=4, fill="#FFFFFF", stroke=ctx.style.color, dash="2 1.4")
                )
                for j in range(n):
                    body.append(
                        draw.shape(
                            Shape(shape_kind(kinds[i]), cx, y + 40 - j * 6.5, 5, 5), fill="#E0483A", width=0.5
                        )
                        .replace("<path ", '<path class="key-ring" ', 1)
                        .replace("<ellipse ", '<ellipse class="key-ring" ', 1)
                        .replace("<rect ", '<rect class="key-ring" ', 1)
                    )
        answer.append(f"الصف {ctx.num(i + 1)}: {ctx.num(start + 3)} ثم {ctx.num(start + 4)}")
    del r
    return Built({"svg": svg(body)}, answer, [])


def completions(grid: list[list[int]], blanks: set[tuple[int, int]], size: int, limit: int = 2) -> int:
    """How many ways the blank cells of a latin square can be filled so no picture repeats in a row or a
    column (stops counting at `limit`): the child's grid has one answer when this is 1."""
    cells = sorted(blanks)
    cur = [[-1 if (a, b) in blanks else grid[a][b] for b in range(size)] for a in range(size)]

    def fill(k: int) -> int:
        if k == len(cells):
            return 1
        a, b = cells[k]
        total = 0
        for v in range(size):
            if all(cur[a][j] != v for j in range(size)) and all(cur[i][b] != v for i in range(size)):
                cur[a][b] = v
                total += fill(k + 1)
                cur[a][b] = -1
                if total >= limit:
                    break
        return total

    return fill(0)


@page_type("picture-grid")
def picture_grid(ctx: PageContext) -> Built:
    """A 4 × 4 grid: each picture once per row and column; some cells empty to fill (a picture sudoku with
    exactly one way to finish it)."""
    size = int(ctx.page.params.get("size", 4))
    r = ctx.rng("grid")
    things = r.sample(("apple", "duck", "star", "ball", "fish", "flower"), size)
    base = [[(row + col) % size for col in range(size)] for row in range(size)]
    r.shuffle(base)
    perm = list(range(size))
    r.shuffle(perm)
    grid = [[perm[v] for v in row] for row in base]
    cells = [(a, b) for a in range(size) for b in range(size)]
    blanks = set(r.sample(cells, size * 2))
    for _ in range(400):  # keep drawing blanks until the picture-sudoku has one answer
        if completions(grid, blanks, size) == 1:
            break
        blanks = set(r.sample(cells, size * 2))
    cell = min((W - 10) / size, 180 / size)
    x0, y0 = (W - cell * size) / 2, 8.0
    body = [card(x0 - 4, y0 - 4, cell * size + 8, cell * size + 8, r=7)]
    answer = []
    for a in range(size):
        for b in range(size):
            x, y = x0 + b * cell, y0 + a * cell
            body.append(
                draw.el(
                    "rect",
                    x=x,
                    y=y,
                    width=cell,
                    height=cell,
                    fill="#FFFFFF",
                    stroke="#D8C9AC",
                    stroke_width=0.5,
                )
            )
            thing = things[grid[a][b]]
            if (a, b) in blanks:
                body.append(pic(thing, x + cell * 0.2, y + cell * 0.2, cell * 0.6, class_="key-ring"))
                answer.append(f"الصف {ctx.num(a + 1)} العمود {ctx.num(b + 1)}: {PICTURES[thing].word_ar}")
            else:
                body.append(pic(thing, x + cell * 0.12, y + cell * 0.12, cell * 0.76))
    body.append(text("كل صورة مرة واحدة في كل صف وعمود", W / 2, 196, 4.8, color=ctx.style.deep))
    answer = answer[:3]
    problems = (
        []
        if all(len(set(row)) == size for row in grid)
        and all(len({grid[a][b] for a in range(size)}) == size for b in range(size))
        and completions(grid, blanks, size) == 1
        else ["the grid repeats a picture, or has more than one way to finish"]
    )
    return Built({"svg": svg(body)}, answer, problems)


@page_type("classify-table")
def classify_table(ctx: PageContext) -> Built:
    """Shapes sorted by colour (rows) and shape (columns): draw each shape where it belongs."""
    colors = (("#E5604E", "أحمر"), ("#5E86D6", "أزرق"), ("#6FAE5F", "أخضر"))
    kinds = ("circle", "square", "triangle")
    r = ctx.rng("table")
    y0, cw, ch = 30.0, (W - 16 - 30) / 3, 40.0
    body = [card(0, 0, W, 204, r=7)]
    for k, kind in enumerate(kinds):
        cx = W - 30 - (k + 0.5) * cw
        body.append(draw.shape(Shape(shape_kind(kind), cx, y0 - 12, 12, 12), fill="#FFFFFF", width=0.9))
    for j, (color, name) in enumerate(colors):
        cy = y0 + (j + 0.5) * ch
        body.append(draw.el("circle", cx=W - 18, cy=cy, r=6, fill=color, stroke=INK, stroke_width=0.5))
        body.append(text(name, W - 18, cy + 11, 3.6, color=INK))
        for k, kind in enumerate(kinds):
            x = W - 30 - (k + 1) * cw
            body.append(
                draw.el(
                    "rect",
                    x=x,
                    y=y0 + j * ch,
                    width=cw,
                    height=ch,
                    fill="#FFFFFF",
                    stroke="#D8C9AC",
                    stroke_width=0.5,
                )
            )
            body.append(
                draw.shape(Shape(shape_kind(kind), x + cw / 2, cy, 14, 14), fill=color, width=0.8)
                .replace("<path ", '<path class="key-ring" ', 1)
                .replace("<ellipse ", '<ellipse class="key-ring" ', 1)
                .replace("<rect ", '<rect class="key-ring" ', 1)
            )
    y = y0 + 3 * ch + 8
    body.append(
        text("هذه الأشكال: أرسم كل شكل في مكانه بلونه", W - 8, y + 6, 4.8, anchor="end", color=ctx.style.deep)
    )
    items = [(kind, color) for kind in kinds for color, _ in colors]
    r.shuffle(items)
    for k, (kind, color) in enumerate(items):
        cx = W - 10 - (k + 0.5) * (W - 20) / len(items)
        body.append(draw.shape(Shape(shape_kind(kind), cx, y + 24, 12, 12), fill=color, width=0.8))
    return Built({"svg": svg(body)}, ["كل شكل في صف لونه وعمود شكله"], [])


@page_type("memory-order")
def memory_order(ctx: PageContext) -> Built:
    """Five pictures to remember in order (numbered, from the right); under the fold, the same five shuffled,
    each with a box to write its number in."""
    count = int(ctx.page.params.get("items", 5))
    r = ctx.rng("order")
    seen = r.sample(POOL, count)
    body = [card(0, 0, W, 72, r=8, fill="#FFF6F2")]
    body.append(text("أنظر إلى الترتيب وأتذكّره", W - 8, 11, 5.2, anchor="end", color=ctx.style.deep))
    step = (W - 16) / count
    for k, thing in enumerate(seen):
        cx = W - 8 - (k + 0.5) * step
        body.append(pic(thing, cx - 15, 18, 30))
        body.append(draw.el("circle", cx=cx, cy=59, r=5.5, fill=ctx.style.color))
        body.append(text(ctx.num(k + 1), cx, 61.2, 6, cls="wb-num", color="#FFFFFF"))
    body.append(
        draw.path(
            draw.d_path(("M", (2, 80)), ("L", (W - 2, 80))),
            stroke="#B8B2A6",
            width=0.7,
            stroke_dasharray="3 2",
        )
    )
    body.append(
        text(
            "أغطّي الصور، ثم أكتب رقم كل صورة حسب ترتيبها", W - 8, 92, 5.2, anchor="end", color=ctx.style.deep
        )
    )
    order = _deranged(r, count)
    shuffled = [seen[i] for i in order]
    body.append(card(0, 98, W, 106, r=7))
    step = (W - 8) / count
    for k, thing in enumerate(shuffled):
        cx = W - 4 - (k + 0.5) * step
        body.append(pic(thing, cx - 15, 120, 30))
        body.append(
            draw.el(
                "rect",
                x=cx - 10,
                y=160,
                width=20,
                height=22,
                rx=3.5,
                fill="#FFFFFF",
                stroke="#B8B2A6",
                stroke_width=0.6,
                stroke_dasharray="2 1.4",
            )
        )
        body.append(key_wrap(numeral_any(ctx, seen.index(thing) + 1, cx, 171, 13, "#E0483A")))
    answer = ["الترتيب: " + "، ".join(PICTURES[t].word_ar for t in seen)]
    return Built({"svg": svg(body)}, answer, [])


@page_type("cause-effect")
def cause_effect(ctx: PageContext) -> Built:
    count = int(ctx.page.params.get("pairs", 4))
    r = ctx.rng("cause")
    pairs = [p for p in CAUSES if p[0] in PICTURES and p[1] in PICTURES]
    pairs = r.sample(pairs, min(count, len(pairs)))
    order = _deranged(r, len(pairs))
    pitch = 204 / len(pairs)
    size = min(40.0, pitch - 8)
    body, key = [], []
    for i, (cause, effect) in enumerate(pairs):
        y = i * pitch + pitch / 2
        body.append(card(W - size - 10, y - size / 2 - 2, size + 8, size + 4, r=6))
        body.append(pic(cause, W - size - 6, y - size / 2, size))
        body.append(hook(W - size - 14, y))
        j = order[i]
        yj = j * pitch + pitch / 2
        body.append(card(2, yj - size / 2 - 2, size + 8, size + 4, r=6))
        body.append(pic(effect, 6, yj - size / 2, size))
        body.append(hook(size + 14, yj))
        key.append(answer_line((W - size - 14, y), (size + 14, yj)))
    answer = [f"{PICTURES[a].word_ar} ← {PICTURES[b].word_ar}" for a, b in pairs]
    return Built({"svg": svg(body + key)}, answer, [])


@page_type("mixed-connect")
def mixed_connect(ctx: PageContext) -> Built:
    """The year on one page: a letter to its picture, a number to its group, an English word to its."""
    r = ctx.rng("mixed")
    left_items: list[tuple[str | int, str]] = [
        ("ب", "duck"),
        ("س", "fish"),
        (3, "apple"),
        (7, "star"),
        ("cat", "cat"),
        ("sun", "sun"),
    ]
    order = _deranged(r, len(left_items))
    pitch = 204 / len(left_items)
    body, key = [], []
    for i, (label, thing) in enumerate(left_items):
        y = i * pitch + pitch / 2
        body.append(card(W - 44, y - 13, 40, 26, r=5, fill=ctx.style.tint, stroke="none"))
        if isinstance(label, int):
            body.append(numeral_any(ctx, label, W - 24, y, 16, ctx.style.deep))
        elif label.isascii():
            body.append(text(label, W - 24, y + 3, 8, cls="wb-en", color=ctx.style.deep, rtl=False))
        else:
            shape = shape_of(label)
            body.append(
                glyph(shape, *fit_lines(shape, W - 36, y - 10, 24, 20), color=ctx.style.deep, width=14)
            )
        body.append(hook(W - 48, y))
        j = order[i]
        yj = j * pitch + pitch / 2
        body.append(card(4, yj - 14, 60, 28, r=5))
        if isinstance(label, int):
            body.append(group_pics(thing, label, 6, yj - 12, 56, 24))
        else:
            body.append(pic(thing, 22, yj - 12, 24))
        body.append(hook(68, yj))
        key.append(answer_line((W - 48, y), (68, yj)))
    return Built({"svg": svg(body + key)}, ["كل شيء بما يناسبه"], [])


@page_type("problem-drawing")
def problem_drawing(ctx: PageContext) -> Built:
    """A river between the duck and its pond: draw how it crosses (a bridge, a boat…), then tell why."""
    body = [card(0, 0, W, 204, r=8)]
    body.append(draw.el("rect", x=0, y=0, width=W, height=204, rx=8, fill="#EEF6E8"))
    body.append(
        draw.el(
            "path",
            d=draw.d_path(
                ("M", (70, 0)),
                ("C", (60, 60, 110, 120, 96, 204)),
                ("L", (128, 204)),
                ("C", (140, 120, 92, 60, 104, 0)),
            )
            + " Z",
            fill="#8EC1EC",
        )
    )
    body.append(pic("duck", 18, 80, 44))
    body.append(pic("tree", 140, 20, 40))
    body.append(pic("flower", 146, 130, 28))
    body.append(card(W - 100, 184, 96, 16, r=8, fill="#FFFFFF", stroke="none"))
    body.append(
        text(
            "كيف تعبر البطة إلى الضفة الأخرى؟ أرسم الحلّ", W - 8, 194.2, 5, anchor="end", color=ctx.style.deep
        )
    )
    return Built({"svg": svg(body)}, ["أي حلّ معقول: جسر، قارب، طوف من الأغصان…"], [])
