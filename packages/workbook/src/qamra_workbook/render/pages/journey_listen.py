"""Journey listening pages (Addendum 6 §4.8) and the first English words (§4.11 in stage 1). Each page prints
a QR to its audio item (`BookSpec.audio_url`); the rows are numbered with dots in the order the audio plays,
and every page still works without audio: the parent reads the words or makes the sounds."""

from __future__ import annotations

from typing import Any

from qamra_workbook.pictures import PICTURES
from qamra_workbook.pictures.journey_words import COLORS
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_kit import H, W, card, dots_mark, picture, pid, svg, text
from qamra_workbook.render.pages.workbook_common import ring_at
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.spec import Figure

# for the grown-up, with the child's gender (`ctx.text`): «ليسمع طفلكم» / «لتسمع طفلتكم»
QR_NOTE = "للأهل: امسحوا الرمز بالهاتف {ليسمع طفلكم/لتسمع طفلتكم}، أو اقرؤوا الكلمات بصوتكم."


def _audio_problem(ctx: PageContext) -> list[str]:
    return [] if ctx.page.audio else ["a listening page carries an audio QR (audio: true)"]


def rows_of(n: int, top: float = 0.0) -> list[tuple[float, float]]:
    """(y, height) of n row cards."""
    pitch = (H - top) / n
    return [(top + i * pitch + 2, pitch - 6) for i in range(n)]


def _row_cards(
    choices: list[str], y: float, h: float, style: str = "color"
) -> list[tuple[str, float, float]]:
    size = min(h - 8, 46.0)
    step = (W - 40) / len(choices)
    return [(w, W - 32 - (k + 0.5) * step - size / 2, size) for k, w in enumerate(choices)]


@page_type("listen-rows")
def listen_rows(ctx: PageContext) -> Built:
    """Rows of pictures in the order the audio plays: in each row, mark the picture you hear (circle it, or
    colour it with `style: line`)."""
    rows = [[str(w) for w in r] for r in ctx.page.params.get("rows", [])]
    answers = [str(a) for a in ctx.page.params.get("answers", [])]
    style = str(ctx.page.params.get("style", "color"))
    problems = _audio_problem(ctx)
    if len(rows) != len(answers) or any(r.count(a) != 1 for r, a in zip(rows, answers, strict=False)):
        problems.append("each row has its answer exactly once")
    body = []
    for i, ((y, h), row) in enumerate(zip(rows_of(len(rows)), rows, strict=True)):
        body.append(card(0, y, W, h, r=8))
        body.append(dots_mark(i + 1, W - 12, y + h / 2))
        for w, x, size in _row_cards(row, y, h):
            body.append(picture(w, x, y + (h - size) / 2, size, style))
            if i < len(answers) and w == answers[i]:
                example = i == 0 and ctx.page.example
                body.append(
                    ring_at(
                        x + size / 2,
                        y + h / 2,
                        size / 2 + 2,
                        h / 2 - 1,
                        color="#2FA36B" if example else "#E0483A",
                    ).replace('class="key-ring"', "" if example else 'class="key-ring"')
                )
    key = [f"{ctx.num(i + 1)}: {PICTURES[pid(a)].word_ar}" for i, a in enumerate(answers)]
    return Built({"svg": svg(body), "qr_note": ctx.text(QR_NOTE)}, key, problems)


def speaker(cx: float, cy: float, s: float, waves: int) -> str:
    """A speaker with 1 (soft) to 3 (loud) sound waves."""
    body = draw.d_path(
        ("M", (cx - s, cy - s * 0.35)),
        ("L", (cx - s * 0.5, cy - s * 0.35)),
        ("L", (cx, cy - s * 0.8)),
        ("L", (cx, cy + s * 0.8)),
        ("L", (cx - s * 0.5, cy + s * 0.35)),
        ("L", (cx - s, cy + s * 0.35)),
        ("Z", ()),
    )
    out = [
        draw.el("path", d=body, fill="#4A95D3", stroke="#2B2E4A", stroke_width=0.8, stroke_linejoin="round")
    ]
    for k in range(waves):
        r = s * (0.55 + 0.4 * k)
        arc = draw.d_path(
            ("M", (cx + r * 0.5, cy - r * 0.85)), ("Q", (cx + r * 1.2, cy, cx + r * 0.5, cy + r * 0.85))
        )
        out.append(draw.path(arc, stroke="#2B2E4A", width=1.3))
    return "".join(out)


