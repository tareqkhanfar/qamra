"""«أُلَوِّنُ رَمَضان»: the scenes (see `scenes.registry`), in book order (content/coloring/ramadan.yaml).

Each scene fills its 186 × 232 mm box: one clear subject, a simple supporting background and a few friendly
details. Night scenes stay line art (no black fills): the night shows through the crescent, the stars and
the lanterns; the colour version paints the sky with `pen.tint` only.
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.coloring.ink import (
    BLUE,
    CREAM,
    GOLD,
    GRASS,
    GREEN,
    HILL_FAR,
    NAVY,
    NIGHT_SKY,
    ORANGE,
    PINK,
    PURPLE,
    RED,
    SAND,
    SKY,
    STONE,
    STONE_DEEP,
    TEAL,
    WOOD,
    WOOD_DARK,
    YELLOW,
    Pen,
    arch,
    c,
    e,
    p,
    place,
    polar,
    poly,
    rect,
    scallop,
    seg,
)
from qamra_workbook.coloring.parts import common as cm
from qamra_workbook.coloring.parts import ramadan as rp
from qamra_workbook.coloring.scenes.registry import scene

Spot = tuple[float, float, float]


def _stars(pen: Pen, spots: list[Spot], fill: str = YELLOW) -> str:
    return "".join(place(pen, rp.twinkle, x, y, s, fill=fill) for x, y, s in spots)


def _sky(pen: Pen, w: float, h: float, fill: str = NIGHT_SKY) -> str:
    return pen.tint(rect(-2, -2, w + 4, h + 4), fill=fill)


def _floor(pen: Pen, w: float, y: float, h: float, fill: str = rp.FLOOR) -> str:
    return pen.shape(rect(-5, y, w + 10, h - y + 10), fill=fill)


# ---- 1. the crescent over the town ---------------------------------------------------------------------


@scene("ramadan", "crescent-sighting")
def crescent_sighting(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h)]
    out.append(place(pen, rp.moon, 140, 46, 1.35, turn=200))
    out.append(_stars(pen, [(24, 26, 1.0), (72, 18, 0.8), (92, 58, 0.7), (178, 18, 0.7), (26, 70, 0.6)]))
    # the town beyond the roof's low wall: domes, a minaret, flat roofs
    out.append(place(pen, rp.house, 22, 176, 1.0, w=48, h=60, dome=True, lit=True, door=False, windows=1))
    out.append(place(pen, rp.house, 160, 176, 1.0, w=50, h=52, lit=True, door=False))
    out.append(place(pen, rp.minaret, 172, 176, 0.62))
    out.append(place(pen, rp.mosque, 104, 176, 0.62, minarets=0))
    # the roof: a low stone wall behind the family, the floor under them
    out.append(pen.shape(rect(-5, 150, w + 10, 36), fill=STONE))
    out.append(pen.shape(rect(-5, 145, w + 10, 9, 2), fill=STONE_DEEP))
    out.append(
        pen.stroke(
            *[seg(x, 154, x, 168) for x in (30, 80, 130, 175)],
            *[seg(x, 168, x, 186) for x in (5, 55, 105, 155)],
            seg(-5, 168, w + 5, 168),
        )
    )
    out.append(_floor(pen, w, 186, h))
    out.append(pen.stroke(seg(-5, 205, w + 5, 205)))
    out.append(place(pen, rp.fanous, 16, 145 - 47 * 0.4, 0.4, kind="round"))
    out.append(place(pen, cm.man, 60, 226, 0.88, pose="reach", robe="#E8E1D2"))
    out.append(place(pen, cm.child, 124, 226, 0.95, pose="wave", dress=PINK, look=0.6))
    return "".join(out)


# ---- 2. the big lantern ---------------------------------------------------------------------------------


@scene("ramadan", "lantern")
def lantern(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h, "#4A3F8F")]
    out.append(pen.stroke(seg(93, -5, 93, 22), weight=2.6))
    rays = []
    for ang in (20, 160, 200, 340, 45, 135):
        x1, y1 = polar(93, 132, 70, ang)
        x2, y2 = polar(93, 132, 82, ang)
        rays.append(seg(x1, y1, x2, y2))
    out.append(pen.stroke(*rays))
    out.append(place(pen, rp.fanous, 93, 122, 1.86, glass=YELLOW, cap=RED, ornate=True))
    out.append(place(pen, rp.moon, 28, 34, 0.9, turn=200))
    out.append(
        _stars(
            pen,
            [
                (160, 30, 1.0),
                (176, 128, 0.7),
                (10, 128, 0.7),
                (26, 204, 1.0),
                (162, 208, 1.0),
                (150, 62, 0.6),
                (36, 70, 0.6),
            ],
        )
    )
    return "".join(out)


# ---- 3. lanterns and bunting across the street ----------------------------------------------------------


@scene("ramadan", "street-lanterns")
def street_lanterns(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h)]
    out.append(place(pen, rp.moon, 93, 28, 0.8, turn=200))
    out.append(_stars(pen, [(70, 18, 0.6), (118, 44, 0.6)]))
    out.append(place(pen, rp.mosque, 93, 206, 0.46))
    out.append(place(pen, rp.house, 22, 206, 1.0, w=58, h=190, rows=3, lit=True))
    out.append(place(pen, rp.house, 164, 206, 1.0, w=58, h=190, rows=3, lit=True))
    out.append(pen.shape(p("M-5 206 L191 206 L191 240 L-5 240 Z"), fill=STONE))
    out.append(
        pen.stroke(
            seg(-5, 218, 191, 218),
            *[seg(x, 206, x + 2, 218) for x in (20, 70, 120, 170)],
            *[seg(x, 218, x + 2, 232) for x in (45, 95, 145)],
        )
    )
    # a cord of lanterns and a cord of flags across the street
    a, b = (51, 46), (135, 46)
    out.append(rp.cord(pen, a, b, 14))
    kinds = (("tall", RED), ("round", TEAL), ("tall", PURPLE))
    for (x, y), (kind, cap) in zip(rp.garland_points(a, b, 14, 3), kinds, strict=True):
        out.append(pen.stroke(seg(x, y, x, y + 4)))
        out.append(place(pen, rp.fanous, x, y + 4 + 54 * 0.34, 0.34, kind=kind, cap=cap))
    out.append(rp.bunting(pen, (51, 102), (135, 102), 8, 5, size=12))
    # a boy walks with his own little lantern
    s, bx = 0.74, 52.0
    out.append(place(pen, cm.child, bx, 229, s, girl=False, pose="reach", shirt=TEAL, look=0.3))
    hx, hy = bx + 24 * s, 229 - 70 * s
    out.append(pen.stroke(seg(hx, hy, hx, hy + 5)))
    out.append(place(pen, rp.fanous, hx, hy + 5 + 54 * 0.28, 0.28, kind="round", cap=RED))
    out.append(rp.hands_on(pen, (hx, hy), r=3.9 * s))
    return "".join(out)


# ---- 4. decorating the house ---------------------------------------------------------------------------


@scene("ramadan", "decorating-home")
def decorating_home(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL)]
    # the window with the night outside
    out.append(pen.shape(p("M58 108 L58 42 A35 35 0 0 1 128 42 L128 108 Z"), fill=STONE_DEEP))
    out.append(pen.shape(p("M64 104 L64 42 A29 29 0 0 1 122 42 L122 104 Z"), fill=NIGHT_SKY))
    out.append(place(pen, rp.moon, 104, 40, 0.7, turn=200))
    out.append(_stars(pen, [(78, 34, 0.6), (80, 78, 0.55), (108, 84, 0.6)]))
    out.append(pen.stroke(seg(93, 13, 93, 104), seg(64, 64, 122, 64)))
    out.append(pen.shape(rect(52, 104, 82, 8, 2), fill=WOOD))
    # lanterns already hung
    for x, kind, fill in ((22.0, "classic", RED), (164.0, "tall", TEAL)):
        out.append(_hanging_lantern(pen, x, 36, 0.44, kind=kind, cap=fill))
    out.append(_floor(pen, w, 184, h))
    out.append(pen.shape(e(93, 214, 78, 14), fill=PURPLE))
    out.append(pen.stroke(e(93, 214, 66, 9)))
    # a big lantern standing on the floor, waiting to be hung
    out.append(place(pen, rp.fanous, 93, 214 - 47 * 0.6, 0.6, kind="round", cap=RED))
    # two children hold up a garland of stars
    s = 1.2
    boy_x, girl_x = 28.0, 158.0
    hand_l = (boy_x + 21 * s, 226 - 84 * s)
    hand_r = (girl_x - 21 * s, 226 - 84 * s)
    out.append(place(pen, cm.child, boy_x, 226, s, girl=False, pose="wave", shirt=ORANGE, look=0.4))
    out.append(
        place(pen, cm.child, girl_x, 226, s, pose="wave", dress=PINK, hair="ponytail", flip=True, look=0.4)
    )
    out.append(rp.cord(pen, hand_l, hand_r, 14))
    for i, (x, y) in enumerate(rp.garland_points(hand_l, hand_r, 14, 4)):
        out.append(pen.stroke(seg(x, y, x, y + 5)))
        out.append(place(pen, rp.twinkle, x, y + 12, 0.95, fill=(YELLOW, GOLD, ORANGE, YELLOW)[i]))
    out.append(rp.hands_on(pen, hand_l, hand_r, r=3.9 * s))
    return "".join(out)


# ---- 5. the mosque at sunset ---------------------------------------------------------------------------


@scene("ramadan", "mosque-sunset")
def mosque_sunset(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h, rp.DUSK)]
    # the big setting sun behind the dome
    out.append(pen.shape(c(90, 150, 82), fill="#FBC67E"))
    out.append(pen.shape(c(90, 150, 66), fill=rp.SUNSET))
    out.append(place(pen, cm.cloud, 30, 26, 0.9))
    out.append(place(pen, cm.cloud, 160, 40, 0.8))
    out.append(place(pen, cm.bird_v, 150, 84, 1.0) + place(pen, cm.bird_v, 164, 74, 0.8))
    out.append(cm.hills(pen, w, 172, 7, 3, fill=HILL_FAR, seed=4))
    out.append(cm.ground(pen, w, 198, fill=GRASS))
    out.append(place(pen, rp.mosque, 90, 200, 0.95))
    out.append(pen.shape(p("M80 200 L100 200 L116 240 L64 240 Z"), fill=STONE))
    out.append(place(pen, cm.bush, 30, 224, 0.9) + place(pen, cm.bush, 156, 224, 0.85))
    out.append(
        place(pen, cm.flower, 12, 232, 0.8, fill=RED) + place(pen, cm.flower, 176, 232, 0.8, fill=PINK)
    )
    out.append(place(pen, cm.tuft, 50, 230, 1.0) + place(pen, cm.tuft, 132, 230, 1.0))
    return "".join(out)


# ---- shared bits of the table scenes ----------------------------------------------------------------------


def _hem(
    pen: Pen, x0: float, x1: float, top: float, bottom: float, step: float = 14.0, fill: str = rp.CLOTH
) -> str:
    """A tablecloth's front falling from `top` to a scalloped hem at `bottom`."""
    n = max(1, round((x1 - x0) / step))
    st = (x1 - x0) / n
    d = f"M{x0:.2f} {top:.2f} L{x1:.2f} {top:.2f} L{x1:.2f} {bottom:.2f}"
    for i in range(n):
        x = x1 - st * (i + 1)
        d += f" A{st / 2:.2f} {st / 2.6:.2f} 0 0 1 {x:.2f} {bottom:.2f}"
    return pen.shape(p(d + " Z"), fill=fill)


