"""Parts of «أُلَوِّنُ فِلَسْطينَ»: olive trees, village houses, sheep, food, the sea of Jaffa, the old city.

Every part follows `coloring.ink`'s conventions: local units are millimetres at `s = 1`, a standing thing has
its origin at the middle of its base (y grows downward), a floating thing at its centre. Parts are drawn at a
natural size that reads well on an A4 page at `s ≈ 1`; scenes scale them with `place(..., s=…)`.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from qamra_workbook.coloring.ink import (
    CREAM,
    GOLD,
    GRASS,
    GRASS_DEEP,
    MAIN,
    OLIVE_BLACK,
    OLIVE_FRUIT,
    OLIVE_LEAF,
    ORANGE,
    PINK,
    RED,
    STONE,
    STONE_DEEP,
    WHITE,
    WOOD,
    WOOD_DARK,
    YELLOW,
    Pen,
    Point,
    c,
    e,
    fmt,
    p,
    polar,
    poly,
    rect,
    scallop,
    smooth,
)
from qamra_workbook.coloring.parts.common import face, leaf_d, limb

# ---- extra palette (flat, CMYK-safe mid tones) ---------------------------------------------------------------

OLIVE_SILVER = "#A9BC84"  # the silvery green of an olive crown
OLIVE_GREEN = "#8DA65A"
BARK = "#8C6B4E"
BASKET = "#D9A55B"
BASKET_DEEP = "#C08A45"
CLOTH = "#F3E3C3"
CLAY = "#D58A5A"
CLAY_DEEP = "#B96D43"
OIL = "#D8C23E"
ZAATAR = "#7E9A4A"
BREAD = "#E8B96F"
BREAD_DEEP = "#D49A4E"
RICE = "#F4E2A8"
EGGPLANT = "#6B4A7E"
KNAFEH = "#F08A3C"
PISTACHIO = "#9BC25B"
SYRUP = "#F4C25A"
LIMESTONE = "#EFE3C8"
LIMESTONE_DEEP = "#E0CDA4"
SHUTTER = "#5E9FB8"
DOOR = "#4F86A8"
VINE = "#7FA35A"
GRAPE = "#8C5BA8"
GRAPE_GREEN = "#B9CF6A"
FIG = "#7D4E7A"
FIG_INSIDE = "#E4677A"
ORANGE_FRUIT = "#F39A3D"
LEAF_DARK = "#5F9450"
TILE_BLUE = "#3F7FBF"
TILE_TEAL = "#4FA8A8"
DOME_GOLD = "#F2C14A"
DOME_LEAD = "#9AA6B2"
CYPRESS = "#4E8A55"
SAIL = "#FBF3E2"
HULL = "#3F78B5"
GULL = "#FFFFFF"
SPICE_RED = "#D8573C"
SPICE_YELLOW = "#F2C230"
SPICE_GREEN = "#8EA84A"
SPICE_BROWN = "#A86B3C"
AWNING_A = "#E5604E"
AWNING_B = "#FFF4DC"
TATREEZ_RED = "#C8343F"
TATREEZ_DEEP = "#8E2A3A"
THOB = "#2F3A5A"
KEFFIYEH = "#FFFFFF"
KEFFIYEH_INK = "#2E2A33"
SUNBIRD = "#3C4C9A"
SUNBIRD_SHINE = "#3FA2A0"
ANEMONE = "#D8303C"
ALMOND = "#FBE0E6"
CACTUS = "#7BAA5C"
CACTUS_FRUIT = "#F08A3C"
WOOL_CREAM = "#FFF8EA"
DOG = "#C99A62"
CAT = "#F2A65A"
WOOD_LIGHT = "#D7A46C"
TEA = "#C0573A"
GLASS = "#E8F2F5"


# ---- geometry helpers ----------------------------------------------------------------------------------------


def sd(points: Sequence[Point], closed: bool = True, tension: float = 1.0) -> str:
    """Path data of `smooth` (no element), to splice into longer paths."""
    return smooth(points, closed=closed, tension=tension).removeprefix('<path d="').removesuffix('"/>')


def blob(points: Sequence[Point], tension: float = 1.0) -> str:
    """A smooth closed outline through `points`."""
    return smooth(points, tension=tension)


def base_blob(points: Sequence[Point], tension: float = 1.0) -> str:
    """A smooth open curve through `points` closed by a straight line (things standing on a flat base)."""
    return p(sd(points, closed=False, tension=tension) + " Z")


def band(points: Sequence[Point], width: float) -> str:
    """A closed ribbon of `width` along a polyline (a stick, a ladder rail, a handle) with round ends."""
    pts = list(points)
    left: list[Point] = []
    right: list[Point] = []
    for i, (x, y) in enumerate(pts):
        x0, y0 = pts[max(i - 1, 0)]
        x1, y1 = pts[min(i + 1, len(pts) - 1)]
        a = math.atan2(y1 - y0, x1 - x0)
        nx, ny = -math.sin(a) * width / 2, math.cos(a) * width / 2
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    r = width / 2
    rr = list(reversed(right))
    d = _path(left)
    d += f" A{fmt(r)} {fmt(r)} 0 0 0 {fmt(rr[0][0])} {fmt(rr[0][1])}"
    d += " " + _path(rr).split(" ", 2)[2]  # the return side, without its own "M x y"
    d += f" A{fmt(r)} {fmt(r)} 0 0 0 {fmt(left[0][0])} {fmt(left[0][1])} Z"
    return p(d)


def _path(pts: Sequence[Point]) -> str:
    """Open path data through `pts` ("M x y C …" or "M x y L …"): smooth when there are 3 points or more."""
    if len(pts) > 2:
        return sd(pts, closed=False)
    return f"M{fmt(pts[0][0])} {fmt(pts[0][1])} L{fmt(pts[1][0])} {fmt(pts[1][1])}"


def ring_arc(cx: float, cy: float, r_out: float, r_in: float, a0: float, a1: float) -> str:
    """A closed arc-shaped band (a basket handle, a rainbow) between angles a0 → a1 (degrees, clockwise)."""
    x0, y0 = polar(cx, cy, r_out, a0)
    x1, y1 = polar(cx, cy, r_out, a1)
    x2, y2 = polar(cx, cy, r_in, a1)
    x3, y3 = polar(cx, cy, r_in, a0)
    big = 1 if (a1 - a0) % 360 > 180 else 0
    return p(
        f"M{fmt(x0)} {fmt(y0)} A{fmt(r_out)} {fmt(r_out)} 0 {big} 1 {fmt(x1)} {fmt(y1)} "
        f"A{fmt((r_out - r_in) / 2)} {fmt((r_out - r_in) / 2)} 0 0 1 {fmt(x2)} {fmt(y2)} "
        f"A{fmt(r_in)} {fmt(r_in)} 0 {big} 0 {fmt(x3)} {fmt(y3)} "
        f"A{fmt((r_out - r_in) / 2)} {fmt((r_out - r_in) / 2)} 0 0 1 {fmt(x0)} {fmt(y0)} Z"
    )


def olive(cx: float, cy: float, size: float = 1.0, turn: float = 0.0) -> str:
    return e(cx, cy, 3.3 * size, 4.4 * size, turn)


# ---- olive trees ---------------------------------------------------------------------------------------------


def leafy_d(
    cx: float, cy: float, rx: float, ry: float, n: int, *, depth: float = 0.16, start: float = -90
) -> str:
    """Path data of a leafy clump: an ellipse whose edge is `n` soft leaf tips (an olive or a fig crown)."""
    d = ""
    for i in range(n):
        a0 = math.radians(start + 360 * i / n)
        a1 = math.radians(start + 360 * (i + 1) / n)
        am = (a0 + a1) / 2
        x0, y0 = cx + math.cos(a0) * rx, cy + math.sin(a0) * ry
        x1, y1 = cx + math.cos(a1) * rx, cy + math.sin(a1) * ry
        tip = (cx + math.cos(am) * rx * (1 + depth), cy + math.sin(am) * ry * (1 + depth))
        k1 = (
            cx + math.cos(a0 + (am - a0) * 0.35) * rx * (1 + depth * 1.1),
            cy + math.sin(a0 + (am - a0) * 0.35) * ry * (1 + depth * 1.1),
        )
        k2 = (
            cx + math.cos(a1 - (a1 - am) * 0.35) * rx * (1 + depth * 1.1),
            cy + math.sin(a1 - (a1 - am) * 0.35) * ry * (1 + depth * 1.1),
        )
        if i == 0:
            d += f"M{fmt(x0)} {fmt(y0)}"
        d += f" Q{fmt(k1[0])} {fmt(k1[1])} {fmt(tip[0])} {fmt(tip[1])} Q{fmt(k2[0])} {fmt(k2[1])} {fmt(x1)} {fmt(y1)}"
    return d + " Z"


_CROWN = (
    # back clumps, then front clumps (cx, cy, rx, ry, tips)
    (-40, -86, 32, 20, 11),
    (38, -88, 32, 20, 11),
    (-2, -108, 38, 22, 12),
    (-50, -64, 24, 14, 9),
    (48, -64, 24, 14, 9),
    (0, -76, 34, 18, 12),
)


def olive_trunk(pen: Pen, fill: str = BARK) -> str:
    """The gnarled, twisting trunk of an old olive tree with a knot hole and two big branches."""
    pts: list[Point] = [
        (-24, 0),
        (-13, -7),
        (-9, -20),
        (-14, -33),
        (-34, -56),
        (-25, -61),
        (-4, -42),
        (8, -62),
        (19, -58),
        (9, -36),
        (10, -20),
        (16, -7),
        (26, 0),
    ]
    out = pen.shape(base_blob(pts), fill=fill)
    out += pen.shape(e(-1, -22, 3.6, 6, 8), fill=WOOD_DARK)
    out += pen.stroke(p("M-16 -4 Q-7 -10 -6 -16"), p("M15 -3 Q7 -10 7 -14"), p("M2 -31 Q-2 -38 -1 -44"))
    return out


def olive_tree(
    pen: Pen,
    *,
    olives: int = 12,
    fruit: str = OLIVE_FRUIT,
    crown: str = OLIVE_SILVER,
    seed: int = 3,
    trunk: float = 1.0,
) -> str:
    """An old olive tree about 165 wide and 135 tall: a twisting trunk under a wide crown of leafy clumps
    with olives (`olives` of them, 0 for none). `trunk` > 1 makes the trunk bigger and older (the crown
    rises with it)."""
    rnd = random.Random(seed)
    lift = (trunk - 1) * 58
    out = [f'<g transform="scale({fmt(trunk)})">{olive_trunk(pen.at(trunk))}</g>']
    for i, (cx, cy, rx, ry, tips) in enumerate(_CROWN):
        out.append(
            pen.shape(
                p(leafy_d(cx, cy - lift, rx, ry, tips, start=-90 + 9 * i)),
                fill=crown if i < 3 else OLIVE_GREEN,
            )
        )
    if olives:
        spots: list[Point] = [
            (-46, -78),
            (-24, -96),
            (10, -120),
            (30, -80),
            (46, -94),
            (-56, -60),
            (56, -58),
            (10, -72),
            (-12, -104),
            (-34, -64),
            (26, -64),
            (18, -98),
            (-52, -90),
            (50, -74),
        ]
        rnd.shuffle(spots)
        out.append(
            pen.shape(
                *(olive(x, y - lift, 1.05, rnd.uniform(-35, 35)) for x, y in spots[:olives]), fill=fruit
            )
        )
    return "".join(out)


def olive_branch(pen: Pen, *, length: float = 120.0, olives: int = 6) -> str:
    """A long olive twig from its origin to the right: narrow silver leaves turned toward the tip and
    hanging oval olives."""
    L = length

    def at(t: float) -> Point:
        return (L * t, -L * 0.06 * math.sin(t * math.pi * 0.9))

    twig = band([at(t / 6) for t in range(7)], 4.4)
    leaves = []
    fruits = []
    n = 8
    for i in range(n):
        t = 0.1 + 0.86 * i / (n - 1)
        x, y = at(t)
        up = i % 2 == 0
        ang = -34 if up else 30
        leaves.append(p(leaf_d(x, y, L * (0.32 - 0.08 * t), L * 0.062, ang)))
    tip = at(1.0)
    leaves.append(p(leaf_d(tip[0] - 2, tip[1], L * 0.18, L * 0.06, -8)))
    for k in range(olives):
        t = 0.18 + 0.7 * k / max(olives - 1, 1)
        x, y = at(t)
        fruits.append(olive(x + 3, y + 10, L / 80, -12 + 24 * (k % 2)))
    out = pen.shape(twig, fill=BARK)
    out += pen.shape(*fruits, fill=OLIVE_FRUIT)
    out += pen.shape(*leaves, fill=OLIVE_LEAF)
    return out


# ---- harvest tools -------------------------------------------------------------------------------------------


def ladder(pen: Pen, *, h: float = 110.0, w: float = 28.0, fill: str = WOOD_LIGHT) -> str:
    """A wooden ladder standing on its origin, `h` tall (place it with `rotate` to lean it)."""
    out = []
    rungs = []
    n = max(3, int(h // 22))
    for i in range(n):
        y = -12 - (h - 22) * i / (n - 1)
        rungs.append(rect(-w / 2, y - 2.2, w, 4.4, 2.2))
    out.append(pen.shape(*rungs, fill=fill))
    out.append(pen.shape(rect(-w / 2 - 3, -h, 5.4, h, 2.7), rect(w / 2 - 2.4, -h, 5.4, h, 2.7), fill=fill))
    return "".join(out)


def basket(
    pen: Pen, *, w: float = 46.0, contents: str = "olives", handle: bool = True, fill: str = BASKET
) -> str:
    """A woven basket standing on its origin (`contents`: olives, figs, grapes, oranges, bread, zaatar, none)."""
    h = w * 0.55
    rim_y = -h
    out = []
    if handle:
        out.append(pen.shape(ring_arc(0, rim_y + 2, w * 0.42, w * 0.42 - 4.6, 180, 360), fill=fill))
    out.append(_heap(pen, contents, w, rim_y))
    body = p(
        f"M{fmt(-w / 2)} {fmt(rim_y)} L{fmt(w / 2)} {fmt(rim_y)} "
        f"C{fmt(w * 0.48)} {fmt(rim_y + h * 0.5)} {fmt(w * 0.42)} {fmt(-h * 0.08)} {fmt(w * 0.3)} 0 "
        f"L{fmt(-w * 0.3)} 0 C{fmt(-w * 0.42)} {fmt(-h * 0.08)} {fmt(-w * 0.48)} {fmt(rim_y + h * 0.5)} {fmt(-w / 2)} {fmt(rim_y)} Z"
    )
    out.append(pen.shape(body, fill=fill))
    # weave: one band across and a few upright ribs (big cells to colour)
    yb = rim_y + h * 0.5
    weave = [p(f"M{fmt(-w * 0.46)} {fmt(yb)} Q0 {fmt(yb + 3)} {fmt(w * 0.46)} {fmt(yb)}")]
    for k in (-1, 0, 1):
        x = k * w * 0.2
        weave.append(p(f"M{fmt(x)} {fmt(rim_y + 3)} L{fmt(x * 0.8)} -1.5"))
    out.append(pen.stroke(*weave))
    out.append(pen.shape(rect(-w / 2 - 2, rim_y - 3.2, w + 4, 6.4, 3.2), fill=BASKET_DEEP))
    return "".join(out)


def _heap(pen: Pen, contents: str, w: float, rim_y: float) -> str:
    """What fills a basket or a bowl: a mound above `rim_y`."""
    if contents == "none":
        return ""
    if contents in ("olives", "oranges", "figs", "lemons"):
        r = {"olives": w * 0.075, "oranges": w * 0.15, "figs": w * 0.12, "lemons": w * 0.13}[contents]
        fill = {"olives": OLIVE_FRUIT, "oranges": ORANGE_FRUIT, "figs": FIG, "lemons": YELLOW}[contents]
        items = []
        cols = max(2, int(w * 0.9 // (2 * r)))
        for row in range(2):
            n = cols - row
            for i in range(n):
                x = (i - (n - 1) / 2) * 2 * r * 1.02
                y = rim_y - r * (0.35 + row * 1.5)
                if contents == "olives":
                    items.append(olive(x, y, r / 4.2, 25 if i % 2 else -25))
                elif contents == "figs":
                    items.append(p(_fig_d(x, y + r * 0.7, r)))
                else:
                    items.append(c(x, y, r))
        return pen.shape(*items, fill=fill)
    if contents == "grapes":
        r = w * 0.075
        grapes = []
        for row in range(3):
            n = 5 - row
            for i in range(n):
                grapes.append(c((i - (n - 1) / 2) * r * 1.9, rim_y - r * (0.4 + row * 1.55), r))
        return pen.shape(*grapes, fill=GRAPE)
    if contents == "bread":
        return pen.shape(
            e(-w * 0.15, rim_y - 3, w * 0.3, w * 0.12, -12),
            e(w * 0.15, rim_y - 4, w * 0.3, w * 0.12, 10),
            fill=BREAD,
        )
    if contents == "zaatar":
        sprigs = []
        for i in range(5):
            x = (i - 2) * w * 0.17
            sprigs.append(p(leaf_d(x, rim_y + 2, w * 0.36, w * 0.14, -90 + (i - 2) * 16)))
        return pen.shape(*sprigs, fill=ZAATAR)
    return ""


def cloth(
    pen: Pen, *, w: float = 150.0, depth: float = 34.0, fill: str = CLOTH, olives: int = 9, seed: int = 2
) -> str:
    """A harvest cloth spread on the ground under a tree (seen in perspective), centred on its origin, with
    fallen olives on it."""
    rnd = random.Random(seed)
    t, b = -depth / 2, depth / 2
    d = sd(
        [
            (-w * 0.4, t),
            (-w * 0.1, t - 2),
            (w * 0.2, t + 1),
            (w * 0.41, t),
            (w * 0.47, b * 0.2),
            (w * 0.5, b),
            (w * 0.2, b + 2.5),
            (-w * 0.15, b + 0.5),
            (-w * 0.5, b + 1.5),
            (-w * 0.46, b * 0.1),
        ],
        tension=0.7,
    )
    out = pen.shape(p(d), fill=fill)
    items = []
    for _ in range(olives):
        x = rnd.uniform(-w * 0.38, w * 0.38)
        y = rnd.uniform(-depth * 0.3, depth * 0.32)
        items.append(olive(x, y, 1.05, rnd.uniform(-60, 60)))
    out += pen.shape(*items, fill=OLIVE_FRUIT)
    return out


# ---- fruit (shared by several parts) -------------------------------------------------------------------------


def _fig_d(x: float, y: float, r: float) -> str:
    """A fig standing on (x, y): a soft teardrop with a little stalk."""
    return (
        f"M{fmt(x)} {fmt(y)} C{fmt(x - r * 1.45)} {fmt(y)} {fmt(x - r * 1.35)} {fmt(y - r * 1.5)} {fmt(x - r * 0.25)} {fmt(y - r * 1.85)} "
        f"Q{fmt(x - r * 0.1)} {fmt(y - r * 2.25)} {fmt(x + r * 0.1)} {fmt(y - r * 2.3)} "
        f"Q{fmt(x + r * 0.1)} {fmt(y - r * 2.0)} {fmt(x + r * 0.25)} {fmt(y - r * 1.85)} "
        f"C{fmt(x + r * 1.35)} {fmt(y - r * 1.5)} {fmt(x + r * 1.45)} {fmt(y)} {fmt(x)} {fmt(y)} Z"
    )


def grape_bunch(
    pen: Pen,
    *,
    x: float = 0.0,
    y: float = 0.0,
    r: float = 5.0,
    rows: int = 4,
    hang: bool = True,
    fill: str = GRAPE,
) -> str:
    """A bunch of grapes: rows of round grapes narrowing downward from (x, y) (its top), with a stalk."""
    out = []
    if hang:
        out.append(pen.shape(band([(x, y - r * 1.6), (x + r * 0.2, y + r * 0.2)], r * 0.55), fill=WOOD_DARK))
    grapes = []
    for row in range(rows):
        n = max(1, rows - row)
        for i in range(n):
            gx = x + (i - (n - 1) / 2) * r * 1.85
            gy = y + r + row * r * 1.6
            grapes.append(c(gx, gy, r))
    # paint from the bottom row up so upper grapes overlap lower ones
    grapes.reverse()
    out.append(pen.shape(*grapes, fill=fill))
    return "".join(out)


def lobed_d(
    x: float,
    y: float,
    lobes: Sequence[tuple[float, float, float]],
    *,
    notch: float,
    R: float,
    size: float = 1.0,
    turn: float = 0.0,
) -> str:
    """Path data of a leaf with round lobes, its stalk end at (x, y), pointing up (turned by `turn`°).
    `lobes`: (angle°, reach, half-width°) for the right half from the top (-90) down; mirrored for the left."""
    cx, cy = 0.0, -R * 0.92
    right: list[Point] = []
    for i, (ang, reach, half) in enumerate(lobes):
        if i:
            prev = lobes[i - 1][0]
            right.append(polar(cx, cy, R * notch, (prev + ang) / 2))
        if ang == -90:
            right += [polar(cx, cy, R * reach, ang), polar(cx, cy, R * reach * 0.94, ang + half)]
        else:
            right += [
                polar(cx, cy, R * reach * 0.94, ang - half),
                polar(cx, cy, R * reach, ang),
                polar(cx, cy, R * reach * 0.94, ang + half),
            ]
    right.append(polar(cx, cy, R * 0.3, 90))
    left = [(-px, py) for px, py in reversed(right[1:-1])]
    pts = right + left
    a = math.radians(turn)
    ca, sa = math.cos(a), math.sin(a)
    return sd(
        [(x + (px * ca - py * sa) * size, y + (px * sa + py * ca) * size) for px, py in pts], tension=1.0
    )


def grape_leaf_d(x: float, y: float, size: float = 1.0, turn: float = 0.0) -> str:
    """Path data of a vine leaf with five round lobes, its stalk end at (x, y), pointing up: about 40 across."""
    return lobed_d(
        x, y, [(-90, 1.0, 14), (-28, 0.95, 14), (30, 0.8, 16)], notch=0.66, R=20.0, size=size, turn=turn
    )


def grape_leaf(pen: Pen, size: float = 1.0, turn: float = 0.0, fill: str = VINE) -> str:
    """A vine leaf on its stalk end (the origin) with three veins."""
    a = math.radians(turn)

    def rot(px: float, py: float) -> Point:
        return (px * math.cos(a) - py * math.sin(a)) * size, (px * math.sin(a) + py * math.cos(a)) * size

    base = rot(0, -12)
    veins = [
        p(f"M{fmt(base[0])} {fmt(base[1])} L{fmt(rot(*t)[0])} {fmt(rot(*t)[1])}")
        for t in ((0, -31), (12, -24), (-12, -24))
    ]
    stalk = band([rot(0, 0), rot(0, -12)], 3.2)
    return (
        pen.shape(stalk, fill=fill)
        + pen.shape(p(grape_leaf_d(0, 0, size, turn)), fill=fill)
        + pen.stroke(*veins)
    )


# ---- the village ---------------------------------------------------------------------------------------------


def _arch_d(x: float, y: float, w: float, h: float) -> str:
    r = w / 2
    top = y - h + r
    return f"M{fmt(x)} {fmt(y)} L{fmt(x)} {fmt(top)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + w)} {fmt(top)} L{fmt(x + w)} {fmt(y)} Z"


def arched_window(
    pen: Pen, x: float, y: float, *, ww: float = 16.0, wh: float = 24.0, fill: str = SHUTTER
) -> str:
    """An arched window whose sill's middle is at (x, y): a stone surround, glass in four panes, a sill."""
    out = pen.shape(p(_arch_d(x - ww / 2 - 3, y, ww + 6, wh + 3)), fill=STONE_DEEP)
    out += pen.shape(p(_arch_d(x - ww / 2, y, ww, wh)), fill=fill)
    out += pen.stroke(
        p(f"M{fmt(x)} {fmt(y - wh + 1)} L{fmt(x)} {fmt(y)}"),
        p(f"M{fmt(x - ww / 2)} {fmt(y - wh * 0.42)} L{fmt(x + ww / 2)} {fmt(y - wh * 0.42)}"),
    )
    out += pen.shape(rect(x - ww / 2 - 5, y - 1, ww + 10, 5, 2), fill=STONE_DEEP)
    return out