def _two_choice_rows(
    ctx: PageContext, rows: list[dict[str, Any]], pick: str, left: Any, right: Any, names: tuple[str, str]
) -> Built:
    """Rows of one source picture (or none) and two answers: `left` (true) and `right` (false) drawers."""
    body, key = [], []
    for i, ((y, h), row) in enumerate(zip(rows_of(len(rows)), rows, strict=True)):
        body.append(card(0, y, W, h, r=8))
        body.append(dots_mark(i + 1, W - 12, y + h / 2))
        size = min(h - 10, 44.0)
        if row.get("sound"):
            body.append(picture(str(row["sound"]), W - 30 - size, y + (h - size) / 2, size))
        body.append(card(W - 36 - size - 6, y + 6, 0.6, h - 12, r=0, fill="#E4D6BC", stroke="none"))
        yes = bool(row.get(pick))
        for k, (drawer, cx) in enumerate(((left, 92.0), (right, 38.0))):
            body.append(card(cx - 26, y + 4, 52, h - 8, r=8, fill="#FFF6F2", stroke="none"))
            body.append(drawer(cx, y + h / 2, min(h - 12, 40.0)))
            if (k == 0) == yes:
                body.append(ring_at(cx, y + h / 2, 27, h / 2 - 3))
        key.append(f"{ctx.num(i + 1)}: {names[0] if yes else names[1]}")
    return Built({"svg": svg(body), "qr_note": ctx.text(QR_NOTE)}, key, _audio_problem(ctx))


@page_type("loud-soft")
def loud_soft(ctx: PageContext) -> Built:
    """Each row plays a sound: circle the loud speaker or the soft one."""
    rows = [dict(r) for r in ctx.page.params.get("rows", [])]
    return _two_choice_rows(
        ctx,
        rows,
        "loud",
        lambda x, y, s: speaker(x, y, s * 0.45, 3),
        lambda x, y, s: speaker(x, y, s * 0.26, 1),
        ("عالٍ", "منخفض"),
    )


@page_type("fast-slow")
def fast_slow(ctx: PageContext) -> Built:
    """Each row plays a rhythm: circle the rabbit (fast) or the turtle (slow)."""
    rows = [dict(r) for r in ctx.page.params.get("rows", [])]
    return _two_choice_rows(
        ctx,
        rows,
        "fast",
        lambda x, y, s: picture("rabbit", x - s / 2, y - s / 2, s),
        lambda x, y, s: picture("turtle", x - s / 2, y - s / 2, s),
        ("سريع", "بطيء"),
    )


def _same(x: float, y: float, s: float) -> str:
    r = s * 0.22
    return draw.el(
        "circle", cx=x - r * 1.3, cy=y, r=r, fill="#7DB46C", stroke="#2B2E4A", stroke_width=0.8
    ) + draw.el("circle", cx=x + r * 1.3, cy=y, r=r, fill="#7DB46C", stroke="#2B2E4A", stroke_width=0.8)


def _different(x: float, y: float, s: float) -> str:
    r = s * 0.22
    tri = draw.polyline([(x + r * 1.3, y - r), (x + r * 2.3, y + r), (x + r * 0.3, y + r)]) + " Z"
    return draw.el(
        "circle", cx=x - r * 1.3, cy=y, r=r, fill="#7DB46C", stroke="#2B2E4A", stroke_width=0.8
    ) + draw.el("path", d=tri, fill="#EE8A6E", stroke="#2B2E4A", stroke_width=0.8, stroke_linejoin="round")


