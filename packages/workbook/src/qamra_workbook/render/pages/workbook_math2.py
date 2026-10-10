"""«دوسية التأسيس» Volume 2 math: the numbers 6–10 (Addendum 5 §3), the same steps as 1–5 (meet → trace →
write → count and circle → number ↔ quantity → compare) with groups of up to ten (a ten as two rows of five,
the ten-frame children meet in Grade 1) and 10 written as two digits. The number train orders 1–10.

Registered under `…-ten` names; `foundation_v2` routes a plan page here when its numbers go past 5.
"""

from __future__ import annotations

from qamra_workbook.digits import digit_shapes
from qamra_workbook.puzzles.counting import LAYOUTS
from qamra_workbook.render import draw
from qamra_workbook.render.foundation_text import NUMBER_NAMES
from qamra_workbook.render.pages.letters import dotted_letter, tracing_row
from qamra_workbook.render.pages.workbook_arabic import big_track, row_svg
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    card,
    fit_lines,
    glyph,
    pic,
    ring_at,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES, _counts
from qamra_workbook.render.registry import Built, PageContext, page_type

Point = tuple[float, float]


def _grid(cols: int, rows: int, count: int) -> tuple[Point, ...]:
    cells = [((c + 0.5) / cols, (r + 0.5) / rows) for r in range(rows) for c in range(cols)]
    return tuple(cells[:count])


# layouts in a unit square: the dice faces up to 5, then rows of three, four and five (a ten-frame for 10)
LAYOUTS10: dict[int, tuple[Point, ...]] = {
    **LAYOUTS,
    6: _grid(3, 2, 6),
    7: (*_grid(4, 2, 4), *(((c + 1) / 4, 0.75) for c in range(3))),  # 4 + 3: none sits on another
    8: _grid(4, 2, 8),
    9: _grid(3, 3, 9),
    10: _grid(5, 2, 10),
}


def layout10(count: int) -> tuple[Point, ...]:
    try:
        return LAYOUTS10[count]
    except KeyError:
        raise ValueError(f"counting pages show 1–10 things, not {count}") from None


def group_any(picture: str, count: int, x: float, y: float, w: float, h: float) -> str:
    """`count` pictures (0–10) in a box; every picture is tagged for the quantity checks."""
    if count == 0:
        return f'<g data-count="0" data-picture="{picture}"></g>'
    cols = {6: 3, 7: 4, 8: 4, 9: 3, 10: 5}.get(count, 2)
    rows = {6: 2, 7: 2, 8: 2, 9: 3, 10: 2}.get(count, 2)
    size = min(w / cols, h / rows) * (0.62 if count <= 2 else 0.5 if count <= 5 else 0.8)
    items = "".join(
        pic(picture, x + u * w - size / 2, y + v * h - size / 2, size, data_count_item=picture)
        for u, v in layout10(count)
    )
    return f'<g data-count="{count}" data-picture="{picture}">{items}</g>'


def numeral_any(ctx: PageContext, n: int, cx: float, cy: float, h: float, color: str = INK) -> str:
    """A number of one or two digits drawn in Qamra's hand, centred at (cx, cy), `h` mm tall."""
    shapes = digit_shapes(n, ctx.numerals)
    w = h * 0.62
    total = w * len(shapes) + 2 * (len(shapes) - 1)
    out = []
    for k, shape in enumerate(shapes):
        x = cx - total / 2 + k * (w + 2)
        out.append(glyph(shape, *fit_lines(shape, x, cy - h / 2, w, h), color=color, width=13))
    return "".join(out)


