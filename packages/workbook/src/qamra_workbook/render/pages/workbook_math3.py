"""«دوسية التأسيس» Volume 3 math (Addendum 5 §3, decision 5): the numbers 11–20 with tens and ones in
pictures only (a bundle of ten tied with a bow, and loose ones), comparing numbers to 20 and the number
lines. Adding and subtracting live in `workbook_sums3`. Numerals, number lines and number sentences read left
to right, like every numeral; the Arabic around them reads right to left."""

from __future__ import annotations

from qamra_workbook.digits import digit_shapes
from qamra_workbook.geometry import bounds
from qamra_workbook.pictures import PICTURES  # noqa: F401  (re-exported for the review module)
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import dotted_letter
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
from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES
from qamra_workbook.render.pages.workbook_math2 import group_any, numeral_any
from qamra_workbook.render.registry import Built, PageContext, page_type

TEN_PICTURES = ("apple", "star", "ball", "flower", "fish")
RIBBON, KNOT = "#E27D63", "#C9604A"
PLUS, MINUS, EQUALS = "+", "−", "="
LRI, PDI, LRM = "\u2066", "\u2069", "\u200e"  # isolate a left-to-right run; a left-to-right mark


def ltr(s: str) -> str:
    """`s` as one left-to-right run for the answer key, whose lines are Arabic: «٣ + ٢ = ٥» stays so. The
    marks matter: Arabic-Indic digits turn the signs between them right-to-left, and an isolate alone does
    not undo that."""
    return f"{LRI}{s.replace(' ', f'{LRM} {LRM}')}{PDI}"


def key_wrap(markup: str) -> str:
    """Drawn only in the answer key: the whole markup (a numeral of two digits is two groups) in one group."""
    return f'<g class="key-line">{markup}</g>'


def group_pics(picture: str, count: int, x: float, y: float, w: float, h: float) -> str:
    """`count` pictures (0–10) in a box, tagged for the quantity checks: Volume 2's `group_any`, with seven
    laid out as 3 + 3 + 1 (its seventh sits on top of the sixth, so a child would count six)."""
    if count != 7:
        return group_any(picture, count, x, y, w, h)
    size = min(w / 3, h / 3) * 0.8
    spots = [((c + 0.5) / 3, (r + 0.5) / 3) for r in range(2) for c in range(3)] + [(0.5, 5 / 6)]
    items = "".join(
        pic(picture, x + u * w - size / 2, y + v * h - size / 2, size, data_count_item=picture)
        for u, v in spots
    )
    return f'<g data-count="7" data-picture="{picture}">{items}</g>'


