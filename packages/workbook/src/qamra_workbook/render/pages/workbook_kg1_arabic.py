"""«دوسية التأسيس» KG1 Arabic (decisions 2–4 of 28 September 2026): bigger tracing (a big track, then two
rows), writing alone only for the simple shapes (one short row after guided rows), the three short vowels as
listening pages, and the two word pages: hear a word and find its picture or its first letter, and trace two
dotted words. Every letter and word is drawn from Qamra's hand."""

from __future__ import annotations

from qamra_workbook.curriculum import REPLACED_WORDS
from qamra_workbook.letters import placed
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures import PICTURES
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.foundation_kg1 import HARAKA_AR, LETTER_PICTURES_KG1, LOOKALIKE_KG1
from qamra_workbook.render.foundation_text import letter_name
from qamra_workbook.render.pages.letters import dotted_letter, letter_extent, tracing_row
from qamra_workbook.render.pages.workbook_arabic import (
    big_track,
    first_letter,
    row_svg,
    same_letter,
    word_markup,
)
from qamra_workbook.render.pages.workbook_arabic2 import alone_row
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    answer_line,
    card,
    fit,
    fit_lines,
    glyph,
    hook,
    pic,
    picture_id,
    picture_of,
    ring_at,
    shape_of,
    start_marks,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_find import (
    CRAYONS,
    _deranged,
    _grid_problems,
    _x,
    letter_grid,
    words_starting,
)
from qamra_workbook.render.pages.workbook_position import word_shapes, written_word
from qamra_workbook.render.registry import Built, PageContext, page_type

CAPS = {"xl": 28.0, "l": 24.0, "m": 18.0, "s": 14.0}
# a picture a child could name by something else (ten stars, a color, a shape, a verb) never stands
# for a letter
NOT_A_FIRST_SOUND = frozenset({"number", "color", "shape", "action"})
HARAKAT = ("fatha", "damma", "kasra")


def row_height(shape: Letter, cap: float) -> float:
    return float(
        str(tracing_row(shape, width=W - 10, cap=cap, count=0, number=str))
        .split('viewBox="0 0 ')[1]
        .split('"')[0]
        .split()[1]
    )


MIN_BODY_MM = 11.0  # the body of a traced letter is never smaller than this (د ه are short letters)
CAP_LIMITS = (30.0, 28.0, 26.0, 24.0, 22.0, 20.0, 18.0, 16.0, 14.0)


def body_ratio(shape: Letter) -> float:
    """The letter's height as a share of its writing band (د and ه are about 0.4, ل 1.4)."""
    _, y0, _, y1 = letter_extent(shape)
    return max((y1 - y0) / (shape.guides.base - shape.guides.top), 0.2)


@page_type("kg1-letter-trace")
def kg1_letter_trace(ctx: PageContext) -> Built:
    """The big letter to trace with a finger and a pen, then two writing rows (the plan's smaller sizes; one
    size is traced twice), all dotted: KG1 traces, it does not write alone here. A short letter gets a shorter
    big card and taller rows, so its dotted body stays big enough to follow."""
    params = ctx.page.params
    char = str(params.get("letter", "ب"))
    sizes = [str(s) for s in params.get("sizes", ["xl", "l"])]
    shape = shape_of(char)
    ratio = body_ratio(shape)
    big = 96.0 if ratio >= 0.6 else 72.0
    body = [card(0, 0, W, big, r=7)]
    body.append(big_track(shape, 20, 2, 146, big - 4, ctx.num, ctx.style.color, most=0.85))
    body.append(card(5, 5, 30, 10, r=5, fill=ctx.style.tint, stroke="none"))
    body.append(text("كبير", 20, 12, 5, color=ctx.style.deep))
    rows = [s for s in sizes[1:] if s in CAPS] or ["l"]
    if len(rows) == 1:
        rows = rows * 2
    y = big + 6.0
    biggest = fitting_cap(shape, len(rows), 204 - y, CAP_LIMITS, 7.0)
    for size in rows:
        # a letter with a mark above (أ) takes taller rows: smaller caps; a short one is never traced tiny
        cap = min(max(CAPS[size], MIN_BODY_MM / ratio), biggest)
        row, height = row_svg(tracing_row(shape, width=W - 10, cap=cap, number=ctx.num), 5, y + 1)
        body.append(card(0, y - 2, W, height + 5, r=6))
        body.append(row)
        y += height + 7
    problems = [] if y <= 206 else [f"the tracing rows need {y:.0f} mm (max 204)"]
    return Built({"svg": svg(body)}, None, problems)


