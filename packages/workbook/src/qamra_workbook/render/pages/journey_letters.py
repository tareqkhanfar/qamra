"""Journey letter pages for stages 2 and 3 (Addendum 6 §4.8–4.11): the first sound of a word, the writing
progression on letters (levels 3–7), the harakat, syllables, words, English words and sentences, and the
alphabet pages. Tracing uses Qamra's own single-stroke letter paths (`qamra_workbook.letters`), never a font;
words the child reads are printed vowelised in Naskh. The دوسية's letter pages (finger-trace, letter-trace,
find-letter, en-letter, unit-review, letter-position, name-trace) are reused as they are."""

from __future__ import annotations

import math
from collections.abc import Callable

from markupsafe import Markup

from qamra_workbook.geometry import Stroke, bounds
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures import PICTURES
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_kit import (
    SOFT,
    H,
    W,
    card,
    dots_mark,
    join_columns,
    join_columns_ltr,
    picture,
    pid,
    svg,
    text,
)
from qamra_workbook.render.pages.letters import (
    ARROW_AT,
    en_letter,
    letter_extent,
    start_points,
    tracing_row,
)
from qamra_workbook.render.pages.workbook_arabic import first_letter, row_svg, same_letter
from qamra_workbook.render.pages.workbook_common import (
    INK,
    answer_line,
    arabic_shape,
    fit,
    fit_lines,
    glyph,
    hook,
    ring_at,
    start_marks,
)
from qamra_workbook.render.pages.workbook_front import arabic_name_row, spell
from qamra_workbook.render.registry import Built, PageContext, page_type

LINE = "#C9B994"
QR_NOTE = "للأهل: امسحوا الرمز ليسمع الطفل، أو اقرؤوا بصوتكم."


def shape(char: str, form: str = "isolated") -> Letter:
    return arabic_shape(char, form)


def solid(shape_: Letter, x: float, y: float, w: float, h: float, color: str, number: object = None) -> str:
    """The letter as a solid marker glyph centred in a box, with its numbered start dots when `number`."""
    scale, dx, dy = fit(shape_, x, y, w, h, pad=1.0)
    out = glyph(shape_, scale, dx, dy, color=color, width=13)
    if number is not None:
        out += start_marks(shape_, scale, dx, dy, 1.6, number)  # type: ignore[arg-type]
    return out


def hollow(shape_: Letter, x: float, y: float, w: float, h: float) -> str:
    """The letter as a thick outline to colour in (a dark edge round a white body: a white letter on white
    paper would be invisible), in the same hand and width as the دوسية's letter-intro."""
    scale, dx, dy = fit(shape_, x, y, w, h, pad=2.6)
    return glyph(shape_, scale, dx, dy, edge=INK, fill="#FFFFFF", width=24)


def starts_with(word_id: str, char: str) -> bool:
    return same_letter(first_letter(PICTURES[word_id].word_ar), char)


def _clear_dots(shape_: Letter, half: float, r: float, gap: float = 3.0) -> list[tuple[float, float]]:
    """The letter's dots, nudged (in the letter's units) until a disc of radius `r` clears the thick body
    (`half` its width) and the other discs: the dots are placed for a thin pen, not for a finger-wide band."""
    pts = [[x, y] for x, y in shape_.dots]
    samples = [p for s in shape_.strokes for p in s.dots(2.0)]
    for _ in range(80):
        moved = False
        for i, p in enumerate(pts):
            near = min(samples, key=lambda q: math.dist((p[0], p[1]), q))
            d = math.dist((p[0], p[1]), near)
            need = half + r + gap
            if d < need - 0.05:
                ux, uy = ((p[0] - near[0]) / d, (p[1] - near[1]) / d) if d > 1e-6 else (0.0, -1.0)
                p[0] += ux * (need - d)
                p[1] += uy * (need - d)
                moved = True
            for j, q in enumerate(pts):
                dd = math.dist((p[0], p[1]), (q[0], q[1]))
                if j != i and dd < 2 * r + gap - 0.05:
                    ux, uy = ((p[0] - q[0]) / dd, (p[1] - q[1]) / dd) if dd > 1e-6 else (1.0, 0.0)
                    push = (2 * r + gap - dd) / 2
                    p[0], p[1], q[0], q[1] = (
                        p[0] + ux * push,
                        p[1] + uy * push,
                        q[0] - ux * push,
                        q[1] - uy * push,
                    )
                    moved = True
        if not moved:
            break
    return [(p[0], p[1]) for p in pts]


def finger_letter(
    shape_: Letter, *, fill: str, edge: str, width: float, number: Callable[[int], str]
) -> tuple[str, tuple[float, float, float, float]]:
    """The big letter a finger traces: a thick body with white arrows and numbered start dots, and its dots as
    numbered discs that clear the body and each other. Returns the drawing and its view box."""
    ex0, ey0, ex1, ey1 = letter_extent(shape_)
    width = max(11.0, min(width, 0.2 * max(ex1 - ex0, ey1 - ey0)))  # a small loop (ه د) keeps its hole open
    r = width * 0.5
    dots = _clear_dots(shape_, width * 0.61, r)
    # a short second stroke (the hamza of أ) is a mark: half as thick, so it stays an open shape
    widths = [
        width * 0.5 if k and shape_.rtl and raw.length < 60 else width for k, raw in enumerate(shape_.strokes)
    ]
    out = [draw.path(s.d, stroke=edge, width=w * 1.22) for s, w in zip(shape_.strokes, widths, strict=True)]
    out += [
        draw.el("circle", cx=x, cy=y, r=r, fill=fill, stroke=edge, stroke_width=width * 0.11) for x, y in dots
    ]
    out += [draw.path(s.d, stroke=fill, width=w) for s, w in zip(shape_.strokes, widths, strict=True)]
    for s, w in zip(shape_.strokes, widths, strict=True):
        if w < width:
            continue  # no arrows on a mark
        for f in ARROW_AT:
            if s.length * f > width * 0.9:  # keep arrows clear of the start dot
                point, angle = s.at(f)
                out.append(draw.chevron(point, angle, width * 0.42, "#FFFFFF", width * 0.12))
    for k, (point, w) in enumerate(
        zip(start_points(shape_.strokes, width * 0.42), widths, strict=True), start=1
    ):
        out.append(draw.start_dot(point, width * 0.42 if w == width else width * 0.3, number(k)))
    for k, (x, y) in enumerate(dots, start=len(shape_.strokes) + 1):
        out.append(draw.start_dot((x, y), width * 0.3, number(k)))
    x0, y0, x1, y1 = bounds(list(shape_.strokes))
    for x, y in dots:
        x0, y0, x1, y1 = min(x0, x - r), min(y0, y - r), max(x1, x + r), max(y1, y + r)
    pad = width
    return "".join(out), (x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)