def ten_bundle(x: float, y: float, w: float, h: float, picture: str) -> str:
    """A ten: two rows of five in a box tied with a ribbon bow (the bundle children meet before place value).
    The bow sits on the top edge inside the (x, y, w, h) footprint, so nothing covers the pictures."""
    top, box_h = y + 3.0, h - 3.0
    cell_w, cell_h = (w - 4) / 5, (box_h - 4) / 2
    size = min(cell_w, cell_h) - 0.6
    items = "".join(
        pic(
            picture,
            x + 2 + (k % 5) * cell_w + (cell_w - size) / 2,
            top + 2 + (k // 5) * cell_h + (cell_h - size) / 2,
            size,
            data_count_item=picture,
        )
        for k in range(10)
    )
    box = draw.el(
        "rect", x=x, y=top, width=w, height=box_h, rx=3, fill="#FFF6F2", stroke=RIBBON, stroke_width=0.9
    )
    cx = x + w / 2
    bow = "".join(
        draw.el(
            "ellipse",
            cx=cx + s * 2.7,
            cy=y + 1.7,
            rx=2.7,
            ry=1.4,
            fill=RIBBON,
            transform=f"rotate({-s * 18} {draw.n(cx + s * 2.7)} {draw.n(y + 1.7)})",
        )
        for s in (-1, 1)
    )
    knot = draw.el("circle", cx=cx, cy=y + 2.3, r=1.3, fill=KNOT)
    return f'<g data-ten="{picture}">{box}{items}{bow}{knot}</g>'


def teen_group(n: int, x: float, y: float, w: float, h: float, picture: str) -> str:
    """`n` (10–20) as bundles of ten and loose ones three to a row, in a box w × h; tagged with the count."""
    tens, ones = divmod(n, 10)
    bw = w * 0.52 if tens == 1 else w * 0.44
    bh = h * 0.94
    out = [ten_bundle(x + w - bw - k * (bw + 4), y + (h - bh) / 2, bw, bh, picture) for k in range(tens)]
    if ones:
        lw = w - tens * (bw + 4) - 2
        rows = -(-ones // 3)  # three to a row: easy to see as 3 + 3 + 1
        size = min(lw / 3 - 1.4, (bh - 4) / rows - 1.4, ((bw - 4) / 5 - 0.6) * 1.25, 11.0)
        grid_w, grid_h = min(ones, 3) * (size + 1.4), rows * (size + 1.4)
        gx, gy = x + (lw - grid_w) / 2, y + (h - grid_h) / 2
        for k in range(ones):
            row, col = divmod(k, 3)
            out.append(
                pic(picture, gx + col * (size + 1.4), gy + row * (size + 1.4), size, data_count_item=picture)
            )
    return f'<g data-count="{n}">{"".join(out)}</g>'


@page_type("teen-quantity-match")
def teen_quantity_match(ctx: PageContext) -> Built:
    numbers = [int(x) for x in ctx.page.params.get("numbers", [11, 12, 13, 14, 15])]
    r = ctx.rng("teens")
    groups = list(numbers)
    for _ in range(50):
        r.shuffle(groups)
        if all(a != b for a, b in zip(groups, numbers, strict=True)):
            break
    pitch = 204 / len(numbers)
    body, key = [], []
    for i, n in enumerate(numbers):
        y = i * pitch + pitch / 2
        body.append(card(W - 40, y - pitch / 2 + 2, 36, pitch - 4, r=6, fill=ctx.style.tint, stroke="none"))
        body.append(numeral_any(ctx, n, W - 22, y, min(22, pitch - 12), ctx.style.deep))
        body.append(draw.el("circle", cx=W - 46, cy=y, r=1.8, fill="#FFFFFF", stroke=INK, stroke_width=0.7))
    for i, n in enumerate(groups):
        y = i * pitch + pitch / 2
        body.append(card(4, y - pitch / 2 + 2, 110, pitch - 4, r=6))
        body.append(teen_group(n, 8, y - pitch / 2 + 4, 102, pitch - 8, TEN_PICTURES[i % len(TEN_PICTURES)]))
        body.append(draw.el("circle", cx=120, cy=y, r=1.8, fill="#FFFFFF", stroke=INK, stroke_width=0.7))
        j = numbers.index(n)
        key.append(
            draw.path(
                draw.polyline([(W - 46, j * pitch + pitch / 2), (120, y)]),
                stroke="#E0483A",
                width=1.1,
                class_="key-line",
            )
        )
    return Built({"svg": svg(body + key)}, ["كل عدد بعشرته وآحاده"], [])


def numeral_trace(
    ctx: PageContext, n: int, right: float, top: float, cap: float, *, first: bool
) -> tuple[str, float]:
    """The numeral in dotted strokes, `cap` mm tall, its right edge at `right` and its top line at `top`
    (digits read left to right, each placed by its ink, not its design box). Returns (markup, left edge)."""
    shapes = digit_shapes(n, ctx.numerals)
    scale, gap = cap / 100, cap * 0.28
    inks = [bounds(list(s.strokes)) for s in shapes]
    widths = [max((x1 - x0) * scale, cap * 0.18) for x0, _, x1, _ in inks]
    left = right - sum(widths) - gap * (len(shapes) - 1)
    x, out = left, []
    for shape, (x0, _, x1, _), width in zip(shapes, inks, widths, strict=True):
        dx = x + width / 2 - (x0 + x1) / 2 * scale
        out.append(dotted_letter(shape, scale=scale, x=dx, y=top - 10 * scale, first=first, number=ctx.num))
        x += width + gap
    return "".join(out), left


@page_type("teen-trace")
def teen_trace(ctx: PageContext) -> Built:
    """Each number 11–20 with its bundle picture: a dotted copy with arrows, a second dotted copy, then room
    on the same lines to write it alone (start dot)."""
    numbers = [int(x) for x in ctx.page.params.get("numbers", [11, 12, 13, 14, 15])]
    pitch = 204 / len(numbers)
    body = []
    for i, n in enumerate(numbers):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 3, r=6))
        body.append(teen_group(n, W - 70, y + 4, 64, pitch - 9, TEN_PICTURES[i % len(TEN_PICTURES)]))
        cap = min(pitch - 17, 22.0)
        top = y + 1 + (pitch - 3 - cap) / 2
        for color, yy in (("#9BB7E0", top), ("#E27D63", top + cap)):
            body.append(
                draw.el(
                    "path", d=draw.d_path(("M", (6, yy)), ("L", (W - 76, yy))), stroke=color, stroke_width=0.5
                )
            )
        right = W - 82
        for k in range(2):
            part, left = numeral_trace(ctx, n, right, top, cap, first=k == 0)
            body.append(part)
            right = left - 13
        body.append(draw.start_dot((right - 2, top + 2.5), 1.8))
    return Built({"svg": svg(body)}, None, [])


