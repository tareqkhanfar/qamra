"""«دوسية التأسيس» KG1 math beyond the KG2 pages: ordering three sizes, equal amounts, the fewer group,
finding
shapes in a scene, and adding and subtracting with pictures within 5 (a story line on the story pages).
The child circles the answer among three numerals: KG1 writes little."""

from __future__ import annotations

import random
from itertools import combinations

from qamra_workbook.digits import digit_shapes
from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import letter_extent
from qamra_workbook.render.pages.workbook_common import INK, W, card, pic, ring_at, svg, text
from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES, _counts, numeral, scatter
from qamra_workbook.render.pages.workbook_math2 import group_any, number_rows, numeral_any
from qamra_workbook.render.pages.workbook_pen import shape_stroke
from qamra_workbook.render.pages.workbook_review import Box, Drawn, Task
from qamra_workbook.render.registry import Built, PageContext, page_type

SHAPE_COLORS = {"circle": ("#E5604E", "أحمر"), "square": ("#5E86D6", "أزرق"), "triangle": ("#6FAE5F", "أخضر")}
SHAPE_COLORS["rectangle"] = ("#F7C84A", "أصفر")
SHAPE_AR = {"circle": "الدوائر", "square": "المربعات", "triangle": "المثلثات", "rectangle": "المستطيلات"}
# the shapes of the scene: (kind, cx, cy, size); a rectangle is 1.5 × wider than tall
# every shape whole and apart inside the panel: the roof sits on the house (it covered its top, so the
# square read as a rectangle), the wheels and the bottom square stay above the panel's edge, the cabin
# beside the truck
SCENE = (
    ("square", 60, 120, 44),
    ("triangle", 60, 72, 52),
    ("rectangle", 60, 134, 12),
    ("circle", 46, 108, 10),
    ("circle", 156, 30, 22),
    ("rectangle", 130, 156, 26),
    ("circle", 118, 168, 9),
    ("circle", 142, 168, 9),
    ("triangle", 150, 120, 30),
    ("rectangle", 158, 160, 10),
    ("square", 108, 60, 18),
    ("triangle", 108, 38, 22),
    ("circle", 20, 40, 12),
    ("square", 20, 160, 16),
    ("triangle", 172, 84, 16),
)
STORY_ADD = ("{a} عَلى الشَّجَرَةِ، جاءَ {b}. كَمْ صارَ العَدَدُ؟", "bird")
STORY_SUB = ("كانَ مَعَنا {a}، أَكَلْنا {b}. كَمْ بَقِيَ؟", "apple")
# the counted noun, vowelised: (singular, accusative singular, nominative dual, accusative dual, the plural
# after 3–10 (genitive), the word «one» that agrees with it)
NOUNS = {
    "bird": ("عُصْفورٌ", "عُصْفورًا", "عُصْفورانِ", "عُصْفورَيْنِ", "عَصافيرَ", "واحِدٌ"),
    "apple": ("تُفّاحَةٌ", "تُفّاحَةً", "تُفّاحَتانِ", "تُفّاحَتَيْنِ", "تُفّاحاتٍ", "واحِدَةٌ"),
}


def counted(ctx: PageContext, n: int, thing: str, *, accusative: bool = False, subject: bool = False) -> str:
    """«عُصْفورٌ واحِدٌ، عُصْفورانِ، ٣ عَصافيرَ»: the noun agrees with its number (a lone `n` = 1 after a verb
    says only the singular: «جاءَ عُصْفورٌ», «أَكَلْنا تُفّاحَةً»)."""
    one, one_acc, two, two_acc, many, word_one = NOUNS[thing]
    if n == 1:
        return f"{one} {word_one}" if subject else one_acc if accusative else one
    if n == 2:
        return two_acc if accusative else two
    return f"{ctx.num(n)} {many}"


