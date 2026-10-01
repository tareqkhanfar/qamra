"""«دوسية التأسيس» Volume 3 reviews, assessments and the certificate: the tasks its units add (marks,
syllables, words and sentences, teen numbers, adding and subtracting in every form, the English units and
first words, joining strokes and long paths, growing patterns and cause and effect), the dispatchers the
review page asks first, and the certificate that closes the level (Addendum 5 §5)."""

from __future__ import annotations

import random

from markupsafe import Markup

from qamra_workbook.geometry import Stroke
from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import art, draw
from qamra_workbook.render.pages.journey import MEDAL, _ray, _star
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
from qamra_workbook.render.pages.workbook_english3 import en_word
from qamra_workbook.render.pages.workbook_math import GROUP_PICTURES
from qamra_workbook.render.pages.workbook_math2 import numeral_any
from qamra_workbook.render.pages.workbook_math3 import (
    MINUS,
    PLUS,
    Token,
    answer_box,
    crossed_group,
    group_pics,
    number_line,
    sentence_row,
    sign,
    teen_group,
)
from qamra_workbook.render.pages.workbook_pen import traced
from qamra_workbook.render.pages.workbook_pen3 import join_path
from qamra_workbook.render.pages.workbook_reading3 import (
    marked_letter,
    read_picture,
    syllable,
    word_row,
    word_width,
)
from qamra_workbook.render.pages.workbook_review import (
    CHECKLIST_AR,
    LEVELS_AR,
    Box,
    Drawn,
    Task,
    circle_first_letter,
    grid,
    match_pairs,
    mini_classify,
    mini_maze,
    read_letters,
    score_box,
    stack,
    write_letters,
)
from qamra_workbook.render.pages.workbook_review2 import ENGLISH_WORDS, pen_row2
from qamra_workbook.render.pages.workbook_sums3 import divider, pairs_of, sentence_key, sentence_tokens
from qamra_workbook.render.registry import Built, PageContext, page_type

V3_LETTERS = ["ف", "ق", "ك", "ل", "م", "ن", "ه", "و", "ي"]
# the S–Z words join the English review pool (Volume 2's dispatcher then serves those pages too)
ENGLISH_WORDS.update(
    {
        "S": ("sun", "sock", "sheep"),
        "T": ("tent", "tiger", "tree"),
        "U": ("umbrella", "uniform"),
        "V": ("van", "vase"),
        "W": ("window", "washer"),
        "X": ("xylophone",),
        "Y": ("yo-yo", "yogurt"),
        "Z": ("zebra", "zaatar"),
    }
)
UNIT_WORDS = {
    "Numbers": ("one", "two", "three"),
    "Colors": ("red", "blue", "green"),
    "Shapes": ("circle", "square", "triangle"),
    "Family": ("mother", "father", "baby"),
    "Body Parts": ("head", "eye", "hand"),
    "Animals": ("cat", "dog", "horse"),
    "Fruits": ("apple", "banana", "grapes"),
    "Food": ("bread", "milk", "egg"),
    "Toys": ("ball", "kite", "doll"),
    "School Objects": ("bag", "book", "pencil"),
}


