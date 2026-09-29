"""«دوسية التأسيس» math pages (Addendum 5 §3): every number goes meet → trace → write → practice (count and
circle) → apply (number ↔ quantity, compare). Numerals are printed and traced in the page's numerals (Hindi
by default, decision 2026-09-28 §4) from `qamra_workbook.digits`; groups use the dice layouts, so every
counting page can assert its quantities (Addendum 5 §8)."""

from __future__ import annotations

import random

from qamra_workbook.digits import digit_shapes
from qamra_workbook.letters.model import Letter
from qamra_workbook.puzzles import layout
from qamra_workbook.render import draw
from qamra_workbook.render.foundation_text import NUMBER_NAMES
from qamra_workbook.render.pages.letters import tracing_row
from qamra_workbook.render.pages.workbook_arabic import big_track, row_svg
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    card,
    fit_lines,
    glyph,
    pic,
    ring_at,
    start_marks,
    svg,
    text,
)
from qamra_workbook.render.registry import Built, PageContext, page_type

# what a number's groups are made of: friendly, easy to count, different page to page
GROUP_PICTURES = ("apple", "duck", "star", "ball", "fish", "flower", "car", "strawberry", "bee", "heart")


def number_shape(ctx: PageContext, n: int) -> Letter:
    """The one-digit numeral as a tracing shape, in the page's numerals."""
    shapes = digit_shapes(n, ctx.numerals)
    if len(shapes) != 1:
        raise ValueError(f"{n} is not a one-digit number")
    return shapes[0]


def group(picture: str, count: int, x: float, y: float, w: float, h: float) -> str:
    """`count` pictures in the dice layout inside a box (0 draws nothing); tagged for the quantity checks."""
    if count == 0:
        return f'<g data-count="0" data-picture="{picture}"></g>'
    size = min(w, h) * (0.5 if count <= 2 else 0.4 if count <= 4 else 0.34)
    items = "".join(
        pic(picture, x + u * w - size / 2, y + v * h - size / 2, size, data_count_item=picture)
        for u, v in layout(count)
    )
    return f'<g data-count="{count}" data-picture="{picture}">{items}</g>'


def numeral(ctx: PageContext, n: int, cx: float, cy: float, h: float, color: str = INK) -> str:
    """A printed numeral drawn in Qamra's hand (so it matches the tracing shapes), centred at (cx, cy)."""
    shape = number_shape(ctx, n)
    return glyph(shape, *fit_lines(shape, cx - h / 2, cy - h / 2, h, h), color=color, width=13)


def plate(x: float, y: float, w: float) -> str:
    h = w * 0.3
    return draw.el(
        "ellipse",
        cx=x + w / 2,
        cy=y + h / 2,
        rx=w / 2,
        ry=h / 2,
        fill="#FFFFFF",
        stroke="#2B2E4A",
        stroke_width=0.8,
    ) + draw.el("ellipse", cx=x + w / 2, cy=y + h / 2, rx=w * 0.38, ry=h * 0.3, fill="#F7F0E3")


