"""Journey math pages for stage 1 (Addendum 6 §4.7; decision 2026-09-28 §3): equal groups, the numerals 1–5
seen (never written) with their dots, above and below, inside and outside, near and far. Quantities are
drawn exactly and checked."""

from __future__ import annotations

from collections.abc import Callable

from markupsafe import Markup

from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_kit import (
    INK,
    SOFT,
    H,
    W,
    card,
    join_columns,
    picture,
    pid,
    svg,
    text,
)
from qamra_workbook.render.pages.journey_shapes import filled
from qamra_workbook.render.pages.workbook_common import ring_at
from qamra_workbook.render.registry import Built, PageContext, page_type

# dice positions in a unit box, for groups of 1–6
PIPS = {
    1: [(0.5, 0.5)],
    2: [(0.28, 0.28), (0.72, 0.72)],
    3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
    4: [(0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)],
    5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
    6: [(0.28, 0.2), (0.72, 0.2), (0.28, 0.5), (0.72, 0.5), (0.28, 0.8), (0.72, 0.8)],
}
SHAPE_OF = {
    "نجوم": ("star", "#F7C84A"),
    "قلوب": ("heart", "#E97A98"),
    "stars": ("star", "#F7C84A"),
    "hearts": ("heart", "#E97A98"),
    "كرات": ("circle", "#5E86D6"),
}


def group(kind: str, count: int, x: float, y: float, size: float) -> str:
    shape, color = SHAPE_OF.get(kind, ("circle", "#5E86D6"))
    s = size * (0.3 if count <= 4 else 0.24)
    return "".join(filled(shape, x + px * size, y + py * size, s, color) for px, py in PIPS[count])


@page_type("same-amount")
def same_amount(ctx: PageContext) -> Built:
    """Groups of stars (right) and of hearts (left): join the two groups with the same amount."""
    numbers = [int(n) for n in ctx.page.params.get("numbers", [2, 3, 4])]
    kinds = [str(k) for k in ctx.page.params.get("groups", ["نجوم", "قلوب"])]
    order = list(numbers)
    shuffler = ctx.rng("same")
    while order == numbers:
        shuffler.shuffle(order)
    problems = (
        []
        if all(1 <= n <= 5 for n in numbers) and len(set(numbers)) == len(numbers)
        else ["stage 1 groups hold 1–5, each amount once"]
    )
    body = join_columns(
        lambda i, x, y, s: group(kinds[0], numbers[i], x, y, s),
        lambda j, x, y, s: group(kinds[-1], order[j], x, y, s),
        len(numbers),
        [order.index(n) for n in numbers],
    )
    return Built({"svg": svg(body)}, [f"{ctx.num(n)} ← {ctx.num(n)}" for n in numbers], problems)


@page_type("numeral-cards")
def numeral_cards(ctx: PageContext) -> Built:
    """The numerals 1–5 to look at (never to write), each with its dots to colour."""
    numbers = [int(n) for n in ctx.page.params.get("numbers", [1, 2, 3, 4, 5])]
    problems = [] if all(1 <= n <= 5 for n in numbers) else ["stage 1 shows the numerals 1–5 only"]
    pitch, body = H / len(numbers), []
    for i, n in enumerate(numbers):
        y = i * pitch
        body.append(card(0, y + 2, W, pitch - 6, r=8))
        body.append(card(W - 40, y + 5, 34, pitch - 12, r=7, fill=ctx.style.tint, stroke="none"))
        body.append(
            text(
                ctx.num(n),
                W - 23,
                y + pitch / 2 + 8,
                min(24.0, pitch - 14),
                cls="wb-num",
                color=ctx.style.deep,
            )
        )
        for k in range(n):
            cx = W - 60 - k * 26
            fill = ctx.style.color if i == 0 and ctx.page.example else "#FFFFFF"
            body.append(
                draw.el(
                    "circle", cx=cx, cy=y + pitch / 2 - 2, r=9, fill=fill, stroke="#2B2E4A", stroke_width=0.9
                )
            )
    return Built({"svg": svg(body)}, None, problems)