def _table_top(pen: Pen, w: float, back: float, front: float, fill: str = rp.CLOTH) -> str:
    return pen.shape(rect(-5, back, w + 10, front - back), fill=fill)


def _cloth_band(pen: Pen, w: float, y: float, fills: tuple[str, ...] = (RED, GOLD, TEAL)) -> str:
    """A row of big diamonds across a tablecloth's front (to colour in turns)."""
    out = []
    for i, x in enumerate(range(8, int(w), 20)):
        pts = [(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)]
        out.append(pen.shape(poly(pts), fill=fills[i % len(fills)]))
    return "".join(out)


def _window(
    pen: Pen, x: float, y: float, ww: float, wh: float, sky: str = NIGHT_SKY, bars: bool = True
) -> str:
    """An arched window ww wide and wh tall standing on (x, y) (its sill's middle), seen from inside."""
    out = [pen.shape(arch(x - ww / 2 - 6, y, ww + 12, wh + 6), fill=STONE_DEEP)]
    out.append(pen.shape(arch(x - ww / 2, y, ww, wh), fill=sky))
    if bars:
        out.append(
            pen.stroke(seg(x, y - wh + 2, x, y), seg(x - ww / 2, y - wh * 0.42, x + ww / 2, y - wh * 0.42))
        )
    out.append(pen.shape(rect(x - ww / 2 - 10, y, ww + 20, 7, 2), fill=WOOD))
    return "".join(out)