@page_type("number-intro")
def number_intro(ctx: PageContext) -> Built:
    n = int(ctx.page.params.get("number", 1))
    r = ctx.rng("intro")
    shape = number_shape(ctx, n)
    thing = GROUP_PICTURES[n % len(GROUP_PICTURES)]
    body = [card(0, 0, W, 100, r=8)]
    scale, dx, dy = fit_lines(shape, W - 80, 6, 72, 74)
    body.append(glyph(shape, scale, dx, dy, color=ctx.style.color, width=17))
    body.append(start_marks(shape, scale, dx, dy, 3, ctx.num))
    body.append(text(NUMBER_NAMES[n], W - 44, 93, 9, cls="wb-word", color=ctx.style.deep))
    if n == 0:
        body.append(plate(10, 28, 46))
        body.append(group("apple", 5, 13, 8, 40, 28))
        body.append(draw.arrow((66, 36), 0, 5, ctx.style.color))
        body.append(plate(76, 28, 46))
        body.append(text("أكلنا التفاحات الخمس", 66, 62, 5))
        body.append(text("فصار الصحن فارغًا: لا شيء", 66, 71, 5, color=ctx.style.deep))
    else:
        body.append(card(8, 8, 90, 58, r=6, fill="#FFF6F2", stroke="none"))
        body.append(group(thing, n, 12, 10, 82, 54))
        for k in range(5):
            filled = k < n
            body.append(
                draw.el(
                    "circle",
                    cx=24 + k * 15,
                    cy=80,
                    r=5.5,
                    fill=ctx.style.color if filled else "#FFFFFF",
                    stroke=ctx.style.deep,
                    stroke_width=0.6,
                )
            )
    # color n stars (none for zero)
    body.append(card(0, 106, W, 46, r=7))
    stars = {0: "ولا نجمة: صفر!", 1: "نجمة واحدة", 2: "نجمتين"}.get(n, f"{ctx.num(n)} نجوم")
    say = f"ألوّن {stars}"
    body.append(text(say, W - 8, 118, 5.2, anchor="end", color=ctx.style.deep))
    for k in range(5):
        cx = W - 22 - k * 34
        body.append(
            draw.el(
                "path",
                d=draw.star_points(cx, 136, 12, 5.4),
                fill="#FFFFFF",
                stroke=INK,
                stroke_width=0.8,
                stroke_linejoin="round",
            )
        )
    # find the numeral
    body.append(card(0, 158, W, 46, r=7))
    body.append(text(f"أحوّط العدد {ctx.num(n)}", W - 8, 170, 5.2, anchor="end", color=ctx.style.deep))
    pool = [k for k in (0, 1, 2, 3, 4, 5) if k != n and (k != 0 or n == 0 or n == 5)]
    options = [n, *r.sample(pool, 4)]
    r.shuffle(options)
    for k, m in enumerate(options):
        cx = W - 26 - k * 33
        body.append(numeral(ctx, m, cx, 187, 18))
        if m == n:
            body.append(ring_at(cx, 187, 12, 12))
    answer = [f"العدد {ctx.num(n)} في الصف الأخير", f"{ctx.num(n)} نجوم ملوّنة" if n else "لا نجوم ملوّنة"]
    problems = [] if options.count(n) == 1 else ["the numeral must appear exactly once"]
    return Built({"svg": svg(body)}, answer, problems)


@page_type("number-trace")
def number_trace(ctx: PageContext) -> Built:
    n = int(ctx.page.params.get("number", 1))
    shape = number_shape(ctx, n)
    body = [card(0, 0, W, 100, r=8)]
    body.append(big_track(shape, 50, 2, 90, 96, ctx.num, ctx.style.color))
    body.append(card(W - 42, 8, 34, 34, r=6, fill="#FFF6F2", stroke="none"))
    body.append(plate(W - 40, 20, 30) if n == 0 else group("apple", n, W - 40, 10, 30, 30))
    y = 106.0
    for cap in (26.0, 18.0):
        row, height = row_svg(tracing_row(shape, width=W - 10, cap=cap, number=ctx.num), 5, y + 1.5)
        body.append(card(0, y, W, height + 3, r=6))
        body.append(row)
        y += height + 6
    problems = [] if y <= 206 else [f"the tracing rows need {y:.0f} mm"]
    return Built({"svg": svg(body)}, None, problems)


@page_type("number-write")
def number_write(ctx: PageContext) -> Built:
    """Guided rows (dotted, then two dotted and room), a row to write alone, then count and write."""
    n = int(ctx.page.params.get("number", 1))
    r = ctx.rng("write")
    shape = number_shape(ctx, n)
    body, y = [], 0.0
    for k, count in enumerate((None, 2, 0)):
        row, height = row_svg(
            tracing_row(shape, width=W - 10, cap=24, count=count, number=ctx.num), 5, y + 1.5
        )
        body.append(card(0, y, W, height + 3, r=6, fill="#FFFFFF" if k < 2 else "#FFFDF6"))
        body.append(row)
        if count == 0:
            body.append(draw.start_dot((15, y + 1.5 + 5 + (shape.strokes[0].start[1] - 10) * 0.24), 1.9))
        y += height + 6
    body.append(card(0, y, W, 204 - y, r=7))
    body.append(text("أعدّ وأكتب العدد", W - 8, y + 10, 5.2, anchor="end", color=ctx.style.deep))
    things = r.sample(GROUP_PICTURES, 2)
    counts = [n, n] if n else [0, 0]
    answer = []
    for k, (thing, count) in enumerate(zip(things, counts, strict=True)):
        x = W - (k + 1) * (W / 2)
        body.append(card(x + 6, y + 14, 52, 204 - y - 20, r=5, fill="#FFF6F2", stroke="none"))
        if count == 0:
            body.append(plate(x + 10, y + 16 + (204 - y - 24) / 2 - 6, 44))
        else:
            body.append(group(thing, count, x + 8, y + 16, 48, 204 - y - 24))
        body.append(card(x + 62, y + 22, 24, 26, r=4, fill="#FFFFFF", stroke="#D8C9AC", dash="2 1.4"))
        answer.append(f"{ctx.num(count)}")
    problems = [] if y <= 160 else [f"the writing rows need {y:.0f} mm"]
    return Built({"svg": svg(body)}, ["في المربّعين: " + " و".join(answer)], problems)


