"""«ماذا تعلمت؟» (Addendum 6 §4.13): a section's closing review. It mixes short versions of the section's
missions (and earlier ones) in panels, each with a star the child colours when they can do it, and ends with
the child's character and «رائع يا {child}!». Mini tasks draw in a box and add their answer to the key."""

from __future__ import annotations

from collections.abc import Callable

from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_eye import boat
from qamra_workbook.render.pages.journey_hand import row_strokes, shape_of
from qamra_workbook.render.pages.journey_kit import (
    SOFT,
    H,
    W,
    card,
    nested,
    picture,
    silhouette,
    star,
    svg,
    text,
)
from qamra_workbook.render.pages.journey_listen import speaker
from qamra_workbook.render.pages.journey_shapes import filled
from qamra_workbook.render.pages.motor import character_image
from qamra_workbook.render.pages.workbook_common import answer_line, hook, ring_at
from qamra_workbook.render.pages.workbook_pen import traced
from qamra_workbook.render.registry import Built, PageContext, page_type

Box = tuple[float, float, float, float]  # x, y, w, h
Mini = Callable[[PageContext, Box], tuple[list[str], str]]  # → SVG, the answer (or "")


def _row(
    words: list[str], box: Box, style: str = "color", ltr: bool = False
) -> tuple[list[str], list[tuple[float, float, float]]]:
    x, y, w, h = box
    size = min(h - 6, (w - 8) / len(words) - 4)
    step = (w - 8) / len(words)
    cells = [(x + w - 4 - (k + 0.5) * step - size / 2, y + (h - size) / 2, size) for k in range(len(words))]
    if ltr:  # English minis read left to right
        cells = [(2 * x + w - cx - s, cy, s) for cx, cy, s in cells]
    return [picture(word, cx, cy, s, style) for word, (cx, cy, s) in zip(words, cells, strict=True)], cells


def _ring(cell: tuple[float, float, float]) -> str:
    x, y, s = cell
    return str(ring_at(x + s / 2, y + s / 2, s / 2 + 1.5, s / 2 + 1.5))


