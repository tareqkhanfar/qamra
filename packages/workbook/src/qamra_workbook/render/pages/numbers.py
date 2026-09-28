"""Math pages: quantity first (Addendum 6 §4.7). The child counts a group and answers with a dot card; once
the numerals are met (stage 1: 1–5 by sight, decision 2026-09-28 §3) the answer can be a numeral card."""

from __future__ import annotations

import random

from markupsafe import Markup

from qamra_workbook.pictures import get as picture
from qamra_workbook.puzzles import CountRow, generate_count_rows, layout
from qamra_workbook.render import draw
from qamra_workbook.render.pages.thinking import ring
from qamra_workbook.render.registry import Built, PageContext, page_type

# rows are marked with little pictures, not numbers: numerals come after quantities (Addendum 6 §4.7)
ROW_MARKS = ("star", "heart", "shapes", "puzzle")
ROW_MARKS_AR = {"star": "النجمة", "heart": "القلب", "shapes": "الأشكال", "puzzle": "قطعة البازل"}


def group_svg(picture_id: str, count: int, w: float = 60, h: float = 40) -> Markup:
    """`count` pictures in a dice layout (the same layout as the dot cards)."""
    size = min(w, h) * (0.62 if count <= 2 else 0.5)
    inner = picture(picture_id).inner("color")
    body = "".join(
        draw.el(
            "svg",
            inner,
            x=u * w - size / 2,
            y=v * h - size / 2,
            width=size,
            height=size,
            viewBox="0 0 100 100",
            data_count_item=picture_id,
        )
        for u, v in layout(count)
    )
    return draw.svg(w, h, body, "group")


def dots_svg(count: int, color: str, size: float = 30) -> Markup:
    """A dot card: `count` big dots in the dice layout."""
    pad, span = size * 0.08, size * 0.84
    body = "".join(
        draw.el("circle", cx=pad + u * span, cy=pad + v * span, r=size * 0.1, fill=color, data_dot=1)
        for u, v in layout(count)
    )
    return draw.svg(size, size, body, "dots")


# how the child answers «كم؟»: circle the dot card with the same amount, or (once the numerals are met,
# decision 2026-09-28 §3) circle the numeral card
DOT_CARDS = ("dots", "dot-cards")
NUMERAL_CARDS = "numerals"


def numeral_card(text: str, n: int) -> Markup:
    """A card with one big numeral, printed in the page's numerals (`text` comes from `PageContext.num`)."""
    return Markup('<span class="numeral" data-numeral="{}">{}</span>').format(n, text)


def fewer_cards(rows: list[CountRow], keep: int, r: random.Random) -> list[CountRow]:
    """Each row keeps its answer and `keep - 1` other cards from the options, shuffled so the answer moves
    from row to row (the checks in `CountRow.problems` still apply)."""
    out: list[CountRow] = []
    for row in rows:
        others = [n for n in row.options if n != row.count]
        r.shuffle(others)
        cards = [row.count, *others[: keep - 1]]
        while True:
            r.shuffle(cards)
            if not out or len(cards) < 2 or cards.index(row.count) != out[-1].answer:
                break
        out.append(CountRow(row.picture, row.count, tuple(cards), row.example))
    return out


@page_type("quantity-first")
def quantity_first(ctx: PageContext) -> Built:
    params = ctx.page.params
    pic = str(params.get("picture", "apple"))
    counts = [int(x) for x in params.get("counts", [1, 2, 3])]
    options = [int(x) for x in params.get("options", [1, 2, 3])]
    example = int(params["example"]) if "example" in params else (2 if ctx.page.example else None)
    answer_with = str(params.get("answer_with", DOT_CARDS[0]))
    problems = []
    if answer_with not in (*DOT_CARDS, NUMERAL_CARDS):
        problems.append(f"quantity-first answers with dot cards or numerals, not {answer_with!r}")
    rows = generate_count_rows(ctx.page.seed, counts, options, pic, example)
    keep = int(params.get("cards", len(options)))
    if keep < len(options):
        rows = fewer_cards(rows, keep, ctx.rng("cards"))
    numerals = answer_with == NUMERAL_CARDS
    color = ctx.style.color
    data = {
        "rows": [
            {
                "group": group_svg(pic, row.count),
                "cards": [
                    numeral_card(ctx.num(n), n) if numerals else dots_svg(n, color) for n in row.options
                ],
                "answer": row.answer,
                "count": row.count,
                "example": row.example,
                "mark": ROW_MARKS[k % len(ROW_MARKS)],
            }
            for k, row in enumerate(rows)
        ],
        "ring": ring,
        "numerals": numerals,
    }
    head = "الرقم الذي يساوي عدد الصور:" if numerals else "البطاقة التي نقاطها بعدد الصور:"
    answer = [head] + [
        f"صف {ROW_MARKS_AR[ROW_MARKS[k % len(ROW_MARKS)]]}: {ctx.num(row.count)}"
        for k, row in enumerate(rows)
        if not row.example
    ]
    return Built(data, answer, problems + [p for row in rows for p in row.problems()])
