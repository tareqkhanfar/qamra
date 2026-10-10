"""«دوسية التأسيس» unit reviews and assessments (Addendum 5 §2.5, §4; decision 9): each page is a few short
tasks in cards, drawn from what the unit taught (its letters, numbers or skills). An assessment ends with a
small score box for the teacher or parent; the pen-skills check is a checklist (grip, pressure, direction)
and two tracing tasks.

Every task is a function that draws into a box (x, y, w, h in mm) and returns its SVG and answer lines.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import row_room, tracing_row
from qamra_workbook.render.pages.workbook_arabic import row_svg
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    answer_line,
    card,
    fit_lines,
    for_child,
    glyph,
    hook,
    pic,
    ring_at,
    shape_of,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_find import words_starting
from qamra_workbook.render.registry import Built, PageContext, page_type


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float


@dataclass
class Drawn:
    body: list[str] = field(default_factory=list)
    answer: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


Task = Callable[[PageContext, Box, random.Random], Drawn]


def framed(ctx: PageContext, box: Box, label: str, task: Task, r: random.Random) -> Drawn:
    """A task in a card with its short label at the top (on the reading side)."""
    rtl = ctx.page.lang != "en"
    out = Drawn([card(box.x, box.y, box.w, box.h, r=6)])
    anchor_x = box.x + box.w - 5 if rtl else box.x + 5
    out.body.append(
        text(
            label, anchor_x, box.y + 7.5, 4.4, anchor="end" if rtl else "start", color=ctx.style.deep, rtl=rtl
        )
    )
    inner = task(ctx, Box(box.x + 3, box.y + 10, box.w - 6, box.h - 12), r)
    out.body += inner.body
    out.answer += inner.answer
    out.problems += inner.problems
    return out


def cap_for(shape: Letter, height: float) -> float:
    """The cap height at which a `tracing_row` of this letter is `height` mm tall."""
    above, below = row_room(shape, 1.0)
    cap = (height - 9) / (1 + above + below)
    return cap if below * cap + 4 >= 7 else (height - 12) / (1 + above)


def pictures_for(letter: str, r: random.Random, count: int = 1, avoid: set[str] | None = None) -> list[str]:
    """Pictures whose word starts with `letter`: Arabic via the letter's words, English via the word."""
    if "A" <= letter.upper() <= "Z":
        pool = [
            pid
            for pid, p in PICTURES.items()
            if p.word_en[:1].upper() == letter.upper() and " " not in p.word_en
        ]
    else:
        pool = list(words_starting(letter))
    pool = [p for p in pool if not avoid or p not in avoid]
    return r.sample(pool, min(count, len(pool)))


def write_letters(letters: list[str]) -> Task:
    """A short writing row per letter: two dotted letters, then room to write it alone."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(letters)
        for i, char in enumerate(letters):
            shape = shape_of(char)
            cap = min(22.0, cap_for(shape, pitch - 1))
            row, _ = row_svg(
                tracing_row(shape, width=box.w, cap=cap, count=2, number=ctx.num), box.x, box.y + i * pitch
            )
            out.body.append(row)
        return out

    return task


def circle_first_letter(letters: list[str]) -> Task:
    """For each letter: three pictures, circle the one that starts with it."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        rtl = ctx.page.lang != "en"
        pitch = box.h / len(letters)
        used: set[str] = set()
        for i, char in enumerate(letters):
            y = box.y + i * pitch
            right = pictures_for(char, r, 1, used)
            if not right:
                out.problems.append(f"no picture starts with {char}")
                continue
            used.add(right[0])
            others = [c for c in letters if c != char] or ["م"]
            wrong: list[str] = []
            for other in others * 2:
                wrong += pictures_for(other, r, 1, used | set(wrong))
                if len(wrong) == 2:
                    break
            choices = right + wrong
            r.shuffle(choices)
            size = min(pitch - 4, 34.0)
            lx = box.x + box.w - 14 if rtl else box.x + 14
            area_x, area_w = (box.x, box.w - 30) if rtl else (box.x + 30, box.w - 30)
            shape = shape_of(char)
            out.body.append(
                glyph(
                    shape,
                    *fit_lines(shape, lx - 8, y + pitch / 2 - 8, 16, 16),
                    color=ctx.style.deep,
                    width=14,
                )
            )
            for k, thing in enumerate(choices):
                cx = area_x + (area_w - (k + 0.5) * area_w / 3 if rtl else (k + 0.5) * area_w / 3)
                out.body.append(pic(thing, cx - size / 2, y + pitch / 2 - size / 2, size))
                if thing == right[0]:
                    out.body.append(ring_at(cx, y + pitch / 2, size / 2 + 2, size / 2 + 2))
            word = PICTURES[right[0]].word_ar if rtl else PICTURES[right[0]].word_en
            out.answer.append(f"{char}: {word}")
        return out

    return task