def arched_door(pen: Pen, x: float, y: float, *, dw: float = 22.0, dh: float = 42.0, fill: str = DOOR) -> str:
    """An arched double door standing on (x, y) (its middle) in a stone surround, with a step."""
    out = pen.shape(rect(x - dw / 2 - 5, y - 3.5, dw + 10, 5, 1.5), fill=STONE_DEEP)
    out += pen.shape(p(_arch_d(x - dw / 2 - 3.5, y - 3.5, dw + 7, dh + 4)), fill=STONE_DEEP)
    out += pen.shape(p(_arch_d(x - dw / 2, y - 3.5, dw, dh)), fill=fill)
    out += pen.stroke(p(f"M{fmt(x)} {fmt(y - 3.5 - dh + dw / 2 - 2)} L{fmt(x)} {fmt(y - 3.5)}"))
    out += pen.solid(c(x - 3.2, y - 3.5 - dh * 0.42, 1.3), c(x + 3.2, y - 3.5 - dh * 0.42, 1.3))
    return out


def stone_courses(
    pen: Pen, x0: float, y0: float, x1: float, y1: float, *, course: float = 17.0, seed: int = 7
) -> str:
    """Stone joints over the box (x0, y0)–(x1, y1): long courses and staggered upright joints (big blocks)."""
    rnd = random.Random(seed)
    h = y1 - y0
    rows = max(2, round(h / course))
    joints = []
    for i in range(1, rows):
        y = y0 + h * i / rows
        joints.append(p(f"M{fmt(x0)} {fmt(y)} L{fmt(x1)} {fmt(y)}"))
    for i in range(rows):
        ya, yb = y0 + h * i / rows, y0 + h * (i + 1) / rows
        x = x0 + rnd.uniform(12, 24) + (12 if i % 2 else 0)
        while x < x1 - 12:
            joints.append(p(f"M{fmt(x)} {fmt(ya)} L{fmt(x)} {fmt(yb)}"))
            x += rnd.uniform(26, 36)
    return pen.stroke(*joints)


def stone_house(
    pen: Pen,
    *,
    w: float = 110.0,
    h: float = 74.0,
    dome: bool = True,
    door: float = -0.22,
    windows: Sequence[float] = (0.22,),
    upper: Sequence[float] = (),
    fill: str = LIMESTONE,
    door_fill: str = DOOR,
    seed: int = 7,
) -> str:
    """A village house of pale stone standing on its origin: big stone courses, a flat roof with a low
    parapet and (with `dome`) the old domed roof, an arched blue door at `door` (fraction of the width from
    the middle) and arched windows at `windows` (lower row) and `upper` (upper row)."""
    out = []
    if dome:
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-w * 0.2)} {fmt(-h)} C{fmt(-w * 0.2)} {fmt(-h - w * 0.26)} {fmt(w * 0.2)} {fmt(-h - w * 0.26)} {fmt(w * 0.2)} {fmt(-h)} Z"
                ),
                fill=fill,
            )
        )
    out.append(pen.shape(rect(-w / 2, -h, w, h), fill=fill))
    out.append(stone_courses(pen, -w / 2, -h, w / 2, 0, seed=seed))
    out.append(pen.shape(rect(-w / 2 - 3, -h - 6, w + 6, 7, 2), fill=STONE_DEEP))
    out.append(arched_door(pen, door * w, 0, dw=w * 0.2, dh=h * 0.58, fill=door_fill))
    for row, xs in ((0, windows), (1, upper)):
        for fx in xs:
            out.append(arched_window(pen, fx * w, -h * (0.3 if row == 0 else 0.62), ww=w * 0.15, wh=h * 0.32))
    return "".join(out)


def flower_pot(pen: Pen, *, w: float = 18.0, bloom: str = RED, fill: str = CLAY) -> str:
    """A clay pot of geraniums standing on its origin (big round blooms over a few leaves)."""
    h = w * 0.8
    out = pen.shape(
        p(leaf_d(-w * 0.1, -h, w * 0.6, w * 0.26, -150)),
        p(leaf_d(w * 0.1, -h, w * 0.6, w * 0.26, -30)),
        fill=GRASS_DEEP,
    )
    out += pen.shape(
        scallop(-w * 0.18, -h - w * 0.55, w * 0.3, w * 0.28, 6, 0.7),
        scallop(w * 0.22, -h - w * 0.45, w * 0.27, w * 0.25, 6, 0.7),
        fill=bloom,
    )
    out += pen.shape(
        p(f"M{fmt(-w / 2)} {fmt(-h)} L{fmt(w / 2)} {fmt(-h)} L{fmt(w * 0.36)} 0 L{fmt(-w * 0.36)} 0 Z"),
        fill=fill,
    )
    out += pen.shape(rect(-w / 2 - 2, -h - 4, w + 4, 6, 2), fill=CLAY_DEEP)
    return out


