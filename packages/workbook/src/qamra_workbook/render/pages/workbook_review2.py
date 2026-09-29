"""«دوسية التأسيس» Volume 2 reviews and assessments: the tasks its units add (numbers to ten, a letter's place
in the word, shapes, position words, ABC patterns, spirals and writing between lines, story order, the missing
part), and the dispatchers `review_sections_v2` / `assessment_sections_v2` that `workbook_review` asks first
(None means "as in Volume 1")."""

from __future__ import annotations

import random

from qamra_workbook.digits import digit_shapes
from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import PICTURES
from qamra_workbook.puzzles.coloring import Shape
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import dotted_letter
from qamra_workbook.render.pages.thinking import SHAPE_COLORS, shape_kind
from qamra_workbook.render.pages.workbook_activity2 import MISSING, STORY
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    answer_line,
    card,
    hook,
    pic,
    ring_at,
    text,
)
from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES, plate
from qamra_workbook.render.pages.workbook_math2 import group_any, numeral_any
from qamra_workbook.render.pages.workbook_pen import PAIRS, traced
from qamra_workbook.render.pages.workbook_pen2 import BETWEEN, spiral
from qamra_workbook.render.pages.workbook_position import POSITIONS, position_of, word_shapes, written_word
from qamra_workbook.render.pages.workbook_review import (
    CHECKLIST_AR,
    LEVELS_AR,
    PEN_LABELS,
    Box,
    Drawn,
    Task,
    circle_first_letter,
    grid,
    match_capitals,
    match_pairs,
    mini_classify,
    mini_maze,
    read_letters,
    score_box,
    stack,
    write_first_letter,
    write_letters,
)
from qamra_workbook.render.registry import PageContext

V2_LETTERS = ["ر", "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ"]
PEN_LABELS_2 = {
    "spiral": "حلزون",
    "narrow-path": "طريق ضيّق",
    "between-lines": "بين السطرين",
    "dot-to-dot": "مثلث",
}


def count_write_any(counts: list[int]) -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        step = box.w / len(counts)
        things = r.sample(GROUP_PICTURES, len(counts))
        for k, (n, thing) in enumerate(zip(counts, things, strict=True)):
            x = box.x + box.w - (k + 1) * step
            gh = box.h - 24
            out.body.append(card(x + 3, box.y, step - 6, gh, r=5, fill="#FFF6F2", stroke="none"))
            out.body.append(
                plate(x + 8, box.y + gh / 2 - 6, step - 16)
                if n == 0
                else group_any(thing, n, x + 4, box.y + 1, step - 8, gh - 2)
            )
            out.body.append(
                card(
                    x + step / 2 - 10,
                    box.y + gh + 3,
                    20,
                    20,
                    r=3,
                    fill="#FFFFFF",
                    stroke="#B8B2A6",
                    dash="2 1.4",
                )
            )
        out.answer.append("أعدّ وأكتب: " + "، ".join(ctx.num(n) for n in counts))
        return out

    return task


def trace_numbers_any(numbers: list[int]) -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        step = box.w / len(numbers)
        cap = min(box.h - 4, 26.0)
        for k, n in enumerate(numbers):
            shapes = digit_shapes(n, ctx.numerals)
            scale = cap / 100
            cx = box.x + box.w - (k + 0.5) * step
            total = sum(s.width for s in shapes) * scale + 3 * (len(shapes) - 1)
            x = cx - total / 2
            for shape in shapes:
                out.body.append(
                    dotted_letter(
                        shape, scale=scale, x=x, y=box.y + 2 - 10 * scale, first=True, number=ctx.num
                    )
                )
                x += shape.width * scale + 3
        return out

    return task


