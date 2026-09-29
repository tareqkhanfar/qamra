"""More counting for «مغامراتي مع عائلتي» (Addendum 7 §4.3, §4.7, §4.8, §4.10): count pictures and color as
many circles, a tally of things found outdoors, setting the table for the whole family, counting Qamra play
money, and the change («الباقي») at the ⭐⭐ level (Tareq's decision 7: ⭐ uses 1, 2 and 5 only; ⭐⭐ every
note and the change). The `counting` page type sends these modes here.
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render import draw
from qamra_workbook.render.pages.family import family_of
from qamra_workbook.render.pages.inserts import NOTE_COLORS, qamra_count
from qamra_workbook.render.registry import Built, PageContext

MODES = ("pictures", "things", "table", "money", "change")
SIMPLE_MONEY = (1, 2, 5)


def play_piece(ctx: PageContext, value: int) -> Markup:
    """A small Qamra coin or note in color, with its number (the same designs as the card-stock money)."""
    color, deep = NOTE_COLORS.get(value, NOTE_COLORS[5])
    label = draw.el(
        "text",
        ctx.num(value),
        x=20 if value < 10 else 26,
        y=25.5 if value < 10 else 20,
        text_anchor="middle",
        class_="piece-num",
        fill=deep,
    )
    if value < 10:
        body = draw.el("circle", cx=20, cy=20, r=18, fill=color, stroke=deep, stroke_width=1.1)
        body += draw.el(
            "circle",
            cx=20,
            cy=20,
            r=14,
            fill="none",
            stroke=deep,
            stroke_width=0.5,
            stroke_dasharray="1.2 1.2",
        )
        return draw.svg(40, 40, body + label, "piece coin")
    body = draw.el("rect", x=1, y=4, width=50, height=24, rx=4, fill=color, stroke=deep, stroke_width=1.1)
    body += draw.el("path", d=draw.star_points(9, 16, 5, 2.3), fill="#FFFFFF")
    return draw.svg(52, 32, body + label, "piece note")


def picture_rows(ctx: PageContext) -> tuple[dict[str, Any], list[str]]:
    """Rows of the same picture (⭐ up to 5, ⭐⭐ up to 10) with ten circles to color as many."""
    from qamra_workbook.render.pages.adventures import group

    params = ctx.page.params
    pic = str(params.get("picture", "spoon"))
    r = ctx.rng("pictures")
    counts = [*r.sample(range(1, 6), int(params.get("rows", 3))), r.randint(6, 10)]
    rows = [
        {"art": group(pic, n, 60, 26), "level": 1 if i < len(counts) - 1 else 2, "circles": list(range(10))}
        for i, n in enumerate(counts)
    ]
    data = {
        "rows": rows,
        "word": strip_tashkeel(picture(pic).word_ar),
        "hint": ctx.text("{لوّن/لوّني} العدد نفسه"),
    }
    return data, [f"{ctx.num(i + 1)}: {ctx.num(n)}" for i, n in enumerate(counts)]


def things_tally(ctx: PageContext) -> dict[str, Any]:
    params = ctx.page.params
    simple = [str(x) for x in params.get("things", ["stone", "leaf", "flower"])]
    more = [str(x) for x in params.get("challenge_things", [])]
    return {
        "columns": [
            {"pic": ctx.pic(x), "name": strip_tashkeel(picture(x).word_ar), "level": 1 if x in simple else 2}
            for x in [*simple, *more]
        ],
        "squares": list(range(int(params.get("squares", 10)))),
        "question": ctx.text(str(params.get("question", "أيّها أكثر؟ {ضع/ضعي} دائرة حوله"))),
    }


def table(ctx: PageContext, problems: list[str]) -> dict[str, Any]:
    """A place at the table for the child and everyone in the family: a plate to draw (⭐), and a spoon and a
    cup (⭐⭐)."""
    family = family_of(ctx, problems)
    names = [ctx.book.child.name] + [m.label for m in (family.members if family else ())]
    return {
        "seats": [{"name": n, "child": i == 0} for i, n in enumerate(names)],
        "how_many": ctx.text("كم صحنًا {وضعت/وضعتِ}؟"),
    }


def money_rows(ctx: PageContext) -> tuple[list[dict[str, Any]], list[str]]:
    """Purses to count: two ⭐ rows of 1, 2 and 5, two ⭐⭐ rows with 10 and 20."""
    r = ctx.rng("money")
    rows, answer = [], []
    for level, pool, size in (
        (1, SIMPLE_MONEY, 3),
        (1, SIMPLE_MONEY, 4),
        (2, (1, 2, 5, 10), 3),
        (2, (2, 5, 10, 20), 3),
    ):
        pieces = sorted((r.choice(pool) for _ in range(size)), reverse=True)
        rows.append({"level": level, "pieces": [play_piece(ctx, v) for v in pieces]})
        answer.append(f"{' + '.join(ctx.num(v) for v in pieces)} = {qamra_count(sum(pieces), ctx.numerals)}")
    return rows, answer


def change_rows(ctx: PageContext) -> tuple[list[dict[str, Any]], list[str]]:
    """⭐: count what was paid (1, 2 and 5); ⭐⭐: a price paid with a 10 or a 20 note, and the change."""
    from qamra_workbook.render.pages.adventures import SHOP_ITEMS, money_piece

    r = ctx.rng("change")
    items = list(SHOP_ITEMS)
    r.shuffle(items)
    rows, answer = [], []
    for i in range(2):
        paid = sorted(r.sample([1, 1, 2, 2, 5], 3), reverse=True)
        rows.append(
            {
                "level": 1,
                "item": ctx.pic(items[i]),
                "price": "",
                "paid": [play_piece(ctx, v) for v in paid],
                "pieces": [],
            }
        )
        answer.append(f"{' + '.join(ctx.num(v) for v in paid)} = {ctx.num(sum(paid))}")
    for i, note in ((2, 10), (3, 20)):
        price = r.randint(3, note - 2)
        rows.append(
            {
                "level": 2,
                "item": ctx.pic(items[i]),
                "price": qamra_count(price, ctx.numerals),
                "paid": [play_piece(ctx, note)],
                "pieces": [
                    money_piece(ctx, v) for v in ((5, 2, 2, 1, 1) if note == 10 else (10, 5, 2, 1, 1))
                ],
            }
        )
        answer.append(f"{ctx.num(note)} − {ctx.num(price)} = {ctx.num(note - price)}")
    return rows, answer


def change_problems() -> list[str]:
    """Every change can be paid with the pieces the row shows."""
    from qamra_workbook.render.pages.adventures import payable

    out = []
    for note in (10, 20):
        pieces = [5, 2, 2, 1, 1] if note == 10 else [10, 5, 2, 1, 1]
        out += [f"change {c} from {note}" for c in range(2, note - 2) if payable(c, pieces) is None]
    return out


def more_counting(ctx: PageContext, mode: str) -> Built:
    problems: list[str] = []
    data: dict[str, Any] = {"mode": mode}
    answer: list[str] | None = None
    match mode:
        case "pictures":
            more, answer = picture_rows(ctx)
            data |= more
        case "things":
            data |= things_tally(ctx)
        case "table":
            data |= table(ctx, problems)
        case "money":
            data["rows"], answer = money_rows(ctx)
            data["total_q"] = ctx.text("كم معي؟")
        case "change":
            data["rows"], answer = change_rows(ctx)
            problems += change_problems()
    return Built(data, answer, problems)