def marks_task(letters: list[str], marks: list[str]) -> Task:
    """Letters with each mark in a grid: the child reads across."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        cw, ch = box.w / len(marks), box.h / len(letters)
        for i, char in enumerate(letters):
            for k, mark in enumerate(marks):
                x, y = box.x + box.w - (k + 1) * cw, box.y + i * ch
                out.body.append(marked_letter(char, mark, x + 2, y, cw - 4, ch - 6, ctx.style.color))
                out.body.append(
                    text(
                        syllable(char, mark),
                        x + cw / 2,
                        y + ch - 1,
                        min(5.0, ch * 0.25),
                        cls="wb-word",
                        color=INK,
                    )
                )
        out.answer.append("يقرأ: " + " ".join(syllable(c, m) for c in letters for m in marks))
        return out

    return task


def syllable_rows(rows: list[str]) -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(rows)
        for i, row in enumerate(rows):
            out.body.append(
                text(
                    row,
                    box.x + box.w - 6,
                    box.y + (i + 0.75) * pitch,
                    min(10.0, pitch * 0.6),
                    anchor="end",
                    cls="wb-word",
                    color=INK if i % 2 == 0 else ctx.style.deep,
                )
            )
        out.answer.append("يقرأ: " + "؛ ".join(rows))
        return out

    return task


def words_task(words: list[str]) -> Task:
    """Each word with two pictures: circle its picture."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(words)
        size = min(pitch - 4, 22.0)
        pool = ("duck", "car", "sun", "star", "tree", "house")
        for i, word in enumerate(words):
            y = box.y + i * pitch + pitch / 2
            right = read_picture(word)
            choices = [right, r.choice([p for p in pool if p != right])]
            r.shuffle(choices)
            out.body.append(text(word, box.x + box.w - 20, y + 3.5, 9, cls="wb-word", color=ctx.style.deep))
            for k, thing in enumerate(choices):
                cx = box.x + box.w - 50 - k * (size + 8)
                out.body.append(pic(thing, cx - size / 2, y - size / 2, size))
                if thing == right:
                    out.body.append(ring_at(cx, y, size / 2 + 2, size / 2 + 2))
            out.answer.append(f"{word}: {PICTURES[right].word_ar}")
        return out

    return task


def write_word_task(word: str) -> Task:
    """The word's picture, then the word in dots to trace and empty lines to write it alone."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        rows = 2 if box.h >= 54 else 1
        band = min(26.0 if rows == 2 else 30.0, (box.h - 4) / rows - (4 if rows == 2 else 2))
        size = min(box.h - 4, 30.0)
        out.body.append(pic(read_picture(word), box.x + box.w - size - 2, box.y + (box.h - size) / 2, size))
        right = box.x + box.w - size - 12
        top = box.y + 2
        for k in range(rows):
            top = box.y + 2 + k * (band + 4)
            for color, yy in (("#9BB7E0", top), ("#E27D63", top + band * 122 / 183)):
                out.body.append(
                    draw.el(
                        "path",
                        d=draw.d_path(("M", (box.x + 2, yy)), ("L", (right + 6, yy))),
                        stroke=color,
                        stroke_width=0.5,
                    )
                )
            if k == 0:
                out.body.append(word_row(word, right, top, band, ctx, dotted=True))
            else:
                out.body.append(draw.start_dot((right - 2, top + band * 0.2), 1.8))
        if rows == 1:  # the free part of the same lines starts where the dotted word ends
            out.body.append(draw.start_dot((right - word_width(word, band) - 8, top + band * 0.2), 1.8))
        out.answer.append(f"يكتب: {word}")
        return out

    return task


def sentences_task(pairs: list[tuple[str, str]]) -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(pairs)
        size = min(pitch - 4, 20.0)
        order = list(range(len(pairs)))
        while len(order) > 1 and order == list(range(len(pairs))):
            r.shuffle(order)
        for i, (sentence, thing) in enumerate(pairs):
            y = box.y + i * pitch + pitch / 2
            out.body.append(
                text(sentence, box.x + box.w - 4, y + 3, 8, anchor="end", cls="wb-word", color=ctx.style.deep)
            )
            out.body.append(hook(box.x + box.w - 60, y))
            j = order[i]
            yj = box.y + j * pitch + pitch / 2
            out.body.append(pic(thing, box.x + 4, yj - size / 2, size))
            out.body.append(hook(box.x + size + 8, yj))
            out.body.append(answer_line((box.x + box.w - 60, y), (box.x + size + 8, yj)))
        out.answer.append("كل جملة بصورتها")
        return out

    return task


def teen_task(numbers: list[int]) -> Task:
    """Two teen numbers as pictures (a bundle of ten and loose ones) to count, each with a box to write in."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        picks = r.sample(numbers, 2)
        half = box.w / 2
        gh = min(box.h - 22, 40.0)
        for k, n in enumerate(picks):
            x = box.x + box.w - (k + 1) * half
            out.body.append(
                teen_group(n, x + 8, box.y + (box.h - 22 - gh) / 2 + 1, half - 16, gh, GROUP_PICTURES[k])
            )
            out.body.append(answer_box(x + half / 2, box.y + box.h - 9, n, ctx, 24, 15, 10))
        out.answer.append("أعدّ وأكتب: " + "، ".join(ctx.num(n) for n in picks))
        return out

    return task