def _hanging_lantern(pen: Pen, x: float, length: float, s: float, **opts: Any) -> str:
    return pen.stroke(seg(x, -5, x, length)) + place(pen, rp.fanous, x, length + 54 * s, s, **opts)


# ---- 6. dates and water ----------------------------------------------------------------------------------


@scene("ramadan", "dates-water")
def dates_water(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL)]
    out.append(_window(pen, 52, 96, 56, 76, sky=rp.DUSK))
    out.append(place(pen, rp.moon, 64, 46, 0.55, turn=200))
    out.append(_stars(pen, [(38, 40, 0.5)]))
    out.append(_hanging_lantern(pen, 150, 16, 0.5, kind="round", cap=TEAL))
    out.append(_table_top(pen, w, 150, 176))
    out.append(_hem(pen, -5, w + 5, 176, 224, 16))
    out.append(_cloth_band(pen, w, 200))
    out.append(place(pen, rp.jug, 46, 182, 1.38))
    out.append(place(pen, rp.glass, 150, 174, 1.2, drink=rp.WATER))
    out.append(place(pen, rp.glass, 168, 186, 1.1, drink=rp.WATER))
    out.append(place(pen, rp.bowl, 104, 192, 2.0, food="dates", fill=GOLD))
    return "".join(out)


# ---- 7. the iftar table -------------------------------------------------------------------------------


@scene("ramadan", "iftar-table")
def iftar_table(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL)]
    out.append(_window(pen, 93, 64, 40, 48, sky=rp.DUSK, bars=False))
    out.append(place(pen, rp.moon, 100, 36, 0.42, turn=200))
    out.append(_hanging_lantern(pen, 22, 8, 0.4, cap=RED))
    out.append(_hanging_lantern(pen, 164, 8, 0.4, kind="tall", cap=TEAL))
    back, front = 140.0, 178.0
    s = 0.95
    people: tuple[tuple[float, str, str, dict[str, Any]], ...] = (
        (27.0, "dad", "#E8E1D2", {}),
        (71.0, "girl", PINK, {"hair": "ponytail"}),
        (115.0, "boy", ORANGE, {}),
        (159.0, "mom", NAVY, {}),
    )
    hands: list[tuple[float, float]] = []
    for x, who, top, opts in people:
        reach = 13.0 if who in ("girl", "boy") else 17.0
        hp = ((-reach, 7.0), (reach, 7.0))
        out.append(place(pen, rp.bust, x, back, s, who=who, top=top, hands=hp, **opts))
        hands += [(x + hx * s, back + hy * s) for hx, hy in hp]
    out.append(_table_top(pen, w, back, front))
    out.append(rp.hands_on(pen, *hands, r=4.3))
    out.append(_hem(pen, -5, w + 5, front, 216, 16))
    out.append(_cloth_band(pen, w, 197))
    out.append(_floor(pen, w, 216, h))
    # the dishes: a back row and a front row
    out.append(place(pen, rp.bowl, 40, 160, 0.8, food="dates", fill=GOLD))
    out.append(place(pen, rp.jug, 93, 160, 0.66))
    out.append(place(pen, rp.bowl, 146, 160, 0.8, food="soup", fill=BLUE))
    out.append(place(pen, rp.food_plate, 34, 178, 0.85, food="sambousek"))
    out.append(place(pen, rp.bowl, 93, 179, 1.0, food="salad", fill=TEAL))
    out.append(place(pen, rp.food_plate, 152, 178, 0.85, food="qatayef"))
    return "".join(out)