def table(x: float, y: float, w: float) -> str:
    top = draw.el(
        "rect", x=x, y=y, width=w, height=8, rx=2, fill="#C98A5B", stroke="#2B2E4A", stroke_width=0.9
    )
    legs = "".join(
        draw.el(
            "rect",
            x=lx,
            y=y + 8,
            width=6,
            height=62,
            rx=1.5,
            fill="#A8734D",
            stroke="#2B2E4A",
            stroke_width=0.9,
        )
        for lx in (x + 8, x + w - 14)
    )
    return legs + top


def crate(x: float, y: float, w: float, h: float) -> str:
    return draw.el(
        "rect", x=x, y=y, width=w, height=h, rx=2, fill="#E3B982", stroke="#2B2E4A", stroke_width=0.9
    ) + draw.path(f"M{x} {y + h / 2} L{x + w} {y + h / 2}", stroke="#A8734D", width=0.8)


@page_type("position-words")
def position_words(ctx: PageContext) -> Built:
    """Above and below (colour what is on the table) or inside and outside (circle the cat in the box)."""
    concept = str(ctx.page.params.get("concept", "above-below"))
    body = [
        card(0, 0, W, H, r=10, fill="#F4F9FD", stroke="none"),
        card(0, 176, W, 28, r=8, fill="#EFE5D2", stroke="none"),
    ]
    key: list[str] = []
    if concept == "above-below":
        above = [str(w) for w in ctx.page.params.get("above", ["ball", "apple"])]
        below = [str(w) for w in ctx.page.params.get("below", ["cat", "shoe"])]
        body.append(table(28, 104, W - 56))
        for k, w in enumerate(above):
            x = 60 + k * 44
            body += [
                picture(w, x, 66, 38, "line"),
                picture(w, x, 66, 38).replace("<svg", '<svg class="key-ring"', 1),
            ]
        for k, w in enumerate(below):
            body.append(picture(w, 56 + k * 44, 136, 40, "line"))
        key.append("فوق الطاولة: " + "، ".join(PICTURES[pid(w)].word_ar for w in above))
    else:
        inside_right = ctx.rng("box").random() < 0.5
        bx = W - 90 if inside_right else 20
        ox = 26 if inside_right else W - 76
        body.append(picture("cat", bx + 12, 84, 48))
        body.append(crate(bx, 112, 70, 64))
        body.append(picture("cat", ox, 128, 48))
        body.append(ring_at(bx + 35, 128, 44, 48))
        key.append(f"القطة داخل الصندوق: {'اليمين' if inside_right else 'اليسار'}")
    return Built({"svg": svg(body)}, key)


@page_type("near-far")
def near_far(ctx: PageContext) -> Built:
    """A house and two trees: colour the tree near the house."""
    thing = pid(str(ctx.page.params.get("item", "tree")))
    near_right = ctx.rng("near").random() < 0.5
    house_x = (
        120.0 if near_right else 6.0
    )  # the house on one side, the near tree beside it, the far one across
    near_x = 72.0 if near_right else 62.0
    far_x = 4.0 if near_right else 128.0
    body = [
        card(0, 0, W, H, r=10, fill="#F4F9FD", stroke="none"),
        card(0, 150, W, 54, r=8, fill="#DDEFD6", stroke="none"),
    ]
    body.append(picture("house", house_x, 92, 60))
    for x, near in ((near_x, True), (far_x, False)):
        body.append(picture(thing, x, 96, 54, "line"))
        if near:
            body.append(picture(thing, x, 96, 54).replace("<svg", '<svg class="key-ring"', 1))
    gap_near, gap_far = abs(near_x + 27 - house_x - 30), abs(far_x + 27 - house_x - 30)
    problems = [] if gap_far >= 1.8 * gap_near else ["the far tree must be clearly farther"]
    side = "اليمين" if (near_x > far_x) else "اليسار"
    return Built({"svg": svg(body)}, [f"الشجرة القريبة: على {side}"], problems)