def sums_task(subtract: bool, top: int = 10, rows: int = 2) -> Task:
    """Pictures to count and the number sentence to finish, left to right: a + b = ▢ (or a − b)."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / rows
        h = min(10.0, pitch * 0.45)
        for i, (a, b) in enumerate(pairs_of(r, top, rows, subtract)):
            y = box.y + i * pitch
            thing = GROUP_PICTURES[(i + 4) % len(GROUP_PICTURES)]
            if subtract:
                out.body.append(crossed_group(thing, a, b, box.x + 2, y + 2, 92, pitch - 4))
            else:
                out.body.append(group_pics(thing, a, box.x + 2, y + 2, 40, pitch - 4))
                out.body.append(sign(PLUS, box.x + 48, y + pitch / 2, 6))
                out.body.append(group_pics(thing, b, box.x + 54, y + 2, 40, pitch - 4))
            out.body.append(divider(box.x + 100, y + 4, y + pitch - 4))
            out.body.append(sentence_row(ctx, sentence_tokens(a, b, subtract), box.x + 108, y + pitch / 2, h))
            out.answer.append(sentence_key(ctx, a, b, subtract))
        return out

    return task


def choose_task() -> Task:
    """One picture problem: circle + or − in the sentence, then write the answer."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        subtract = r.random() < 0.5
        a, b = pairs_of(r, 10, 1, subtract)[0]
        thing = GROUP_PICTURES[5]
        if subtract:
            out.body.append(crossed_group(thing, a, b, box.x + 2, box.y + 2, 92, box.h - 4))
        else:
            out.body.append(group_pics(thing, a, box.x + 2, box.y + 2, 40, box.h - 4))
            out.body.append(sign(PLUS, box.x + 48, box.y + box.h / 2, 6))
            out.body.append(group_pics(thing, b, box.x + 54, box.y + 2, 40, box.h - 4))
        out.body.append(divider(box.x + 100, box.y + 4, box.y + box.h - 4))
        total = a - b if subtract else a + b
        tokens: list[Token] = [
            ("num", a),
            ("choice", MINUS if subtract else PLUS),
            ("num", b),
            ("eq", ""),
            ("box", total),
        ]
        out.body.append(sentence_row(ctx, tokens, box.x + 106, box.y + box.h / 2, 9, gap=2.0))
        out.answer.append(sentence_key(ctx, a, b, subtract))
        return out

    return task


def line_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        a, b = r.randint(1, 5), r.randint(1, 4)
        out.body.append(sentence_row(ctx, sentence_tokens(a, b, False), box.x + 10, box.y + 7, 9))
        out.body.append(
            number_line(box.x + 8, box.y + box.h - 14, box.w - 16, 10, ctx, jumps=(a, b), size=6.0)
        )
        out.answer.append(sentence_key(ctx, a, b, False))
        return out

    return task