# ---- 8. making qatayef ----------------------------------------------------------------------------------


@scene("ramadan", "qatayef")
def qatayef_making(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL)]
    out.append(pen.shape(rect(-5, 64, w + 10, 76), fill=rp.WALL_COOL))
    out.append(pen.stroke(*[seg(x, 64, x, 140) for x in range(19, 186, 24)], seg(-5, 102, w + 5, 102)))
    out.append(pen.shape(rect(20, 34, 146, 7, 2), fill=WOOD))
    for x, fill in ((40, RED), (70, TEAL), (100, YELLOW), (130, GOLD), (158, PURPLE)):
        out.append(
            pen.shape(rect(x - 9, 12, 18, 22, 4), fill=fill) + pen.shape(rect(x - 10, 8, 20, 6, 2), fill=WOOD)
        )
    back = 140.0
    out.append(place(pen, rp.bust, 42, back, 1.0, who="mom", top=TEAL, hands=((-14, 6), (18, 6))))
    gs = 1.05
    g_hands = ((-12.0, -10.0), (12.0, -10.0))
    out.append(place(pen, rp.bust, 128, back, gs, who="girl", top=PINK, hair="ponytail", hands=g_hands))
    out.append(rp.qatayef_piece(pen, 128, back - 7, 1.15))
    out.append(rp.hands_on(pen, *[(128 + x * gs, back + y * gs) for x, y in g_hands], r=3.9 * gs))
    out.append(pen.shape(rect(-5, back, w + 10, 36), fill=STONE))
    out.append(pen.shape(rect(-5, back + 36, w + 10, 70), fill=WOOD))
    out.append(pen.stroke(rect(8, 186, 78, 50, 3), rect(100, 186, 78, 50, 3)))
    out.append(pen.solid(c(78, 200, 2), c(108, 200, 2)))
    out.append(place(pen, rp.griddle, 38, 166, 1.0))
    out.append(rp.hands_on(pen, (28, 146), (60, 146), r=4.6))
    # the tray of folded qatayef, the batter and the nuts
    out.append(place(pen, rp.plate, 126, 174, 1.55))
    for x, y, fill in (
        (108, 156, rp.PASTRY_DEEP),
        (126, 155, rp.PASTRY_DEEP),
        (144, 156, rp.PASTRY_DEEP),
        (117, 164, rp.PASTRY),
        (135, 164, rp.PASTRY),
    ):
        out.append(rp.qatayef_piece(pen, x, y, 1.0, fill))
    out.append(place(pen, rp.jug, 170, 176, 0.6, fill=CREAM))
    out.append(place(pen, rp.bowl, 80, 178, 0.7, food="nuts", fill=BLUE, band=False))
    return "".join(out)


# ---- 9. the charity box ---------------------------------------------------------------------------------


@scene("ramadan", "charity-box")
def charity_box(pen: Pen, w: float, h: float) -> str:
    out = [pen.shape(rect(-5, -5, w + 10, 160), fill=STONE)]
    for x in (4, 68, 132):
        out.append(pen.shape(arch(x, 150, 50, 118, pointed=True), fill=rp.DUSK))
    out.append(place(pen, rp.moon, 30, 74, 0.5, turn=200))
    out.append(_stars(pen, [(150, 70, 0.55), (166, 96, 0.45)]))
    out.append(pen.stroke(*[seg(x, 6, x, 150) for x in (61, 125)]))
    out.append(_hanging_lantern(pen, 93, 30, 0.42, cap=TEAL))
    out.append(_floor(pen, w, 150, h))
    out.append(
        pen.stroke(
            seg(-5, 184, w + 5, 184),
            seg(40, 150, 20, 184),
            seg(146, 150, 166, 184),
            seg(20, 184, 0, 236),
            seg(166, 184, 190, 236),
        )
    )
    out.append(place(pen, rp.charity_box, 96, 202, 1.15))
    s = 1.1
    bx = 52.0
    hand = (33.0, -88.0)
    out.append(place(pen, cm.child, bx, 230, s, girl=False, shirt=ORANGE, look=0.6, hands=((-15, -38), hand)))
    hx, hy = bx + hand[0] * s, 230 + hand[1] * s
    out.append(place(pen, rp.coin, hx + 4, hy + 7, 1.0))
    out.append(rp.hands_on(pen, (hx, hy), r=3.9 * s))
    gx, gs = 154.0, 1.05
    out.append(place(pen, cm.child, gx, 230, gs, pose="hold", dress=YELLOW, hair="pigtails", look=-0.6))
    out.append(place(pen, rp.coin, gx, 230 - 48 * gs - 5, 1.0))
    out.append(rp.hands_on(pen, (gx - 6 * gs, 230 - 48 * gs), (gx + 6 * gs, 230 - 48 * gs), r=3.9 * gs))
    return "".join(out)


# ---- 10. a plate for the neighbours --------------------------------------------------------------------