def order_numbers(seq: list[int], blanks: int = 2) -> Task:
    """A row of numbers in order with `blanks` missing, to write."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        gone = sorted(r.sample(range(1, len(seq) - 1), blanks))
        step = box.w / len(seq)
        w, h = min(step - 3, 18.0), min(box.h - 2, 22.0)
        for k, n in enumerate(
            seq
        ):  # draft: educator review: sequences run left to right, as numerals are read
            cx = box.x + (k + 0.5) * step
            blank = k in gone
            out.body.append(
                draw.el(
                    "rect",
                    x=cx - w / 2,
                    y=box.y + (box.h - h) / 2,
                    width=w,
                    height=h,
                    rx=3,
                    fill="#FFFFFF",
                    stroke=INK if not blank else "#B8B2A6",
                    stroke_width=0.6,
                    stroke_dasharray="2 1.4" if blank else "none",
                )
            )
            num = numeral_any(ctx, n, cx, box.y + box.h / 2, h - 6, "#E0483A" if blank else INK)
            out.body.append(num.replace("<g ", '<g class="key-line" ', 1) if blank else num)
        out.answer.append("الأعداد الناقصة: " + "، ".join(ctx.num(seq[k]) for k in gone))
        return out

    return task


def letter_place(letters: list[str], words: list[str]) -> Task:
    """Words with the letter coloured; tick where it is (beginning, middle, end)."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(words)
        for i, word in enumerate(words):
            y = box.y + i * pitch
            shapes = word_shapes(word)
            target = next((t for t in letters if position_of(shapes, t) is not None), None)
            if target is None:
                out.problems.append(f"«{word}» holds none of {letters}")
                continue
            from qamra_workbook.render.pages.workbook_arabic import same_letter

            hit = next(j for j, x in enumerate(shapes) if same_letter(x.char, target))
            where = position_of(shapes, target) or 0
            band = min(pitch - 5, 16.0)
            written, boxes = written_word(
                shapes, box.x + box.w - 4, y + (pitch - band) / 2, band, color={hit: ctx.style.color}
            )
            out.body.append(written)
            cx, cy, half = boxes[hit]
            out.body.append(ring_at(cx, cy, half + 2, band / 2 + 1))
            for k, label in enumerate(POSITIONS):
                bx = box.x + 4 + k * 20
                out.body.append(
                    draw.el(
                        "rect",
                        x=bx,
                        y=y + pitch / 2 - 7,
                        width=13,
                        height=10,
                        rx=2,
                        fill="#FFFFFF",
                        stroke="#B8B2A6",
                        stroke_width=0.5,
                    )
                )
                out.body.append(text(label, bx + 6.5, y + pitch / 2 + 8, 3.2, color="#676B83"))
                if k == where:
                    out.body.append(
                        draw.path(
                            draw.d_path(
                                ("M", (bx + 3, y + pitch / 2 - 2)),
                                ("L", (bx + 6, y + pitch / 2 + 1)),
                                ("L", (bx + 10, y + pitch / 2 - 5)),
                            ),
                            stroke="#E0483A",
                            width=1,
                            class_="key-line",
                        )
                    )
            out.answer.append(f"{word}: {POSITIONS[where]}")
        return out

    return task


def shapes_task() -> Task:
    """Six shapes: circle the triangles, colour the circles."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        kinds = ["circle", "square", "triangle", "rectangle", "triangle", "circle"]
        r.shuffle(kinds)
        step = box.w / len(kinds)
        size = min(step - 6, box.h - 4)
        for k, kind in enumerate(kinds):
            cx, cy = box.x + box.w - (k + 0.5) * step, box.y + box.h / 2
            w = size * (1.4 if kind == "rectangle" else 1.0)
            out.body.append(
                draw.shape(
                    Shape(kind, cx, cy, min(w, step - 4), size * (0.7 if kind == "rectangle" else 1)),  # type: ignore[arg-type]
                    fill="#FFFFFF",
                    width=0.9,
                )
            )
            if kind == "triangle":
                out.body.append(ring_at(cx, cy, size / 2 + 3, size / 2 + 3))
        out.answer.append("المثلثات محوّطة، والدوائر ملوّنة")
        return out

    return task


def positions_task(concept: str) -> Task:
    """Above/below the table, or right/left of the house: circle what the label says."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        cx, mid = box.x + box.w / 2, box.y + box.h / 2
        if concept == "right-left":
            out.body.append(pic("house", cx - 14, mid - 14, 28))
            out.body.append(pic("cat", cx + 22, mid - 10, 20))
            out.body.append(pic("ball", cx - 42, mid - 10, 20))
            out.body.append(ring_at(cx + 32, mid, 13, 13))
            out.answer.append("على يمين البيت: القطة")
        else:
            size = min(box.h - 4, 44.0)
            out.body.append(pic("table", cx - size * 0.7, mid - size / 2, size * 1.4))
            out.body.append(pic("cat", cx - size * 0.1, mid - size * 0.5, size * 0.36))
            out.body.append(pic("dog", cx - size * 0.15, mid + size * 0.08, size * 0.36))
            out.body.append(ring_at(cx + size * 0.08, mid - size * 0.32, size * 0.22, size * 0.2))
            out.answer.append("فوق الطاولة: القطة")
        return out

    return task