def vocab_task(units: list[str]) -> Task:
    """Words from the units and their pictures, shuffled: connect each word to its picture."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        words = [r.choice(UNIT_WORDS[u]) for u in units if u in UNIT_WORDS][:5]
        words = [w for w in words if w in PICTURES]
        order = list(range(len(words)))
        while len(order) > 1 and order == list(range(len(words))):
            r.shuffle(order)
        pitch = box.h / max(len(words), 1)
        size = min(pitch - 3, 18.0)
        for i, w in enumerate(words):
            y = box.y + i * pitch + pitch / 2
            out.body.append(en_word(PICTURES[w].word_en, box.x + 24, y + 2.5, 6.5, ctx.style.color))
            out.body.append(hook(box.x + 48, y))
            j = order[i]
            yj = box.y + j * pitch + pitch / 2
            out.body.append(pic(w, box.x + box.w - size - 4, yj - size / 2, size))
            out.body.append(hook(box.x + box.w - size - 8, yj))
            out.body.append(answer_line((box.x + 48, y), (box.x + box.w - size - 8, yj)))
        out.answer.append(", ".join(PICTURES[w].word_en for w in words))
        return out

    return task


def joins_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        cap = min(box.h - 10, 12.0)
        base = box.y + (box.h - cap) / 2 + cap
        for color, yy in (("#9BB7E0", base - cap), ("#E27D63", base)):
            out.body.append(
                draw.el(
                    "path",
                    d=draw.d_path(("M", (box.x + 2, yy)), ("L", (box.x + box.w - 2, yy))),
                    stroke=color,
                    stroke_width=0.5,
                )
            )
        stroke = Stroke(join_path("hills", box.x + box.w - 8, box.x + 8, base, cap))
        out.body.append(traced(stroke, spacing=2.8, r=0.8, start=2.2))
        return out

    return task


def growing_task() -> Task:
    """Dots that grow by one: three steps given, two dashed boxes for the child (the key fills them in)."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        step = box.w / 5
        rad = min(5.0, (box.h - 8) / 11.6)  # five stacked dots must fit the height
        pitch = 2 * rad + 1.6
        for k in range(5):
            cx = box.x + box.w - (k + 0.5) * step
            if k >= 3:  # the box first, so the key's dots sit on it
                out.body.append(
                    card(
                        cx - rad - 3,
                        box.y + box.h - 5 * pitch - 5,
                        2 * rad + 6,
                        5 * pitch + 4,
                        r=3,
                        fill="#FFFFFF",
                        stroke=ctx.style.color,
                        dash="2 1.4",
                    )
                )
            for j in range(k + 1):
                cy = box.y + box.h - 3 - rad - j * pitch
                if k < 3:
                    out.body.append(draw.el("circle", cx=cx, cy=cy, r=rad, fill=ctx.style.color))
                else:
                    out.body.append(draw.el("circle", cx=cx, cy=cy, r=rad, fill="#E0483A", class_="key-ring"))
        out.answer.append("الخطوتان التاليتان: ٤ ثم ٥")
        return out

    return task


def causes_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pairs = [("raindrop", "umbrella"), ("sun", "hat"), ("hen", "egg")]
        order = [1, 2, 0]
        pitch = box.h / 3
        size = min(pitch - 3, 16.0)
        for i, (a, b) in enumerate(pairs):
            y = box.y + i * pitch + pitch / 2
            out.body.append(pic(a, box.x + box.w - size - 2, y - size / 2, size))
            out.body.append(hook(box.x + box.w - size - 6, y))
            yj = box.y + order[i] * pitch + pitch / 2
            out.body.append(pic(b, box.x + 2, yj - size / 2, size))
            out.body.append(hook(box.x + size + 6, yj))
            out.body.append(answer_line((box.x + box.w - size - 6, y), (box.x + size + 6, yj)))
        out.answer.append("المطر والمظلة، الشمس والقبعة، الدجاجة والبيضة")
        return out

    return task


def river_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        cx = box.x + box.w / 2
        out.body.append(draw.el("rect", x=cx - 12, y=box.y, width=24, height=box.h, fill="#8EC1EC"))
        out.body.append(pic("duck", box.x + box.w - 24, box.y + box.h / 2 - 10, 20))
        out.body.append(pic("flower", box.x + 4, box.y + box.h / 2 - 10, 20))
        out.answer.append("أي حلّ معقول للعبور")
        return out

    return task


def fine_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        size = min(box.h - 2, 40.0)
        out.body.append(
            pic("peacock", box.x + box.w / 2 - size / 2, box.y + (box.h - size) / 2, size, "line")
        )
        out.answer.append("تلوين دقيق داخل الأجزاء")
        return out

    return task


def pen_row3(skill: str) -> Task:
    """joins → the joining chain; complex-path → a short winding path; others → Volume 2's rows."""
    if skill == "joins":
        return joins_task()
    if skill in ("complex-path", "fine-coloring"):
        return pen_row2("narrow-path") if skill == "complex-path" else fine_task()
    return pen_row2(skill)


PEN_LABELS_3 = {
    "joins": "خطوط الوصل",
    "dot-to-dot": "مثلث",
    "complex-path": "طريق طويل",
    "fine-coloring": "تلوين دقيق",
}
V3_MATH = {"addition", "subtraction", "story-add", "story-subtract", "number-line", "choose-operation"}