def read_letters(letters: list[str]) -> Task:
    """The letters in a row, each with a box the grown-up ticks when the child names it."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        rtl = ctx.page.lang != "en"
        order = list(letters)
        r.shuffle(order)
        step = box.w / len(order)
        size = min(step - 6, box.h - 14)  # wide letters (ص ض) side by side keep a visible gap
        for k, char in enumerate(order):
            cx = box.x + box.w - (k + 0.5) * step if rtl else box.x + (k + 0.5) * step
            shape = shape_of(char)
            out.body.append(
                glyph(shape, *fit_lines(shape, cx - size / 2, box.y, size, size), color=INK, width=13)
            )
            out.body.append(
                draw.el(
                    "rect",
                    x=cx - 3,
                    y=box.y + size + 3,
                    width=6,
                    height=6,
                    rx=1.2,
                    fill="#FFFFFF",
                    stroke="#B8B2A6",
                    stroke_width=0.5,
                )
            )
        out.answer.append(for_child(ctx, "القراءة: علامة تحت كل حرف {سمّاه الطفل/سمّته الطفلة}"))
        return out

    return task


def write_first_letter(letters: list[str]) -> Task:
    """Pictures with an empty box under each: write the letter the word starts with."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        rtl = ctx.page.lang != "en"
        chosen = r.sample(letters, min(4, len(letters)))
        step = box.w / len(chosen)
        size = min(step - 12, box.h - 26)
        for k, char in enumerate(chosen):
            cx = box.x + box.w - (k + 0.5) * step if rtl else box.x + (k + 0.5) * step
            thing = pictures_for(char, r, 1)
            if not thing:
                out.problems.append(f"no picture starts with {char}")
                continue
            out.body.append(pic(thing[0], cx - size / 2, box.y, size))
            out.body.append(
                card(cx - 10, box.y + size + 3, 20, 20, r=3, fill="#FFFFFF", stroke="#B8B2A6", dash="2 1.4")
            )
            out.answer.append(f"{PICTURES[thing[0]].word_ar if rtl else PICTURES[thing[0]].word_en}: {char}")
        return out

    return task


def match_capitals(letters: list[str]) -> Task:
    """Capitals on top, small letters below in another order: connect each pair."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        smalls = list(letters)
        while len(smalls) > 1 and smalls == letters:
            r.shuffle(smalls)
        step = box.w / len(letters)
        size = min(step - 6, (box.h - 20) / 2)
        top, bottom = box.y + size / 2, box.y + box.h - size / 2
        for k, (cap, small) in enumerate(zip(letters, smalls, strict=True)):
            cx = box.x + (k + 0.5) * step
            for char, cy in ((cap.upper(), top), (small.lower(), bottom)):
                shape = shape_of(char)
                out.body.append(
                    glyph(
                        shape,
                        *fit_lines(shape, cx - size / 2, cy - size / 2, size, size),
                        color=INK,
                        width=12,
                    )
                )
            out.body += [hook(cx, top + size / 2 + 2), hook(cx, bottom - size / 2 - 2)]
        for k, cap in enumerate(letters):
            j = smalls.index(cap)
            out.body.append(
                answer_line(
                    (box.x + (k + 0.5) * step, top + size / 2 + 2),
                    (box.x + (j + 0.5) * step, bottom - size / 2 - 2),
                )
            )
        out.answer.append(" ".join(f"{c.upper()}–{c.lower()}" for c in letters))
        return out

    return task


# the score box's three marks: the child mastered the skill, needs a little practice, needs more practice
SCORE_AR = (
    "{أتقن/أتقنت} المهارة",
    "{يحتاج/تحتاج} قليلًا من التدريب",
    "{يحتاج/تحتاج} تدريبًا أكثر",
)  # draft: educator review


def score_box(ctx: PageContext, y: float) -> list[str]:
    """«للمعلّمة أو الأهل»: circle one of three faces, and a line to sign (Addendum 5 §4 assessment)."""
    out = [card(0, y, W, 204 - y, r=6, fill="#FFFDF6", stroke="#D8C9AC", dash="2.4 1.6")]
    out.append(text("للمعلّمة أو الأهل:", W - 6, y + 8.5, 4.4, anchor="end", color=ctx.style.deep))
    for k, label in enumerate(SCORE_AR):
        cx = W - 62 - k * 50
        out.append(
            draw.el("circle", cx=cx + 18, cy=y + 7, r=3.2, fill="#FFFFFF", stroke=INK, stroke_width=0.5)
        )
        out.append(text(for_child(ctx, label), cx + 13, y + 8.5, 3.6, anchor="end", color=INK))
    out.append(
        text(
            "التوقيع والتاريخ: ....................................",
            W - 6,
            y + 17.5,
            3.8,
            anchor="end",
            color="#676B83",
        )
    )
    return out


def count_write(counts: list[int]) -> Task:
    """Groups to count, each with a box to write how many."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES, group, plate

        out = Drawn()
        step = box.w / len(counts)
        things = r.sample(GROUP_PICTURES, len(counts))
        for k, (n, thing) in enumerate(zip(counts, things, strict=True)):
            x = box.x + box.w - (k + 1) * step
            gh = box.h - 24
            out.body.append(card(x + 3, box.y, step - 6, gh, r=5, fill="#FFF6F2", stroke="none"))
            if n == 0:
                out.body.append(plate(x + 8, box.y + gh / 2 - 6, step - 16))
            else:
                out.body.append(group(thing, n, x + 4, box.y + 1, step - 8, gh - 2))
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