@page_type("count-to-twenty")
def count_to_twenty(ctx: PageContext) -> Built:
    numbers = [int(x) for x in ctx.page.params.get("numbers", list(range(11, 21)))]
    r = ctx.rng("count20")
    counts = r.sample(numbers, 4)
    body, answer = [], []
    for i, n in enumerate(counts):
        y = i * 51
        body.append(card(0, y + 1, W, 47, r=7))
        body.append(teen_group(n, W - 96, y + 5, 90, 39, TEN_PICTURES[i]))
        options = sorted({n, *r.sample([m for m in numbers if m != n], 2)})
        for k, m in enumerate(options):
            cx = 16 + k * 28.5
            body.append(
                draw.el(
                    "rect",
                    x=cx - 12.5,
                    y=y + 11,
                    width=25,
                    height=26,
                    rx=4,
                    fill="#FFFFFF",
                    stroke="#D8C9AC",
                    stroke_width=0.6,
                )
            )
            body.append(numeral_any(ctx, m, cx, y + 24, 15))
            if m == n:
                body.append(ring_at(cx, y + 24, 13.5, 15))
        answer.append(ctx.num(n))
    return Built({"svg": svg(body)}, ["الأعداد: " + "، ".join(answer)], [])


@page_type("compare-numbers")
def compare_numbers(ctx: PageContext) -> Built:
    """Two numbers up to 20, each with its picture group under it: circle the bigger."""
    top = int(ctx.page.params.get("range", 20))
    r = ctx.rng("compare20")
    body, answer = [], []
    for i in range(3):
        y = i * 68
        a, b = r.sample(range(1, top + 1), 2)
        body.append(card(0, y + 1, W, 64, r=7))
        for k, n in enumerate((a, b)):
            cx = W * (0.72 if k == 0 else 0.28)
            body.append(numeral_any(ctx, n, cx, y + 15.5, 14))
            thing = GROUP_PICTURES[(i * 2 + k) % len(GROUP_PICTURES)]
            if n > 10:
                body.append(teen_group(n, cx - 40, y + 25, 80, 37, thing))
            else:
                body.append(group_pics(thing, n, cx - 30, y + 25, 60, 37))
            if n == max(a, b):
                body.append(ring_at(cx, y + 15, 14, 10.5))
        answer.append(f"{ctx.num(max(a, b))} أكبر من {ctx.num(min(a, b))}")
    return Built({"svg": svg(body)}, answer, [])


def sign(ch: str, cx: float, cy: float, size: float = 7.0) -> str:
    return text(ch, cx, cy + size * 0.36, size, cls="wb-num", color=INK, rtl=False)


