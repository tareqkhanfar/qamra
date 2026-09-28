"""The family book's inserts (Addendum 7 §6), printed on their own paper with cut lines: the sticker sheet
(passport stamps, rewards, the challenge's day stars, routine icons, with kiss-cut outlines) and the card
stock with the play money and blank price tags for the home shop.

Qamra play money is visibly fake (A7 §4.10, §9): Qamra's moon and stars, one big number, «للعب فقط» on
every note and coin; no portrait of a real person, no state emblem, no real currency's layout or name.
"""

from __future__ import annotations

import re
from typing import Any

from markupsafe import Markup, escape

from qamra_workbook.pictures.model import scallop_d
from qamra_workbook.render import art, draw
from qamra_workbook.render.pages.family import CORE_BADGES, seal, section_badges
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.spec import Numerals, format_number

CUT = "#EC008C"  # the printer's cut-contour color (a kiss-cut line, not printed ink)
FOR_PLAY = "للعب فقط"
# names and signs of real money that must never appear on play money
REAL_MONEY = re.compile(
    r"شيكل|شيقل|شواقل|دينار|دنانير|دولار|يورو|₪|\$|€|\b(JOD|JD|NIS|ILS|USD)\b", re.IGNORECASE
)

REWARDS = (  # shape, word, color, text color
    ("star", "رائع!", "#F7C84A", "#7A4E00"),
    ("heart", "{أحسنت/أحسنتِ}!", "#E4769D", "#FFFFFF"),
    ("sun", "{بطل/بطلة}!", "#F08A3E", "#FFFFFF"),
    ("cloud", "شكرًا!", "#2E9FD6", "#FFFFFF"),
    ("burst", "ممتاز!", "#8C6CCB", "#FFFFFF"),
    ("flower", "هيّا!", "#2FA36B", "#FFFFFF"),
)
CHALLENGE_DAYS = 7  # one star sticker per day of «تحدي العائلة الكبير»
ROUTINE = (  # the plan's routine icons: waking, breakfast, teeth, clothes, play, reading, sleep
    ("sun", "أستيقظ", "#F2B33D"),
    ("plate", "أفطر", "#F08A3E"),
    ("toothbrush", "أنظّف أسناني", "#2E9FD6"),
    ("shirt", "ألبس ثيابي", "#E4769D"),
    ("ball", "ألعب", "#2FA36B"),
    ("book", "أقرأ", "#8C6CCB"),
    ("moon", "أنام", "#3C468F"),
)


def _shape(kind: str, cx: float, cy: float, r: float) -> str:
    """The outline of a reward sticker (path data)."""
    match kind:
        case "star":
            return draw.star_points(cx, cy + r * 0.08, r, r * 0.62, 5)
        case "heart":
            return draw.heart_path(cx, cy + r * 0.04, r * 2.05, r * 1.85)
        case "sun":
            return draw.star_points(cx, cy, r, r * 0.84, 12)
        case "cloud":
            return scallop_d(cx, cy, r, r * 0.8, 9, 0.62)
        case "burst":
            return draw.star_points(cx, cy, r, r * 0.8, 16)
        case _:
            return scallop_d(cx, cy, r * 0.96, r * 0.96, 6, 0.9)


def reward_sticker(kind: str, color: str) -> Markup:
    """A reward sticker (the word is set over it in HTML) with its kiss-cut line."""
    d = _shape(kind, 20, 20, 16.5)
    body = (
        draw.el("path", d=_shape(kind, 20, 20, 18.6), fill="none", stroke=CUT, stroke_width=0.35)
        + draw.el("path", d=d, fill="#FFFFFF", stroke="#FFFFFF", stroke_width=2.4, stroke_linejoin="round")
        + draw.el("path", d=d, fill=color, stroke_linejoin="round")
    )
    return Markup(f'<svg class="reward-art" viewBox="0 0 40 40" aria-hidden="true">{body}</svg>')  # nosec B704


def cut_ring(r: float = 18.8) -> Markup:
    """A round kiss-cut line, in a 40-unit box drawn at the sticker's size (the passport slot is 27 mm with a
    24.8 mm ring; the cut is 25.4 mm across, so a stuck stamp covers its slot)."""
    body = draw.el("circle", cx=20, cy=20, r=r, fill="none", stroke=CUT, stroke_width=0.5)
    return Markup(f'<svg class="cut" viewBox="0 0 40 40" aria-hidden="true">{body}</svg>')  # nosec B704


def day_star(label: str) -> Markup:
    """A star sticker for one day of the family challenge (`label`: the day, in the book's numerals), with
    its kiss-cut line."""
    d = draw.star_points(20, 21, 17, 8.6)
    body = (
        draw.el(
            "path",
            d=draw.star_points(20, 21, 19.6, 10.6),
            fill="none",
            stroke=CUT,
            stroke_width=0.5,
            stroke_linejoin="round",
        )
        + draw.el("path", d=d, fill="#F7C84A", stroke="#FFFFFF", stroke_width=1.6, stroke_linejoin="round")
        + draw.el("circle", cx=20, cy=22, r=6.2, fill="#FFFFFF")
    )
    svg = f'<svg class="day-art" viewBox="0 0 40 40" aria-hidden="true">{body}</svg>'
    return Markup(f"{svg}<b>{escape(label)}</b>")  # nosec B704


MAX_STAMPS = 18  # three rows of six at the passport slot's size


