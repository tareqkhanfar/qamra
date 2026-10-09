"""The reward sticker sheet of «رحلتي الأولى للتعلّم» (one per stage) and of «قلبي يعرف الله» (one per volume),
printed on its own A4 sticker paper with kiss-cut lines, like the family book's sheet (`inserts.py`).

The sheet holds exactly what the book asks the child to stick, read from the very pages being printed, and a
few rewards on top:

* the journey: the hero sticker for the map (`journey-map`), one sticker for the dashed circle of every
  section opener (`journey-opener`: the stop's icon and colour, 15 mm to cover the 13 mm circle), the
  pictures a pattern train asks to stick in its empty wagon (each picture of the train, so the child still
  chooses), and the shapes of «نمطي أنا» (each shape `ceil(slots / shapes) + 2` times, sized to its slots);
* «قلبي يعرف الله»: one unit stamp for every circle of every passport page (`muslim-passport`: the front
  passport and the end card each ask for one per unit; each set is sized to its page's circle), and a strip of
  stars (or green leaves) for each home board a unit's closing or parent page asks the child to stick on;
* rewards: stars, Qamra's moon, «أحسنت/أحسنتِ» in the child's gender and the child's name.

The Islamic sheet is a page that is cut and thrown away (Addendum 10 §3.6, docs/islamic/content-guide.md):
no verse, dhikr, source, the name of Allah, ﷺ or a prophet's name in its own words, and no person (the
stamps are the units' icons). `sacred_words` checks the sheet's copy; the child's own name is theirs.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from markupsafe import Markup

from qamra_pdf.arabic_names import genitive
from qamra_workbook.pictures.islamic import glyph_svg, unit_glyph
from qamra_workbook.pictures.model import scallop_d, strip_tashkeel
from qamra_workbook.render import art, draw
from qamra_workbook.render.islamic_content import Passport
from qamra_workbook.render.islamic_units import Unit, volume_units
from qamra_workbook.render.pages.journey import STOPS, stop_key
from qamra_workbook.render.pages.journey_kit import picture, pid
from qamra_workbook.render.pages.workbook_common import W
from qamra_workbook.render.registry import Built, PageContext, page_type

CUT = "#EC008C"  # the printer's cut-contour colour (a kiss-cut line, never printed ink)
CUT_W = 0.3  # mm
EDGE = 0.6  # room round a sticker's drawing for its cut line, mm

# ---- the journey's needs ------------------------------------------------------------------------------

STATION_MM = 15.0  # the opener's dashed circle is 12.8 mm across (13.5 with its stroke)
HERO_W, HERO_H = 27.0, 40.0
WAGON_MM = 30.0  # the train's wagon is 36 × 40 mm, its picture 28 mm
SPARE = 2  # each shape of «نمطي أنا»: the simple repeat (ABAB…) and two more, for a pattern like AAB
SHAPE_COLORS = ("#F7C84A", "#E97A98", "#5E86D6")  # as the pattern page's legend (journey_shapes)
FINISH = {"label": "finish", "icon": "flag", "color": "#E5604E"}
STOP_STYLE = {s["label"]: s for s in STOPS}


@dataclass(frozen=True)
class Station:
    """A section opener's dashed circle, where the character stands on the map."""

    page: int
    stop: str  # the stop's key («أفكر»…) or "finish"

    @property
    def style(self) -> dict[str, str]:
        return FINISH if self.stop == "finish" else STOP_STYLE.get(self.stop, FINISH)


@dataclass(frozen=True)
class Wagon:
    """A pattern train whose empty wagon waits for a sticker: one sticker of each of its pictures."""

    page: int
    title: str
    choices: tuple[str, ...]  # picture ids


@dataclass(frozen=True)
class PatternRow:
    """«نمطي أنا»: empty slots the child fills with shape stickers."""

    page: int
    title: str
    slots: int
    shapes: tuple[str, ...]  # star, heart, circle

    @property
    def per_shape(self) -> int:
        return math.ceil(self.slots / max(len(self.shapes), 1)) + SPARE

    @property
    def slot_mm(self) -> float:
        """The slot's diameter, as `journey_shapes.create_your_pattern` draws it."""
        return 2 * min(12.0, (W - 50) / self.slots / 2)

    @property
    def sticker_mm(self) -> float:
        return round(self.slot_mm - 0.8, 1)