def arbor(pen: Pen, *, w: float = 130.0, h: float = 96.0, bunches: int = 4, seed: int = 11) -> str:
    """A grapevine trellis («عَريشَة») standing on its origin: two posts, a beam and a twisting vine whose
    leaves make a roof, with grape bunches hanging under it."""
    rnd = random.Random(seed)
    out = []
    for sx in (-1, 1):
        out.append(pen.shape(rect(sx * w * 0.42 - 3.5, -h, 7, h, 1.5), fill=WOOD))
    out.append(
        pen.shape(
            band([(-w * 0.42, -6), (-w * 0.38, -h * 0.5), (-w * 0.44, -h * 0.85), (-w * 0.3, -h)], 5.5),
            fill=BARK,
        )
    )
    out.append(pen.shape(rect(-w / 2, -h - 4, w, 7, 2), fill=WOOD))
    for i in range(bunches):  # grapes first: the leaves cover their stalks
        x = -w * 0.3 + w * 0.6 * i / max(bunches - 1, 1) + rnd.uniform(-3, 3)
        out.append(
            grape_bunch(
                pen,
                x=x,
                y=-h + 8 + rnd.uniform(0, 4),
                r=3.6,
                rows=4,
                hang=True,
                fill=GRAPE if i % 2 == 0 else GRAPE_GREEN,
            )
        )
    n = 7
    for i in range(n):
        x = -w / 2 + w * i / (n - 1)
        up = i % 2 == 0
        y = -h + (8 if up else -10) + rnd.uniform(-3, 3)
        out.append(
            pen.shape(
                p(grape_leaf_d(x, y + (14 if up else -14), 1.05, rnd.uniform(-25, 25) + (0 if up else 180))),
                fill=LEAF_DARK if up else VINE,
            )
        )
    return "".join(out)


GREY_BLUE = "#9DB4C8"


def well(pen: Pen, *, w: float = 44.0, fill: str = STONE) -> str:
    """A round stone well standing on its origin, with a little wooden frame, a rope and a bucket."""
    h = w * 0.55
    top = -h - w * 0.75
    out = []
    out.append(
        pen.shape(rect(-w / 2 + 2, top, 5, w * 0.75, 1.5), rect(w / 2 - 7, top, 5, w * 0.75, 1.5), fill=WOOD)
    )
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w / 2 - 4)} {fmt(top + 2)} L0 {fmt(top - w * 0.24)} L{fmt(w / 2 + 4)} {fmt(top + 2)} Z"
            ),
            fill=RED,
        )
    )
    out.append(pen.stroke(p(f"M0 {fmt(top + 2)} L0 {fmt(-h - w * 0.36)}")))
    bt = -h - w * 0.36
    out.append(
        pen.shape(p(f"M-6 {fmt(bt)} L6 {fmt(bt)} L4.5 {fmt(bt + 10)} L-4.5 {fmt(bt + 10)} Z"), fill=GREY_BLUE)
    )
    out.append(pen.shape(rect(-w / 2, -h, w, h, 3), fill=fill))
    joints = [p(f"M{fmt(-w / 2)} {fmt(-h * 0.5)} L{fmt(w / 2)} {fmt(-h * 0.5)}")]
    for x, y0, y1 in (
        (-w * 0.17, -h, -h * 0.5),
        (w * 0.2, -h, -h * 0.5),
        (0, -h * 0.5, 0),
        (-w * 0.33, -h * 0.5, 0),
        (w * 0.33, -h * 0.5, 0),
    ):
        joints.append(p(f"M{fmt(x)} {fmt(y0)} L{fmt(x)} {fmt(y1)}"))
    out.append(pen.stroke(*joints))
    out.append(pen.shape(e(0, -h, w / 2 + 2, 5), fill=STONE_DEEP))
    return "".join(out)


def stone_wall(
    pen: Pen, *, w: float = 120.0, h: float = 30.0, rows: int = 2, fill: str = STONE, seed: int = 4
) -> str:
    """A dry-stone field wall standing on its origin and running right to x = w: rows of big rounded stones."""
    rnd = random.Random(seed)
    out = []
    rh = h / rows
    for r in range(rows):
        y1 = -r * rh
        y0 = y1 - rh
        x = -rnd.uniform(4, 14) if r % 2 else 0.0
        while x < w:
            sw = rnd.uniform(18, 28)
            x2 = min(x + sw, w + 6)
            j = [rnd.uniform(-1.5, 1.5) for _ in range(6)]
            pts: list[Point] = [
                (x + 1, y1 - 1 + j[0]),
                (x + 0.5, (y0 + y1) / 2 + j[1]),
                (x + 2, y0 + 1.5 + j[2]),
                ((x + x2) / 2, y0 + j[3]),
                (x2 - 1.5, y0 + 1.5),
                (x2 - 0.5, (y0 + y1) / 2 + j[4]),
                (x2 - 1.5, y1 - 0.5),
                ((x + x2) / 2, y1 + j[5] * 0.4),
            ]
            out.append(pen.shape(blob(pts, 0.8), fill=fill if rnd.random() < 0.6 else STONE_DEEP))
            x = x2
    return "".join(out)


# ---- animals -------------------------------------------------------------------------------------------------


def sheep(
    pen: Pen, *, wool: str = WOOL_CREAM, face_fill: str = "#E9D8C4", lamb: bool = False, grazing: bool = False
) -> str:
    """A woolly sheep facing right, standing on its origin (about 80 long, 56 tall); `lamb` is rounder with a
    bigger head; `grazing` puts the head down to the grass."""
    k = 0.8 if lamb else 1.0
    body_cy = -32 * k
    rx, ry = (24, 17) if lamb else (30, 19)
    xs = (-13, -5, 6, 14) if lamb else (-16, -7, 9, 18)
    out = []
    out.append(
        pen.shape(
            *[rect(lx - 3.2, body_cy + ry * 0.5, 6.4, -body_cy - ry * 0.5, 3.2) for lx in xs], fill=face_fill
        )
    )
    out.append(pen.shape(*[rect(lx - 3.6, -5, 7.2, 5, 2.2) for lx in xs], fill="#5B4A44"))
    out.append(pen.shape(scallop(-rx - 2, body_cy - 6, 6, 6, 5, 0.75), fill=wool))  # tail
    out.append(pen.shape(scallop(0, body_cy, rx, ry, 10 if lamb else 12, 0.68), fill=wool))
    hx, hy = (rx + 4, body_cy - 8) if not grazing else (rx + 6, body_cy + 14)
    hr = 10.5 if lamb else 10.0
    turn = 25 if grazing else 0
    out.append(pen.shape(p(leaf_d(hx - 5, hy - 4, 12, 6, 160 + turn)), fill=face_fill))  # far ear
    head = blob(
        [
            (hx - hr * 0.8, hy - hr * 0.7),
            (hx + hr * 0.3, hy - hr * 0.95),
            (hx + hr * 1.1, hy - hr * 0.1),
            (hx + hr * 1.0, hy + hr * 0.75),
            (hx + hr * 0.1, hy + hr * 0.9),
            (hx - hr * 0.85, hy + hr * 0.3),
        ],
        0.9,
    )
    out.append(pen.shape(head, fill=face_fill))
    out.append(
        pen.shape(scallop(hx - 2, hy - hr * 0.85, hr * 0.75, hr * 0.42, 6, 0.75), fill=wool)
    )  # fleece cap
    out.append(pen.shape(p(leaf_d(hx - 6, hy - 2, 13, 6.5, 200 - turn)), fill=face_fill))  # near ear
    out.append(
        pen.solid(e(hx + hr * 0.25, hy - hr * 0.05, 1.5, 1.9), e(hx + hr * 0.8, hy + hr * 0.35, 0.9, 0.9))
    )
    out.append(
        pen.stroke(
            p(
                f"M{fmt(hx + hr * 0.35)} {fmt(hy + hr * 0.55)} Q{fmt(hx + hr * 0.6)} {fmt(hy + hr * 0.75)} {fmt(hx + hr * 0.85)} {fmt(hy + hr * 0.6)}"
            )
        )
    )
    out.append(pen.tint(e(hx + hr * 0.05, hy + hr * 0.4, 2.4, 1.6), fill="#F2A3A0"))
    return "".join(out)


def dog(pen: Pen, *, fill: str = DOG, patch: str = "#8F6A45") -> str:
    """A friendly shepherd dog sitting, facing right, on its origin (about 58 tall)."""
    out = []
    out.append(pen.shape(band([(-16, -8), (-27, -14), (-31, -26)], 6.5), fill=fill))  # tail
    out.append(
        pen.shape(
            blob([(-22, -1), (-24, -16), (-14, -30), (0, -40), (12, -36), (14, -16), (12, -1)], 0.9),
            fill=fill,
        )
    )
    out.append(pen.shape(e(-12, -13, 12, 12), fill=fill))  # haunch
    out.append(pen.shape(rect(1, -24, 7, 24, 3.5), rect(9, -24, 7, 24, 3.5), fill=fill))
    out.append(pen.shape(e(4.5, -2.5, 5.5, 3.5), e(12.5, -2.5, 5.5, 3.5), fill=fill))
    out.append(pen.shape(p("M0 -34 Q10 -28 18 -35 L17 -30 Q9 -23 1 -29 Z"), fill=RED))  # collar
    out.append(pen.shape(c(9, -46, 12), fill=fill))
    out.append(pen.shape(e(20, -42, 8.5, 6.5), fill=WHITE))  # snout
    out.append(pen.solid(e(27.5, -44.5, 2.6, 2.1), e(12, -49, 1.6, 2)))
    out.append(pen.stroke(p("M21 -38 Q24 -36 27 -38.5")))
    out.append(pen.shape(p("M3 -56 C-6 -56 -9 -44 -5 -35 C0 -38 4 -46 5 -54 Z"), fill=patch))  # ear
    return "".join(out)


def cat(pen: Pen, *, fill: str = CAT) -> str:
    """A cat sitting and facing us on its origin (about 62 tall), its tail curled round its paws."""
    out = []
    out.append(pen.shape(band([(10, -4), (24, -6), (26, -20), (20, -26)], 6), fill=fill))
    out.append(
        pen.shape(base_blob([(-15, 0), (-14, -18), (-8, -32), (8, -32), (14, -18), (15, 0)]), fill=fill)
    )
    out.append(pen.shape(e(-6, -2, 5.5, 3.6), e(6, -2, 5.5, 3.6), fill=fill))
    out.append(pen.shape(p("M-12 -48 L-13 -62 L-3 -55 Z"), p("M12 -48 L13 -62 L3 -55 Z"), fill=fill))
    out.append(pen.shape(e(0, -45, 14, 12), fill=fill))
    out.append(pen.solid(e(-5, -47, 1.6, 2.1), e(5, -47, 1.6, 2.1), p("M-2 -42.5 L2 -42.5 L0 -40.5 Z")))
    out.append(
        pen.stroke(
            p("M-4 -38.5 Q-2 -37 0 -39 Q2 -37 4 -38.5"),
            p("M-9 -42 L-18 -43"),
            p("M-9 -40 L-17 -38"),
            p("M9 -42 L18 -43"),
            p("M9 -40 L17 -38"),
        )
    )
    return "".join(out)


def crook(pen: Pen, *, h: float = 150.0, fill: str = WOOD) -> str:
    """A shepherd's crook standing on its origin, the hook at the top turned right."""
    return pen.shape(
        band([(0, 0), (0.5, -h * 0.5), (0, -h), (4, -h - 9), (12, -h - 8), (13, -h + 1)], 4.5), fill=fill
    )


# ---- food and the kitchen ------------------------------------------------------------------------------------


def ellipse_chord(
    cx: float, cy: float, rx: float, ry: float, x0: float, y0: float, dx: float, dy: float
) -> tuple[Point, Point] | None:
    """Where the line through (x0, y0) along (dx, dy) crosses the ellipse: its chord inside, or None."""
    ux, uy = (x0 - cx) / rx, (y0 - cy) / ry
    vx, vy = dx / rx, dy / ry
    a = vx * vx + vy * vy
    b = 2 * (ux * vx + uy * vy)
    k = ux * ux + uy * uy - 1
    disc = b * b - 4 * a * k
    if disc <= 0:
        return None
    t1 = (-b - math.sqrt(disc)) / (2 * a)
    t2 = (-b + math.sqrt(disc)) / (2 * a)
    return (x0 + dx * t1, y0 + dy * t1), (x0 + dx * t2, y0 + dy * t2)


def jar(pen: Pen, *, h: float = 64.0, fill: str = CLAY, handles: bool = True) -> str:
    """A clay oil jar («جَرَّة») standing on its origin, with two handles and a painted band."""
    k = h / 64
    half: list[Point] = [(10, 0), (20, -13), (22, -32), (15, -48), (8, -54), (8, -60), (11, -63)]
    pts = [(x * k, y * k) for x, y in half]
    body = p(sd([(-x, y) for x, y in reversed(pts)] + pts, closed=False, tension=0.8) + " Z")
    out = []
    if handles:
        for sx in (-1, 1):
            out.append(
                pen.shape(
                    band(
                        [
                            (sx * 14 * k, -46 * k),
                            (sx * 22 * k, -52 * k),
                            (sx * 20 * k, -60 * k),
                            (sx * 9 * k, -58 * k),
                        ],
                        4.2,
                    ),
                    fill=fill,
                )
            )
    out.append(pen.shape(body, fill=fill))
    out.append(
        pen.stroke(
            p(f"M{fmt(-21.5 * k)} {fmt(-26 * k)} Q0 {fmt(-22 * k)} {fmt(21.5 * k)} {fmt(-26 * k)}"),
            p(f"M{fmt(-21 * k)} {fmt(-36 * k)} Q0 {fmt(-32 * k)} {fmt(21 * k)} {fmt(-36 * k)}"),
        )
    )
    out.append(pen.shape(e(0, -63 * k, 11.5 * k, 3.2 * k), fill=CLAY_DEEP))
    return "".join(out)


def bowl(pen: Pen, *, w: float = 40.0, contents: str = "oil", fill: str = "#F2F2EE") -> str:
    """A shallow bowl standing on its origin: with olive `oil`, `zaatar`, `olives`, `labneh` or `none`."""
    h = w * 0.36
    out = []
    top = -h
    if contents == "zaatar":
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-w * 0.44)} {fmt(top + 1)} C{fmt(-w * 0.35)} {fmt(top - w * 0.24)} {fmt(w * 0.35)} {fmt(top - w * 0.24)} {fmt(w * 0.44)} {fmt(top + 1)} Z"
                ),
                fill=ZAATAR,
            )
        )
    elif contents == "olives":
        out.append(
            pen.shape(
                *[
                    olive(
                        x,
                        top - 3 - abs(x) * -0.0 - (4 if abs(x) < w * 0.15 else 0),
                        w / 40 * 1.15,
                        30 if i % 2 else -30,
                    )
                    for i, x in enumerate((-w * 0.3, -w * 0.1, w * 0.1, w * 0.3, -w * 0.2, 0, w * 0.2))
                ],
                fill=OLIVE_BLACK,
            )
        )
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w / 2)} {fmt(top)} C{fmt(-w / 2)} {fmt(-h * 0.1)} {fmt(-w * 0.25)} 0 0 0 C{fmt(w * 0.25)} 0 {fmt(w / 2)} {fmt(-h * 0.1)} {fmt(w / 2)} {fmt(top)} Z"
            ),
            fill=fill,
        )
    )
    out.append(pen.shape(e(0, top, w / 2, w * 0.1), fill=fill))
    if contents == "oil":
        out.append(pen.shape(e(0, top + 0.6, w * 0.4, w * 0.065), fill=OIL))
    elif contents == "labneh":
        out.append(pen.shape(e(0, top + 0.6, w * 0.4, w * 0.065), fill=WHITE))
        out.append(pen.shape(e(0, top + 0.6, w * 0.13, w * 0.035), fill=OIL))
    return "".join(out)