@page_type("badge-sticker-sheet", frame="sheet")
def badge_sticker_sheet(ctx: PageContext) -> Built:
    """The seven badges and each adventure's stamp; an adventure whose stamp is one of the badges (the chef
    earns «طبّاخ صغير») shares its sticker."""
    labels: set[str] = set()
    badges = []
    for badge in [*CORE_BADGES, *section_badges(ctx)]:
        label = ctx.text(badge.label)
        if label not in labels:
            labels.add(label)
            badges.append((badge, label))
    problems = (
        [] if len(badges) <= MAX_STAMPS else [f"the sheet holds {MAX_STAMPS} stamps, not {len(badges)}"]
    )
    data = {
        "badges": [{"svg": seal(b), "label": label, "color": b.color} for b, label in badges],
        "rewards": [
            {"svg": reward_sticker(k, c), "word": ctx.text(w), "kind": k, "ink": ink}
            for k, w, c, ink in REWARDS
        ],
        "days": [day_star(ctx.num(i + 1)) for i in range(CHALLENGE_DAYS)],
        "routine": [{"icon": i, "label": t, "color": c} for i, t, c in ROUTINE],
        "cut": cut_ring(),
        "owner": ctx.book.child.name,
    }
    return Built(data, None, problems)


# ---- Qamra play money ---------------------------------------------------------------------------------

NOTE_COLORS = {  # pastel, nothing like a real banknote
    1: ("#FFE9A8", "#B27A0C"),
    2: ("#FFD9C2", "#B25A20"),
    5: ("#CFEFE0", "#1E7A52"),
    10: ("#D6E8FA", "#215A8C"),
    20: ("#E6DDF7", "#5B3E9C"),
    50: ("#FBDDE8", "#9A2F5C"),
}


def qamra_count(n: int, numerals: Numerals = "hindi") -> str:
    """«قمرة واحدة», «قمرتان», «٥ قمرات», «٢٠ قمرة»: the play currency's name agrees with the number."""
    if n == 1:
        return "قمرة واحدة"
    if n == 2:
        return "قمرتان"
    return f"{format_number(n, numerals)} {'قمرات' if 3 <= n <= 10 else 'قمرة'}"


def note_art(color: str, deep: str) -> Markup:
    """The note's background: a star burst for the number, stars and a crescent (Qamra's, not a state's)."""
    w, h = 88.0, 42.0
    body = [
        draw.el(
            "rect", x=0.5, y=0.5, width=w - 1, height=h - 1, rx=5, fill=color, stroke=deep, stroke_width=0.8
        ),
        draw.el(
            "rect",
            x=3,
            y=3,
            width=w - 6,
            height=h - 6,
            rx=3.4,
            fill="none",
            stroke="#FFFFFF",
            stroke_width=0.7,
            stroke_dasharray="1.6 1.4",
        ),
        draw.el("path", d=draw.star_points(18, 21, 14.5, 11.2, 14), fill="#FFFFFF"),
        draw.el("path", d=draw.star_points(18, 21, 12.5, 9.6, 14), fill=deep, opacity=0.9),
    ]
    for x, y, r in ((40, 8, 1.6), (47, 34.5, 1.3), (80, 9, 1.4), (33, 33, 1.1), (60, 6.5, 1.1)):
        body.append(draw.el("path", d=draw.star_points(x, y, r, r * 0.45), fill="#FFFFFF"))
    return draw.svg(w, h, "".join(body), "note-art")


def coin_art(value: int) -> Markup:
    gold = value % 2 == 1
    rim, face, deep = ("#F2C14E", "#FBE08A", "#A8740F") if gold else ("#BFCBE0", "#E4EAF4", "#566482")
    body = (
        draw.el("path", d=scallop_d(20, 20, 19, 19, 22, 0.62), fill=rim, stroke=deep, stroke_width=0.6)
        + draw.el("circle", cx=20, cy=20, r=15.6, fill=face, stroke=deep, stroke_width=0.5)
        + draw.el(
            "circle",
            cx=20,
            cy=20,
            r=13.8,
            fill="none",
            stroke=deep,
            stroke_width=0.35,
            stroke_dasharray="1 1.1",
        )
        + draw.el("path", d="M17.1 6.9 A3.2 3.2 0 1 0 21.1 10.9 A2.5 2.5 0 0 1 17.1 6.9 Z", fill=deep)
        + draw.el("path", d=draw.star_points(23.6, 8.4, 1.5, 0.7), fill=deep)
    )
    return draw.svg(40, 40, body, "coin-art")


@page_type("play-money", frame="sheet")
def play_money(ctx: PageContext) -> Built:
    params = ctx.page.params
    notes_in = [int(x) for x in params.get("notes", [5, 5, 10, 10, 20, 20])]
    coins_in = [int(x) for x in params.get("coins", [1] * 6 + [2] * 6)]
    problems = []
    for value in {*notes_in, *coins_in}:
        if value not in NOTE_COLORS:
            problems.append(f"no Qamra note or coin of {value}")
    notes: list[dict[str, Any]] = []
    for v in notes_in:
        color, deep = NOTE_COLORS.get(v, NOTE_COLORS[5])
        notes.append(
            {
                "art": note_art(color, deep),
                "value": ctx.num(v),
                "words": qamra_count(v, ctx.numerals),
                "deep": deep,
                "play": FOR_PLAY,
            }
        )
    coins = [{"art": coin_art(v), "value": ctx.num(v), "play": FOR_PLAY} for v in coins_in]
    printed = " ".join(
        [*(n["words"] for n in notes), ctx.text(ctx.page.title), ctx.text(ctx.page.instruction)]
    )
    if REAL_MONEY.search(printed):
        problems.append("play money never names or shows a real currency")
    tags = int(params.get("price_tags", 5))  # blank price tags for the home shop (A7 §4.2)
    data = {
        "notes": notes,
        "coins": coins,
        "tags": list(range(tags)),
        "banner": f"{FOR_PLAY} — نقود قمرة",
        "scissors": art.icon("scissors"),
    }
    return Built(data, None, problems)