def pattern_abc_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        kinds = ("circle", "square", "triangle")
        step = box.w / 8
        size = min(step - 3, box.h - 4)
        for k in range(8):
            cx, cy = box.x + box.w - (k + 0.5) * step, box.y + box.h / 2
            kind = kinds[k % 3]
            if k < 6:
                shape = Shape(shape_kind(kind), cx, cy, size * 0.8, size * 0.8)
                out.body.append(draw.shape(shape, fill=SHAPE_COLORS[kind], width=0.9))
            else:
                out.body.append(
                    card(
                        cx - size / 2,
                        cy - size / 2,
                        size,
                        size,
                        r=3,
                        fill="#FFFFFF",
                        stroke=ctx.style.color,
                        dash="2 1.4",
                    )
                )
        out.answer.append("النمط: دائرة ثم مربع ثم مثلث")
        return out

    return task


def pen_row2(skill: str) -> Task:
    """A Volume 2 pen drill in a strip: spirals, shapes between two lines, or a short narrow path."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        mid = box.y + box.h / 2
        if skill == "spiral":
            radius = min(box.h / 2 - 2, 14.0)
            for k in range(3):
                out.body.append(
                    traced(
                        spiral(box.x + box.w - (k + 0.5) * box.w / 3, mid, radius, 2),
                        spacing=3.6,
                        r=0.95,
                        start=2,
                    )
                )
        elif skill == "between-lines":
            top, h = mid - 5, 10.0
            for yy, color in ((top, "#9BB7E0"), (top + h, "#E27D63")):
                out.body.append(
                    draw.el(
                        "path",
                        d=draw.d_path(("M", (box.x + 2, yy)), ("L", (box.x + box.w - 2, yy))),
                        stroke=color,
                        stroke_width=0.5,
                    )
                )
            for k, name in enumerate(("zigzag", "wave", "loops")):
                out.body.append(
                    traced(
                        Stroke(BETWEEN[name](box.x + box.w - 8 - k * 40, top, h)),
                        spacing=3.0,
                        r=0.85,
                        start=1.8,
                    )
                )
        else:
            a, b = r.choice(PAIRS)
            size = min(box.h - 2, 16.0)
            out.body.append(pic(a, box.x + box.w - size, mid - size / 2, size))
            out.body.append(pic(b, box.x, mid - size / 2, size))
            x0, x1 = box.x + box.w - size - 4, box.x + size + 4
            d = (
                f"M{x0} {mid} C{x0 - 20} {mid - 12} {x0 - 40} {mid + 12} {x0 - 60} {mid} "
                f"C{x0 - 80} {mid - 12} {x1 + 20} {mid + 12} {x1} {mid}"
            )
            road = Stroke(d)
            out.body.append(draw.path(road.d, stroke="#E5CD9E", width=8))
            out.body.append(draw.path(road.d, stroke="#FFFFFF", width=6))
            out.body.append(traced(road, spacing=4.4, r=0.85, start=2))
        return out

    return task


def sequence_task() -> Task:
    """The story's four pictures out of order, with a box under each to number."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        order = list(range(4))
        while order == [0, 1, 2, 3]:
            r.shuffle(order)
        step = box.w / 4
        size = min(step - 6, box.h - 12)
        for k, i in enumerate(order):
            cx = box.x + box.w - (k + 0.5) * step
            out.body.append(pic(STORY[i], cx - size / 2, box.y, size))
            out.body.append(
                draw.el(
                    "rect",
                    x=cx - 5,
                    y=box.y + size + 2,
                    width=10,
                    height=9,
                    rx=2,
                    fill="#FFFFFF",
                    stroke="#B8B2A6",
                    stroke_width=0.5,
                )
            )
            out.body.append(
                text(ctx.num(i + 1), cx, box.y + size + 9, 4.4, cls="wb-num", color="#E0483A").replace(
                    "<text ", '<text class="key-line wb-num" ', 1
                )
            )
        out.answer.append("الترتيب: " + " ← ".join(PICTURES[t].word_ar for t in STORY))
        return out

    return task