@scene("ramadan", "sharing-food")
def sharing_food(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h, rp.DUSK)]
    out.append(place(pen, rp.moon, 64, 30, 0.7, turn=200))
    out.append(_stars(pen, [(36, 20, 0.6), (82, 62, 0.5)]))
    out.append(place(pen, rp.palm, 14, 200, 0.95, lean=6))
    out.append(pen.shape(rect(96, 30, 110, 180), fill=STONE))
    out.append(pen.shape(rect(92, 24, 110, 9, 2), fill=STONE_DEEP))
    out.append(pen.shape(arch(112, 198, 58, 118), fill=STONE_DEEP))
    out.append(pen.shape(arch(118, 198, 46, 110), fill=rp.GLOW))
    out.append(pen.shape(p("M118 198 L118 112 L104 104 L104 206 Z"), fill=WOOD))
    out.append(pen.stroke(seg(108, 120, 108, 194)))
    out.append(place(pen, cm.woman, 142, 198, 0.72, pose="wave", dress=PURPLE, scarf="#E9D9B8"))
    out.append(_hanging_lantern(pen, 172, 40, 0.3, cap=RED))
    out.append(pen.shape(rect(104, 198, 76, 10, 2), fill=STONE_DEEP))
    out.append(cm.ground(pen, w, 208, fill=SAND, wobble=1.0))
    out.append(place(pen, cm.flower, 175, 184, 0.7, fill=RED))
    out.append(pen.shape(p("M166 198 L168 184 L182 184 L184 198 Z"), fill=rp.COPPER))
    s = 1.15
    x0 = 64.0
    hands = ((-11.0, -36.0), (11.0, -36.0))
    out.append(place(pen, cm.child, x0, 230, s, dress=TEAL, hair="pigtails", look=0.6, hands=hands))
    hy = 230 + hands[0][1] * s
    out.append(place(pen, rp.covered_plate, x0, hy + 6, 0.72))
    out.append(rp.hands_on(pen, (x0 + hands[0][0] * s, hy), (x0 + hands[1][0] * s, hy), r=3.9 * s))
    return "".join(out)


# ---- 11. the musaharati ------------------------------------------------------------------------------------


@scene("ramadan", "musaharati")
def musaharati(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h)]
    out.append(place(pen, rp.moon, 36, 34, 0.9, turn=200))
    out.append(_stars(pen, [(90, 20, 0.7), (130, 36, 0.6), (172, 18, 0.8), (78, 60, 0.5)]))
    out.append(place(pen, rp.house, 26, 196, 1.0, w=62, h=118, rows=2, lit=True, door=False))
    out.append(place(pen, rp.house, 96, 196, 1.0, w=70, h=140, rows=2, lit=True, dome=True))
    out.append(place(pen, rp.house, 166, 196, 1.0, w=62, h=108, rows=2, lit=True, door=False))
    out.append(pen.shape(p("M-5 196 L191 196 L191 240 L-5 240 Z"), fill=STONE))
    out.append(pen.stroke(seg(-5, 212, 191, 212), *[seg(x, 196, x - 4, 212) for x in (30, 80, 130, 175)]))
    s = 0.95
    x0 = 98.0
    out.append(place(pen, cm.man, x0, 228, s, keffiyeh=True, pose="reach", robe="#E8E1D2"))
    # the drum in his lowered hand, the stick raised in the other
    lx, ly = x0 - 25 * s, 228 - 66 * s
    out.append(place(pen, rp.frame_drum, lx - 9, ly - 8, 1.2, fill=CREAM))
    out.append(rp.hands_on(pen, (lx, ly), r=4.4))
    hx, hy = x0 + 33 * s, 228 - 132 * s
    out.append(
        pen.shape(p(rp.band_d([(hx + 2, hy + 6), (hx - 6, hy - 8), (hx - 12, hy - 20)], 4.6)), fill=WOOD)
    )
    out.append(pen.shape(c(hx - 13, hy - 22, 4.2), fill=WOOD))
    out.append(rp.hands_on(pen, (hx, hy), r=4.4))
    out.append(
        pen.stroke(
            p(f"M{lx - 36:.1f} {ly - 18:.1f} q-4 -4 -9 -2"),
            p(f"M{lx - 37:.1f} {ly - 4:.1f} q-5 0 -9 3"),
            p(f"M{hx + 6:.1f} {hy - 22:.1f} q4 -3 8 -2"),
        )
    )
    return "".join(out)


# ---- 12. suhoor ------------------------------------------------------------------------------------------