def flatbread(pen: Pen, *, r: float = 22.0, tilt: float = 0.42, fill: str = BREAD) -> str:
    """A round taboon loaf seen from above at a slant, centred on its origin, with its baked dimples."""
    out = pen.shape(e(0, 0, r, r * tilt), fill=fill)
    out += pen.shape(
        e(-r * 0.4, -r * tilt * 0.15, 3.2, 3.2 * tilt * 1.6),
        e(r * 0.25, -r * tilt * 0.35, 3, 3 * tilt * 1.6),
        e(r * 0.05, r * tilt * 0.4, 3.2, 3.2 * tilt * 1.6),
        e(r * 0.55, r * tilt * 0.2, 2.8, 2.8 * tilt * 1.6),
        fill=BREAD_DEEP,
    )
    return out


def teapot(pen: Pen, *, fill: str = "#E9EEF3") -> str:
    """A round teapot standing on its origin (about 40 tall), spout to the right."""
    out = pen.shape(band([(14, -18), (24, -26), (30, -32)], 5), fill=fill)
    out += pen.shape(ring_arc(-17, -20, 10, 5, 100, 280), fill=fill)
    out += pen.shape(
        base_blob([(-12, 0), (-19, -10), (-17, -24), (0, -30), (17, -24), (19, -10), (12, 0)]), fill=fill
    )
    out += pen.shape(e(0, -30, 11, 3.5), fill=fill)
    out += pen.shape(c(0, -35, 3.2), fill=RED)
    out += pen.stroke(p("M-18 -14 Q0 -9 18 -14"))
    return out


def tea_glass(pen: Pen, *, fill: str = TEA) -> str:
    """A small tulip glass of tea on a saucer, standing on its origin (about 22 tall)."""
    out = pen.shape(e(0, -1.5, 11, 3), fill=GLASS)
    out += pen.shape(
        p("M-6.5 -22 L6.5 -22 C6.5 -15 4 -11 5 -3 L-5 -3 C-4 -11 -6.5 -15 -6.5 -22 Z"), fill=GLASS
    )
    out += pen.shape(
        p("M-5.6 -17 L5.6 -17 C5.4 -13 3.8 -10 4.4 -4.2 L-4.4 -4.2 C-3.8 -10 -5.4 -13 -5.6 -17 Z"), fill=fill
    )
    return out


def plate(pen: Pen, *, w: float = 44.0, fill: str = WHITE) -> str:
    """A round plate seen at a slant, centred on its origin."""
    return pen.shape(e(0, 0, w / 2, w * 0.17), fill=fill) + pen.stroke(e(0, -0.5, w * 0.33, w * 0.1))


def taboon(pen: Pen, *, w: float = 92.0, fill: str = CLAY) -> str:
    """A village taboon oven: a low clay dome standing on its origin with an arched mouth and a glowing fire,
    a round lid leaning beside it."""
    h = w * 0.55
    out = []
    out.append(
        pen.shape(
            base_blob(
                [
                    (-w / 2, 0),
                    (-w * 0.46, -h * 0.55),
                    (-w * 0.25, -h * 0.95),
                    (0, -h),
                    (w * 0.25, -h * 0.95),
                    (w * 0.46, -h * 0.55),
                    (w / 2, 0),
                ]
            ),
            fill=fill,
        )
    )
    out.append(
        pen.stroke(
            p(f"M{fmt(-w * 0.44)} {fmt(-h * 0.45)} Q0 {fmt(-h * 0.62)} {fmt(w * 0.44)} {fmt(-h * 0.45)}")
        )
    )
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w * 0.12)} {fmt(-h)} C{fmt(-w * 0.1)} {fmt(-h - 9)} {fmt(w * 0.1)} {fmt(-h - 9)} {fmt(w * 0.12)} {fmt(-h)} Z"
            ),
            fill=CLAY_DEEP,
        )
    )
    mw, mh = w * 0.4, h * 0.56
    out.append(pen.shape(p(_arch_d(-mw / 2, 0, mw, mh)), fill="#5B3A29"))
    flames = [
        p(
            f"M{fmt(-mw * 0.32)} 0 C{fmt(-mw * 0.4)} -8 {fmt(-mw * 0.2)} -12 {fmt(-mw * 0.18)} -18 C{fmt(-mw * 0.05)} -12 {fmt(-mw * 0.02)} -6 {fmt(-mw * 0.02)} 0 Z"
        ),
        p(
            f"M{fmt(-mw * 0.08)} 0 C{fmt(-mw * 0.15)} -10 {fmt(mw * 0.05)} -16 {fmt(mw * 0.06)} -24 C{fmt(mw * 0.22)} -15 {fmt(mw * 0.28)} -7 {fmt(mw * 0.3)} 0 Z"
        ),
    ]
    out.append(pen.shape(*flames, fill=ORANGE))
    out.append(pen.shape(rect(-mw / 2 - 6, -4, mw + 12, 6, 3), fill=CLAY_DEEP))
    return "".join(out)


def peel(pen: Pen, *, length: float = 70.0, fill: str = WOOD_LIGHT) -> str:
    """A long wooden bread peel lying left → right from its origin (handle first, round blade at the end)."""
    out = pen.shape(band([(0, 0), (length * 0.62, 0)], 5), fill=fill)
    out += pen.shape(e(length * 0.78, 0, length * 0.2, length * 0.13), fill=fill)
    return out


def smoke(pen: Pen, *, h: float = 40.0) -> str:
    """Two soft curls of smoke rising from the origin (open lines)."""
    return pen.stroke(
        p(
            f"M0 0 C-8 {fmt(-h * 0.2)} 8 {fmt(-h * 0.4)} 0 {fmt(-h * 0.6)} C-8 {fmt(-h * 0.8)} 4 {fmt(-h * 0.95)} 2 {fmt(-h)}"
        ),
        p(f"M9 {fmt(-h * 0.15)} C2 {fmt(-h * 0.32)} 15 {fmt(-h * 0.5)} 8 {fmt(-h * 0.72)}"),
    )


def pot(pen: Pen, *, w: float = 60.0, fill: str = "#B9C3CC") -> str:
    """A big cooking pot standing on its origin, with side handles and a rim."""
    h = w * 0.62
    out = pen.shape(rect(-w / 2 - 9, -h * 0.78, 12, 6, 3), rect(w / 2 - 3, -h * 0.78, 12, 6, 3), fill=fill)
    out += pen.shape(
        p(
            f"M{fmt(-w / 2)} {fmt(-h)} L{fmt(w / 2)} {fmt(-h)} L{fmt(w / 2)} -6 Q{fmt(w / 2)} 0 {fmt(w / 2 - 6)} 0 L{fmt(-w / 2 + 6)} 0 Q{fmt(-w / 2)} 0 {fmt(-w / 2)} -6 Z"
        ),
        fill=fill,
    )
    out += pen.shape(rect(-w / 2 - 3, -h - 4, w + 6, 7, 3.5), fill=fill)
    return out


def _cubic(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
    )


def maqluba(pen: Pen, *, w: float = 100.0) -> str:
    """Maqluba turned out onto a round tray, origin at the tray's middle: a dome of rice under a cap of
    overlapping fried aubergine slices, crowned with chicken, toasted nuts and parsley."""
    out = []
    out.append(pen.shape(e(0, 0, w * 0.62, w * 0.17), fill="#D9D2C2"))
    out.append(pen.shape(e(0, -1.5, w * 0.54, w * 0.13), fill="#EFEAE0"))
    H = w * 0.5
    right = ((w * 0.42, 0.0), (w * 0.44, -H * 0.75), (w * 0.25, -H), (0.0, -H))
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w * 0.42)} 0 C{fmt(-w * 0.44)} {fmt(-H * 0.75)} {fmt(-w * 0.25)} {fmt(-H)} 0 {fmt(-H)} C{fmt(w * 0.25)} {fmt(-H)} {fmt(w * 0.44)} {fmt(-H * 0.75)} {fmt(w * 0.42)} 0 Q0 {fmt(w * 0.06)} {fmt(-w * 0.42)} 0 Z"
            ),
            fill=RICE,
        )
    )
    # the cap: the dome's outline above `level`, closed by a scalloped edge of slices
    level = -H * 0.42
    pts = [_cubic(*right, t / 40) for t in range(41)]
    side = [pt for pt in pts if pt[1] <= level]
    over = [*side, *[(-x, y) for x, y in reversed(side[:-1])]]
    d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in over)
    n = 6
    x0, x1 = over[-1][0], over[0][0]
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    r = (x1 - x0) / n / 2 * 1.08
    for i in range(n):
        d += f" A{fmt(r)} {fmt(r)} 0 0 0 {fmt(xs[i + 1])} {fmt(level)}"
    out.append(pen.shape(p(d + " Z"), fill=EGGPLANT))
    out.append(
        pen.stroke(
            *[
                p(
                    f"M{fmt(x)} {fmt(level)} Q{fmt(x * 0.8)} {fmt(level - H * 0.2)} {fmt(x * 0.5)} {fmt(-H * 0.86)}"
                )
                for x in xs[1:-1]
            ]
        )
    )
    out.append(
        pen.shape(
            blob(
                [
                    (-w * 0.16, -H * 0.86),
                    (-w * 0.05, -H * 1.08),
                    (w * 0.12, -H * 1.0),
                    (w * 0.15, -H * 0.84),
                    (0, -H * 0.78),
                ]
            ),
            fill=BREAD_DEEP,
        )
    )
    nuts = [
        e(x, y, 3.2, 2.0, rot)
        for x, y, rot in (
            (-w * 0.2, -H * 0.72, -30),
            (w * 0.22, -H * 0.72, 30),
            (-w * 0.05, -H * 1.12, 0),
            (w * 0.08, -H * 1.11, 10),
        )
    ]
    out.append(pen.shape(*nuts, fill=GOLD))
    out.append(
        pen.shape(
            p(leaf_d(-w * 0.3, -H * 0.18, 11, 5, 200)),
            p(leaf_d(w * 0.3, -H * 0.18, 11, 5, -20)),
            fill=GRASS_DEEP,
        )
    )
    return "".join(out)


def knafeh_tray(pen: Pen, *, w: float = 140.0, cut: bool = True) -> str:
    """A round tray of knafeh seen at a slant, centred on its origin: a crisp orange top cut in diamonds,
    a pistachio crumb in each piece, two handles."""
    ry = w * 0.3
    out = []
    out.append(
        pen.shape(
            ring_arc(-w * 0.5 - 2, 0, 9, 4.2, 100, 260),
            ring_arc(w * 0.5 + 2, 0, 9, 4.2, -80, 80),
            fill="#C7A25A",
        )
    )
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w / 2)} 0 L{fmt(-w / 2)} 9 A{fmt(w / 2)} {fmt(ry)} 0 0 0 {fmt(w / 2)} 9 L{fmt(w / 2)} 0 Z"
            ),
            fill="#C7A25A",
        )
    )
    out.append(pen.shape(e(0, 0, w / 2, ry), fill="#E2BE6E"))
    ix, iy = w / 2 - 6, ry - 4.5
    out.append(pen.shape(e(0, 0.5, ix, iy), fill=KNAFEH))
    if cut:
        lines = []
        step = 40.0
        crumbs = []
        for k in range(-8, 9):
            for dx, dy in ((1.0, 0.55), (1.0, -0.55)):
                ch = ellipse_chord(0, 0.5, ix, iy, k * step, 0, dx, dy)
                if ch:
                    (x1, y1), (x2, y2) = ch
                    lines.append(p(f"M{fmt(x1)} {fmt(y1)} L{fmt(x2)} {fmt(y2)}"))
        out.append(pen.stroke(*lines))
        # one crumb in the middle of each diamond that lies well inside the top
        for i in range(-8, 9):
            for j in range(-8, 9):
                # diamond centres: halfway between neighbouring crossings
                x = (i + j) * step / 2 + step / 2
                y = (j - i) * step * 0.55 / 2
                if (x / (ix - 12)) ** 2 + (y / (iy - 8)) ** 2 < 1:
                    crumbs.append(e(x, y, 4.6, 3.2))
        out.append(pen.shape(*crumbs, fill=PISTACHIO))
    return "".join(out)


def knafeh_slice(pen: Pen, *, w: float = 40.0) -> str:
    """A diamond piece of knafeh on a small plate, its cheese stretching; centred on the plate."""
    out = plate(pen, w=w * 1.5)
    out += pen.shape(
        p(f"M{fmt(-w * 0.45)} -2 L0 {fmt(-w * 0.16)} L{fmt(w * 0.45)} -2 L0 {fmt(w * 0.12)} Z"), fill=CREAM
    )
    out += pen.shape(
        p(
            f"M{fmt(-w * 0.45)} -8 L0 {fmt(-w * 0.16 - 6)} L{fmt(w * 0.45)} -8 L{fmt(w * 0.45)} -2 L0 {fmt(w * 0.12)} L{fmt(-w * 0.45)} -2 Z"
        ),
        fill=CREAM,
    )
    out += pen.shape(
        p(f"M{fmt(-w * 0.45)} -8 L0 {fmt(-w * 0.16 - 6)} L{fmt(w * 0.45)} -8 L0 {fmt(w * 0.12 - 6)} Z"),
        fill=KNAFEH,
    )
    out += pen.shape(e(0, -8.5, 3.4, 2.4), fill=PISTACHIO)
    return out


# ---- plants and flowers --------------------------------------------------------------------------------------


def blossom(cx: float, cy: float, r: float, petals: int = 5, turn: float = -90) -> list[str]:
    """A five-petal blossom centred at (cx, cy), `r` its radius: separate round petals (each its own area)."""
    out = []
    for i in range(petals):
        a = turn + 360 * i / petals
        px, py = polar(cx, cy, r * 0.56, a)
        out.append(e(px, py, r * 0.44, r * 0.4, a))
    return out