def missing_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        step = box.w / 2
        size = min(step - 10, box.h - 2)
        for k, (thing, (px, py, pw, ph), name) in enumerate(MISSING[:2]):
            ox, oy = box.x + box.w - (k + 1) * step + (step - size) / 2, box.y + (box.h - size) / 2
            out.body.append(pic(thing, ox, oy, size))
            s = size / 100
            out.body.append(
                draw.el("rect", x=ox + px * s, y=oy + py * s, width=pw * s, height=ph * s, fill="#FFFFFF")
            )
            out.body.append(pic(thing, ox, oy, size, class_="key-ring"))
            out.answer.append(f"{PICTURES[thing].word_ar}: {name}")
        return out

    return task


def related_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.render.pages.workbook_thinking2 import RELATED

        out = Drawn()
        pairs = r.sample(RELATED, 3)
        order = [1, 2, 0]
        pitch = box.h / 3
        size = min(pitch - 3, 18.0)
        for i, (a, _) in enumerate(pairs):
            y = box.y + i * pitch + pitch / 2
            out.body.append(pic(a, box.x + box.w - size - 2, y - size / 2, size))
            out.body.append(pic(pairs[order[i]][1], box.x + 2, y - size / 2, size))
            out.body += [hook(box.x + box.w - size - 6, y), hook(box.x + size + 6, y)]
            j = order.index(i)
            out.body.append(
                answer_line((box.x + box.w - size - 6, y), (box.x + size + 6, box.y + j * pitch + pitch / 2))
            )
        out.answer.append("كل شيء بما يناسبه")
        return out

    return task


# the words the letter-position pages used, for the reviews
POSITION_WORDS = {
    "أ": ("أرنب", "باب"),
    "ب": ("بطة", "حبل", "عنب"),
    "ت": ("تاج", "كتاب", "بيت"),
    "ث": ("مثلث",),
    "ج": ("جمل", "دجاجة", "درج"),
    "ح": ("حصان", "نحلة", "مفتاح"),
    "خ": ("نخلة",),
    "د": ("دب", "هدية", "يد"),
    "ذ": ("حذاء",),
    "ع": ("عين", "نعامة", "ضفدع"),
    "غ": ("غيمة", "ببغاء"),
}
V2_PEN = {"spiral", "narrow-path", "between-lines"}


def _place_words(letters: list[str], r: random.Random, count: int) -> tuple[list[str], list[str]]:
    picked = [x for x in dict.fromkeys(letters) if x in POSITION_WORDS]
    chosen = r.sample(picked, min(count, len(picked)))
    return chosen, [r.choice(POSITION_WORDS[x]) for x in chosen]


def review_sections_v2(ctx: PageContext, r: random.Random) -> Drawn | None:
    params, subject = ctx.page.params, ctx.page.section
    letters = [str(x) for x in params.get("letters", [])]
    numbers = [int(x) for x in params.get("numbers", [])]
    skills = [str(x) for x in params.get("skills", [])]
    if subject == "english" and letters and all(c in ENGLISH_WORDS for c in letters):
        return english_review_v2(ctx, r, letters)
    if subject == "arabic" and letters and "الكلمة" in ctx.page.skill:
        chosen, words = _place_words(letters, r, 4)
        out = stack(
            ctx,
            [
                ("أين الحرف في الكلمة؟", letter_place(chosen, words), 1.5),
                (
                    "أحوّط الصورة التي تبدأ بالحرف",
                    circle_first_letter(r.sample(letters, min(3, len(letters)))),
                    1.0,
                ),
            ],
            r,
        )
        # one short key line (the title takes two lines on the answer key; the solved page shows the rest)
        out.answer = ["المواقع: " + "، ".join(out.answer[: len(words)])]
        return out
    if subject == "math" and numbers and max(numbers) > 5:
        top = max(numbers)
        return stack(
            ctx,
            [
                (
                    "أعدّ وأكتب",
                    count_write_any(numbers[:4] if len(numbers) > 2 else [*numbers, *numbers][:4]),
                    1.3,
                ),
                ("أتتبّع الأعداد", trace_numbers_any(numbers), 0.8),
                ("أكتب العدد الناقص", order_numbers(list(range(max(1, top - 4), top + 1))), 0.8),
            ],
            r,
        )
    if subject == "math" and "shapes" in skills:
        return grid(
            ctx,
            [
                ("أحوّط المثلثات وألوّن الدوائر", shapes_task()),
                ("أحوّط ما فوق الطاولة", positions_task("above-below")),
                ("أحوّط ما على يمين البيت", positions_task("right-left")),
                ("أكمل النمط", pattern_abc_task()),
            ],
            r,
        )
    if subject == "pen" and V2_PEN & set(skills):
        from qamra_workbook.render.pages.workbook_review import pen_row

        rows = [
            (
                PEN_LABELS_2.get(s, PEN_LABELS.get(s, s)),
                pen_row2(s) if s in V2_PEN else pen_row("triangle" if s == "dot-to-dot" else s),
                1.0,
            )
            for s in skills
        ]
        return stack(ctx, rows, r)
    if subject == "thinking" and {"sequence", "problem-solving"} & set(skills):
        tasks = {
            "memory": ("أطابق الصور", match_pairs(3)),
            "connect": ("أصل ما يناسب", related_task()),
            "sequence": ("أرتّب القصة", sequence_task()),
            "problem-solving": ("أرسم ما ينقص", missing_task()),
        }
        return grid(ctx, [tasks[s] for s in skills if s in tasks], r)
    if subject == "mixed" and any("ر" in str(c) for c in params.get("covers", [])):
        return stack(
            ctx,
            [
                ("أكتب الحرف الأول من اسم كل صورة", write_first_letter(V2_LETTERS), 1.0),
                ("أعدّ وأكتب", count_write_any([6, 9, 10, 7]), 1.0),
                ("أصل الحرف الكبير بالصغير", match_capitals(list("IJKLMN")), 0.9),
            ],
            r,
        )
    return None


