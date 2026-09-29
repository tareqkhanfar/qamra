"""Journey thinking pages (Addendum 6 §4.1, §4.12): twins, memory (look, then recall on the back), what's
missing, part and whole, which belongs, picture stories and sorting. Every answer comes from the page's own
params and is checked here."""

from __future__ import annotations

from typing import Any

from qamra_workbook.pictures import PICTURES
from qamra_workbook.render import draw
from qamra_workbook.render.pages.journey_kit import (
    CUTS,
    SOFT,
    H,
    W,
    card,
    dots_mark,
    join_columns,
    nested,
    picture,
    pid,
    svg,
    text,
)
from qamra_workbook.render.pages.workbook_common import answer_line, hook, ring_at
from qamra_workbook.render.registry import Built, PageContext, page_type


def words(ctx: PageContext, key: str) -> list[str]:
    raw = ctx.page.params.get(key, [])
    return [str(w) for w in (raw if isinstance(raw, list) else [raw])]


def grid(n: int, cols: int, *, h: float = H, gap: float = 8.0) -> list[tuple[float, float, float]]:
    """Cells (x, y, size) for n pictures in rows of `cols`, right to left."""
    rows = (n + cols - 1) // cols
    size = min((W - gap * (cols + 1)) / cols, (h - gap * (rows + 1)) / rows)
    out = []
    for i in range(n):
        r, k = divmod(i, cols)
        in_row = min(cols, n - r * cols)
        x0 = (W - in_row * size - (in_row - 1) * gap) / 2
        out.append(
            (W - x0 - size - k * (size + gap), gap + r * (size + gap) + (h - rows * (size + gap)) / 2, size)
        )
    return out


def bow(cx: float, cy: float, s: float, color: str) -> str:
    wings = draw.d_path(
        ("M", (cx, cy)), ("L", (cx - s, cy - s * 0.6)), ("L", (cx - s, cy + s * 0.6)), ("Z", ())
    )
    wings += " " + draw.d_path(
        ("M", (cx, cy)), ("L", (cx + s, cy - s * 0.6)), ("L", (cx + s, cy + s * 0.6)), ("Z", ())
    )
    paint: dict[str, str | float] = {
        "fill": color,
        "stroke": "#2B2E4A",
        "stroke_width": 2.2,
        "stroke_linejoin": "round",
    }
    return draw.el("path", d=wings, **paint) + draw.el("circle", cx=cx, cy=cy, r=s * 0.3, **paint)


COLOR_HEX = {"red": "#E5604E", "blue": "#5E86D6", "yellow": "#F7C84A", "green": "#7DB46C", "pink": "#F4A6B8"}


@page_type("find-identical-pair")
def find_identical_pair(ctx: PageContext) -> Built:
    """Four versions of one picture, with a bow of a colour or none: two are the same."""
    thing = pid(str(ctx.page.params.get("picture", "cat")))
    bows = words(ctx, "bows") or ["red", "blue", "red", "none"]
    bx, by = (float(v) for v in ctx.page.params.get("bow_at", [50, 84]))
    twins = [i for i, b in enumerate(bows) if bows.count(b) == 2]
    problems = (
        [] if len(twins) == 2 and len(set(bows)) == len(bows) - 1 else ["exactly two pictures are the same"]
    )
    body = []
    for i, (x, y, size) in enumerate(grid(len(bows), 2)):
        body.append(card(x - 4, y - 4, size + 8, size + 8, r=8))
        extra = bow(bx, by, 11, COLOR_HEX.get(bows[i], bows[i])) if bows[i] != "none" else ""
        body.append(nested(PICTURES[thing].inner("color") + extra, x, y, size))
        if i in twins:
            body.append(ring_at(x + size / 2, y + size / 2, size / 2 + 2, size / 2 + 2))
    return Built(
        {"svg": svg(body)},
        [f"المتطابقتان: الصورة {ctx.num(twins[0] + 1)} والصورة {ctx.num(twins[1] + 1)}"]
        if len(twins) == 2
        else None,
        problems,
    )