def almond_branch(pen: Pen, *, length: float = 140.0, seed: int = 8) -> str:
    """A flowering almond branch from its origin to the upper right: a dark twig, pink-white blossoms with
    pink hearts, a few buds."""
    rnd = random.Random(seed)
    L = length
    main = [(0, 0), (L * 0.3, -L * 0.1), (L * 0.62, -L * 0.24), (L, -L * 0.3)]
    side = [(L * 0.34, -L * 0.11), (L * 0.46, -L * 0.3), (L * 0.52, -L * 0.48)]
    out = pen.shape(band(main, 6), band(side, 4.6), fill=BARK)
    spots: list[Point] = [
        (L * 0.15, -L * 0.1),
        (L * 0.27, -L * 0.03),
        (L * 0.42, -L * 0.2),
        (L * 0.55, -L * 0.42),
        (L * 0.6, -L * 0.15),
        (L * 0.75, -L * 0.33),
        (L * 0.88, -L * 0.22),
        (L * 0.98, -L * 0.36),
    ]
    blooms = []
    hearts = []
    for x, y in spots:
        r = L * 0.13 * rnd.uniform(0.9, 1.1)
        blooms += blossom(x, y, r, turn=rnd.uniform(-90, -18))
        hearts.append(c(x, y, r * 0.3))
    buds = [e(L * 0.5, -L * 0.53, 3.5, 5, 20), e(L * 0.07, -L * 0.07, 3.5, 5, -30)]
    out += pen.shape(*buds, fill=PINK)
    out += pen.shape(*blooms, fill=ALMOND)
    out += pen.shape(*hearts, fill=PINK)
    return out


def almond_tree(pen: Pen, *, seed: int = 9, blooms: int = 11) -> str:
    """A young almond tree in blossom standing on its origin (about 110 tall): a slim trunk, open branches
    and clouds of five-petal flowers."""
    rnd = random.Random(seed)
    out = []
    trunk = [
        band([(0, 0), (-1, -30), (-4, -48)], 9),
        band([(-1, -30), (14, -52), (30, -70)], 6),
        band([(-4, -48), (-24, -70), (-36, -80)], 6),
        band([(-3, -46), (2, -78), (-2, -98)], 5.5),
        band([(8, -44), (26, -56)], 4.5),
    ]
    out.append(pen.shape(*trunk, fill=BARK))
    spots: list[Point] = []
    tries = 0
    while len(spots) < blooms and tries < 4000:  # spread the flowers out: each one keeps its own room
        tries += 1
        cx, cy, rr = rnd.choice(
            ((30, -72, 20), (-34, -80, 20), (-1, -100, 20), (14, -60, 12), (-18, -64, 12))
        )
        a = rnd.uniform(0, 2 * math.pi)
        d = rr * math.sqrt(rnd.random())
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
        if all(math.dist((x, y), q) > 24 for q in spots):
            spots.append((x, y))
    for k, (x, y) in enumerate(spots):
        out.append(pen.shape(*blossom(x, y, 15, turn=-90 + 17 * k), fill=ALMOND))
        out.append(pen.shape(c(x, y, 4.6), fill=PINK))
    return "".join(out)


def anemone(pen: Pen, *, h: float = 60.0, fill: str = ANEMONE, lean: float = 0.0) -> str:
    """A red anemone («دَحْنون»): six round petals round a dark heart on a tall stem with a frilly leaf
    collar and two cut basal leaves; origin at the stem's foot."""
    top_x, top_y = lean * h, -h
    R = h * 0.26
    out = []
    out.append(
        pen.shape(*_cut_leaf(-2, -1, h * 0.28, -140), *_cut_leaf(2, -1, h * 0.28, -40), fill=GRASS_DEEP)
    )
    out.append(
        pen.stroke(
            p(f"M0 0 Q{fmt(top_x * 0.2 + h * 0.06)} {fmt(-h * 0.5)} {fmt(top_x)} {fmt(top_y)}"), weight=MAIN
        )
    )
    collar_y = -h * 0.62
    cx = top_x * 0.62
    out.append(
        pen.shape(
            p(leaf_d(cx, collar_y, h * 0.2, h * 0.06, -150)),
            p(leaf_d(cx, collar_y, h * 0.2, h * 0.06, -30)),
            fill=GRASS_DEEP,
        )
    )
    for layer in (0, 1):  # three petals behind, three in front
        petals = []
        for i in range(3):
            a = -90 + 120 * i + 60 * layer
            px, py = polar(top_x, top_y, R * 0.56, a)
            petals.append(e(px, py, R * 0.56, R * 0.44, a))
        out.append(pen.shape(*petals, fill=fill))
    out.append(pen.shape(c(top_x, top_y, R * 0.3), fill="#2E2A33"))
    out.append(
        pen.solid(*[c(*polar(top_x, top_y, R * 0.45, 22.5 + 45 * i), max(0.9, R * 0.045)) for i in range(8)])
    )
    return "".join(out)


def _cut_leaf(x: float, y: float, length: float, angle: float) -> list[str]:
    """A three-fingered cut leaf (anemone, poppy) from (x, y) toward `angle`: three narrow leaflets."""
    return [
        p(leaf_d(x, y, length * k, length * 0.22, angle + d)) for d, k in ((-28, 0.8), (0, 1.0), (28, 0.8))
    ]


def daisy(pen: Pen, *, h: float = 44.0, r: float = 11.0, lean: float = 0.0) -> str:
    """A white daisy («أُقْحُوان») on a thin stem: one frilled ring of petals and a big yellow heart."""
    tx, ty = lean * h, -h
    out = pen.stroke(p(f"M0 0 Q{fmt(h * 0.05)} {fmt(-h * 0.5)} {fmt(tx)} {fmt(ty)}"), weight=MAIN)
    out += pen.shape(p(leaf_d(0, -h * 0.3, h * 0.25, h * 0.08, -40)), fill=GRASS_DEEP)
    out += pen.shape(scallop(tx, ty, r, r, 12, 0.72), fill=WHITE)
    out += pen.stroke(
        *[
            p(
                f"M{fmt(polar(tx, ty, r * 0.45, a)[0])} {fmt(polar(tx, ty, r * 0.45, a)[1])} L{fmt(polar(tx, ty, r * 0.8, a)[0])} {fmt(polar(tx, ty, r * 0.8, a)[1])}"
            )
            for a in range(-75, 285, 60)
        ]
    )
    out += pen.shape(c(tx, ty, r * 0.42), fill=YELLOW)
    return out


def butterfly(pen: Pen, *, w: float = 44.0, wing: str = "#F2B33D", spots: str = "#E5604E") -> str:
    """A butterfly seen from above, centred on its origin, wings open."""
    k = w / 44
    out = []
    for sx in (-1, 1):
        up = blob(
            [
                (sx * 2 * k, -2 * k),
                (sx * 10 * k, -18 * k),
                (sx * 22 * k, -17 * k),
                (sx * 21 * k, -4 * k),
                (sx * 4 * k, 1 * k),
            ],
            0.9,
        )
        low = blob(
            [
                (sx * 2 * k, 1 * k),
                (sx * 16 * k, 3 * k),
                (sx * 17 * k, 14 * k),
                (sx * 7 * k, 16 * k),
                (sx * 1.5 * k, 6 * k),
            ],
            0.9,
        )
        out.append(pen.shape(low, fill=wing))
        out.append(pen.shape(up, fill=wing))
        out.append(pen.shape(c(sx * 13 * k, -9 * k, 4 * k), c(sx * 9.5 * k, 8.5 * k, 3 * k), fill=spots))
    out.append(pen.shape(e(0, 0, 2.8 * k, 12 * k), fill="#5B3A29"))
    out.append(
        pen.stroke(
            p(f"M-1 {fmt(-11 * k)} Q{fmt(-4 * k)} {fmt(-18 * k)} {fmt(-7 * k)} {fmt(-20 * k)}"),
            p(f"M1 {fmt(-11 * k)} Q{fmt(4 * k)} {fmt(-18 * k)} {fmt(7 * k)} {fmt(-20 * k)}"),
        )
    )
    out.append(pen.solid(c(-7 * k, -20 * k, 1.4), c(7 * k, -20 * k, 1.4)))
    return "".join(out)


def zaatar_plant(pen: Pen, *, sprigs: int = 5, seed: int = 6) -> str:
    """A za'atar plant standing on its origin (about 80 wide, 80 tall): upright sprigs fanning out, each with
    pairs of soft oval leaves turned upward and a little white flower head at the tip."""
    rnd = random.Random(seed)
    stalks = []
    leaves = []
    heads = []
    for i in range(sprigs):
        t = i / (sprigs - 1) - 0.5
        ang = -90 + t * 70 + rnd.uniform(-3, 3)
        length = 74 - 26 * abs(t) + rnd.uniform(-3, 3)
        x0 = t * 14
        tip = polar(x0, 0, length, ang)
        stalks.append(p(f"M{fmt(x0)} 0 L{fmt(tip[0])} {fmt(tip[1])}"))
        for f in (0.36, 0.62, 0.86):
            bx, by = polar(x0, 0, length * f, ang)
            for side in (-1, 1):
                la = ang + side * 48
                lx, ly = polar(bx, by, 6.2, la)
                leaves.append(e(lx, ly, 6.6, 3.7, la))
        heads.append(scallop(tip[0], tip[1] - 3, 6.2, 5.4, 9, 0.7))
    return pen.stroke(*stalks, weight=MAIN) + pen.shape(*leaves, fill=ZAATAR) + pen.shape(*heads, fill=WHITE)


def cactus(pen: Pen, *, fruits: bool = True) -> str:
    """A prickly pear («صَبْر») standing on its origin (about 120 wide, 130 tall): flat oval pads growing
    from one another, orange fruits on the top edges, a few prickles."""
    pads = [
        (0, -22, 20, 26, 0),
        (-30, -50, 17, 23, -35),
        (28, -54, 17, 24, 30),
        (-6, -72, 18, 24, -5),
        (-48, -84, 14, 19, -20),
        (42, -92, 15, 20, 25),
        (10, -108, 15, 20, 12),
        (-24, -104, 13, 17, -25),
    ]
    out = []
    fruit_spots = []
    pricks = []
    for cx, cy, rx, ry, rot in pads:
        out.append(pen.shape(e(cx, cy, rx, ry, rot), fill=CACTUS))
        for dx, dy in ((-0.4, -0.2), (0.35, 0.1), (-0.1, 0.45), (0.15, -0.5)):
            a = math.radians(rot)
            x = cx + (dx * rx) * math.cos(a) - (dy * ry) * math.sin(a)
            y = cy + (dx * rx) * math.sin(a) + (dy * ry) * math.cos(a)
            pricks.append(c(x, y, 1.1))
        if fruits and cy < -80:
            for k in (-0.5, 0.5):
                ang = math.radians(rot - 90 + k * 50)
                fx = cx + math.cos(ang) * rx * 0.9
                fy = cy + math.sin(ang) * ry * 0.95
                fruit_spots.append((fx, fy, rot + k * 50))
    out.append(pen.solid(*pricks))
    out.append(pen.shape(*[e(x, y - 3, 5.2, 7, r) for x, y, r in fruit_spots], fill=CACTUS_FRUIT))
    return "".join(out)


def kite(
    pen: Pen,
    *,
    w: float = 40.0,
    colors: Sequence[str] = (RED, YELLOW, "#4FA36B", "#5E86D6"),
    tail: float = 50.0,
) -> str:
    """A diamond kite centred on its origin: four triangles to colour, a wavy tail with bows."""
    k = w / 40
    t, r, b, lft = (0, -26 * k), (20 * k, -5 * k), (0, 32 * k), (-20 * k, -5 * k)
    o = (0, -5 * k)
    out = []
    tail_pts: list[Point] = [b, (6 * k, b[1] + tail * 0.3), (-4 * k, b[1] + tail * 0.6), (5 * k, b[1] + tail)]
    out.append(pen.stroke(p(sd(tail_pts, closed=False))))
    bows = []
    for x, y in tail_pts[1:]:
        bows.append(
            p(
                f"M{fmt(x)} {fmt(y)} L{fmt(x - 7 * k)} {fmt(y - 4.5 * k)} L{fmt(x - 7 * k)} {fmt(y + 4.5 * k)} Z"
            )
        )
        bows.append(
            p(
                f"M{fmt(x)} {fmt(y)} L{fmt(x + 7 * k)} {fmt(y - 4.5 * k)} L{fmt(x + 7 * k)} {fmt(y + 4.5 * k)} Z"
            )
        )
    out.append(pen.shape(*bows, fill=colors[0]))
    for (p1, p2), fill in zip(((t, r), (r, b), (b, lft), (lft, t)), colors, strict=True):
        out.append(
            pen.shape(
                p(f"M{fmt(o[0])} {fmt(o[1])} L{fmt(p1[0])} {fmt(p1[1])} L{fmt(p2[0])} {fmt(p2[1])} Z"),
                fill=fill,
            )
        )
    return "".join(out)


def orange(cx: float, cy: float, r: float) -> str:
    return c(cx, cy, r)


def orange_tree(pen: Pen, *, seed: int = 12, fruit: int = 11) -> str:
    """An orange tree standing on its origin (about 120 wide, 130 tall): a short trunk, a round dark crown,
    round oranges."""
    rnd = random.Random(seed)
    out = [
        pen.shape(
            base_blob(
                [
                    (-10, 0),
                    (-6, -20),
                    (-8, -40),
                    (-16, -56),
                    (-6, -58),
                    (0, -46),
                    (8, -60),
                    (16, -56),
                    (7, -40),
                    (6, -20),
                    (11, 0),
                ]
            ),
            fill=BARK,
        )
    ]
    out.append(pen.shape(p(leafy_d(0, -88, 58, 44, 18, depth=0.08)), fill=LEAF_DARK))
    out.append(pen.shape(p(leafy_d(-8, -96, 40, 30, 13, depth=0.1)), fill=GRASS_DEEP))
    spots: list[Point] = [
        (-36, -70),
        (-14, -60),
        (16, -66),
        (40, -78),
        (-28, -100),
        (4, -84),
        (30, -104),
        (-6, -116),
        (-44, -92),
        (44, -98),
        (20, -122),
        (-24, -124),
    ]
    rnd.shuffle(spots)
    out.append(pen.shape(*[orange(x, y, 7.5) for x, y in spots[:fruit]], fill=ORANGE_FRUIT))
    out.append(pen.shape(*[p(leaf_d(x + 2, y - 7, 8, 3.4, -40)) for x, y in spots[:fruit]], fill=GRASS))
    return "".join(out)