@dataclass(frozen=True)
class JourneyNeeds:
    stage: int
    hero: tuple[int, ...]  # the map pages («أَلْصِقْ مُلْصَقَ بَطَلِكَ»)
    stations: tuple[Station, ...]
    wagons: tuple[Wagon, ...]
    patterns: tuple[PatternRow, ...]
    reward_stars: int = 6
    moons: int = 2
    well_done: int = 3
    names: int = 2

    @property
    def asked(self) -> int:
        """How many stickers the book's pages ask for (the rewards not counted)."""
        return (
            len(self.hero)
            + len(self.stations)
            + sum(len(w.choices) for w in self.wagons)
            + sum(p.per_shape * len(p.shapes) for p in self.patterns)
        )

    @property
    def rewards(self) -> int:
        return self.reward_stars + self.moons + self.well_done + self.names

    @property
    def total(self) -> int:
        return self.asked + self.rewards


def _asks_to_stick(text: str) -> bool:
    return "لصق" in strip_tashkeel(text)


def journey_needs(pages: Sequence[Any], stage: int | None = None) -> JourneyNeeds:
    """What a stage's pages (engine `PageSpec`s, as printed) ask the child to stick."""
    hero, stations, wagons, patterns = [], [], [], []
    for p in pages:
        params = p.params
        if p.type == "journey-map":
            hero.append(p.number)
        elif p.type == "journey-opener":
            raw = params.get("here") or [params.get("stop")]
            spots = [stop_key(s) for s in (raw if isinstance(raw, list) else [raw]) if s]
            if spots:  # the dashed circle is drawn beside the last stop the character reaches
                stations.append(Station(p.number, spots[-1]))
        elif p.type == "pattern-train" and _asks_to_stick(p.instruction):
            seen: list[str] = []
            for word in params.get("sequence", []):
                if str(word) != "__" and pid(str(word)) not in seen:
                    seen.append(pid(str(word)))
            wagons.append(Wagon(p.number, p.title, tuple(seen)))
        elif p.type == "create-your-pattern" and params.get("stickers"):
            shapes = tuple(str(s) for s in params["stickers"])
            patterns.append(PatternRow(p.number, p.title, int(params.get("slots", 8)), shapes))
    first = next((p.stage for p in pages if getattr(p, "stage", None)), None)
    return JourneyNeeds(
        stage if stage is not None else int(first or 1),
        tuple(hero),
        tuple(stations),
        tuple(wagons),
        tuple(patterns),
    )


# ---- «قلبي يعرف الله»'s needs ------------------------------------------------------------------------

# the passport's stamp circle: r = 18.2 of the art's 40 units, drawn 32 mm wide (36 mm on the end card)
RING_MM = {"passport": 32 * 18.2 / 20, "journey-card": 36 * 18.2 / 20}
STAMP_MM = {"passport": 30.8, "journey-card": 34.4}  # covers the ring and its stroke
BOARD_MM = 13.0
BOARD_COUNT = 7  # a week on the board at home
# a closing or parent page that asks the child to stick a star (or a leaf) on a board at home
BOARD_ASK = re.compile(r"\S*(?:لصق|يضع)\S*\s+(?:الطفل\s+)?(نجمة|ورقة)")
BoardKind = Literal["star", "leaf"]


@dataclass(frozen=True)
class PassportPage:
    page: int
    title: str  # as printed for the child (gendered)
    layout: str  # passport | journey-card
    units: tuple[Unit, ...]
    stars: int

    @property
    def sticker_mm(self) -> float:
        return STAMP_MM.get(self.layout, STAMP_MM["passport"])


@dataclass(frozen=True)
class Board:
    page: int  # the first page that asks for it
    unit: str
    kind: BoardKind
    count: int = BOARD_COUNT