def stars(n: int, x: float, y: float, w: float) -> str:
    """Ten star outlines in two rows of five (the child colours `n`); tagged with the count to colour."""
    out = []
    for k in range(10):
        cx = x + w - (k % 5 + 0.5) * w / 5
        cy = y + 9 + (k // 5) * 18
        out.append(
            draw.el(
                "path",
                d=draw.star_points(cx, cy, 8, 3.6),
                fill="#FFFFFF",
                stroke=INK,
                stroke_width=0.7,
                stroke_linejoin="round",
            )
        )
    return f'<g data-stars="{n}">{"".join(out)}</g>'


@page_type("number-intro-ten")
def number_intro_ten(ctx: PageContext) -> Built:
    n = int(ctx.page.params.get("number", 6))
    r = ctx.rng("intro")
    thing = GROUP_PICTURES[n % len(GROUP_PICTURES)]
    body = [card(0, 0, W, 96, r=8)]
    shapes = digit_shapes(n, ctx.numerals)
    dw = 62.0 if len(shapes) == 1 else 34.0
    for k, shape in enumerate(shapes):
        scale, dx, dy = fit_lines(shape, W - 72 + k * (dw + 4) - (0 if len(shapes) == 1 else 2), 6, dw, 70)
        body.append(glyph(shape, scale, dx, dy, color=ctx.style.color, width=17))
        from qamra_workbook.render.pages.workbook_common import start_marks

        body.append(start_marks(shape, scale, dx, dy, 3, ctx.num))
    body.append(text(NUMBER_NAMES[n], W - 40, 90, 8.5, cls="wb-word", color=ctx.style.deep))
    body.append(card(6, 6, 100, 66, r=6, fill="#FFF6F2", stroke="none"))
    body.append(group_any(thing, n, 9, 8, 94, 62))
    for k in range(10):
        cx, cy = 18.0 + (k % 5) * 18, 80.0 + (k // 5) * 9
        body.append(
            draw.el(
                "circle",
                cx=cx,
                cy=cy,
                r=3.6,
                fill=ctx.style.color if k < n else "#FFFFFF",
                stroke=ctx.style.deep,
                stroke_width=0.5,
            )
        )
    body.append(card(0, 102, W, 52, r=7))
    body.append(text(f"أُلَوِّنُ {ctx.num(n)} نُجومٍ", W - 8, 113, 5.2, anchor="end", color=ctx.style.deep))
    body.append(stars(n, 8, 116, W - 16))
    body.append(card(0, 160, W, 44, r=7))
    body.append(text(f"أُحَوِّطُ العَدَدَ {ctx.num(n)}", W - 8, 171, 5.2, anchor="end", color=ctx.style.deep))
    options = [n, *r.sample([m for m in range(5, 11) if m != n], 4)]
    r.shuffle(options)
    for k, m in enumerate(options):
        cx = W - 22.0 - k * 36
        body.append(numeral_any(ctx, m, cx, 188, 18))
        if m == n:
            body.append(ring_at(cx, 188, 14, 12))
    answer = [f"العدد {ctx.num(n)} في الصف الأخير، و{ctx.num(n)} نجوم ملوّنة"]
    problems = [] if options.count(n) == 1 else ["the numeral must appear exactly once"]
    return Built({"svg": svg(body)}, answer, problems)


def number_rows(ctx: PageContext, n: int, cap: float, count: int | None, y: float) -> tuple[str, float]:
    """A writing row of the number: one digit through `tracing_row`; 10 as dotted «١٠» pairs."""
    shapes = digit_shapes(n, ctx.numerals)
    if len(shapes) == 1:
        return row_svg(tracing_row(shapes[0], width=W - 10, cap=cap, count=count, number=ctx.num), 5, y)
    scale = cap / 100
    height = cap + 12
    body = [
        draw.el(
            "path",
            d=draw.d_path(("M", (7, y + 5)), ("L", (W - 7, y + 5))),
            stroke="#9BB7E0",
            stroke_width=0.5,
        ),
        draw.el(
            "path",
            d=draw.d_path(("M", (7, y + 5 + cap)), ("L", (W - 7, y + 5 + cap))),
            stroke="#E27D63",
            stroke_width=0.6,
        ),
    ]
    pair_w = sum(s.width for s in shapes) * scale + 3
    fits = int((W - 26) // (pair_w + 10))
    for i in range(fits if count is None else min(count, fits)):
        x = W - 12 - (i + 1) * (pair_w + 10) + 10
        for k, shape in enumerate(shapes):
            body.append(
                dotted_letter(
                    shape,
                    scale=scale,
                    x=x + k * (shape.width * scale + 3),
                    y=y + 5 - 10 * scale,
                    first=i == 0,
                    number=ctx.num,
                )
            )
    return "".join(body), height


@page_type("number-trace-ten")
def number_trace_ten(ctx: PageContext) -> Built:
    n = int(ctx.page.params.get("number", 6))
    shapes = digit_shapes(n, ctx.numerals)
    body = [card(0, 0, W, 100, r=8)]
    if len(shapes) == 1:
        body.append(big_track(shapes[0], 50, 8, 90, 84, ctx.num, ctx.style.color))  # the band stays inside
    else:
        for k, shape in enumerate(shapes):
            body.append(big_track(shape, 40 + k * 56, 6, 50, 88, ctx.num, ctx.style.color))
    body.append(card(W - 46, 6, 40, 40, r=6, fill="#FFF6F2", stroke="none"))
    body.append(group_any("apple", n, W - 44, 8, 36, 36))
    y = 106.0
    for cap in (26.0, 18.0):
        row, height = number_rows(ctx, n, cap, None, y + 1.5)
        body.append(card(0, y, W, height + 3, r=6))
        body.append(row)
        y += height + 6
    return Built({"svg": svg(body)}, None, [] if y <= 206 else [f"the rows need {y:.0f} mm"])


@page_type("number-write-ten")
def number_write_ten(ctx: PageContext) -> Built:
    n = int(ctx.page.params.get("number", 6))
    r = ctx.rng("write")
    body, y = [], 0.0
    for k, count in enumerate((None, 2, 0)):
        row, height = number_rows(ctx, n, 24, count, y + 1.5)
        body.append(card(0, y, W, height + 3, r=6, fill="#FFFFFF" if k < 2 else "#FFFDF6"))
        body.append(row)
        if count == 0:
            body.append(draw.start_dot((W - 15, y + 1.5 + 5 + 2), 1.9))
        y += height + 6
    body.append(card(0, y, W, 204 - y, r=7))
    body.append(text("أَعُدُّ وَأَكْتُبُ العَدَدَ", W - 8, y + 10, 5.2, anchor="end", color=ctx.style.deep))
    things = r.sample(GROUP_PICTURES, 2)
    for k, thing in enumerate(things):
        x = W - (k + 1) * (W / 2)
        body.append(card(x + 6, y + 14, 56, 204 - y - 20, r=5, fill="#FFF6F2", stroke="none"))
        body.append(group_any(thing, n, x + 8, y + 16, 52, 204 - y - 24))
        body.append(card(x + 66, y + 24, 22, 26, r=4, fill="#FFFFFF", stroke="#D8C9AC", dash="2 1.4"))
    return Built({"svg": svg(body)}, [f"في المربّعين: {ctx.num(n)} و{ctx.num(n)}"], [])


@page_type("count-and-circle-ten")
def count_and_circle_ten(ctx: PageContext) -> Built:
    numbers = [int(x) for x in ctx.page.params.get("numbers", [6, 7, 8])]
    r = ctx.rng("count")
    counts = _counts(r, numbers, 4)
    options = sorted(set(numbers))
    while len(options) < 3:
        options = sorted({*options, max(1, min(options) - 1), min(10, max(options) + 1)})[:4]
    things = r.sample(GROUP_PICTURES, 4)
    body, answer, problems = [], [], []
    pitch = 51.0
    for i, (count, thing) in enumerate(zip(counts, things, strict=True)):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 4, r=7))
        body.append(card(W - 84, y + 5, 78, pitch - 12, r=5, fill="#FFF6F2", stroke="none"))
        body.append(group_any(thing, count, W - 82, y + 6, 74, pitch - 14))
        body.append(draw.arrow((W - 92, y + pitch / 2), 180, 3.5, "#D7C6A5"))
        step = (W - 104) / len(options)
        for k, m in enumerate(options):
            cx = W - 106 - (k + 0.5) * step
            body.append(
                draw.el(
                    "rect",
                    x=cx - 11,
                    y=y + 12,
                    width=22,
                    height=24,
                    rx=4,
                    fill="#FFFFFF",
                    stroke="#D8C9AC",
                    stroke_width=0.6,
                )
            )
            body.append(numeral_any(ctx, m, cx, y + 24, 16))
            if m == count:
                body.append(ring_at(cx, y + 24, 13, 14))
        answer.append(ctx.num(count))
        if options.count(count) != 1:
            problems.append(f"row {i + 1}: exactly one card must show {count}")
    return Built({"svg": svg(body)}, ["الأعداد: " + "، ".join(answer)], problems)


@page_type("number-quantity-match-ten")
def number_quantity_match_ten(ctx: PageContext) -> Built:
    numbers = [int(x) for x in ctx.page.params.get("numbers", [6, 7, 8])]
    r = ctx.rng("match")
    groups = list(numbers)
    for _ in range(50):
        r.shuffle(groups)
        if all(a != b for a, b in zip(groups, numbers, strict=True)):
            break
    things = r.sample(GROUP_PICTURES, len(numbers))
    pitch = 204 / len(numbers)
    body, key = [], []
    for i, n in enumerate(numbers):
        y = i * pitch + pitch / 2
        body.append(card(W - 40, y - pitch / 2 + 3, 36, pitch - 6, r=6, fill=ctx.style.tint, stroke="none"))
        body.append(numeral_any(ctx, n, W - 22, y, min(24, pitch - 12), ctx.style.deep))
        body.append(draw.el("circle", cx=W - 46, cy=y, r=1.8, fill="#FFFFFF", stroke=INK, stroke_width=0.7))
    for i, count in enumerate(groups):
        y = i * pitch + pitch / 2
        body.append(card(4, y - pitch / 2 + 3, 96, pitch - 6, r=6, fill="#FFF6F2", stroke="none"))
        body.append(group_any(things[i], count, 6, y - pitch / 2 + 5, 92, pitch - 10))
        body.append(draw.el("circle", cx=106, cy=y, r=1.8, fill="#FFFFFF", stroke=INK, stroke_width=0.7))
        j = numbers.index(count)
        key.append(
            draw.path(
                draw.polyline([(W - 46, j * pitch + pitch / 2), (106, y)]),
                stroke="#E0483A",
                width=1.1,
                class_="key-line",
            )
        )
    return Built({"svg": svg(body + key)}, ["كل عدد بالمجموعة التي فيها أشياء بعدده"], [])


@page_type("compare-ten")
def compare_ten(ctx: PageContext) -> Built:
    """More or less, up to ten: circle the group with more and write both numbers."""
    numbers = [int(x) for x in ctx.page.params.get("numbers", [6, 7, 8, 9, 10])]
    r = ctx.rng("compare")
    body, answer = [], []
    things = r.sample(GROUP_PICTURES, 3)
    for i in range(3):
        y = i * 68
        body.append(card(0, y + 2, W, 62, r=7))
        few, many = sorted(r.sample(numbers, 2))
        win = r.randrange(2)
        for k, cx in enumerate((W * 0.3, W * 0.7)):
            count = many if k == win else few
            body.append(card(cx - 38, y + 6, 76, 44, r=6, fill="#FFF6F2", stroke="none"))
            body.append(group_any(things[i], count, cx - 36, y + 8, 72, 40))
            body.append(card(cx - 9, y + 52, 18, 10, r=2.5, fill="#FFFFFF", stroke="#B8B2A6", dash="2 1.4"))
            if k == win:
                body.append(ring_at(cx, y + 28, 41, 24))
        answer.append(f"الصف {ctx.num(i + 1)}: {ctx.num(many)} أكثر من {ctx.num(few)}")
    return Built({"svg": svg(body)}, answer, [])


@page_type("number-train")
def number_train(ctx: PageContext) -> Built:
    """Trains of five wagons carrying numbers in order, with a missing number to write in each."""
    numbers = [int(x) for x in ctx.page.params.get("numbers", list(range(1, 11)))]
    r = ctx.rng("train")
    body, answer, problems = [], [], []
    for i in range(4):
        y = i * 51
        start = 1 + i * 2 if i < 3 else 6
        seq = [n for n in range(start, start + 5) if n in numbers]
        if len(seq) < 5:
            seq = numbers[-5:]
        blank = r.randrange(1, 4)
        body.append(card(0, y + 1, W, 47, r=7))
        # draft: educator review: the engine on the left, the numbers growing rightwards as numerals read
        body.append(draw.el("rect", x=6, y=y + 10, width=26, height=24, rx=4, fill=ctx.style.color))
        body.append(draw.el("rect", x=20, y=y + 4, width=10, height=8, rx=2, fill=ctx.style.deep))
        body.append(draw.el("circle", cx=12, cy=y + 38, r=4, fill=INK))
        body.append(draw.el("circle", cx=26, cy=y + 38, r=4, fill=INK))
        for k, n in enumerate(seq):
            x = 40 + k * 29
            body.append(
                draw.el(
                    "rect",
                    x=x,
                    y=y + 10,
                    width=26,
                    height=24,
                    rx=3,
                    fill="#FFFFFF",
                    stroke=INK,
                    stroke_width=0.7,
                    stroke_dasharray="2 1.4" if k == blank else "none",
                )
            )
            body.append(draw.el("circle", cx=x + 6, cy=y + 38, r=3.2, fill=INK))
            body.append(draw.el("circle", cx=x + 20, cy=y + 38, r=3.2, fill=INK))
            body.append(
                draw.path(draw.d_path(("M", (x - 3, y + 22)), ("L", (x, y + 22))), stroke=INK, width=1)
            )
            if k != blank:
                body.append(numeral_any(ctx, n, x + 13, y + 22, 16))
            else:
                body.append(
                    numeral_any(ctx, n, x + 13, y + 22, 16, "#E0483A").replace(
                        "<g ", '<g class="key-line" ', 1
                    )
                )
                answer.append(f"القطار {ctx.num(i + 1)}: {ctx.num(n)}")
        if seq != sorted(seq):
            problems.append("a train's numbers are out of order")
    return Built({"svg": svg(body)}, answer, problems)