@page_type("count-print")
def count_print(ctx: PageContext) -> Built:
    """Count the pictures and press one fingerprint under each (one to one)."""
    thing = pid(str(ctx.page.params.get("picture", "duck")))
    count = int(ctx.page.params.get("count", 4))
    problems = [] if 1 <= count <= 5 else ["stage 1 counts 1–5"]
    step = (W - 16) / count
    size = min(44.0, step - 8)
    body = [card(0, 20, W, 150, r=10, fill=SOFT, stroke="none")]
    for k in range(count):
        cx = W - 8 - (k + 0.5) * step
        body.append(picture(thing, cx - size / 2, 40, size))
        body.append(
            draw.el(
                "ellipse",
                cx=cx,
                cy=128,
                rx=size * 0.3,
                ry=size * 0.38,
                fill="#FFFFFF",
                stroke="#8C90A6",
                stroke_width=0.8,
                stroke_dasharray="2.6 2",
            )
        )
        if k == 0 and ctx.page.example:
            body.append(
                draw.el(
                    "ellipse", cx=cx, cy=128, rx=size * 0.26, ry=size * 0.34, fill="#8C79C9", opacity=0.55
                )
            )
    return Built({"svg": svg(body)}, [f"{PICTURES[thing].word_ar}: {ctx.num(count)}"], problems)


# ---- stages 2–3 (§4.7): numerals 1–10 traced and written, ten frames, before/after, adding and taking away


def ten_frame(x: float, y: float, w: float, filled: int, color: str, css: str = "") -> str:
    """A 2 × 5 frame with `filled` counters (in reading order)."""
    cw, ch = w / 5, w / 5
    attrs: dict[str, str | float] = {"class_": css} if css else {}
    out = [
        draw.el("rect", x=x, y=y, width=w, height=2 * ch, rx=2, fill="#FFFFFF", stroke=INK, stroke_width=0.7)
    ]
    out += [
        draw.path(f"M{x + k * cw} {y} L{x + k * cw} {y + 2 * ch}", stroke=INK, width=0.5) for k in range(1, 5)
    ]
    out.append(draw.path(f"M{x} {y + ch} L{x + w} {y + ch}", stroke=INK, width=0.5))
    for k in range(filled):
        r, c = divmod(k, 5)
        out.append(
            draw.el(
                "circle",
                cx=x + w - (c + 0.5) * cw,
                cy=y + (r + 0.5) * ch,
                r=cw * 0.34,
                fill=color,
                stroke=INK,
                stroke_width=0.5,
                **attrs,
            )
        )
    return "".join(out)


def _numbered_from(ctx: PageContext, offset: int) -> Callable[[int], str]:
    """Stroke numbers in the page's numerals, counted on from `offset` strokes already written."""

    def number(j: int) -> str:
        return ctx.num(j + offset)

    return number


