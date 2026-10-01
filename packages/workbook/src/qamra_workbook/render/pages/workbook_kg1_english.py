"""«دوسية التأسيس» KG1 English (recognition first): the letter page traces only in Volume 1 (one written row
from Volume 2), the ten vocabulary units as picture cards to say and color (numbers, colors and shapes drawn
on the page), the color-and-say page and the vocabulary review. English pages run left to right."""

from __future__ import annotations

import random

from markupsafe import Markup

from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import en_letter, row_room, tracing_row
from qamra_workbook.render.pages.workbook_arabic import word_markup
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    answer_line,
    card,
    fit_lines,
    glyph,
    hook,
    pic,
    ring_at,
    shape_of,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_pen import crayon, shape_stroke
from qamra_workbook.render.pages.workbook_review import Box, Drawn, Task
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.strokes import letter

NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
NUMBER_AR = {1: "واحد", 2: "اثنان", 3: "ثلاثة", 4: "أربعة", 5: "خمسة"}
COLORS = {"red": ("#E5604E", "أحمر", "apple"), "blue": ("#5E86D6", "أزرق", "fish")}
COLORS |= {"yellow": ("#F7C84A", "أصفر", "sun"), "green": ("#6FAE5F", "أخضر", "leaf")}
SHAPES = {"circle": "دائرة", "square": "مربع", "triangle": "مثلث", "star": "نجمة"}
VOCAB = {  # the units of the plan, for the reviews
    "Numbers": ["one", "two", "three", "four", "five"],
    "Colors": ["red", "blue", "yellow", "green"],
    "Shapes": ["circle", "square", "triangle", "star"],
    "Family": ["mother", "father", "brother", "sister"],
    "Body Parts": ["head", "eye", "nose", "mouth", "hand"],
    "Animals": ["cat", "cow", "horse", "bird", "sheep"],
    "Fruits": ["apple", "banana", "orange", "grapes", "lemon"],
    "Food": ["bread", "milk", "rice", "cheese"],
    "Toys": ["ball", "doll", "car", "kite"],
    "School Objects": ["book", "pencil", "bag", "crayon"],
}


def crayon_fit(x: float, y: float, width: float, color: str) -> str:
    """The crayon of the plan's color pages drawn `width` mm wide (it is 34 mm wide as drawn)."""
    k = width / 34.0
    return f'<g transform="translate({draw.n(x)} {draw.n(y)}) scale({draw.n(k)})">{crayon(0, 0, color)}</g>'


