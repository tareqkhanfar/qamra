"""«مغامراتي مع عائلتي» pages for doing things in order and every day (Addendum 7 §4.4, §4.7, §4.8, §4.11):
sequence cards (the day, a story from pictures, a chain of moves), the routine builder and the weekly chore
chart (both filled with stickers from the sticker sheet), and nature bingo for the child and a grown-up.
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_workbook.pictures import get as picture
from qamra_workbook.render import draw
from qamra_workbook.render.pages.family import uri
from qamra_workbook.render.registry import Built, PageContext, page_type

WEEK = ("السَّبْتُ", "الأَحَدُ", "الاثْنَيْنِ", "الثُّلاثاءُ", "الأَرْبِعاءُ", "الخَميسُ", "الجُمُعَةُ")

# ---- pictogram moves --------------------------------------------------------------------------------------

Seg = tuple[float, float, float, float]
# pose: head (x, y) and the limbs as segments in a 40 × 50 box
POSES: dict[str, tuple[tuple[float, float], tuple[Seg, ...]]] = {
    "jump": (
        (20, 8),
        ((20, 14, 20, 30), (20, 17, 10, 6), (20, 17, 30, 6), (20, 30, 13, 42), (20, 30, 27, 42)),
    ),
    "spin": (
        (20, 8),
        ((20, 14, 20, 30), (20, 18, 7, 18), (20, 18, 33, 18), (20, 30, 17, 45), (20, 30, 23, 45)),
    ),
    "clap": (
        (20, 10),
        ((20, 16, 20, 32), (20, 19, 18, 3), (20, 19, 22, 3), (20, 32, 16, 46), (20, 32, 24, 46)),
    ),
    "hop": (
        (20, 8),
        ((20, 14, 20, 30), (20, 18, 9, 13), (20, 18, 31, 13), (20, 30, 20, 46), (20, 30, 29, 37)),
    ),
    "stretch": (
        (20, 11),
        ((20, 17, 20, 33), (20, 19, 15, 1), (20, 19, 25, 1), (20, 33, 18, 47), (20, 33, 22, 47)),
    ),
    "touch": (
        (29, 25),
        ((24, 22, 14, 26), (22, 23, 26, 40), (22, 23, 22, 42), (14, 26, 14, 46), (14, 26, 19, 46)),
    ),
    "statue": (
        (20, 8),
        ((20, 14, 20, 30), (20, 18, 8, 10), (20, 18, 32, 26), (20, 30, 12, 44), (20, 30, 26, 45)),
    ),
}
EXTRAS = {
    "jump": "M9 48 L15 48 M25 48 L31 48",
    "spin": "M5 37 A15 6 0 1 0 35 37",
    "clap": "M13 3 L10 1 M27 3 L30 1 M20 -1 L20 -3",
    "hop": "M31 41 L35 41 M31 44 L34 44",
}


def pictogram(pose: str, color: str) -> Markup:
    (hx, hy), limbs = POSES.get(pose, POSES["jump"])
    body = [draw.path(f"M{a} {b} L{c} {d}", stroke=color, width=4.2) for a, b, c, d in limbs]
    body.append(draw.el("circle", cx=hx, cy=hy, r=5.4, fill=color))
    if pose in EXTRAS:
        body.append(draw.path(EXTRAS[pose], stroke="#8A8FA8", width=1.1))
    return draw.svg(40, 50, "".join(body), "move-pic")


def scene(pictures: list[str]) -> Markup:
    """A small scene from library pictures: the first big, the others smaller around it."""
    parts = []
    spots = ((10, 10, 80), (60, 4, 36), (4, 58, 34), (62, 60, 34))
    for pic, (x, y, size) in zip(pictures, spots, strict=False):
        inner = picture(pic).inner("color")
        parts.append(draw.el("svg", inner, x=x, y=y, width=size, height=size, viewBox="0 0 100 100"))
    return draw.svg(100, 100, "".join(parts), "scene-pic")


def shuffled(ctx: PageContext, count: int, shown: list[int] | None = None) -> list[int]:
    """The order the cards are printed in (1-based step numbers), never already in order."""
    if shown and sorted(shown) == list(range(1, count + 1)):
        return shown
    order = list(range(1, count + 1))
    r = ctx.rng("order")
    while count > 1 and order == sorted(order):
        r.shuffle(order)
    return order


@page_type("sequence-cards")
def sequence_cards(ctx: PageContext) -> Built:
    """Cards to put in order: `mode: day` (the day from morning to night; `cards` in the right order, the
    ⭐⭐ ones marked `level: 2`), `mode: story` (three story `panels` to order and tell) or `mode: moves` (a
    chain of `moves` to copy, the first `simple` of them for ⭐)."""
    params = ctx.page.params
    mode = str(params.get("mode", "day"))
    problems = [] if mode in ("day", "story", "moves") else [f"no sequence mode {mode!r}"]
    data: dict[str, Any] = {"mode": mode, "character": uri(ctx.assets.character)}
    answer = None
    if mode == "moves":
        moves = [dict(m) for m in params.get("moves", [])]
        simple = int(params.get("simple", 3))
        if not 3 <= len(moves) <= 7:
            problems.append(f"a chain has 3–7 moves, not {len(moves)}")
        data["moves"] = [
            {
                "pic": pictogram(str(m.get("pose", "jump")), ctx.style.color),
                "text": ctx.text(str(m.get("text", ""))),
                "n": ctx.num(i + 1),
                "level": 1 if i < simple else 2,
            }
            for i, m in enumerate(moves)
        ]
        data["mine"] = ctx.text(str(params.get("mine", "حَرَكَتي أَنا")))
    else:
        key = "panels" if mode == "story" else "cards"
        steps = [dict(c) for c in params.get(key, [])]  # in the right order; a card may be `level: 2`
        limits = (3, 3) if mode == "story" else (3, 7)
        if not limits[0] <= len(steps) <= limits[1]:
            problems.append(f"{mode} cards: {limits[0]}–{limits[1]}, not {len(steps)}")
        order = shuffled(ctx, len(steps), [int(x) for x in params.get("shown", [])] or None)
        cards = []
        for n in order:
            step = steps[n - 1]
            pics = [str(x) for x in step.get("pictures", [step.get("picture", "star")])]
            cards.append(
                {
                    "pic": scene(pics) if len(pics) > 1 else ctx.pic(pics[0]),
                    "text": ctx.text(str(step.get("text", ""))),
                    "level": int(step.get("level", 1)),
                    "n": n,
                }
            )
        data["cards"] = cards
        data["from_to"] = [ctx.text(str(x)) for x in params.get("from_to", ["الصَّباحُ", "المَساءُ"])]
        data["ending"] = ctx.text(str(params.get("ending", "{غَيِّرِ/غَيِّري} النِّهايَةَ: ماذا حَدَثَ بَعْدَ ذَلِكَ؟")))
        answer = [
            "الترتيب: "
            + "، ".join(f"{ctx.num(i + 1)} {ctx.text(str(s.get('text', '')))}" for i, s in enumerate(steps))
        ]
    return Built(data, answer, problems)


# ---- the routine builder and the chore chart (sticker pages) ----------------------------------------------

ROUTINE_SLOT_MM = 21.0  # a routine sticker (inserts.ROUTINE) is 19 mm: it fits its slot with room to spare
CHORE_SLOT_MM = 13.0  # a reward star (inserts.CHORE_STARS) is 11.5 mm


@page_type("routine-builder")
def routine_builder(ctx: PageContext) -> Built:
    """Morning and evening: a numbered slot for each routine sticker (⭐ `steps`, ⭐⭐ `challenge` more), and
    a week to tick every morning and evening the child follows the routine."""
    params = ctx.page.params
    steps, more = int(params.get("steps", 3)), int(params.get("challenge", 2))
    problems = (
        [] if 2 <= steps <= 4 and steps + more <= 5 else ["a routine has 2–4 steps (⭐), at most 5 (⭐⭐)"]
    )
    slots = [{"n": ctx.num(i + 1), "level": 1 if i < steps else 2} for i in range(steps + more)]
    hints = [str(h) for h in params.get("hints", [])]
    data = {
        "parts": [
            {"key": "morning", "icon": "sun", "title": "روتينُ الصَّباحِ", "slots": slots},
            {"key": "evening", "icon": "moon", "title": "روتينُ المَساءِ", "slots": slots},
        ],
        "slot_mm": ROUTINE_SLOT_MM,
        "stick": ctx.text("{أَلْصِقْ/أَلْصِقي} هُنا"),
        "week": WEEK,
        "hints": [{"pic": ctx.pic(h), "word": picture(h).word_ar} for h in hints],
        "track": ctx.text(str(params.get("track", "{لَوِّنِ/لَوِّني} الشَّمْسَ وَالقَمَرَ كُلَّ يَوْمٍ"))),
    }
    return Built(data, None, problems)


@page_type("chore-chart")
def chore_chart(ctx: PageContext) -> Built:
    """A week of home tasks: a row per task (⭐ `tasks` rows, ⭐⭐ `challenge` more) with a star slot a day
    for the reward stickers, task ideas to pick from, and the family's reward at the end of the week."""
    params = ctx.page.params
    tasks, more = int(params.get("tasks", 2)), int(params.get("challenge", 1))
    problems = [] if tasks >= 1 and tasks + more <= 4 else ["a chart has 1–4 task rows"]
    ideas = [dict(i) for i in params.get("ideas", [])]
    data = {
        "rows": [{"n": ctx.num(i + 1), "level": 1 if i < tasks else 2} for i in range(tasks + more)],
        "week": WEEK,
        "slot_mm": CHORE_SLOT_MM,
        "ideas": [
            {"pic": ctx.pic(str(i["picture"])), "text": ctx.text(str(i.get("text", "")))} for i in ideas[:6]
        ],
        "owner": ctx.text(str(params.get("owner", "جَدْوَلُ {child:gen}"))),
        "reward": ctx.text(str(params.get("reward", "مُكافَأَتي فِي آخِرِ الأُسْبوعِ:"))),
    }
    return Built(data, None, problems)


# ---- nature bingo -----------------------------------------------------------------------------------------

BINGO_SIZE = 3


@page_type("nature-bingo")
def nature_bingo(ctx: PageContext) -> Built:
    """Two 3 × 3 bingo cards (the child's and a grown-up's), the same things in a different order, with a
    free star in the middle; `hear` marks the things to listen for rather than see."""
    params = ctx.page.params
    items = [str(i) for i in params.get("items", [])]
    hear = {str(i) for i in params.get("hear", [])}
    problems = [] if len(items) == BINGO_SIZE**2 - 1 else [f"a bingo card has {BINGO_SIZE**2 - 1} things"]
    cards = []
    for k, owner in enumerate((ctx.book.child.name, ctx.text("{adult}"))):
        order = list(items)
        ctx.rng(f"bingo-{k}").shuffle(order)
        order.insert(len(order) // 2, "")
        cells = [
            {"pic": ctx.pic(i), "word": picture(i).word_ar, "hear": i in hear} if i else {} for i in order
        ]
        cards.append({"owner": owner, "cells": cells, "child": k == 0})
    data = {"cards": cards, "size": BINGO_SIZE, "see": "أَرى", "listen": "أَسْمَعُ"}
    return Built(data, None, problems)
