"""Choosing pages for «مغامراتي مع عائلتي» (Addendum 7 §4.10, §4.12), reached through `sort-choose`:
`mode: budget` (what can I buy with the money I have? ⭐ five qamras in 1, 2 and 5; ⭐⭐ twenty with every
note, and a second way) and `mode: choice` (situations with a few solutions: choose the kindest and say why).
Both are open: any right answer counts, so neither has an answer key.
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.render.pages.family_count import play_piece
from qamra_workbook.render.pages.inserts import qamra_count
from qamra_workbook.render.registry import Built, PageContext

MODES = ("budget", "choice")


def budget(ctx: PageContext, problems: list[str]) -> dict[str, Any]:
    from qamra_workbook.render.pages.adventures import SHOP_ITEMS

    params = ctx.page.params
    purses = [
        (1, [int(x) for x in params.get("simple_purse", [2, 2, 1])]),
        (2, [int(x) for x in params.get("challenge_purse", [10, 5, 5])]),
    ]
    items = [str(x) for x in params.get("products", SHOP_ITEMS[:6])]
    prices = [int(x) for x in params.get("prices", [1, 2, 3, 4, 6, 8])]
    if len(items) != len(prices):
        problems.append("every product needs a price")
    if min(prices, default=0) > sum(purses[0][1]):
        problems.append("the ⭐ purse cannot buy anything")
    return {
        "wallets": [
            {
                "level": level,
                "pieces": [play_piece(ctx, v) for v in pieces],
                "total": qamra_count(sum(pieces), ctx.numerals),
            }
            for level, pieces in purses
        ],
        "products": [
            {"pic": ctx.pic(i), "price": qamra_count(p, ctx.numerals)}
            for i, p in zip(items, prices, strict=False)
        ],
        "bought": ctx.text("ماذا {اشْتَرَيْتَ/اشْتَرَيْتِ}؟"),
        "second": ctx.text("طَريقَةٌ ثانِيَةٌ"),
    }


def choice(ctx: PageContext, problems: list[str]) -> dict[str, Any]:
    situations = [dict(x) for x in ctx.page.params.get("situations", [])]
    if not 1 <= len(situations) <= 3:
        problems.append(f"1–3 situations to solve, not {len(situations)}")
    from qamra_workbook.render.pages.family_day import scene

    return {
        "situations": [
            {
                "pic": scene([str(p) for p in x.get("pictures", [])]),
                "text": ctx.text(str(x["text"])),
                "options": [
                    {"icon": str(o.get("icon", "star")), "text": ctx.text(str(o["text"]))}
                    for o in x.get("options", [])
                ],
            }
            for x in situations
        ],
        "mine": ctx.text("حَلٌّ مِنْ عِنْدي:"),
    }


def more_choosing(ctx: PageContext, mode: str) -> Built:
    problems: list[str] = []
    data: dict[str, Any] = {"mode": mode}
    data |= budget(ctx, problems) if mode == "budget" else choice(ctx, problems)
    return Built(data, None, problems)