def crate(
    pen: Pen, *, w: float = 64.0, h: float = 34.0, contents: str = "oranges", fill: str = WOOD_LIGHT
) -> str:
    """A wooden fruit crate standing on its origin, heaped with fruit (front view, two slats)."""
    out = []
    if contents != "none":
        r = 7.5
        items = []
        for row in range(2):
            n = int((w - 4) // (2 * r)) - row
            for i in range(n):
                items.append(c((i - (n - 1) / 2) * 2 * r, -h - r * 0.2 - row * r * 1.5, r))
        out.append(pen.shape(*items, fill=ORANGE_FRUIT if contents == "oranges" else RED))
    out.append(
        pen.shape(rect(-w / 2, -h, w, h * 0.42, 1.5), rect(-w / 2, -h * 0.5, w, h * 0.5, 1.5), fill=fill)
    )
    out.append(
        pen.shape(rect(-w / 2 - 2, -h - 1, 6, h + 1, 1.5), rect(w / 2 - 4, -h - 1, 6, h + 1, 1.5), fill=WOOD)
    )
    return "".join(out)


# ---- figs ------------------------------------------------------------------------------------------------------


def fig_leaf_d(x: float, y: float, size: float = 1.0, turn: float = 0.0) -> str:
    """Path data of a big fig leaf (three long round fingers and two small side lobes), its stalk end at
    (x, y), pointing up: about 46 across at size 1."""
    return lobed_d(
        x, y, [(-90, 1.0, 16), (-36, 0.96, 16), (22, 0.74, 18)], notch=0.6, R=23.0, size=size, turn=turn
    )


def fig(pen: Pen, *, r: float = 9.0, fill: str = FIG) -> str:
    """A ripe fig standing on its origin (its round bottom), its little stalk up."""
    return pen.shape(p(_fig_d(0, 0, r)), fill=fill) + pen.stroke(
        p(f"M{fmt(-r * 0.4)} {fmt(-r * 0.6)} Q0 {fmt(-r * 0.3)} {fmt(r * 0.4)} {fmt(-r * 0.6)}")
    )


def fig_half(pen: Pen, *, r: float = 11.0) -> str:
    """A fig cut in half lying on its side, showing its pink heart, centred on its origin."""
    out = pen.shape(e(0, 0, r * 1.25, r), fill=FIG)
    out += pen.shape(e(0, 0, r * 0.95, r * 0.72), fill=FIG_INSIDE)
    out += pen.solid(
        *[
            c(r * dx, r * dy, 0.9)
            for dx, dy in ((-0.35, -0.2), (0.1, -0.35), (0.4, 0.05), (-0.1, 0.3), (0.25, 0.35), (-0.45, 0.2))
        ]
    )
    return out


def fig_branch(pen: Pen, *, length: float = 110.0) -> str:
    """A fig branch from its origin to the left (it grows in from the page's right edge): big lobed leaves
    and ripe figs hanging under it."""
    L = length
    out = pen.shape(
        band([(0, 0), (-L * 0.4, -L * 0.04), (-L * 0.75, L * 0.04), (-L, L * 0.02)], 6), fill=BARK
    )
    out += "".join(
        fig_hanging(pen, x, y, 9.5)
        for x, y in ((-L * 0.25, -L * 0.01), (-L * 0.55, L * 0.0), (-L * 0.88, L * 0.04))
    )
    leaves = [
        p(fig_leaf_d(x, y, k, t))
        for x, y, k, t in (
            (-L * 0.12, -L * 0.02, 1.0, -20),
            (-L * 0.42, -L * 0.04, 1.05, 15),
            (-L * 0.7, L * 0.03, 0.95, -30),
            (-L * 0.98, L * 0.02, 0.85, -70),
        )
    ]
    out += pen.shape(*leaves, fill=VINE)
    return out


def fig_hanging(pen: Pen, x: float, y: float, r: float) -> str:
    """A ripe fig hanging from a branch at (x, y) (its stalk end): a short stalk, a narrow neck, a round
    heavy bottom."""
    d = (
        f"M{fmt(x - r * 0.18)} {fmt(y + r * 0.4)} "
        f"C{fmt(x - r * 0.3)} {fmt(y + r * 0.9)} {fmt(x - r * 1.3)} {fmt(y + r * 1.0)} {fmt(x - r * 1.2)} {fmt(y + r * 1.9)} "
        f"C{fmt(x - r * 1.1)} {fmt(y + r * 2.7)} {fmt(x + r * 1.1)} {fmt(y + r * 2.7)} {fmt(x + r * 1.2)} {fmt(y + r * 1.9)} "
        f"C{fmt(x + r * 1.3)} {fmt(y + r * 1.0)} {fmt(x + r * 0.3)} {fmt(y + r * 0.9)} {fmt(x + r * 0.18)} {fmt(y + r * 0.4)} Z"
    )
    return pen.shape(band([(x, y - 1), (x, y + r * 0.5)], r * 0.32), fill=VINE) + pen.shape(p(d), fill=FIG)


def fig_tree(pen: Pen, *, seed: int = 4) -> str:
    """A small fig tree standing on its origin (about 100 wide, 120 tall): a smooth grey trunk with open
    branches, big lobed leaves and hanging figs."""
    rnd = random.Random(seed)
    out = [
        pen.shape(
            band([(0, 0), (-2, -36), (-20, -66)], 9),
            band([(-2, -36), (18, -62), (30, -76)], 7),
            band([(-1, -40), (2, -86)], 6),
            fill="#A9A49A",
        )
    ]
    figs = []
    for x, y in ((-30, -66), (-6, -58), (22, -54), (38, -78), (-38, -92), (12, -92)):
        figs.append(fig_hanging(pen, x, y, 6.5))
    leaves = []
    for x, y, t in (
        (-34, -70, -60),
        (-14, -98, -20),
        (20, -100, 25),
        (40, -76, 65),
        (2, -72, 0),
        (-42, -104, -45),
        (44, -112, 40),
    ):
        leaves.append(p(fig_leaf_d(x, y + 14, 1.0 + rnd.uniform(-0.05, 0.05), t)))
    out.append(pen.shape(*leaves[:4], fill=LEAF_DARK))
    out.append("".join(figs[:3]))
    out.append(pen.shape(*leaves[4:], fill=VINE))
    out.append("".join(figs[3:]))
    return "".join(out)


# ---- seated people ---------------------------------------------------------------------------------------------


def _head(
    pen: Pen, cx: float, cy: float, r: float, *, hair: str, hair_fill: str, skin: str, scarf: str = ""
) -> str:
    out = []
    if scarf:
        out.append(
            pen.shape(
                p(
                    f"M{fmt(cx - r * 1.4)} {fmt(cy + r * 0.3)} C{fmt(cx - r * 1.55)} {fmt(cy - r * 1.75)} {fmt(cx + r * 1.55)} {fmt(cy - r * 1.75)} "
                    f"{fmt(cx + r * 1.4)} {fmt(cy + r * 0.3)} C{fmt(cx + r * 1.45)} {fmt(cy + r * 1.2)} {fmt(cx + r * 1.2)} {fmt(cy + r * 1.6)} "
                    f"{fmt(cx + r * 0.9)} {fmt(cy + r * 1.8)} L{fmt(cx - r * 0.9)} {fmt(cy + r * 1.8)} C{fmt(cx - r * 1.2)} {fmt(cy + r * 1.6)} "
                    f"{fmt(cx - r * 1.45)} {fmt(cy + r * 1.2)} {fmt(cx - r * 1.4)} {fmt(cy + r * 0.3)} Z"
                ),
                fill=scarf,
            )
        )
        out.append(pen.shape(e(cx, cy + r * 0.12, r * 0.84, r * 0.94), fill=skin))
        out.append(face(pen, cx, cy + r * 0.16, r * 0.86))
        return "".join(out)
    if hair == "pigtails":
        out.append(
            pen.shape(
                e(cx - r * 1.3, cy + r * 0.15, r * 0.4, r * 0.58, 20),
                e(cx + r * 1.3, cy + r * 0.15, r * 0.4, r * 0.58, -20),
                fill=hair_fill,
            )
        )
    out.append(pen.shape(c(cx, cy, r), fill=skin))
    cap = (
        f"M{fmt(cx - r - 0.6)} {fmt(cy + 2)} C{fmt(cx - r - 1)} {fmt(cy - r - 4)} {fmt(cx + r + 1)} {fmt(cy - r - 4)} {fmt(cx + r + 0.6)} {fmt(cy + 2)} "
        f"C{fmt(cx + r * 0.5)} {fmt(cy - r * 0.55)} {fmt(cx - r * 0.2)} {fmt(cy - r * 0.4)} {fmt(cx - r * 0.15)} {fmt(cy - r * 0.75)} "
        f"C{fmt(cx - r * 0.4)} {fmt(cy - r * 0.35)} {fmt(cx - r * 0.8)} {fmt(cy - r * 0.4)} {fmt(cx - r - 0.6)} {fmt(cy + 2)} Z"
    )
    out.append(pen.shape(p(cap), fill=hair_fill))
    if hair == "pigtails":
        out.append(
            pen.shape(c(cx - r * 1.05, cy - r * 0.3, 2.6), c(cx + r * 1.05, cy - r * 0.3, 2.6), fill=RED)
        )
    out.append(face(pen, cx, cy + 2, r))
    return "".join(out)


def seated(
    pen: Pen,
    *,
    kind: str = "girl",
    dress: str = PINK,
    shirt: str = "#4FA89A",
    trousers: str = "#2F3E7A",
    skin: str = "#F3C9A4",
    hair_fill: str = "#5B3A29",
    scarf: str = "#E9D9B8",
    hands: str = "lap",
) -> str:
    """A person sitting cross-legged on the ground and facing us, on its origin: `kind` girl, boy or grandma
    (a grandmother in an embroidered thob and a soft headscarf; about 95 tall, a child about 70).
    `hands`: lap (on the knees), tell (one hand raised, telling a story) or clap."""
    big = kind == "grandma"
    k = 1.3 if big else 1.0
    lap_fill = dress if kind != "boy" else trousers
    top_fill = dress if kind != "boy" else shirt
    out = []
    # the crossed legs (a long soft lap) and the two feet tucked in front
    out.append(
        pen.shape(
            p(
                f"M{fmt(-27 * k)} 0 C{fmt(-30 * k)} {fmt(-14 * k)} {fmt(-12 * k)} {fmt(-17 * k)} 0 {fmt(-15 * k)} C{fmt(12 * k)} {fmt(-17 * k)} {fmt(30 * k)} {fmt(-14 * k)} {fmt(27 * k)} 0 Z"
            ),
            fill=lap_fill,
        )
    )
    out.append(
        pen.shape(
            e(-8 * k, -3 * k, 7 * k, 3.6 * k, -8),
            e(8 * k, -3 * k, 7 * k, 3.6 * k, 8),
            fill=skin if kind != "boy" else RED,
        )
    )
    sh_y = -46 * k
    body = f"M{fmt(-10 * k)} {fmt(sh_y)} C{fmt(-4 * k)} {fmt(sh_y - 3 * k)} {fmt(4 * k)} {fmt(sh_y - 3 * k)} {fmt(10 * k)} {fmt(sh_y)} L{fmt(16 * k)} {fmt(-12 * k)} Q0 {fmt(-8 * k)} {fmt(-16 * k)} {fmt(-12 * k)} Z"
    out.append(pen.shape(p(body), fill=top_fill))
    if big:
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-7 * k)} {fmt(sh_y + 2)} L{fmt(7 * k)} {fmt(sh_y + 2)} L{fmt(6 * k)} {fmt(sh_y + 20 * k)} L{fmt(-6 * k)} {fmt(sh_y + 20 * k)} Z"
                ),
                fill=RED,
            )
        )
        out.append(
            pen.stroke(
                p(
                    f"M0 {fmt(sh_y + 5 * k)} L{fmt(4 * k)} {fmt(sh_y + 11 * k)} L0 {fmt(sh_y + 17 * k)} L{fmt(-4 * k)} {fmt(sh_y + 11 * k)} Z"
                )
            )
        )
    hand_pts = {
        "lap": ((-17, -16), (17, -16)),
        "tell": ((-17, -16), (30, -50)),
        "clap": ((-3, -34), (3, -34)),
    }[hands]
    for sx, (hx, hy) in zip((-1, 1), hand_pts, strict=True):
        out.append(pen.shape(limb(sx * 9.5 * k, sh_y + 4 * k, hx * k, hy * k, 7 * k), fill=top_fill))
        out.append(pen.shape(c(hx * k, hy * k, 4 * k), fill=skin))
    r = 13 * k
    out.append(
        _head(
            pen,
            0,
            sh_y - r + 1,
            r,
            hair="pigtails" if kind == "girl" else "short",
            hair_fill=hair_fill,
            skin=skin,
            scarf=scarf if big else "",
        )
    )
    return "".join(out)


def mat(
    pen: Pen,
    *,
    w: float = 150.0,
    depth: float = 40.0,
    fill: str = TATREEZ_RED,
    border: str = "#F2B33D",
    pattern: bool = True,
) -> str:
    """A woven floor mat seen at a slant, centred on its origin: a border band and (with `pattern`) a row of
    big diamonds."""
    t, b = -depth / 2, depth / 2
    outer = p(
        f"M{fmt(-w * 0.42)} {fmt(t)} L{fmt(w * 0.42)} {fmt(t)} L{fmt(w / 2)} {fmt(b)} L{fmt(-w / 2)} {fmt(b)} Z"
    )
    inset = 5.5
    inner = p(
        f"M{fmt(-w * 0.42 + inset)} {fmt(t + inset * 0.7)} L{fmt(w * 0.42 - inset)} {fmt(t + inset * 0.7)} L{fmt(w / 2 - inset * 1.2)} {fmt(b - inset * 0.7)} L{fmt(-w / 2 + inset * 1.2)} {fmt(b - inset * 0.7)} Z"
    )
    out = pen.shape(outer, fill=border) + pen.shape(inner, fill=fill)
    if not pattern:
        return out
    n = 5
    diamonds = []
    for i in range(n):
        x = (i - (n - 1) / 2) * w * 0.17
        diamonds.append(p(f"M{fmt(x)} {fmt(t + 9)} L{fmt(x + 9)} 0 L{fmt(x)} {fmt(b - 9)} L{fmt(x - 9)} 0 Z"))
    out += pen.shape(*diamonds, fill=border)
    return out


def tray(pen: Pen, *, w: float = 50.0, fill: str = "#E2BE6E") -> str:
    """A round brass tray seen at a slant, centred on its origin."""
    return (
        pen.shape(e(0, 2.5, w / 2, w * 0.2), fill=fill)
        + pen.shape(e(0, 0, w / 2, w * 0.2), fill=fill)
        + pen.stroke(e(0, 0, w * 0.38, w * 0.13))
    )


def hen(pen: Pen, *, fill: str = "#E9A25A") -> str:
    """A round village hen facing right, standing on its origin (about 40 tall)."""
    out = pen.stroke(p("M-3 -9 L-4 0 M3 -9 L4 0"), weight=MAIN)
    out += pen.shape(p("M-22 -26 C-26 -36 -20 -42 -14 -34 C-14 -42 -6 -42 -8 -32 Z"), fill="#C8603A")  # tail
    out += pen.shape(
        blob([(-18, -14), (-20, -28), (-4, -32), (6, -34), (16, -24), (12, -10), (0, -7)], 0.9), fill=fill
    )
    out += pen.shape(c(12, -36, 8), fill=fill)
    out += pen.shape(p("M8 -43 Q10 -50 13 -44 Q16 -50 18 -42 Z"), fill=RED)  # comb
    out += pen.shape(p("M19 -38 L25 -35.5 L19 -33 Z"), fill=YELLOW)
    out += pen.shape(e(17, -30, 2.2, 3.2), fill=RED)
    out += pen.solid(c(14, -38, 1.4))
    out += pen.shape(p("M-10 -22 Q0 -14 8 -22 Q0 -28 -10 -22 Z"), fill="#C8603A")  # wing
    return out