# ---- the first sound (Addendum 6 §4.8) ------------------------------------------------------------------


@page_type("journey-first-sound")
def first_sound(ctx: PageContext) -> Built:
    """Hear the sound of a letter with its key word, then colour (or join to the letter) the pictures whose
    names start with it; the others are distractors. The letter itself is only heard: it is met later."""
    params = ctx.page.params
    char = str(params.get("letter", "ب"))
    words = [pid(str(w)) for w in params.get("words", [])]
    others = [pid(str(w)) for w in params.get("distractors", [])]
    problems = [
        f"{PICTURES[w].word_ar} does not start with {char}" for w in words if not starts_with(w, char)
    ]
    problems += [f"{PICTURES[w].word_ar} starts with {char}" for w in others if starts_with(w, char)]
    if not ctx.page.audio:
        problems.append("a first-sound page carries an audio QR")
    key = words[0] if words else None
    body = [card(0, 0, W, 68, r=10, fill=SOFT, stroke="none")]
    if key:
        body.append(picture(key, W - 62, 5, 46))
        body.append(text(PICTURES[key].word_ar, W - 39, 62, 7, cls="wb-word", color=ctx.style.deep))
        body.append(text("أَسْمَعُ الصَّوْتَ الأَوَّلَ", 60, 28, 6.5, cls="wb-title", color="#1C2140"))
        body.append(
            text(
                "«" + strip_tashkeel(PICTURES[key].word_ar)[:1] + "»",
                60,
                52,
                12,
                cls="wb-title",
                color=ctx.style.color,
            )
        )
    items = words + others
    ctx.rng("sound").shuffle(items)
    cols, size = 3, 44.0
    for k, w in enumerate(items[:6]):
        r, c = divmod(k, cols)
        x, y = W - 12 - (c + 1) * (size + 12), 80 + r * (size + 18)
        body.append(card(x - 4, y - 4, size + 8, size + 8, r=8))
        body.append(picture(w, x, y, size, "line"))
        if w in words:
            body.append(picture(w, x, y, size).replace("<svg", '<svg class="key-ring"', 1))
            if k == 0 and ctx.page.example:
                body.append(ring_at(x + size / 2, y + size / 2, size / 2 + 3, size / 2 + 3, color="#2FA36B"))
    key_text = "تبدأ بالصوت نفسه: " + "، ".join(PICTURES[w].word_ar for w in words)
    return Built({"svg": svg(body), "qr_note": QR_NOTE}, [key_text], problems)


@page_type("journey-en-letter")
def journey_en_letter(ctx: PageContext) -> Built:
    """The دوسية's English letter page; with `position: end` the key word ends with the letter (x — box)."""
    built = en_letter(ctx)
    if ctx.page.params.get("position") == "end":
        built.problems = [p for p in built.problems if "does not start with" not in p]
    return built


# ---- the writing progression on letters (§4.10, levels 3–7) ----------------------------------------------


def partial(shape_: Letter, scale: float, dx: float, dy: float, keep: float) -> str:
    """The letter with its first stroke solid up to `keep` of its length and dotted after it, its other
    strokes and dots dotted: the child completes it (level 4)."""
    first = shape_.strokes[0].scaled(scale, dx, dy)
    pts = first.polyline
    k = max(2, int(len(pts) * keep))
    out = [draw.path(draw.polyline(pts[:k]), stroke=INK, width=13 * scale)]
    rest = Stroke(draw.polyline(pts[k - 1 :]))
    out.append(draw.dotted(rest, spacing=3.2, r=1.0))
    for s in shape_.strokes[1:]:
        out.append(draw.dotted(s.scaled(scale, dx, dy), spacing=3.0, r=0.9))
    out += [
        draw.el(
            "circle",
            cx=dx + x * scale,
            cy=dy + y * scale,
            r=shape_.dot_r * scale,
            fill="none",
            stroke=INK,
            stroke_width=0.6,
            stroke_dasharray="1.2 1",
        )
        for x, y in shape_.dots
    ]
    return "".join(out)


def _row_card(y: float, h: float, model: Letter, ctx: PageContext) -> list[str]:
    out = [card(0, y, W, h, r=7), card(W - 38, y + 4, 34, h - 8, r=6, fill=ctx.style.tint, stroke="none")]
    out.append(solid(model, W - 36, y + 6, 30, h - 12, ctx.style.color, ctx.num))
    return out


def row_cap(model: Letter, width: float, repeats: int, most: float) -> float:
    """The row's cap height (mm), at most `most`, small enough that `repeats` copies of the letter fit the row
    (a wide letter like ب gets a smaller row than ا, so the page keeps its «three times»)."""
    x0, _, x1, _ = letter_extent(model)
    g = model.guides
    glyph_max = (width - 16 - 13 * (repeats - 1)) / repeats
    return min(most, glyph_max / max(x1 - x0, 1) * (g.base - g.top))