def fitting_cap(shape: Letter, rows: int, room: float, caps: tuple[float, ...], gap: float = 4.0) -> float:
    """The biggest cap height at which `rows` writing rows (`gap` mm apart) fit in `room` mm."""
    for cap in caps:
        if rows * (row_height(shape, cap) + gap) <= room:
            return cap
    return caps[-1]


def model_header(ctx: PageContext, chars: list[str], y: float, h: float, note: str) -> list[str]:
    out = [card(0, y, W, h, r=7)]
    for k, char in enumerate(chars):
        shape = shape_of(char)
        scale, dx, dy = fit_lines(shape, W - 40 - k * 42, y + 3, 34, h - 6)
        out.append(glyph(shape, scale, dx, dy, color=ctx.style.color, width=15))
        out.append(start_marks(shape, scale, dx, dy, 2.2, ctx.num))
    out.append(text("أبدأ من النقطة الخضراء وأتبع السهم", 58, y + h / 2 - 3, 5.0, color=INK))
    out.append(text(note, 58, y + h / 2 + 6, 4.6, color="#676B83"))
    return out


def writing_rows(
    ctx: PageContext,
    char: str,
    guided: int,
    alone: int,
    cap: float,
    y: float,
    gap: float = 4.0,
    label: str = "",
) -> tuple[list[str], float]:
    """Guided rows (all dotted, then two dotted and room to go on) and rows to write alone; `label` names
    the letter in a chip at the first row's right end."""
    out = []
    shape = shape_of(char)
    for k in range(guided + alone):
        if k < guided:
            row = tracing_row(shape, width=W - 10, cap=cap, count=None if k == 0 else 2, number=ctx.num)
            part, height = row_svg(row, 5, y + 2)
        else:
            part, height = alone_row(ctx, char, cap, y + 2)
        out.append(card(0, y, W, height + 3, r=6, fill="#FFFFFF" if k < guided else "#FFFDF6"))
        out.append(part)
        if k == 0 and label:
            out.append(card(W - 28, y + 1, 26, 5.6, r=2.8, fill=ctx.style.tint, stroke="none"))
            out.append(text(label, W - 15, y + 5.2, 3.6, color=ctx.style.deep))
        y += height + gap
    return out, y


@page_type("kg1-letter-write")
def kg1_letter_write(ctx: PageContext) -> Built:
    params = ctx.page.params
    char = str(params.get("letter", "ب"))
    guided, alone = int(params.get("guided", 3)), int(params.get("independent", 1))
    cap = fitting_cap(shape_of(char), guided + alone, 204 - 32, (24.0, 22.0, 20.0, 18.0, 16.0, 14.0, 12.0))
    body = model_header(ctx, [char], 0, 28, "ثم أكتب على النقاط، ثم وحدي")
    rows, y = writing_rows(ctx, char, guided, alone, cap, 32)
    problems = [] if y <= 208 else [f"the writing rows need {y:.0f} mm (max 204)"]
    if guided < 1 or alone < 1:
        problems.append("letter-write has guided rows, then a row to write alone")
    return Built({"svg": svg(body + rows)}, None, problems)


@page_type("kg1-letters-write")
def kg1_letters_write(ctx: PageContext) -> Built:
    """Two letters of one shape family (ت ث، د ذ، ر ز) share the page: guided rows, then a row alone each."""
    params = ctx.page.params
    chars = [str(c) for c in params.get("letters", ["ت", "ث"])]
    guided, alone = int(params.get("guided", 2)), int(params.get("independent", 1))
    per = guided + alone
    cap = fitting_cap(shape_of(chars[0]), per * len(chars), 204 - 26, (16.0, 14.0, 12.0, 11.0, 10.0), 3.0)
    body = model_header(ctx, chars, 0, 22, "الحرفان يختلفان بالنقاط فقط")
    y = 26.0
    for char in chars:
        rows, y = writing_rows(ctx, char, guided, alone, cap, y, 3.0, f"حرف {letter_name(char)}")
        body += rows
    problems = [] if y <= 208 else [f"the writing rows need {y:.0f} mm (max 204)"]
    return Built({"svg": svg(body)}, None, problems)


