"""«دوسية التأسيس» Volume 2: the letter at the beginning, middle and end of a word (letter-position), and the
position words above/below, inside/outside, in front/behind, right/left (the plan's position-words,
registered as `place-words`: the journey book owns the other name) (Addendum 5 §3).

Words are written in Qamra's hand from the committed letter paths (`workbook_front.spell`), so the child sees
the same shapes they trace. Every page carries an answer key and checks that each word holds the letter.
"""

from __future__ import annotations

from qamra_workbook.letters import placed
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures import PICTURES
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.pages.letters import letter_extent
from qamra_workbook.render.pages.workbook_arabic import same_letter
from qamra_workbook.render.pages.workbook_common import (
    INK,
    W,
    arabic_shape,
    card,
    fit_lines,
    glyph,
    pic,
    picture_id,
    ring_at,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_front import spell
from qamra_workbook.render.pages.workbook_review import compact
from qamra_workbook.render.registry import Built, PageContext, page_type

POSITIONS = ("أَوَّل", "وَسَط", "آخِر")
FORMS = ("initial", "medial", "final")


def word_shapes(word: str) -> list[Letter]:
    return spell(strip_tashkeel(word))


def written_word(
    letters: list[Letter], right: float, y: float, h: float, *, color: dict[int, str] | None = None
) -> tuple[str, list[tuple[float, float, float]]]:
    """The word written right to left, box to box, its band (top line to tail line) `h` mm tall with its right
    edge at `right`. Returns the SVG and, per letter, (centre x, centre y, half width) for rings."""
    g = letters[0].guides
    low = g.low if g.low is not None else g.base
    scale = h / (low - g.top)
    xs, total = placed(letters, gap=12.0)
    out, boxes = [], []
    for i, (shape, x) in enumerate(zip(letters, xs, strict=True)):
        dx, dy = right - total * scale + x * scale, y - g.top * scale
        out.append(glyph(shape, scale, dx, dy, color=(color or {}).get(i, INK), width=13))
        x0, y0, x1, y1 = letter_extent(shape)
        boxes.append((dx + (x0 + x1) / 2 * scale, dy + (y0 + y1) / 2 * scale, max(x1 - x0, 60) / 2 * scale))
    return "".join(out), boxes


def position_of(letters: list[Letter], target: str) -> int | None:
    hits = [i for i, x in enumerate(letters) if same_letter(x.char, target)]
    if not hits:
        return None
    i = hits[0]
    return 0 if i == 0 else 2 if i == len(letters) - 1 else 1


@page_type("letter-position")
def letter_position(ctx: PageContext) -> Built:
    params = ctx.page.params
    targets = [str(x) for x in params.get("letters", [])]
    words = [str(w) for w in params.get("words", [])]
    color = ctx.style.color
    body, answer, problems = [], [], []
    # the forms: each target letter at the beginning, in the middle and at the end
    head_h = 12 + 16 * len(targets)
    body.append(card(0, 0, W, head_h, r=7, fill=ctx.style.tint, stroke="none"))
    for k, label in enumerate(("في الأَوَّلِ", "في الوَسَطِ", "في الآخِرِ")):
        body.append(text(label, W - 50 - k * 44, 8.5, 4.6, color=ctx.style.deep))
    for i, t in enumerate(targets):
        y = 12.0 + i * 16
        shape = arabic_shape(t)
        body.append(glyph(shape, *fit_lines(shape, W - 22, y + 1, 14, 14), color=ctx.style.deep, width=14))
        for k, form in enumerate(FORMS):
            # inside and at the end of a word the alif is plain «ـا» (باب، حذاء), never «ـأ»
            shown = "ا" if t in "أإآ" and form != "initial" else t
            try:
                part = arabic_shape(shown, form)
            except KeyError:
                part = arabic_shape(shown, "isolated" if form == "initial" else "final")
            body.append(glyph(part, *fit_lines(part, W - 60 - k * 44, y, 20, 15), color=INK, width=13))
    top = float(head_h + 4)
    pitch = (204 - top) / max(len(words), 1)
    for i, word in enumerate(words):
        y = top + i * pitch
        letters = word_shapes(word)
        target = next((t for t in targets if position_of(letters, t) is not None), None)
        if target is None:
            problems.append(f"«{word}» holds none of {targets}")
            continue
        hit = next(j for j, x in enumerate(letters) if same_letter(x.char, target))
        where = position_of(letters, target)
        body.append(card(0, y + 1, W, pitch - 3, r=6))
        size = min(pitch - 7, 24.0)
        body.append(pic(picture_id(word), W - size - 4, y + (pitch - 3) / 2 - size / 2 + 1, size))
        band = min(pitch - 9, 20.0)
        written, boxes = written_word(
            letters, W - size - 12, y + (pitch - 3) / 2 - band / 2 + 1, band, color={hit: color}
        )
        body.append(written)
        cx, cy, half = boxes[hit]
        body.append(ring_at(cx, cy, half + 2, band / 2 + 1))
        for k, label in enumerate(POSITIONS):
            bx = 8 + (len(POSITIONS) - 1 - k) * 20  # «أَوَّل» on the right, as the word is read
            body.append(
                draw.el(
                    "rect",
                    x=bx,
                    y=y + pitch / 2 - 8,
                    width=14,
                    height=12,
                    rx=2.5,
                    fill="#FFFFFF",
                    stroke="#B8B2A6",
                    stroke_width=0.5,
                )
            )
            body.append(text(label, bx + 7, y + pitch / 2 + 9, 3.4, color="#676B83"))
            if k == where:
                body.append(
                    draw.path(
                        draw.d_path(
                            ("M", (bx + 3, y + pitch / 2 - 2)),
                            ("L", (bx + 6, y + pitch / 2 + 1)),
                            ("L", (bx + 11, y + pitch / 2 - 6)),
                        ),
                        stroke="#E0483A",
                        width=1.1,
                        class_="key-line",
                    )
                )
        answer.append(f"{PICTURES[picture_id(word)].word_ar}: {POSITIONS[where or 0]}")
    return Built({"svg": svg(body)}, compact(answer, 60), problems)


RED, BLUE_ = "#E5604E", "#5E86D6"
CONCEPT_AR = {
    "above-below": ("فوق", "تحت"),
    "inside-outside": ("داخل", "خارج"),
    "front-behind": ("أمام", "خلف"),
    "right-left": ("يمين", "يسار"),
}


def _crayon_legend(x: float, y: float, first: str, second: str) -> str:
    """«الأحمر: فوق · الأزرق: تحت» as two colour dots with their words."""
    return "".join(
        (
            draw.el("circle", cx=x - 4, cy=y, r=3.2, fill=RED),
            text(first, x - 10, y + 1.6, 4.2, anchor="end", color=INK),
            draw.el("circle", cx=x - 42, cy=y, r=3.2, fill=BLUE_),
            text(second, x - 48, y + 1.6, 4.2, anchor="end", color=INK),
        )
    )


def above_below(ctx: PageContext, y0: float, h: float) -> tuple[list[str], list[str]]:
    """A table with things on it and under it, to colour red (above) and blue (below)."""
    body = [card(0, y0, W, h, r=7), _crayon_legend(W - 6, y0 + 8, "فَوْقَ", "تَحْتَ")]
    top, size = y0 + 14, min(h - 20, 74.0)
    tx = W / 2 - size * 0.7
    body.append(pic("table", tx, top, size * 1.4, "color"))
    on = ("cat", "ball")
    under = ("dog", "basket")
    small = size * 0.36
    for k, thing in enumerate(on):
        body.append(pic(thing, tx + size * 0.35 + k * size * 0.4, top + size * 0.34 - small, small, "line"))
    for k, thing in enumerate(under):
        body.append(pic(thing, tx + size * 0.4 + k * size * 0.36, top + size * 0.58, small, "line"))
    answer = [
        "فوق الطاولة (أحمر): " + "، ".join(PICTURES[t].word_ar for t in on),
        "تحت الطاولة (أزرق): " + "، ".join(PICTURES[t].word_ar for t in under),
    ]
    return body, answer


def inside_outside(ctx: PageContext, y0: float, h: float) -> tuple[list[str], list[str]]:
    """An open crate: circle what is inside, underline what is outside."""
    body = [card(0, y0, W, h, r=7)]
    body.append(
        text(
            "أُحَوِّطُ ما داخِلَ الصُّنْدوقِ، وَأَضَعُ خَطًّا تَحْتَ ما خارِجَهُ",
            W - 6,
            y0 + 8,
            4.4,
            anchor="end",
            color=ctx.style.deep,
        )
    )
    cx, cy, bw, bh = W / 2, y0 + h / 2 + 6, 70.0, 34.0
    body.append(
        draw.el(
            "rect",
            x=cx - bw / 2,
            y=cy - bh / 2 - 8,
            width=bw,
            height=bh,
            rx=3,
            fill="#CFA872",
            stroke=INK,
            stroke_width=0.8,
        )
    )
    inside = ("apple", "duck")
    outside = ("car", "star")
    size = 22.0
    for k, thing in enumerate(inside):
        body.append(pic(thing, cx - 26 + k * 30, cy - bh / 2 - 12, size))
        body.append(
            ring_at(cx - 26 + k * 30 + size / 2, cy - bh / 2 - 12 + size / 2, size / 2 + 2, size / 2 + 2)
        )
    body.append(
        draw.el(
            "rect",
            x=cx - bw / 2,
            y=cy - 2,
            width=bw,
            height=bh / 2 + 8,
            rx=3,
            fill="#E6C28E",
            stroke=INK,
            stroke_width=0.8,
        )
    )
    for k, thing in enumerate(outside):
        x = cx - bw / 2 - 34 if k == 0 else cx + bw / 2 + 10
        body.append(pic(thing, x, cy + 4, size))
        body.append(
            draw.path(
                draw.d_path(("M", (x, cy + size + 8)), ("L", (x + size, cy + size + 8))),
                stroke="#E0483A",
                width=1.1,
                class_="key-line",
            )
        )
    answer = [
        "داخل الصندوق: " + "، ".join(PICTURES[t].word_ar for t in inside),
        "خارجه: " + "، ".join(PICTURES[t].word_ar for t in outside),
    ]
    return body, answer


def front_behind(ctx: PageContext) -> tuple[list[str], list[str]]:
    """Three rows: something in front of a tree or house (whole), something behind it (half hidden)."""
    body, answer = [], []
    r = ctx.rng("front")
    scenes = [("tree", "rabbit", "bear"), ("house", "cat", "dog"), ("tree", "duck", "sheep")]
    for i, (big, front, behind) in enumerate(scenes):
        y = i * 68
        body.append(card(0, y + 1, W, 64, r=7))
        body.append(
            text(
                "أُحَوِّطُ ما أَمامَ " + ("الشَّجَرَةِ" if big == "tree" else "البَيْتِ"),
                W - 6,
                y + 9,
                4.4,
                anchor="end",
                color=ctx.style.deep,
            )
        )
        cx = W / 2 + r.choice((-20, 20))
        body.append(pic(behind, cx + 14, y + 22, 26))  # peeks out from behind
        body.append(pic(big, cx - 24, y + 10, 52))
        body.append(pic(front, cx - 30, y + 36, 24))
        body.append(ring_at(cx - 18, y + 48, 15, 14))
        answer.append(
            f"الصف {ctx.num(i + 1)}: {PICTURES[front].word_ar} أمام، {PICTURES[behind].word_ar} خلف"
        )
    return body, answer


def right_left(ctx: PageContext) -> tuple[list[str], list[str]]:
    """The two hands on top, then rows with something on the right and the left of a thing in the middle."""
    body = [card(0, 0, W, 44, r=7, fill=ctx.style.tint, stroke="none")]
    body.append(pic("hand", W - 44, 4, 36))
    body.append(text("يَدي اليُمْنى", W - 26, 43, 4.2, color=ctx.style.deep))
    mirrored = '<g transform="translate(100 0) scale(-1 1)">' + PICTURES["hand"].inner("color") + "</g>"
    body.append(draw.el("svg", mirrored, x=8, y=4, width=36, height=36, viewBox="0 0 100 100"))
    body.append(text("يَدي اليُسْرى", 26, 43, 4.2, color=ctx.style.deep))
    body.append(_crayon_legend(W - 6, 54, "يَمين", "يَسار"))
    rows = [("house", "cat", "ball"), ("tree", "bird", "rabbit"), ("car", "duck", "flower")]
    answer = []
    for i, (mid, right, left) in enumerate(rows):
        y = 60 + i * 48
        body.append(card(0, y, W, 44, r=6))
        body.append(pic(mid, W / 2 - 17, y + 5, 34))
        body.append(pic(right, W / 2 + 34, y + 9, 26, "line"))
        body.append(pic(left, W / 2 - 60, y + 9, 26, "line"))
        answer.append(f"يمين: {PICTURES[right].word_ar}، يسار: {PICTURES[left].word_ar}")
    return body, answer


@page_type("place-words")
def position_words(ctx: PageContext) -> Built:
    raw = ctx.page.params.get("concept", "above-below")
    concepts = [str(c) for c in (raw if isinstance(raw, list) else [raw])]
    body: list[str] = []
    answer: list[str] = []
    problems: list[str] = []
    if concepts == ["front-behind"]:
        body, answer = front_behind(ctx)
    elif concepts == ["right-left"]:
        body, answer = right_left(ctx)
    else:
        h = (204 - 4 * (len(concepts) - 1)) / len(concepts)
        for k, concept in enumerate(concepts):
            part = above_below if concept == "above-below" else inside_outside
            drawn, lines = part(ctx, k * (h + 4), h)
            body += drawn
            answer += lines
    unknown = [c for c in concepts if c not in CONCEPT_AR]
    if unknown:
        problems.append(f"unknown position concept {unknown}")
    return Built({"svg": svg(body)}, compact(answer), problems)