@page_type("memory-look")
def memory_look(ctx: PageContext) -> Built:
    """Look and remember (the front of a sheet): big pictures, then an arrow to turn the page."""
    items = [pid(w) for w in words(ctx, "items")]
    problems = [] if 3 <= len(items) <= 6 else ["a memory page shows 3–6 pictures"]
    cols = 2 if len(items) <= 4 else 3
    body = [card(0, 0, W, H - 30, r=10, fill=SOFT, stroke="none")]
    for x, y, size in grid(len(items), cols, h=H - 30):
        body.append(card(x - 3, y - 3, size + 6, size + 6, r=8))
    body += [
        picture(w, x, y, size)
        for w, (x, y, size) in zip(items, grid(len(items), cols, h=H - 30), strict=True)
    ]
    turn = draw.d_path(
        ("M", (W / 2 + 26, H - 8)), ("C", (W / 2 + 10, H - 26, W / 2 - 14, H - 26, W / 2 - 26, H - 12))
    )
    body.append(draw.path(turn, stroke="#E27D63", width=2.4))
    body.append(draw.arrow((W / 2 - 27, H - 11), 140, 5))
    return Built({"svg": svg(body)}, None, problems)


def _previous(ctx: PageContext) -> Any:
    return next((p for p in ctx.book.pages if p.number == ctx.page.number - 1), None)


@page_type("memory-recall")
def memory_recall(ctx: PageContext) -> Built:
    """On the back: colour what you saw (`answer`: a list), or circle the one that went (`shown`: the pictures
    still there, `answer`: the missing one)."""
    choices, answer, shown = words(ctx, "choices"), words(ctx, "answer"), words(ctx, "shown")
    prev, problems = _previous(ctx), []
    if prev is not None and prev.type == "memory-look":
        seen = {pid(str(w)) for w in prev.params.get("items", [])}
        if {pid(w) for w in answer + shown} != seen:
            problems.append("the answer does not match the pictures on the front of the sheet")
    if not set(answer) <= set(choices):
        problems.append("every answer must be among the choices")
    body, top = [], 0.0
    if shown:
        top = 70.0
        body.append(card(0, 0, W, 62, r=8, fill=SOFT, stroke="none"))
        slots = [*shown, ""]
        for k, w in enumerate(slots):
            x = W - 14 - (k + 1) * 42 - k * 2
            if w:
                body.append(picture(w, x, 11, 40))
            else:
                body.append(
                    card(x, 11, 40, 40, r=6, fill="#FFFFFF", stroke="#8C90A6", dash="3 2.4", width=0.8)
                )
                body.append(text("؟", x + 20, 38, 18, cls="wb-title", color="#8C90A6"))
    style = "color" if shown else "line"
    for w, (x, y, size) in zip(choices, grid(len(choices), 3, h=H - top), strict=True):
        body.append(card(x - 3, top + y - 3, size + 6, size + 6, r=8))
        body.append(picture(w, x, top + y, size, style))
        if w in answer:
            body.append(ring_at(x + size / 2, top + y + size / 2, size / 2 + 3, size / 2 + 3))
    names = "، ".join(PICTURES[pid(w)].word_ar for w in answer)
    return Built({"svg": svg(body)}, [("اختفت: " if shown else "رأى: ") + names], problems)


@page_type("whats-missing")
def whats_missing(ctx: PageContext) -> Built:
    """Each picture misses a part (right); join it to the part (left)."""
    cuts = [CUTS[k] for k in words(ctx, "items")]
    order = list(range(len(cuts)))
    ctx.rng("missing").shuffle(order)
    answer = [order.index(i) for i in range(len(cuts))]
    body = join_columns(
        lambda i, x, y, s: cuts[i].without(x, y, s),
        lambda j, x, y, s: cuts[order[j]].piece(x, y, s),
        len(cuts),
        answer,
    )
    key = [f"{PICTURES[c.picture].word_ar}: {c.word}" for c in cuts]
    return Built({"svg": svg(body)}, key, [] if len(cuts) >= 2 else ["join at least two pictures"])


@page_type("part-to-whole")
def part_to_whole(ctx: PageContext) -> Built:
    """A piece of each picture (right); join it to the whole picture (left)."""
    cuts = [CUTS[k] for k in words(ctx, "items")]
    order = list(range(len(cuts)))
    ctx.rng("whole").shuffle(order)
    answer = [order.index(i) for i in range(len(cuts))]
    body = join_columns(
        lambda i, x, y, s: cuts[i].crop(x, y, s),
        lambda j, x, y, s: picture(cuts[order[j]].picture, x, y, s),
        len(cuts),
        answer,
    )
    key = [f"{c.word} ← {PICTURES[c.picture].word_ar}" for c in cuts]
    return Built({"svg": svg(body)}, key, [] if len(cuts) >= 2 else ["join at least two pictures"])