def odd(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    body, cells = _row(["apple", "apple", "ball", "apple"], box)
    return [*body, _ring(cells[2])], "المختلف: الكرة"


def big_small(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 6
    return [
        picture("duck", x + w - s - 10, y + 3, s),
        picture("duck", x + 14, y + h - s / 2 - 3, s / 2),
        ring_at(x + w - s / 2 - 10, y + h / 2, s / 2 + 1, s / 2),
    ], "الكبير: البطة الكبيرة"


def gone(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    top, _ = _row(["sun", "ball", "cat"], (x + w / 2, y, w / 2, h))
    shown, cells = _row(["sun", "sun", "cat"], (x, y, w / 2, h))
    sx, sy, s = cells[1]
    hole = card(sx, sy, s, s, r=3, fill="#FFFFFF", stroke="#8C90A6", dash="2.4 2")
    mark = text("؟", sx + s / 2, sy + s * 0.72, s * 0.6, cls="wb-title", color="#8C90A6")
    missing = picture("ball", sx, sy, s).replace("<svg", '<svg class="key-ring"', 1)
    arrow = draw.arrow((x + w / 2, y + h / 2), 180, 3.5)
    return [*top, arrow, shown[0], shown[2], hole, mark, missing], "اختفت الكرة"


def path(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h * 0.6
    a, b = (x + w - s - 6, y + h / 2), (x + s + 6, y + h / 2)
    road = Stroke(f"M{a[0]} {a[1]} C{x + w * 0.6} {y + 4} {x + w * 0.4} {y + h - 4} {b[0]} {b[1]}")
    return [
        picture("butterfly", x + w - s - 2, y + (h - s) / 2, s),
        picture("flower", x + 2, y + (h - s) / 2, s),
        traced(road, spacing=3.6, r=0.95, start=2),
    ], ""


def pairs(
    ctx: PageContext, box: Box, items: tuple[tuple[str, str], ...] = (("rabbit", "carrot"), ("bee", "flower"))
) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h / 2 - 3
    body = []
    for i, (a, _) in enumerate(items):
        body.append(picture(a, x + w - s - 4, y + i * (s + 4) + 1, s))
        body.append(picture(items[1 - i][1], x + 4, y + i * (s + 4) + 1, s))
        body += [
            hook(x + w - s - 8, y + i * (s + 4) + s / 2 + 1, 1.4),
            hook(x + s + 8, y + i * (s + 4) + s / 2 + 1, 1.4),
        ]
    for i in range(2):
        body.append(
            answer_line(
                (x + w - s - 8, y + i * (s + 4) + s / 2 + 1), (x + s + 8, y + (1 - i) * (s + 4) + s / 2 + 1)
            )
        )
    return body, "، ".join(f"{PICTURES[a].word_ar} ← {PICTURES[b].word_ar}" for a, b in items)


def boats(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h / 2 - 3
    body = []
    for i, spec in enumerate(("1-below", "2-above")):
        body.append(nested(boat(spec), x + w - s - 4, y + i * (s + 4) + 1, s))
        body.append(nested(boat(("2-above", "1-below")[i]), x + 4, y + i * (s + 4) + 1, s))
        body += [
            hook(x + w - s - 8, y + i * (s + 4) + s / 2, 1.4),
            hook(x + s + 8, y + i * (s + 4) + s / 2, 1.4),
        ]
        body.append(
            answer_line((x + w - s - 8, y + i * (s + 4) + s / 2), (x + s + 8, y + (1 - i) * (s + 4) + s / 2))
        )
    return body, "كل قارب بالقارب الذي له النقاط نفسها"


def sound(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    body, cells = _row(["cow", "cat", "rooster"], (x, y, w - 20, h))
    return [speaker(x + w - 10, y + h / 2, 5, 2), *body, _ring(cells[0])], "الصوت: بقرة"


def loud_soft(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    return [
        picture("drum", x + w - h - 4, y + 2, h - 4),
        speaker(x + w * 0.42, y + h / 2, h * 0.3, 3),
        speaker(x + w * 0.14, y + h / 2, h * 0.18, 1),
        ring_at(x + w * 0.42 + 3, y + h / 2, h * 0.36, h * 0.4),
    ], "الطبل: عالٍ"


def word(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    body, cells = _row(["sun", "moon"], box, "line")
    return [*body, _ring(cells[0])], "الكلمة: شمس"


def strokes(kind: str) -> Mini:
    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        x, y, w, h = box
        out = [
            traced(s, spacing=3.8, r=1.0, start=2)
            for s in row_strokes(kind, x + w - 8, x + 8, y + h / 2, h - 16)
        ]
        return out, ""

    return mini


def beach(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    third = h / 3
    out = [card(x, y + 2 * third, w, third, r=4, fill="#E1EEFA", stroke="none")]
    for kind, (y0, hh) in (("vertical", (y + third / 2, third - 6)), ("waves", (y + 2.5 * third, third - 6))):
        out += [traced(s, spacing=3.6, r=0.9, start=1.8) for s in row_strokes(kind, x + w - 8, x + 8, y0, hh)]
    grass = [
        traced(s, spacing=3.2, r=0.9, start=1.8)
        for s in row_strokes("vertical", x + w / 2 - 4, x + 8, y + 1.5 * third, third * 0.5)
    ]
    return out + grass, ""


def draw_shape(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    return [
        card(x + w * 0.35, y + 3, w * 0.62, h - 6, r=6, fill="#FFFFFF", stroke="#8C90A6", dash="3 2.4"),
        picture("crayons", x + 2, y + (h - w * 0.3) / 2, w * 0.3),
    ], ""


def shapes(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 12
    return [
        traced(shape_of(k, x + w - (i + 0.5) * w / 3, y + h / 2, s), spacing=3.4, r=0.95, start=1.9)
        for i, k in enumerate(("circle", "triangle", "square"))
    ], ""


def pattern(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = min(h - 10, w / 6 - 4)
    seq = ["circle", "triangle", "circle", "triangle", "circle", "?"]
    out = []
    for k, kind in enumerate(seq):
        cx = x + w - (k + 0.5) * w / 6
        if kind == "?":
            out.append(
                card(
                    cx - s / 2 - 2,
                    y + h / 2 - s / 2 - 2,
                    s + 4,
                    s + 4,
                    r=3,
                    fill="#FFFFFF",
                    stroke="#8C90A6",
                    dash="2.4 2",
                )
            )
            out.append(filled("triangle", cx, y + h / 2, s, "#EE8A6E", "key-ring"))
        else:
            out.append(filled(kind, cx, y + h / 2, s, "#5E86D6" if kind == "circle" else "#EE8A6E"))
    return out, "النمط: مثلث"


def sequence(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    from qamra_workbook.render.pages.journey_think import _panel

    x, y, w, h = box
    s = min(h - 12, w / 3 - 8)
    out = []
    for k, step in enumerate((2, 0, 1)):
        cx = x + w - (k + 0.5) * w / 3
        out.append(nested(_panel("seed", step), cx - s / 2, y + 1, s))
        out.append(card(cx - 7, y + s + 3, 14, 8, r=2, fill="#FFFFFF", stroke="#8C90A6", dash="2 1.6"))
    return out, "الترتيب: الصورة الثانية، ثم الثالثة، ثم الأولى"


def rule(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = min(h - 12, w / 5 - 4)
    out = []
    for k, kind in enumerate(("circle", "square", "circle", "triangle", "circle")):
        cx = x + w - (k + 0.5) * w / 5
        out.append(filled(kind, cx, y + h / 2, s, "#FFFFFF"))
        if kind == "circle":
            out.append(filled(kind, cx, y + h / 2, s, "#E5604E", "key-ring"))
    return out, "نلوّن الدوائر فقط"


def model(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    return [
        picture("fish", x + w - h * 0.5 - 4, y + 2, h * 0.5),
        picture("fish", x + 8, y + 2, h - 4, "line"),
    ], ""


def rtl(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    body, _ = _row(["sun", "moon", "house"], (x, y, w, h - 8))
    line = draw.path(f"M{x + w - 6} {y + h - 4} L{x + 10} {y + h - 4}", stroke="#E5CD9E", width=4)
    return [
        line,
        draw.start_dot((x + w - 6, y + h - 4), 2),
        draw.arrow((x + 8, y + h - 4), 180, 3.2),
        *body,
    ], ""


def boat_line(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h * 0.7
    out = [draw.path(f"M{x + w - 4} {y + h - 6} L{x + 4} {y + h - 6}", stroke="#C9B994", width=0.8)]
    out += [
        traced(
            shape_of("boat-curve", x + w - (k + 0.5) * w / 3, y + h - 6 - s * 0.3, s),
            spacing=3.4,
            r=0.95,
            start=1.9,
        )
        for k in range(3)
    ]
    return out, ""


def animals(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    body, cells = _row(["cat", "duck", "cow"], (x, y, w, h - 8), ltr=True)
    labels = [
        text(PICTURES[k].word_en, cx + s / 2, y + h - 1, 4.2, cls="wb-en", rtl=False)
        for k, (cx, _, s) in zip(("cat", "duck", "cow"), cells, strict=True)
    ]
    return [*body, *labels, _ring(cells[0])], "cat"


def colors(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    out = []
    for k, (name, hexa) in enumerate((("red", "#E5604E"), ("blue", "#5E86D6"))):
        cx = x + (k + 0.5) * w / 2
        out.append(picture("balloon", cx - (h - 10) / 2, y, h - 10, "line"))
        out.append(
            picture("balloon", cx - (h - 10) / 2, y, h - 10, main=hexa).replace(
                "<svg", '<svg class="key-ring"', 1
            )
        )
        out.append(text(name, cx, y + h - 1, 4.2, cls="wb-en", rtl=False))
    return out, "red, blue"


def count(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = min(h / 2 - 2, w / 8)
    out = [picture("apple", x + w - (k + 1) * (s + 2) - 4, y + 2, s) for k in range(3)]
    for k in range(5):
        cx = x + w - (k + 0.5) * (s + 2) - 4
        out.append(
            draw.el(
                "circle",
                cx=cx,
                cy=y + h - s / 2 - 2,
                r=s / 3,
                fill="#FFFFFF",
                stroke="#2B2E4A",
                stroke_width=0.7,
            )
        )
    return out, f"التفاح: {ctx.num(3)}"


def numeral(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    out = []
    for i, n in enumerate((2, 3)):
        yy = y + i * h / 2 + h / 4
        out.append(text(ctx.num(n), x + w - 10, yy + 4, 11, cls="wb-num", color="#2C6440"))
        out.append(hook(x + w - 22, yy, 1.4))
        m = 3 if i == 0 else 2
        out += [
            draw.el(
                "circle", cx=x + 10 + k * 7, cy=yy, r=2.6, fill="#F2B33D", stroke="#2B2E4A", stroke_width=0.5
            )
            for k in range(m)
        ]
        out.append(hook(x + 34, yy, 1.4))
    out += [
        answer_line((x + w - 22, y + h / 4), (x + 34, y + 3 * h / 4)),
        answer_line((x + w - 22, y + 3 * h / 4), (x + 34, y + h / 4)),
    ]
    return out, f"{ctx.num(2)} ← نقطتان، {ctx.num(3)} ← ثلاث نقاط"


def above(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    top = draw.el("rect", x=x + w * 0.2, y=y + h * 0.45, width=w * 0.6, height=3, fill="#C98A5B")
    legs = "".join(
        draw.el("rect", x=lx, y=y + h * 0.45 + 3, width=2.5, height=h * 0.5, fill="#A8734D")
        for lx in (x + w * 0.24, x + w * 0.74)
    )
    s = h * 0.4
    return [
        top,
        legs,
        picture("ball", x + w / 2 - s / 2, y + h * 0.45 - s, s, "line"),
        picture("ball", x + w / 2 - s / 2, y + h * 0.45 - s, s).replace("<svg", '<svg class="key-ring"', 1),
        picture("cat", x + w / 2 - s / 2, y + h - s, s, "line"),
    ], "فوق الطاولة: الكرة"


def difference(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 6
    return [
        picture("house", x + w - s - 6, y + 3, s),
        picture("house", x + 6, y + 3, s),
        picture("sun", x + 6 + s * 0.62, y, s * 0.34),
        ring_at(x + 6 + s * 0.79, y + s * 0.17, s * 0.2, s * 0.2),
    ], "الفرق: الشمس فوق البيت الثاني"


def shadow(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h / 2 - 3
    out = []
    for i, k in enumerate(("camel", "elephant")):
        yy = y + i * (s + 4) + 1
        out += [picture(k, x + w - s - 4, yy, s), silhouette(("elephant", "camel")[i], x + 4, yy, s)]
        out += [hook(x + w - s - 8, yy + s / 2, 1.4), hook(x + s + 8, yy + s / 2, 1.4)]
    out += [
        answer_line((x + w - s - 8, y + s / 2 + 1), (x + s + 8, y + s * 1.5 + 5)),
        answer_line((x + w - s - 8, y + s * 1.5 + 5), (x + s + 8, y + s / 2 + 1)),
    ]
    return out, "الجمل ← الظل الثاني، الفيل ← الظل الأول"


MINIS: dict[str, tuple[str, Mini]] = {
    "odd-one-out": ("مَن المختلف؟", odd),
    "big-small": ("كبير وصغير", big_small),
    "gone": ("ماذا اختفى؟", gone),
    "trace-path": ("أتبع الطريق", path),
    "connect-pairs": ("أصل الصور", pairs),
    "animal-sound": ("مَن الصوت؟", sound),
    "loud-soft": ("عالٍ أم منخفض؟", loud_soft),
    "word": ("أسمع الكلمة", word),
    "beach": ("مطر وعشب وأمواج", beach),
    "pen-lines": ("أتتبّع الخط", strokes("horizontal")),
    "draw-shape": ("أرسم شكلًا وألوّنه", draw_shape),
    "shapes": ("أتتبّع الأشكال", shapes),
    "pattern": ("أكمل النمط", pattern),
    "sequence": ("أرتّب القصة", sequence),
    "rule-coloring": ("ألوّن حسب القاعدة", rule),
    "like-model": ("ألوّن مثل النموذج", model),
    "right-to-left": ("من اليمين إلى اليسار", rtl),
    "boats-dots": ("قوارب ونقاط", boats),
    "boat-on-line": ("قوارب على السطر", boat_line),
    "animals": ("Animals", animals),
    "colors": ("Colors", colors),
    "counting": ("أعدّ", count),
    "numerals": ("الرقم ومجموعته", numeral),
    "above-below": ("فوق وتحت", above),
    "spot-difference": ("أجد الفرق", difference),
    "shadow": ("الظل", shadow),
}


@page_type("what-i-learned")
def what_i_learned(ctx: PageContext) -> Built:
    """Panels of mini tasks (params.tasks, keys of MINIS), a star to colour on each, and the cheer."""
    tasks = [str(t) for t in ctx.page.params.get("tasks", [])]
    problems = [f"no mini task {t!r} (have: {', '.join(MINIS)})" for t in tasks if t not in MINIS]
    tasks = [t for t in tasks if t in MINIS] or ["odd-one-out"]
    cols = 1 if len(tasks) <= 3 else 2
    rows = (len(tasks) + cols - 1) // cols
    area = 164.0
    pw, ph = (W - (cols - 1) * 6) / cols, area / rows - 6
    body, key = [], []
    for k, task in enumerate(tasks):
        r, c = divmod(k, cols)
        x, y = W - (c + 1) * pw - c * 6, r * (ph + 6)
        label, mini = MINIS[task]
        body.append(card(x, y, pw, ph, r=8))
        body.append(text(label, x + pw - 14, y + 8, 4.6, cls="wb-label", color="#676B83", anchor="end"))
        body.append(star(x + pw - 7, y + 6.5, 4))
        drawn, answer = mini(ctx, (x + 4, y + 12, pw - 8, ph - 15))
        body += drawn
        if answer:
            key.append(f"{label}: {answer}")
    cheer = ctx.text(str(ctx.page.params.get("cheer", "رائع يا {child}!")))
    body.append(card(0, area + 2, W, 204 - area - 2, r=10, fill=SOFT, stroke="none"))
    body.append(character_image(ctx, W - 36, 204, 36))
    body.append(
        text(cheer, W / 2 + 10, area + 24, 9.5, cls="wb-title", color="#1C2140", rtl=ctx.page.lang == "ar")
    )
    body += [star(26 + k * 13, area + 21, 5.5) for k in range(3)]
    return Built({"svg": svg(body), "cheer": cheer}, key or None, problems)


# ---- stages 2–3: more mini tasks, the final assessment and the observation checklist -----------------------


def _box(x: float, y: float, w: float, h: float) -> str:
    return card(x, y, w, h, r=4, fill="#FFFFFF", stroke="#8C90A6", dash="2.4 2", width=0.6)


def story_mini(story: str, steps: int) -> Mini:
    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        from qamra_workbook.render.pages.journey_think import _story_panel

        x, y, w, h = box
        s = min(h - 12, w / steps - 6)
        out = []
        order = list(range(steps))
        ctx.rng("mini-story").shuffle(order)
        for k, step in enumerate(order):
            cx = x + w - (k + 0.5) * w / steps
            out.append(nested(_story_panel(story, step), cx - s / 2, y + 1, s))
            out.append(_box(cx - 6, y + s + 3, 12, 7))
        return out, "الترتيب: " + "، ".join(str(order.index(i) + 1) for i in range(steps))

    return mini


def memory_mini(n: int) -> Mini:
    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        words = ["moon", "key", "apple", "cat", "ball", "sun"][:n]
        body, _ = _row(words, box)
        return body, "يتذكّر الصور ثم يقلب الصفحة"

    return mini


def classify_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    out = [
        filled(k, x + w - (i + 0.5) * w / 4, y + h * 0.3, h * 0.36, c)
        for i, (k, c) in enumerate(
            (("circle", "#E5604E"), ("triangle", "#5E86D6"), ("circle", "#5E86D6"), ("triangle", "#E5604E"))
        )
    ]
    out += [_box(x + w - (i + 1) * w / 2 + 6, y + h * 0.62, w / 2 - 12, h * 0.34) for i in range(2)]
    return out, "دوائر معًا ومثلثات معًا"


def maze_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 6
    x0 = x + w / 2 - s / 2
    out = [card(x0, y + 3, s, s, r=2, fill="#FFFFFF", stroke="#4F8A45", width=1.2)]
    out.append(
        draw.path(
            f"M{x0 + s * 0.33} {y + 3} L{x0 + s * 0.33} {y + 3 + s * 0.66}"
            f" M{x0 + s * 0.66} {y + 3 + s * 0.33} L{x0 + s * 0.66} {y + 3 + s}",
            stroke="#4F8A45",
            width=1.2,
        )
    )
    out.append(picture("rabbit", x + w / 2 + s / 2 + 2, y + 2, 12))
    out.append(picture("carrot", x + w / 2 - s / 2 - 14, y + h - 14, 12))
    return out, ""


def first_sound_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    body, cells = _row(["duck", "house", "fish"], box, "line")
    return [*body, _ring(cells[0]), _ring(cells[1])], "تبدأ بالباء: بطة، بيت"


def claps_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = min(h - 8, w * 0.42)
    out = [picture("butterfly", x + w - s - 2, y + (h - s) / 2, s)]
    step = min(12.0, (w - s - 12) / 4)
    out += [
        draw.el(
            "circle",
            cx=x + w - s - 8 - (k + 0.5) * step,
            cy=y + h / 2,
            r=min(4.5, step * 0.4),
            fill="#FFFFFF",
            stroke="#2B2E4A",
            stroke_width=0.6,
        )
        for k in range(4)
    ]
    return out, "فراشة: 3 مقاطع"


def waves_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    return [
        traced(s, spacing=3.2, r=0.9, start=1.8)
        for s in row_strokes("waves", x + w - 6, x + 6, y + h / 2, h * 0.5)
    ], ""


def letters_mini(chars: tuple[str, ...], style: str) -> Mini:
    """Letters to name and colour (`hollow`), to find (`find`), or to trace (`trace`)."""

    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        from qamra_workbook.render.pages.journey_letters import hollow, shape, solid

        x, y, w, h = box
        out = []
        side = min(h - 4, w / len(chars) - 6, 26.0)
        for i, ch in enumerate(chars):
            cx = x + w - (i + 0.5) * w / len(chars)
            if style == "trace":
                out.append(solid(shape(ch), cx - side / 2, y + 2, side, h - 4, "#F7C84A", ctx.num))
            elif style == "find":
                out.append(solid(shape(ch), cx - side / 2, y + 2, side, h - 4, "#1C2140"))
            else:  # hollow: an outline to colour in
                out.append(hollow(shape(ch), cx - side / 2, y + 2, side, h - 4))
        return out, "، ".join(chars)

    return mini


def complete_mini(chars: tuple[str, ...]) -> Mini:
    """Letters written halfway in ink and dotted after: the child finishes them."""

    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        from qamra_workbook.render.pages.journey_letters import partial, shape
        from qamra_workbook.render.pages.workbook_common import fit

        x, y, w, h = box
        out = []
        for i, ch in enumerate(chars):
            sh = shape(ch)
            cx = x + w - (i + 0.5) * w / len(chars)
            scale, dx, dy = fit(sh, cx - 15, y + 2, 30, h - 4, pad=2.0)
            out.append(partial(sh, scale, dx, dy, 0.55))
        return out, "، ".join(chars)

    return mini


def write_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    from qamra_workbook.render.pages.journey_letters import shape, solid

    x, y, w, h = box
    out = [solid(shape("ب"), x + w - 22, y + 2, 20, h - 4, "#E27D63", ctx.num)]
    side = min(22.0, (w - 30) / 3 - 4, h - 8)
    out += [_box(x + w - 28 - (k + 1) * (side + 4), y + (h - side) / 2, side, side) for k in range(3)]
    return out, ""


def en_letters_mini(chars: str) -> Mini:
    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        x, y, w, h = box
        out = [
            text(
                f"{c} {c.lower()}",
                x + (i + 0.5) * w / len(chars),
                y + h * 0.68,
                h * 0.5,
                cls="wb-en",
                rtl=False,
            )
            for i, c in enumerate(chars)
        ]
        return out, chars

    return mini


def count_write_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = min(h / 2 - 2, w / 8)
    out = [
        picture("star", x + w - (k % 5 + 1) * (s + 2) - 2, y + 2 + (k // 5) * (s + 2), s) for k in range(7)
    ]
    side = min(h - 8, 24.0, w - 5 * (s + 2) - 12)
    out.append(_box(x + 4, y + (h - side) / 2, side, side))
    out.append(text(ctx.num(7), x + 4 + side / 2, y + h / 2 + 3.5, 9, cls="wb-num key-ring", color="#E0483A"))
    return out, f"النجوم: {ctx.num(7)}"


def before_after_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    cx = x + w / 2
    out = [
        card(cx - 9, y + h / 2 - 9, 18, 18, r=3, fill="#E1EFE4", stroke="none"),
        text(ctx.num(5), cx, y + h / 2 + 4, 10, cls="wb-num", color="#2C6440"),
    ]
    out += [_box(cx + 14, y + h / 2 - 9, 18, 18), _box(cx - 32, y + h / 2 - 9, 18, 18)]
    out += [
        text(ctx.num(4), cx + 23, y + h / 2 + 4, 10, cls="wb-num key-ring", color="#E0483A"),
        text(ctx.num(6), cx - 23, y + h / 2 + 4, 10, cls="wb-num key-ring", color="#E0483A"),
    ]
    return out, f"{ctx.num(4)} و{ctx.num(6)}"


def more_less_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = min(h / 2 - 2, w / 12)
    out = [
        picture("apple", x + w - (k % 4 + 1) * (s + 2) - 4, y + 2 + (k // 4) * (s + 2), s) for k in range(7)
    ]
    out += [picture("apple", x + w / 2 - (k + 1) * (s + 2) - 4, y + 2, s) for k in range(3)]
    out.append(ring_at(x + w * 0.76, y + h / 2, w * 0.22, h / 2 - 1))
    return out, "الأكثر: 7 تفاحات"


def hidden_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 6
    out = [
        picture("stall", x + w / 2 - s / 2, y + 3, s),
        picture("key", x + w / 2 + s / 2 + 2, y + h - 14, 12, "line"),
        ring_at(x + w / 2 + s / 2 + 8, y + h - 8, 8, 8),
    ]
    return out, "المفتاح بجانب البسطة"


def riddle_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    body, cells = _row(["camel", "cat", "fish"], (x, y, w * 0.6, h))
    out = [
        text("لي سنام", x + w - 4, y + h / 2 + 2, 5.2, cls="wb-word", color="#1C2140", anchor="end"),
        *body,
        _ring(cells[0]),
    ]
    return out, "الجمل"


def position_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    out = [
        text(wd, x + w - (i + 0.5) * w / 3, y + h * 0.6, min(h * 0.4, w / 12), cls="wb-word", color="#1C2140")
        for i, wd in enumerate(("بَطَّة", "عُلْبَة", "كِتاب"))
    ]
    return out, "ب في الأول، الوسط، الآخر"


def harakat_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    out = [
        text(s, x + w - (i + 0.5) * w / 4, y + h * 0.68, h * 0.55, cls="wb-word", color="#1C2140")
        for i, s in enumerate(("بَ", "بُ", "بِ", "بْ"))
    ]
    return out, "يقرأ: بَ بُ بِ بْ"


def read_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 6
    out = [
        text("قَمَر", x + w - 24, y + h * 0.66, h * 0.5, cls="wb-word", color="#1C2140"),
        picture("moon", x + w - 60 - s, y + 3, s),
        picture("cat", x + w - 68 - 2 * s, y + 3, s),
        ring_at(x + w - 60 - s / 2, y + h / 2, s / 2 + 1, s / 2),
    ]
    return out, "قمر ← القمر"


def write_line_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    out = [
        text("وَلَد", x + w - 16, y + h * 0.6, h * 0.45, cls="wb-word", color="#676B83"),
        draw.path(f"M{x + w - 34} {y + h - 6} L{x + 6} {y + h - 6}", stroke="#C9B994", width=0.8),
    ]
    return out, ""


def write_alone_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 6
    return [picture("fish", x + w - s - 2, y + 3, s), _box(x + 6, y + 4, w - s - 16, h - 8)], "سمك"


def ltr(markup: str) -> str:
    """English text on an Arabic page: its direction is set, so `start` is the left end (the page is rtl)."""
    return markup.replace("<text ", '<text direction="ltr" ', 1)


def en_word_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 6
    return [
        ltr(text("sun", x + 6, y + h * 0.66, h * 0.45, cls="wb-en", anchor="start", rtl=False)),
        picture("sun", x + w - s - 2, y + 3, s),
    ], "sun"


def sentence_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    s = h - 6
    return [
        ltr(text("I see a cat.", x + 6, y + h * 0.66, h * 0.4, cls="wb-en", anchor="start", rtl=False)),
        picture("cat", x + w - s - 2, y + 3, s),
    ], "I see a cat."


def sum_mini(op: str) -> Mini:
    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        x, y, w, h = box
        s = min(h - 8, w / 8)
        a, b = (3, 2) if op == "+" else (4, 1)
        out = [picture("apple", x + w - (k + 1) * (s + 2) - 2, y + 4, s) for k in range(a)]
        if op == "+":
            out += [picture("apple", x + w - (a + k + 1) * (s + 2) - 8, y + 4, s) for k in range(b)]
        else:
            k = a - 1
            out.append(
                draw.path(
                    f"M{x + w - (k + 1) * (s + 2) - 2} {y + 4} L{x + w - k * (s + 2) - 4} {y + 4 + s}",
                    stroke="#E0483A",
                    width=1,
                    class_="key-line",
                )
            )
        sign = "+" if op == "+" else "−"
        out.append(
            text(
                f"{ctx.num(a)} {sign} {ctx.num(b)} =", x + 34, y + h / 2 + 4, 8, cls="wb-num", color="#1C2140"
            )
        )
        out.append(_box(x + 4, y + h / 2 - 8, 14, 16))
        return out, f"{ctx.num(a)} {sign} {ctx.num(b)} = {ctx.num(a + b if op == '+' else a - b)}"

    return mini


def rhyme_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    body, cells = _row(["moon", "tree", "cat"], box)
    return [*body, _ring(cells[0]), _ring(cells[1])], "قمر وشجر"


def joins_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    out = []
    for k in range(int((w - 16) // 24)):
        x1 = x + w - 8 - k * 24
        d = f"M{x1} {y + h * 0.7} Q{x1 - 12} {y + h * 0.2} {x1 - 24} {y + h * 0.7}"
        out.append(traced(Stroke(d), spacing=3.2, r=0.9, start=1.8))
    return out, ""


def build_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    return [
        filled("square", x + w - 20, y + h * 0.62, h * 0.5, "#F7C84A"),
        filled("triangle", x + w - 20, y + h * 0.26, h * 0.56, "#E5604E"),
        _box(x + 6, y + 4, w - 40, h - 8),
    ], ""


def mix_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    r = min(h * 0.32, 9.0)
    out = [
        draw.el(
            "circle", cx=x + w - 14, cy=y + h / 2, r=r, fill="#F7C84A", stroke="#2B2E4A", stroke_width=0.6
        ),
        draw.el(
            "circle", cx=x + w - 40, cy=y + h / 2, r=r, fill="#5E86D6", stroke="#2B2E4A", stroke_width=0.6
        ),
    ]
    out += [
        text("+", x + w - 27, y + h / 2 + 3, 8, cls="wb-num"),
        text("=", x + w - 54, y + h / 2 + 3, 8, cls="wb-num"),
    ]
    out.append(
        draw.el(
            "circle",
            cx=x + w - 68,
            cy=y + h / 2,
            r=r,
            fill="#FFFFFF",
            stroke="#8C90A6",
            stroke_width=0.6,
            stroke_dasharray="2 1.6",
        )
    )
    out.append(draw.el("circle", cx=x + w - 68, cy=y + h / 2, r=r - 1, fill="#7DB46C", class_="key-ring"))
    return out, "أخضر"


def growing_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    x, y, w, h = box
    out = []
    for k in range(4):
        cx = x + w - (k + 0.5) * w / 4
        for j in range(k + 1):
            out.append(
                filled("circle", cx + (j - k / 2) * 7, y + h / 2, 6, "#5E86D6", "key-ring" if k == 3 else "")
            )
    out.append(_box(x + 2, y + 3, w / 4 - 4, h - 6))
    return out, "4 دوائر"


def key_mini(label: str) -> Mini:
    """Numbers or letters to colour by a key; the key is printed under them (a swatch and its sign)."""

    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        x, y, w, h = box
        r = min(h * 0.2, 8.0)
        items = (
            (("1", "#F7C84A"), ("2", "#E5604E"), ("3", "#5E86D6"))
            if label == "number"
            else (("ب", "#E5604E"), ("ت", "#5E86D6"), ("ث", "#7DB46C"))
        )
        out = [draw.path(f"M{x + 4} {y + h * 0.62} L{x + w - 4} {y + h * 0.62}", stroke="#E5CD9E", width=0.5)]
        for k, (lab, c) in enumerate(items):
            cx = x + w - (k + 0.5) * w / 3
            sign = ctx.num(lab) if lab.isdigit() else lab
            css = "wb-num" if lab.isdigit() else "wb-word"
            cy = y + h * 0.3
            out.append(
                draw.el("circle", cx=cx, cy=cy, r=r, fill="#FFFFFF", stroke="#2B2E4A", stroke_width=0.6)
            )
            out.append(draw.el("circle", cx=cx, cy=cy, r=r - 0.6, fill=c, class_="key-ring"))
            out.append(text(sign, cx, cy + r * 0.38, r * 1.0, cls=css, color="#1C2140"))
            ky = y + h * 0.82  # the key: the swatch beside its sign
            out.append(draw.el("circle", cx=cx + 6, cy=ky, r=3.4, fill=c, stroke="#2B2E4A", stroke_width=0.5))
            out.append(text(sign, cx - 4, ky + 2.4, 6.4, cls=css, color="#1C2140"))
        return out, "حسب المفتاح"

    return mini


def key_shapes_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    """Shapes to colour by a key; the key is printed under them."""
    x, y, w, h = box
    s = min(h * 0.36, w / 3 - 8)
    out = [draw.path(f"M{x + 4} {y + h * 0.62} L{x + w - 4} {y + h * 0.62}", stroke="#E5CD9E", width=0.5)]
    for k, (kind, color) in enumerate(
        (("circle", "#F7C84A"), ("triangle", "#E5604E"), ("square", "#5E86D6"))
    ):
        cx = x + w - (k + 0.5) * w / 3
        out.append(filled(kind, cx, y + h * 0.3, s, "#FFFFFF"))
        out.append(filled(kind, cx, y + h * 0.3, s, color, "key-ring"))
        out.append(filled(kind, cx, y + h * 0.82, s * 0.5, color))
    return out, "حسب المفتاح"


def en_match_mini(chars: str, words: tuple[str, ...]) -> Mini:
    """English letters (left to right) to join to the pictures of their words, which sit in another order."""

    def mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
        x, y, w, h = box
        n = len(chars)
        slot = [(i + 1) % n for i in range(n)]  # the picture in each slot: never under its own letter
        s = min(h * 0.5, w / n - 8)
        out = []
        for j in range(n):
            cx = x + (j + 0.5) * w / n
            out.append(text(f"{chars[j]} {chars[j].lower()}", cx, y + 7.5, 8.0, cls="wb-en", rtl=False))
            out += [hook(cx, y + 11.5, 1.5), hook(cx, y + h - s - 3.5, 1.5)]
            out.append(picture(words[slot[j]], cx - s / 2, y + h - s - 1.5, s))
        for i in range(n):
            j = slot.index(i)
            out.append(
                answer_line((x + (i + 0.5) * w / n, y + 11.5), (x + (j + 0.5) * w / n, y + h - s - 3.5))
            )
        return out, "، ".join(f"{c} ← {PICTURES[wd].word_en}" for c, wd in zip(chars, words, strict=True))

    return mini


def sort_colors_mini(ctx: PageContext, box: Box) -> tuple[list[str], str]:
    body, _cells = _row(["strawberry", "banana", "cucumber"], box, "line")
    return [*body], "أحمر، أصفر، أخضر"


MINIS.update(
    {
        "sequence-4": ("أرتّب القصة", story_mini("eid", 4)),
        "sequence-6": ("أرتّب القصة", story_mini("olive", 6)),
        "memory": ("أتذكّر", memory_mini(5)),
        "memory-6": ("أتذكّر", memory_mini(6)),
        "classify": ("أصنّف", classify_mini),
        "maze": ("المتاهة", maze_mini),
        "same-different": ("متشابهان أم مختلفان؟", word),
        "syllables": ("أصفّق للمقاطع", claps_mini),
        "first-sound": ("الصوت الأول", first_sound_mini),
        "small-waves": ("أمواج صغيرة", waves_mini),
        "find-shapes": ("أجد الأشكال", shapes),
        "sort-colors": ("ألوّن بالألوان", sort_colors_mini),
        "pattern-abb": ("أكمل النمط", pattern),
        "first-sound-coloring": ("ألوّن حسب الصوت", first_sound_mini),
        "key-coloring": ("ألوّن حسب المفتاح", key_shapes_mini),
        "name": ("أسمّي الحرف", letters_mini(("أ", "ب", "ت", "ث"), "hollow")),
        "find": ("أجد الحرف", letters_mini(("ج", "ح", "خ"), "find")),
        "write": ("أكتب الحرف", write_mini),
        "trace": ("أتتبّع", letters_mini(("د", "ذ", "ر"), "trace")),
        "complete": ("أكمل الحرف", complete_mini(("س", "ش"))),
        "copy": ("أكتب بجانب النموذج", write_mini),
        "sound": ("أقول الصوت", en_letters_mini("ABC")),
        "match": ("أصل الحرف بصورته", en_match_mini("DEF", ("duck", "egg", "fish"))),
        "count-write": ("أعدّ وأكتب", count_write_mini),
        "before-after": ("قبل وبعد", before_after_mini),
        "more-less": ("أكثر أم أقل؟", more_less_mini),
        "hidden": ("الأشياء المخبّأة", hidden_mini),
        "riddle": ("الحزّورة", riddle_mini),
        "arabic-letter": ("حرف عربي", letters_mini(("ص",), "trace")),
        "write-next-to-model": ("أكتب بجانب النموذج", write_mini),
        "english-letter": ("English letter", en_letters_mini("N")),
        "count-and-write": ("أعدّ وأكتب", count_write_mini),
        "rhyme": ("القافية", rhyme_mini),
        "joins": ("جسور صغيرة", joins_mini),
        "build-shape": ("أبني بالأشكال", build_mini),
        "mix-colors": ("أمزج الألوان", mix_mini),
        "growing-pattern": ("نمط يكبر", growing_mini),
        "number-key": ("ألوّن حسب الرقم", key_mini("number")),
        "letter-key": ("ألوّن حسب الحرف", key_mini("letter")),
        "position": ("مكان الحرف", position_mini),
        "harakat": ("الحركات", harakat_mini),
        "read": ("أقرأ", read_mini),
        "write-on-line": ("أكتب على السطر", write_line_mini),
        "write-alone": ("أكتب وحدي", write_alone_mini),
        "alphabet": ("Alphabet", en_letters_mini("XYZ")),
        "vocabulary": ("Words", en_word_mini),
        "sentence": ("A sentence", sentence_mini),
        "add": ("أجمع", sum_mini("+")),
        "subtract": ("أطرح", sum_mini("-")),
    }
)


# ---- the final assessment (stage 3, §4.13): child tasks with a face to colour, and the checklist --------

FACES = (("😊", "#7DB46C"), ("😐", "#F7C84A"), ("😕", "#EE8A6E"))


def faces(x: float, y: float, r: float = 4.2) -> str:
    """Three faces to colour one of: happy, so-so, not yet (drawn, not emoji)."""
    out = []
    for k, (_, color) in enumerate(FACES):
        cx = x - k * (2 * r + 3)
        out.append(draw.el("circle", cx=cx, cy=y, r=r, fill="#FFFFFF", stroke=color, stroke_width=0.9))
        out += [
            draw.el("circle", cx=cx + dx, cy=y - r * 0.25, r=r * 0.14, fill="#2B2E4A")
            for dx in (-r * 0.35, r * 0.35)
        ]
        mouth = {
            0: f"M{cx - r * 0.4} {y + r * 0.2} Q{cx} {y + r * 0.7} {cx + r * 0.4} {y + r * 0.2}",
            1: f"M{cx - r * 0.4} {y + r * 0.4} L{cx + r * 0.4} {y + r * 0.4}",
            2: f"M{cx - r * 0.4} {y + r * 0.55} Q{cx} {y + r * 0.15} {cx + r * 0.4} {y + r * 0.55}",
        }[k]
        out.append(draw.path(mouth, stroke="#2B2E4A", width=0.7))
    return "".join(out)


ASSESS: dict[str, Mini] = {
    "first-letter": write_alone_mini,
    "harakat": harakat_mini,
    "read": read_mini,
    "write-word": write_line_mini,
    "count": count_write_mini,
    "before-after": before_after_mini,
    "add": sum_mini("+"),
    "english": en_word_mini,
    "pattern": growing_mini,
    "memory": memory_mini(4),
}


@page_type("journey-assessment")
def assessment(ctx: PageContext) -> Built:
    """Final tasks the child does alone (params.tasks: keys of ASSESS, each with a label), a face to colour
    per task, and the score box for the grown-up."""
    tasks = [dict(t) for t in ctx.page.params.get("tasks", [])]
    problems = [f"no assessment task {t.get('kind')!r}" for t in tasks if str(t.get("kind")) not in ASSESS]
    tasks = [t for t in tasks if str(t.get("kind")) in ASSESS] or [{"kind": "count", "label": "أعدّ"}]
    pitch = (H - 24) / len(tasks)
    body, key = [], []
    for i, t in enumerate(tasks):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 4, r=8))
        body.append(
            text(str(t.get("label", "")), W - 8, y + 9, 4.8, cls="wb-label", color="#676B83", anchor="end")
        )
        body.append(faces(28, y + 8))
        drawn, answer = ASSESS[str(t["kind"])](ctx, (4, y + 13, W - 8, pitch - 18))
        body += drawn
        if answer:
            key.append(f"{t.get('label', '')}: {answer}")
    body.append(card(0, H - 20, W, 20, r=8, fill=SOFT, stroke="none"))
    body.append(text("عدد الوجوه المبتسمة:", W - 8, H - 7, 5, cls="wb-label", color="#676B83", anchor="end"))
    body.append(_box(W - 74, H - 17, 18, 14))
    body.append(
        text(f"/ {ctx.num(len(tasks))}", W - 82, H - 7, 5, cls="wb-label", color="#676B83", anchor="end")
    )
    return Built({"svg": svg(body)}, key or None, problems)


@page_type("journey-observation-checklist")
def observation_checklist(ctx: PageContext) -> Built:
    """The parent's or teacher's observation card: one row per skill, three faces, and a line for notes."""
    skills = [str(s) for s in ctx.page.params.get("skills", [])]
    problems = [] if 4 <= len(skills) <= 14 else ["list 4–14 skills"]
    body = [card(0, 0, W, 16, r=6, fill=SOFT, stroke="none")]
    body.append(text("المهارة", W - 8, 11, 5, cls="wb-label", color="#676B83", anchor="end"))
    body.append(text("أتقنها · تقريبًا · ليس بعد", 40, 11, 4.4, cls="wb-label", color="#676B83"))
    pitch = min(11.5, (H - 44) / max(len(skills), 1))
    for i, skill in enumerate(skills):
        y = 18 + i * pitch
        body.append(draw.path(f"M{W - 4} {y + pitch} L4 {y + pitch}", stroke="#EFE5D2", width=0.5))
        body.append(text(skill, W - 8, y + pitch * 0.7, 5, cls="wb-label", color="#1C2140", anchor="end"))
        body.append(faces(40, y + pitch / 2, 3.6))
    top = 18 + len(skills) * pitch + 6
    body.append(card(0, top, W, H - top, r=8))
    body.append(text("ملاحظات", W - 8, top + 9, 4.8, cls="wb-label", color="#676B83", anchor="end"))
    body += [
        draw.path(f"M{W - 8} {top + 18 + k * 8} L8 {top + 18 + k * 8}", stroke="#C9B994", width=0.6)
        for k in range(int((H - top - 20) // 8))
    ]
    return Built({"svg": svg(body)}, None, problems)