@dataclass(frozen=True)
class IslamicNeeds:
    volume: str
    passports: tuple[PassportPage, ...]
    boards: tuple[Board, ...]
    reward_stars: int = 8
    moons: int = 2
    well_done: int = 2
    names: int = 1

    @property
    def asked(self) -> int:
        return sum(len(p.units) for p in self.passports) + sum(b.count for b in self.boards)

    @property
    def rewards(self) -> int:
        return self.reward_stars + self.moons + self.well_done + self.names

    @property
    def total(self) -> int:
        return self.asked + self.rewards


def _strings(node: Any) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in _strings(v)]
    if isinstance(node, list | tuple):
        return [s for v in node for s in _strings(v)]
    return []


def islamic_needs(pages: Sequence[Any], volume: str = "") -> IslamicNeeds:
    """What a volume's pages (engine `PageSpec`s whose `params["page"]` is the content model) ask to stick."""
    passports: list[PassportPage] = []
    boards: dict[str, Board] = {}
    for p in pages:
        model = p.params.get("page")
        if model is None:
            continue
        volume = volume or str(getattr(model, "volume", ""))
        if isinstance(model, Passport):
            units = tuple(volume_units(model.volume))
            passports.append(PassportPage(p.number, p.title, model.layout, units, model.challenge_stars))
            continue
        for text in _strings(model.model_dump()):
            found = BOARD_ASK.search(strip_tashkeel(text))
            if not found:
                continue
            kind: BoardKind = "leaf" if found[1] == "ورقة" else "star"
            unit = str(getattr(model, "unit", "") or p.section)
            if unit not in boards:
                boards[unit] = Board(p.number, unit, kind)
            elif kind == "leaf":
                boards[unit] = Board(boards[unit].page, unit, "leaf")
    stars = max((pp.stars for pp in passports), default=8)
    return IslamicNeeds(volume, tuple(passports), tuple(boards.values()), reward_stars=stars)


# words the Islamic sheet's own copy never prints (it is cut and thrown away): the name of Allah, ﷺ, a
# prophet's honorific, the Quran, a surah, a verse
SACRED = re.compile(
    r"الله|ﷺ|عليه السلام|قرآن|سورة|آية"
    r"|(?<!\S)[وفبل]?(?:ال)?(?:رب|ربي|ربك|ربنا|ربه|نبي|نبيي|نبينا|أنبياء)(?!\S)"
)


def sacred_words(text: str) -> list[str]:
    return SACRED.findall(strip_tashkeel(text))


# ---- the stickers' art (an SVG in mm; every kiss-cut line has the class `cut`) -------------------------


def _cut(tag: str, **attrs: Any) -> str:
    return draw.el(
        tag, fill="none", stroke=CUT, stroke_width=CUT_W, stroke_linejoin="round", class_="cut", **attrs
    )


def _svg(size_w: float, size_h: float, body: str) -> Markup:
    return draw.svg(size_w + EDGE, size_h + EDGE, body, "rs-art")


def _nested(inner: str, x: float, y: float, size: float, box: str = "0 0 24 24") -> str:
    return draw.el("svg", inner, x=x, y=y, width=size, height=size, viewBox=box)


def disc_sticker(size: float, color: str, inner: str, *, ring: bool = False) -> Markup:
    """A round sticker: a white edge, a coloured disc and its drawing; the cut follows the edge."""
    c, r = (size + EDGE) / 2, size / 2
    body = [
        draw.el("circle", cx=c, cy=c, r=r, fill="#FFFFFF"),
        draw.el("circle", cx=c, cy=c, r=r - 1.0, fill=color),
    ]
    if ring:  # a stamp's inner dashed ring
        body.append(
            draw.el(
                "circle",
                cx=c,
                cy=c,
                r=r - 2.5,
                fill="none",
                stroke="#FFFFFF",
                stroke_width=0.45,
                stroke_dasharray="1.3 1.1",
                opacity=0.75,
            )
        )
    body += [inner, _cut("circle", cx=c, cy=c, r=r)]
    return _svg(size, size, "".join(body))


def station_art(station: Station, size: float = STATION_MM) -> Markup:
    style = station.style
    g = size * 0.56
    c = (size + EDGE) / 2
    glyph = _nested(art.glyph(style["icon"], "#FFFFFF", 2.4), c - g / 2, c - g / 2, g)
    return disc_sticker(size, style["color"], glyph)