def review_sections_v3(ctx: PageContext, r: random.Random) -> Drawn | None:
    params, subject = ctx.page.params, ctx.page.section
    numbers = [int(x) for x in params.get("numbers", [])]
    skills = [str(x) for x in params.get("skills", [])]
    marks = [str(h) for h in params.get("harakat", [])]
    units = [str(u) for u in params.get("units", [])]
    letters = [str(x) for x in params.get("letters", [])]
    if subject == "arabic" and len(letters) >= 3 and not marks and not skills:
        return stack(  # three letters need taller writing rows than the two-letter reviews give them
            ctx,
            [
                ("أكتب الحرف", write_letters(letters), 1.5),
                ("أحوّط الصورة التي تبدأ بالحرف", circle_first_letter(letters), 0.95),
            ],
            r,
        )
    if subject == "arabic" and marks:
        out = stack(
            ctx,
            [
                ("أقرأ الحرف مع كل حركة", marks_task(["ب", "ن", "م"], marks), 1.4),
                ("أقرأ", syllable_rows(["بَ بُ بِ بْ", "نَ نُ نِ نْ", "مَ مُ مِ مْ"]), 0.8),
            ],
            r,
        )
        out.answer = ["يقرأ الحرف مع الفتحة والضمة والكسرة والسكون"]
        return out
    if subject == "arabic" and "short-syllables" in skills:
        return stack(
            ctx,
            [
                ("مقاطع قصيرة", syllable_rows(["سَ سُ سِ", "تَ تُ تِ", "رَ رُ رِ"]), 1.0),
                ("مقاطع طويلة", syllable_rows(["با بو بي", "دا دو دي", "نا نو ني"]), 1.0),
                ("أركّب وأقرأ", marks_task(["ك", "ل"], ["فتحة", "ضمة", "كسرة"]), 1.2),
            ],
            r,
        )
    if subject == "arabic" and "read-words" in skills:
        return stack(
            ctx,
            [
                ("أقرأ وأحوّط الصورة", words_task(["بَاب", "قَمَر", "الْفِيل"]), 1.4),
                ("أكتب الكلمة", write_word_task("سَمَك"), 0.8),
            ],
            r,
        )
    if subject == "arabic" and "read-sentences" in skills:
        return stack(
            ctx,
            [
                (
                    "أصل الجملة بصورتها",
                    sentences_task(
                        [("كَتَبَ باسِم", "writing"), ("رَسَمَتْ سَلْمى", "drawing"), ("لَعِبَ عُمَر", "playing")]
                    ),
                    1.4,
                ),
                ("أقرأ وأحوّط الصورة", words_task(["شَمْس", "وَرْد"]), 1.0),
            ],
            r,
        )
    if subject == "math" and numbers and max(numbers) > 10:
        return stack(
            ctx,
            [
                ("أعدّ العشرة والآحاد وأكتب", teen_task(numbers), 1.0),
                ("أجمع", sums_task(False, 5, 1), 0.9),
                ("أحوّط الأكبر", compare_task(), 0.8),
            ],
            r,
        )
    if subject == "math" and V3_MATH & set(skills):
        top = int(params.get("max", 10))
        kinds = [
            kind
            for kind, wanted in (
                ("add", {"addition", "story-add"}),
                ("sub", {"subtraction", "story-subtract"}),
                ("line", {"number-line"}),
                ("choose", {"choose-operation"}),
            )
            if wanted & set(skills)
        ]
        per_task = {1: 4, 2: 2}.get(len(kinds), 1)  # one kind: four problems; more kinds: fewer, bigger
        sections: dict[str, tuple[str, Task, float]] = {
            "add": ("أجمع", sums_task(False, top, per_task), 1.0),
            "sub": ("أطرح", sums_task(True, top, per_task), 1.0),
            "line": ("أجمع على خط الأعداد", line_task(), 0.95),
            "choose": ("أجمع أم أطرح؟", choose_task(), 0.85),
        }
        return stack(ctx, [sections[k] for k in kinds], r)
    if subject == "english" and units:
        return stack(ctx, [("Match the words", vocab_task(units), 1.0)], r)
    if subject == "pen" and ("joins" in skills or "complex-path" in skills):
        from qamra_workbook.render.pages.workbook_review import pen_row

        pen_tasks = [
            (PEN_LABELS_3.get(s, s), pen_row3(s) if s != "dot-to-dot" else pen_row("triangle"), 1.0)
            for s in skills
        ]
        return stack(ctx, pen_tasks, r)
    if subject == "thinking" and ("cause-effect" in skills or "problem-solving" in skills):
        tasks2 = {
            "classify": ("أصنّف بالألوان", mini_classify()),
            "pattern": ("أكمل النمط المتزايد", growing_task()),
            "cause-effect": ("السبب والنتيجة", causes_task()),
            "maze": ("أحلّ المتاهة", mini_maze()),
            "problem-solving": ("أرسم حلًّا: كيف تعبر البطة؟", river_task()),
        }
        return grid(ctx, [tasks2[s] for s in skills if s in tasks2][:4], r)
    if subject == "mixed" and "arabic" in params.get("covers", []):
        return stack(
            ctx,
            [
                ("أقرأ وأحوّط الصورة", words_task(["بَاب", "فِيل"]), 0.9),
                ("أجمع وأطرح", sums_task(False, 10, 1), 0.75),
                ("Match the words", vocab_task(["Animals", "Fruits", "Toys"]), 0.95),
                ("أكمل النمط", growing_task(), 0.85),
            ],
            r,
        )
    return None


