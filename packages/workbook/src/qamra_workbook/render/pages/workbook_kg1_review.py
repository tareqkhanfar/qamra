"""«دوسية التأسيس» KG1 unit reviews and assessments (Addendum 5 §2.5, decision 9), from the KG2 tasks with
KG1's params and scope: recognition before writing (circle the letter, trace it), the KG1 pen strokes in the
pen reviews and the pen check, picture sums in the math reviews, the volume's own letters and numbers in
the cross-subject review. Pages the KG2 code already serves well are handed to it."""

from __future__ import annotations

import random

from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.foundation_kg1 import ENGLISH_PICTURES_KG1, LETTER_PICTURES_KG1, LOOKALIKE_KG1
from qamra_workbook.render.pages.letters import tracing_row
from qamra_workbook.render.pages.workbook_arabic import row_svg
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    card,
    fit_lines,
    for_child,
    glyph,
    pic,
    ring_at,
    shape_of,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_kg1_arabic import first_sound_pictures
from qamra_workbook.render.pages.workbook_kg1_math import sums_task
from qamra_workbook.render.pages.workbook_kg1_pen import kg1_pen_row
from qamra_workbook.render.pages.workbook_review import (
    CHECKLIST_AR,
    LEVELS_AR,
    OBSERVE_AR,
    THINKING,
    Box,
    Drawn,
    Task,
    assessment_sections,
    color_names,
    compact,
    compare_pair,
    count_write,
    grid,
    match_capitals,
    match_pairs,
    mini_maze,
    mini_symmetry,
    pen_row,
    read_letters,
    review_sections,
    score_box,
    stack,
    trace_numbers,
    write_first_letter,
    write_letters,
)
from qamra_workbook.render.pages.workbook_review2 import (
    _place_words,
    count_write_any,
    letter_place,
    order_numbers,
    pattern_abc_task,
    pen_row2,
    related_task,
    sequence_task,
    shapes_task,
    trace_numbers_any,
)
from qamra_workbook.render.registry import Built, PageContext, page_type

PEN_LABELS_KG1 = {
    "horizontal": "خُطوطٌ أُفُقِيَّةٌ",
    "vertical": "خُطوطٌ عَمودِيَّةٌ",
    "diagonal": "خُطوطٌ مائِلَةٌ",
    "arc": "أَقْواسٌ",
    "wave": "أَمْواجٌ",
    "zigzag": "خَطٌّ مُتَعَرِّجٌ",
    "circle": "دَوائِرُ",
    "spiral": "حَلَزونٌ",
    "shape": "أَشْكالٌ",
    "coloring": "أَلْوانٌ",
    "maze": "مَتاهَةٌ",
    "lane": "داخِلَ المَمَرِّ",
    "dot-to-dot": "مُثَلَّثٌ",
    "bridge": "جُسورٌ",
    "loop": "حَلَقاتٌ",
    "teeth": "أَسْنانُ السّينِ",
    "small-loop": "حَلَقاتٌ مُغْلَقَةٌ",
    "winding": "طَريقٌ مُتَعَرِّجٌ",
    "grid-copy": "أَرْسُمُ مِثْلَهُ",
    "connected": "خُطوطٌ مُتَّصِلَةٌ",
    "connected-rtl": "خَطٌّ مُتَّصِلٌ إلى اليَسارِ",
    "connected-ltr": "خَطٌّ مُتَّصِلٌ إلى اليَمينِ",
    "trace-path": "طَريقٌ",
    "drawing": "أُكْمِلُ الرَّسْمَ",
    "sharp-turns": "مُنْعَطَفاتٌ",
}
VOLUME_LETTERS = {1: "أبتثجحخدذ", 2: "رزسشصضطظعغ", 3: "فقكلمنهوي"}
VOLUME_ENGLISH = {1: "ABCDEF", 2: "IJKLMN", 3: "STUVWX"}
THINKING_KG1 = {
    "connect": "matching",
    "shadows": "matching",
    "related": "related",
    "need": "related",
    "hidden": "matching",
}
THINKING_KG1 |= {"pattern-complete": "pattern", "sequence": "sequence", "puzzle": "puzzle"}
# the KG2 pattern row draws shapes the picture library has no ids for; the ABC pattern task serves instead


def pen_task(skill: str) -> tuple[str, Task, float]:
    label = PEN_LABELS_KG1.get(skill, skill)
    if skill == "coloring":
        return label, color_names(), 1.0
    if skill == "maze":
        return label, mini_maze(), 1.2
    if skill == "drawing":
        return label, mini_symmetry(), 1.2
    if skill in ("spiral", "winding"):
        return label, pen_row2("spiral" if skill == "spiral" else "narrow-path"), 1.0
    if skill in ("shape", "dot-to-dot", "trace-path", "vertical", "diagonal"):
        return label, pen_row({"shape": "shapes", "dot-to-dot": "triangle"}.get(skill, skill)), 1.0
    return label, kg1_pen_row({"grid-copy": "connected", "sharp-turns": "zigzag"}.get(skill, skill)), 1.0