def stamp_art(unit: Unit, size: float) -> Markup:
    """A unit's stamp: the unit's icon on its colour (the passport prints its ghost to stick this over)."""
    g = size * 0.5
    c = (size + EDGE) / 2
    glyph = _nested(glyph_svg(unit_glyph(unit.icon), unit.on_color, 1.7), c - g / 2, c - g / 2, g)
    return disc_sticker(size, unit.color, glyph, ring=True)


def star_art(size: float, color: str = "#F7C84A") -> Markup:
    """A five-pointed star sticker, its cut following the star (the family sheet's reward stars)."""
    c = (size + EDGE) / 2
    outer = size / 2
    art_outer = outer - 1.0
    body = draw.el(
        "path",
        d=draw.star_points(c, c + size * 0.03, art_outer, art_outer * 0.5),
        fill=color,
        stroke="#FFFFFF",
        stroke_width=0.9,
        stroke_linejoin="round",
    ) + _cut("path", d=draw.star_points(c, c + size * 0.03, outer, art_outer * 0.5 + 0.8))
    return _svg(size, size, body)


def heart_art(size: float, color: str) -> Markup:
    c = (size + EDGE) / 2
    h = size * 0.92
    body = draw.el(
        "path",
        d=draw.heart_path(c, c, size - 1.8, h - 1.8),
        fill=color,
        stroke="#FFFFFF",
        stroke_width=0.9,
        stroke_linejoin="round",
    ) + _cut("path", d=draw.heart_path(c, c, size, h))
    return _svg(size, size, body)


def circle_art(size: float, color: str) -> Markup:
    c = (size + EDGE) / 2
    body = draw.el(
        "circle", cx=c, cy=c, r=size / 2 - 0.9, fill=color, stroke="#FFFFFF", stroke_width=0.9
    ) + _cut("circle", cx=c, cy=c, r=size / 2)
    return _svg(size, size, body)


def shape_art(kind: str, size: float, color: str) -> Markup:
    if kind == "heart":
        return heart_art(size, color)
    if kind == "circle":
        return circle_art(size, color)
    return star_art(size, color)


def picture_art(word: str, size: float = WAGON_MM) -> Markup:
    """A library picture on a white rounded square (the wagon's picture, to stick in the empty wagon)."""
    o = EDGE / 2
    inner = size * 0.8
    body = (
        draw.el("rect", x=o, y=o, width=size, height=size, rx=4, fill="#FFFFFF")
        + draw.el(
            "rect",
            x=o + 1.1,
            y=o + 1.1,
            width=size - 2.2,
            height=size - 2.2,
            rx=3.2,
            fill="#FFF6F2",
            stroke="#E27D63",
            stroke_width=0.5,
        )
        + picture(word, o + (size - inner) / 2, o + (size - inner) / 2, inner)
        + _cut("rect", x=o, y=o, width=size, height=size, rx=4)
    )
    return _svg(size, size, body)


def leaf_d(cx: float, cy: float, w: float, h: float) -> str:
    top, bottom = cy - h / 2, cy + h / 2
    return (
        f"M{draw.n(cx)} {draw.n(bottom)} "
        f"C{draw.n(cx + w * 0.78)} {draw.n(cy + h * 0.16)} {draw.n(cx + w * 0.56)} {draw.n(cy - h * 0.4)} "
        f"{draw.n(cx)} {draw.n(top)} "
        f"C{draw.n(cx - w * 0.56)} {draw.n(cy - h * 0.4)} {draw.n(cx - w * 0.78)} {draw.n(cy + h * 0.16)} "
        f"{draw.n(cx)} {draw.n(bottom)} Z"
    )


def leaf_art(size: float = BOARD_MM) -> Markup:
    """A green leaf (the manners tree at home), with its vein, a little tilted; the cut follows it."""
    c = (size + EDGE) / 2
    w, h = (size - 1.8) * 0.66, size - 1.8
    turn = f"rotate(28 {draw.n(c)} {draw.n(c)})"
    body = (
        draw.el(
            "path",
            d=leaf_d(c, c, w, h),
            fill="#5FA37F",
            stroke="#FFFFFF",
            stroke_width=0.9,
            stroke_linejoin="round",
            transform=turn,
        )
        + draw.path(
            draw.d_path(("M", (c, c + h * 0.44)), ("Q", (c + w * 0.08, c, c, c - h * 0.34))),
            stroke="#DDF0E3",
            width=0.55,
            transform=turn,
        )
        + _cut("path", d=leaf_d(c, c, w + 1.6, h + 1.6), transform=turn)
    )
    return _svg(size, size, body)