@scene("ramadan", "suhoor")
def suhoor(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL_COOL)]
    out.append(_window(pen, 95, 96, 46, 72))
    out.append(place(pen, rp.moon, 104, 48, 0.5, turn=200))
    out.append(_stars(pen, [(84, 44, 0.45), (86, 80, 0.4)]))
    out.append(place(pen, rp.clock, 32, 40, 1.2))
    out.append(_hanging_lantern(pen, 160, 6, 0.36, kind="tall", cap=PURPLE))
    back, front = 146.0, 182.0
    mom_hands = ((-16.0, 7.0), (16.0, 7.0))
    boy_hands = ((-13.0, 7.0), (6.0, -45.0))
    out.append(place(pen, rp.bust, 44, back, 1.0, who="mom", top=TEAL, hands=mom_hands))
    out.append(place(pen, rp.bust, 146, back, 1.0, who="boy", top=ORANGE, hands=boy_hands, mood="yawn"))
    out.append(rp.hands_on(pen, (146 + 6, back - 45), r=3.9))
    out.append(_table_top(pen, w, back, front))
    out.append(rp.hands_on(pen, (44 - 16, back + 7), (44 + 16, back + 7), (146 - 13, back + 7), r=4.4))
    out.append(_hem(pen, -5, w + 5, front, 218, 16))
    out.append(_cloth_band(pen, w, 200, (TEAL, GOLD, PURPLE)))
    out.append(_floor(pen, w, 218, h))
    out.append(place(pen, rp.bowl, 64, 168, 0.7, food="hummus", fill=GOLD))
    out.append(place(pen, rp.teapot, 100, 170, 0.75, fill=RED))
    out.append(place(pen, rp.bowl, 166, 166, 0.7, food="olives", fill=BLUE, band=False))
    out.append(place(pen, rp.food_plate, 28, 181, 0.75, food="bread"))
    out.append(place(pen, rp.glass, 74, 181, 0.7, drink=rp.WATER))
    out.append(place(pen, rp.food_plate, 116, 181, 0.7, food="eggs"))
    out.append(place(pen, rp.food_plate, 160, 181, 0.72, food="cheese"))
    return "".join(out)


# ---- 13. the Quran on its stand -------------------------------------------------------------------------


@scene("ramadan", "quran-stand")
def quran_stand(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL)]
    out.append(pen.shape(arch(36, 164, 114, 150, pointed=True), fill=STONE_DEEP))
    out.append(pen.shape(arch(46, 164, 94, 136, pointed=True), fill=STONE))
    out.append(_hanging_lantern(pen, 18, 14, 0.4, cap=RED))
    out.append(_floor(pen, w, 164, h))
    # a plant in a pot and a lantern standing on the floor, by the wall
    out.append(place(pen, cm.bush, 17, 158, 0.62))
    out.append(pen.shape(p("M6 176 L8 156 L26 156 L28 176 Z"), fill=rp.COPPER))
    out.append(place(pen, rp.fanous, 168, 176 - 47 * 0.48, 0.48, kind="round", cap=TEAL))
    out.append(pen.stroke(*[seg(x, 166, x - 1, 159) for x in range(32, 158, 9)]))
    out.append(pen.shape(p("M26 166 L160 166 L192 236 L-6 236 Z"), fill=rp.RUG))
    out.append(pen.stroke(p("M36 174 L150 174 L174 232"), p("M12 232 L36 174")))
    out.append(place(pen, rp.quran_stand, 93, 216, 1.22, cover=GREEN))
    return "".join(out)


# ---- 14. the prayer rug and the prayer beads ------------------------------------------------------------


@scene("ramadan", "prayer-rug")
def prayer_rug(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.FLOOR)]
    out.append(
        pen.stroke(
            *[seg(-5, y, w + 5, y) for y in (40, 100, 160, 220)],
            *[seg(x, -5, x, h + 5) for x in (35, 93, 151)],
        )
    )
    out.append(place(pen, rp.prayer_rug, 88, 114, 1.08, rotate=-4))
    out.append(place(pen, rp.misbaha, 150, 176, 1.0, r=26))
    return "".join(out)


# ---- 15. my Ramadan night ----------------------------------------------------------------------------


@scene("ramadan", "ramadan-night")
def ramadan_night(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h)]
    out.append(place(pen, rp.moon, 148, 38, 1.15, turn=200))
    out.append(_stars(pen, [(24, 24, 0.9), (66, 40, 0.7), (100, 16, 0.6), (20, 70, 0.6), (178, 82, 0.6)]))
    out.append(pen.shape(rect(-5, 92, w + 10, 150), fill=STONE))
    out.append(pen.shape(rect(-7, 86, w + 14, 10, 2), fill=STONE_DEEP))
    out.append(
        pen.stroke(
            seg(-5, 120, 26, 120),
            seg(160, 120, 191, 120),
            seg(12, 96, 12, 120),
            seg(176, 96, 176, 120),
            seg(-5, 214, 191, 214),
            seg(40, 214, 40, 232),
            seg(140, 214, 140, 232),
        )
    )
    # the open shutters and the lit window
    out.append(pen.shape(rect(10, 112, 26, 92, 2), rect(150, 112, 26, 92, 2), fill=TEAL))
    out.append(
        pen.stroke(
            *[seg(14, y, 32, y) for y in range(124, 200, 12)],
            *[seg(154, y, 172, y) for y in range(124, 200, 12)],
        )
    )
    out.append(pen.shape(arch(40, 202, 106, 100), fill=STONE_DEEP))
    out.append(pen.shape(arch(48, 202, 90, 92), fill=rp.GLOW))
    s = 1.18
    x0, sill = 93.0, 196.0
    hand_r = (26.0, -44.0)
    out.append(
        place(
            pen,
            rp.bust,
            x0,
            sill,
            s,
            who="girl",
            top=PINK,
            hair="pigtails",
            hands=((-14, 2), hand_r),
            look=0.4,
        )
    )
    hx, hy = x0 + hand_r[0] * s, sill + hand_r[1] * s
    out.append(pen.stroke(seg(hx, hy, hx, hy + 6)))
    out.append(place(pen, rp.fanous, hx, hy + 6 + 54 * 0.34, 0.34, kind="classic", cap=RED))
    out.append(rp.hands_on(pen, (hx, hy), r=3.9 * s))
    out.append(pen.shape(rect(34, sill, 118, 10, 2), fill=STONE_DEEP))
    out.append(rp.hands_on(pen, (x0 - 14 * s, sill + 2 * s), r=3.9 * s))
    out.append(place(pen, cm.flower, 50, sill, 0.7, fill=RED))
    out.append(pen.shape(p(f"M40 {sill} L42 {sill - 14} L58 {sill - 14} L60 {sill} Z"), fill=rp.COPPER))
    return "".join(out)