def letter_progression(ctx: PageContext, level: int) -> Built:
    params = ctx.page.params
    targets = [str(t) for t in params.get("target", [])] if isinstance(params.get("target"), list) else []
    body: list[str] = []
    problems: list[str] = []
    if level in (3, 4, 5):
        pitch = H / max(len(targets), 1)
        for i, char in enumerate(targets[:3]):
            model = shape(char)
            y = i * pitch
            body += _row_card(y + 1, pitch - 4, model, ctx)
            if level == 3:
                repeats = int(params.get("repeats", 3))
                row, _ = row_svg(
                    tracing_row(
                        model,
                        width=W - 46,
                        cap=row_cap(model, W - 46, repeats, min(26.0, pitch - 20)),
                        count=repeats,
                        number=ctx.num,
                    ),
                    5,
                    y + (pitch - 4) / 2 - 12,
                )
                body.append(row)
            elif level == 4:
                for k in range(3):
                    bx = W - 46 - (k + 1) * 44
                    scale, dx, dy = fit(model, bx, y + 8, 38, pitch - 18, pad=2.0)
                    body.append(partial(model, scale, dx, dy, 0.55 if k < 2 else 0.35))
            else:
                row, _height = row_svg(
                    tracing_row(model, width=W - 46, cap=min(24.0, pitch - 20), count=0, number=ctx.num),
                    5,
                    y + (pitch - 4) / 2 - 12,
                )
                body.append(row)
                for k in range(3):
                    body.append(draw.start_dot((W - 54 - k * 44, y + pitch / 2 - 2), 1.9))
        return Built({"svg": svg(body)}, None, problems)
    if level == 6:
        pitch = H / max(len(targets), 1)
        for i, char in enumerate(targets[:3]):
            model = shape(char)
            y = i * pitch
            body += _row_card(y + 1, pitch - 4, model, ctx)
            scale, dx, dy = fit_lines(model, W - 36, y + 6, 30, pitch - 12)
            base = dy + model.guides.base * scale
            body.append(draw.path(f"M{W - 44} {base} L8 {base}", stroke=LINE, width=0.9))
            for k in range(4):
                sx = W - 56 - k * 36
                start = model.strokes[0].start
                body.append(
                    draw.start_dot((sx + (start[0] - model.width / 2) * scale, dy + start[1] * scale), 1.9)
                )
        return Built({"svg": svg(body)}, None, problems)
    # level 7: the first letter of pictures, or a dictation
    letters = [str(c) for c in params.get("letters", [])]
    pictures = [pid(str(w)) for w in params.get("pictures", [])]
    pitch = H / max(len(letters), 1)
    key = []
    for i, char in enumerate(letters):
        y = i * pitch
        body.append(card(0, y + 1, W, pitch - 4, r=7))
        if pictures:
            body.append(picture(pictures[i], W - 8 - (pitch - 12), y + 5, pitch - 12))
            if not starts_with(pictures[i], char):
                problems.append(f"{PICTURES[pictures[i]].word_ar} does not start with {char}")
        else:
            body.append(dots_mark(i + 1, W - 16, y + pitch / 2 - 1))
        box_w = 60.0
        body.append(
            card(
                W / 2 - box_w / 2 - 20,
                y + 8,
                box_w,
                pitch - 18,
                r=6,
                fill="#FFFFFF",
                stroke="#8C90A6",
                dash="3 2.4",
                width=0.7,
            )
        )
        body.append(
            draw.path(
                f"M{W / 2 - box_w / 2 - 16} {y + pitch - 16} L{W / 2 + box_w / 2 - 24} {y + pitch - 16}",
                stroke=LINE,
                width=0.8,
            )
        )
        body.append(  # the answer: the whole letter (its dots too) shows in the answer key only
            f'<g class="key-ring">{solid(shape(char), W / 2 - 16, y + 12, 32, pitch - 28, "#E0483A")}</g>'
        )
        key.append(f"{ctx.num(i + 1)}: {char}")
    if params.get("target") == "dictation" and not ctx.page.audio:
        problems.append("a dictation page carries an audio QR")
    return Built({"svg": svg(body), "qr_note": QR_NOTE}, key, problems)


def _trace_caps(shape_: Letter) -> dict[str, float]:
    """The cap heights of the large, medium and small rows: a small letter (ه د) gets a taller row, so that
    it is drawn about as big as the others and its dots do not crowd."""
    x0, y0, x1, y1 = letter_extent(shape_)
    g = shape_.guides
    units, base = max(y1 - y0, (x1 - x0) * 0.6, 1.0), g.base - g.top
    grow = max(1.0, min(1.3, 0.8 * base / units))  # at 1.3 the two rows still fit the page
    return {"l": 24.0 * grow, "m": 17.0 * grow, "s": 13.0 * grow}


@page_type("journey-letter-trace")
def journey_letter_trace(ctx: PageContext) -> Built:
    """The دوسية's letter-trace page (the letter big with a dotted centre line, then rows of dotted letters),
    sized to the letter: a small letter gets a thinner band and taller rows."""
    from qamra_workbook.render.pages.workbook_arabic import big_track

    params = ctx.page.params
    sh = shape(str(params.get("letter", "ب")))
    sizes = [str(k) for k in params.get("sizes", ["xl", "l", "m"])]
    x0, y0, x1, y1 = letter_extent(sh)
    extent = max(x1 - x0, y1 - y0)
    body = [card(0, 0, W, 84, r=7)]
    body.append(
        big_track(
            sh,
            20,
            2,
            146,
            80,
            ctx.num,
            ctx.style.color,
            most=0.8 if extent < 70 else 0.5,
            band_units=min(24.0, 0.25 * extent),
        )
    )
    body.append(card(5, 5, 30, 10, r=5, fill=ctx.style.tint, stroke="none"))
    body.append(text("كَبيرٌ", 20, 12, 5, color=ctx.style.deep))
    y, caps = 90.0, _trace_caps(sh)
    for size in [k for k in sizes if k in caps]:
        row, height = row_svg(tracing_row(sh, width=W - 10, cap=caps[size], number=ctx.num), 5, y + 1)
        body.append(card(0, y - 2, W, height + 5, r=6))
        body.append(row)
        y += height + 7
    problems = [] if y <= 206 else [f"the tracing rows need {y:.0f} mm (max 204)"]
    if sizes[:1] != ["xl"]:
        problems.append("letter-trace starts with the big letter (xl)")
    return Built({"svg": svg(body)}, None, problems)