def star8_art(size: float) -> Markup:
    """An eight-pointed gold star (the series' ornament) on a round sticker."""
    c = (size + EDGE) / 2
    r = size / 2 - 0.9
    pts = []
    for i in range(16):
        k = 1.0 if i % 2 == 0 else 0.64
        a = math.radians(-90 + 22.5 * i)
        pts.append((c + r * k * math.cos(a), c + r * k * math.sin(a)))
    body = (
        draw.el("circle", cx=c, cy=c, r=size / 2, fill="#FFFFFF")
        + draw.el("path", d=draw.polyline(pts) + " Z", fill="#E2A93A", stroke="#B9801A", stroke_width=0.35)
        + draw.el("circle", cx=c, cy=c, r=r * 0.34, fill="#FFF4D6")
        + _cut("circle", cx=c, cy=c, r=size / 2)
    )
    return _svg(size, size, body)


def moon_art(size: float, color: str) -> Markup:
    """Qamra's moon on a night disc, with two small stars."""
    c = (size + EDGE) / 2
    m = size * 0.66
    inner = (
        _nested(_mascot_body(), c - m / 2, c - m / 2 + 0.3, m, "0 0 100 100")
        + draw.el("path", d=draw.star_points(c + size * 0.26, c + size * 0.2, 1.1, 0.5), fill="#FFE7A3")
        + draw.el("path", d=draw.star_points(c - size * 0.3, c - size * 0.22, 0.8, 0.36), fill="#FFE7A3")
    )
    return disc_sticker(size, color, inner)


def _mascot_body() -> str:
    """The mascot's drawing, without its own <svg> wrapper (to nest it in a sticker)."""
    markup = str(art.mascot())
    start = markup.index(">") + 1
    return markup[start : markup.rindex("</svg>")]


def badge_art(size: float, color: str) -> Markup:
    """A scalloped badge for «أحسنت» (the words are set over it in HTML)."""
    c = (size + EDGE) / 2
    r = size / 2
    body = (
        draw.el("circle", cx=c, cy=c, r=r, fill="#FFFFFF")
        + draw.el("path", d=scallop_d(c, c, r - 2.3, r - 2.3, 16, 0.62), fill=color)
        + draw.el(
            "circle",
            cx=c,
            cy=c,
            r=r - 4.2,
            fill="none",
            stroke="#FFFFFF",
            stroke_width=0.45,
            stroke_dasharray="1.1 0.9",
            opacity=0.8,
        )
        + _cut("circle", cx=c, cy=c, r=r)
    )
    return _svg(size, size, body)


# ---- the sheet ---------------------------------------------------------------------------------------

Cell = dict[str, Any]
Block = dict[str, Any]


def _cell(kind: str, art_svg: Markup | None = None, size: float = 0.0, **more: Any) -> Cell:
    return {"kind": kind, "art": art_svg, "size": size, **more}


def _page(ctx: PageContext, n: int) -> str:
    return "ص " + ctx.num(n)


@dataclass(frozen=True)
class Palette:
    """The sheet's colours: the series' own."""

    badge: str  # «أحسنت»
    night: str  # the moon's disc
    name: str  # the name label
    name_ink: str
    title_font: str


JOURNEY_PALETTE = Palette("#2FA36B", "#3C468F", "#F2B33D", "#16204A", "title")
ISLAMIC_PALETTE = Palette("#1F5A46", "#22306A", "#1F5A46", "#FFE7A3", "kitab")

REWARDS_AR = {"journey": "مُلْصَقاتُ المُكافَأَةِ", "islamic": "مُلْصَقَاتُ الْمُكَافَأَةِ"}
WELL_DONE = {"journey": "{أَحْسَنْتَ/أَحْسَنْتِ}!", "islamic": "{أَحْسَنْتَ/أَحْسَنْتِ}!"}