# ---- the sea of Jaffa ------------------------------------------------------------------------------------------


def boat(pen: Pen, *, w: float = 80.0, hull: str = HULL, sail: str = SAIL, stripe: str = YELLOW) -> str:
    """A Jaffa fishing boat with a lateen sail, bow to the right, its origin on the waterline's middle."""
    out = []
    yard_top = (w * 0.22, -w * 1.0)
    yard_foot = (-w * 0.38, -w * 0.3)
    out.append(
        pen.shape(rect(-w * 0.02 - 2.6, -w * 0.5, 5.2, w * 0.5 - 10, 2), fill=WOOD)
    )  # mast (behind the sail)
    sail_d = (
        f"M{fmt(yard_top[0])} {fmt(yard_top[1])} Q{fmt(w * 0.42)} {fmt(-w * 0.5)} {fmt(w * 0.32)} {fmt(-w * 0.24)} "
        f"L{fmt(yard_foot[0] + 6)} {fmt(yard_foot[1] + 4)} Z"
    )
    out.append(pen.shape(p(sail_d), fill=sail))
    out.append(pen.stroke(p(f"M{fmt(w * 0.27)} {fmt(-w * 0.62)} L{fmt(-w * 0.12)} {fmt(-w * 0.36)}")))
    out.append(pen.shape(band([yard_foot, yard_top], 3.6), fill=WOOD_DARK))
    body = (
        f"M{fmt(-w / 2)} -16 L{fmt(w / 2 + 4)} -21 C{fmt(w * 0.44)} -4 {fmt(w * 0.32)} 6 {fmt(w * 0.18)} 6 "
        f"L{fmt(-w * 0.24)} 6 C{fmt(-w * 0.4)} 6 {fmt(-w * 0.47)} -3 {fmt(-w / 2)} -16 Z"
    )
    out.append(pen.shape(p(body), fill=hull))
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w * 0.49)} -13 L{fmt(w / 2 + 2.4)} -17.6 L{fmt(w / 2 + 1.4)} -12.4 L{fmt(-w * 0.47)} -8 Z"
            ),
            fill=stripe,
        )
    )
    return "".join(out)


def gull(pen: Pen, *, w: float = 34.0) -> str:
    """A seagull gliding, centred on its origin: two arched wings and a small round body."""
    k = w / 34
    wing = (
        f"M0 {fmt(-1 * k)} C{fmt(-5 * k)} {fmt(-9 * k)} {fmt(-12 * k)} {fmt(-10 * k)} {fmt(-17 * k)} {fmt(-3 * k)} "
        f"C{fmt(-11 * k)} {fmt(-6 * k)} {fmt(-6 * k)} {fmt(-4 * k)} 0 {fmt(3 * k)} "
        f"C{fmt(6 * k)} {fmt(-4 * k)} {fmt(11 * k)} {fmt(-6 * k)} {fmt(17 * k)} {fmt(-3 * k)} "
        f"C{fmt(12 * k)} {fmt(-10 * k)} {fmt(5 * k)} {fmt(-9 * k)} 0 {fmt(-1 * k)} Z"
    )
    return pen.shape(p(wing), fill=GULL)


def sea(pen: Pen, w: float, y: float, *, rows: int = 4, floor: float = 260.0, fill: str = "#5BA9D6") -> str:
    """The sea from the horizon `y` down: one big area cut into bands by soft wave lines."""
    out = pen.shape(rect(-10, y, w + 20, floor - y), fill=fill)
    lines = []
    for i in range(rows):
        yy = y + 12 + i * (floor - y) / (rows + 0.5)
        lines.append(p(_wave_line(-10, w + 10, yy, 2.6 + i * 0.8, 6 + (i % 2))))
    out += pen.stroke(*lines)
    return out


def _wave_line(x0: float, x1: float, y: float, amp: float, n: int) -> str:
    step = (x1 - x0) / n
    d = f"M{fmt(x0)} {fmt(y)}"
    for i in range(n):
        xa = x0 + step * i
        d += f" Q{fmt(xa + step / 4)} {fmt(y - amp)} {fmt(xa + step / 2)} {fmt(y)} Q{fmt(xa + step * 0.75)} {fmt(y + amp)} {fmt(xa + step)} {fmt(y)}"
    return d


def block(
    pen: Pen,
    *,
    w: float = 30.0,
    h: float = 26.0,
    windows: int = 1,
    dome: bool = False,
    fill: str = LIMESTONE,
    win: str = SHUTTER,
) -> str:
    """A little stone house of the old city standing on its origin: a flat roof, `windows` arched windows,
    perhaps a dome."""
    out = []
    if dome:
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-w * 0.32)} {fmt(-h)} C{fmt(-w * 0.32)} {fmt(-h - w * 0.42)} {fmt(w * 0.32)} {fmt(-h - w * 0.42)} {fmt(w * 0.32)} {fmt(-h)} Z"
                ),
                fill=fill,
            )
        )
    out.append(pen.shape(rect(-w / 2, -h, w, h), fill=fill))
    out.append(pen.shape(rect(-w / 2 - 1.5, -h - 3, w + 3, 4, 1.5), fill=LIMESTONE_DEEP))
    ww = min(9.0, w / (windows + 1) * 0.9)
    arches = []
    for i in range(windows):
        x = -w / 2 + w * (i + 1) / (windows + 1)
        arches.append(p(_arch_d(x - ww / 2, -h * 0.3, ww, h * 0.42)))
    out.append(pen.shape(*arches, fill=win))
    return "".join(out)


def minaret(pen: Pen, *, h: float = 100.0, fill: str = LIMESTONE) -> str:
    """A slender stone minaret standing on its origin: a square shaft, a balcony, a narrower upper shaft, a
    pointed cap and a small crescent."""
    out = []
    out.append(pen.shape(rect(-7, -h * 0.68, 14, h * 0.68), fill=fill))
    out.append(pen.shape(p(_arch_d(-3, -h * 0.36, 6, 13)), p(_arch_d(-3, -h * 0.56, 6, 11)), fill=SHUTTER))
    out.append(pen.shape(rect(-5, -h * 0.84, 10, h * 0.17), fill=fill))
    out.append(pen.shape(rect(-10, -h * 0.7, 20, 5, 1.5), fill=LIMESTONE_DEEP))
    out.append(
        pen.shape(p(f"M-6.5 {fmt(-h * 0.84)} L0 {fmt(-h * 0.97)} L6.5 {fmt(-h * 0.84)} Z"), fill=DOME_GOLD)
    )
    out.append(pen.shape(p(crescent_up(0, -h * 0.97 - 5, 4.2)), fill=DOME_GOLD))
    return "".join(out)


def crescent_up(cx: float, cy: float, r: float) -> str:
    """Path data of a small crescent with its horns up (a finial), centred at (cx, cy)."""
    return (
        f"M{fmt(cx - r)} {fmt(cy - r * 0.2)} A{fmt(r)} {fmt(r)} 0 0 0 {fmt(cx + r)} {fmt(cy - r * 0.2)} "
        f"A{fmt(r * 0.8)} {fmt(r * 0.8)} 0 0 1 {fmt(cx - r)} {fmt(cy - r * 0.2)} Z"
    )


def clock_tower(pen: Pen, *, h: float = 92.0, fill: str = LIMESTONE) -> str:
    """A square stone clock tower standing on its origin: a round clock face (hands only, no numbers), arched
    openings, a cornice and a small pointed roof."""
    out = []
    out.append(pen.shape(rect(-11, -h * 0.82, 22, h * 0.82), fill=fill))
    out.append(pen.shape(p(_arch_d(-4.5, -h * 0.12, 9, 18)), p(_arch_d(-4, -h * 0.4, 8, 14)), fill=SHUTTER))
    out.append(
        pen.shape(rect(-13, -h * 0.84, 26, 5, 1.5), rect(-13, -h * 0.5, 26, 4, 1.5), fill=LIMESTONE_DEEP)
    )
    out.append(pen.shape(c(0, -h * 0.67, 7.5), fill=WHITE))
    out.append(
        pen.stroke(
            p(f"M0 {fmt(-h * 0.67)} L0 {fmt(-h * 0.67 - 5)}"),
            p(f"M0 {fmt(-h * 0.67)} L3.6 {fmt(-h * 0.67 + 1.4)}"),
        )
    )
    out.append(pen.shape(p(f"M-12 {fmt(-h * 0.85)} L0 {fmt(-h)} L12 {fmt(-h * 0.85)} Z"), fill=RED))
    return "".join(out)


def palm(pen: Pen, *, h: float = 80.0) -> str:
    """A date palm standing on its origin: a slightly curved trunk and a crown of long drooping fronds."""
    top = (6.0, -h)
    out = [pen.shape(band([(0, 0), (4, -h * 0.5), top], 7), fill=BARK)]
    out.append(
        pen.stroke(
            *[
                p(f"M{fmt(-3 + 4 * f)} {fmt(-h * f)} L{fmt(4 + 4 * f)} {fmt(-h * f - 2)}")
                for f in (0.2, 0.4, 0.6, 0.78)
            ]
        )
    )
    fronds = [p(leaf_d(top[0], top[1], h * 0.42, h * 0.11, a)) for a in (-160, -125, -90, -55, -20, 25, 160)]
    out.append(pen.shape(*fronds, fill=GRASS_DEEP))
    out.append(pen.shape(c(top[0] - 3, top[1] + 4, 3.2), c(top[0] + 3, top[1] + 5, 3.2), fill=ORANGE))
    return "".join(out)


def lantern(pen: Pen, *, h: float = 34.0, fill: str = GOLD, glass: str = "#FFE9A8") -> str:
    """A hanging lantern whose ring (its origin) hangs from a chain above: a cap, glass panes, a base."""
    k = h / 34
    out = pen.stroke(p(f"M0 {fmt(-14 * k)} L0 0"))
    out += pen.shape(c(0, 0, 2.2 * k), fill=fill)
    out += pen.shape(
        p(f"M{fmt(-9 * k)} {fmt(9 * k)} L0 {fmt(2 * k)} L{fmt(9 * k)} {fmt(9 * k)} Z"), fill=fill
    )
    out += pen.shape(
        p(
            f"M{fmt(-8 * k)} {fmt(9 * k)} L{fmt(8 * k)} {fmt(9 * k)} L{fmt(6 * k)} {fmt(26 * k)} L{fmt(-6 * k)} {fmt(26 * k)} Z"
        ),
        fill=glass,
    )
    out += pen.stroke(p(f"M0 {fmt(9 * k)} L0 {fmt(26 * k)}"))
    out += pen.shape(
        p(
            f"M{fmt(-7 * k)} {fmt(26 * k)} L{fmt(7 * k)} {fmt(26 * k)} L{fmt(3 * k)} {fmt(32 * k)} L{fmt(-3 * k)} {fmt(32 * k)} Z"
        ),
        fill=fill,
    )
    return out


# ---- the Aqsa mosque compound (exterior only, simplified) -----------------------------------------------------


def dome_of_the_rock(pen: Pen, *, w: float = 150.0) -> str:
    """The Dome of the Rock seen from outside, standing on its origin (about w wide, 0.98 w tall): three
    faces of the octagon with blue tile panels and arched windows over a pale marble base, a drum with
    windows, the golden dome and its crescent finial. Big simple shapes; no inscriptions."""
    W = w
    H = W * 0.36  # the octagon's wall
    side = W * 0.24
    out = []
    # the drum and the dome (behind the parapet)
    dw = W * 0.5
    drum_h = W * 0.15
    roof = -H - 6
    out.append(
        pen.shape(
            p(
                f"M{fmt(-dw * 0.5)} {fmt(roof - drum_h)} C{fmt(-dw * 0.56)} {fmt(roof - drum_h - dw * 0.62)} {fmt(-dw * 0.12)} {fmt(roof - drum_h - dw * 0.8)} 0 {fmt(roof - drum_h - dw * 0.82)} C{fmt(dw * 0.12)} {fmt(roof - drum_h - dw * 0.8)} {fmt(dw * 0.56)} {fmt(roof - drum_h - dw * 0.62)} {fmt(dw * 0.5)} {fmt(roof - drum_h)} Z"
            ),
            fill=DOME_GOLD,
        )
    )
    top = roof - drum_h - dw * 0.82
    out.append(pen.shape(rect(-2.2, top - 13, 4.4, 13, 1.5), fill=DOME_GOLD))
    out.append(pen.shape(c(0, top - 9, 3.4), fill=DOME_GOLD))
    out.append(pen.shape(p(crescent_up(0, top - 18, 5.2)), fill=DOME_GOLD))
    out.append(pen.shape(rect(-dw * 0.5 - 2, roof - drum_h - 4, dw + 4, 5, 2), fill=TILE_TEAL))
    out.append(pen.shape(rect(-dw * 0.5, roof - drum_h + 1, dw, drum_h - 1), fill=TILE_BLUE))
    n = 5
    arches = []
    for i in range(n):
        x = -dw * 0.5 + dw * (i + 0.5) / n
        arches.append(p(_arch_d(x - 3.4, roof - 3, 6.8, drum_h - 7)))
    out.append(pen.shape(*arches, fill=WHITE))
    # the sloping roof between the drum and the parapet
    out.append(
        pen.shape(
            p(
                f"M{fmt(-W * 0.36)} {fmt(-H)} L{fmt(-dw * 0.5)} {fmt(roof)} L{fmt(dw * 0.5)} {fmt(roof)} L{fmt(W * 0.36)} {fmt(-H)} Z"
            ),
            fill=GREY_BLUE,
        )
    )
    # three faces: left and right foreshortened, the middle one square-on
    # (the side faces turn away: their outer edge is shorter, top and bottom slope toward it, so the walls read
    # as an octagon and not as one flat front)
    drop = H * 0.1

    def side_face(xo: float, xi: float) -> None:
        """A side face from its outer edge `xo` to the corner `xi` it shares with the middle face."""

        def y(x: float, at: float) -> float:  # the height `at` on the corner edge, followed along the face
            t = (x - xi) / (xo - xi)
            top, bottom = -H + t * drop, -t * drop * 0.5
            f = (at + H) / H  # 0 at the top of the wall, 1 at its foot
            return top + (bottom - top) * f

        def quad(top: float, bottom: float) -> str:
            return poly([(xo, y(xo, top)), (xi, top), (xi, bottom), (xo, y(xo, bottom))])

        out.append(pen.shape(quad(-H, 0), fill=STONE))
        out.append(pen.shape(quad(-H, -H * 0.44), fill=TILE_BLUE))
        out.append(pen.shape(quad(-H, -H + 5), fill=TILE_TEAL))
        wins = []
        for i in range(2):
            x = xi + (xo - xi) * (i + 0.5) / 2
            ww = min(8.0, abs(xo - xi) / 2 * 0.42)
            wins.append(p(_arch_d(x - ww / 2, y(x, -H * 0.5), ww, H * 0.3)))
        out.append(pen.shape(*wins, fill=WHITE))

    side_face(-W / 2, -W / 2 + side)
    side_face(W / 2, W / 2 - side)
    x0, x1 = -W / 2 + side, W / 2 - side
    fw = x1 - x0
    out.append(pen.shape(rect(x0, -H, fw, H), fill=STONE))
    out.append(pen.shape(rect(x0, -H, fw, H * 0.56), fill=TILE_BLUE))
    out.append(pen.shape(rect(x0, -H, fw, 5), fill=TILE_TEAL))
    wins = []
    for i in range(3):
        x = x0 + fw * (i + 0.5) / 3
        ww = min(9.0, fw / 3 * 0.45)
        wins.append(p(_arch_d(x - ww / 2, -H * 0.5, ww, H * 0.34)))
    out.append(pen.shape(*wins, fill=WHITE))
    # the south porch: an arched doorway with a small roof
    out.append(pen.shape(rect(-W * 0.14, -H * 0.42, W * 0.28, H * 0.42), fill=STONE))
    out.append(pen.shape(rect(-W * 0.16, -H * 0.46, W * 0.32, 5, 1.5), fill=STONE_DEEP))
    out.append(
        pen.shape(
            p(_arch_d(-W * 0.11, 0, W * 0.09, H * 0.32)),
            p(_arch_d(W * 0.02, 0, W * 0.09, H * 0.32)),
            fill=DOOR,
        )
    )
    return "".join(out)