def trace_numbers(numbers: list[int]) -> Task:
    """The numbers in dots, in order, to trace (each with its start dot)."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.render.pages.letters import dotted_letter
        from qamra_workbook.render.pages.workbook_math import number_shape

        out = Drawn()
        step = box.w / len(numbers)
        cap = min(box.h - 4, 30.0)
        for k, n in enumerate(numbers):
            shape = number_shape(ctx, n)
            scale = cap / 100
            cx = box.x + box.w - (k + 0.5) * step
            x0 = cx - shape.width * scale / 2
            out.body.append(
                dotted_letter(shape, scale=scale, x=x0, y=box.y + 2 - 10 * scale, first=True, number=ctx.num)
            )
        return out

    return task


def circle_group(n: int, others: list[int]) -> Task:
    """Three groups: circle the one with `n` things."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES, group, numeral, plate

        out = Drawn()
        amounts = [n, *r.sample([m for m in others if m != n], 2)]
        r.shuffle(amounts)
        thing = r.choice(GROUP_PICTURES)
        out.body.append(card(box.x + box.w - 26, box.y, 24, box.h, r=5, fill=ctx.style.tint, stroke="none"))
        out.body.append(numeral(ctx, n, box.x + box.w - 14, box.y + box.h / 2, 16, ctx.style.deep))
        step = (box.w - 30) / 3
        for k, m in enumerate(amounts):
            x = box.x + box.w - 30 - (k + 1) * step
            out.body.append(card(x + 2, box.y, step - 4, box.h, r=5, fill="#FFF6F2", stroke="none"))
            if m == 0:
                out.body.append(plate(x + 6, box.y + box.h / 2 - 5, step - 12))
            else:
                out.body.append(group(thing, m, x + 3, box.y + 1, step - 6, box.h - 2))
            if m == n:
                out.body.append(ring_at(x + step / 2, box.y + box.h / 2, step / 2, box.h / 2 + 1))
        out.answer.append(f"المجموعة التي فيها {ctx.num(n)}")
        return out

    return task