def circle_letter(letters: list[str]) -> Task:
    """For each letter: the model, then three look-alikes in circles; circle the same letter."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(letters)
        for i, char in enumerate(letters):
            cy = box.y + (i + 0.5) * pitch
            shape = shape_of(char)
            out.body.append(
                glyph(
                    shape,
                    *fit_lines(shape, box.x + box.w - 18, cy - 8, 14, 16),
                    color=ctx.style.deep,
                    width=14,
                )
            )
            options = [char, *r.sample([c for c in LOOKALIKE_KG1.get(char, "بت") if c != char], 2)]
            r.shuffle(options)
            radius = min(pitch / 2 - 2, 10.0)
            for k, c in enumerate(options):
                cx = box.x + box.w - 40 - (k + 0.5) * 28
                out.body.append(
                    draw.el(
                        "circle", cx=cx, cy=cy, r=radius, fill="#FFFFFF", stroke="#D8C9AC", stroke_width=0.6
                    )
                )
                s = shape_of(c)
                out.body.append(
                    glyph(
                        s,
                        *fit_lines(s, cx - radius * 0.7, cy - radius * 0.75, radius * 1.4, radius * 1.5),
                        color=INK,
                        width=14,
                    )
                )
                if c == char:
                    out.body.append(ring_at(cx, cy, radius + 1, radius + 1))
            out.answer.append(f"{char}: الدائرة {ctx.num(options.index(char) + 1)} من اليمين")
        return out

    return task


def trace_letters(letters: list[str]) -> Task:
    """A dotted row per letter (up to three): trace, do not write alone."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        chosen = letters[:3]
        pitch = box.h / len(chosen)
        for i, char in enumerate(chosen):
            shape = shape_of(char)
            cap = min(16.0, (pitch - 12) * (0.6 if shape.rtl else 0.75))
            row, _ = row_svg(
                tracing_row(shape, width=box.w, cap=cap, number=ctx.num), box.x, box.y + i * pitch
            )
            out.body.append(row)
        return out

    return task


def pictures_for(letter: str, r: random.Random, count: int = 1, avoid: set[str] | None = None) -> list[str]:
    """Pictures whose name starts with `letter` (English: the word the plan taught), taught words first."""
    if "A" <= letter.upper() <= "Z":
        pool = [ENGLISH_PICTURES_KG1[letter.upper()]]
    else:
        pool = first_sound_pictures(letter)
    pool = [p for p in pool if not avoid or p not in avoid]
    return r.sample(pool, min(count, len(pool)))


def everyone(letter: str) -> list[str]:
    """Every letter of the same alphabet the plan teaches (the fallback for a review of only two letters)."""
    if "A" <= letter.upper() <= "Z":
        return list(ENGLISH_PICTURES_KG1)
    return list(LETTER_PICTURES_KG1)


def with_pictures(letters: list[str], r: random.Random) -> list[str]:
    return [c for c in letters if pictures_for(c, r, 1)]


def circle_first_letter(letters: list[str]) -> Task:
    """For each letter: three pictures, circle the one that starts with it (KG1's pictures only)."""

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
            wrong: list[str] = []
            # the volume's other letters first; any other taught letter when there are too few of them
            pool = [c for c in letters if c != char] + [
                c for c in everyone(char) if c != char and c not in letters
            ]
            for other in pool:
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