def pen_check2(ctx: PageContext, r: random.Random, tracing: list[str], checklist: list[str]) -> Drawn:
    out = stack(
        ctx,
        [(f"أتتبّع: {PEN_LABELS_2.get(t, PEN_LABELS.get(t, t))}", pen_row2(t), 1.0) for t in tracing],
        r,
        0,
        104,
    )
    y = 110.0
    out.body.append(card(0, y, W, 204 - y, r=6, fill="#FFFDF6", stroke="#D8C9AC"))
    out.body.append(
        text(
            "للمعلّمة أو الأهل: لاحظوا الطفل وهو يتتبّع، ثم ضعوا علامة",
            W - 6,
            y + 8,
            4.4,
            anchor="end",
            color=ctx.style.deep,
        )
    )
    col_x = [W - 128, W - 150, W - 172]
    for k, label in enumerate(LEVELS_AR):
        out.body.append(text(label, col_x[k], y + 18, 3.6, color=INK))
    for i, item in enumerate(checklist):
        yy = y + 22 + i * 14
        out.body.append(
            draw.path(draw.d_path(("M", (4, yy)), ("L", (W - 4, yy))), stroke="#E4D6BC", width=0.4)
        )
        out.body.append(text(CHECKLIST_AR.get(item, item), W - 6, yy + 9, 3.9, anchor="end", color=INK))
        for x in col_x:
            out.body.append(
                draw.el(
                    "rect",
                    x=x - 3,
                    y=yy + 4,
                    width=6,
                    height=6,
                    rx=1.2,
                    fill="#FFFFFF",
                    stroke=INK,
                    stroke_width=0.5,
                )
            )
    yy = y + 22 + len(checklist) * 14 + 8
    out.body.append(
        text(
            "ملاحظات: ..................................................................",
            W - 6,
            yy,
            3.9,
            anchor="end",
            color="#676B83",
        )
    )
    out.body.append(
        text(
            "التوقيع والتاريخ: ...................................",
            W - 6,
            yy + 10,
            3.9,
            anchor="end",
            color="#676B83",
        )
    )
    out.answer.append("تقييم ملاحظة: " + "، ".join(CHECKLIST_AR.get(c, c).split(":")[0] for c in checklist))
    if len(tracing) != 2 or {"grip", "pressure", "direction"} - set(checklist):
        out.problems.append("the pen check has the grip/pressure/direction checklist and two tracing tasks")
    return out