def answer_box(
    cx: float,
    cy: float,
    n: int,
    ctx: PageContext,
    w: float = 16.0,
    h: float = 18.0,
    numeral_h: float | None = None,
) -> str:
    """A dashed box for the child's answer; the answer (all its digits) shows only in the answer key."""
    nh = h - 6 if numeral_h is None else numeral_h
    digits = len(digit_shapes(n, ctx.numerals))
    w = max(w, digits * nh * 0.62 + 2 * (digits - 1) + 6)
    box = draw.el(
        "rect",
        x=cx - w / 2,
        y=cy - h / 2,
        width=w,
        height=h,
        rx=3,
        fill="#FFFFFF",
        stroke="#B8B2A6",
        stroke_width=0.6,
        stroke_dasharray="2 1.4",
    )
    return box + key_wrap(numeral_any(ctx, n, cx, cy, nh, "#E0483A"))


def crossed_group(picture: str, count: int, gone: int, x: float, y: float, w: float, h: float) -> str:
    """`count` pictures with the last `gone` crossed out (taken away)."""
    inner = group_pics(picture, count, x, y, w, h)
    # cross the last `gone` items: they are the last <svg …> elements of the group
    parts = inner.split("<svg ")
    head, items = parts[0], parts[1:]
    out = [head]
    for k, item in enumerate(items):
        out.append("<svg " + item)
        if k >= count - gone:
            xs = item.split('x="')[1].split('"')[0]
            ys = item.split('y="')[1].split('"')[0]
            size = float(item.split('width="')[1].split('"')[0])
            x0, y0 = float(xs), float(ys)
            out.append(
                draw.path(
                    draw.d_path(
                        ("M", (x0, y0)),
                        ("L", (x0 + size, y0 + size)),
                        ("M", (x0 + size, y0)),
                        ("L", (x0, y0 + size)),
                    ),
                    stroke="#E0483A",
                    width=1.2,
                    class_="cross",
                )
            )
    return "".join(out)


Token = tuple[str, int | str]  # ("num", 3) · ("op", "+") · ("eq", "") · ("box", 5) · ("choice", "+")


def _token_width(ctx: PageContext, tok: Token, h: float) -> float:
    kind, value = tok
    if kind in ("num", "box"):
        d = len(digit_shapes(int(value), ctx.numerals))
        plain = d * h * 0.62 + 2 * (d - 1)
        return plain if kind == "num" else max(h * 1.3, plain + 8)
    return 2 * h * 0.9 + 3 if kind == "choice" else h * 0.62


def sentence_width(ctx: PageContext, tokens: list[Token], h: float, gap: float = 3.0) -> float:
    return sum(_token_width(ctx, t, h) for t in tokens) + gap * (len(tokens) - 1)


def sentence_row(
    ctx: PageContext, tokens: list[Token], x: float, cy: float, h: float, gap: float = 3.0
) -> str:
    """A number sentence left to right from `x`: numerals `h` mm tall, signs, «=», answer boxes (the answer
    only in the key) and, for «أجمع أم أطرح؟», the two sign circles with the right one ringed in the key."""
    out = []
    for kind, value in tokens:
        w = _token_width(ctx, (kind, value), h)
        cx = x + w / 2
        if kind == "num":
            out.append(numeral_any(ctx, int(value), cx, cy, h))
        elif kind in ("op", "eq"):
            out.append(sign(str(value) if kind == "op" else EQUALS, cx, cy, h * 0.55))
        elif kind == "box":
            out.append(answer_box(cx, cy, int(value), ctx, w, h * 1.3, h * 0.85))
        else:
            rad = h * 0.45
            for j, ch in enumerate((PLUS, MINUS)):
                ccx = x + rad + j * (2 * rad + 3)
                out.append(
                    draw.el(
                        "circle",
                        cx=ccx,
                        cy=cy,
                        r=rad,
                        fill="#FFFFFF",
                        stroke="#B8B2A6",
                        stroke_width=0.5,
                    )
                )
                out.append(sign(ch, ccx, cy, h * 0.5))
                if ch == value:
                    out.append(ring_at(ccx, cy, rad + 1.3, rad + 1.3))
        x += w + gap
    return "".join(out)