def kg1_review(ctx: PageContext, r: random.Random) -> Drawn | None:
    params, subject = ctx.page.params, ctx.page.section
    letters = [str(x) for x in params.get("letters", [])]
    skills = [str(x) for x in params.get("skills", [])]
    numbers = [int(x) for x in params.get("numbers", [])]
    volume = int(params.get("volume", 1))
    if subject == "arabic" and params.get("mode") == "positions":
        chosen, words = _place_words(letters, r, 3)
        return stack(
            ctx,
            [
                ("أَيْنَ الحَرْفُ في الكَلِمَةِ؟", letter_place(chosen, words), 1.4),
                ("أُحَوِّطُ الصّورَةَ الَّتي تَبْدَأُ بِالحَرْفِ", circle_first_letter(letters[:2]), 1.0),
            ],
            r,
        )
    if subject == "arabic" and letters:
        return stack(
            ctx,
            [
                ("أُحَوِّطُ الحَرْفَ نَفْسَهُ", circle_letter(letters[:3]), 1.0),
                ("أُحَوِّطُ الصّورَةَ الَّتي تَبْدَأُ بِالحَرْفِ", circle_first_letter(with_pictures(letters, r)[:3]), 1.0),
                ("أَتَتَبَّعُ الحَرْفَ", trace_letters(letters), 0.9),
            ],
            r,
        )
    if subject == "math" and len(numbers) > 6:  # counting to 10: four groups, five numerals, a missing number
        top = max(numbers)
        return stack(
            ctx,
            [
                ("أَعُدُّ وَأَكْتُبُ", count_write_any(sorted(r.sample([n for n in numbers if n >= 2], 4))), 1.3),
                ("أَتَتَبَّعُ الأَعْدادَ", trace_numbers_any(numbers[-5:]), 0.8),
                ("أَكْتُبُ العَدَدَ النّاقِصَ", order_numbers(list(range(max(1, top - 4), top + 1))), 0.8),
            ],
            r,
        )
    if subject == "math" and "max" in params:
        top = int(params["max"])
        if "subtract" not in params.get("ops", ("add", "subtract")):  # the addition unit: no subtraction yet
            return stack(ctx, [("أَجْمَعُ بِالصُّوَرِ", sums_task(top, False, 4), 2.0)], r)
        return stack(
            ctx, [("أَجْمَعُ بِالصُّوَرِ", sums_task(top, False), 1.0), ("أَطْرَحُ بِالصُّوَرِ", sums_task(top, True), 1.0)], r
        )
    if subject == "pen":
        return stack(ctx, [pen_task(s) for s in skills[:5]], r)
    if subject == "thinking":
        keys = [THINKING_KG1.get(s, s) for s in skills]
        extra = {"related": ("أَصِلُ ما يُناسِبُ", related_task()), "sequence": ("أُرَتِّبُ القِصَّةَ", sequence_task())}
        extra["pattern"] = ("أُكْمِلُ النَّمَطَ", pattern_abc_task())
        tasks: dict[str, Task] = {}
        for k in [*keys, "matching", "pattern", "classify", "odd-one-out"]:
            found = extra.get(k) or THINKING.get(k)
            if found and found[0] not in tasks and len(tasks) < 4:
                tasks[found[0]] = found[1]
        return grid(ctx, list(tasks.items()), r)
    if subject == "english" and letters:
        return stack(
            ctx,
            [
                ("Trace the letters", trace_letters(letters), 1.0),
                ("Circle the picture", circle_first_letter(with_pictures(letters, r)[:3]), 1.0),
                ("Match big and small", match_capitals(letters[:4]), 0.9),
            ],
            r,
        )
    if subject == "mixed":
        counts = {1: [2, 5, 0, 4], 2: [6, 9, 10, 7], 3: [3, 8, 10, 6]}[volume]
        return stack(
            ctx,
            [
                (
                    "أُحَوِّطُ الصّورَةَ الَّتي تَبْدَأُ بِالحَرْفِ",
                    circle_first_letter(r.sample(list(VOLUME_LETTERS[volume]), 3)),
                    1.1,
                ),
                ("أَعُدُّ وَأَكْتُبُ", count_write(counts) if volume == 1 else count_write_any(counts), 1.0),
                ("أَصِلُ الحَرْفَ الكَبيرَ بِالصَّغيرِ", match_capitals(list(VOLUME_ENGLISH[volume])), 0.9),
            ],
            r,
        )
    return None


def merged(lines: list[str], width: int = 46, most: int = 2) -> list[str]:
    """Short answer lines side by side, at most `most` of them: a line per picture would make the card of the
    answer key tall (the solved page above it shows every answer)."""
    out: list[str] = []
    for line in lines:
        if out and len(out[-1]) + len(line) + 2 <= width:
            out[-1] += (", " if line.isascii() else "، ") + line
        else:
            out.append(line)
    return out[:most]


@page_type("kg1-unit-review")
def kg1_unit_review(ctx: PageContext) -> Built:
    from qamra_workbook.render.pages.workbook_review2 import review_sections_v2

    r = ctx.rng("review")
    drawn = kg1_review(ctx, r) or review_sections_v2(ctx, r) or review_sections(ctx, r)
    return Built({"svg": svg(drawn.body)}, compact(merged(drawn.answer)), drawn.problems)


