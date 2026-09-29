"""«دوسية التأسيس» find-the-letter and match pages, for Arabic (right to left) and English (left to right):
color every target letter in a grid of letter bubbles (Arabic) or circle it in rows (English), pick the letter
a picture starts with, and connect letter ↔ picture ↔ word. Every page carries its answer key and checks."""

from __future__ import annotations

import random
from dataclasses import dataclass

from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.workbook_arabic import first_letter, same_letter, word_markup
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    answer_line,
    card,
    fit_lines,
    glyph,
    hook,
    pic,
    picture_id,
    picture_of,
    ring_at,
    shape_of,
    svg,
    text,
)
from qamra_workbook.render.registry import Built, PageContext, page_type

CRAYONS = (("#E5604E", "الأحمر"), ("#5E86D6", "الأزرق"), ("#F2B33D", "الأصفر"), ("#5FA85A", "الأخضر"))
# letters that look alike, the distractors a find page draws from (count the dots: Addendum 5 §3)
LOOKALIKE = {
    "أ": "لد",
    "ب": "تثن",
    "ت": "بثن",
    "ث": "بتن",
    "ج": "حخع",
    "ح": "جخع",
    "خ": "جحع",
    "د": "ذرز",
    "ذ": "درز",
    "ر": "زد",
    "ز": "رذ",
}


# the pictures a find page shows for a letter: the plan's letter words first (the child met them already)
LETTER_WORDS = {
    "أ": ("rabbit", "lion", "jug"),
    "ب": ("duck", "house", "door", "cow"),
    "ت": ("apple", "crown", "dates"),
    "ث": ("fox", "garlic", "fridge"),
    "ج": ("camel", "carrot", "bell"),
    "ح": ("horse", "bag", "dove"),
    "خ": ("sheep", "tent", "cucumber"),
    "د": ("bear", "hen", "rooster", "bucket"),
    "ذ": ("corn", "tail"),
}