@page_type("same-different")
def same_different(ctx: PageContext) -> Built:
    """Each row plays two sounds: circle the twins (the same) or the two different shapes."""
    pairs = [(str(a), str(b)) for a, b in ctx.page.params.get("pairs", [])]
    rows = [{"same": a == b} for a, b in pairs]
    # the key agrees with what the title compares: two sounds («متشابهان») or two words («متشابهتان»)
    same, different = (str(x) for x in ctx.page.params.get("names", ("متشابهان", "مختلفان")))
    built = _two_choice_rows(ctx, rows, "same", _same, _different, (same, different))
    built.answer = [
        f"{ctx.num(i + 1)}: {PICTURES[pid(a)].word_ar} و{PICTURES[pid(b)].word_ar} — "
        f"{same if a == b else different}"
        for i, (a, b) in enumerate(pairs)
    ]
    return built


@page_type("vocab-unit")
def vocab_unit(ctx: PageContext) -> Built:
    """First English words: pictures with their word (point to what you hear), or balloons to colour."""
    params = ctx.page.params
    names = [str(w) for w in params.get("words", [])]
    colours = [str(c) for c in params.get("colors", [])]
    body, key = [], []
    ltr = ctx.page.lang == "en"  # English pages read left to right
    if colours:
        size = 60.0
        for k, c in enumerate(colours):
            r, col = divmod(k, 2)
            x, y = (W / 2 + 10 if col == 0 else W / 2 - 10 - size), 6 + r * (size + 40)
            if ltr:
                x = W - x - size
            body.append(card(x - 4, y - 4, size + 8, size + 32, r=8))
            body.append(picture("balloon", x, y, size, "line"))
            body.append(
                picture("balloon", x, y, size, main=COLORS[c][0]).replace("<svg", '<svg class="key-ring"', 1)
            )
            body.append(text(COLORS[c][2], x + size / 2, y + size + 18, 9, cls="wb-en", rtl=False))
        key.append(", ".join(COLORS[c][2] for c in colours))
    else:
        cells = [(w, k) for k, w in enumerate(names)]
        cols = 3
        size = 50.0
        for w, k in cells:
            r, col = divmod(k, cols)
            in_row = min(cols, len(names) - r * cols)
            x = W / 2 + (in_row / 2 - col - 1) * (size + 12) + 6
            y = 8 + r * (size + 40)
            if ltr:
                x = W - x - size
            body.append(card(x - 4, y - 4, size + 8, size + 32, r=8))
            body.append(picture(w, x, y, size))
            body.append(
                text(PICTURES[pid(w)].word_en, x + size / 2, y + size + 18, 9, cls="wb-en", rtl=False)
            )
        key.append(", ".join(PICTURES[pid(w)].word_en for w in names))
    return Built(
        {"svg": svg(body), "qr_note": "For parents: scan to hear the words, or read them aloud."},
        key,
        _audio_problem(ctx),
    )


@page_type("picture-riddle")
def picture_riddle(ctx: PageContext) -> Built:
    """A riddle for the grown-up to read aloud, and three pictures: circle the answer."""
    riddle = ctx.text(str(ctx.page.params.get("riddle", "")))
    choices = [str(w) for w in ctx.page.params.get("choices", [])]
    answer = str(ctx.page.params.get("answer", ""))
    problems = (
        [] if choices.count(answer) == 1 and riddle else ["a riddle, and its answer once among the choices"]
    )
    body = [card(8, 0, W - 16, 70, r=12, fill="#FCEFD2", stroke="#E2A32A", width=0.8)]
    body.append(text("؟", W - 24, 44, 26, cls="wb-title", color="#E2A32A"))
    if len(strip_tashkeel(riddle)) <= 34:  # a short riddle on one line
        body.append(text(riddle, W / 2 - 6, 40, 9.5, cls="wb-word", color="#1C2140"))
    else:  # a longer one: a clue to a line
        clues = [c.strip() for c in riddle.replace("؟", "").split("،") if c.strip()]
        for k, clue in enumerate(clues):
            y = 70 * (k + 1) / (len(clues) + 1) + 3.2
            body.append(text(clue, W - 42, y, 8.6, cls="wb-word", color="#1C2140", anchor="end"))
    size, step = 50.0, (W - 20) / max(len(choices), 1)
    for k, w in enumerate(choices):
        x = W - 10 - (k + 0.5) * step - size / 2
        body.append(card(x - 4, 96, size + 8, size + 8, r=8))
        body.append(picture(w, x, 100, size))
        if w == answer:
            body.append(ring_at(x + size / 2, 125, size / 2 + 5, size / 2 + 5))
    return Built(
        {"svg": svg(body)}, [f"الجواب: {PICTURES[pid(answer)].word_ar}"] if answer else None, problems
    )