@page_type("journey-writing-review")
def writing_review(ctx: PageContext) -> Built:
    """A review of writing levels 3 and 4: for each letter its model, a dotted copy to trace and a copy
    written halfway for the child to finish."""
    targets = [str(t) for t in ctx.page.params.get("letters", [])][:3]
    pitch = H / max(len(targets), 1)
    body: list[str] = []
    for i, char in enumerate(targets):
        model, y = shape(char), i * pitch
        body += _row_card(y + 1, pitch - 4, model, ctx)
        row, _ = row_svg(
            tracing_row(model, width=66, cap=min(22.0, pitch - 24), count=1, number=ctx.num),
            W - 46 - 66,
            y + 12,
        )
        body.append(row)
        body.append(text("أَتَتَبَّعُ", W - 50, y + 9, 3.8, cls="wb-label", color="#676B83", anchor="end"))
        scale, dx, dy = fit(model, 8, y + 14, 56, pitch - 24, pad=2.0)
        body.append(partial(model, scale, dx, dy, 0.55))
        body.append(text("أُكْمِلُ", 64, y + 9, 3.8, cls="wb-label", color="#676B83", anchor="end"))
    return Built({"svg": svg(body)}, None, [] if targets else ["letters to review"])


# ---- harakat, syllables, words (§4.9) -----------------------------------------------------------------

HARAKAT = {
    "fatha": ("َ", "الفَتْحَةُ", "above"),
    "damma": ("ُ", "الضَّمَّةُ", "above"),
    "kasra": ("ِ", "الكَسْرَةُ", "below"),
    "sukun": ("ْ", "السُّكونُ", "above"),
}


def mark(kind: str, x: float, y: float, s: float, color: str, dotted: bool = False) -> str:
    """A haraka drawn with a stroke (not a font): fatha and kasra are short slants, the damma a small waw,
    the sukun a small circle."""
    if kind == "damma":
        d = (
            f"M{x + s * 0.4} {y - s * 0.3} C{x + s * 0.4} {y - s * 0.9} {x - s * 0.5} {y - s * 0.9}"
            f" {x - s * 0.4} {y - s * 0.3} L{x + s * 0.5} {y + s * 0.1}"
        )
    elif kind == "sukun":
        r = s * 0.4
        d = f"M{x - r} {y} A{r} {r} 0 1 1 {x + r} {y} A{r} {r} 0 1 1 {x - r} {y}"
    else:
        d = f"M{x - s * 0.5} {y + s * 0.2} L{x + s * 0.5} {y - s * 0.2}"
    if dotted:
        return draw.dotted(Stroke(d), spacing=1.4, r=0.62)  # a tight dotted mark: it must read as a mark
    return draw.path(d, stroke=color, width=s * 0.28)


def with_mark(
    char: str, kind: str, x: float, y: float, w: float, h: float, color: str, dotted: bool = False
) -> str:
    """A letter with its haraka: the letter from our strokes, the mark above (or below for the kasra)."""
    sh = shape(char)
    scale, dx, dy = fit(sh, x, y + 8, w, h - 16, pad=1.0)
    x0, y0, x1, y1 = letter_extent(sh)
    cx = dx + (x0 + x1) / 2 * scale
    my = dy + (y0 * scale - 6) if HARAKAT[kind][2] == "above" else dy + (y1 * scale + 6)
    out = draw.dotted(Stroke(sh.strokes[0].scaled(scale, dx, dy).d), spacing=3.2, r=1.0) if dotted else ""
    if dotted:
        out += "".join(draw.dotted(s.scaled(scale, dx, dy), spacing=3.0, r=0.9) for s in sh.strokes[1:])
        out += "".join(
            draw.el("circle", cx=dx + px * scale, cy=dy + py * scale, r=sh.dot_r * scale, fill=INK)
            for px, py in sh.dots
        )
    else:
        out = glyph(sh, scale, dx, dy, color=INK, width=13)
    return out + mark(kind, cx, my, 6.5 if dotted else 5.0, color, dotted)


