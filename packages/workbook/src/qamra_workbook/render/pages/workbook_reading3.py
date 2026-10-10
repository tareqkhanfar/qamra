"""«دوسية التأسيس» Volume 3 reading (Addendum 5 §3, decisions 3 and 6): the short vowels and sukun on letters
drawn in Qamra's hand, syllables (short, long with a madd letter, and built from a letter and a mark), then
words and very short sentences read with their pictures, and words written on dots and alone. No tanween, no
shadda; «ال» only with familiar words before moon letters."""

from __future__ import annotations

from qamra_workbook.geometry import Stroke
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures import PICTURES
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import Number, dotted_letter, letter_extent
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    arabic_shape,
    card,
    fit_lines,
    for_child,
    glyph,
    pic,
    svg,
    text,
)
from qamra_workbook.render.registry import Built, PageContext, page_type

HARAKA = {"فتحة": "َ", "ضمة": "ُ", "كسرة": "ِ", "سكون": "ْ"}
HARAKA_EN = {"fatha": "فتحة", "damma": "ضمة", "kasra": "كسرة", "sukun": "سكون"}
HARAKA_TITLE = {"فتحة": "الفَتْحَةُ", "ضمة": "الضَّمَّةُ", "كسرة": "الكَسْرَةُ", "سكون": "السُّكونُ"}
HARAKA_SAY = {  # draft: educator review
    "فتحة": "خَطٌّ صَغيرٌ فَوْقَ الحَرْفِ، نَفْتَحُ فَمَنا: بَ",
    "ضمة": "واوٌ صَغيرَةٌ فَوْقَ الحَرْفِ، نَضُمُّ شَفَتَيْنا: بُ",
    "كسرة": "خَطٌّ صَغيرٌ تَحْتَ الحَرْفِ، نَكْسِرُ صَوْتَنا: بِ",
    "سكون": "دائِرَةٌ صَغيرَةٌ فَوْقَ الحَرْفِ: لا حَرَكَةَ، الصَّوْتُ يَقِفُ",
}
# a long syllable keeps its short vowel (بَا بُو بِي), as the child learns the madd and as the words print it
MADD = {"ا": "َا", "و": "ُو", "ي": "ِي"}


def mark_path(haraka: str, x0: float, y0: float, x1: float, y1: float) -> str:
    """The mark's stroke in the letter's units, placed by its extent (kasra below, the others above)."""
    cx = (x0 + x1) / 2
    top, bottom = y0 - 14, y1 + 16
    if haraka == "فتحة":
        return f"M{cx + 14} {top - 12} L{cx - 14} {top - 2}"
    if haraka == "كسرة":
        return f"M{cx + 14} {bottom + 2} L{cx - 14} {bottom + 12}"
    if haraka == "ضمة":
        return (
            f"M{cx + 4} {top - 20} C{cx + 14} {top - 22} {cx + 14} {top - 8} {cx + 2} {top - 10} "
            f"L{cx - 12} {top - 2}"
        )
    k, r, cy = 3.9, 7.0, top - 14  # a ring: four béziers
    return (
        f"M{cx + r} {cy} C{cx + r} {cy + k} {cx + k} {cy + r} {cx} {cy + r} "
        f"C{cx - k} {cy + r} {cx - r} {cy + k} {cx - r} {cy} "
        f"C{cx - r} {cy - k} {cx - k} {cy - r} {cx} {cy - r} "
        f"C{cx + k} {cy - r} {cx + r} {cy - k} {cx + r} {cy}"
    )


# each mark as a thick stroke in a 100-unit box, against a faint letter line at y = 50: the fatha slants up to
# the right and the damma is a small و with its tail, both above the line; the kasra slants like the fatha
# below it; the sukun is a ring above it (a child sees the mark big and alone before meeting it on a letter)
MARK_SIGNS = {
    "فتحة": "M74 30 L26 46",
    "ضمة": "M56 14 C74 8 76 34 54 30 L28 46",
    "كسرة": "M74 56 L26 72",
    "سكون": "M62 30 C62 37 57 42 50 42 C43 42 38 37 38 30 C38 23 43 18 50 18 C57 18 62 23 62 30",
}