# ---- 16. Eid clothes -----------------------------------------------------------------------------------


@scene("ramadan", "eid-clothes")
def eid_clothes(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL)]
    out.append(rp.bunting(pen, (-4, 6), (w + 4, 6), 6, 9, size=11))
    out.append(pen.shape(rect(6, 34, 174, 7, 3.5), fill=WOOD))
    out.append(pen.shape(c(6, 37.5, 6), c(180, 37.5, 6), fill=WOOD_DARK))
    out.append(place(pen, rp.eid_dress, 54, 37, 1.02, fill=PINK, trim=YELLOW))
    out.append(place(pen, rp.eid_shirt, 134, 37, 1.02, fill=BLUE, trousers=NAVY))
    out.append(_floor(pen, w, 196, h))
    out.append(place(pen, rp.shoe, 30, 222, 0.85, fill=RED))
    out.append(place(pen, rp.shoe, 72, 226, 0.85, fill=RED))
    out.append(place(pen, rp.shoe, 116, 222, 0.85, kind="boy", fill=TEAL))
    out.append(place(pen, rp.shoe, 160, 226, 0.85, kind="boy", fill=TEAL))
    return "".join(out)


# ---- 17. ka'ak and ma'amoul ---------------------------------------------------------------------------


@scene("ramadan", "kaak-maamoul")
def kaak_maamoul(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.CLOTH)]
    out.append(rp.bunting(pen, (-4, 4), (w + 4, 4), 6, 9, size=11))
    cx, cy = 93.0, 122.0
    out.append(place(pen, rp.tray, cx, cy, 1.0, r=80))
    out.append(place(pen, rp.maamoul, cx, cy, 1.25, style="star"))
    for i in range(8):
        a = 360 * i / 8 - 90
        x, y = polar(cx, cy, 46, a)
        if i % 2 == 0:
            out.append(place(pen, rp.kaak, x, y, 1.0, r=15))
        else:
            out.append(place(pen, rp.maamoul, x, y, 1.0, r=14, style="flower" if i % 4 == 1 else "grooves"))
    out.append(place(pen, rp.kaak, 22, 216, 1.0, r=14, hole=rp.CLOTH))
    out.append(place(pen, rp.maamoul, 164, 216, 1.0, r=14, style="star"))
    out.append(place(pen, rp.star8, 93, 220, 0.75, fill=GOLD))
    return "".join(out)


# ---- 18. Eid gifts and balloons ------------------------------------------------------------------------


@scene("ramadan", "eid-gifts")
def eid_gifts(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL)]
    knot = (93.0, 132.0)
    balloons = (
        (34, 56, 17, RED),
        (70, 34, 18, YELLOW),
        (114, 40, 18, TEAL),
        (152, 60, 17, PURPLE),
        (92, 82, 15, ORANGE),
    )
    strings = []
    for x, y, r, _fill in balloons:
        bx, by = x, y + r * 1.22 + 4
        strings.append(
            p(f"M{bx} {by:.1f} Q{(bx + knot[0]) / 2 + 6:.1f} {(by + knot[1]) / 2:.1f} {knot[0]} {knot[1]}")
        )
    out.append(pen.stroke(*strings))
    for x, y, r, fill in balloons:
        out.append(place(pen, rp.balloon, x, y, 1.0, r=r, fill=fill))
    out.append(_floor(pen, w, 200, h))
    out.append(place(pen, rp.gift, 93, 216, 1.0, w=80, h=56, fill=PURPLE, ribbon=YELLOW, pattern="stripes"))
    out.append(place(pen, rp.gift, 32, 222, 1.0, w=50, h=46, fill=RED, ribbon=GOLD, pattern="dots"))
    out.append(place(pen, rp.gift, 156, 222, 1.0, w=52, h=60, fill=TEAL, ribbon=PINK, pattern="stars"))
    out.append(place(pen, rp.gift, 93, 150, 1.0, w=40, h=30, fill=YELLOW, ribbon=RED))
    out.append(_stars(pen, [(20, 120, 0.7), (170, 118, 0.7), (160, 12, 0.6)]))
    return "".join(out)


# ---- 19. visiting the grandparents on Eid ---------------------------------------------------------------