def mark(kind: str, cx: float, top: float, bottom: float, size: float, color: str) -> str:
    """A short vowel over or under a letter whose drawing runs from `top` to `bottom` (mm) in a card of `size`
    mm: fatha (a slant above), damma (a small waw above), kasra (a slant below, under any dot)."""
    u = size * 0.085  # half the length of the slant
    if kind == "kasra":
        y = bottom + size * 0.1
        return draw.path(
            draw.polyline([(cx + u, y - u * 0.35), (cx - u, y + u * 0.6)]), stroke=color, width=1.9
        )
    if kind == "damma":
        y, s = top - size * 0.17, size * 0.36
        return draw.path(
            f"M{draw.n(cx + s * 0.18)} {draw.n(y)} a{draw.n(s * 0.14)} {draw.n(s * 0.14)} 0 1 1 "
            f"{draw.n(s * 0.02)} {draw.n(s * 0.22)} L{draw.n(cx - s * 0.2)} {draw.n(y + s * 0.38)}",
            stroke=color,
            width=1.7,
        )
    y = top - size * 0.1
    return draw.path(draw.polyline([(cx + u, y - u * 0.5), (cx - u, y + u * 0.4)]), stroke=color, width=1.9)


def syllable(ctx: PageContext, char: str, kind: str, x: float, y: float, size: float, color: str) -> str:
    """The letter in the middle of a `size` mm card with a vowel over or under it, the vowel in `color`."""
    shape = shape_of(char)
    box_w, box_h = size * 0.64, size * 0.36
    scale, dx, dy = fit(shape, x + (size - box_w) / 2, y + size * 0.36, box_w, box_h)
    x0, y0, x1, y1 = letter_extent(shape)
    cx = dx + (x0 + x1) / 2 * scale
    return glyph(shape, scale, dx, dy, color=INK, width=14) + mark(
        kind, cx, dy + y0 * scale, dy + y1 * scale, size, color
    )


@page_type("kg1-harakat")
def kg1_harakat(ctx: PageContext) -> Built:
    """Listening only (decision 3): the vowel's mark and name, its sound on three known letters, then a row
    per letter with the three vowels: the grown-up says one syllable and the child circles it."""
    params = ctx.page.params
    targets = [str(h) for h in params.get("harakat", [params.get("haraka", "fatha")])]
    chars = [str(c) for c in params.get("letters", ["ب", "د", "ر"])]
    color = ctx.style.color
    body = [card(0, 0, W, 48, r=7, fill=ctx.style.tint, stroke="none")]
    names = " و".join(HARAKA_AR[t] for t in targets)
    body.append(text(names, W - 8, 11, 6.2, cls="wb-title", anchor="end", color=ctx.style.deep))
    body.append(text("أسمع وأقول", 8, 11, 4.8, anchor="start", color=ctx.style.deep))
    big = 32.0
    left = (W - len(chars) * big - (len(chars) - 1) * 8) / 2
    for k, char in enumerate(chars):  # the first letter at the right, as the book is read
        x = W - left - (k + 1) * big - k * 8
        body.append(card(x, 14, big, big - 2, r=5))
        body.append(syllable(ctx, char, targets[k % len(targets)], x, 13, big, color))
    pitch = (204 - 54) / len(chars)
    answer = []
    for i, char in enumerate(chars):
        y = 54 + i * pitch
        target = targets[i % len(targets)]
        body.append(card(0, y, W, pitch - 5, r=7))
        body.append(text(f"حرف {letter_name(char)}", W - 8, y + 9, 4.8, anchor="end", color=ctx.style.deep))
        size = min(pitch - 17, 36.0)
        for k, kind in enumerate(HARAKAT):
            x = W - 30 - (k + 1) * (size + 12)
            top = y + 11
            body.append(card(x, top, size, size, r=6, fill="#FFFDF6"))
            body.append(syllable(ctx, char, kind, x, top, size, color))
            if kind == target:
                body.append(ring_at(x + size / 2, top + size / 2, size / 2 + 2, size / 2 + 2))
        answer.append(f"{letter_name(char)} مع {HARAKA_AR[target]}")
    problems = [] if params.get("mode", "listen") == "listen" else ["KG1 meets the vowels by listening only"]
    return Built({"svg": svg(body)}, answer, problems)