def words_starting(letter: str, avoid: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """Pictures whose word starts with `letter` (أ for any alif): its known words, else the library's."""
    known = [w for w in LETTER_WORDS.get(letter, ()) if w not in avoid]
    return known or [
        pid
        for pid, p in PICTURES.items()
        if same_letter(first_letter(p.word_ar), letter) and pid not in avoid
    ]


@dataclass(frozen=True)
class Cell:
    char: str
    target: int | None  # index of the target letter, None for a distractor


def letter_grid(r: random.Random, targets: list[str], others: list[str], cells: int) -> list[Cell]:
    each = max(3, (cells * 2 // 5) // len(targets))
    out = [Cell(t, i) for i, t in enumerate(targets) for _ in range(each)]
    while len(out) < cells:
        out.append(Cell(others[len(out) % len(others)], None))
    r.shuffle(out)
    return out


def _grid_problems(grid: list[Cell], targets: list[str]) -> list[str]:
    out = []
    for i, t in enumerate(targets):
        n = sum(1 for c in grid if c.target == i)
        if n < 3:
            out.append(f"{t} appears {n} times in the grid (at least 3)")
    if any(c.target is None and c.char in targets for c in grid):
        out.append("a distractor is one of the target letters")
    return out


def arabic_find(ctx: PageContext) -> Built:
    params = ctx.page.params
    targets = [str(x) for x in params.get("letters", [params.get("letter", "ب")])]
    others = [str(x) for x in params.get("distractors", [])]
    for t in targets:
        others += [c for c in LOOKALIKE.get(t, "") if c not in targets and c not in others]
    r = ctx.rng("grid")
    cols, rows = (6, 3) if len(targets) >= 3 else (5, 4)
    grid = letter_grid(r, targets, others, cols * rows)
    body = []
    legend_w = W / len(targets)
    for i, t in enumerate(targets):
        color, name = CRAYONS[i]
        x = W - (i + 1) * legend_w
        body.append(card(x + 2, 0, legend_w - 4, 15, r=7.5))
        body.append(draw.el("circle", cx=x + legend_w - 11, cy=7.5, r=4.6, fill=color))
        shape = shape_of(t)
        body.append(glyph(shape, *fit_lines(shape, x + legend_w - 32, 1.5, 14, 12), color=INK, width=14))
        body.append(text(f"ألوّنه ب{name}", x + legend_w - 36, 10.2, 4.6, anchor="end", color=color))
    cw, ch, top = W / cols, 26.0, 20.0
    solved_marks = []
    for k, cell in enumerate(grid):
        cx = W - (k % cols + 0.5) * cw
        cy = top + (k // cols + 0.5) * (ch + 3)
        radius = min(13.0, cw / 2 - 2)
        body.append(
            draw.el("circle", cx=cx, cy=cy, r=radius, fill="#FFFFFF", stroke="#D8C9AC", stroke_width=0.6)
        )
        if cell.target is not None:
            solved_marks.append(ring_at(cx, cy, radius + 0.5, radius + 0.5, CRAYONS[cell.target][0], 1.6))
        shape = shape_of(cell.char)
        body.append(
            glyph(
                shape,
                *fit_lines(shape, cx - radius * 0.85, cy - radius * 0.85, radius * 1.7, radius * 1.7),
                color=INK,
                width=15,
            )
        )
    body += solved_marks
    y = top + rows * (ch + 3) + 6
    body.append(text("أحوّط الحرف الذي تبدأ به الصورة", W - 4, y + 2, 5, anchor="end", color=ctx.style.deep))
    answer = [f"{t}: {ctx.num(sum(1 for c in grid if c.target == i))} مرات" for i, t in enumerate(targets)]
    problems = _grid_problems(grid, targets)
    used: set[str] = set()
    stacked = len(targets) >= 3  # three cards one under the other; two side by side
    card_w = W if stacked else W / len(targets)
    card_h = (204 - y - 6 - 3 * (len(targets) - 1)) / len(targets) if stacked else 40.0
    for i, t in enumerate(targets):
        choices_pool = words_starting(t, used)
        if not choices_pool:
            problems.append(f"no picture starts with {t}")
            continue
        word = r.choice(choices_pool)
        used.add(word)
        options = [t, *r.sample([c for c in [*targets, *others] if c != t], 2)]
        r.shuffle(options)
        x = 0.0 if stacked else W - (i + 1) * card_w
        top = y + 6 + (i * (card_h + 3) if stacked else 0)
        size = min(card_h - 6, 28.0)
        body.append(card(x + 2, top, card_w - 4, card_h, r=6))
        body.append(pic(word, x + card_w - size - 6, top + (card_h - size) / 2, size))
        box_h = min(card_h - 8, 20.0)
        for j, c in enumerate(options):
            bx = x + card_w - size - 18 - j * 19
            body.append(
                draw.el(
                    "rect",
                    x=bx - 8,
                    y=top + (card_h - box_h) / 2,
                    width=16,
                    height=box_h,
                    rx=4,
                    fill="#FFFFFF",
                    stroke="#D8C9AC",
                    stroke_width=0.5,
                )
            )
            shape = shape_of(c)
            body.append(
                glyph(
                    shape,
                    *fit_lines(shape, bx - 7, top + (card_h - box_h) / 2 + 1, 14, box_h - 2),
                    color=INK,
                    width=15,
                )
            )
            if c == t:
                body.append(ring_at(bx, top + card_h / 2, 10, box_h / 2 + 2))
        answer.append(f"{PICTURES[word].word_ar}: {t}")
    return Built({"svg": svg(body)}, answer, problems)


def english_find(ctx: PageContext) -> Built:
    params = ctx.page.params
    targets = [str(x).upper() for x in params.get("letters", ["A"])]
    r = ctx.rng("rows")
    pool = [c for c in "ABCDEFGHKMNRSTU" if c not in targets]
    body, answer, problems = [], [], []
    row_h = min(52.0, 200 / len(targets))
    for i, t in enumerate(targets):
        y = i * row_h
        items = [t, t.lower(), t, t.lower()][: 3 + (i % 2)]
        items += [c if r.random() < 0.5 else c.lower() for c in r.sample(pool, 7 - len(items))]
        r.shuffle(items)
        body.append(card(0, y + 2, W, row_h - 6, r=7))
        body.append(card(3, y + 6, 30, row_h - 14, r=5, fill=ctx.style.tint, stroke="none"))
        for k, c in enumerate((t, t.lower())):
            shape = shape_of(c)
            body.append(
                glyph(
                    shape,
                    *fit_lines(shape, 5 + k * 13, y + 12, 12, row_h - 26),
                    color=ctx.style.deep,
                    width=13,
                )
            )
        step = (W - 44) / len(items)
        for k, c in enumerate(items):
            cx = 42 + (k + 0.5) * step
            shape = shape_of(c)
            body.append(glyph(shape, *fit_lines(shape, cx - 8, y + 12, 16, row_h - 26), color=INK, width=12))
            if c.upper() == t:
                body.append(ring_at(cx, y + row_h / 2 - 1, 10, row_h / 2 - 9))
        count = sum(1 for c in items if c.upper() == t)
        if count < 2:
            problems.append(f"row {t} shows the letter {count} times")
        answer.append(f"{t} {t.lower()}: {count}")
    return Built({"svg": svg(body)}, answer, problems)


@page_type("find-letter")
def find_letter(ctx: PageContext) -> Built:
    return english_find(ctx) if ctx.page.lang == "en" else arabic_find(ctx)


def _deranged(r: random.Random, items: list[str], avoid: list[str]) -> list[str]:
    """`items` shuffled so no item keeps the place it has in `avoid` (when there are at least 2)."""
    out = list(items)
    for _ in range(50):
        r.shuffle(out)
        if len(out) < 2 or all(a != b for a, b in zip(out, avoid, strict=True)):
            break
    return out


def _x(rtl: bool, x: float, w: float = 0.0) -> float:
    """An x measured from the reading start: from the right on Arabic pages."""
    return W - x - w if rtl else x


def match_capitals(ctx: PageContext) -> Built:
    letters = [str(x).upper() for x in ctx.page.params.get("letters", list("ABCDEFGH"))]
    r = ctx.rng("match")
    smalls = _deranged(r, [c.lower() for c in letters], [c.lower() for c in letters])
    pitch = 200 / len(letters)
    body, key = [], []
    for i, c in enumerate(letters):
        y = i * pitch + pitch / 2
        for k, char in enumerate((c, smalls[i])):
            x = 12 if k == 0 else W - 42
            body.append(card(x, y - pitch / 2 + 2, 30, pitch - 4, r=5))
            shape = shape_of(char)
            body.append(
                glyph(shape, *fit_lines(shape, x + 4, y - pitch / 2 + 4, 22, pitch - 8), color=INK, width=12)
            )
        body += [hook(46, y), hook(W - 46, y)]
    for i, c in enumerate(letters):
        j = smalls.index(c.lower())
        key.append(answer_line((46, i * pitch + pitch / 2), (W - 46, j * pitch + pitch / 2)))
    answer = [" ".join(f"{c}–{c.lower()}" for c in letters)]
    return Built({"svg": svg(body + key)}, answer, [])


@page_type("match-letter-picture")
def match_letter_picture(ctx: PageContext) -> Built:
    params = ctx.page.params
    if ctx.page.lang == "en" and params.get("mode") == "capital-small":
        return match_capitals(ctx)
    rtl = ctx.page.lang != "en"
    letters = [str(x) for x in params.get("letters", [])]
    words = [str(w) for w in params.get("words", [])]
    r = ctx.rng("match")
    problems = []

    def starts(word: str) -> str:
        if not rtl:
            return picture_of(word).word_en[:1].upper()
        return next((t for t in letters if same_letter(first_letter(word), t)), "")

    owners = {w: starts(w) for w in words}
    problems += [f"«{w}» starts with none of {letters}" for w, t in owners.items() if not t]
    problems += [f"{t} has no picture" for t in letters if t not in owners.values()]
    pics = _deranged(r, words, words)
    labels = _deranged(r, words, pics)
    pitch = 200 / max(len(words), 1)
    body, key = [], []
    letter_y = {t: (i + 0.5) * 200 / len(letters) for i, t in enumerate(letters)}
    for t in letters:
        x = _x(rtl, 0, 36)
        y = letter_y[t]
        body.append(card(x, y - 20, 36, 40, r=7, fill=ctx.style.tint, stroke="none"))
        shape = shape_of(t)
        body.append(glyph(shape, *fit_lines(shape, x + 5, y - 16, 26, 32), color=ctx.style.deep, width=14))
        body.append(hook(_x(rtl, 40), y))
    for i, w in enumerate(pics):
        y = (i + 0.5) * pitch
        x = _x(rtl, 70, 40)
        body.append(card(x, y - 21, 40, 42, r=7))
        body.append(pic(picture_id(w), x + 2, y - 18, 36))
        body += [hook(_x(rtl, 66), y), hook(_x(rtl, 114), y)]
        key.append(answer_line((_x(rtl, 40), letter_y[owners[w]]), (_x(rtl, 66), y)))
    for i, w in enumerate(labels):
        y = (i + 0.5) * pitch
        x = _x(rtl, 136, W - 136)
        body.append(card(x, y - 13, W - 136, 26, r=6))
        p = picture_of(w)
        if rtl:
            body.append(word_markup(p.word_ar, x + (W - 136) / 2, y + 3.5, 9.5, ctx.style.color))
        else:
            body.append(word_markup(p.word_en, x + (W - 136) / 2, y + 3, 8, ctx.style.color, rtl=False))
        body.append(hook(_x(rtl, 132), y))
        key.append(answer_line((_x(rtl, 114), (pics.index(w) + 0.5) * pitch), (_x(rtl, 132), y)))
    answer = [
        f"{t}: "
        + "، ".join(
            (picture_of(w).word_ar if rtl else picture_of(w).word_en) for w in words if owners[w] == t
        )
        for t in letters
    ]
    return Built({"svg": svg(body + key)}, answer, problems)