def compare_pair(concept: str) -> Task:
    """One pair to compare: circle the big one, the long one, or the group with many."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES, long_thing, scatter

        out = Drawn()
        win = r.randrange(2)
        centers = (box.x + box.w * 0.27, box.x + box.w * 0.73)
        mid = box.y + box.h / 2
        thing = r.choice(GROUP_PICTURES)
        full = min(box.h - 4, box.w * 0.44)  # the big one stays in its half of the box
        for k, cx in enumerate(centers):
            if concept == "big-small":
                size = full * (1.0 if k == win else 0.45)
                out.body.append(pic(thing, cx - size / 2, mid - size / 2, size))
            elif concept == "long-short":
                length = box.w * (0.36 if k == win else 0.16)
                out.body.append(long_thing("pencil", cx - length / 2, mid, length, "#EE8A6E"))
            else:
                count = 6 if k == win else 2
                # each group on its own card, so the eye sees two groups and not eight scattered things
                out.body.append(
                    card(cx - box.w * 0.22, box.y + 1, box.w * 0.44, box.h - 2, r=5, fill="#FFF6F2")
                )
                out.body.append(
                    scatter(
                        r,
                        thing,
                        count,
                        cx - box.w * 0.2,
                        box.y + 2,
                        box.w * 0.4,
                        box.h - 4,
                        min(11, box.h / 3),
                    )
                )
        out.body.append(ring_at(centers[win], mid, box.w * 0.22, box.h / 2))
        out.answer.append({"big-small": "الكبير", "long-short": "الطويل"}.get(concept, "الكثير"))
        return out

    return task


def color_names() -> Task:
    """Pictures to color, each with a small crayon dot of its color."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.render.pages.workbook_pen import COLOR_ROWS

        out = Drawn()
        names = list(COLOR_ROWS)
        cols = 2 if box.h > box.w * 0.6 else len(names)  # a 2 × 2 block in a squarish box
        step, row_h = box.w / cols, box.h / (len(names) // cols)
        size = min(step - 10, row_h - 4)
        for k, name in enumerate(names):
            color, things = COLOR_ROWS[name]
            cx = box.x + box.w - (k % cols + 0.5) * step
            y = box.y + (k // cols) * row_h + (row_h - size) / 2
            out.body.append(pic(r.choice(things), cx - size / 2, y, size, "line"))
            out.body.append(
                draw.el(
                    "circle", cx=cx + size / 2 + 1, cy=y + 3, r=3, fill=color, stroke=INK, stroke_width=0.4
                )
            )
        out.answer.append("كل صورة بلون النقطة التي بجانبها")
        return out

    return task


def pen_row(skill: str) -> Task:
    """A short pen drill: a stroke of this kind on dots, from its start picture to its end picture."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.geometry import Stroke
        from qamra_workbook.render.pages.workbook_pen import PAIRS, _row_path, shape_stroke, traced

        out = Drawn()
        mid = box.y + box.h / 2
        if skill == "letter-strokes":
            from qamra_workbook.render.pages.workbook_pen import _letter_strokes

            step = box.w / 4
            for k, stroke in enumerate(_letter_strokes()):
                xs = [p[0] for p in stroke.polyline]
                ys = [p[1] for p in stroke.polyline]
                scale = min((box.h - 4) / (max(ys) - min(ys)), (step - 8) / (max(xs) - min(xs)))
                right = box.x + box.w - k * step - 4
                moved = stroke.scaled(scale, right - max(xs) * scale, box.y + 2 - min(ys) * scale)
                out.body.append(traced(moved, spacing=3.4, r=0.95, start=2))
            return out
        if skill in ("shapes", "circle", "square", "triangle"):
            kinds = ["circle", "square", "triangle"] if skill == "shapes" else [skill] * 3
            step = box.w / 3
            size = min(box.h - 6, step - 8)
            for k, kind in enumerate(kinds):
                out.body.append(
                    traced(
                        shape_stroke(kind, box.x + box.w - (k + 0.5) * step, mid, size),
                        spacing=3.6,
                        r=0.95,
                        start=2,
                    )
                )
            return out
        if skill == "vertical" or skill == "diagonal":
            step = box.w / 6
            for k in range(6):
                x = box.x + box.w - (k + 0.5) * step
                dx = 6 if skill == "diagonal" else 0
                out.body.append(
                    traced(
                        Stroke(draw.polyline([(x + dx, box.y + 2), (x - dx, box.y + box.h - 2)])),
                        spacing=3.6,
                        r=0.95,
                        start=2,
                    )
                )
            return out
        a, b = r.choice(PAIRS)
        size = min(box.h - 2, 18.0)
        out.body.append(pic(a, box.x + box.w - size, mid - size / 2, size))
        out.body.append(pic(b, box.x, mid - size / 2, size))
        kind = {"horizontal": "straight", "trace-path": "curve", "letter-strokes": "curve"}.get(skill, skill)
        amp = {"zigzag": 5.0, "curve": 4.0, "loops": 5.0}.get(kind, 0.0)
        out.body.append(
            traced(
                _row_path(kind, box.x + box.w - size - 4, box.x + size + 4, mid, amp),
                spacing=3.8,
                r=0.95,
                start=2,
            )
        )
        return out

    return task


def match_pairs(count: int = 3) -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.render.pages.workbook_thinking import POOL

        out = Drawn()
        things = r.sample(POOL, count)
        order = list(range(count))
        while count > 1 and order == list(range(count)):
            r.shuffle(order)
        pitch = box.h / count
        size = min(pitch - 3, 20.0)
        for i, thing in enumerate(things):
            y = box.y + i * pitch + pitch / 2
            out.body.append(pic(thing, box.x + box.w - size - 2, y - size / 2, size))
            out.body.append(pic(things[order[i]], box.x + 2, y - size / 2, size))
            out.body += [hook(box.x + box.w - size - 6, y), hook(box.x + size + 6, y)]
        for i in range(len(things)):
            j = order.index(i)
            out.body.append(
                answer_line(
                    (box.x + box.w - size - 6, box.y + i * pitch + pitch / 2),
                    (box.x + size + 6, box.y + j * pitch + pitch / 2),
                )
            )
        out.answer.append("كل صورة بمثيلتها")
        return out

    return task


def odd_level(ctx: PageContext) -> tuple[str, int]:
    """The book's level and volume from the page id («kg1-v2-p116»); KG2 when the id does not say."""
    parts = ctx.page.id.split("-")
    if len(parts) >= 2 and parts[0] in ("kg1", "kg2") and parts[1][1:].isdigit():
        return parts[0], int(parts[1][1:])
    return "kg2", 1


def odd_row() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.puzzles import generate_odd_rows
        from qamra_workbook.puzzles.odd import BASIC_GROUPS

        out = Drawn()
        level, volume = odd_level(ctx)
        if level == "kg1" and volume == 1:  # KG1's first volume: the difference is seen (3 alike, 1 not)
            row = generate_odd_rows(ctx.page.seed, ["same", "same"], [4, 4])[1]
        else:  # a named group, asked as a question under the pictures
            groups = BASIC_GROUPS if level == "kg1" else None
            row = generate_odd_rows(ctx.page.seed, ["same", "category"], [4, 4], groups)[1]
        question = 9.0 if row.question else 0.0
        if question:
            out.body.append(
                text(row.question, box.x + box.w / 2, box.y + box.h - 2.2, 4.6, color=ctx.style.deep)
            )
        square = box.h > box.w * 0.6  # a 2 × 2 block when the box is not a strip
        cols = 2 if square else 4
        step, rows_h = box.w / cols, (box.h - question) / (2 if square else 1)
        size = min(step - 8, rows_h - 6)
        for k, thing in enumerate(row.items):
            cx = box.x + box.w - (k % cols + 0.5) * step
            cy = box.y + (k // cols + 0.5) * rows_h
            out.body.append(pic(thing, cx - size / 2, cy - size / 2, size))
            if k == row.odd:
                out.body.append(ring_at(cx, cy, size / 2 + 2, size / 2 + 2))
        out.problems += row.problems()
        out.answer.append(f"المختلف: {row.answer}")
        return out

    return task


def pattern_row() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.puzzles import generate_pattern_rows

        out = Drawn()
        row = generate_pattern_rows(ctx.page.seed, ["AB", "AB"], [4, 5])[1]
        slots = len(row.shown) + row.blanks
        step = box.w / slots
        size = min(step - 4, box.h - 4)
        for k, thing in enumerate([*row.shown, *row.answer]):
            cx = box.x + box.w - (k + 0.5) * step
            if k < len(row.shown):
                out.body.append(pic(thing, cx - size / 2, box.y + box.h / 2 - size / 2, size))
            else:
                out.body.append(
                    card(
                        cx - size / 2,
                        box.y + box.h / 2 - size / 2,
                        size,
                        size,
                        r=4,
                        fill="#FFFFFF",
                        stroke=ctx.style.color,
                        dash="2 1.4",
                    )
                )
        out.problems += row.problems()
        out.answer.append("النمط: " + " ثم ".join(PICTURES[t].word_ar for t in row.answer))
        return out

    return task


def mini_maze() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.puzzles import generate_maze

        out = Drawn()
        m = generate_maze(4, 4, f"{ctx.page.seed}-mini", start_side="top", end_side="left")
        cell = min((box.w - 20) / 4, (box.h - 4) / 4)
        x0, y0 = box.x + box.w - 4 * cell - 4, box.y + 2
        walls = " ".join(
            draw.d_path(
                ("M", (x0 + a[0] * cell, y0 + a[1] * cell)), ("L", (x0 + b[0] * cell, y0 + b[1] * cell))
            )
            for a, b in m.walls()
        )
        out.body.append(draw.path(walls, stroke="#4F8A45", width=1.8))
        out.body.append(draw.start_dot((x0 + (m.start[0] + 0.5) * cell, y0 + 3), 1.8))
        out.body.append(pic("star", x0 - 15, y0 + (m.end[1] + 0.5) * cell - 7, 14))
        path = m.solve() or []
        pts = [(x0 + (c + 0.5) * cell, y0 + (rr + 0.5) * cell) for c, rr in path]
        out.body.append(draw.path(draw.polyline(pts), stroke="#E0483A", width=1, class_="key-line"))
        out.problems += m.problems()
        out.answer.append("المتاهة: طريق واحد إلى النجمة")
        return out

    return task


def mini_classify() -> Task:
    """Four things into two baskets by color."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        from qamra_workbook.render.pages.workbook_pen import COLOR_ROWS

        out = Drawn()
        names = ["أحمر", "أصفر"]
        items = [(t, g) for g, name in enumerate(names) for t in r.sample(COLOR_ROWS[name][1], 2)]
        r.shuffle(items)
        step = box.w / len(items)
        size = min(step - 6, box.h * 0.4)
        for k, (thing, _) in enumerate(items):
            cx = box.x + box.w - (k + 0.5) * step
            out.body.append(pic(thing, cx - size / 2, box.y, size))
            out.body.append(hook(cx, box.y + size + 2))
        for g, name in enumerate(names):
            cx = box.x + box.w * (0.72 if g == 0 else 0.28)
            y = box.y + box.h - 12
            color = COLOR_ROWS[name][0]
            out.body.append(
                draw.el(
                    "path",
                    d=draw.d_path(
                        ("M", (cx - 16, y)),
                        ("L", (cx + 16, y)),
                        ("L", (cx + 12, y + 11)),
                        ("L", (cx - 12, y + 11)),
                    )
                    + " Z",
                    fill=color,
                    stroke=INK,
                    stroke_width=0.6,
                )
            )
            out.body.append(hook(cx, y - 2))
            for k, (_, h) in enumerate(items):
                if h == g:
                    out.body.append(
                        answer_line((box.x + box.w - (k + 0.5) * step, box.y + size + 2), (cx, y - 2))
                    )
        out.answer.append("الأحمر في السلّة الحمراء، والأصفر في الصفراء")
        return out

    return task


def mini_symmetry() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        gap = min(box.w / 10, box.h / 7)
        x0, y0 = box.x + box.w / 2 - 4 * gap, box.y + 1

        def at(c: float, rr: float) -> tuple[float, float]:
            return x0 + c * gap, y0 + rr * gap

        for c in range(9):
            for rr in range(7):
                x, y = at(c, rr)
                out.body.append(draw.el("circle", cx=x, cy=y, r=0.7, fill="#9A94A8"))
        out.body.append(
            draw.path(
                draw.d_path(("M", at(4, -0.3)), ("L", at(4, 6.3))),
                stroke=ctx.style.color,
                width=0.6,
                stroke_dasharray="2 1.5",
            )
        )
        half = [(4, 0), (7, 3), (6, 3), (6, 6), (4, 6)]
        out.body.append(draw.path(draw.polyline([at(c, rr) for c, rr in half]), stroke=INK, width=1.3))
        out.body.append(
            draw.path(
                draw.polyline([at(8 - c, rr) for c, rr in half]),
                stroke="#E0483A",
                width=1.1,
                stroke_dasharray="2 1.4",
                class_="key-line",
            )
        )
        out.answer.append("النصف الآخر مثل الأول")
        return out

    return task


def stack(
    ctx: PageContext,
    sections: list[tuple[str, Task, float]],
    r: random.Random,
    top: float = 0.0,
    bottom: float = 204.0,
) -> Drawn:
    """Tasks one under the other, heights by weight."""
    out = Drawn()
    total = sum(w for _, _, w in sections)
    gap = 4.0
    room = bottom - top - gap * (len(sections) - 1)
    y = top
    for label, task, weight in sections:
        h = room * weight / total
        part = framed(ctx, Box(0, y, W, h), label, task, r)
        out.body += part.body
        out.answer += part.answer
        out.problems += part.problems
        y += h + gap
    return out


def grid(
    ctx: PageContext,
    sections: list[tuple[str, Task]],
    r: random.Random,
    top: float = 0.0,
    bottom: float = 204.0,
) -> Drawn:
    """Tasks in two columns (right column first on Arabic pages)."""
    out = Drawn()
    rows = (len(sections) + 1) // 2
    gap = 4.0
    h = (bottom - top - gap * (rows - 1)) / rows
    w = (W - gap) / 2
    rtl = ctx.page.lang != "en"
    for k, (label, task) in enumerate(sections):
        row, col = divmod(k, 2)
        x = (W - w if col == 0 else 0) if rtl else (0 if col == 0 else W - w)
        part = framed(ctx, Box(x, top + row * (h + gap), w, h), label, task, r)
        out.body += part.body
        out.answer += part.answer
        out.problems += part.problems
    return out


PEN_LABELS = {
    "horizontal": "خَطٌّ أُفُقِيٌّ",
    "vertical": "خُطوطٌ عَمودِيَّةٌ",
    "diagonal": "خُطوطٌ مائِلَةٌ",
    "zigzag": "خَطٌّ مُتَعَرِّجٌ",
    "curve": "خَطٌّ مُنْحَنٍ",
    "loops": "حَلَقاتٌ",
    "trace-path": "طَريقٌ",
    "dot-to-dot": "مُثَلَّثٌ",
    "coloring": "أَلْوانٌ",
    "shapes": "أَشْكالٌ",
    "letter-strokes": "ضَرَباتُ الحُروفِ",
    "circle": "دَوائِرُ",
}
THINKING: dict[str, tuple[str, Task]] = {
    "matching": ("أُطابِقُ الصُّوَرَ", match_pairs(3)),
    "odd-one-out": ("أَجِدُ المُخْتَلِفَ", odd_row()),
    "spot-difference": ("أَجِدُ المُخْتَلِفَ", odd_row()),
    "maze": ("أَحُلُّ المَتاهَةَ", mini_maze()),
    "classify": ("أُصَنِّفُ بِالأَلْوانِ", mini_classify()),
    "memory": ("أُطابِقُ الصُّوَرَ", match_pairs(3)),
    "puzzle": ("أُطابِقُ الصُّوَرَ", match_pairs(3)),
    "pattern": ("أُكْمِلُ النَّمَطَ", pattern_row()),
    "symmetry": ("أُكْمِلُ الرَّسْمَ", mini_symmetry()),
}
V1_LETTERS = ["أ", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ"]


def _thinking(skills: list[str]) -> list[tuple[str, Task]]:
    """The review's tasks for these skills, one per kind, filled up to four with the volume's other kinds."""
    out: dict[str, Task] = {}
    for s in [*skills, "matching", "pattern", "maze", "classify", "odd-one-out"]:
        if len(out) >= max(4, min(6, len(skills))):
            break
        if s in THINKING and THINKING[s][0] not in out:
            out[THINKING[s][0]] = THINKING[s][1]
    return list(out.items())[:6]


def _pen_task(skill: str) -> tuple[str, Task, float]:
    if skill == "coloring":
        return PEN_LABELS[skill], color_names(), 1.0
    kind = {"dot-to-dot": "triangle"}.get(skill, skill)
    return PEN_LABELS.get(skill, skill), pen_row(kind), 1.0


def review_sections(ctx: PageContext, r: random.Random) -> Drawn:
    params = ctx.page.params
    subject = ctx.page.section
    letters = [str(x) for x in params.get("letters", [])]
    numbers = [int(x) for x in params.get("numbers", [])]
    skills = [str(x) for x in params.get("skills", [])]
    if subject == "english":
        return stack(
            ctx,
            [
                ("Write the letters", write_letters(letters), 1.3),
                ("Circle the picture", circle_first_letter(letters), 1.0),
            ],
            r,
        )
    if subject == "arabic":
        return stack(
            ctx,
            [
                ("أَكْتُبُ الحَرْفَ", write_letters(letters), 1.0),
                ("أُحَوِّطُ الصّورَةَ الَّتي تَبْدَأُ بِالحَرْفِ", circle_first_letter(letters), 1.0),
            ],
            r,
        )
    if subject == "math" and numbers:
        others = sorted(set(range(0 if 0 in numbers else 1, 6)) - {numbers[-1]})
        return stack(
            ctx,
            [
                ("أَعُدُّ وَأَكْتُبُ", count_write(numbers), 1.3),
                ("أَتَتَبَّعُ الأَعْدادَ", trace_numbers(numbers), 0.8),
                (f"أُحَوِّطُ المَجْموعَةَ الَّتي فيها {ctx.num(numbers[-1])}", circle_group(numbers[-1], others), 1.0),
            ],
            r,
        )
    if subject == "math":
        tasks = {
            "colors": ("أُلَوِّنُ كُلَّ صورَةٍ بِلَوْنِها", color_names()),
            "big-small": ("أُحَوِّطُ الكَبيرَ", compare_pair("big-small")),
            "long-short": ("أُحَوِّطُ الطَّويلَ", compare_pair("long-short")),
            "many-few": ("أُحَوِّطُ الكَثيرَ", compare_pair("many-few")),
        }
        return grid(ctx, [tasks[s] for s in skills if s in tasks], r)
    if subject == "pen":
        return stack(ctx, [_pen_task(s) for s in skills], r)
    if subject == "thinking":
        return grid(ctx, _thinking(skills), r)
    # the volume's cross-subject review
    return stack(
        ctx,
        [
            ("أَكْتُبُ الحَرْفَ الأَوَّلَ مِنِ اسْمِ كُلِّ صورَةٍ", write_first_letter(V1_LETTERS), 1.0),
            ("أَعُدُّ وَأَكْتُبُ", count_write([2, 5, 0, 4]), 1.0),
            ("أَصِلُ الحَرْفَ الكَبيرَ بِالصَّغيرِ", match_capitals(list("ABCDEF")), 0.9),
        ],
        r,
    )


def compact(lines: list[str], limit: int = 100) -> list[str] | None:
    """The answer lines that fit a card of the answer key (the solved page above them shows every answer)."""
    out: list[str] = []
    for line in lines:
        if out and sum(len(x) for x in out) + len(line) > limit:
            break
        out.append(line)
    return out or None


@page_type("unit-review")
def unit_review(ctx: PageContext) -> Built:
    from qamra_workbook.render.pages.workbook_review2 import (
        review_sections_v2,  # lazy: it imports this module
    )
    from qamra_workbook.render.pages.workbook_review3 import review_sections_v3  # lazy, as above

    drawn = (
        review_sections_v3(ctx, ctx.rng("review"))
        or review_sections_v2(ctx, ctx.rng("review"))
        or review_sections(ctx, ctx.rng("review"))
    )
    return Built({"svg": svg(drawn.body)}, compact(drawn.answer), drawn.problems)


CHECKLIST_AR = {  # draft: educator review
    "grip": "مسكة القلم: بين الإبهام والسبابة، مسنودة على الوسطى",
    "pressure": "الضغط: خط واضح لا يمزّق الورقة",
    "direction": "الاتجاه: من البداية الخضراء، ومن اليمين إلى اليسار",
}
# The grown-ups' lines talk about the child, in the child's gender (`for_child`): the observation note and the
# checklist's columns (the child mastered the row's skill, is improving, needs practice)
OBSERVE_AR = "للمعلّمة أو الأهل: لاحظوا {الطفل وهو يتتبّع/الطفلة وهي تتتبّع}، ثم ضعوا علامة"
LEVELS_AR = ("{أتقنها/أتقنتها}", "{يتحسّن/تتحسّن}", "{يحتاج تدريبًا/تحتاج تدريبًا}")  # draft: educator review


def pen_check(ctx: PageContext, r: random.Random) -> Drawn:
    """Decision 9: two tracing tasks, then a short observation checklist for the teacher or parent."""
    params = ctx.page.params
    tracing = [str(t) for t in params.get("tracing", ["zigzag", "circle"])]
    checklist = [str(c) for c in params.get("checklist", ["grip", "pressure", "direction"])]
    out = stack(ctx, [(f"أَتَتَبَّعُ: {PEN_LABELS.get(t, t)}", pen_row(t), 1.0) for t in tracing], r, 0, 104)
    y = 110.0
    out.body.append(card(0, y, W, 204 - y, r=6, fill="#FFFDF6", stroke="#D8C9AC"))
    out.body.append(
        text(
            for_child(ctx, OBSERVE_AR),
            W - 6,
            y + 8,
            4.4,
            anchor="end",
            color=ctx.style.deep,
        )
    )
    col_x = [W - 128, W - 150, W - 172]  # the three levels, right to left
    for k, label in enumerate(LEVELS_AR):
        out.body.append(text(for_child(ctx, label), col_x[k], y + 18, 3.6, color=INK))
    row_h = 14.0
    for i, item in enumerate(checklist):
        yy = y + 22 + i * row_h
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
    yy = y + 22 + len(checklist) * row_h + 8
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
    out.answer.append(
        "تقييم بالملاحظة: " + "، ".join(CHECKLIST_AR.get(c, c).split(":")[0] for c in checklist)
    )
    missing = [c for c in ("grip", "pressure", "direction") if c not in checklist]
    if missing or len(tracing) != 2:
        out.problems.append("the pen check has the grip/pressure/direction checklist and two tracing tasks")
    return out


def assessment_sections(ctx: PageContext, r: random.Random) -> Drawn:
    subject = ctx.page.section
    covers = [str(x) for x in ctx.page.params.get("covers", [])]
    if subject == "pen":
        return pen_check(ctx, r)
    if subject == "arabic":
        letters = [c for c in covers if len(c) == 1] or V1_LETTERS
        out = stack(
            ctx,
            [
                ("أَقْرَأُ الحُروفَ", read_letters(letters), 0.8),
                ("أَكْتُبُ الحَرْفَ الأَوَّلَ مِنِ اسْمِ كُلِّ صورَةٍ", write_first_letter(letters), 1.1),
                ("أُحَوِّطُ الصّورَةَ الَّتي تَبْدَأُ بِالحَرْفِ", circle_first_letter(r.sample(letters, 3)), 1.2),
            ],
            r,
            0,
            178,
        )
    elif subject == "english":
        letters = [c for c in covers if len(c) == 1] or list("ABCDEFGH")
        out = stack(
            ctx,
            [
                ("Read the letters", read_letters(letters), 0.8),
                ("Match big and small", match_capitals(r.sample(letters, 5)), 1.1),
                ("Circle the picture", circle_first_letter(r.sample(letters, 3)), 1.2),
            ],
            r,
            0,
            178,
        )
    elif subject == "math":
        out = stack(
            ctx,
            [
                ("أَعُدُّ وَأَكْتُبُ", count_write([3, 0, 5, 1]), 1.3),
                ("أَتَتَبَّعُ الأَعْدادَ", trace_numbers([1, 2, 3, 4, 5, 0]), 0.8),
                ("أُحَوِّطُ الكَثيرَ", compare_pair("many-few"), 0.9),
            ],
            r,
            0,
            178,
        )
    else:
        out = grid(ctx, _thinking([*covers, "matching", "pattern", "maze", "classify"])[:4], r, 0, 178)
    out.body += score_box(ctx, 182)
    return out


@page_type("assessment")
def assessment(ctx: PageContext) -> Built:
    from qamra_workbook.render.pages.workbook_review2 import (
        assessment_sections_v2,  # lazy: it imports this module
    )
    from qamra_workbook.render.pages.workbook_review3 import assessment_sections_v3  # lazy, as above

    drawn = (
        assessment_sections_v3(ctx, ctx.rng("assessment"))
        or assessment_sections_v2(ctx, ctx.rng("assessment"))
        or assessment_sections(ctx, ctx.rng("assessment"))
    )
    return Built({"svg": svg(drawn.body)}, compact(drawn.answer), drawn.problems)
