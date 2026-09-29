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