@scene("ramadan", "eid-visit")
def eid_visit(pen: Pen, w: float, h: float) -> str:
    out = [pen.tint(rect(-2, -2, w + 4, h + 4), fill=rp.WALL)]
    out.append(rp.bunting(pen, (-4, 6), (w + 4, 6), 7, 9, size=11))
    out.append(place(pen, rp.clock, 93, 46, 1.0))
    out.append(_hanging_lantern(pen, 24, 16, 0.36, cap=RED))
    out.append(_hanging_lantern(pen, 162, 16, 0.36, kind="round", cap=TEAL))
    out.append(_floor(pen, w, 194, h))
    out.append(place(pen, rp.sofa, 93, 198, 1.0, w=150, fill=TEAL))
    out.append(place(pen, rp.seated, 62, 198, 1.0, who="grandma", top=PURPLE))
    out.append(place(pen, rp.seated, 124, 198, 1.0, who="grandpa", top="#E8E1D2"))
    gx, gs = 24.0, 1.0
    g_hands = ((8.0, -50.0), (26.0, -50.0))
    out.append(place(pen, cm.child, gx, 230, gs, dress=PINK, hair="pigtails", look=0.6, hands=g_hands))
    out.append(
        place(pen, rp.gift, gx + 17, 230 - 50 + 9, 1.0, w=26, h=16, fill=YELLOW, ribbon=RED, bow=False)
    )
    out.append(rp.hands_on(pen, *[(gx + x * gs, 230 + y * gs) for x, y in g_hands], r=3.9))
    out.append(
        place(pen, cm.child, 166, 230, 0.95, girl=False, pose="wave", shirt=BLUE, look=-0.6, flip=True)
    )
    out.append(pen.shape(rect(62, 210, 62, 7, 2), fill=WOOD))
    out.append(pen.shape(rect(68, 217, 6, 20), rect(112, 217, 6, 20), fill=WOOD))
    out.append(place(pen, rp.bowl, 93, 211, 0.75, food="dates", fill=GOLD))
    return "".join(out)


# ---- 20. playing on Eid -----------------------------------------------------------------------------------


@scene("ramadan", "eid-park")
def eid_park(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h, SKY)]
    out.append(place(pen, cm.sun, 26, 26, 0.8))
    out.append(place(pen, cm.cloud, 150, 24, 0.9))
    out.append(place(pen, rp.tree, 172, 182, 1.25))
    out.append(place(pen, rp.tree, 14, 176, 1.0))
    out.append(cm.ground(pen, w, 176, fill=GRASS))
    # the swing frame
    bar_y = 56.0
    out.append(
        pen.shape(
            p(rp.band_d([(36, bar_y), (16, 214)], 7)),
            p(rp.band_d([(36, bar_y), (54, 214)], 7)),
            p(rp.band_d([(150, bar_y), (132, 214)], 7)),
            p(rp.band_d([(150, bar_y), (170, 214)], 7)),
            fill=RED,
        )
    )
    out.append(pen.shape(rect(26, bar_y - 5, 134, 10, 5), fill=YELLOW))
    out.append(rp.bunting(pen, (40, bar_y + 4), (146, bar_y + 4), 3, 6, size=9))
    swings = ((70.0, 156.0, "girl", PINK, "pigtails"), (116.0, 148.0, "boy", TEAL, None))
    for x, seat_y, who, top, hair in swings:
        rope_x = (x - 14, x + 14)
        out.append(
            pen.stroke(
                seg(rope_x[0], bar_y + 5, rope_x[0], seat_y), seg(rope_x[1], bar_y + 5, rope_x[1], seat_y)
            )
        )
        out.append(pen.shape(rect(x - 26, seat_y - 3, 52, 7, 2.5), fill=WOOD))
        hands = ((-14.0, -52.0), (14.0, -52.0))
        out.append(place(pen, rp.seated, x, seat_y + 30, 1.0, who=who, top=top, hands=hands, hair=hair))
        out.append(rp.hands_on(pen, (x - 14, seat_y + 30 - 52), (x + 14, seat_y + 30 - 52), r=3.9))
    out.append(
        place(pen, cm.flower, 80, 228, 0.8, fill=YELLOW) + place(pen, cm.flower, 150, 230, 0.7, fill=PINK)
    )
    out.append(place(pen, cm.tuft, 100, 222, 1.0) + place(pen, cm.tuft, 30, 228, 1.0))
    out.append(place(pen, rp.balloon, 176, 112, 1.0, r=12, fill=RED, string=50))
    return "".join(out)


# ---- 21. Eid decorations: a pattern page ------------------------------------------------------------------


@scene("ramadan", "eid-pattern")
def eid_pattern(pen: Pen, w: float, h: float) -> str:
    out = [_sky(pen, w, h, "#4A3F8F")]
    lanterns = (
        (18, 8, "tall", TEAL),
        (55, 30, "classic", RED),
        (93, 4, "round", PURPLE),
        (131, 30, "classic", ORANGE),
        (168, 8, "tall", GREEN),
    )
    for x, length, kind, cap in lanterns:
        out.append(_hanging_lantern(pen, x, length, 0.36, kind=kind, cap=cap))
    # the medallion: a crescent holding a star inside a scalloped ring
    cx, cy = 93.0, 128.0
    out.append(pen.shape(scallop(cx, cy, 56, 56, 16, 0.6), fill=GOLD))
    out.append(pen.shape(c(cx, cy, 46), fill="#3D4B8F"))
    out.append(place(pen, rp.moon, cx - 8, cy, 1.75, turn=0))
    out.append(place(pen, rp.star8, cx + 14, cy, 1.0, fill=YELLOW))
    for x, y in ((22, 92), (164, 92), (22, 166), (164, 166)):
        out.append(place(pen, rp.star8, x, y, 0.95, fill=ORANGE))
    out.append(_stars(pen, [(28, 130, 0.6), (158, 130, 0.6), (93, 56, 0.6), (60, 190, 0.6), (126, 190, 0.6)]))
    out.append(pen.shape(rect(-5, 194, w + 10, 50), fill=TEAL))
    for x in (21, 57, 93, 129, 165):
        out.append(pen.shape(c(x, 214, 15), fill=YELLOW))
        out.append(place(pen, rp.star8, x, 214, 0.95, fill=ORANGE, hole=False))
    return "".join(out)