@page_type("journey-harakat")
def harakat(ctx: PageContext) -> Built:
    """Meet a haraka: its name and mark, then three letters carrying it (read them, trace one), or the
    sukun on short words to read."""
    params = ctx.page.params
    kind = str(params.get("haraka", "fatha"))
    sign, name, _ = HARAKAT[kind]
    letters = [str(c) for c in params.get("letters", [])]
    examples = [str(e) for e in params.get("examples", [])]
    problems = [] if ctx.page.audio else ["a harakat page carries an audio QR"]
    body = [card(0, 0, W, 46, r=10, fill=SOFT, stroke="none")]
    body.append(text(name, W - 40, 30, 12, cls="wb-title", color=ctx.style.deep))
    body.append(mark(kind, 60, 26, 14, ctx.style.color))
    body.append(text("ـ" + sign, 30, 34, 16, cls="wb-word", color=ctx.style.color))
    if kind == "sukun" or not letters:
        _size, step = 40.0, W / max(len(examples), 1)
        for k, ex in enumerate(examples):
            cx = W - step * (k + 0.5)
            body.append(card(cx - step / 2 + 4, 60, step - 8, 70, r=8))
            body.append(text(ex, cx, 108, 22, cls="wb-word", color="#1C2140"))
        body.append(card(0, 140, W, 60, r=8))
        body.append(text("أَقْرَأُ ثُمَّ أَكْتُبُ:", W - 8, 154, 5.2, cls="wb-label", color="#676B83", anchor="end"))
        body.append(draw.path(f"M{W - 8} 190 L8 190", stroke=LINE, width=0.9))
        return Built({"svg": svg(body), "qr_note": QR_NOTE}, ["يقرأ: " + "، ".join(examples)], problems)
    pitch = (H - 52) / len(letters)
    for i, char in enumerate(letters):
        y = 52 + i * pitch
        body.append(card(0, y, W, pitch - 5, r=8))
        body.append(card(W - 46, y + 4, 42, pitch - 13, r=6, fill=ctx.style.tint, stroke="none"))
        body.append(with_mark(char, kind, W - 44, y + 4, 38, pitch - 13, ctx.style.color))
        ex = examples[i] if i < len(examples) else char + sign
        body.append(text(ex, W - 66, y + pitch / 2 + 6, 16, cls="wb-word", color="#1C2140"))
        for k in range(2):
            body.append(
                with_mark(char, kind, W - 100 - k * 36, y + 4, 32, pitch - 13, ctx.style.color, dotted=True)
            )
        body.append(draw.start_dot((W - 100 + 4, y + 10), 1.6))
    return Built({"svg": svg(body), "qr_note": QR_NOTE}, ["يقرأ: " + "، ".join(examples)], problems)


def _word_start(word_id: str, syllable: str) -> bool:
    w = PICTURES[word_id].word_ar
    core = strip_tashkeel(syllable)
    return w.startswith(core) and (len(syllable) < 2 or syllable[1] in w[1:3])


@page_type("journey-syllables")
def syllables(ctx: PageContext) -> Built:
    """Read a syllable and join it to a picture whose name starts with it; or build a word from its syllables
    (`build`: «قَ + مَ + رْ = قَمَر») and trace the word."""
    params = ctx.page.params
    problems = [] if ctx.page.audio else ["a syllables page carries an audio QR"]
    builds = [str(b) for b in params.get("build", [])]
    if builds:
        body, key = [], []
        pitch = H / len(builds)
        ch, size = pitch - 4, min(pitch - 18, 44.0)
        area = W - size - 30  # the syllables and the dotted word sit left of the picture
        for i, b in enumerate(builds):
            parts, _, result = b.partition("=")
            result = result.strip()
            y = i * pitch
            body.append(card(0, y + 1, W, ch, r=8))
            word_id = next(
                (p.id for p in PICTURES.values() if strip_tashkeel(p.word_ar) == strip_tashkeel(result)), None
            )
            if word_id:
                body.append(picture(word_id, W - 10 - size, y + 1 + (ch - size) / 2, size))
            body.append(
                text(parts.strip(), 6 + area - 4, y + 19, 12, cls="wb-word", color="#1C2140", anchor="end")
            )
            body.append(
                text("= " + result, 12, y + 19, 12.5, cls="wb-word", color=ctx.style.deep, anchor="start")
            )
            letters = spell(result)
            cap = word_cap(letters, area, ch - 30)
            row, _height = row_svg(
                arabic_name_row(
                    letters, area, cap, first=i == 0 and ctx.page.example, mode="dotted", number=ctx.num
                ),
                6,
                y + 25,
            )
            body.append(row)
            key.append(result)
        return Built({"svg": svg(body), "qr_note": QR_NOTE}, ["الكلمات: " + "، ".join(key)], problems)
    examples = [str(e) for e in params.get("examples", [])]
    matches = [pid(str(w)) for w in params.get("pictures", [])]
    if len(matches) != len(examples):
        problems.append("one picture per syllable")
        matches = (matches + ["apple"] * len(examples))[: len(examples)]
    problems += [
        f"{PICTURES[w].word_ar} does not start with {s}"
        for s, w in zip(examples, matches, strict=True)
        if not _word_start(w, s)
    ]
    order = list(range(len(examples)))
    shuffler = ctx.rng("syllables")
    while order == list(range(len(examples))):
        shuffler.shuffle(order)
    body = join_columns(
        lambda i, x, y, s: text(
            examples[i], x + s / 2, y + s * 0.72, s * 0.7, cls="wb-word", color="#1C2140"
        ),
        lambda j, x, y, s: picture(matches[order[j]], x, y, s),
        len(examples),
        [order.index(i) for i in range(len(examples))],
    )
    key = [f"{s} ← {PICTURES[w].word_ar}" for s, w in zip(examples, matches, strict=True)]
    return Built({"svg": svg(body), "qr_note": QR_NOTE}, key, problems)


# ---- reading and writing words (§4.9), English words and sentences (§4.11) ----------------------------


def _picture_for(word: str) -> str | None:
    bare = strip_tashkeel(word)
    for p in PICTURES.values():
        if strip_tashkeel(p.word_ar) == bare or p.word_en.lower() == word.lower():
            return p.id
    return None


