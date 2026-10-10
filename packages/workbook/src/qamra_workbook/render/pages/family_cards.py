"""The family book's card-stock sheets (Addendum 7 §6, §10): the recipes' step cards, the memory game's
picture pairs, the family question cards, the role cards and the finger puppets. Each is printed on 250 g
card on its own sheet, without a page number; every card has a printed guide to cut along with a grown-up
and, on its own die-line layer (`render.dielines`), the cut line the printer's die follows. The card's
color runs 1.5 mm past its cut line, so a slightly shifted cut never shows a white edge.
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_pdf.arabic_names import GEN, in_case
from qamra_workbook.pictures import get as picture
from qamra_workbook.render import art, draw, people
from qamra_workbook.render.pages.family import step_picture
from qamra_workbook.render.pages.family_games import MEMORY_PAIRS
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.sections import section_style

RECIPE_COLORS = ("#E4675A", "#F08A3E", "#2FA36B", "#8C6CCB", "#2E9FD6")


def sheet_data(ctx: PageContext, case: str = "") -> dict[str, Any]:
    """The sheet's owner (the child's name under the sheet's label) and the scissors icon. `case` is the
    name's case after the label: `GEN` when the label owns the name («بِطاقاتُ أبي بكر»), as typed under a
    label that is complete («لُعْبَةُ الذّاكِرَةِ», «دُمى الأَصابِعِ»)."""
    return {"owner": in_case(ctx.book.child.name, case), "scissors": art.icon("scissors")}


@page_type("recipe-cards", frame="sheet")
def recipe_cards(ctx: PageContext) -> Built:
    """Every recipe's steps as picture cards to cut out, shuffle and put back in order (`recipes`: the
    recipe pages' titles and steps, taken from the plan)."""
    recipes = [dict(r) for r in ctx.page.params.get("recipes", [])]
    cards = []
    for k, recipe in enumerate(recipes):
        color = str(recipe.get("color", RECIPE_COLORS[k % len(RECIPE_COLORS)]))
        for n, step in enumerate(recipe.get("steps", []), start=1):
            cards.append(
                {
                    "pic": step_picture(str(step["picture"])),
                    "text": ctx.text(str(step["text"])),
                    "recipe": ctx.text(str(recipe["title"])),
                    "color": color,
                    "n": ctx.num(n),
                }
            )
    problems = [] if 6 <= len(cards) <= 20 else [f"a recipe sheet holds 6–20 step cards, not {len(cards)}"]
    return Built(sheet_data(ctx, GEN) | {"cards": cards}, None, problems)  # «بِطاقاتُ» + the name


@page_type("memory-cards", frame="sheet")
def memory_cards(ctx: PageContext) -> Built:
    """The memory game: every picture twice; the first `pairs` pairs are the ⭐ game, all of them ⭐⭐."""
    params = ctx.page.params
    pics = [str(x) for x in params.get("cards", MEMORY_PAIRS)]
    simple = int(params.get("pairs", 6))
    cards = [
        {"pic": ctx.pic(x), "word": picture(x).word_ar, "level": 1 if i < simple else 2}
        for i, x in enumerate(pics)
        for _ in range(2)
    ]
    problems = [] if len(pics) <= 12 else [f"the memory sheet holds 12 pairs, not {len(pics)}"]
    return Built(sheet_data(ctx) | {"cards": cards}, None, problems)


@page_type("question-cards", frame="sheet")
def question_cards(ctx: PageContext) -> Built:
    """The family question cards: ⭐ questions and ⭐⭐ ones to answer in turn at game night."""
    cards = [
        {
            "text": ctx.text(str(c["text"])),
            "icon": str(c.get("icon", "talk")),
            "level": int(c.get("level", 1)),
        }
        for c in (dict(x) for x in ctx.page.params.get("cards", []))
    ]
    problems = [] if 6 <= len(cards) <= 12 else [f"a question sheet holds 6–12 cards, not {len(cards)}"]
    return Built(sheet_data(ctx) | {"cards": cards}, None, problems)


@page_type("role-cards", frame="sheet")
def role_cards(ctx: PageContext) -> Built:
    """Role cards for play-acting: who you are (a person at work), what you might say, and a prop from
    home."""
    roles = []
    for r in (dict(x) for x in ctx.page.params.get("roles", [])):
        figure = ctx.text(str(r["figure"])) if r.get("figure") else None  # «{man/woman}»: a boy's set and a girl's
        art = people.job_bust(str(r["job"]), 1.2, figure)  # type: ignore[arg-type]
        bust = draw.svg(60, people.BUST_H + 10, f'<g transform="translate(0 10)">{art}</g>', "bust")  # a hat fits
        roles.append(
            {
                "art": bust,
                "label": ctx.text(str(r["label"])),
                "lines": [ctx.text(str(x)) for x in r.get("lines", [])],
                "prop": ctx.pic(str(r["prop"])) if r.get("prop") else Markup(""),
                "color": people.JOBS.get(str(r["job"]), ("adult", "#E98AA6", ""))[1],
            }
        )
    problems = [] if 4 <= len(roles) <= 6 else [f"a role sheet holds 4–6 cards, not {len(roles)}"]
    return Built(sheet_data(ctx) | {"roles": roles}, None, problems)


PUPPET_W, PUPPET_H = 58.0, 72.0  # mm: a round head on a band that rolls round a child's finger
BAND_TOP, BAND_BOTTOM, GLUE_W = 42.0, 68.0, 10.0


def puppet_die() -> str:
    """The puppet's cut line (path data in mm): the head, then the band (its left end is the glue tab)."""
    cx, r = PUPPET_W / 2, 19.0
    return (
        f"M{cx - 12} {BAND_TOP} A{r} {r} 0 1 1 {cx + 12} {BAND_TOP} L{PUPPET_W - 2} {BAND_TOP} "
        f"L{PUPPET_W - 2} {BAND_BOTTOM} L2 {BAND_BOTTOM} L2 {BAND_TOP} Z"
    )


@page_type("puppets", frame="sheet")
def puppets(ctx: PageContext) -> Built:
    """Finger puppets: the animal on the head, the band to roll round a finger and glue at its end."""
    animals = [
        str(x) for x in ctx.page.params.get("animals", ["cat", "rabbit", "lion", "duck", "sheep", "dog"])
    ]
    tint = section_style("act", ctx.book.product).tint
    back = draw.el("path", d=puppet_die(), fill=tint, stroke=tint, stroke_width=3)  # color past the cut line
    glue = draw.el(
        "rect", x=2, y=BAND_TOP, width=GLUE_W, height=BAND_BOTTOM - BAND_TOP, fill="#FFFFFF", opacity=0.7
    )
    guide = draw.el(
        "path", d=puppet_die(), fill="none", stroke="#8E93AB", stroke_width=0.35, stroke_dasharray="1.6 1.4"
    )
    die = draw.el("path", d=puppet_die(), fill="none", stroke="#EC008C", stroke_width=0.3, class_="cut")
    items = [
        {
            "pic": ctx.pic(a),
            "word": picture(a).word_ar,
            "back": draw.svg(PUPPET_W, PUPPET_H, back + glue, "puppet-back"),
            "outline": draw.svg(PUPPET_W, PUPPET_H, guide + die, "puppet-lines"),
        }
        for a in animals
    ]
    problems = [] if 2 <= len(items) <= 6 else [f"a puppet sheet holds 2–6 puppets, not {len(items)}"]
    data = sheet_data(ctx) | {"puppets": items, "size": (PUPPET_W, PUPPET_H), "band": (BAND_TOP, BAND_BOTTOM)}
    return Built(data, None, problems)