def numeral_compact(ctx: PageContext, n: int, cx: float, cy: float, h: float, color: str = INK) -> str:
    """A number of one or two digits `h` mm tall, centred at (cx, cy), the digits set by their ink (a thin ١
    takes a thin cell), so two-digit numerals on a crowded line stay two numerals, not a string of digits."""
    shapes = digit_shapes(n, ctx.numerals)
    scale = h / 100
    cells = [max((x1 - x0) * scale, h * 0.26) for x0, _, x1, _ in (bounds(list(s.strokes)) for s in shapes)]
    gap = h * 0.1
    x = cx - (sum(cells) + gap * (len(cells) - 1)) / 2
    out = []
    for shape, cell in zip(shapes, cells, strict=True):
        out.append(glyph(shape, *fit_lines(shape, x, cy - h / 2, cell, h), color=color, width=13))
        x += cell + gap
    return "".join(out)


def number_line(
    x: float,
    y: float,
    w: float,
    top: int,
    ctx: PageContext,
    jumps: tuple[int, int] | None = None,
    blanks: set[int] | None = None,
    start: int = 0,
    size: float = 7.0,
) -> str:
    """A number line start–top (left to right, as numerals are read) with ticks, numbers, optional jumps and
    blank boxes for numbers the child writes."""
    step = w / (top - start)
    out = [draw.path(draw.d_path(("M", (x, y)), ("L", (x + w, y))), stroke=INK, width=0.8)]
    ny = y + 4 + size * 0.7
    for k in range(start, top + 1):
        px = x + (k - start) * step
        out.append(draw.path(draw.d_path(("M", (px, y - 2)), ("L", (px, y + 2))), stroke=INK, width=0.6))
        if blanks and k in blanks:
            d = len(digit_shapes(k, ctx.numerals))
            bw = min(max(10.0, d * size * 0.62 + 2 * (d - 1) + 4), step - 1.5)
            out.append(
                draw.el(
                    "rect",
                    x=px - bw / 2,
                    y=ny - (size + 3) / 2,
                    width=bw,
                    height=size + 3,
                    rx=2,
                    fill="#FFFFFF",
                    stroke="#B8B2A6",
                    stroke_width=0.5,
                    stroke_dasharray="1.6 1.2",
                )
            )
            out.append(key_wrap(numeral_compact(ctx, k, px, ny, size, "#E0483A")))
        else:
            out.append(numeral_compact(ctx, k, px, ny, size))
    if jumps:
        a, b = jumps
        for k in range(a, a + b):
            x0, x1 = x + (k - start) * step, x + (k + 1 - start) * step
            out.append(
                draw.path(
                    f"M{x0} {y - 1} Q{(x0 + x1) / 2} {y - 12} {x1} {y - 1}", stroke="#E27D63", width=0.9
                )
            )
            out.append(draw.arrow((x1 - 0.5, y - 2), 60, 2.2))
    return "".join(out)


@page_type("number-line-fill")
def number_line_fill(ctx: PageContext) -> Built:
    """Number lines with a few numbers missing: 0–10, 10–20, then 5–15 across the ten (11 numbers each, so the
    numerals stay big enough to read and to write)."""
    top = int(ctx.page.params.get("range", 20))
    r = ctx.rng("line")
    body, answer = [], []
    spans = [(0, 10), (10, 20), (5, 15)] if top > 10 else [(0, top)] * 3
    for i, (lo, hi) in enumerate(spans):
        y = i * 68
        blanks = set(r.sample(range(lo + 1, hi), 4))
        body.append(card(0, y + 1, W, 64, r=7))
        body.append(
            number_line(10, y + 30, W - 20, hi, ctx, blanks=blanks, start=lo, size=11.0 if hi <= 10 else 10.0)
        )
        answer.append("الأعداد الناقصة: " + "، ".join(ctx.num(n) for n in sorted(blanks)))
    return Built({"svg": svg(body)}, answer, [])