@page_type("journey-word-read")
def word_read(ctx: PageContext) -> Built:
    """Read vowelised words (or English words) and join each to its picture; with `picture_words` the word
    sits over its line-art picture to colour."""
    params = ctx.page.params
    words = [str(w) for w in params.get("words", [])]
    en = ctx.page.lang == "en"
    ids = [_picture_for(w) for w in words]
    problems = [f"no picture for «{w}»" for w, i in zip(words, ids, strict=True) if i is None]
    found = [i or "apple" for i in ids]
    if params.get("picture_words"):
        body = []
        cols = 2
        size = 62.0
        for k, (w, i) in enumerate(zip(words, found, strict=True)):
            r, c = divmod(k, cols)
            x, y = W / 2 + 6 - c * (size + 24) + (size + 24) / 2 - size / 2 - 6, 4 + r * (size + 34)
            x = W - 16 - (c + 1) * (size + 16) + 8
            body.append(card(x - 4, y - 2, size + 8, size + 30, r=8))
            body.append(text(w, x + size / 2, y + 14, 10, cls="wb-word", color=ctx.style.deep))
            body.append(picture(i, x, y + 18, size, "line"))
            body.append(picture(i, x, y + 18, size).replace("<svg", '<svg class="key-ring"', 1))
        return Built({"svg": svg(body)}, ["الكلمات: " + "، ".join(words)], problems)
    order = list(range(len(words)))
    shuffler = ctx.rng("read")
    while order == list(range(len(words))) and len(words) > 1:
        shuffler.shuffle(order)
    size_cls = "wb-en" if en else "wb-word"
    columns = (
        join_columns_ltr if en else join_columns
    )  # English reads left to right: words left, pictures right
    body = columns(
        lambda i, x, y, s: text(
            words[i],
            x + s / 2,
            y + s * 0.68,
            s * (0.42 if en else 0.5),
            cls=size_cls,
            color="#1C2140",
            rtl=not en,
        ),
        lambda j, x, y, s: picture(found[order[j]], x, y, s),
        len(words),
        [order.index(i) for i in range(len(words))],
    )
    key = [
        f"{w} ← {PICTURES[i].word_en if en else PICTURES[i].word_ar}"
        for w, i in zip(words, found, strict=True)
    ]
    return Built({"svg": svg(body)}, key, problems)


def _room_units(letters: list[Letter]) -> float:
    """The writing band of a word in the letters' units: from the highest mark (a hamza) down to the
    descender line."""
    g = letters[0].guides
    low = g.low if g.low is not None else g.base
    above = max(0.0, max(g.top - letter_extent(x)[1] for x in letters))
    return above + (low - g.top)


def word_cap(letters: list[Letter], width: float, row_height: float, most: float = 26.0) -> float:
    """The cap height (mm) at which the word fits a writing row `width` wide and `row_height` tall."""
    g = letters[0].guides
    units = sum(x.width for x in letters)
    by_width = (width - 16) / units * (g.base - g.top)
    by_height = (row_height - 9) / _room_units(letters) * (g.base - g.top)
    return max(8.0, min(most, by_width, by_height))


@page_type("journey-word-write")
def word_write(ctx: PageContext) -> Built:
    """Write words, each beside its picture: trace the dotted word then write it once on the line under
    it (`dotted`), copy the model word on a line (`on-line`), or write the picture's name alone
    (`independent`)."""
    params = ctx.page.params
    words = [str(w) for w in params.get("words", [])]
    mode = str(params.get("mode", "dotted"))
    pitch = H / max(len(words), 1)
    ch = pitch - 4
    pic = min(ch - 14, 46.0)
    area = W - pic - 30  # the writing rows sit left of the picture
    body, key, problems = [], [], []
    for i, w in enumerate(words):
        y = i * pitch
        body.append(card(0, y + 1, W, ch, r=8))
        pic_id = _picture_for(w)
        if pic_id:
            body.append(picture(pic_id, W - 10 - pic, y + 1 + (ch - pic) / 2, pic))
        else:
            problems.append(f"no picture for «{w}»")
        letters = spell(w)
        if mode == "dotted":
            cap = word_cap(letters, area, (ch - 6) / 2)
            row1, h1 = row_svg(
                arabic_name_row(letters, area, cap, first=True, mode="dotted", number=ctx.num), 6, y + 4
            )
            row2, _ = row_svg(
                arabic_name_row(letters, area, cap, first=False, mode="empty", number=ctx.num),
                6,
                y + 5 + h1,
            )
            body += [row1, row2]
        elif mode == "on-line":
            model = max(12.0, min(18.0, ch / 5.5))
            body.append(
                text(w, 6 + area - 6, y + 4 + model, model, cls="wb-word", color=ctx.style.deep, anchor="end")
            )
            cap = word_cap(letters, area, ch - model - 12)
            row, _ = row_svg(
                arabic_name_row(letters, area, cap, first=False, mode="empty", number=ctx.num),
                6,
                y + model + 9,
            )
            body.append(row)
        else:
            cap = word_cap(letters, area, ch - 12)
            empty = arabic_name_row(letters, area, cap, first=False, mode="empty", number=ctx.num)
            _, row_h = row_svg(empty, 0, 0)
            top_y = y + 1 + (ch - row_h) / 2
            row, _ = row_svg(empty, 6, top_y)
            body.append(row)  # writing lines as large as the card allows; the answer shows in the key only
            g = letters[0].guides
            above = max(0.0, max(g.top - letter_extent(x)[1] for x in letters))
            base_y = top_y + 5 + (above + g.base - g.top) * cap / (g.base - g.top)
            body.append(
                text(
                    w, 6 + area - 6, base_y, cap * 0.7, cls="wb-word key-ring", color="#E0483A", anchor="end"
                )
            )
        key.append(w)
    return Built({"svg": svg(body)}, ["الكلمات: " + "، ".join(key)], problems)


def _deranged(order: list[int], rng: object) -> list[int]:
    """`order` shuffled so that no item keeps its place (when there are at least two)."""
    out = list(order)
    for _ in range(60):
        rng.shuffle(out)  # type: ignore[attr-defined]
        if len(out) < 2 or all(a != b for a, b in zip(out, order, strict=True)):
            break
    return out