@page_type("belongs-to-group")
def belongs_to_group(ctx: PageContext) -> Built:
    """A group of three (a basket at the top) and three pictures: circle the one that belongs."""
    shown, choices = words(ctx, "shown"), words(ctx, "choices")
    answer = str(ctx.page.params.get("answer", ""))
    kinds = {PICTURES[pid(w)].category for w in shown}
    fits = [w for w in choices if PICTURES[pid(w)].category in kinds]
    problems = [] if len(kinds) == 1 and fits == [answer] else ["exactly one choice belongs to the group"]
    body = [card(10, 0, W - 20, 84, r=10, fill=SOFT, stroke="#E5CD9E", width=0.8)]
    label = str(ctx.page.params.get("group", ""))
    if label:
        body.append(text(label, W / 2, 14, 7, cls="wb-title", color="#8A5A08"))
    for k, w in enumerate(shown):
        body.append(picture(w, W / 2 + 48 - k * 48 - 22, 22, 48))
    body.append(draw.path(draw.d_path(("M", (W / 2, 90)), ("L", (W / 2, 104))), stroke="#E5CD9E", width=2))
    body.append(draw.arrow((W / 2, 105), 90, 5, "#E5CD9E"))
    for w, (x, y, size) in zip(choices, grid(len(choices), 3, h=H - 112), strict=True):
        body.append(card(x - 3, 112 + y - 3, size + 6, size + 6, r=8))
        body.append(picture(w, x, 112 + y, size))
        if w == answer:
            body.append(ring_at(x + size / 2, 112 + y + size / 2, size / 2 + 3, size / 2 + 3))
    return Built(
        {"svg": svg(body)}, [f"يناسب المجموعة: {PICTURES[pid(answer)].word_ar}"] if answer else None, problems
    )


OUTLINE = "#2B2E4A"
SOIL = (
    '<path d="M4 82 C24 64 76 64 96 82 L96 96 L4 96 Z" fill="#B98556" stroke="#2B2E4A" stroke-width="2.4"/>'
)


def _sprout(big: bool) -> str:
    top = 40 if big else 56
    leaves = (
        f'<path d="M50 {top + 14} C40 {top + 4} 30 {top + 8} 28 {top + 14} C36 {top + 20} 46 {top + 18} '
        f"50 {top + 14} Z M50 {top + 8} C60 {top - 2} 70 {top + 2} 72 {top + 8} C64 {top + 14} 54 {top + 12} "
        f'50 {top + 8} Z" fill="#7DB46C" stroke="#2B2E4A" stroke-width="2.2"/>'
    )
    return f'<path d="M50 74 L50 {top}" stroke="#5E9651" stroke-width="3.2" stroke-linecap="round"/>{leaves}'


def _panel(story: str, step: int) -> str:
    """One panel of a picture story, drawn in a 100-unit box."""
    if story == "seed":
        if step == 0:
            return (
                SOIL
                + '<ellipse cx="50" cy="75" rx="6" ry="4" fill="#E3B982" stroke="#2B2E4A" stroke-width="2"/>'
            )
        if step == 1:
            return SOIL + _sprout(False)
        return SOIL + PICTURES["flower"].inner("color").replace(
            "<g", '<g transform="translate(20 -2) scale(0.6)"', 1
        )
    if story == "handwash":
        if step == 0:
            return PICTURES["faucet"].inner("color")
        if step == 1:
            bubbles = "".join(
                f'<circle cx="{x}" cy="{y}" r="{r}"/>'
                for x, y, r in ((22, 30, 7), (78, 24, 9), (70, 50, 5), (30, 60, 5))
            )
            return (
                PICTURES["soap"].inner("color")
                + f'<g fill="#E3F0FB" stroke="#8EC1EC" stroke-width="1.6">{bubbles}</g>'
            )
        towel = (
            '<path d="M18 18 L82 18" stroke="#6E6A7A" stroke-width="4" stroke-linecap="round"/>'
            '<rect x="26" y="18" width="48" height="66" rx="5" fill="#8EC1EC" stroke="#2B2E4A" '
            'stroke-width="2.4"/><path d="M26 66 L74 66 M26 72 L74 72" stroke="#FFFFFF" stroke-width="3"/>'
        )
        return towel
    raise KeyError(f"no picture story {story!r} (have: seed, handwash)")