def _counts(r: random.Random, numbers: list[int], rows: int) -> list[int]:
    """`rows` amounts from `numbers` (each at least once), shuffled so they do not climb in a staircase."""
    out = (numbers * rows)[:rows]
    for _ in range(20):
        r.shuffle(out)
        if out != sorted(out):
            break
    return out


@page_type("count-and-circle")
def count_and_circle(ctx: PageContext) -> Built:
    numbers = [int(x) for x in ctx.page.params.get("numbers", [1, 2, 3])]
    r = ctx.rng("count")
    counts = _counts(r, numbers, 4)
    options = sorted(set(numbers))
    things = r.sample(GROUP_PICTURES, 4)
    body, answer, problems = [], [], []
    pitch = 51.0
    for i, (count, thing) in enumerate(zip(counts, things, strict=True)):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 4, r=7))
        body.append(card(W - 68, y + 5, 62, pitch - 12, r=5, fill="#FFF6F2", stroke="none"))
        body.append(group(thing, count, W - 66, y + 6, 58, pitch - 14))
        body.append(draw.arrow((W - 76, y + pitch / 2), 180, 3.5, "#D7C6A5"))
        step = (W - 90) / len(options)
        for k, m in enumerate(options):
            cx = W - 92 - (k + 0.5) * step
            body.append(
                draw.el(
                    "rect",
                    x=cx - 10,
                    y=y + 12,
                    width=20,
                    height=24,
                    rx=4,
                    fill="#FFFFFF",
                    stroke="#D8C9AC",
                    stroke_width=0.6,
                )
            )
            body.append(numeral(ctx, m, cx, y + 24, 16))
            if m == count:
                body.append(ring_at(cx, y + 24, 13, 14))
        answer.append(ctx.num(count))
        if options.count(count) != 1:
            problems.append(f"row {i + 1}: exactly one card must show {count}")
    return Built({"svg": svg(body)}, ["الأعداد: " + "، ".join(answer)], problems)


@page_type("number-quantity-match")
def number_quantity_match(ctx: PageContext) -> Built:
    numbers = [int(x) for x in ctx.page.params.get("numbers", [1, 2, 3])]
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
        body.append(card(W - 36, y - pitch / 2 + 3, 32, pitch - 6, r=6, fill=ctx.style.tint, stroke="none"))
        body.append(numeral(ctx, n, W - 20, y, min(24, pitch - 12), ctx.style.deep))
        body.append(draw.el("circle", cx=W - 42, cy=y, r=1.8, fill="#FFFFFF", stroke=INK, stroke_width=0.7))
    for i, count in enumerate(groups):
        y = i * pitch + pitch / 2
        body.append(card(4, y - pitch / 2 + 3, 74, pitch - 6, r=6, fill="#FFF6F2", stroke="none"))
        if count == 0:
            body.append(plate(16, y - 7, 50))
        else:
            body.append(group(things[i], count, 6, y - pitch / 2 + 4, 70, pitch - 8))
        body.append(draw.el("circle", cx=84, cy=y, r=1.8, fill="#FFFFFF", stroke=INK, stroke_width=0.7))
        j = numbers.index(count)
        key.append(
            draw.path(
                draw.polyline([(W - 42, j * pitch + pitch / 2), (84, y)]),
                stroke="#E0483A",
                width=1.1,
                class_="key-line",
            )
        )
    answer = [", ".join(f"{ctx.num(n)}" for n in numbers) + ": كل عدد بالمجموعة التي فيها بعدده"]
    return Built({"svg": svg(body + key)}, answer, [])