def pen_check_kg1(ctx: PageContext, r: random.Random) -> Drawn:
    """Decision 9 with KG1's strokes: two tracing rows, then the grip / pressure / direction checklist."""
    tracing = [str(t) for t in ctx.page.params.get("tracing", ["wave", "circle"])]
    checklist = [str(c) for c in ctx.page.params.get("checklist", ["grip", "pressure", "direction"])]
    out = stack(ctx, [(f"أَتَتَبَّعُ: {label}", task, 1.0) for label, task, _ in map(pen_task, tracing)], r, 0, 104)
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
    col_x = [W - 128, W - 150, W - 172]
    for k, label in enumerate(LEVELS_AR):
        out.body.append(text(for_child(ctx, label), col_x[k], y + 18, 3.6, color=INK))
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
    yy = y + 30 + len(checklist) * 14
    out.body.append(text("ملاحظات: " + "." * 70, W - 6, yy, 3.9, anchor="end", color="#676B83"))
    out.body.append(text("التوقيع والتاريخ: " + "." * 40, W - 6, yy + 10, 3.9, anchor="end", color="#676B83"))
    out.answer.append(
        "تقييم بالملاحظة: " + "، ".join(CHECKLIST_AR.get(c, c).split(":")[0] for c in checklist)
    )
    if {"grip", "pressure", "direction"} - set(checklist) or len(tracing) != 2:
        out.problems.append("the pen check has the grip/pressure/direction checklist and two tracing tasks")
    return out


def kg1_assessment(ctx: PageContext, r: random.Random) -> Drawn | None:
    params, subject = ctx.page.params, ctx.page.section
    letters = [str(x) for x in params.get("letters", [])]
    numbers = [int(x) for x in params.get("numbers", [])]
    covers = [str(x) for x in params.get("covers", [])]
    if subject == "pen":
        return pen_check_kg1(ctx, r)
    if subject == "arabic" and letters:
        write = [str(x) for x in params.get("write", [])][:3]
        sections = [
            ("أَقْرَأُ الحُروفَ", read_letters(letters), 0.8),
            (
                "أُحَوِّطُ الصّورَةَ الَّتي تَبْدَأُ بِالحَرْفِ",
                circle_first_letter(r.sample(with_pictures(letters, r), 3)),
                1.2,
            ),
            (
                "أَكْتُبُ الحَرْفَ" if write else "أَتَتَبَّعُ الحَرْفَ",
                write_letters(write) if write else trace_letters(letters[:3]),
                1.1,
            ),
        ]
    elif subject == "math" and numbers:
        third = (
            ("أَجْمَعُ بِالصُّوَرِ", sums_task(3, False), 1.0)
            if "picture-add" in covers
            else ("أُحَوِّطُ المُثَلَّثاتِ وَأُلَوِّنُ الدَّوائِرَ", shapes_task(), 0.9)
            if "shapes" in covers
            else ("أُحَوِّطُ الكَثيرَ", compare_pair("many-few"), 0.9)
        )
        counting = r.sample([n for n in numbers if n], min(4, len(numbers)))
        sections = [
            ("أَعُدُّ وَأَكْتُبُ", count_write(counting) if max(numbers) <= 5 else count_write_any(counting), 1.3),
            (
                "أَتَتَبَّعُ الأَعْدادَ",
                trace_numbers(numbers[:6]) if max(numbers) <= 5 else trace_numbers_any(numbers[-5:]),
                0.8,
            ),
            third,
        ]
    elif subject == "english" and letters:
        sections = [
            ("Read the letters", read_letters(letters), 0.8),
            ("Match big and small", match_capitals(r.sample(letters, min(5, len(letters)))), 1.1),
            ("Circle the picture", circle_first_letter(r.sample(with_pictures(letters, r), 3)), 1.2),
        ]
    elif subject == "thinking":
        keys = [THINKING_KG1.get(s, s) for s in covers]
        extra = {"related": ("أَصِلُ ما يُناسِبُ", related_task()), "sequence": ("أُرَتِّبُ القِصَّةَ", sequence_task())}
        extra["pattern"] = ("أُكْمِلُ النَّمَطَ", pattern_abc_task())
        tasks: dict[str, Task] = {}
        for k in [*keys, "matching", "pattern", "classify", "maze"]:
            found = extra.get(k) or THINKING.get(k)
            if found and found[0] not in tasks and len(tasks) < 4:
                tasks[found[0]] = found[1]
        out = grid(ctx, list(tasks.items()), r, 0, 178)
        out.body += score_box(ctx, 182)
        return out
    else:
        return None
    out = stack(ctx, sections, r, 0, 178)
    out.body += score_box(ctx, 182)
    return out


@page_type("kg1-assessment")
def kg1_assessment_page(ctx: PageContext) -> Built:
    r = ctx.rng("assessment")
    drawn = kg1_assessment(ctx, r) or assessment_sections(ctx, r)
    return Built({"svg": svg(drawn.body)}, compact(merged(drawn.answer)), drawn.problems)


__all__ = ["kg1_assessment_page", "kg1_unit_review", "match_pairs", "write_first_letter"]