@page_type("journey-match-letters")
def match_letters(ctx: PageContext) -> Built:
    """A review that joins letters to pictures. Arabic (right to left): each letter to the picture of a word
    that starts with it, and the picture to its written word. English (left to right): `A a` to the picture
    of a word that starts with it, in two cards of four."""
    params = ctx.page.params
    en = ctx.page.lang == "en"
    letters = [str(c) for c in params.get("letters", [])]
    words = [str(w) for w in params.get("words", [])]
    ids = [_picture_for(w) for w in words]
    problems = [f"no picture for «{w}»" for w, i in zip(words, ids, strict=True) if i is None]
    problems += [] if len(letters) == len(words) else ["one word for each letter"]
    pics = [i or "apple" for i in ids]
    for c, i in zip(letters, pics, strict=False):
        ok = PICTURES[i].word_en[:1].upper() == c.upper() if en else starts_with(i, c)
        problems += (
            [] if ok else [f"{PICTURES[i].word_en if en else PICTURES[i].word_ar} does not start with {c}"]
        )
    n, rng = len(letters), ctx.rng("match-letters")
    body: list[str] = []
    key: list[str] = []
    if en:
        groups = [list(range(0, n // 2)), list(range(n // 2, n))]
        for g, members in enumerate(groups):
            top, height = g * 104.0, 98.0
            body.append(card(0, top, W, height, r=10, fill="#FFFFFF"))
            pitch = height / len(members)
            order = _deranged(list(range(len(members))), rng)  # the picture in each row of the right column
            for r, idx in enumerate(members):
                cy = top + (r + 0.5) * pitch
                body.append(
                    card(8, cy - pitch / 2 + 3, 44, pitch - 6, r=6, fill=ctx.style.tint, stroke="none")
                )
                body.append(
                    text(
                        f"{letters[idx]} {letters[idx].lower()}",
                        30,
                        cy + 4,
                        min(pitch * 0.4, 11.0),
                        cls="wb-en",
                        color=ctx.style.deep,
                        rtl=False,
                    )
                )
                body.append(hook(60, cy, 2.2))
                size = min(pitch - 8, 26.0)
                body.append(card(W - 8 - 44, cy - pitch / 2 + 3, 44, pitch - 6, r=6, fill="#FFFFFF"))
                body.append(picture(pics[members[order[r]]], W - 8 - 22 - size / 2, cy - size / 2, size))
                body.append(hook(W - 60, cy, 2.2))
            for r in range(len(members)):
                target = order.index(r)
                body.append(
                    answer_line((60, top + (r + 0.5) * pitch), (W - 60, top + (target + 0.5) * pitch))
                )
            key += [f"{letters[i]} {letters[i].lower()} ← {PICTURES[pics[i]].word_en}" for i in members]
        return Built({"svg": svg(body)}, key, problems)
    pitch = H / max(n, 1)
    order = _deranged(list(range(n)), rng)  # the picture in each row of the middle column
    names = _deranged(order, rng)  # the word in each row of the left column
    size = min(pitch - 12, 34.0)
    for r in range(n):
        cy = (r + 0.5) * pitch
        shape_ = shape(letters[r])
        body.append(card(W - 36, cy - pitch / 2 + 3, 34, pitch - 6, r=7, fill=ctx.style.tint, stroke="none"))
        body.append(
            glyph(
                shape_,
                *fit_lines(shape_, W - 33, cy - pitch / 2 + 6, 28, pitch - 12),
                color=ctx.style.deep,
                width=14,
            )
        )
        body.append(card(76, cy - pitch / 2 + 3, 36, pitch - 6, r=7))
        body.append(picture(pics[order[r]], 94 - size / 2, cy - size / 2, size))
        word = words[names[r]]
        body.append(card(2, cy - pitch / 2 + 3, 40, pitch - 6, r=7))
        body.append(
            text(PICTURES[pics[names[r]]].word_ar, 22, cy + 3.5, 8.6, cls="wb-word", color=ctx.style.deep)
        )
        body += [hook(W - 40, cy, 2.2), hook(114, cy, 2.2), hook(74, cy, 2.2), hook(44, cy, 2.2)]
        del word
    for r in range(n):
        j = order.index(r)  # the row whose picture belongs to letter r
        k = names.index(order[j])  # the row whose word names that picture
        body.append(answer_line((W - 40, (r + 0.5) * pitch), (114, (j + 0.5) * pitch)))
        body.append(answer_line((74, (j + 0.5) * pitch), (44, (k + 0.5) * pitch)))
        key.append(f"{letters[r]} ← {PICTURES[pics[r]].word_ar}")
    return Built({"svg": svg(body)}, key, problems)


@page_type("journey-sentence-read")
def sentence_read(ctx: PageContext) -> Built:
    """Very short English sentences (§4.11), each joined to the picture it describes; `pictures` lists the
    picture ids in the sentences' order."""
    sentences = [str(s) for s in ctx.page.params.get("sentences", [])]
    ids = [pid(str(p)) for p in ctx.page.params.get("pictures", [])]
    problems = [] if len(ids) == len(sentences) else ["one picture per sentence"]
    problems += [] if ctx.page.audio else ["a sentence page carries an audio QR"]
    ids = (ids + ["cat"] * len(sentences))[: len(sentences)]
    order = list(range(len(sentences)))
    shuffler = ctx.rng("sentences")
    while order == list(range(len(sentences))) and len(sentences) > 1:
        shuffler.shuffle(order)
    pitch = H / max(len(sentences), 1)
    size = min(pitch - 14, 38.0)
    left_hook, right_hook = 92.0, W - size - 26  # about 34 mm between the hooks: the lines are easy to draw
    body = []
    for i, sentence in enumerate(sentences):
        y = i * pitch + pitch / 2
        body.append(card(4, y - 18, 80, 36, r=8))
        body.append(text(sentence, 10, y + 3.4, 7.2, cls="wb-en", color="#1C2140", anchor="start", rtl=False))
        body.append(hook(left_hook, y, 2.2))
        body.append(card(W - size - 20, y - size / 2 - 4, size + 14, size + 8, r=8, fill=SOFT, stroke="none"))
        body.append(picture(ids[order[i]], W - size - 13, y - size / 2, size))
        body.append(hook(right_hook, y, 2.2))
    for i in range(len(sentences)):
        j = order.index(i)
        body.append(answer_line((left_hook, i * pitch + pitch / 2), (right_hook, j * pitch + pitch / 2)))
    key = [f"{s} → {PICTURES[i].word_en}" for s, i in zip(sentences, ids, strict=True)]
    return Built(
        {"svg": svg(body), "qr_note": "For parents: scan to hear the sentences, or read them aloud."},
        key,
        problems,
    )


ALPHABET_AR = tuple("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")


@page_type("journey-alphabet")
def alphabet(ctx: PageContext) -> Built:
    """The whole Arabic alphabet to sing and colour (`song`, with a QR), or an English alphabet train with
    missing letters to write (`from`, `to`, `missing`)."""
    params = ctx.page.params
    body: list[str] = []
    if params.get("song"):
        problems = [] if ctx.page.audio else ["the alphabet song page carries an audio QR"]
        cols, rows_, cw, ch = 6, 5, 28.0, 31.0
        gap_x = (W - cols * cw) / (cols + 1)
        shapes = [shape("أ" if c == "ا" else c) for c in ALPHABET_AR]
        scale = min(fit(sh, 0, 0, cw - 3, ch - 4, pad=1.0)[0] for sh in shapes)  # one size for every letter
        for k, sh in enumerate(shapes):
            r, c = divmod(k, cols)
            x, y = W - gap_x - (c + 1) * cw - c * gap_x, 2 + r * (ch + 2)
            body.append(card(x, y, cw, ch, r=4))
            x0, y0, x1, y1 = letter_extent(sh)
            dx = x + (cw - (x1 - x0) * scale) / 2 - x0 * scale
            dy = y + (ch - (y1 - y0) * scale) / 2 - y0 * scale
            body.append(glyph(sh, scale, dx, dy, edge=INK, fill="#FFFFFF", width=24))
        below = 2 + rows_ * (ch + 2) + 2  # the song's box under the letters
        body.append(card(0, below, W, H - below, r=10, fill=SOFT, stroke="none"))
        body.append(
            text(
                "أُغَنّي الحُروفَ مِنَ الأَلِفِ إِلى الياءِ وَأُلَوِّنُ ما أَعْرِفُهُ",
                W / 2,
                below + (H - below) / 2 + 2.4,
                6.5,
                cls="wb-title",
                color="#1C2140",
            )
        )
        return Built({"svg": svg(body), "qr_note": QR_NOTE}, ["الحروف الثمانية والعشرون"], problems)
    start, end = str(params.get("from", "A")).upper(), str(params.get("to", "T")).upper()
    missing = {str(m).upper() for m in params.get("missing", [])}
    letters = [chr(c) for c in range(ord(start), ord(end) + 1)]
    cols, size = 5, 30.0
    pitch = (H - 8) / ((len(letters) + cols - 1) // cols)
    for r in range((len(letters) + cols - 1) // cols):  # a track under each row of wagons
        body.append(
            draw.path(
                f"M4 {4 + r * pitch + size + 7} L{W - 4} {4 + r * pitch + size + 7}",
                stroke="#8C90A6",
                width=1.2,
            )
        )
    for k, char in enumerate(letters):
        r, c = divmod(k, cols)
        x, y = 4 + c * (size + 6), 4 + r * pitch + 2
        blank = char in missing
        body.append(
            card(
                x,
                y,
                size,
                size,
                r=4,
                fill="#FFFFFF",
                stroke="#8C90A6" if blank else "#E27D63",
                dash="3 2" if blank else "none",
            )
        )
        body += [
            draw.el("circle", cx=x + size * f, cy=y + size + 3, r=2.6, fill="#3D4262") for f in (0.3, 0.7)
        ]
        cls = "wb-en key-ring" if blank else "wb-en"
        body.append(
            text(
                char,
                x + size / 2,
                y + size * 0.72,
                size * 0.62,
                cls=cls,
                color="#E0483A" if blank else "#1C2140",
                rtl=False,
            )
        )
    return Built({"svg": svg(body)}, ["Missing: " + ", ".join(sorted(missing))], [])


@page_type("journey-finger-trace")
def journey_finger_trace(ctx: PageContext) -> Built:
    """The دوسية's finger-trace page drawn from `arabic_shape`, so أ (the alif with its hamza) works too."""
    from qamra_workbook.render.pages.letters import highlight_first

    params = ctx.page.params
    char = str(params.get("letter", "ب"))
    # a finger traces the plain alif: the hamza of أ is a small mark for the pen pages that follow
    sh = shape("ا" if char in "أإآ" else char, str(params.get("form", "isolated")))
    word = pid(str(params.get("word", "duck")))
    pic = PICTURES[word]
    problems = [] if starts_with(word, char) else [f"{pic.word_ar} does not start with {char}"]
    if not ctx.page.audio:
        problems.append("a finger-trace page carries an audio QR (the letter's sound)")
    body, box = finger_letter(sh, fill="#F7C84A", edge=ctx.style.deep, width=20, number=ctx.num)
    view = " ".join(draw.n(v) for v in box)
    letter_svg = Markup(f'<svg class="finger" viewBox="{view}" aria-hidden="true">{body}</svg>')  # nosec B704
    data = {
        "letter": letter_svg,
        "char": char,
        "pic": ctx.pic(word),
        "word": highlight_first(pic.word_ar, ctx.style.color),
    }
    return Built(data, None, problems)