@dataclass(frozen=True)
class RewardSizes:
    praise: float
    moon: float
    star: float
    name: tuple[float, float]


JOURNEY_REWARDS = RewardSizes(praise=28.0, moon=24.0, star=20.0, name=(52.0, 14.0))
ISLAMIC_REWARDS = RewardSizes(praise=23.0, moon=20.0, star=14.5, name=(46.0, 12.5))


def reward_blocks(ctx: PageContext, needs: JourneyNeeds | IslamicNeeds, palette: Palette) -> list[Block]:
    islamic = isinstance(needs, IslamicNeeds)
    size = ISLAMIC_REWARDS if islamic else JOURNEY_REWARDS
    well_done = ctx.text(WELL_DONE["islamic" if islamic else "journey"])
    praise = [
        _cell("badge", badge_art(size.praise, palette.badge), size.praise, text=well_done)
        for _ in range(needs.well_done)
    ]
    moons = [_cell("svg", moon_art(size.moon, palette.night), size.moon) for _ in range(needs.moons)]
    w, h = size.name
    names = [
        _cell("name", None, h, text=ctx.book.child.name, color=palette.name, ink=palette.name_ink, w=w, h=h)
        for _ in range(needs.names)
    ]
    stars = [
        _cell("svg", star8_art(size.star) if islamic else star_art(size.star), size.star)
        for _ in range(needs.reward_stars)
    ]
    if islamic:  # one row: the praise, the moons and the name; then the stars
        return [
            {"cells": [*praise, *moons, *names], "cols": len(praise) + len(moons) + len(names)},
            {"cells": stars, "cols": len(stars)},
        ]
    return [
        {"cells": [*praise, *moons], "cols": len(praise) + len(moons)},
        {"cells": names, "cols": 1},
        {"cells": stars, "cols": len(stars)},
    ]


def journey_groups(ctx: PageContext, needs: JourneyNeeds) -> list[dict[str, Any]]:
    hero_img = ctx.assets.character.resolve().as_uri() if ctx.assets.character else ""
    hero = [
        _cell("hero", None, HERO_H, img=hero_img, caption=_page(ctx, n), w=HERO_W, h=HERO_H)
        for n in needs.hero
    ]
    stations = [_cell("svg", station_art(s), STATION_MM, caption=_page(ctx, s.page)) for s in needs.stations]
    per_row = 6 if len(stations) > 10 else 5
    groups: list[dict[str, Any]] = [
        {
            "label": ctx.text("{مُلْصَقُ بَطَلِكَ/مُلْصَقُ بَطَلَتِكِ}، وَمُلْصَقٌ لِكُلِّ دائِرَةٍ عَلى الخَريطَةِ"),
            "icon": "flag",
            "blocks": [
                {"cells": hero, "cols": max(len(hero), 1)},
                {"cells": stations, "cols": per_row},
            ],
        }
    ]
    patterns: list[Block] = []
    for w in needs.wagons:
        cells = [_cell("svg", picture_art(c), WAGON_MM) for c in w.choices]
        patterns.append({"caption": f"{_page(ctx, w.page)} · {ctx.text(w.title)}", "cells": cells, "cols": 2})
    for row in needs.patterns:
        cells = [
            _cell("svg", shape_art(kind, row.sticker_mm, SHAPE_COLORS[k % 3]), row.sticker_mm)
            for k, kind in enumerate(row.shapes)
            for _ in range(row.per_shape)
        ]
        caption = f"{_page(ctx, row.page)} · {ctx.text(row.title)}"
        patterns.append({"caption": caption, "cells": cells, "cols": row.per_shape})
    if patterns:
        groups.append({"label": "مُلْصَقاتُ الأَنْماطِ", "icon": "pattern", "blocks": patterns})
    groups.append(
        {
            "label": REWARDS_AR["journey"],
            "icon": "trophy",
            "blocks": reward_blocks(ctx, needs, JOURNEY_PALETTE),
        }
    )
    return groups


BOARD_LABELS: dict[BoardKind, str] = {
    "star": "نُجُومٌ لِلَوْحَةِ الْبَيْتِ",
    "leaf": "أَوْرَاقٌ لِشَجَرَةِ الْأَخْلَاقِ",
}