def long_thing(kind: str, x: float, y: float, length: float, color: str) -> str:
    """Something long or short to compare, drawn `length` mm long from (x, y) (its middle line)."""
    if kind == "pencil":
        d = draw.d_path(
            ("M", (x, y - 4)),
            ("L", (x + length - 9, y - 4)),
            ("L", (x + length, y)),
            ("L", (x + length - 9, y + 4)),
            ("L", (x, y + 4)),
        )
        tip = draw.d_path(
            ("M", (x + length - 4, y - 1.8)), ("L", (x + length, y)), ("L", (x + length - 4, y + 1.8))
        )
        return (
            draw.el("path", d=d + " Z", fill=color, stroke=INK, stroke_width=0.7, stroke_linejoin="round")
            + draw.el("path", d=tip + " Z", fill=INK)
            + draw.el(
                "rect",
                x=x - 3,
                y=y - 4,
                width=4,
                height=8,
                rx=1.5,
                fill="#F4A6B8",
                stroke=INK,
                stroke_width=0.7,
            )
        )
    if kind == "snake":
        waves: list[tuple[str, float | tuple[float, ...]]] = [("M", (x, y))]
        k = max(2, round(length / 16))
        for i in range(k):
            x1, x2 = x + (i + 0.5) * length / k, x + (i + 1) * length / k
            waves.append(("Q", (x1, y - 7 if i % 2 else y + 7, x2, y)))
        return (
            draw.path(draw.d_path(*waves), stroke=INK, width=6.4)
            + draw.path(draw.d_path(*waves), stroke=color, width=4.8)
            + draw.el("circle", cx=x + length, cy=y, r=4.6, fill=color, stroke=INK, stroke_width=0.7)
            + draw.el("circle", cx=x + length + 1.4, cy=y - 1.4, r=0.9, fill=INK)
        )
    # ribbon
    return draw.el(
        "rect", x=x, y=y - 3.5, width=length, height=7, rx=3.5, fill=color, stroke=INK, stroke_width=0.7
    ) + draw.el("circle", cx=x, cy=y, r=4.5, fill=color, stroke=INK, stroke_width=0.7)


def scatter(
    r: random.Random, picture: str, count: int, x: float, y: float, w: float, h: float, size: float
) -> str:
    """`count` pictures spread over a box on a jittered grid (no overlaps); tagged with the count."""
    cols = max(1, round((count * w / h) ** 0.5))
    rows = -(-count // cols)
    cells = [(c, k) for k in range(rows) for c in range(cols)][:count]
    out = []
    for c, k in cells:
        cx = x + (c + 0.5) * w / cols + r.uniform(-1.5, 1.5)
        cy = y + (k + 0.5) * h / rows + r.uniform(-1.5, 1.5)
        out.append(pic(picture, cx - size / 2, cy - size / 2, size))
    return f'<g data-count="{count}" data-picture="{picture}">{"".join(out)}</g>'


COMPARE_ROWS = {"big-small": 4, "long-short": 4, "many-few": 3, "more-less": 3}


@page_type("compare")
def compare(ctx: PageContext) -> Built:
    concept = str(ctx.page.params.get("concept", "big-small"))
    rows = COMPARE_ROWS.get(concept, 4)
    r = ctx.rng(concept)
    pitch = 204 / rows
    body, answer = [], []
    things = r.sample(GROUP_PICTURES, rows)
    colors = ("#EE8A6E", "#5E86D6", "#7DB46C", "#F2B33D")
    for i in range(rows):
        y = i * pitch
        body.append(card(0, y + 2, W, pitch - 6, r=7))
        left_wins = r.random() < 0.5
        mid = y + pitch / 2 - 1
        centers = (W * 0.27, W * 0.73)
        win = 0 if left_wins else 1
        if concept == "big-small":
            for k, cx in enumerate(centers):
                size = pitch - 14 if k == win else (pitch - 14) * 0.45
                body.append(pic(things[i], cx - size / 2, mid - size / 2, size))
            answer.append("الكبير")
        elif concept == "long-short":
            kind = ("pencil", "snake", "ribbon", "pencil")[i]
            for k, cx in enumerate(centers):
                length = 70 if k == win else 30
                body.append(long_thing(kind, cx - length / 2, mid, length, colors[i]))
            answer.append("الطويل")
        else:
            few, many = (1, 7) if concept == "many-few" else r.sample([3, 4, 5], 2)
            if concept == "more-less" and few > many:
                few, many = many, few
            for k, cx in enumerate(centers):
                count = many if k == win else few
                body.append(card(cx - 38, y + 7, 76, pitch - 16, r=6, fill="#FFF6F2", stroke="none"))
                body.append(scatter(r, things[i], count, cx - 36, y + 9, 72, pitch - 20, min(15, pitch / 4)))
            answer.append(f"{ctx.num(many)} أكثر من {ctx.num(few)}" if concept == "more-less" else "الكثير")
        cx = centers[win]
        body.append(ring_at(cx, mid, 42, pitch / 2 - 6))
        if concept == "more-less":
            lose = centers[1 - win]
            body.append(
                draw.path(
                    draw.d_path(
                        ("M", (lose + 30, y + 10)),
                        ("L", (lose + 38, y + 18)),
                        ("M", (lose + 38, y + 10)),
                        ("L", (lose + 30, y + 18)),
                    ),
                    stroke="#E0483A",
                    width=1.2,
                    class_="key-line",
                )
            )
    return Built({"svg": svg(body)}, [f"الصف {ctx.num(i + 1)}: {a}" for i, a in enumerate(answer)], [])