def assessment_sections_v2(ctx: PageContext, r: random.Random) -> Drawn | None:
    subject = ctx.page.section
    covers = [str(x) for x in ctx.page.params.get("covers", [])]
    tracing = [str(t) for t in ctx.page.params.get("tracing", [])]
    if subject == "english" and covers and all(c in ENGLISH_WORDS for c in covers):
        return english_assessment_v2(ctx, r, covers)
    if subject == "pen" and V2_PEN & set(tracing):
        return pen_check2(ctx, r, tracing, [str(c) for c in ctx.page.params.get("checklist", [])])
    if subject == "arabic" and "positions" in covers:
        letters = [c for c in covers if len(c) == 1]
        chosen, words = _place_words([*letters, "ع", "غ"], r, 3)
        out = stack(
            ctx,
            [
                ("أقرأ الحروف", read_letters(letters), 0.8),
                ("أكتب الحرف الأول من اسم كل صورة", write_first_letter(r.sample(letters, 4)), 1.1),
                ("أين الحرف في الكلمة؟", letter_place(chosen, words), 1.2),
            ],
            r,
            0,
            178,
        )
    elif subject == "math" and "6–10" in covers:
        out = stack(
            ctx,
            [
                ("أعدّ وأكتب", count_write_any([7, 10, 6, 9]), 1.3),
                ("أكتب الأعداد الناقصة", order_numbers(list(range(1, 11)), 3), 0.7),
                ("أحوّط المثلثات وألوّن الدوائر", shapes_task(), 0.8),
            ],
            r,
            0,
            178,
        )
    elif subject == "thinking" and "sequence" in covers:
        out = grid(
            ctx,
            [
                ("أصنّف بالألوان", mini_classify()),
                ("أرتّب القصة", sequence_task()),
                ("أطابق الصور", match_pairs(3)),
                ("أحلّ المتاهة", mini_maze()),
            ],
            r,
            0,
            178,
        )
    else:
        return None
    out.body += score_box(ctx, 182)
    return out


# the English words of the I–R units, first for the reviews (the library also has kitchen, lunchbox…)
ENGLISH_WORDS = {
    "I": ("insect", "ice-cream"),
    "J": ("jar", "jacket", "jug"),
    "K": ("kite", "key"),
    "L": ("lion", "leaf", "lemon"),
    "M": ("moon", "monkey", "milk"),
    "N": ("nest", "nose"),
    "O": ("octopus", "olive", "orange"),
    "P": ("parrot", "pencil", "pear"),
    "Q": ("queen", "quilt"),
    "R": ("rabbit", "ring", "rose"),
}


def circle_english(letters: list[str]) -> Task:
    """For each letter: three pictures from the units' English words, circle the one that starts with it."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(letters)
        for i, char in enumerate(letters):
            y = box.y + i * pitch
            right = r.choice(ENGLISH_WORDS[char])
            others = [c for c in ENGLISH_WORDS if c != char and c in "IJKLMNOPQR"]
            wrong = [r.choice(ENGLISH_WORDS[c]) for c in r.sample(others, 2)]
            choices = [right, *wrong]
            r.shuffle(choices)
            size = min(pitch - 4, 34.0)
            from qamra_workbook.render.pages.workbook_common import fit_lines, glyph, shape_of

            shape = shape_of(char)
            out.body.append(
                glyph(
                    shape,
                    *fit_lines(shape, box.x + 6, y + pitch / 2 - 8, 16, 16),
                    color=ctx.style.deep,
                    width=14,
                )
            )
            for k, thing in enumerate(choices):
                cx = box.x + 30 + (k + 0.5) * (box.w - 30) / 3
                out.body.append(pic(thing, cx - size / 2, y + pitch / 2 - size / 2, size))
                if thing == right:
                    out.body.append(ring_at(cx, y + pitch / 2, size / 2 + 2, size / 2 + 2))
            out.answer.append(f"{char}: {PICTURES[right].word_en}")
        return out

    return task


def english_review_v2(ctx: PageContext, r: random.Random, letters: list[str]) -> Drawn:
    return stack(
        ctx,
        [
            ("Write the letters", write_letters(letters), 1.3),
            ("Circle the picture", circle_english(letters), 1.0),
        ],
        r,
    )


def english_assessment_v2(ctx: PageContext, r: random.Random, letters: list[str]) -> Drawn:
    out = stack(
        ctx,
        [
            ("Read the letters", read_letters(letters), 0.8),
            ("Match big and small", match_capitals(r.sample(letters, 5)), 1.1),
            ("Circle the picture", circle_english(r.sample(letters, 3)), 1.2),
        ],
        r,
        0,
        178,
    )
    out.body += score_box(ctx, 182)
    return out