def word_art(word: str, x: float, y: float, size: float, style: str = "line") -> str:
    """A vocabulary word as a picture: numbers as counted apples, colors as a crayon, shapes as outlines."""
    if word in NUMBERS:
        n = NUMBERS[word]
        per = min(n, 3)
        s = size * (0.6 if n == 1 else 0.45 if n == 2 else 0.34)
        rows = (n + per - 1) // per
        left, top = x + (size - per * s * 1.05) / 2, y + (size - rows * s * 1.1) / 2
        return "".join(
            pic("apple", left + (k % per) * s * 1.05, top + (k // per) * s * 1.1, s) for k in range(n)
        )
    if word in COLORS:
        color, _, thing = COLORS[word]
        width = size * 0.8
        return crayon_fit(x + size * 0.1, y + size * 0.04, width, color) + pic(
            thing, x + size * 0.15, y + size * 0.3, size * 0.7, "line"
        )
    if word in SHAPES:
        if word == "star":
            return draw.el(
                "path",
                d=draw.star_points(x + size / 2, y + size / 2, size * 0.42, size * 0.18),
                fill="#FFFFFF",
                stroke=INK,
                stroke_width=1.0,
                stroke_linejoin="round",
            )
        return draw.path(
            shape_stroke(word, x + size / 2, y + size / 2, size * 0.7).d,
            stroke=INK,
            width=1.0,
            fill="#FFFFFF",
        )
    return pic(word, x, y, size, style)  # type: ignore[arg-type]


def word_ar(word: str) -> str:
    if word in NUMBERS:
        return NUMBER_AR[NUMBERS[word]]
    if word in COLORS:
        return COLORS[word][1]
    if word in SHAPES:
        return SHAPES[word]
    return PICTURES[word].word_ar


@page_type("kg1-en-letter")
def kg1_en_letter(ctx: PageContext) -> Built:
    """The KG2 letter page, traced only in Volume 1; «box» is allowed for X (the sound is inside the word)."""
    out = en_letter(ctx)
    char = str(ctx.page.params.get("letter", "A")).upper()
    word = str(ctx.page.params.get("word", ""))
    out.problems = [
        p for p in out.problems if not (char == "X" and "x" in word.lower() and "does not start" in p)
    ]
    if int(ctx.page.params.get("volume", 1)) == 1:
        capital, small = letter(char, "capital"), letter(char.lower(), "small")
        cap = 28.0 if row_room(small, 33)[1] > 0 else 33.0
        out.data["rows"] = [
            tracing_row(capital, width=176, cap=cap, number=ctx.num),
            tracing_row(small, width=176, cap=cap, number=ctx.num),
            tracing_row(capital, width=176, cap=cap, number=ctx.num),
        ]
    return out


def vocab_card(ctx: PageContext, word: str, x: float, y: float, w: float, h: float) -> str:
    out = [card(x, y, w, h, r=7)]
    size = min(w - 12, h - 26)
    out.append(word_art(word, x + (w - size) / 2, y + 4, size))
    en = word[:1].upper() + word[1:]
    out.append(
        f'<text x="{draw.n(x + w / 2)}" y="{draw.n(y + h - 12)}" font-size="7" text-anchor="middle" '
        f'class="wb-en" fill="{INK}"><tspan fill="{ctx.style.color}">{en[:1]}</tspan>{en[1:]}</text>'
    )
    out.append(text(word_ar(word), x + w / 2, y + h - 3.5, 4.6, cls="wb-word", color="#676B83"))
    return "".join(out)


@page_type("kg1-vocab-unit")
def kg1_vocab_unit(ctx: PageContext) -> Built:
    """A unit's words as cards: the picture to color, the English word and the Arabic under it."""
    unit = str(ctx.page.params.get("unit", "Animals"))
    words = [str(w) for w in ctx.page.params.get("words", VOCAB.get(unit, []))][:6]
    problems = [
        f"no vocabulary picture for {w!r}"
        for w in words
        if w not in PICTURES and w not in NUMBERS | COLORS | SHAPES
    ]
    cols = 2
    rows = (len(words) + 1) // 2
    cw, ch = (W - 6) / cols, (204 - 6 * (rows - 1)) / rows
    body = []
    for k, word in enumerate([w for w in words if w in PICTURES or w in NUMBERS | COLORS | SHAPES]):
        row, col = divmod(k, cols)
        x = col * (cw + 6) if k // cols < rows - 1 or len(words) % cols == 0 else (W - cw) / 2
        body.append(vocab_card(ctx, word, x, row * (ch + 6), cw, ch))
    answer = [f"{w} = {word_ar(w)}" for w in words]
    return Built({"svg": svg(body)}, answer, problems)


@page_type("kg1-en-coloring")
def kg1_en_coloring(ctx: PageContext) -> Built:
    """Three letters with their pictures to color and their words to say."""
    letters = [str(c).upper() for c in ctx.page.params.get("letters", ["P", "Q", "R"])]
    words = [str(w) for w in ctx.page.params.get("words", ["pencil", "queen", "rabbit"])]
    pitch = 204 / len(letters)
    body = []
    for i, (char, word) in enumerate(zip(letters, words, strict=True)):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 5, r=7))
        for k, shape in enumerate((shape_of(char), shape_of(char.lower()))):
            body.append(
                glyph(
                    shape,
                    *fit_lines(shape, 8 + k * 24, y + pitch / 2 - 16, 20, 28),
                    color=ctx.style.color,
                    width=14,
                )
            )
        size = min(pitch - 12, 56.0)
        body.append(pic(word, 68, y + (pitch - 4) / 2 - size / 2, size, "line"))
        body.append(
            word_markup(
                PICTURES[word].word_en[:1].upper() + PICTURES[word].word_en[1:],
                152,
                y + pitch / 2 - 2,
                8,
                ctx.style.color,
                rtl=False,
            )
        )
        body.append(text(PICTURES[word].word_ar, 152, y + pitch / 2 + 9, 4.8, cls="wb-word", color="#676B83"))
    return Built({"svg": svg(body)}, [f"{c}: {w}" for c, w in zip(letters, words, strict=True)], [])


