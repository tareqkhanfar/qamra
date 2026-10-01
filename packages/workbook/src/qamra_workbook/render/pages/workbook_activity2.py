"""«دوسية التأسيس» Volume 2 activities: cut out a story's pictures and paste them in order, draw the missing
part, find hidden things in a busy picture, and colour by letter (the review week's picture)."""

from __future__ import annotations

from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import art, draw
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    arabic_shape,
    card,
    fit_lines,
    glyph,
    pic,
    ring_at,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_pen import OUTLINES
from qamra_workbook.render.registry import Built, PageContext, page_type

# draft: educator review: the story «المطر ينزل فتنبت الزهرة»
STORY = ("cloud", "raindrop", "sprout", "flower")
ORDER_AR = ("أَوَّلًا", "ثُمَّ", "بَعْدَ ذَلِكَ", "أَخيرًا")
# what is missing: the picture, the patch that hides a part (x, y, w, h in the 100-box), the part's name
MISSING = (
    ("car", (14, 58, 28, 26), "العجلة"),
    ("house", (38, 62, 24, 30), "الباب"),
    ("table", (70, 46, 18, 46), "الرِّجل"),
    ("umbrella", (44, 56, 14, 40), "المقبض"),
)
HIDDEN_POOL = (
    "apple",
    "star",
    "key",
    "ball",
    "fish",
    "cat",
    "duck",
    "car",
    "house",
    "flower",
    "heart",
    "moon",
    "bee",
    "cup",
    "book",
    "tree",
    "sun",
    "hat",
    "bell",
    "crown",
)


@page_type("story-sequence")
def story_sequence(ctx: PageContext) -> Built:
    """Four numbered frames on top; the story's pictures below, shuffled, to cut and paste in order."""
    r = ctx.rng("story")
    order = list(range(4))
    while order == [0, 1, 2, 3]:
        r.shuffle(order)
    body = []
    fw = (W - 18) / 4
    for k in range(4):
        x = W - (k + 1) * (fw + 4) + 4
        body.append(card(x, 8, fw, fw + 14, r=5, fill="#FFFFFF", stroke="#B8B2A6", dash="2.4 1.6"))
        body.append(draw.el("circle", cx=x + fw - 6, cy=14, r=4.5, fill=ctx.style.color))
        body.append(text(ctx.num(k + 1), x + fw - 6, 15.8, 4.6, cls="wb-num", color="#FFFFFF"))
        body.append(text(ORDER_AR[k], x + fw / 2, fw + 18, 4.2, color=ctx.style.deep))
        body.append(pic(STORY[k], x + 4, 18, fw - 8, class_="key-ring"))
    body.append(
        text(
            "أَقُصُّ الصُّوَرَ عَلى الخَطِّ المُتَقَطِّعِ وَأُلْصِقُها بِالتَّرْتيبِ",
            W - 8,
            fw + 34,
            4.6,
            anchor="end",
            color=ctx.style.deep,
        )
    )
    body.append(
        draw.el(
            "svg", art.glyph("scissors", INK, 1.8), x=4, y=fw + 27, width=9, height=9, viewBox="0 0 24 24"
        )
    )
    y0 = fw + 40
    ph = min(204 - y0 - 6, fw + 6)
    for k, i in enumerate(order):
        x = W - (k + 1) * (fw + 4) + 4
        body.append(
            draw.el(
                "rect",
                x=x - 2,
                y=y0,
                width=fw + 4,
                height=ph + 4,
                fill="none",
                stroke=INK,
                stroke_width=0.6,
                stroke_dasharray="2.4 1.6",
            )
        )
        body.append(pic(STORY[i], x + 4, y0 + 4, fw - 8))
    answer = ["الترتيب: " + " ← ".join(PICTURES[t].word_ar for t in STORY)]
    return Built({"svg": svg(body)}, answer, [])


@page_type("missing-part")
def missing_part(ctx: PageContext) -> Built:
    """Four things with a part missing: draw it so the thing works again (the key shows the whole thing)."""
    body, answer = [], []
    for k, (thing, (px, py, pw, ph), name) in enumerate(MISSING):
        row, col = divmod(k, 2)
        x, y = W - (col + 1) * (W / 2) + 4, row * 102
        body.append(card(x, y + 2, W / 2 - 8, 96, r=7))
        size = 70.0
        ox, oy = x + (W / 2 - 8 - size) / 2, y + 8
        body.append(pic(thing, ox, oy, size))
        s = size / 100
        body.append(
            draw.el("rect", x=ox + px * s, y=oy + py * s, width=pw * s, height=ph * s, fill="#FFFFFF")
        )
        body.append(pic(thing, ox, oy, size, class_="key-ring"))
        body.append(text("ماذا يَنْقُصُ؟", x + W / 4 - 4, y + 90, 4.6, color=ctx.style.deep))
        answer.append(f"{PICTURES[thing].word_ar}: {name}")
    return Built({"svg": svg(body)}, answer, [])