# ---- stages 2–3: syllable claps, rhymes, English vocabulary without pictures ------------------------------


@page_type("journey-claps")
def claps(ctx: PageContext) -> Built:
    """Clap the syllables of a word: its picture, then circles to colour, one per clap."""
    words = [pid(str(w)) for w in ctx.page.params.get("words", [])]
    counts = [int(c) for c in ctx.page.params.get("claps", [])]
    problems = _audio_problem(ctx) + ([] if len(words) == len(counts) else ["one clap count per word"])
    counts = (counts + [1] * len(words))[: len(words)]
    body, key = [], []
    for i, ((y, h), w) in enumerate(zip(rows_of(len(words)), words, strict=True)):
        body.append(card(0, y, W, h, r=8))
        body.append(dots_mark(i + 1, W - 12, y + h / 2))
        size = min(h - 8, 40.0)
        body.append(picture(w, W - 28 - size, y + (h - size) / 2, size))
        body.append(
            text(PICTURES[w].word_ar, W - 28 - size / 2, y + h - 3, 4.8, cls="wb-word", color="#676B83")
        )
        for k in range(4):
            cx = W - 44 - size - (k + 0.5) * 22
            fill = "#FFFFFF" if not (i == 0 and ctx.page.example and k < counts[0]) else ctx.style.color
            body.append(
                draw.el("circle", cx=cx, cy=y + h / 2, r=8, fill=fill, stroke="#2B2E4A", stroke_width=0.8)
            )
            if k < counts[i]:
                body.append(
                    draw.el("circle", cx=cx, cy=y + h / 2, r=6.4, fill=ctx.style.color, class_="key-ring")
                )
        key.append(f"{PICTURES[w].word_ar}: {ctx.num(counts[i])}")
    return Built({"svg": svg(body), "qr_note": ctx.text(QR_NOTE)}, key, problems)


@page_type("journey-rhyme")
def rhyme(ctx: PageContext) -> Built:
    """Each row: three pictures; colour the two whose names end the same way (`pairs` lists the rhyming
    pair, `odd` the third; `words`: the pair's words as the audio says them, «قَمَر، شَجَر», when a picture's
    own name does not rhyme, «شَجَرَة»)."""
    pairs = [[pid(str(a)), pid(str(b))] for a, b in ctx.page.params.get("pairs", [])]
    odd = [pid(str(o)) for o in ctx.page.params.get("odd", [])]
    problems = _audio_problem(ctx) + ([] if len(odd) == len(pairs) else ["one odd picture per pair"])
    odd = (odd + ["apple"] * len(pairs))[: len(pairs)]
    words = [[str(x) for x in pair] for pair in ctx.page.params.get("words", [])]
    body, key = [], []
    for i, ((y, h), pair) in enumerate(zip(rows_of(len(pairs)), pairs, strict=True)):
        body.append(card(0, y, W, h, r=8))
        body.append(dots_mark(i + 1, W - 12, y + h / 2))
        row = [*pair, odd[i]]
        ctx.rng(f"rhyme{i}").shuffle(row)
        for w, x, size in _row_cards(row, y, h):
            body.append(picture(w, x, y + (h - size) / 2, size, "line"))
            if w in pair:
                body.append(
                    picture(w, x, y + (h - size) / 2, size).replace("<svg", '<svg class="key-ring"', 1)
                )
        said = words[i] if i < len(words) else [PICTURES[w].word_ar for w in pair]
        key.append(f"{said[0]} و{said[1]}")
    return Built({"svg": svg(body), "qr_note": ctx.text(QR_NOTE)}, key, problems)