def match_words(pairs: list[str]) -> Task:
    """Words on the left, their pictures shuffled on the right: draw the lines."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        order = list(range(len(pairs)))
        while order == sorted(order):
            r.shuffle(order)
        pitch = box.h / len(pairs)
        size = min(pitch - 3, 24.0)
        for i, word in enumerate(pairs):
            cy = box.y + (i + 0.5) * pitch
            out.body.append(
                text(
                    word[:1].upper() + word[1:],
                    box.x + 4,
                    cy + 2.5,
                    6.4,
                    cls="wb-en",
                    anchor="start",
                    rtl=False,
                )
            )
            out.body.append(hook(box.x + 46, cy))
            j = order[i]
            py = box.y + (j + 0.5) * pitch
            out.body.append(word_art(word, box.x + box.w - size - 2, py - size / 2, size, "color"))
            out.body.append(hook(box.x + box.w - size - 6, py))
            out.body.append(answer_line((box.x + 46, cy), (box.x + box.w - size - 6, py)))
            out.answer.append(f"{word} → {word_ar(word)}")
        return out

    return task


def circle_words(rows: list[tuple[str, list[str]]]) -> Task:
    """«Circle: cat»: three pictures a row, the named one to circle."""

    def task(ctx: PageContext, box: Box, r: random.Random) -> Drawn:
        out = Drawn()
        pitch = box.h / len(rows)
        size = min(pitch - 4, 26.0)
        for i, (target, options) in enumerate(rows):
            cy = box.y + (i + 0.5) * pitch
            out.body.append(
                text(f"Circle: {target}", box.x + 4, cy + 2.5, 5.6, cls="wb-en", anchor="start", rtl=False)
            )
            for k, word in enumerate(options):
                cx = box.x + box.w - (k + 0.5) * (box.w - 48) / 3
                out.body.append(word_art(word, cx - size / 2, cy - size / 2, size, "color"))
                if word == target:
                    out.body.append(ring_at(cx, cy, size / 2 + 2, size / 2 + 2))
            out.answer.append(f"{target}: {word_ar(target)}")
        return out

    return task


def vocab_tasks(units: list[str], r: random.Random) -> tuple[Task, Task]:
    words = {
        u: [w for w in VOCAB.get(u, []) if w in PICTURES or w in NUMBERS | COLORS | SHAPES] for u in units
    }
    pool = [w for ws in words.values() for w in ws if w in PICTURES or w in SHAPES]
    pairs = [r.choice(words[u]) for u in units if words[u]][:4]
    rows = []
    for u in units[-3:]:
        if not words[u]:
            continue
        target = r.choice(words[u])
        options = [target, *r.sample([w for w in pool if w != target and w not in words[u]], 2)]
        r.shuffle(options)
        rows.append((target, options))
    return match_words(pairs), circle_words(rows)


@page_type("kg1-vocab-review")
def kg1_vocab_review(ctx: PageContext) -> Built:
    from qamra_workbook.render.pages.workbook_review import compact, stack

    units = [str(u) for u in ctx.page.params.get("units", list(VOCAB))]
    r = ctx.rng("vocab")
    match, circle = vocab_tasks(units, r)
    drawn = stack(
        ctx, [("Match the word to its picture", match, 1.1), ("Circle the picture", circle, 1.0)], r
    )
    return Built({"svg": svg(drawn.body)}, compact(drawn.answer), drawn.problems)


@page_type("kg1-find-letter-en")
def kg1_find_letter_en(ctx: PageContext) -> Built:
    """Four big rows that fill the page, the plan's letters taking turns: circle the letter (capital or small)
    among six."""
    targets = [str(x).upper() for x in ctx.page.params.get("letters", ["A"])]
    r = ctx.rng("rows")
    pool = [c for c in "ABCDEFGHKMNRSTU" if c not in targets]
    rows = 4
    row_h = 204 / rows
    body, answer, problems = [], [], []
    for i in range(rows):
        t = targets[i % len(targets)]
        y = i * row_h
        items = [t, t.lower(), t, t.lower()][: 2 + i % 2]
        items += [c if r.random() < 0.5 else c.lower() for c in r.sample(pool, 6 - len(items))]
        r.shuffle(items)
        body.append(card(0, y + 2, W, row_h - 6, r=7))
        body.append(card(3, y + 6, 32, row_h - 14, r=5, fill=ctx.style.tint, stroke="none"))
        for k, c in enumerate((t, t.lower())):
            shape = shape_of(c)
            scale, dx, dy = fit_lines(shape, 5 + k * 14, y + 12, 13, row_h - 26)
            body.append(glyph(shape, scale, dx, dy, color=ctx.style.deep, width=13))
        step = (W - 46) / len(items)
        for k, c in enumerate(items):
            cx = 42 + (k + 0.5) * step
            shape = shape_of(c)
            body.append(glyph(shape, *fit_lines(shape, cx - 10, y + 10, 20, row_h - 22), color=INK, width=12))
            if c.upper() == t:
                body.append(ring_at(cx, y + row_h / 2 - 1, 11, row_h / 2 - 8))
        found = sum(1 for c in items if c.upper() == t)
        problems += [f"row {i + 1} shows {t} only {found} times"] if found < 2 else []
        answer.append(f"{t} {t.lower()}: {found}")
    return Built({"svg": svg(body)}, answer, problems)


__all__ = ["VOCAB", "Markup", "match_words", "word_art"]