def items_row(picture: str, count: int, x: float, y: float, w: float, h: float, crossed: int = 0) -> str:
    """`count` pictures in a row (two rows from 3: 2+1, 2+2, 3+2), the last `crossed` ones crossed out."""
    per_row = count if count <= 2 else 2 if count <= 4 else 3
    rows = (count + per_row - 1) // per_row if count else 1
    size = min(w / max(per_row, 1) - 2, h / rows - 2, 22.0)
    out = []
    for k in range(count):
        row, col = divmod(k, per_row)
        cx = x + w - (col + 0.5) * (w / per_row)
        cy = y + (row + 0.5) * (h / rows)
        out.append(pic(picture, cx - size / 2, cy - size / 2, size, class_=f"pic item-{k}"))
        if k >= count - crossed:
            out.append(
                draw.path(
                    draw.d_path(
                        ("M", (cx - size / 2, cy - size / 2)),
                        ("L", (cx + size / 2, cy + size / 2)),
                        ("M", (cx + size / 2, cy - size / 2)),
                        ("L", (cx - size / 2, cy + size / 2)),
                    ),
                    stroke="#E0483A",
                    width=1.4,
                )
            )
    return f'<g data-count="{count}" data-crossed="{crossed}">{"".join(out)}</g>'


def choices(
    ctx: PageContext, right: int, pool: list[int], r: random.Random, x: float, cy: float, h: float
) -> list[str]:
    """Three numerals to circle (the right one among them), from x leftwards."""
    options = [right, *r.sample([n for n in pool if n != right], 2)]
    r.shuffle(options)
    out = []
    for k, n in enumerate(options):
        cx = x - (k + 0.5) * 22
        out.append(
            draw.el("circle", cx=cx, cy=cy, r=h / 2 + 2, fill="#FFFDF6", stroke="#D8C9AC", stroke_width=0.5)
        )
        out.append(numeral(ctx, n, cx, cy, h))
        if n == right:
            out.append(ring_at(cx, cy, h / 2 + 3, h / 2 + 3))
    return out


def sum_row(
    ctx: PageContext, r: random.Random, a: int, b: int, box: Box, subtract: bool, story: bool
) -> tuple[list[str], str]:
    """One picture sum: the groups, the sign, and three numerals to choose from."""
    thing = GROUP_PICTURES[(a * 3 + b) % len(GROUP_PICTURES)]
    out = []
    y, h = box.y + (14 if story else 4), box.h - (18 if story else 8)
    if story:
        template, thing = STORY_SUB if subtract else STORY_ADD
        line = template.format(
            a=counted(ctx, a, thing, subject=True), b=counted(ctx, b, thing, accusative=subtract)
        )
        out.append(text(line, box.x + box.w - 4, box.y + 9, 4.6, anchor="end", color=ctx.style.deep))
    mid = y + h / 2 + 3
    if subtract:
        gw = (box.w - 76) / 2
        out.append(items_row(thing, a, box.x + box.w - gw - 4, y, gw, h, crossed=b))
        out.append(text("−", box.x + box.w - gw - 12, mid, 8, cls="wb-num", color=INK))
        out.append(text(ctx.num(b), box.x + box.w - gw - 26, mid, 8, cls="wb-num", color=INK))
        total, equals, options = a - b, box.x + 70, box.x + 66
    else:  # from the right: the first group, «+», the second group, «=», three numerals: nothing overlaps
        gw = 40.0
        left = box.x + box.w - 4 - gw
        out.append(items_row(thing, a, left, y, gw, h))
        out.append(text("+", left - 6, mid, 8, cls="wb-num", color=INK))
        out.append(items_row(thing, b, left - 12 - gw, y, gw, h))
        total, equals, options = a + b, left - 12 - gw - 6, left - 12 - gw - 12
    out.append(text("=", equals, mid, 8, cls="wb-num", color=INK))
    out += choices(ctx, total, list(range(0, 6)), r, options, y + h / 2, min(h - 6, 14.0))
    sign = "−" if subtract else "+"
    return out, f"{ctx.num(a)} {sign} {ctx.num(b)} = {ctx.num(total)}"


def sums(r: random.Random, top: int, count: int, subtract: bool) -> list[tuple[int, int]]:
    pairs = [
        (a, b)
        for a in range(1, top + 1)
        for b in range(1, top + 1)
        if (a - b >= 0 if subtract else a + b <= top)
    ]
    r.shuffle(pairs)
    return sorted(pairs[:count], key=lambda p: p[0] + p[1])


def sums_page(ctx: PageContext, subtract: bool) -> Built:
    top = int(ctx.page.params.get("max", 5))
    story = ctx.page.params.get("mode") == "story"
    r = ctx.rng("sums")
    rows = 3
    pitch = 204 / rows
    body, answer = [], []
    for i, (a, b) in enumerate(sums(r, top, rows, subtract)):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 5, r=7))
        part, line = sum_row(ctx, r, a, b, Box(2, y + 1, W - 4, pitch - 5), subtract, story)
        body += part
        answer.append(line)
    return Built({"svg": svg(body)}, answer, [])