def dotted_word(
    ctx: PageContext, word: str, right: float, y: float, h: float
) -> tuple[str, float, tuple[float, float]]:
    """The word in tracing dots, from its highest mark to its lowest tail `h` mm tall, its right edge at
    `right` and its top at `y`: the SVG, its width and the y of its top and base lines."""
    letters = word_shapes(word)
    g = letters[0].guides
    top = min(letter_extent(s)[1] for s in letters)
    scale = h / (max(letter_extent(s)[3] for s in letters) - top)
    xs, total = placed(letters, gap=12.0)
    out = []
    for i, (shape, x) in enumerate(zip(letters, xs, strict=True)):
        dx, dy = right - total * scale + x * scale, y - top * scale
        out.append(dotted_letter(shape, scale=scale, x=dx, y=dy, first=i == 0, number=ctx.num))
    return "".join(out), total * scale, (max(y, y + (g.top - top) * scale), y + (g.base - top) * scale)


@page_type("kg1-word-write")
def kg1_word_write(ctx: PageContext) -> Built:
    """Two picture words traced on dots: the picture, the written model, then one big row of the dotted word
    (twice when it fits)."""
    words = [str(w) for w in ctx.page.params.get("words", ["أسد", "قمر"])][:2]
    pitch = 204 / len(words)
    body, problems = [], []
    if ctx.page.params.get("mode", "dotted") != "dotted":
        problems.append("KG1 traces words on dots only (decision 2)")
    for i, word in enumerate(words):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 5, r=7))
        body.append(card(W - 38, y + 5, 34, 34, r=6, fill="#FFF6F2", stroke="none"))
        body.append(pic(picture_id(word), W - 37, y + 6, 32))
        model, _ = written_word(word_shapes(word), W - 48, y + 9, 22, color={0: ctx.style.color})
        body.append(model)
        body.append(text(picture_of(word).word_ar, W - 88, y + 38, 5.6, cls="wb-word", color=INK))
        top = y + 44
        band = min(46.0, pitch - 5 - 44 - 6)  # the whole word, its highest mark to its lowest tail
        part, width, (top_y, base_y) = dotted_word(ctx, word, W - 10, top, band)
        for gy, color in ((top_y, "#9BB7E0"), (base_y, "#E27D63")):
            body.append(draw.path(draw.d_path(("M", (6, gy)), ("L", (W - 6, gy))), stroke=color, width=0.5))
        body.append(part)
        if width + 16 < (W - 20) / 2:
            body.append(dotted_word(ctx, word, W - 10 - width - 16, top, band)[0])
    return Built({"svg": svg(body)}, None, problems)


WORD_ROOM = 46.0  # the width a model word may take on its row, at the right


def model_word(letters: list[Letter], cy: float, h: float, color: dict[int, str]) -> tuple[str, float]:
    """The word written at the right end of a row, centred on `cy`, no wider than WORD_ROOM: the SVG and its
    width."""
    g = letters[0].guides
    low = g.low if g.low is not None else g.base
    _, total = placed(letters, gap=12.0)
    h = min(h, WORD_ROOM / total * (low - g.top))
    return written_word(letters, W - 8, cy - h / 2, h, color=color)[0], total * h / (low - g.top)