def qibli_mosque(pen: Pen, *, w: float = 110.0) -> str:
    """The Qibli (Al-Aqsa) mosque seen from outside, standing on its origin: a long stone front with a
    row of arches, a raised middle bay and the grey lead dome behind. Simple shapes, no inscriptions."""
    h = w * 0.3
    out = []
    dw = w * 0.32
    base = -h - 16  # the drum's top
    out.append(pen.shape(rect(-dw / 2 + 2, base, dw - 4, 18), fill=STONE))
    out.append(
        pen.shape(
            p(
                f"M{fmt(-dw / 2)} {fmt(base)} C{fmt(-dw / 2)} {fmt(base - dw * 0.72)} {fmt(dw / 2)} {fmt(base - dw * 0.72)} {fmt(dw / 2)} {fmt(base)} Z"
            ),
            fill=DOME_LEAD,
        )
    )
    out.append(pen.shape(rect(-dw / 2 - 2, base - 2, dw + 4, 6, 2), fill=STONE_DEEP))
    tip = base - dw * 0.54
    out.append(pen.shape(rect(-1.6, tip - 8, 3.2, 9, 1), fill=DOME_GOLD))
    out.append(pen.shape(p(crescent_up(0, tip - 12, 3.8)), fill=DOME_GOLD))
    out.append(pen.shape(rect(-w / 2, -h, w, h), fill=STONE))
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w * 0.14)} {fmt(-h)} L{fmt(-w * 0.14)} {fmt(-h - 6)} L0 {fmt(-h - 12)} L{fmt(w * 0.14)} {fmt(-h - 6)} L{fmt(w * 0.14)} {fmt(-h)} Z"
            ),
            fill=STONE,
        )
    )
    n = 7
    arches = []
    for i in range(n):
        x = -w / 2 + w * (i + 0.5) / n
        aw = w / n * 0.62
        arches.append(p(_arch_d(x - aw / 2, 0, aw, h * 0.66)))
    out.append(pen.shape(*arches, fill=SHUTTER))
    out.append(pen.shape(rect(-w / 2 - 2, -h - 3, w + 4, 5, 2), fill=STONE_DEEP))
    return "".join(out)


def cypress_tree(pen: Pen, *, h: float = 70.0, fill: str = CYPRESS) -> str:
    """A tall cypress tree standing on its origin: a slim flame of green on a short trunk."""
    wdt = h * 0.2
    out = pen.shape(rect(-2.5, -8, 5, 8, 1.5), fill=BARK)
    out += pen.shape(
        p(
            f"M0 {fmt(-h)} C{fmt(wdt * 0.9)} {fmt(-h * 0.7)} {fmt(wdt * 0.75)} {fmt(-h * 0.2)} {fmt(wdt * 0.45)} -6 Q0 -3 {fmt(-wdt * 0.45)} -6 C{fmt(-wdt * 0.75)} {fmt(-h * 0.2)} {fmt(-wdt * 0.9)} {fmt(-h * 0.7)} 0 {fmt(-h)} Z"
        ),
        fill=fill,
    )
    return out


def city_wall(
    pen: Pen, *, w: float = 200.0, h: float = 40.0, merlons: int = 9, fill: str = LIMESTONE, seed: int = 3
) -> str:
    """The old city's stone wall standing on its origin's left end (it runs right to x = w): crenellations
    along the top and big stone courses."""
    mw = w / (2 * merlons)
    d = f"M0 0 L0 {fmt(-h)}"
    for i in range(merlons):
        x = i * 2 * mw
        d += f" L{fmt(x + mw * 0.5)} {fmt(-h)} L{fmt(x + mw * 0.5)} {fmt(-h - 8)} L{fmt(x + mw * 1.5)} {fmt(-h - 8)} L{fmt(x + mw * 1.5)} {fmt(-h)}"
    d += f" L{fmt(w)} {fmt(-h)} L{fmt(w)} 0 Z"
    return pen.shape(p(d), fill=fill) + stone_courses(pen, 0, -h, w, 0, course=14, seed=seed)


# ---- the souk --------------------------------------------------------------------------------------------------


def awning(
    pen: Pen,
    *,
    w: float = 120.0,
    h: float = 26.0,
    stripes: int = 6,
    colors: Sequence[str] = (AWNING_A, AWNING_B),
) -> str:
    """A striped shop awning hanging from y = 0 across 0…w, its edge scalloped."""
    sw = w / stripes
    out = []
    for i in range(stripes):
        x = i * sw
        d = f"M{fmt(x)} 0 L{fmt(x + sw)} 0 L{fmt(x + sw)} {fmt(h)} A{fmt(sw / 2)} {fmt(sw / 2.4)} 0 0 1 {fmt(x)} {fmt(h)} Z"
        out.append(pen.shape(p(d), fill=colors[i % len(colors)]))
    out.append(pen.shape(rect(-3, -5, w + 6, 6, 2), fill=WOOD))
    return "".join(out)


def sack(
    pen: Pen, *, w: float = 38.0, spice: str = SPICE_RED, fill: str = "#E6D3AE", scoop: bool = False
) -> str:
    """An open sack of spice standing on its origin: a rolled-down rim and a heaped mound of spice."""
    h = w * 0.9
    out = []
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w * 0.42)} {fmt(-h + 2)} C{fmt(-w * 0.34)} {fmt(-h - w * 0.32)} {fmt(w * 0.34)} {fmt(-h - w * 0.32)} {fmt(w * 0.42)} {fmt(-h + 2)} Z"
            ),
            fill=spice,
        )
    )
    if scoop:
        out.append(pen.shape(band([(w * 0.05, -h - w * 0.1), (w * 0.35, -h - w * 0.45)], 3.4), fill=WOOD))
        out.append(pen.shape(e(w * 0.02, -h - w * 0.05, 6, 4, -20), fill="#C9CCD6"))
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w * 0.44)} {fmt(-h + 4)} C{fmt(-w * 0.56)} {fmt(-h * 0.5)} {fmt(-w * 0.6)} -4 {fmt(-w * 0.4)} 0 L{fmt(w * 0.4)} 0 C{fmt(w * 0.6)} -4 {fmt(w * 0.56)} {fmt(-h * 0.5)} {fmt(w * 0.44)} {fmt(-h + 4)} Z"
            ),
            fill=fill,
        )
    )
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w * 0.5)} {fmt(-h + 2)} Q0 {fmt(-h + 7)} {fmt(w * 0.5)} {fmt(-h + 2)} L{fmt(w * 0.47)} {fmt(-h + 10)} Q0 {fmt(-h + 15)} {fmt(-w * 0.47)} {fmt(-h + 10)} Z"
            ),
            fill="#D4BC8E",
        )
    )
    return "".join(out)


def fruit_pile(pen: Pen, *, r: float = 7.0, base: int = 5, fill: str = ORANGE_FRUIT) -> str:
    """A pyramid of round fruit standing on its origin."""
    items = []
    for row in range(base):
        n = base - row
        for i in range(n):
            items.append(c((i - (n - 1) / 2) * 2 * r, -r - row * r * 1.72, r))
    return pen.shape(*items, fill=fill)


# ---- birds and flowers -----------------------------------------------------------------------------------------


def sunbird(pen: Pen, *, body: str = SUNBIRD, shine: str = SUNBIRD_SHINE) -> str:
    """The Palestine sunbird («عُصْفورُ الشَّمْس») perched and facing left, its feet on the origin (the top
    of a branch; about 110 long): a plump tilted body, a round head, a long curved beak, a folded wing, a
    long tail and the little orange tuft at its side."""
    out = []
    out.append(pen.shape(p("M20 -24 L58 -2 Q62 4 55 5 L14 -12 Z"), fill=body))  # tail
    out.append(pen.shape(e(6, -27, 26, 17, -28), fill=body))
    out.append(pen.shape(p("M-8 -20 Q0 -10 10 -14 Q2 -22 -8 -20 Z"), fill="#F2A23A"))  # side tuft
    out.append(pen.shape(p("M-6 -38 C8 -46 30 -34 38 -14 C24 -20 6 -22 -4 -28 Z"), fill=shine))  # wing
    out.append(pen.stroke(p("M4 -34 Q18 -32 30 -20"), p("M2 -28 Q16 -26 26 -18")))
    out.append(
        pen.shape(p("M-26 -50 C-38 -54 -52 -49 -60 -37 C-50 -44 -38 -46 -26 -45 Z"), fill="#2E2A33")
    )  # beak
    out.append(pen.shape(c(-16, -46, 12.5), fill=shine))  # head
    out.append(pen.solid(c(-19, -48.5, 2.3)))
    feet = [p("M-4 -10 L-6 0"), p("M6 -9 L6 0"), p("M-11 1 Q-6 -3 -1 1"), p("M1 1 Q6 -3 11 1")]
    out.append(pen.stroke(*feet, weight=MAIN))
    return "".join(out)


def trumpet_flower(cx: float, cy: float, length: float, angle: float) -> str:
    """Path data of a tubular flower from its base (cx, cy) along `angle`: a narrow tube flaring into a
    frilled mouth (sunbird food)."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    L = length

    def pt(t: float, s: float) -> str:
        return f"{fmt(cx + ux * L * t + nx * s)} {fmt(cy + uy * L * t + ny * s)}"

    tw, mw = L * 0.1, L * 0.34
    return (
        f"M{pt(0, -tw)} L{pt(0.62, -tw * 1.2)} Q{pt(0.85, -mw * 0.6)} {pt(0.95, -mw)} "
        f"Q{pt(1.08, -mw * 0.45)} {pt(1.0, 0)} Q{pt(1.08, mw * 0.45)} {pt(0.95, mw)} "
        f"Q{pt(0.85, mw * 0.6)} {pt(0.62, tw * 1.2)} L{pt(0, tw)} Z"
    )


# ---- the embroidered dress -----------------------------------------------------------------------------------


def thob(pen: Pen, *, fill: str = THOB) -> str:
    """A Palestinian embroidered dress laid out flat (about 176 wide, 200 tall), its hem's middle on the
    origin: wide winged sleeves with embroidered cuffs, a square chest panel with an eight-pointed star, a
    sash, side panels of cypress trees and a hem band of stepped teeth (big cells, `heritage`)."""
    from qamra_workbook.coloring.parts import heritage as hz  # local: keeps heritage free of this module

    def edge(y: float) -> float:  # the body's half-width at height y (armpit → hem)
        return 36 + 26 * (y + 150) / 150

    out = []
    for sx in (-1, 1):
        sleeve = [(sx * 30, -197), (sx * 88, -158), (sx * 80, -104), (sx * 37, -142)]
        out.append(pen.shape(poly_d(sleeve), fill=fill))
        cuff = [(sx * 74, -167), (sx * 88, -158), (sx * 80, -104), (sx * 67, -112)]
        out.append(pen.shape(poly_d(cuff), fill=TATREEZ_RED))
        out.append(pen.stroke(p(f"M{fmt(sx * 81)} {fmt(-162)} L{fmt(sx * 73.5)} {fmt(-108)}")))
    body = [
        (-30, -197),
        (-13, -200),
        (13, -200),
        (30, -197),
        (edge(-150), -150),
        (62, 0),
        (-62, 0),
        (-edge(-150), -150),
    ]
    out.append(pen.shape(poly_d(body), fill=fill))
    out.append(pen.shape(p("M-13 -200 Q0 -184 13 -200 Z"), fill=LIMESTONE))  # the neck opening
    out.append(pen.shape(rect(-24, -190, 48, 52), fill=TATREEZ_RED))
    out.append(
        f'<g transform="translate(0 -164)">{hz.star_motif(pen, size=4, cell=4.6, colors=(GOLD, LINEN_C, TATREEZ_DEEP))}</g>'
    )
    out.append(
        pen.shape(
            poly_d([(-edge(-128), -128), (edge(-128), -128), (edge(-116), -116), (-edge(-116), -116)]),
            fill=GOLD,
        )
    )  # sash
    y0, y1 = -66, -19
    out.append(
        pen.shape(
            poly_d([(-edge(y0), y0), (edge(y0), y0), (edge(y1), y1), (-edge(y1), y1)]), fill=TATREEZ_RED
        )
    )
    for k in range(4):
        x = -39 + 26 * k
        tree = hz.motif(
            pen, layers=[(hz.shift(hz.cypress(6), 0, 3), GOLD if k % 2 == 0 else "#3F8A5A")], cell=3.6
        )
        out.append(f'<g transform="translate({fmt(x)} -46)">{tree}</g>')
    out.append(
        f'<g transform="translate(0 -96)">{hz.motif(pen, layers=[(hz.diamond(3), TATREEZ_RED), (hz.diamond(1), GOLD)], cell=4.4)}</g>'
    )
    out.append(
        f'<g transform="translate(-61 -19)">{hz.band_of(pen, w=122, h=19, unit="teeth", cell=4.4, fill=TATREEZ_RED, colors=(GOLD,))}</g>'
    )
    return "".join(out)


def poly_d(points: Sequence[Point]) -> str:
    """A closed polygon element (straight sides)."""
    return p("M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in points) + " Z")


LINEN_C = "#FBF3E2"