def digits_row(ctx: PageContext, n: int, width: float, cap: float, count: int) -> Markup:
    """A writing row (an `<svg>` in mm, like `tracing_row`) for a two-digit number (10): `count` dotted
    copies, each its digits side by side (numbers are written left to right: the 1, then the 0)."""
    from qamra_workbook.digits import digit_shapes
    from qamra_workbook.render.pages.letters import dotted_letter, letter_extent, row_room

    shapes = digit_shapes(n, ctx.numerals)
    g = shapes[0].guides
    scale = cap / (g.base - g.top)
    above, below = row_room(shapes[0], cap)
    top = 5.0 + above
    height = top + cap + max(7.0, below + 4.0)

    def guide(units: float, color: str, stroke: float, dash: str = "none") -> str:
        yy = top + (units - g.top) * scale
        return draw.el(
            "path",
            d=draw.d_path(("M", (2, yy)), ("L", (width - 2, yy))),
            stroke=color,
            stroke_width=stroke,
            stroke_dasharray=dash,
        )

    body = [guide(g.top, "#9BB7E0", 0.5), guide(g.base, "#E27D63", 0.6)]
    if g.mid is not None:
        body.append(guide(g.mid, "#9BB7E0", 0.45, "2 1.6"))
    extents = [letter_extent(sh) for sh in shapes]
    widths = [(e[2] - e[0]) * scale for e in extents]
    gap = 7.0
    copy_w = sum(widths) + gap * (len(shapes) - 1)
    step = copy_w + 12
    fits = int((width - 16 - copy_w) // step) + 1
    for i in range(min(count, fits)):
        cursor = width - 10 - i * step - copy_w  # the first copy at the right end, as for a single numeral
        for k, sh in enumerate(shapes):
            body.append(
                dotted_letter(
                    sh,
                    scale=scale,
                    x=cursor - extents[k][0] * scale,
                    y=top - g.top * scale,
                    first=i == 0,
                    number=_numbered_from(ctx, k),  # the second digit's stroke follows the first's
                )
            )
            cursor += widths[k] + gap
    return draw.svg(width, height, "".join(body), "trace-row")


def _rows(ctx: PageContext, numbers: list[int]) -> list[tuple[int, float, float]]:
    pitch = H / max(len(numbers), 1)
    return [(n, i * pitch, pitch) for i, n in enumerate(numbers)]


@page_type("journey-number-trace")
def number_trace(ctx: PageContext) -> Built:
    """Trace the numerals (1–10, in the book's numerals) from the green dot; each row shows the amount."""
    from qamra_workbook.render.pages.letters import tracing_row
    from qamra_workbook.render.pages.workbook_arabic import row_svg
    from qamra_workbook.render.pages.workbook_math import number_shape

    numbers = [int(n) for n in ctx.page.params.get("numbers", [1, 2, 3, 4, 5])]
    problems = [] if all(1 <= n <= 10 for n in numbers) else ["numerals 1–10"]
    body = []
    for n, y, pitch in _rows(ctx, numbers):
        body.append(card(0, y + 1, W, pitch - 4, r=7))
        body.append(card(W - 40, y + 4, 36, pitch - 10, r=6, fill=ctx.style.tint, stroke="none"))
        body.append(
            text(
                ctx.num(n),
                W - 22,
                y + pitch / 2 + (pitch - 10) * 0.28,
                min(pitch - 14, 22.0),
                cls="wb-num",
                color=ctx.style.deep,
            )
        )
        body.append(ten_frame(W - 84, y + pitch / 2 - 7, 38, n, ctx.style.color))
        if n < 10:
            shape = number_shape(ctx, n)
            row, _ = row_svg(
                tracing_row(shape, width=W - 94, cap=min(20.0, pitch - 14), count=4, number=ctx.num),
                5,
                y + pitch / 2 - 12,
            )
            body.append(row)
        else:  # ten is two digits: 1 then 0, side by side
            row, _ = row_svg(digits_row(ctx, n, W - 94, min(20.0, pitch - 14), 3), 5, y + pitch / 2 - 12)
            body.append(row)
    return Built({"svg": svg(body)}, None, problems)


@page_type("journey-number-write")
def number_write(ctx: PageContext) -> Built:
    """Write each numeral next to its model: a dotted one to trace, then three empty boxes."""
    from qamra_workbook.render.pages.letters import tracing_row
    from qamra_workbook.render.pages.workbook_arabic import row_svg
    from qamra_workbook.render.pages.workbook_math import number_shape

    numbers = [int(n) for n in ctx.page.params.get("numbers", [1, 2, 3, 4, 5])]
    body = []
    for n, y, pitch in _rows(ctx, numbers):
        body.append(card(0, y + 1, W, pitch - 4, r=7))
        body.append(card(W - 34, y + 4, 30, pitch - 10, r=6, fill=ctx.style.tint, stroke="none"))
        body.append(
            text(
                ctx.num(n),
                W - 19,
                y + pitch / 2 + (pitch - 10) * 0.28,
                min(pitch - 14, 22.0),
                cls="wb-num",
                color=ctx.style.deep,
            )
        )
        cap = min(20.0, pitch - 14)
        if n < 10:
            model_x, box_w = W - 74, 28.0
            row, _ = row_svg(
                tracing_row(number_shape(ctx, n), width=34, cap=cap, count=1, number=ctx.num),
                model_x,
                y + pitch / 2 - 12,
            )
        else:  # ten: both digits in the model, and narrower boxes to fit
            model_x, box_w = W - 86, 26.0
            row, _ = row_svg(digits_row(ctx, n, 46, cap, 1), model_x, y + pitch / 2 - 12)
        body.append(row)
        for k in range(3):
            bx = model_x - 6 - (k + 1) * box_w - k * 4
            body.append(
                card(
                    bx,
                    y + 8,
                    box_w,
                    pitch - 20,
                    r=5,
                    fill="#FFFFFF",
                    stroke="#8C90A6",
                    dash="3 2.4",
                    width=0.7,
                )
            )
            body.append(draw.start_dot((bx + box_w - 6, y + 14), 1.5))
    return Built({"svg": svg(body)}, None, [] if all(1 <= n <= 10 for n in numbers) else ["numerals 1–10"])


@page_type("journey-number-intro")
def number_intro(ctx: PageContext) -> Built:
    """Meet 6–10: the numeral, its word and its ten frame; join each numeral to the frame with that amount."""
    numbers = [int(n) for n in ctx.page.params.get("numbers", [6, 7, 8, 9, 10])]
    words = {
        6: "سِتَّة",
        7: "سَبْعَة",
        8: "ثَمانِيَة",
        9: "تِسْعَة",
        10: "عَشَرَة",
        1: "واحِد",
        2: "اثْنانِ",
        3: "ثَلاثَة",
        4: "أَرْبَعَة",
        5: "خَمْسَة",
    }
    order = list(numbers)
    shuffler = ctx.rng("intro")
    while order == numbers:
        shuffler.shuffle(order)
    body = join_columns(
        lambda i, x, y, s: (
            text(ctx.num(numbers[i]), x + s * 0.7, y + s * 0.62, s * 0.55, cls="wb-num", color=ctx.style.deep)
            + text(words[numbers[i]], x + s * 0.25, y + s * 0.62, s * 0.16, cls="wb-word", color="#676B83")
        ),
        lambda j, x, y, s: ten_frame(x, y + s * 0.28, s, order[j], ctx.style.color),
        len(numbers),
        [order.index(n) for n in numbers],
    )
    return Built(
        {"svg": svg(body)},
        [f"{ctx.num(n)}: {words[n]}" for n in numbers],
        [] if all(1 <= n <= 10 for n in numbers) else ["1–10"],
    )


@page_type("journey-count-frame")
def count_frame(ctx: PageContext) -> Built:
    """Count a group of 6–10 things and colour that many counters in the ten frame (or draw a dot each)."""
    numbers = [int(n) for n in ctx.page.params.get("numbers", [6, 7])]
    things = [pid(str(w)) for w in ctx.page.params.get("items", ["bird"])]
    body, key = [], []
    for k, (n, y, pitch) in enumerate(_rows(ctx, numbers)):
        thing = things[k % len(things)]
        body.append(card(0, y + 1, W, pitch - 4, r=8))
        size = min((pitch - 14) / 2, 15.0)
        rows = (n + 4) // 5
        top = y + 1 + (pitch - 4 - rows * (size + 3) + 3) / 2  # the things sit in the middle of their card
        for j in range(n):
            r, c = divmod(j, 5)
            body.append(picture(thing, W - 8 - (c + 1) * (size + 2.5), top + r * (size + 3), size))
        body.append(draw.arrow((W - 8 - 5 * (size + 2.5) - 6, y + pitch / 2), 180, 4, "#E5CD9E"))
        body.append(ten_frame(8, y + pitch / 2 - 7, 68, 0, ctx.style.color))
        body.append(ten_frame(8, y + pitch / 2 - 7, 68, n, ctx.style.color, "key-ring"))
        key.append(f"{PICTURES[thing].word_ar}: {ctx.num(n)}")
    return Built({"svg": svg(body)}, key, [] if all(6 <= n <= 10 for n in numbers) else ["6–10 here"])


@page_type("journey-before-after")
def before_after(ctx: PageContext) -> Built:
    """The number before and the number after (1–10): a number line to look at, then rows to fill."""
    numbers = [int(n) for n in ctx.page.params.get("numbers", [2, 5, 7, 9])]
    problems = [] if all(2 <= n <= 9 for n in numbers) else ["numbers 2–9 have a neighbour on each side"]
    body = [card(0, 0, W, 30, r=8, fill=SOFT, stroke="none")]
    body.append(draw.path(f"M{W - 10} 18 L10 18", stroke=INK, width=0.8))
    for k in range(1, 11):
        x = W - 10 - (k - 0.5) * (W - 20) / 10
        body.append(
            draw.el("circle", cx=x, cy=18, r=5.5, fill="#FFFFFF", stroke=ctx.style.color, stroke_width=0.8)
        )
        body.append(text(ctx.num(k), x, 20.4, 6, cls="wb-num", color="#1C2140"))
    pitch = (H - 36) / len(numbers)
    key = []
    for i, n in enumerate(numbers):
        y = 36 + i * pitch
        body.append(card(0, y + 1, W, pitch - 4, r=8))
        cy = y + pitch / 2
        for k, (dx, value) in enumerate(((0.0, n), (44.0, n - 1), (-44.0, n + 1))):
            cx = W / 2 + dx
            if k == 0:
                body.append(card(cx - 15, cy - 15, 30, 30, r=6, fill=ctx.style.tint, stroke="none"))
                body.append(text(ctx.num(value), cx, cy + 7, 18, cls="wb-num", color=ctx.style.deep))
            else:
                body.append(
                    card(
                        cx - 15,
                        cy - 15,
                        30,
                        30,
                        r=6,
                        fill="#FFFFFF",
                        stroke="#8C90A6",
                        dash="3 2.4",
                        width=0.7,
                    )
                )
                body.append(text(ctx.num(value), cx, cy + 7, 18, cls="wb-num key-ring", color="#E0483A"))
        body.append(text("قَبْلَ", W / 2 + 44, cy - 19, 4.6, cls="wb-label", color="#676B83"))
        body.append(text("بَعْدَ", W / 2 - 44, cy - 19, 4.6, cls="wb-label", color="#676B83"))
        key.append(f"{ctx.num(n - 1)} ← {ctx.num(n)} → {ctx.num(n + 1)}")
    return Built({"svg": svg(body)}, key, problems)


def _problems(raw: list[object]) -> list[tuple[int, int, str]]:
    out = []
    for p in raw:
        a, op, b = str(p).replace("−", "-").split()
        out.append((int(a), int(b), op))
    return out


@page_type("journey-picture-sum")
def picture_sum(ctx: PageContext) -> Built:
    """Add with pictures (`op: +`): count both groups, one on each row, and write the total; or take away
    (`op: -`): cross out the ones that went and write what is left. Answers stay within `max`."""
    params = ctx.page.params
    items = [pid(str(w)) for w in params.get("items", ["apple"])]
    problems_ = _problems(list(params.get("problems", [])))
    top = int(params.get("max", 10))
    checks = [
        f"{a} {op} {b} is outside 0–{top}"
        for a, b, op in problems_
        if not 0 <= (a + b if op == "+" else a - b) <= top
    ]
    checks += [f"{a} + {b}: a group of at most six" for a, b, op in problems_ if op == "+" and max(a, b) > 6]
    pitch = H / max(len(problems_), 1)
    ch = pitch - 4
    zone = (72.0, W - 8.0)  # the pictures; the equation and its answer box sit left of them
    gap = 11.0  # between the two groups of an addition: the plus sign sits in it
    body, key = [], []
    for i, (a, b, op) in enumerate(problems_):
        y = i * pitch
        thing = items[i % len(items)]
        body.append(card(0, y + 1, W, ch, r=8))
        per_row = 6 if op == "+" else 5
        n_rows = 2 if op == "+" else (a + 4) // 5
        spread = gap if op == "+" else 4.0
        size = min(
            18.0,
            (ch - 10 - (n_rows - 1) * spread) / n_rows,
            (zone[1] - zone[0] - (per_row - 1) * 2.5) / per_row,
        )
        first = y + 1 + (ch - n_rows * size - (n_rows - 1) * spread) / 2
        if op == "+":
            cells = [(0, c) for c in range(a)] + [(1, c) for c in range(b)]
        else:
            cells = [divmod(j, per_row) for j in range(a)]
        for j, (r, c) in enumerate(cells):
            x, py = zone[1] - (c + 1) * size - c * 2.5, first + r * (size + spread)
            body.append(picture(thing, x, py, size))
            if op == "-" and j >= a - b:
                body.append(
                    draw.path(
                        f"M{x} {py} L{x + size} {py + size} M{x + size} {py} L{x} {py + size}",
                        stroke="#E0483A",
                        width=1.1,
                        class_="key-line",
                    )
                )
        if op == "+":  # a plus between the two groups, and a hairline under the first
            mid = first + size + gap / 2
            body.append(text("+", (zone[0] + zone[1]) / 2, mid + 2.4, 7, cls="wb-num", color="#8C90A6"))
        answer = a + b if op == "+" else a - b
        sign = "+" if op == "+" else "−"
        body.append(
            text(
                f"{ctx.num(a)} {sign} {ctx.num(b)} =", 66, y + pitch / 2 + 4.6, 11, cls="wb-num", anchor="end"
            )
        )
        body.append(
            card(
                6, y + pitch / 2 - 12, 24, 24, r=6, fill="#FFFFFF", stroke="#8C90A6", dash="3 2.4", width=0.7
            )
        )
        body.append(
            text(ctx.num(answer), 18, y + pitch / 2 + 5.6, 14, cls="wb-num key-ring", color="#E0483A")
        )
        key.append(f"{ctx.num(a)} {sign} {ctx.num(b)} = {ctx.num(answer)}")
        if i == 0 and ctx.page.example:
            body.append(text(ctx.num(answer), 18, y + pitch / 2 + 5.6, 14, cls="wb-num", color="#8C90A6"))
    return Built({"svg": svg(body)}, key, checks)


@page_type("journey-front-behind")
def front_behind(ctx: PageContext) -> Built:
    """In front of and behind a tree: one cat hides behind the trunk, the other stands in front of it (colour
    that one); and left and right: circle what is on the right of the tree."""
    body = [
        card(0, 0, W, 142, r=10, fill="#F4F9FD", stroke="none"),
        card(0, 112, W, 30, r=8, fill="#DDEFD6", stroke="none"),
    ]
    body.append(picture("cat", 88, 72, 44, "line"))  # behind the tree: the trunk hides the left of its face
    body.append(picture("tree", 38, 2, 110))
    body.append(picture("cat", 52, 86, 44, "line"))  # in front of the tree: whole, lower, over the trunk
    body.append(picture("cat", 52, 86, 44).replace("<svg", '<svg class="key-ring"', 1))
    body.append(card(0, 148, W, 56, r=10, fill="#FFF6F2", stroke="none"))
    body.append(
        text(
            "ضَعْ دائِرَةً حَوْلَ ما عَلى يَمينِ الشَّجَرَةِ", W - 8, 160, 5.2, cls="wb-label", color="#676B83", anchor="end"
        )
    )
    body.append(picture("tree", 73, 164, 40))
    body.append(picture("kite", 24, 164, 34))
    body.append(picture("ball", 128, 168, 30))
    body.append(ring_at(143, 183, 20, 20))
    body.append(text("يَسار", 14, 200, 4.6, cls="wb-label", color="#8C90A6", anchor="start"))
    body.append(text("يَمين", W - 14, 200, 4.6, cls="wb-label", color="#8C90A6", anchor="end"))
    return Built(
        {"svg": svg(body)}, ["القطة التي أمام الشجرة: التي على يسار الجذع وتغطّيه؛ على يمين الشجرة: الكرة"]
    )
