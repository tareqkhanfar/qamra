"""Journey listening pages (Addendum 6 §4.8) and the first English words (§4.11 in stage 1). Each page prints
a QR to its audio item (`BookSpec.audio_url`); the rows are numbered with dots in the order the audio plays,
and every page still works without audio: the parent reads the words or makes the sounds."""

from __future__ import annotations

from typing import Any

from qamra_workbook.pictures import PICTURES
from qamra_workbook.pictures.journey_words import COLORS
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_kit import H, W, card, dots_mark, picture, pid, svg, text
from qamra_workbook.render.pages.workbook_common import ring_at
from qamra_workbook.render.registry import Built, PageContext, page_type

QR_NOTE = "للأهل: امسحوا الرمز بالهاتف ليسمع الطفل، أو اقرؤوا الكلمات بصوتكم."


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
    return Built({"svg": svg(body), "qr_note": QR_NOTE}, key, problems)


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
    return Built({"svg": svg(body), "qr_note": QR_NOTE}, key, _audio_problem(ctx))


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
    built = _two_choice_rows(ctx, rows, "same", _same, _different, ("متشابهان", "مختلفان"))
    built.answer = [
        f"{ctx.num(i + 1)}: {PICTURES[pid(a)].word_ar} و{PICTURES[pid(b)].word_ar} — "
        f"{'متشابهان' if a == b else 'مختلفان'}"
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
    body.append(text(riddle, W / 2 - 6, 40, 9.5, cls="wb-word", color="#1C2140"))
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