STORY_STEPS = {"seed": 3, "handwash": 3}
ORDER_WORDS = ("أولًا", "ثمّ", "أخيرًا")


@page_type("sequence-story")
def sequence_story(ctx: PageContext) -> Built:
    """Three panels out of order: the child marks the order with dots (• first, •• then, ••• last)."""
    story = str(ctx.page.params.get("story", "seed"))
    steps = STORY_STEPS.get(story, 3)
    order = [int(i) for i in ctx.page.params.get("order", [])] or list(range(steps))
    shuffler = ctx.rng("story")
    while order == list(range(steps)):
        shuffler.shuffle(order)
    problems = [] if sorted(order) == list(range(steps)) else ["the panels must show every step once"]
    size, gap = 54.0, 10.0
    x0 = (W - steps * size - (steps - 1) * gap) / 2
    body = []
    for k in range(steps):
        cx = W - x0 - size / 2 - k * (size + gap)
        body.append(dots_mark(k + 1, cx, 10))
        body.append(text(ORDER_WORDS[min(k, 2)], cx, 24, 5.2, cls="wb-label", color="#676B83"))
    for k, step in enumerate(order):
        x = W - x0 - size - k * (size + gap)
        body.append(card(x - 3, 40, size + 6, size + 6, r=8))
        body.append(nested(_panel(story, step), x, 43, size))
        body.append(
            card(x + 4, 110, size - 8, 30, r=6, fill="#FFFFFF", stroke="#8C90A6", dash="2.6 2", width=0.7)
        )
        if step == 0 and ctx.page.example:
            body.append(draw.el("circle", cx=x + size / 2, cy=125, r=3, fill="#3D4262"))
        body.append(text(ctx.num(step + 1), x + size / 2, 131, 12, cls="wb-num key-ring", color="#E0483A"))
    key = ["الترتيب: " + "، ".join(f"الصورة {ctx.num(order.index(s) + 1)}" for s in range(steps))]
    return Built({"svg": svg(body)}, key, problems)


@page_type("classify-by")
def classify_by(ctx: PageContext) -> Built:
    """Pictures on top, a box per group below: join each picture to its box."""
    groups: list[dict[str, Any]] = [dict(g) for g in ctx.page.params.get("groups", [])]
    items = [(str(w), int(g)) for w, g in ctx.page.params.get("items", [])]
    problems = (
        [] if groups and all(0 <= g < len(groups) for _, g in items) else ["every item needs its group"]
    )
    top_h = 118.0
    cells = grid(len(items), 3, h=top_h)
    body = []
    for (w, _), (x, y, size) in zip(items, cells, strict=True):
        body.append(card(x - 3, y - 3, size + 6, size + 6, r=8))
        body.append(picture(w, x, y, size, str(groups[0].get("style", "color"))))
        body.append(hook(x + size / 2, y + size + 6, 2.2))
    bw = (W - 12 * (len(groups) + 1)) / len(groups)
    tops = []
    for k, g in enumerate(groups):
        x = W - 12 - (k + 1) * bw - k * 12
        color = COLOR_HEX.get(str(g.get("color", "")), str(g.get("color") or "#FCEFD2"))
        body.append(card(x, top_h + 26, bw, H - top_h - 28, r=10, fill=color, stroke="#2B2E4A", width=0.8))
        body.append(card(x + 6, top_h + 32, bw - 12, 16, r=6, fill="#FFFFFF", stroke="none"))
        body.append(text(str(g.get("label", "")), x + bw / 2, top_h + 43, 7, cls="wb-title", color="#1C2140"))
        if g.get("icon"):
            body.append(picture(str(g["icon"]), x + bw / 2 - 12, top_h + 50, 24))
        tops.append((x + bw / 2, top_h + 22))
        body.append(hook(x + bw / 2, top_h + 22, 2.4))
    for (_, grp), (x, y, size) in zip(items, cells, strict=True):
        body.append(answer_line((x + size / 2, y + size + 6), tops[grp]))
    key = [
        f"{groups[g].get('label', '')}: " + "، ".join(PICTURES[pid(w)].word_ar for w, k in items if k == g)
        for g in range(len(groups))
    ]
    return Built({"svg": svg(body)}, key, problems)
