"""«ليلة الألعاب العائلية» (Addendum 7 §4.11): the memory game's page (how to play, the cards from the card
stock, a pairs tally for every player) and the family scoreboard. The players are the child and everyone the
parent listed, so the tables grow and shrink with the family (2–7 players).
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render.pages.family import family_of
from qamra_workbook.render.registry import Built, PageContext, page_type

MEMORY_PAIRS = (
    "apple",
    "cat",
    "sun",
    "car",
    "fish",
    "ball",
    "flower",
    "bird",
    "house",
    "banana",
    "kite",
    "teddy",
)


def pairs_ar(n: int, ctx: PageContext) -> str:
    """«زوجان», «٦ أزواج», «١٢ زوجًا»: the counted noun agrees with the number."""
    if n == 2:
        return "زوجان"
    return f"{ctx.num(n)} {'أزواج' if 3 <= n <= 10 else 'زوجًا'}"


def players(ctx: PageContext, problems: list[str]) -> list[dict[str, Any]]:
    family = family_of(ctx, problems)
    names = [ctx.book.child.name] + [m.label for m in (family.members if family else ())]
    return [{"name": n, "child": i == 0} for i, n in enumerate(names)]


@page_type("family-game-cards")
def family_game_cards(ctx: PageContext) -> Built:
    """`mode: memory`: how to play with the memory cards (⭐ `pairs`, ⭐⭐ `challenge` more) and a tally of
    the pairs each player finds; `mode: scoreboard`: stars to color for every round, then the totals."""
    params = ctx.page.params
    mode = str(params.get("mode", "scoreboard"))
    problems: list[str] = [] if mode in ("memory", "scoreboard") else [f"no game mode {mode!r}"]
    who = players(ctx, problems)
    data: dict[str, Any] = {"mode": mode, "players": who}
    if mode == "memory":
        pairs, more = int(params.get("pairs", 6)), int(params.get("challenge", 6))
        cards = [str(c) for c in params.get("cards", MEMORY_PAIRS)][: pairs + more]
        if len(cards) < pairs + more:
            problems.append(f"the memory game needs {pairs + more} pictures")
        data |= {
            "steps": [ctx.text(str(s)) for s in params.get("steps", [])],
            "shown": [{"pic": ctx.pic(cards[0]), "word": strip_tashkeel(picture(cards[0]).word_ar)}] * 2,
            "backs": 6,
            "levels": [(1, pairs_ar(pairs, ctx)), (2, pairs_ar(pairs + more, ctx))],
            "boxes": list(range(pairs + more)),
            "simple": pairs,
        }
    else:
        rounds = int(params.get("rounds", 5))
        data |= {
            "rounds": [ctx.num(i + 1) for i in range(rounds)],
            "total": "المجموع",
            "cheer": ctx.text(str(params.get("cheer", "كلنا ربحنا وقتًا حلوًا معًا!"))),
        }
    return Built(data, None, problems)