def islamic_groups(ctx: PageContext, needs: IslamicNeeds) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for pp in needs.passports:
        cells = [
            _cell(
                "svg",
                stamp_art(u, pp.sticker_mm),
                pp.sticker_mm,
                badge=ctx.num(i),
                color=u.color,
                ink=u.on_color,
            )
            for i, u in enumerate(pp.units, start=1)
        ]
        groups.append(
            {
                "label": f"أَخْتَامُ وَحَدَاتِي: {ctx.text(pp.title)} ({_page(ctx, pp.page)})",
                "icon": "stamp",
                "blocks": [{"cells": cells, "cols": 5}],
            }
        )
    for kind in ("star", "leaf"):
        boards = [b for b in needs.boards if b.kind == kind]
        if not boards:
            continue
        blocks = []
        for b in boards:
            cells = [
                _cell("svg", leaf_art() if kind == "leaf" else star_art(BOARD_MM), BOARD_MM)
                for _ in range(b.count)
            ]
            blocks.append({"caption": _page(ctx, b.page), "cells": cells, "cols": math.ceil(b.count / 2)})
        groups.append(
            {"label": BOARD_LABELS[kind], "icon": "star" if kind == "star" else "leaf", "blocks": blocks}
        )
    groups.append(
        {
            "label": REWARDS_AR["islamic"],
            "icon": "trophy",
            "blocks": reward_blocks(ctx, needs, ISLAMIC_PALETTE),
        }
    )
    return groups


SHEET_TEXT = {
    "journey": {
        "owner": "مُلْصَقاتُ",
        "key": "ص: صَفْحَةُ الكِتابِ الَّتي يُلْصَقُ فيها المُلْصَقُ",
    },
    "islamic": {
        "owner": "مُلْصَقَاتُ",
        "key": "الرَّقْمُ فَوْقَ الْخَتْمِ: رَقْمُ وَحْدَتِهِ فِي الْجَوَازِ",
    },
}


def count_cells(groups: list[dict[str, Any]]) -> int:
    return sum(len(b["cells"]) for g in groups for b in g["blocks"])


@page_type("reward-stickers", frame="sheet")
def reward_stickers(ctx: PageContext) -> Built:
    """The book's sticker sheet (`params["needs"]`: `JourneyNeeds` or `IslamicNeeds`; `params["brand"]`: the
    footer's line). Every sticker has its kiss-cut line on the die layer."""
    needs = ctx.page.params.get("needs")
    problems: list[str] = []
    if isinstance(needs, JourneyNeeds):
        groups, text = journey_groups(ctx, needs), SHEET_TEXT["journey"]
    elif isinstance(needs, IslamicNeeds):
        groups, text = islamic_groups(ctx, needs), SHEET_TEXT["islamic"]
    else:
        return Built({"groups": [], "count": 0}, None, ["a sticker sheet needs the book's needs"])
    count = count_cells(groups)
    if count != needs.total:
        problems.append(f"the sheet holds {count} stickers, the book needs {needs.total}")
    brand = str(ctx.page.params.get("brand", "قمرة"))
    if isinstance(needs, IslamicNeeds):
        blocks = [b for g in groups for b in g["blocks"]]
        copy = [ctx.text(ctx.page.title), ctx.text(ctx.page.instruction), brand, *text.values()]
        copy += [g["label"] for g in groups] + [str(b.get("caption", "")) for b in blocks]
        copy += [str(c.get("text", "")) for b in blocks for c in b["cells"] if c["kind"] != "name"]
        found = sorted({w for line in copy for w in sacred_words(line)})
        if found:
            problems.append(f"the sticker sheet is thrown away: no sacred words on it ({', '.join(found)})")
    data = {
        "groups": groups,
        "count": count,
        "owner": genitive(ctx.book.child.name),  # «مُلْصَقاتُ أبي بكر»: the label owns the name
        "owner_label": text["owner"],
        "key": text["key"],
        "brand": brand,
        "font": JOURNEY_PALETTE.title_font if isinstance(needs, JourneyNeeds) else ISLAMIC_PALETTE.title_font,
    }
    return Built(data, None, problems)