@page_type("hidden-pictures")
def hidden_pictures(ctx: PageContext) -> Built:
    """Find the five things shown on top among many line-art things, and colour them."""
    count = int(ctx.page.params.get("hidden", 5))
    r = ctx.rng("hidden")
    targets = r.sample(HIDDEN_POOL, count)
    others = [t for t in HIDDEN_POOL if t not in targets]
    cells = targets + r.sample(others, 20 - count)
    r.shuffle(cells)
    body = [card(0, 0, W, 34, r=7, fill=ctx.style.tint, stroke="none")]
    body.append(text("أَبْحَثُ عَنْ هَذِهِ الأَشْياءِ وَأُلَوِّنُها", W - 6, 9, 4.6, anchor="end", color=ctx.style.deep))
    for k, thing in enumerate(targets):
        body.append(pic(thing, W - 30 - k * 30, 11, 20))
    body.append(card(0, 40, W, 164, r=8))
    cols, rows = 5, 4
    cw, ch = (W - 8) / cols, 156 / rows
    for k, thing in enumerate(cells):
        row, col = divmod(k, cols)
        cx, cy = W - 4 - (col + 0.5) * cw, 44 + (row + 0.5) * ch
        size = min(cw, ch) - 8
        body.append(pic(thing, cx - size / 2, cy - size / 2, size, "line"))
        if thing in targets:
            body.append(ring_at(cx, cy, size / 2 + 2, size / 2 + 2))
    return Built(
        {"svg": svg(body)}, ["الأشياء المخفية: " + "، ".join(PICTURES[t].word_ar for t in targets)], []
    )


def _inside(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


COLOR_BY = (("#E5604E", "أحمر"), ("#5E86D6", "أزرق"), ("#F7C84A", "أصفر"), ("#6FAE5F", "أخضر"))


@page_type("color-by-letter")
def color_by_letter(ctx: PageContext) -> Built:
    """A fish made of cells, each with a letter; the legend gives each letter a colour."""
    letters = [str(c) for c in ctx.page.params.get("letters", ["ر", "ز", "س", "ش"])][:4]
    r = ctx.rng("color")
    body = [card(0, 0, W, 22, r=7, fill=ctx.style.tint, stroke="none")]
    for k, char in enumerate(letters):
        color, _ = COLOR_BY[k]
        x = W - 12 - k * 46
        body.append(draw.el("circle", cx=x, cy=11, r=5, fill=color))
        shape = arabic_shape(char)
        body.append(glyph(shape, *fit_lines(shape, x - 26, 3, 16, 16), color=INK, width=14))
        body.append(text("=", x - 9, 13, 5, color=INK))
    outline = Stroke(OUTLINES["fish"])
    poly = [(x * 0.95 + 5, y * 0.85 + 30) for x, y in outline.polyline]
    body.append(draw.el("path", d=draw.polyline(poly) + " Z", fill="#FFFFFF", stroke=INK, stroke_width=1.2))
    counts = dict.fromkeys(letters, 0)
    cell = 17.0
    for row in range(int(150 / cell)):
        for col in range(int(W / cell) + 1):
            cx, cy = col * cell + cell / 2, 32 + row * cell + cell / 2
            if not _inside(cx, cy, poly):
                continue
            char = r.choice(letters)
            counts[char] += 1
            body.append(
                draw.el(
                    "rect",
                    x=cx - cell / 2,
                    y=cy - cell / 2,
                    width=cell,
                    height=cell,
                    fill="none",
                    stroke="#B8B2A6",
                    stroke_width=0.35,
                )
            )
            shape = arabic_shape(char)
            body.append(glyph(shape, *fit_lines(shape, cx - 5, cy - 5, 10, 10), color=INK, width=13))
    body.append(draw.el("path", d=draw.polyline(poly) + " Z", fill="none", stroke=INK, stroke_width=1.2))
    answer = ["، ".join(f"{c} {COLOR_BY[k][1]} ({ctx.num(counts[c])})" for k, c in enumerate(letters))]
    problems = [] if all(counts.values()) else ["a letter of the legend has no cell"]
    return Built({"svg": svg(body)}, answer, problems)
