"""«مغامراتي مع عائلتي» pages (Addendum 7 §6): the adventurer's passport, an adventure's opening spread,
the treasure hunt, the shopping list, a recipe, the feelings thermometer, the memory page, the 7-day family
challenge and the family certificate.

Every mission names the child and, through `{adult}` / `{member}`, the family members the parent entered
(A7 §7); nothing assumes a mother and a father. Checks keep the Addendum 7 rules a page can see on its own:
the ⭐ / ⭐⭐ counts, a recipe's safety box (knife and heat, allergies, washing hands; no nuts or raw eggs),
seven different days in the challenge.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from markupsafe import Markup

from qamra_workbook.family import NUTS_AND_RAW_EGGS
from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import OUTLINE, scallop_d, strip_tashkeel
from qamra_workbook.puzzles.coloring import Shape
from qamra_workbook.render import art, draw, people
from qamra_workbook.render.pages.journey import MEDAL, _ray, _star
from qamra_workbook.render.pages.motor import nested_picture
from qamra_workbook.render.pages.thinking import shape_kind
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.sections import FAMILY as FAMILY_SECTIONS
from qamra_workbook.render.sections import section_style
from qamra_workbook.render.spec import Family, Member


@dataclass(frozen=True)
class Badge:
    """A passport stamp: the seven adventurer badges (A7 §4.15) and one per adventure."""

    key: str
    label: str  # may carry {masc/fem}
    icon: str  # a key of art.ICONS
    color: str


CORE_BADGES = (
    Badge("adventurer", "{مغامر/مغامرة}", "compass", "#F08A3E"),
    Badge("thinker", "{مفكّر/مفكّرة}", "bulb", "#8C6CCB"),
    Badge("artist", "{فنان/فنانة}", "palette", "#E4769D"),
    Badge("explorer", "{مستكشف/مستكشفة}", "magnifier", "#2FA36B"),
    Badge("chef", "{طبّاخ صغير/طبّاخة صغيرة}", "chef", "#E4675A"),
    Badge("responsible", "{طفل مسؤول/طفلة مسؤولة}", "check-list", "#23A094"),
    Badge("friend", "{صديق لطيف/صديقة لطيفة}", "friend", "#2E9FD6"),
)


def section_badges(ctx: PageContext) -> list[Badge]:
    """The adventures' stamps a page lists in `stamps`: [{section, label}], drawn in the section's style;
    without `stamps`, every adventure of the book under its own name."""
    out = []
    default = [{"section": k} for k in FAMILY_SECTIONS if k not in ("front", "back")]
    for raw in ctx.page.params.get("stamps", default):
        style = section_style(str(raw["section"]), ctx.book.product)
        out.append(Badge(style.id, str(raw.get("label", style.name_ar)), style.icon, style.color))
    return out


def seal(badge: Badge, *, filled: bool = True, css_class: str = "seal") -> Markup:
    """A round badge: a scalloped sticker with a white icon, or (not filled) the dashed slot it goes on."""
    if filled:
        body = (
            draw.el("path", d=scallop_d(20, 20, 18.6, 18.6, 16, 0.58), fill=badge.color)
            + draw.el("circle", cx=20, cy=20, r=14.6, fill="#FFFFFF")
            + draw.el("circle", cx=20, cy=20, r=12.9, fill=badge.color)
            + draw.el(
                "path",
                d="M10.5 15 A11 11 0 0 1 20 8.6",
                fill="none",
                stroke="#FFFFFF",
                stroke_width=1.3,
                stroke_linecap="round",
                opacity=0.45,
            )
            + draw.el(
                "svg",
                art.glyph(badge.icon, "#FFFFFF", 2.1),
                x=11.5,
                y=11.5,
                width=17,
                height=17,
                viewBox="0 0 24 24",
            )
        )
    else:
        body = (
            draw.el(
                "circle",
                cx=20,
                cy=20,
                r=18.4,
                fill="#FFFFFF",
                stroke=badge.color,
                stroke_width=0.9,
                stroke_dasharray="2.4 1.9",
                stroke_linecap="round",
            )
            + draw.el("circle", cx=20, cy=20, r=14.4, fill=badge.color, opacity=0.08)
            + draw.el(
                "g",
                draw.el(
                    "svg",
                    art.glyph(badge.icon, badge.color, 2),
                    x=12.5,
                    y=12.5,
                    width=15,
                    height=15,
                    viewBox="0 0 24 24",
                ),
                opacity=0.4,
            )
        )
    return Markup(f'<svg class="{css_class}" viewBox="0 0 40 40" aria-hidden="true">{body}</svg>')  # nosec B704


def rosette(badge: Badge, *, filled: bool = True, css_class: str = "seal") -> Markup:
    """One of the seven adventurer badges: a rosette with two ribbon tails (the adventures' stamps are round
    seals, so the two kinds never look alike), or (not filled) the dashed slot it goes on."""
    tails = "M15 24 L9.5 38 L13.4 36 L15.8 39.5 L20 26 Z M25 24 L30.5 38 L26.6 36 L24.2 39.5 L20 26 Z"
    if filled:
        body = (
            draw.el("path", d=tails, fill=badge.color, stroke="#FFFFFF", stroke_width=0.9)
            + draw.el("path", d=draw.star_points(20, 17, 16.5, 13.6, 18), fill=badge.color)
            + draw.el("circle", cx=20, cy=17, r=12.2, fill="#FFFFFF")
            + draw.el("circle", cx=20, cy=17, r=10.6, fill=badge.color)
            + draw.el(
                "svg",
                art.glyph(badge.icon, "#FFFFFF", 2.2),
                x=13,
                y=10,
                width=14,
                height=14,
                viewBox="0 0 24 24",
            )
        )
    else:
        ring: dict[str, float | str] = {
            "fill": "#FFFFFF",
            "stroke": badge.color,
            "stroke_width": 0.9,
            "stroke_dasharray": "2.2 1.8",
        }
        body = (
            draw.el("path", d=tails, stroke_linejoin="round", opacity=0.55, **ring)
            + draw.el("path", d=draw.star_points(20, 17, 16.3, 13.4, 18), stroke_linejoin="round", **ring)
            + draw.el("circle", cx=20, cy=17, r=11, fill=badge.color, opacity=0.08)
            + draw.el(
                "g",
                draw.el(
                    "svg",
                    art.glyph(badge.icon, badge.color, 2),
                    x=14,
                    y=11,
                    width=12,
                    height=12,
                    viewBox="0 0 24 24",
                ),
                opacity=0.4,
            )
        )
    return Markup(f'<svg class="{css_class}" viewBox="0 0 40 40" aria-hidden="true">{body}</svg>')  # nosec B704


def uri(path: Path | None) -> str:
    return path.resolve().as_uri() if path is not None else ""


def family_of(ctx: PageContext, problems: list[str]) -> Family | None:
    if ctx.book.family is None:
        problems.append("a family page needs the book's family (names, roles, city)")
    return ctx.book.family


def members_line(members: Sequence[Member]) -> str:
    """«ماما وبابا وكرم وستّي»."""
    labels = [m.label for m in members]
    return " و".join(labels) if len(labels) > 1 else "".join(labels)


# ---- the passport (front pages) -------------------------------------------------------------------------


@page_type("passport")
def passport(ctx: PageContext) -> Built:
    """The passport card and two rows of slots: one stamp per adventure (numbered, in the book's order) and
    the seven adventurer badges."""
    problems: list[str] = []
    family = family_of(ctx, problems)
    stamps = section_badges(ctx)
    if not 1 <= len(stamps) <= 12:
        problems.append(f"the passport holds 1–12 adventure stamps, not {len(stamps)}")
    data = {
        "photo": uri(ctx.assets.character),
        "name": ctx.book.child.name,
        "family": family.name if family else "",
        "city": family.city if family else "",
        "date": ctx.book.date_ar(),
        "slots": [
            {"label": ctx.text(b.label), "svg": seal(b, filled=False), "color": b.color, "n": ctx.num(i)}
            for i, b in enumerate(stamps, start=1)
        ],
        "badges": [
            {"label": ctx.text(b.label), "svg": rosette(b, filled=False), "color": b.color}
            for b in CORE_BADGES
        ],
    }
    return Built(data, None, problems)


# ---- an adventure's opening spread ---------------------------------------------------------------------


def _hill(y: float, amp: float, phase: float, color: str, w: float, h: float) -> str:
    pts: list[tuple[str, float | tuple[float, ...]]] = [("M", (0, y))]
    step = w / 6
    for i in range(6):
        x0 = i * step
        dy = amp if (i + phase) % 2 else -amp
        pts.append(("Q", (x0 + step / 2, y + dy, x0 + step, y)))
    pts += [("L", (w, h)), ("L", (0, h))]
    return draw.el("path", d=draw.d_path(*pts) + " Z", fill=color)


# the picture behind the family on an adventure's opening spread
SCENES = {
    "home": "house",
    "market": "stall",
    "chef": "kitchen",
    "nature": "tree",
    "day": "sun",
    "responsible": "pot-plant",
    "feelings": "heart",
    "talk": "book",
    "jobs": "briefcase",
    "shop": "shopping-bag",
    "games": "dice",
    "act": "theatre",
}


def spread_size(ctx: PageContext) -> tuple[float, float]:
    """The spread's drawing: two trims and the outer bleeds wide, one page (with bleed) tall."""
    g = ctx.book.geometry
    return 2 * g.trim_w + 2 * g.bleed, g.page_h


def spread_art(ctx: PageContext) -> Markup:
    """The landscape across both pages (the gutter at x = bleed + trim width): sky in the section's tint,
    rolling hills, and a road from the right-hand page to the family's home on the left-hand page. The sky
    things hang from the top and the land stands on the bottom, so the art fits any page height; the
    right-hand page's upper half stays clear for the title and the story."""
    style = ctx.style
    g = ctx.book.geometry
    w, h = spread_size(ctx)
    gutter = g.bleed + g.trim_w
    left_mid = g.bleed + g.trim_w / 2
    sky = f"sky-{ctx.page.id}"
    body = [
        f'<defs><linearGradient id="{sky}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{style.tint}"/><stop offset="0.7" stop-color="#FFFDF7"/>'
        "</linearGradient></defs>",
        draw.el("rect", x=0, y=0, width=w, height=h, fill=f"url(#{sky})"),
        # the sun in the left-hand page's outer corner, clouds and birds where no text goes
        draw.el("circle", cx=26, cy=26, r=24, fill="#FFE7A3", opacity=0.55),
        nested_picture("sun", 8, 8, 36),
        nested_picture("cloud", 150, 64, 28),
        nested_picture("cloud", gutter + 176, 4, 26),
        nested_picture("cloud", gutter + 8, h - 122, 22),
    ]
    for x, y in ((52, 74), (63, 69), (gutter + 150, h - 110)):
        bird = f"M{x - 4} {y} Q{x - 2} {y - 2.6} {x} {y} Q{x + 2} {y - 2.6} {x + 4} {y}"
        body.append(draw.path(bird, stroke="#4A5078", width=0.7))
    scene = str(ctx.page.params.get("scene", SCENES.get(style.id, "")))
    if scene:  # the adventure's place, behind the family
        body.append(draw.el("ellipse", cx=left_mid, cy=h - 136, rx=70, ry=62, fill="#FFFFFF", opacity=0.5))
        body.append(nested_picture(scene, left_mid - 62, h - 202, 124))
    body += [_hill(h - 88, 9, 0, "#CFE8C0", w, h), _hill(h - 70, 8, 1, "#B9DDA6", w, h)]
    body.append(_hill(h - 46, 6, 0, "#A6D293", w, h))
    road = draw.d_path(
        ("M", (w + 10, h - 2)),
        ("C", (gutter + 150, h - 22, gutter + 100, h - 50, gutter + 24, h - 50)),
        ("S", (gutter - 50, h - 54, gutter - 80, h - 60)),
    )
    body += [
        draw.path(road, stroke="#F1DDB0", width=17),
        draw.path(road, stroke="#FBEFD2", width=14),
        draw.path(road, stroke="#FFFFFF", width=0.9, stroke_dasharray="3 3.6", opacity=0.9),
        nested_picture("tree", gutter + 168, h - 118, 48),
    ]
    for x, y, color in ((gutter + 40, h - 136, "#E4769D"), (gutter + 52, h - 144, "#F2B33D")):
        body += _balloon(x, y, color, gutter + 54, h - 100)
    body += _balloon(gutter + 63, h - 134, "#2E9FD6", gutter + 54, h - 100)
    body.append(nested_picture("butterfly", gutter + 142, h - 50, 14))
    for x, dy in (
        (gutter + 34, 34),
        (gutter + 124, 22),
        (gutter + 172, 46),
        (22, 38),
        (gutter - 24, 24),
        (190, 30),
    ):
        body.append(nested_picture("flower", x, h - dy, 12))
    for x, y, r in (
        (gutter + 22, 30, 3),
        (gutter + 196, 120, 2.4),
        (gutter - 16, 100, 2.2),
        (70, 40, 2.8),
        (196, 30, 2),
    ):
        body.append(draw.el("path", d=draw.star_points(x, y, r, r * 0.45), fill="#F2B33D"))
    return draw.svg(w, h, "".join(body), "spread-svg")


def _balloon(x: float, y: float, color: str, hand_x: float, hand_y: float) -> list[str]:
    """A balloon on a string held at (hand_x, hand_y)."""
    string = draw.path(f"M{x + 7} {y + 15} Q{x + 4} {y + 24} {hand_x} {hand_y}", stroke="#8E93AB", width=0.35)
    balloon = picture("balloon").inner("color", {"main": color})
    return [string, draw.el("svg", balloon, x=x, y=y, width=16, height=16, viewBox="0 0 100 100")]


def family_group(
    ctx: PageContext, family: Family, width: float, height: float
) -> tuple[Markup, list[dict[str, Any]]]:
    """The child (the character, waving when the sheet has a waving pose) in the middle of their family, and
    where each name tag goes (mm from the drawing's top-left). A small family stands close together; a big
    one gets smaller figures so that all of them fit."""
    members = list(family.members)
    # right to left: every other member on the child's right, the rest on the left, the first ones nearest
    order: list[Member | None] = [*reversed(members[0::2]), None, *members[1::2]]  # None: the child
    weights = [1.3 if who is None else 1.0 for who in order]
    unit = min(width / sum(weights), 40.0)  # a small family stands together in the middle
    scale = min(1.0, unit / 36)
    feet = height - 11
    body, front, tags = [], [], []
    right = (width + unit * sum(weights)) / 2
    for who, weight in zip(order, weights, strict=True):
        slot = unit * weight
        x, right = right - slot / 2, right - slot
        body.append(
            draw.el("ellipse", cx=x, cy=feet + 0.6, rx=slot * 0.34, ry=2.2, fill="#5E8F4E", opacity=0.18)
        )
        if who is None:
            img = ctx.assets.wave or ctx.assets.character
            aspect = ctx.assets.wave_aspect if ctx.assets.wave else ctx.assets.character_aspect
            h = 82 * max(scale, 0.75)
            if img is not None:
                w = h * aspect
                front.append(
                    draw.el(
                        "image",
                        href=uri(img),
                        x=x - w / 2,
                        y=feet + 1 - h,
                        width=w,
                        height=h,
                        preserveAspectRatio="xMidYMax meet",
                    )
                )
            tags.append({"x": x, "y": feet + 3, "w": slot - 1.5, "label": ctx.book.child.name, "child": True})
            continue
        index = members.index(who)
        scarf = people.SCARVES[index % len(people.SCARVES)] if who.scarf else None
        figure = people.person(who.drawn_as, people.OUTFITS[index % len(people.OUTFITS)], scarf=scarf)
        body.append(people.place(figure, x, feet + 1.2, 98 * scale))
        tags.append({"x": x, "y": feet + 3, "w": slot - 1.5, "label": who.label, "child": False})
    return draw.svg(width, height, "".join(body + front), "family-group"), tags


@page_type("section-opener", frame="full")
def section_opener(ctx: PageContext) -> Built:
    """Two facing pages: the right-hand one (read first) tells the story, the left-hand one shows the family
    and the stamp the adventure earns. Both show the same landscape, shifted by a page."""
    problems: list[str] = []
    family = family_of(ctx, problems)
    first = ctx.page.number % 2 == 0  # a spread starts on an even, right-hand page
    g = ctx.book.geometry
    style = ctx.style
    badge = Badge(style.id, str(ctx.page.params.get("badge", style.name_ar)), style.icon, style.color)
    inside = [
        {"icon": str(x.get("icon", "star")), "text": ctx.text(str(x["text"]))}
        for x in ctx.page.params.get("inside", [])
    ]
    group, tags = Markup(""), list[dict[str, Any]]()
    if family is not None and not first:
        group, tags = family_group(ctx, family, 186.0, 140.0)
    data = {
        "first": first,
        "art": spread_art(ctx),
        "art_size": spread_size(ctx),
        "shift": -g.trim_w if first else 0.0,  # the right-hand page shows the landscape's right half
        "adventure": ctx.num(int(ctx.page.params.get("adventure", style.slot))),
        "hook": ctx.text(ctx.page.instruction),
        "inside": inside,
        "badge": seal(badge),
        "badge_label": ctx.text(badge.label),
        "group": group,
        "tags": tags,
        "family": family.name if family else "",
    }
    return Built(data, None, problems)


# ---- treasure hunt ----------------------------------------------------------------------------------------

SHAPES_AR = {"circle": "دائرية", "square": "مربعة", "triangle": "مثلثة"}


@page_type("scavenger-hunt")
def scavenger_hunt(ctx: PageContext) -> Built:
    params = ctx.page.params
    if "items" in params:  # a checklist of named things to find (nature, the neighbourhood's heroes)
        return checklist_hunt(ctx)
    if "colors" in params:  # a color hunt («كنز الألوان»)
        from qamra_workbook.render.pages.adventures import color_hunt  # (adventures imports this module)

        return color_hunt(ctx)
    shape = str(params.get("shape", "circle"))
    find = int(params.get("find", 3))
    extra = int(params.get("challenge", 2))
    problems = []
    if find not in (3, 4):
        problems.append(f"the ⭐ hunt finds 3–4 things, not {find}")
    if extra and not 5 <= find + extra <= 7:
        problems.append(f"the ⭐⭐ hunt finds 5–7 things, not {find + extra}")
    if shape not in SHAPES_AR:
        problems.append(f"no hunt for {shape!r} yet (have {sorted(SHAPES_AR)})")
    examples = [str(x) for x in params.get("examples", ["plate", "orange", "clock"])]
    cards = [{"n": ctx.num(i + 1), "level": 1} for i in range(find)]
    cards += [{"n": ctx.num(find + i + 1), "level": 2} for i in range(extra)]
    target = Shape(shape_kind(shape if shape in SHAPES_AR else "circle"), 15, 15, 24, 24)
    shape_svg = draw.svg(
        30, 30, draw.shape(target, fill=ctx.style.tint, stroke=ctx.style.color, width=1.6), "hunt-shape"
    )
    data = {
        "character": uri(ctx.assets.character),
        "shape": shape_svg,
        "shape_ar": SHAPES_AR.get(shape, shape),
        "examples": [{"pic": ctx.pic(x), "word": strip_tashkeel(picture(x).word_ar)} for x in examples],
        "cards": cards,
        "count": [ctx.num(i + 1) for i in range(find + extra)],
        "found_q": ctx.text("كم شيئًا {وجدت/وجدتِ}؟"),
    }
    return Built(data, None, problems)


def checklist_hunt(ctx: PageContext) -> Built:
    """Things to find and tick: ⭐ `items`, ⭐⭐ `challenge_items` (each a picture id or {picture, label}),
    with a box to count how many times (`count: true`) and a place to compare two finds (`compare`)."""
    params = ctx.page.params

    def entry(raw: Any, level: int) -> dict[str, Any]:
        pic = str(raw["picture"] if isinstance(raw, Mapping) else raw)
        label = str(raw.get("label", "")) if isinstance(raw, Mapping) else ""
        return {
            "pic": ctx.pic(pic),
            "word": ctx.text(label) or strip_tashkeel(picture(pic).word_ar),
            "level": level,
        }

    items = [entry(x, 1) for x in params.get("items", [])] + [
        entry(x, 2) for x in params.get("challenge_items", [])
    ]
    problems = [] if 4 <= len(items) <= 9 else [f"a checklist hunt has 4–9 things, not {len(items)}"]
    data = {
        "mode": "checklist",
        "finds": items,
        "count": bool(params.get("count", False)),
        "compare": ctx.text(str(params.get("compare", ""))),
        "character": uri(ctx.assets.character),
        "found_q": ctx.text("كم شيئًا {وجدت/وجدتِ}؟"),
        "total": [ctx.num(i + 1) for i in range(len(items))],
        "safety": ctx.text(str(params["safety"])) if params.get("safety") else "",
    }
    return Built(data, None, problems)


# ---- shopping list ----------------------------------------------------------------------------------------

CHOICES = (
    {"key": "healthy", "icon": "heart", "label": "صحي", "color": "#E4769D"},
    {"key": "needed", "icon": "check", "label": "نحتاجه", "color": "#2FA36B"},
    {"key": "not-needed", "icon": "cross", "label": "لا نحتاجه", "color": "#8A8FA8"},
)


@page_type("shopping-list")
def shopping_list(ctx: PageContext) -> Built:
    params = ctx.page.params
    rows = int(params.get("rows", 4))
    products = [str(x) for x in params.get("products", ["apple", "milk", "bread", "candy", "carrot", "soda"])]
    problems = []
    if not 3 <= rows <= 5:
        problems.append(f"the list has 3–5 lines, not {rows}")
    if not 4 <= len(products) <= 6:
        problems.append(f"choose among 4–6 products, not {len(products)}")
    family = ctx.book.family
    data = {
        "rows": list(range(rows)),
        "count_dots": 5,
        "products": [{"pic": ctx.pic(x), "word": strip_tashkeel(picture(x).word_ar)} for x in products],
        "choices": CHOICES,
        "city": family.city if family else "",
        "character": uri(ctx.assets.character),
        "bag": ctx.pic("shopping-bag"),
        "choose": ctx.text(str(params.get("choose", "{اختر/اختاري} لكل شيء: صحي؟ نحتاجه؟"))),
        "safety": ctx.text(str(params["safety"])) if params.get("safety") else "",  # outdoors (A7 §9)
    }
    return Built(data, None, problems)


# ---- a recipe -------------------------------------------------------------------------------------------

SAFETY_NEEDS = {
    "the knife and heat are for grown-ups": ("سكين", "السكين", "النار", "الفرن"),
    "ask about allergies": ("حساسي",),
    "wash hands": ("نغسل", "اغسلوا", "غسل"),
}


def _ball(cx: float, cy: float, r: float, coated: bool = False) -> str:
    out = draw.el("circle", cx=cx, cy=cy, r=r, fill="#FFFBF0", stroke=OUTLINE, stroke_width=0.9)
    if coated:
        for i in range(9):
            a = i * 2.4
            rr = r * (0.25 + 0.6 * ((i * 37) % 10) / 10)
            out += draw.el(
                "circle", cx=cx + rr * math.cos(a), cy=cy + rr * math.sin(a), r=r * 0.13, fill="#7E8F3C"
            )
    return out + draw.el(
        "ellipse", cx=cx - r * 0.35, cy=cy - r * 0.38, rx=r * 0.22, ry=r * 0.13, fill="#FFFFFF"
    )


def step_picture(kind: str) -> Markup:
    """A recipe step as a small square scene (40 × 40 mm) composed from the picture library."""
    match kind:
        case "wash":
            drops = "".join(
                draw.el(
                    "svg", art.glyph("drop", "#4A95D3", 2.2), x=x, y=y, width=9, height=9, viewBox="0 0 24 24"
                )
                for x, y in ((6, 4), (17, 1.5), (28, 5))
            )
            body = drops + nested_picture("soap", 3, 9, 34)
        case "roll":
            body = (
                nested_picture("labneh", 0, 12, 29)
                + _ball(31, 31, 5.4)
                + _ball(33, 18, 4.6)
                + _ball(24, 8, 3.8)
            )
        case "dip":
            body = nested_picture("zaatar", 2, 10, 32) + _ball(30, 11, 5.6, coated=True)
        case "oil":
            plate = picture("plate").inner("color")
            body = (
                draw.el(
                    "svg",
                    plate,
                    x=6,
                    y=19,
                    width=33,
                    height=24,
                    viewBox="0 0 100 100",
                    preserveAspectRatio="none",
                )
                + _ball(15.5, 30, 4.2, True)
                + _ball(23, 32.5, 4.2, True)
                + _ball(30.5, 29.5, 4.2, True)
                + f'<g transform="rotate(-38 11 10)">{nested_picture("olive-oil", 0, -2, 23)}</g>'
                + draw.path("M17.5 16.5 Q19.2 20 19.8 23.5", stroke="#D9BE3A", width=1.4)
            )
        case "cut":  # the grown-up's knife: fruit on a board
            board = draw.el(
                "rect", x=3, y=22, width=34, height=15, rx=4, fill="#E7B070", stroke=OUTLINE, stroke_width=0.9
            )
            knife = draw.el(
                "svg", art.glyph("knife", OUTLINE, 1.8), x=22, y=2, width=16, height=16, viewBox="0 0 24 24"
            )
            body = board + nested_picture("apple", 5, 8, 17) + nested_picture("banana", 16, 14, 15) + knife
        case "mix":
            body = (
                nested_picture("fruit-bowl", 2, 8, 32)
                + f'<g transform="rotate(35 30 12)">{nested_picture("spoon", 22, -2, 20)}</g>'
            )
        case _:
            body = nested_picture(kind, 3, 3, 34)
    return draw.svg(40.0, 40.0, body, "step-pic")


def safety_items(ctx: PageContext, raw: Any) -> list[dict[str, str]]:
    """The safety box: a list of {icon, text}, or the activity's safety note split into its sentences, each
    with the icon its words call for (the knife and heat, allergies, washing hands)."""
    if isinstance(raw, list):
        return [{"icon": str(x.get("icon", "shield")), "text": ctx.text(str(x["text"]))} for x in raw]
    out = []
    for sentence in (x.strip() for x in re.split(r"(?<=[.!؟])\s+", str(raw)) if x.strip()):
        icon = "shield"
        if any(w in sentence for w in ("سكين", "السكين", "النار", "يقطّعون", "الفرن")):
            icon = "knife"
        elif "حساسي" in sentence:
            icon = "alert"
        elif any(w in sentence for w in ("نغسل", "اغسلوا")):
            icon = "drop"
        out.append({"icon": icon, "text": ctx.text(sentence.rstrip("."))})
    return out


@page_type("recipe-steps")
def recipe_steps(ctx: PageContext) -> Built:
    params = ctx.page.params
    ingredients = list(params.get("ingredients", []))
    steps = list(params.get("steps", []))
    shown = [int(x) for x in params.get("shown", range(1, len(steps) + 1))]
    safety = safety_items(ctx, params.get("safety", []))
    variant = str(params.get("variant", "steps"))  # steps · count (count the pieces) · layers (a layered cup)
    problems = [] if variant in ("steps", "count", "layers") else [f"no recipe variant {variant!r}"]
    if variant != "layers":
        if not 3 <= len(steps) <= 5:
            problems.append(f"a recipe has 3–5 step cards, not {len(steps)}")
        if sorted(shown) != list(range(1, len(steps) + 1)):
            problems.append("`shown` must list every step number once")
        elif shown == sorted(shown):
            problems.append("the step cards are shown out of order, for the child to number")
    if not 1 <= len(ingredients) <= 4:
        problems.append(f"a recipe counts 1–4 ingredients, not {len(ingredients)}")
    words = " ".join(str(i.get("name", "")) for i in ingredients)
    if NUTS_AND_RAW_EGGS.search(words):
        problems.append("no nuts or raw eggs by default (A7 §9)")
    safety_text = " ".join(s["text"] for s in safety)
    for need, words_needed in SAFETY_NEEDS.items():
        if not any(w in safety_text for w in words_needed):
            problems.append(f"the safety box must say: {need}")
    cards = []
    for number in shown:
        step = steps[number - 1] if 0 < number <= len(steps) else {"picture": "star", "text": ""}
        cards.append(
            {"pic": step_picture(str(step["picture"])), "text": ctx.text(str(step["text"])), "n": number}
        )
    layers, more = int(params.get("layers", 2)), int(params.get("challenge_layers", 2))
    data = {
        "variant": variant,
        "ingredients": [
            {
                "pic": ctx.pic(str(i["picture"])),
                "mini": ctx.pic(str(i["picture"]), css_class="pic mini"),
                "name": ctx.text(str(i["name"])),
                "count": int(i.get("count", 1)),
            }
            for i in ingredients
        ],
        "cup": art_cup(layers, more) if variant == "layers" else Markup(""),
        "layers": [{"n": ctx.num(k + 1), "level": 1 if k < layers else 2} for k in range(layers + more)],
        "cards": cards,
        "safety": safety,
        "count_label": ctx.text(str(params.get("count_label", "المكوّنات: {عُدّ/عُدّي} الملاعق"))),
        "steps_label": ctx.text(str(params.get("steps_label", "خطوات الطبخ: ما رقم كل بطاقة؟"))),
    }
    answer = [
        "الترتيب: "
        + "، ".join(f"{ctx.num(n)} {ctx.text(str(steps[n - 1]['text']))}" for n in range(1, len(steps) + 1))
    ]
    return Built(data, answer if steps else None, problems)


def art_cup(layers: int, more: int) -> Markup:
    from qamra_workbook.render.pages.family_art import cup_svg

    return cup_svg(layers, more)


# ---- feelings thermometer ---------------------------------------------------------------------------------

LEVELS: tuple[tuple[people.Feeling, str, str], ...] = (  # bottom to top: how big the feeling is
    ("calm", "هادئ", "#8FD3B6"),
    ("happy", "صغير", "#C9E27A"),
    ("uneasy", "متوسط", "#F7D774"),
    ("upset", "كبير", "#F5B06B"),
    ("angry", "كبير جدًا", "#EE8A7A"),
)
FEELINGS: tuple[tuple[people.Feeling, str], ...] = (("angry", "الغضب"), ("sad", "الحزن"), ("scared", "الخوف"))
STRATEGIES = (
    ("wind", "أتنفّس ببطء"),
    ("heart", "أطلب حضنًا"),
    ("talk", "أحكي لـ{adult}"),
    ("cup", "أشرب ماء"),
    ("crayon", "أرسم شعوري"),
    ("hand", "أعدّ حتى ٥"),
)


THERMO_W, THERMO_H = 34.0, 150.0  # drawing units; printed at THERMO_MM tall
THERMO_MM = 124.0
_TUBE_X, _TUBE_W, _TOP, _BULB_CY, _BULB_R = 11.0, 16.0, 4.0, 134.0, 13.0


def _band_h(levels: int) -> float:
    return (_BULB_CY - _BULB_R * 0.6 - _TOP - 6) / levels


def band_centers(levels: int) -> list[float]:
    """Where each level's band sits on the printed thermometer (mm from its top), bottom band first."""
    k = THERMO_MM / THERMO_H
    return [(_BULB_CY - _BULB_R - 4 - (i + 0.5) * _band_h(levels)) * k for i in range(levels)]


def thermometer(levels: Sequence[tuple[people.Feeling, str, str]]) -> Markup:
    """A tall, rounded thermometer with one band per level (outlined, for the child to color); the ticks
    point at the level labels on its left."""
    band_h = _band_h(len(levels))
    tube_cx = _TUBE_X + _TUBE_W / 2
    body = [
        draw.el(
            "rect",
            x=_TUBE_X - 2.2,
            y=_TOP - 2.2,
            width=_TUBE_W + 4.4,
            height=_BULB_CY - _TOP + 4,
            rx=(_TUBE_W + 4.4) / 2,
            fill="#FFFFFF",
            stroke=OUTLINE,
            stroke_width=1.1,
        ),
        draw.el(
            "circle",
            cx=tube_cx,
            cy=_BULB_CY,
            r=_BULB_R + 2.2,
            fill="#FFFFFF",
            stroke=OUTLINE,
            stroke_width=1.1,
        ),
        draw.el("circle", cx=tube_cx, cy=_BULB_CY, r=_BULB_R, fill=levels[0][2]),
        draw.el(
            "rect", x=_TUBE_X + 3, y=_BULB_CY - _BULB_R - 6, width=_TUBE_W - 6, height=10, fill=levels[0][2]
        ),
    ]
    for i, (_, _, color) in enumerate(levels):
        y = _BULB_CY - _BULB_R - 4 - (i + 1) * band_h
        body.append(
            draw.el(
                "rect",
                x=_TUBE_X + 1.2,
                y=y + 0.8,
                width=_TUBE_W - 2.4,
                height=band_h - 1.6,
                rx=3,
                fill="#FFFFFF",
                stroke=color,
                stroke_width=1.1,
                stroke_dasharray="2 1.4",
            )
        )
        mid = y + band_h / 2
        body.append(
            draw.path(
                f"M{_TUBE_X - 2.2} {draw.n(mid)} L{_TUBE_X - 6} {draw.n(mid)}", stroke=OUTLINE, width=0.8
            )
        )
    body.append(
        draw.el("ellipse", cx=tube_cx - 4, cy=_BULB_CY - 4, rx=2.6, ry=4, fill="#FFFFFF", opacity=0.6)
    )
    return draw.svg(THERMO_W, THERMO_H, "".join(body), "thermo")


@page_type("feelings-thermometer")
def feelings_thermometer(ctx: PageContext) -> Built:
    centers = band_centers(len(LEVELS))
    levels = [
        {
            "face": draw.svg(22, 22, people.feeling_face(kind, 11, 11, 10.2, color), "face"),
            "label": label,
            "color": color,
            "top": center,
        }
        for (kind, label, color), center in zip(LEVELS, centers, strict=True)
    ]
    data = {
        "thermo": thermometer(LEVELS),
        "thermo_mm": THERMO_MM,
        "levels": list(reversed(levels)),  # top to bottom, as printed
        "feelings": [
            {"face": draw.svg(22, 22, people.feeling_face(kind, 11, 11, 10.2), "face"), "label": label}
            for kind, label in FEELINGS
        ],
        "strategies": [{"icon": icon, "text": ctx.text(text)} for icon, text in STRATEGIES],
    }
    return Built(data)


# ---- the memory page --------------------------------------------------------------------------------------


@page_type("memory-page")
def memory_page(ctx: PageContext) -> Built:
    problems: list[str] = []
    family = family_of(ctx, problems)
    members = list(family.members) if family else []
    data = {
        "members": [m.label for m in members],
        "quote_from": ctx.text(str(ctx.page.params.get("quote_from", "كلمة من {adult}"))),
        "stars_q": ctx.text(str(ctx.page.params.get("stars_q", "كم نجمة {تعطي/تعطين} مغامرتنا؟"))),
        "stars": int(ctx.page.params.get("stars", 5)),  # how many stars to color (the plan's `stars`)
        "draw_label": ctx.text("أو {ارسم/ارسمي} ما فعلناه"),
        "with_q": "مع مَن كانت المغامرة؟",
        "star": art.stars(1, "big-star", fill="#FFFFFF", edge="#E2A32A"),
    }
    return Built(data, None, problems)


# ---- the 7-day family challenge (back pages) ------------------------------------------------------------

DAY_NAMES = ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع")


def challenge_board(
    ctx: PageContext, days: Sequence[Mapping[str, Any]]
) -> tuple[Markup, list[dict[str, Any]]]:
    """Seven stepping stones on a winding road (right to left, then back), ending at the trophy."""
    w, h = 186.0, 118.0
    rows = ((24.0, (160.0, 114.0, 68.0, 22.0)), (84.0, (40.0, 86.0, 132.0)))
    spots = [(x, y) for y, xs in rows for x in xs]
    road = draw.d_path(
        ("M", (184, 24)),
        ("L", (22, 24)),
        ("C", (-4, 24, -4, 84, 22, 84)),
        ("L", (40, 84)),
        ("L", (164, 84)),
    )
    body = [
        draw.path(road, stroke="#F4E3BE", width=15),
        draw.path(road, stroke="#FFF6E2", width=12),
        draw.path(road, stroke="#E8C77F", width=0.8, stroke_dasharray="2.6 3"),
    ]
    stones = []
    for k, ((x, y), day) in enumerate(zip(spots, days, strict=False)):
        color = _day_color(k)
        body += [
            draw.el("circle", cx=x, cy=y + 1.2, r=12.5, fill="#1C2140", opacity=0.1),
            draw.el("circle", cx=x, cy=y, r=12.5, fill="#FFFFFF"),
            draw.el("circle", cx=x, cy=y, r=10.8, fill=color),
            draw.el(
                "svg",
                art.glyph(str(day.get("icon", "star")), "#FFFFFF", 2.1),
                x=x - 6.4,
                y=y - 6.4,
                width=12.8,
                height=12.8,
                viewBox="0 0 24 24",
            ),
        ]
        stones.append(
            {
                "x": x,
                "y": y,
                "color": color,
                "n": ctx.num(k + 1),
                "text": ctx.text(str(day.get("text", ""))),
            }
        )
    # the trophy at the end of the road
    body.append(draw.el("circle", cx=172, cy=84, r=15, fill="#FFF1C9"))
    body.append(
        draw.el(
            "svg", art.glyph("trophy", "#E2A32A", 2), x=161, y=73, width=22, height=22, viewBox="0 0 24 24"
        )
    )
    return draw.svg(w, h, "".join(body), "board"), stones


def _day_color(k: int) -> str:
    return ("#F08A3E", "#2FA36B", "#E4675A", "#2E9FD6", "#8C6CCB", "#E4769D", "#23A094")[k % 7]


@page_type("seven-day-challenge")
def seven_day_challenge(ctx: PageContext) -> Built:
    days = list(ctx.page.params.get("days", []))
    problems = []
    if len(days) != 7:
        problems.append(f"the challenge has 7 days, not {len(days)}")
    texts = [str(d.get("text", "")) for d in days]
    if len(set(texts)) != len(texts):
        problems.append("a different family activity every day")
    board, stones = challenge_board(ctx, days)
    data = {
        "board": board,
        "stones": stones,
        "days": DAY_NAMES,
        "reward": ctx.text(str(ctx.page.params.get("reward", "مكافأة عائلتنا"))),
        "ideas": ctx.text(str(ctx.page.params.get("ideas", ""))),
        "gift": art.icon("gift"),
    }
    return Built(data, None, problems)


# ---- the family certificate (the last page) --------------------------------------------------------------


@page_type("certificate-family", frame="full")
def certificate_family(ctx: PageContext) -> Built:
    problems: list[str] = []
    family = family_of(ctx, problems)
    hero = ctx.assets.wave or ctx.assets.character
    data = {
        "line": ctx.text(str(ctx.page.params.get("line", "{أنهى/أنهت} كل مغامرات «مغامراتي مع عائلتي»"))),
        "name": ctx.book.child.name,
        "family": family.name if family else "",
        "members": ("مع " + members_line(family.members)) if family else "",
        "date": ctx.book.date_ar(),
        "character": uri(hero),
        "badges": [rosette(b, css_class="cert-seal") for b in CORE_BADGES],
        "star": _star,
        "ray": _ray,
        "medal": MEDAL,
    }
    return Built(data, None, problems)