def mark_sign(haraka: str, x: float, y: float, size: float, color: str) -> str:
    """The mark alone, big, above or below a faint letter line, in a size × size box at (x, y)."""
    line = draw.path(
        draw.d_path(("M", (x + size * 0.08, y + size / 2)), ("L", (x + size * 0.92, y + size / 2))),
        stroke="#D8C9AC",
        width=size * 0.03,
        stroke_dasharray="2 1.6",
    )
    moved = Stroke(MARK_SIGNS[haraka]).scaled(size / 100, x, y)
    return line + draw.path(moved.d, stroke=color, width=size * 0.1)


def marked_letter(char: str, haraka: str, x: float, y: float, w: float, h: float, color: str) -> str:
    """The isolated letter with its mark in colour, fitted in the box."""
    shape = arabic_shape(char)
    x0, y0, x1, y1 = letter_extent(shape)
    scale, dx, dy = fit_lines(shape, x, y + h * 0.2, w, h * 0.65)
    out = glyph(shape, scale, dx, dy, color=INK, width=13)
    if not haraka:
        return out
    moved = Stroke(mark_path(haraka, x0, y0, x1, y1)).scaled(scale, dx, dy)
    return out + draw.path(moved.d, stroke=color, width=13 * scale * 0.9, fill="none")


def syllable(char: str, haraka: str) -> str:
    return char + HARAKA[haraka]