def compare_task() -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pairs = [tuple(r.sample(range(1, 21), 2)) for _ in range(3)]
        step = box.w / 3
        h = min(box.h - 10, 18.0)
        for k, (a, b) in enumerate(pairs):
            x = box.x + box.w - (k + 1) * step
            cx, cy = x + step / 2, box.y + box.h / 2
            out.body.append(card(x + 2, box.y + 1, step - 4, box.h - 2, r=5, fill="#FFFFFF"))
            out.body.append(numeral_any(ctx, a, cx + step * 0.23, cy, h))
            out.body.append(numeral_any(ctx, b, cx - step * 0.23, cy, h))
            out.body.append(ring_at(cx + step * 0.23 * (1 if a > b else -1), cy, step * 0.2, h * 0.62))
        out.answer.append("الأكبر: " + "، ".join(ctx.num(max(a, b)) for a, b in pairs))
        return out

    return task


def assessment_sections_v3(ctx: PageContext, r: random.Random) -> Drawn | None:
    subject = ctx.page.section
    covers = [str(x) for x in ctx.page.params.get("covers", [])]
    tracing = [str(t) for t in ctx.page.params.get("tracing", [])]
    if subject == "pen" and {"joins", "complex-path"} & set(tracing):
        checklist = [str(c) for c in ctx.page.params.get("checklist", [])]
        out = stack(ctx, [(f"أتتبّع: {PEN_LABELS_3.get(t, t)}", pen_row3(t), 1.0) for t in tracing], r, 0, 104)
        out.body += checklist_box(ctx, checklist)
        out.answer.append(
            "تقييم ملاحظة: " + "، ".join(CHECKLIST_AR.get(c, c).split(":")[0] for c in checklist)
        )
        if len(tracing) != 2 or {"grip", "pressure", "direction"} - set(checklist):
            out.problems.append(
                "the pen check has the grip/pressure/direction checklist and two tracing tasks"
            )
        return out
    if subject == "arabic" and "harakat" in covers:
        out = stack(
            ctx,
            [
                ("أقرأ الحروف", read_letters(V3_LETTERS), 0.75),
                ("أقرأ الحرف مع حركته", marks_task(["ب", "د"], ["فتحة", "ضمة", "كسرة", "سكون"]), 0.9),
                ("أقرأ وأحوّط الصورة", words_task(["قَمَر", "بَاب"]), 0.85),
                ("أكتب الكلمة", write_word_task("فِيل"), 0.9),
            ],
            r,
            0,
            178,
        )
    elif subject == "math" and "11–20" in covers:
        out = stack(
            ctx,
            [
                ("أعدّ العشرة والآحاد وأكتب", teen_task([13, 17]), 1.0),
                ("أجمع", sums_task(False, 10, 1), 0.75),
                ("أطرح", sums_task(True, 10, 1), 0.75),
            ],
            r,
            0,
            178,
        )
    elif subject == "english" and "vocabulary" in covers:
        letters = [c for c in covers if len(c) == 1]
        out = stack(
            ctx,
            [
                ("Read the letters", read_letters(letters), 0.8),
                ("Match the words", vocab_task(["Animals", "Fruits", "Toys", "Food"]), 1.4),
                ("Read and circle", words_task_en(["cat", "sun", "bed"]), 1.0),
            ],
            r,
            0,
            178,
        )
    elif subject == "thinking" and "problem-solving" in covers:
        out = grid(
            ctx,
            [
                ("أصنّف بالألوان", mini_classify()),
                ("أكمل النمط", growing_task()),
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


def words_task_en(words: list[str]) -> Task:
    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(words)
        size = min(pitch - 4, 20.0)
        pool = ("duck", "car", "star", "tree", "house", "fish")
        for i, word in enumerate(words):
            y = box.y + i * pitch + pitch / 2
            choices = [word, r.choice([p for p in pool if p != word])]
            r.shuffle(choices)
            out.body.append(text(word, box.x + 16, y + 3, 7, cls="wb-en", color=ctx.style.deep, rtl=False))
            for k, thing in enumerate(choices):
                cx = box.x + 44 + k * (size + 10)
                out.body.append(pic(thing, cx - size / 2, y - size / 2, size))
                if thing == word:
                    out.body.append(ring_at(cx, y, size / 2 + 2, size / 2 + 2))
            out.answer.append(f"{word}: {PICTURES[word].word_en}")
        return out

    return task


@page_type("workbook-certificate", frame="full")
def workbook_certificate(ctx: PageContext) -> Built:
    """The level's certificate: the child's character, name, date, a badge per subject and the signature."""
    badges = [
        Markup('<span class="cert-stop" style="background: {}">{}</span>').format(color, art.icon(icon))
        for icon, color in (
            ("pencil", "#E27D63"),
            ("letter-ba", "#D9961B"),
            ("abacus", "#5A9E6C"),
            ("letter-a", "#D65E54"),
            ("brain", "#8C79C9"),
        )
    ]
    level = str(ctx.page.params.get("level_title", "دوسية التأسيس"))
    data = {
        "line": ctx.text(f"لقد {{أنهيتَ/أنهيتِ}} «{level}» بنجاح"),
        "name": ctx.book.child.name,
        "date": ctx.book.date_ar(),
        "character": ctx.assets.character.resolve().as_uri() if ctx.assets.character else "",
        "badges": badges,
        "star": _star,
        "ray": _ray,
        "medal": MEDAL,
        "signer": "توقيع المعلّمة أو الأهل",
    }
    return Built(data)


def checklist_box(ctx: PageContext, checklist: list[str], y: float = 110.0) -> list[str]:
    """The teacher's or parent's observation checklist (grip, pressure, direction) under the tracing tasks."""
    out = [card(0, y, W, 204 - y, r=6, fill="#FFFDF6", stroke="#D8C9AC")]
    out.append(
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
        out.append(text(label, col_x[k], y + 18, 3.6, color=INK))
    for i, item in enumerate(checklist):
        yy = y + 22 + i * 14
        out.append(draw.path(draw.d_path(("M", (4, yy)), ("L", (W - 4, yy))), stroke="#E4D6BC", width=0.4))
        out.append(text(CHECKLIST_AR.get(item, item), W - 6, yy + 9, 3.9, anchor="end", color=INK))
        for x in col_x:
            out.append(
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
    out.append(
        text(
            "ملاحظات: ..................................................................",
            W - 6,
            yy,
            3.9,
            anchor="end",
            color="#676B83",
        )
    )
    out.append(
        text(
            "التوقيع والتاريخ: ...................................",
            W - 6,
            yy + 10,
            3.9,
            anchor="end",
            color="#676B83",
        )
    )
    return out