FIGURES: dict[str, Figure] = {
    "mother": "woman",
    "father": "man",
    "sister": "girl",
    "brother": "boy",
    "grandma": "grandma",
    "grandpa": "grandpa",
    "baby": "baby",
}
SHAPE_COLORS = {
    "circle": "#F7C84A",
    "square": "#5E86D6",
    "triangle": "#E5604E",
    "rectangle": "#7DB46C",
    "star": "#F2994A",
    "heart": "#E97A98",
}
NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


@page_type("journey-vocab-cards")
def vocab_cards(ctx: PageContext) -> Built:
    """An English vocabulary unit as word cards, left to right: family members as figures, numbers as digits
    with dots, everything else as its picture (`words` are picture ids or family words)."""
    from qamra_workbook.render.pages.journey_kit import person
    from qamra_workbook.render.people import person as figure

    words = [str(w) for w in ctx.page.params.get("words", [])]
    numbers = [int(n) for n in ctx.page.params.get("numbers", [])]
    body, labels = [], []
    cells = [(w, k) for k, w in enumerate(words or [str(n) for n in numbers])]
    cols = 4 if len(cells) > 6 else 3
    size = 38.0 if cols == 4 else 48.0
    rows = (len(cells) + cols - 1) // cols
    step_x, step_y = (W - 8) / cols, min((H - 8) / rows, size + 44)  # the cards use the page, centred in it
    left = (H - 8 - rows * step_y) / 2
    for w, k in cells:
        r, c = divmod(k, cols)
        x, y = 4 + c * step_x + (step_x - size) / 2, 4 + left + r * step_y + (step_y - (size + 26)) / 2 + 3
        body.append(card(x - 4, y - 3, size + 8, size + 26, r=8))
        if numbers:
            n = int(w)
            body.append(
                text(
                    str(n),
                    x + size / 2,
                    y + size * 0.62,
                    size * 0.6,
                    cls="wb-en",
                    color=ctx.style.deep,
                    rtl=False,
                )
            )
            body += [
                draw.el(
                    "circle",
                    cx=x + 4 + (j % 5) * (size - 8) / 4,
                    cy=y + size - 8 + (j // 5) * 6,
                    r=2.2,
                    fill=ctx.style.color,
                )
                for j in range(n)
            ]
            label = NUMBER_WORDS[n]
        elif w in FIGURES:
            outfit = {
                "woman": "#E98AA6",
                "man": "#6E95DB",
                "girl": "#F2A65A",
                "boy": "#86BF72",
                "grandma": "#A58BD8",
                "grandpa": "#5DB7A8",
                "baby": "#F2A65A",
            }[FIGURES[w]]
            body.append(
                person(
                    figure(FIGURES[w], outfit, scarf="#8FB9A8" if w in ("mother", "grandma") else None),
                    x + size / 2,
                    y + size,
                    size * 0.98,
                )
            )
            label = w
        elif w in SHAPE_COLORS:  # the shapes themselves, in the colours of the shape key
            from qamra_workbook.render.pages.journey_shapes import filled

            body.append(filled(w, x + size / 2, y + size / 2, size * 0.78, SHAPE_COLORS[w]))
            label = w
        else:
            body.append(picture(w, x, y, size))
            label = PICTURES[pid(w)].word_en
        body.append(
            text(
                label,
                x + size / 2,
                y + size + 16,
                7.5 if len(label) < 9 else 6,
                cls="wb-en",
                color="#1C2140",
                rtl=False,
            )
        )
        labels.append(label)
    return Built(
        {"svg": svg(body), "qr_note": "For parents: scan to hear the words, or read them aloud."},
        [", ".join(labels)],
        _audio_problem(ctx),
    )