@page_type("harakat")
def harakat(ctx: PageContext) -> Built:
    params = ctx.page.params
    haraka = str(params.get("haraka", "فتحة"))
    haraka = HARAKA_EN.get(haraka, haraka)
    letters = [str(c) for c in params.get("letters", ["ب", "ت", "د"])]
    color = ctx.style.color
    body = [card(0, 0, W, 34, r=7, fill=ctx.style.tint, stroke="none")]
    body.append(marked_letter("ب", haraka, W - 40, 2, 34, 30, color))
    body.append(
        text(HARAKA_TITLE[haraka], W - 50, 14, 6.2, anchor="end", cls="wb-title", color=ctx.style.deep)
    )
    body.append(text(HARAKA_SAY[haraka], W - 50, 26, 4.4, anchor="end", color=INK))
    cols = 3
    rows = -(-len(letters) // cols)
    cw, ch = W / cols, min(58.0, (150 - 8) / rows)
    for k, char in enumerate(letters):
        row, col = divmod(k, cols)
        x, y = W - (col + 1) * cw + 3, 40 + row * (ch + 4)
        body.append(card(x, y, cw - 6, ch, r=6))
        body.append(marked_letter(char, haraka, x + 6, y + 2, cw - 18, ch - 18, color))
        body.append(text(syllable(char, haraka), x + (cw - 6) / 2, y + ch - 4, 8, cls="wb-word", color=INK))
    y = 40 + rows * (ch + 4) + 4
    if haraka == "سكون":
        words = [str(w) for w in params.get("words", ["أَبْ", "مِنْ", "قُمْ"])]
        body.append(card(0, y, W, 204 - y, r=7))
        body.append(text("أَقْرَأُ: الحَرْفُ السّاكِنُ يَقِفُ", W - 8, y + 10, 4.8, anchor="end", color=ctx.style.deep))
        for k, word in enumerate(words):
            body.append(text(word, W - 30 - k * 52, y + (204 - y) / 2 + 4, 14, cls="wb-word", color=INK))
    else:
        body.append(card(0, y, W, 204 - y, r=7))
        body.append(
            text("أَقْرَأُ الصَّفَّ مِنَ اليَمينِ إلى اليَسارِ", W - 8, y + 10, 4.8, anchor="end", color=ctx.style.deep)
        )
        line_y = y + (204 - y) / 2 + 4
        for k, char in enumerate(letters):
            body.append(
                text(
                    syllable(char, haraka),
                    W - 16 - k * (W - 20) / len(letters),
                    line_y,
                    13,
                    cls="wb-word",
                    color=INK if k % 2 == 0 else ctx.style.deep,
                )
            )
    answer = [for_child(ctx, "{يقرأ الطفل/تقرأ الطفلة}: ") + " ".join(syllable(c, haraka) for c in letters)]
    return Built({"svg": svg(body)}, answer, [] if haraka in HARAKA else [f"unknown mark {haraka}"])


@page_type("syllables")
def syllables(ctx: PageContext) -> Built:
    params = ctx.page.params
    mode = str(params.get("mode", "short"))
    letters = [str(c) for c in params.get("letters", ["ب", "ت"])]
    marks = [HARAKA_EN.get(str(h), str(h)) for h in params.get("harakat", ["فتحة", "ضمة", "كسرة"])]
    body, answer = [], []
    if mode == "build":
        for i, char in enumerate(letters):
            y = i * 51.0
            haraka = marks[i % len(marks)]
            body.append(card(0, y + 1, W, 47, r=7))
            body.append(card(W - 46, y + 6, 40, 37, r=5, fill="#FFF6F2", stroke="none"))
            body.append(marked_letter(char, "", W - 44, y + 8, 36, 33, INK))
            body.append(text("+", W - 54, y + 30, 8, cls="wb-num", color=INK, rtl=False))
            body.append(card(W - 96, y + 6, 36, 37, r=5, fill=ctx.style.tint, stroke="none"))
            body.append(mark_sign(haraka, W - 94, y + 8, 32, ctx.style.color))
            body.append(text("=", W - 106, y + 30, 8, cls="wb-num", color=INK, rtl=False))
            body.append(
                draw.el(
                    "rect",
                    x=W - 154,
                    y=y + 6,
                    width=40,
                    height=37,
                    rx=5,
                    fill="#FFFFFF",
                    stroke="#B8B2A6",
                    stroke_width=0.6,
                    stroke_dasharray="2 1.4",
                )
            )
            body.append(
                text(syllable(char, haraka), W - 134, y + 32, 14, cls="key-line wb-word", color="#E0483A")
            )
            answer.append(syllable(char, haraka))
        return Built({"svg": svg(body)}, ["المقاطع: " + " ".join(answer)], [])
    cols = [MADD[m] for m in marks] if mode == "long" else marks
    rows = len(letters)
    ch = min(29.0, 196 / rows)
    body.append(card(0, 0, W, rows * ch + 8, r=7))
    cw = (W - 30) / len(cols)
    for i, char in enumerate(letters):
        y = 4.0 + i * ch
        body.append(
            draw.path(draw.d_path(("M", (4, y + ch)), ("L", (W - 4, y + ch))), stroke="#EFE5D2", width=0.5)
        )
        body.append(text(char, W - 14, y + ch * 0.7, 9, cls="wb-word", color=ctx.style.deep))
        cells = []
        for k, col in enumerate(cols):
            syl = char + col if mode == "long" else syllable(char, col)
            cells.append(syl)
            body.append(
                text(
                    syl,
                    W - 30 - (k + 0.5) * cw,
                    y + ch * 0.72,
                    min(11.0, ch * 0.42),
                    cls="wb-word",
                    color=INK,
                )
            )
        answer.append(" ".join(cells))
    return Built(
        {"svg": svg(body)}, [for_child(ctx, "{يقرأ الطفل/تقرأ الطفلة} كل صف: ") + "؛ ".join(answer)], []
    )


# the reading words → their pictures (tashkeel and «ال» ignored); the rest resolve through the library
READ_PICTURES = {
    "كتب": "writing",
    "رسم": "drawing",
    "أكل": "eating",
    "لعب": "playing",
    "قلم": "pencil",
    "سمك": "fish",
    "ورد": "rose",
    "ليمون": "lemon",
    "موز": "banana",
}


def read_picture(word: str) -> str:
    bare = strip_tashkeel(word)
    bare = bare[2:] if bare.startswith("ال") else bare
    if bare in READ_PICTURES:
        return READ_PICTURES[bare]
    from qamra_workbook.render.pages.workbook_common import picture_id

    return picture_id(bare)


@page_type("word-read")
def word_read(ctx: PageContext) -> Built:
    """Each word (with its marks) beside three pictures: circle the word's picture."""
    words = [str(w) for w in ctx.page.params.get("words", [])]
    r = ctx.rng("read")
    en = ctx.page.lang == "en"
    pool = [
        p
        for p in (
            "apple",
            "duck",
            "cat",
            "car",
            "sun",
            "fish",
            "ball",
            "flower",
            "house",
            "star",
            "tree",
            "bee",
            "key",
            "hat",
            "bed",
            "pen",
            "bus",
        )
    ]
    pitch = 204 / len(words)
    body, answer, problems = [], [], []
    for i, word in enumerate(words):
        y = i * pitch
        try:
            right = read_picture(word) if not en else word
        except KeyError:
            problems.append(f"no picture for «{word}»")
            continue
        if right not in PICTURES:
            problems.append(f"no picture for «{word}»")
            continue
        choices = [right, *r.sample([p for p in pool if p != right], 2)]
        r.shuffle(choices)
        body.append(card(0, y + 1, W, pitch - 3, r=7))
        size = min(pitch - 9, 30.0)
        if en:
            body.append(text(word, 30, y + pitch / 2 + 3, 9, cls="wb-en", color=ctx.style.deep, rtl=False))
        else:
            body.append(text(word, W - 30, y + pitch / 2 + 2, 12, cls="wb-word", color=ctx.style.deep))
        for k, thing in enumerate(choices):
            cx = (W - 70 - (k + 0.5) * (W - 76) / 3) if not en else (66 + (k + 0.5) * (W - 72) / 3)
            body.append(pic(thing, cx - size / 2, y + pitch / 2 - size / 2, size))
            if thing == right:
                from qamra_workbook.render.pages.workbook_common import ring_at

                body.append(ring_at(cx, y + pitch / 2, size / 2 + 2, size / 2 + 2))
        answer.append(f"{word}: {PICTURES[right].word_en if en else PICTURES[right].word_ar}")
    return Built({"svg": svg(body)}, answer, problems)


def _word_layout(word: str, h: float) -> tuple[list[Letter], float, float, list[float], float]:
    """The word's letters in their written forms, the scale that fits the writing band `h`, their offsets and
    the total width (in the letters' units)."""
    from qamra_workbook.letters import placed
    from qamra_workbook.render.pages.workbook_front import spell

    letters = spell(strip_tashkeel(word))
    g = letters[0].guides
    low = g.low if g.low is not None else g.base
    scale = h / (low - g.top)
    xs, total = placed(letters, gap=12.0)
    return letters, g.top, scale, xs, total


def word_width(word: str, h: float) -> float:
    """The width (mm) of the word written in a writing band `h` mm tall."""
    _, _, scale, _, total = _word_layout(word, h)
    return total * scale


def dotted_word_letter(
    shape: Letter, *, scale: float, x: float, y: float, first: bool, number: Number
) -> str:
    """A letter of a word in fine tracing dots (the small teeth of سـ and the loops of مـ need a closer dot
    spacing than a single big letter does), drawn like a writing row's letters (`letters.dotted_letter`):
    its own dots are round dots to fill in, a small mark has its ghost and its start dot beside it. Every
    stroke starts at a green dot, and the first letter of the word carries the numbers and arrows."""
    return dotted_letter(
        shape,
        scale=scale,
        x=x,
        y=y,
        first=first,
        number=number,
        spacing=2.5,
        dot=0.68,
        mark=0.6,
        number_dots=False,
    )


def word_row(word: str, right: float, y: float, h: float, ctx: PageContext, *, dotted: bool) -> str:
    """The word in Qamra's hand on writing lines: dotted to trace, or as a small solid model."""
    letters, top, scale, xs, total = _word_layout(word, h)
    out = []
    for i, (shape, x) in enumerate(zip(letters, xs, strict=True)):
        dx, dy = right - total * scale + x * scale, y - top * scale
        if dotted:
            out.append(dotted_word_letter(shape, scale=scale, x=dx, y=dy, first=i == 0, number=ctx.num))
        else:
            out.append(glyph(shape, scale, dx, dy, color=INK, width=12))
    return "".join(out)


@page_type("word-write")
def word_write(ctx: PageContext) -> Built:
    """Each word beside its picture on two pairs of writing lines: dotted (or modelled) on the first, then
    room to write it alone on the second, with a green dot where the word starts."""
    words = [str(w) for w in ctx.page.params.get("words", [])]
    dotted = str(ctx.page.params.get("mode", "dotted")) == "dotted"
    pitch = 204 / len(words)
    body, problems = [], []
    for i, word in enumerate(words):
        y = i * pitch
        try:
            thing = read_picture(word)
        except KeyError:
            problems.append(f"no picture for «{word}»")
            continue
        body.append(card(0, y + 1, W, pitch - 3, r=7))
        size = min(30.0, pitch - 26)
        body.append(pic(thing, W - size - 6, y + 5, size))
        body.append(text(word, W - size / 2 - 6, y + pitch - 8, 7, cls="wb-word", color=ctx.style.deep))
        band = min(27.0, (pitch - 3 - 10) / 2)
        right = W - size - 18
        for k in range(2):
            top = y + 4 + k * (band + 4)
            for color, yy in (("#9BB7E0", top), ("#E27D63", top + band * 122 / 183)):
                body.append(
                    draw.el(
                        "path",
                        d=draw.d_path(("M", (6, yy)), ("L", (right + 6, yy))),
                        stroke=color,
                        stroke_width=0.5,
                    )
                )
            if k == 0:
                body.append(
                    word_row(word, right, top, band, ctx, dotted=True)
                    if dotted
                    else word_row(word, right, top + band * 0.1, band * 0.8, ctx, dotted=False)
                )
            else:
                body.append(draw.start_dot((right - 2, top + band * 0.2), 1.8))
    return Built({"svg": svg(body)}, None, problems)


# a sentence → the picture it tells (draft: educator review)
SENTENCE_PICTURES = {
    "كتب": "writing",
    "رسم": "drawing",
    "لعب": "playing",
    "أكل": "eating",
    "أقرأ": "book",
    "أكتب": "pencil",
    "أرسم": "crayon",
    "cat": "cat",
    "ball": "ball",
    "apple": "apple",
    "dog": "dog",
    "sun": "sun",
}


# an action's picture is named by its verb («رَسَمَ»); the key names it by the action, so «رَسَمَتْ سَلْمى» never
# points to a masculine verb
ACTION_PICTURES = {
    "writing": "صورة الكتابة",
    "drawing": "صورة الرسم",
    "drawing-girl": "صورة الرسم",
    "playing": "صورة اللعب",
    "eating": "صورة الأكل",
}


GIRL_PICTURES = {"drawing": "drawing-girl"}  # a feminine verb («رَسَمَتْ سَلْمَى») shows a girl


def sentence_picture(sentence: str) -> str | None:
    words = strip_tashkeel(sentence).replace(".", "").split()
    for w in words:
        key = w[:-1] if w.endswith("ت") and w[:-1] in SENTENCE_PICTURES else w
        for cand in (key, w, w.rstrip("s")):
            if cand in SENTENCE_PICTURES:
                found = SENTENCE_PICTURES[cand]
                return GIRL_PICTURES.get(found, found) if key != w else found
    return None


@page_type("sentence-read")
def sentence_read(ctx: PageContext) -> Built:
    """Sentences on the reading side, their pictures shuffled on the other side: connect each to its picture.
    With `personal`, the child's own character stands beside the thing the sentence says («أنا أقرأ»)."""
    params = ctx.page.params
    sentences = [str(s) for s in params.get("sentences", [])]
    personal = bool(params.get("personal"))
    en = ctx.page.lang == "en"
    r = ctx.rng("sentences")
    body, key, problems = [], [], []
    pictures = []
    for s in sentences:
        found = sentence_picture(s)
        if found is None:
            problems.append(f"no picture tells «{s}»")
        pictures.append(found or "star")
    order = list(range(len(sentences)))
    while len(order) > 1 and order == list(range(len(sentences))):
        r.shuffle(order)
    pitch = 204 / max(len(sentences), 1)
    character = ctx.assets.character.resolve().as_uri() if (personal and ctx.assets.character) else ""
    size = min(pitch - 8, 36.0)
    card_w = size + 8 + (14 if character else 0)  # the picture's card
    sentence_w = 88.0 if en else 80.0
    # the sentences stand on the reading side (right for Arabic, left for English), the pictures opposite;
    # the two rows of hooks keep a wide gap so the child's lines are long and easy to follow
    s_left = 2.0 if en else W - 2 - sentence_w
    p_left = W - 2 - card_w if en else 2.0
    s_hook = s_left + sentence_w + 6 if en else s_left - 6
    p_hook = p_left - 6 if en else p_left + card_w + 6
    for i, s in enumerate(sentences):
        y = i * pitch + pitch / 2
        body.append(card(s_left, y - 16, sentence_w, 32, r=6))
        body.append(
            text(
                s,
                s_left + sentence_w / 2,
                y + 4,
                10 if not en else 8,
                cls="wb-word" if not en else "wb-en",
                color=ctx.style.deep,
                rtl=not en,
            )
        )
        body.append(draw.el("circle", cx=s_hook, cy=y, r=1.8, fill="#FFFFFF", stroke=INK, stroke_width=0.7))
    for j, i in enumerate(order):
        y = j * pitch + pitch / 2
        body.append(card(p_left, y - size / 2 - 3, card_w, size + 6, r=6))
        if character:
            body.append(
                draw.el(
                    "image",
                    href=character,
                    x=p_left + 4,
                    y=y - size / 2,
                    width=size * 0.5,
                    height=size,
                    preserveAspectRatio="xMidYMax meet",
                )
            )
            body.append(pic(pictures[i], p_left + 4 + size * 0.55, y - size / 2 + 4, size * 0.75))
        else:
            body.append(pic(pictures[i], p_left + 4, y - size / 2, size))
        body.append(draw.el("circle", cx=p_hook, cy=y, r=1.8, fill="#FFFFFF", stroke=INK, stroke_width=0.7))
        key.append(
            draw.path(
                draw.polyline([(s_hook, i * pitch + pitch / 2), (p_hook, y)]),
                stroke="#E0483A",
                width=1.1,
                class_="key-line",
            )
        )
    answer = [
        f"{s} ← {PICTURES[p].word_en if en else ACTION_PICTURES.get(p, PICTURES[p].word_ar)}"
        for s, p in zip(sentences, pictures, strict=True)
    ]
    return Built({"svg": svg(body + key)}, answer, problems)


def _syllables_of(word: str) -> list[str]:
    """A three-letter open word into its syllables: each letter with its mark (قَ مَ ر)."""
    out, cur = [], ""
    for ch in word:
        if "ً" <= ch <= "ْ":
            cur += ch
        else:
            if cur:
                out.append(cur)
            cur = ch
    if cur:
        out.append(cur)
    return out


@page_type("build-words")
def build_words(ctx: PageContext) -> Built:
    """Each picture with empty slots for its syllables; the syllable cards below, shuffled, to cut out."""
    words = [str(w) for w in ctx.page.params.get("words", ["قَمَر", "سَمَك", "جَمَل"])]
    r = ctx.rng("build")
    body, answer, problems = [], [], []
    cards: list[str] = []
    pitch = 120 / len(words)
    for i, word in enumerate(words):
        y = i * pitch
        try:
            thing = read_picture(word)
        except KeyError:
            problems.append(f"no picture for «{word}»")
            continue
        parts = _syllables_of(word)
        cards += parts
        body.append(card(0, y + 1, W, pitch - 3, r=7))
        body.append(pic(thing, W - 36, y + 3, pitch - 8))
        for k, part in enumerate(parts):
            x = W - 50 - (k + 1) * 30
            body.append(
                draw.el(
                    "rect",
                    x=x,
                    y=y + 6,
                    width=26,
                    height=pitch - 12,
                    rx=4,
                    fill="#FFFFFF",
                    stroke="#B8B2A6",
                    stroke_width=0.6,
                    stroke_dasharray="2 1.4",
                )
            )
            body.append(text(part, x + 13, y + pitch / 2 + 4, 11, cls="key-line wb-word", color="#E0483A"))
        answer.append(f"{word}: " + " + ".join(parts))
    r.shuffle(cards)
    body.append(text("أَقُصُّ البِطاقاتِ عَلى الخَطِّ المُتَقَطِّعِ", W - 8, 132, 4.8, anchor="end", color=ctx.style.deep))
    for k, part in enumerate(cards):
        row, col = divmod(k, 5)
        x, y = W - 4 - (col + 1) * 36, 138 + row * 34
        body.append(
            draw.el(
                "rect",
                x=x,
                y=y,
                width=32,
                height=30,
                rx=0,
                fill="#FFFFFF",
                stroke=INK,
                stroke_width=0.6,
                stroke_dasharray="2.4 1.6",
            )
        )
        body.append(text(part, x + 16, y + 20, 11, cls="wb-word", color=INK))
    return Built({"svg": svg(body)}, answer, problems)