@page_type("kg1-picture-add")
def kg1_picture_add(ctx: PageContext) -> Built:
    return sums_page(ctx, False)


@page_type("kg1-picture-subtract")
def kg1_picture_subtract(ctx: PageContext) -> Built:
    return sums_page(ctx, True)


def sums_task(top: int, subtract: bool, rows: int = 2) -> Task:
    """Picture sums in a review box (two, or `rows`), each a different pair."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        for i, (a, b) in enumerate(sums(r, top, rows, subtract)):
            part, line = sum_row(
                ctx, r, a, b, Box(box.x, box.y + i * box.h / rows, box.w, box.h / rows), subtract, False
            )
            out.body += part
            out.answer.append(line)
        return out

    return task


@page_type("kg1-compare")
def kg1_compare(ctx: PageContext) -> Built:
    """Order three sizes (write 1–3), find the rows with equal amounts, circle the group with more (numbers of
    the plan, a different pair in each row) or the fewer group."""
    concept = str(ctx.page.params.get("concept", "fewer"))
    numbers = [int(n) for n in ctx.page.params.get("numbers", [1, 2, 3, 4, 5])]
    r = ctx.rng(concept)
    pairs = list(combinations(sorted(set(numbers)), 2))
    r.shuffle(pairs)
    rows = 3 if concept == "order-size" else 4 if concept != "more-less" else min(4, len(pairs))
    pitch = 204 / rows
    things = r.sample(GROUP_PICTURES, rows)
    body, answer = [], []
    for i in range(rows):
        y = i * pitch
        body.append(card(0, y + 2, W, pitch - 6, r=7))
        mid = y + pitch / 2 - 1
        if concept == "order-size":
            sizes = [pitch - 30, (pitch - 30) * 0.7, (pitch - 30) * 0.42]
            order = [0, 1, 2]
            r.shuffle(order)
            for k, j in enumerate(order):
                cx = W - (k + 0.5) * W / 3
                body.append(pic(things[i], cx - sizes[j] / 2, mid - 8 - sizes[j] / 2, sizes[j]))
                body.append(card(cx - 7, y + pitch - 22, 14, 12, r=3, fill="#FFFDF6"))
                body.append(
                    text(ctx.num(3 - j), cx, y + pitch - 12.5, 6, cls="wb-num key-line", color="#E0483A")
                )
            answer.append(f"الصف {ctx.num(i + 1)}: " + "، ".join(ctx.num(3 - j) for j in order))
            continue
        if concept == "equal":
            equal = i % 2 == 0
            a = r.choice(numbers)
            b = a if equal else r.choice([n for n in numbers if n != a])
        elif concept == "more-less":
            a, b = pairs[i] if r.random() < 0.5 else pairs[i][::-1]
        else:
            a, b = r.sample(numbers, 2)
        for k, count in enumerate((a, b)):
            cx = W * (0.27 if k else 0.73)
            body.append(card(cx - 38, y + 7, 76, pitch - 16, r=6, fill="#FFF6F2", stroke="none"))
            size = min(
                22.0 if max(a, b) <= 3 else 17.0 if max(a, b) <= 6 else 13.0, pitch / 3
            )  # big, to count
            body.append(scatter(r, things[i], count, cx - 36, y + 9, 72, pitch - 20, size))
        if concept == "equal":
            if a == b:
                body.append(ring_at(W / 2, mid, W / 2 - 4, pitch / 2 - 5))
            answer.append(
                f"الصف {ctx.num(i + 1)}: {'متساوٍ' if a == b else 'غير متساوٍ'} ({ctx.num(a)} و{ctx.num(b)})"
            )
        else:
            pick = max(a, b) if concept == "more-less" else min(a, b)
            side = W * 0.73 if (a == pick) else W * 0.27
            body.append(ring_at(side, mid, 42, pitch / 2 - 6))
            word = "الأكثر" if concept == "more-less" else "الأقل"
            answer.append(f"الصف {ctx.num(i + 1)}: {word} {ctx.num(pick)}")
    problems = [] if rows >= 3 else ["compare needs at least three rows"]
    return Built({"svg": svg(body)}, answer, problems)


@page_type("kg1-shape-find")
def kg1_shape_find(ctx: PageContext) -> Built:
    """A scene drawn only with circles, squares, triangles and rectangles: color each kind with its color."""
    kinds = [str(k) for k in ctx.page.params.get("shapes", list(SHAPE_AR))]
    body = [card(0, 0, W, 22, r=7, fill=ctx.style.tint, stroke="none")]
    for k, kind in enumerate(kinds):
        color, _ = SHAPE_COLORS[kind]
        x = W - 22 - k * 46
        body.append(draw.el("circle", cx=x + 12, cy=11, r=5, fill=color))
        body.append(draw.path(shape_stroke(kind, x, 11, 9).d, stroke=INK, width=0.9, fill="#FFFFFF"))
    body.append(card(0, 26, W, 178, r=8, fill="#F4F9FD", stroke="none"))
    counts = dict.fromkeys(kinds, 0)
    for kind, cx, cy, size in SCENE:
        if kind not in kinds:
            continue
        counts[kind] += 1
        body.append(
            draw.path(
                shape_stroke(kind, cx, cy + 26, size).d,
                stroke=INK,
                width=1.1,
                fill="#FFFFFF",
                data_shape=kind,
            )
        )
    for k, kind in enumerate(kinds):
        body.append(
            text(
                f"{SHAPE_AR[kind]}: {ctx.num(counts[kind])}",
                W - 8 - k * 46,
                200,
                4.2,
                anchor="end",
                color=ctx.style.deep,
                cls="wb-label key-line",
            )
        )
    answer = ["، ".join(f"{SHAPE_AR[k]} {ctx.num(counts[k])} ({SHAPE_COLORS[k][1]})" for k in kinds)]
    return Built(
        {"svg": svg(body)},
        answer,
        [] if all(counts.values()) else ["a shape of the legend is not in the scene"],
    )


def alone_start(ctx: PageContext, n: int, cap: float, y: float) -> str:
    """The green dot where the numeral `n` starts on an empty writing row placed at `y` (right end: the
    numerals run right to left like the Arabic rows, left end for Latin digits)."""
    shape = digit_shapes(n, ctx.numerals)[0]
    g = shape.guides
    s = cap / (g.base - g.top)
    x0, y0, x1, _ = letter_extent(shape)
    start = shape.strokes[0].start
    sx = 5 + (W - 10) - 10 - (x1 - start[0]) * s if shape.rtl else 5 + 10 + (start[0] - x0) * s
    sy = y + 5 + max(0.0, (g.top - y0) * s) + (start[1] - g.top) * s
    return draw.start_dot((sx, sy), 1.9)


@page_type("kg1-number-write")
def kg1_number_write(ctx: PageContext) -> Built:
    """«أكتب ١ و٢ و٣ بالتتبّع ثم وحدي»: every number has a row that starts with dotted numerals and leaves room
    to go on (two numbers: a full dotted row first); the last row, with the numbers named above it, is empty
    for writing them alone. Big numerals: the rows are as tall as the page allows."""
    params = ctx.page.params
    numbers = [int(n) for n in params.get("numbers", [1, 2, 3])]
    guided, alone = int(params.get("guided", 2)), int(params.get("independent", 1))
    problems = [] if guided >= 1 and alone >= 1 else ["number-write has guided rows, then a row alone"]
    per = 2 if len(numbers) <= 2 else 1  # three numbers get one guided row each: the rows stay big
    rows = [(n, count) for n in numbers for count in ((None, 3) if per == 2 else (3,))]
    label, gap = 8.0, 4.0
    cap = 14.0
    for cap in (26.0, 24.0, 22.0, 20.0, 18.0, 16.0, 15.0, 14.0):
        heights = sum(number_rows(ctx, n, cap, count, 0)[1] + 3 + gap for n, count in rows)
        alone_h = alone * (number_rows(ctx, numbers[0], cap, 0, 0)[1] + 3 + label + gap)
        if heights + alone_h - gap <= 204:
            break
    body, y = [], 0.0
    for n, count in rows:
        row, height = number_rows(ctx, n, cap, count, y + 1.5)
        body.append(card(0, y, W, height + 3, r=6))
        body.append(row)
        y += height + 3 + gap
    names = " ".join(ctx.num(n) for n in numbers)
    for _ in range(alone):
        body.append(text(f"أَكْتُبُ وَحْدي: {names}", W - 6, y + 5.4, 4.8, anchor="end", color=ctx.style.deep))
        row, height = number_rows(ctx, numbers[0], cap, 0, y + label + 1.5)
        body.append(card(0, y + label, W, height + 3, r=6, fill="#FFFDF6"))
        body.append(row)
        body.append(alone_start(ctx, numbers[0], cap, y + label + 1.5))
        y += label + height + 3 + gap
    if y - gap > 204.5:
        problems.append(f"the writing rows need {y - gap:.0f} mm (max 204)")
    return Built({"svg": svg(body)}, None, problems)


@page_type("kg1-count-and-circle")
def kg1_count_and_circle(ctx: PageContext) -> Built:
    """Count the group and circle its number among three (the right one and its two nearest neighbours): KG1
    never offers five numerals in a row."""
    numbers = [int(x) for x in ctx.page.params.get("numbers", [6, 7, 8, 9, 10])]
    r = ctx.rng("count")
    counts = _counts(r, numbers, 4)
    things = r.sample(GROUP_PICTURES, 4)
    body, answer = [], []
    pitch = 51.0
    for i, (count, thing) in enumerate(zip(counts, things, strict=True)):
        y = i * pitch
        near = sorted((n for n in set(numbers) if n != count), key=lambda n: (abs(n - count), r.random()))
        options = sorted([count, *near[:2]])
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
    problems = [] if len(set(numbers)) >= 3 else ["count-and-circle needs three different numbers"]
    return Built({"svg": svg(body)}, ["الأعداد: " + "، ".join(answer)], problems)


BOX_COLORS = (("#C98F4E", "#E3B87E"), ("#5B8FC9", "#8DB6E3"), ("#6BA866", "#A0D09A"))  # (inside, front)


@page_type("kg1-inside-outside")
def kg1_inside_outside(ctx: PageContext) -> Built:
    """«أين الكرة؟»: three big boxes, one picture sitting inside each (its lower part hidden by the front of
    the box) and two outside it: circle the one that is inside."""
    r = ctx.rng("inout")
    things = [
        "ball",
        *r.sample([t for t in GROUP_PICTURES if t != "ball"], 8),
    ]  # the ball is in the first box
    pitch = 204 / 3
    body, answer = [], []
    for i, (inner, front) in enumerate(BOX_COLORS):
        y = i * pitch
        cy = y + pitch / 2 + 3
        inside, left, right = things[3 * i : 3 * i + 3]
        body.append(card(0, y + 1, W, pitch - 5, r=7))
        size = 27.0
        body.append(pic(left, 14, cy - size / 2, size))
        body.append(pic(right, W - 14 - size, cy - size / 2, size))
        x0, x1 = 55.0, W - 55.0
        body.append(
            draw.el(
                "rect",
                x=x0,
                y=cy - 16,
                width=x1 - x0,
                height=36,
                rx=3,
                fill=inner,
                stroke=INK,
                stroke_width=0.8,
            )
        )
        body.append(pic(inside, W / 2 - size / 2 - 1, cy - 29, size))
        body.append(
            draw.el(
                "rect",
                x=x0,
                y=cy - 2,
                width=x1 - x0,
                height=22,
                rx=3,
                fill=front,
                stroke=INK,
                stroke_width=0.8,
            )
        )
        body.append(ring_at(W / 2, cy - 14, 21, 19))
        answer.append(f"الصف {ctx.num(i + 1)}: داخل الصندوق {PICTURES[inside].word_ar}")
    problems = [] if len(set(things)) == 9 else ["a picture repeats"]
    return Built({"svg": svg(body)}, answer, problems)


STARS = {1: "نجمة واحدة ملوّنة", 2: "نجمتان ملوّنتان"}


@page_type("kg1-number-intro")
def kg1_number_intro(ctx: PageContext) -> Built:
    """The KG2 number page; its key says «نجمة واحدة ملوّنة» and «نجمتان ملوّنتان», not «١ نجوم»."""
    from qamra_workbook.render.pages.workbook_math import number_intro

    out = number_intro(ctx)
    n = int(ctx.page.params.get("number", 1))
    if n in STARS and out.answer:
        out.answer = [out.answer[0], STARS[n]]
    return out