@page_type("kg1-word-read")
def kg1_word_read(ctx: PageContext) -> Built:
    """Recognition, not reading (decision 2): the grown-up says a word; the child finds its picture among
    three (`listen`) or circles its first letter among three (`first-letter`; the review does both)."""
    params = ctx.page.params
    words = [str(w) for w in params.get("words", ["أسد", "قمر", "موز"])]
    mode = str(
        params.get(
            "mode",
            "review"
            if ctx.page.type == "kg1-word-read" and "words" in params and len(words) > 3
            else "listen",
        )
    )
    r = ctx.rng("words")
    rows = words[:4] if mode == "review" else words[:3]
    pitch = 204 / len(rows)
    body, answer = [], []
    for i, word in enumerate(rows):
        y = i * pitch
        cy = y + (pitch - 5) / 2 + 1
        by_letter = mode == "first-letter" or (mode == "review" and i % 2 == 1)
        body.append(card(0, y + 1, W, pitch - 5, r=7))
        letters = word_shapes(word)
        body.append(model_word(letters, cy, 22, {0: ctx.style.color if by_letter else INK})[0])
        if by_letter:
            size = min(pitch - 16, 40.0)
            body.append(pic(picture_id(word), W - WORD_ROOM - 12 - size, cy - size / 2, size))
            first = letters[0].char if letters[0].char != "ا" else "أ"
            options = [first, *r.sample([c for c in LOOKALIKE_KG1.get(first, "بت") if c != first], 2)]
            r.shuffle(options)
            for k, char in enumerate(options):
                cx = 19.0 + k * 27.0
                body.append(
                    draw.el("circle", cx=cx, cy=cy, r=11, fill="#FFFDF6", stroke="#D8C9AC", stroke_width=0.6)
                )
                shape = shape_of(char)
                body.append(glyph(shape, *fit_lines(shape, cx - 7.5, cy - 8, 15, 16), color=INK, width=14))
                if char == first:
                    body.append(ring_at(cx, cy, 12, 12))
            answer.append(f"{word}: الحرف الأول {first}")
        else:
            size = min(pitch - 16, 32.0)
            others = r.sample([w for w in words if w != word] or ["كرة", "بيت"], 2)
            options = [word, *others]
            r.shuffle(options)
            for k, w in enumerate(options):
                cx = 8 + (size + 4) / 2 + k * (size + 8)
                body.append(
                    card(cx - size / 2 - 2, cy - size / 2 - 2, size + 4, size + 4, r=5, fill="#FFFDF6")
                )
                body.append(pic(picture_id(w), cx - size / 2, cy - size / 2, size))
                if w == word:
                    body.append(ring_at(cx, cy, size / 2 + 3, size / 2 + 3))
            answer.append(f"{word}: صورة {picture_of(word).word_ar}")
    return Built({"svg": svg(body)}, answer, [])


@page_type("kg1-match-letter-picture")
def kg1_match_letter_picture(ctx: PageContext) -> Built:
    """Three letters and six words (ج ح خ، ه و ي): the KG2 page with picture cards that fit their rows."""
    params = ctx.page.params
    letters = [str(x) for x in params.get("letters", [])]
    words = [str(w) for w in params.get("words", [])]
    r = ctx.rng("match")
    owners = {w: next((t for t in letters if same_letter(first_letter(w), t)), "") for w in words}
    problems = [f"«{w}» starts with none of {letters}" for w, t in owners.items() if not t]
    problems += [f"{t} has no picture" for t in letters if t not in owners.values()]
    pics = _deranged(r, words, words)
    labels = _deranged(r, words, pics)
    pitch = 200 / max(len(words), 1)
    box = min(42.0, pitch - 3)
    body, key = [], []
    letter_y = {t: (i + 0.5) * 200 / len(letters) for i, t in enumerate(letters)}
    for t in letters:
        x, y = _x(True, 0, 36), letter_y[t]
        body.append(card(x, y - 20, 36, 40, r=7, fill=ctx.style.tint, stroke="none"))
        shape = shape_of(t)
        body.append(glyph(shape, *fit_lines(shape, x + 5, y - 16, 26, 32), color=ctx.style.deep, width=14))
        body.append(hook(_x(True, 40), y))
    for i, w in enumerate(pics):
        y = (i + 0.5) * pitch
        x = _x(True, 70, 40)
        body.append(card(x, y - box / 2, 40, box, r=7))
        body.append(pic(picture_id(w), x + (40 - box + 6) / 2, y - box / 2 + 3, box - 6))
        body += [hook(_x(True, 66), y), hook(_x(True, 114), y)]
        key.append(answer_line((_x(True, 40), letter_y[owners[w]]), (_x(True, 66), y)))
    for i, w in enumerate(labels):
        y = (i + 0.5) * pitch
        x = _x(True, 136, W - 136)
        body.append(card(x, y - 13, W - 136, 26, r=6))
        body.append(word_markup(picture_of(w).word_ar, x + (W - 136) / 2, y + 3.5, 9.5, ctx.style.color))
        body.append(hook(_x(True, 132), y))
        key.append(answer_line((_x(True, 114), (pics.index(w) + 0.5) * pitch), (_x(True, 132), y)))
    answer = [f"{t}: " + "، ".join(picture_of(w).word_ar for w in words if owners[w] == t) for t in letters]
    return Built({"svg": svg(body + key)}, answer, problems)


