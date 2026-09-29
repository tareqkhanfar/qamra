"""Journey math pages for stage 1 (Addendum 6 §4.7; decision 2026-09-28 §3): equal groups, the numerals 1–5
seen (never written) with their dots, above and below, inside and outside, near and far. Quantities are
drawn exactly and checked."""

from __future__ import annotations

from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_kit import SOFT, H, W, card, join_columns, picture, pid, svg, text
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