def first_sound_pictures(letter: str, avoid: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """Pictures whose name starts with `letter`: the words the plan taught for it first (a child is asked only
    about words met before), then the library's, as a four-year-old names them; never a word decision 7
    replaced (ظبي، لقلق، ذئب) or a plain «طائرة» (it is a kite: «طائرة ورقية»)."""
    taught = [p for p in LETTER_PICTURES_KG1.get(letter, ()) if p not in avoid]
    if taught:
        return taught
    return [
        p
        for p in words_starting(letter, avoid)
        if PICTURES[p].category not in NOT_A_FIRST_SOUND
        and strip_tashkeel(PICTURES[p].word_ar) not in REPLACED_WORDS
    ]


@page_type("kg1-find-letter")
def kg1_find_letter(ctx: PageContext) -> Built:
    """Find the letters among look-alikes: the legend (a color for each letter), big bubbles to color, and one
    full-width row per letter: a picture and three letters, circle the one it starts with."""
    params = ctx.page.params
    targets = [str(x) for x in params.get("letters", [params.get("letter", "ب")])]
    others = [str(x) for x in params.get("distractors", [])]
    r = ctx.rng("grid")
    cols, rows = (5, 3) if len(targets) >= 3 else (4, 3)
    grid = letter_grid(r, targets, others, cols * rows)
    body, marks = [], []
    legend_w = W / len(targets)
    for i, t in enumerate(targets):
        color, name = CRAYONS[i]
        x = W - (i + 1) * legend_w
        body.append(card(x + 2, 0, legend_w - 4, 15, r=7.5))
        body.append(draw.el("circle", cx=x + legend_w - 11, cy=7.5, r=4.6, fill=color))
        shape = shape_of(t)
        body.append(glyph(shape, *fit_lines(shape, x + legend_w - 32, 1.5, 14, 12), color=INK, width=14))
        body.append(text(f"ألوّنه ب{name}", x + legend_w - 36, 10.2, 4.4, anchor="end", color=color))
    cw, pitch, top = W / cols, 29.0, 19.0
    radius = min(14.0, cw / 2 - 2)
    for k, cell in enumerate(grid):
        cx, cy = W - (k % cols + 0.5) * cw, top + (k // cols + 0.5) * pitch
        body.append(
            draw.el("circle", cx=cx, cy=cy, r=radius, fill="#FFFFFF", stroke="#D8C9AC", stroke_width=0.6)
        )
        if cell.target is not None:
            marks.append(ring_at(cx, cy, radius + 0.5, radius + 0.5, CRAYONS[cell.target][0], 1.6))
        shape = shape_of(cell.char)
        side = radius * 1.7
        body.append(
            glyph(shape, *fit_lines(shape, cx - side / 2, cy - side / 2, side, side), color=INK, width=15)
        )
    y = top + rows * pitch + 4
    body.append(text("أحوّط الحرف الذي تبدأ به الصورة", W - 4, y + 4, 5, anchor="end", color=ctx.style.deep))
    answer = [f"{t}: {ctx.num(sum(1 for c in grid if c.target == i))} مرات" for i, t in enumerate(targets)]
    problems = _grid_problems(grid, targets)
    used: set[str] = set()
    n = len(targets)
    card_h = (204 - y - 10 - 3 * (n - 1)) / n
    for i, t in enumerate(targets):
        pool = first_sound_pictures(t, used)
        if not pool:
            problems.append(f"no picture starts with {t}")
            continue
        word = r.choice(pool)
        used.add(word)
        options = [t, *r.sample([c for c in [*targets, *others] if c != t], 2)]
        r.shuffle(options)
        top_y = y + 8 + i * (card_h + 3)
        size = min(card_h - 6, 30.0)
        box = min(card_h - 8, 24.0)
        body.append(card(0, top_y, W, card_h, r=6))
        body.append(pic(word, W - size - 6, top_y + (card_h - size) / 2, size))
        for j, c in enumerate(options):
            bx = W - size - 22 - j * (box + 8)
            by = top_y + (card_h - box) / 2
            body.append(
                draw.el(
                    "rect",
                    x=bx - box,
                    y=by,
                    width=box,
                    height=box,
                    rx=4,
                    fill="#FFFFFF",
                    stroke="#D8C9AC",
                    stroke_width=0.5,
                )
            )
            shape = shape_of(c)
            body.append(
                glyph(shape, *fit_lines(shape, bx - box + 2, by + 2, box - 4, box - 4), color=INK, width=15)
            )
            if c == t:
                marks.append(ring_at(bx - box / 2, by + box / 2, box / 2 + 2, box / 2 + 2))
        answer.append(f"{PICTURES[word].word_ar}: {t}")
    return Built({"svg": svg(body + marks)}, answer, problems)
