"""Parts of «أُلَوِّنُ رَمَضان»: lanterns, the crescent and stars, mosques seen from outside, old-town houses,
the iftar and suhoor tables and their dishes, Eid sweets, gifts and clothes, the prayer rug and the stand of
the Quran (blank pages only), and family figures sitting or seen behind a table.

All parts follow `coloring.ink`'s conventions: local units are millimetres at s = 1, a standing thing has
its origin at the middle of its base (y grows downward), a floating thing (a lantern, a star, a balloon)
at its centre. No writing anywhere: no letters, no words of the takbeer, no text on the Quran's pages.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

from qamra_workbook.coloring.ink import (
    BLUE,
    CREAM,
    EARTH,
    FINE,
    GOLD,
    GRASS,
    GRASS_DEEP,
    GREEN,
    GREY,
    HAIR,
    HAIR_DARK,
    LAVENDER,
    MAIN,
    NAVY,
    ORANGE,
    PINK,
    PURPLE,
    RED,
    SAND,
    SKIN,
    SKY,
    STONE,
    STONE_DEEP,
    TEAL,
    TRUNK,
    WHITE,
    WOOD,
    WOOD_DARK,
    YELLOW,
    Pen,
    Point,
    arch,
    c,
    crescent,
    e,
    fmt,
    p,
    polar,
    poly,
    rect,
    rounded_star,
    scallop,
    seg,
    smooth,
    star_d,
)
from qamra_workbook.coloring.parts.common import face, limb

# A few extra flat colours for this book (CMYK-safe mid tones).
DATE = "#9A5B34"
DATE_DARK = "#7A4328"
BRASS = "#E2B04A"
COPPER = "#D98A4E"
WATER = "#CDEBF7"
SOUP = "#F0A54A"
LENTIL = "#E8A23F"
PASTRY = "#F2C77E"
PASTRY_DEEP = "#E3A95B"
CHEESE = "#FFF1C9"
ROSE = "#E57A93"
MINT = "#9AD3BC"
WALL = "#FBE9CF"
WALL_COOL = "#E7E3F4"
FLOOR = "#E6C79A"
CLOTH = "#F7D5D9"
RUG = "#C8504A"
RUG_DEEP = "#8E3B4E"
DUSK = "#F7B27A"
SUNSET = "#F79A4A"
GLOW = "#FFE69A"

Who = Literal["girl", "boy", "mom", "dad", "grandma", "grandpa"]


def _d(path_element: str) -> str:
    """The `d` text of a `<path d="…"/>` element (to extend a smooth outline into a closed area)."""
    return path_element.removeprefix('<path d="').removesuffix('"/>')


# ---- sky: the crescent and the stars ---------------------------------------------------------------------


def moon(pen: Pen, r: float = 20.0, turn: float = 0.0, fill: str = YELLOW) -> str:
    """The crescent moon centred on its origin (horns to the right at turn 0)."""
    return pen.shape(crescent(0, 0, r, 0.55, turn), fill=fill)


def twinkle(pen: Pen, r: float = 8.0, fill: str = YELLOW, points: int = 5) -> str:
    """A soft rounded star centred on its origin."""
    return pen.shape(rounded_star(0, 0, r, r * 0.5, points), fill=fill)


def star8(pen: Pen, r: float = 12.0, fill: str = GOLD, inner: float = 0.72, hole: bool = True) -> str:
    """The eight-pointed star of Islamic geometry (two crossed squares), with a round middle to colour."""
    out = pen.shape(p(star_d(0, 0, r, r * inner, 8, -90)), fill=fill)
    if hole and r >= 14:
        out += pen.shape(c(0, 0, r * 0.38), fill=WHITE)
    return out


# ---- lanterns ----------------------------------------------------------------------------------------------

Lantern = Literal["classic", "round", "tall"]


def fanous(
    pen: Pen,
    kind: Lantern = "classic",
    *,
    glass: str = YELLOW,
    metal: str = BRASS,
    cap: str = RED,
    detail: bool = True,
    glow: bool = True,
    ornate: bool = False,
) -> str:
    """A Ramadan lantern about 100 mm tall centred on its origin; its hanging ring's top is at y = -54.

    `detail` adds the windows and the bands' patterns (for lanterns drawn large), `glow` a soft halo in
    the colour version."""
    out: list[str] = []
    small = pen.scale < 0.42  # printed under ~42 mm tall: only the big shapes
    detail = detail and not small
    if glow:
        out.append(pen.tint(c(0, 2, 46), fill=GLOW))
    if not small:
        out.append(pen.shape(c(0, -49, 4.6), fill=metal))  # the ring
    if kind == "classic":
        if not small:
            out.append(pen.shape(p("M-4.5 -36 Q-3 -41 0 -44 Q3 -41 4.5 -36 Z"), fill=metal))  # the spire
        out.append(pen.shape(p("M-12 -26 C-12 -33 -6 -37 0 -37 C6 -37 12 -33 12 -26 Z"), fill=cap))  # dome
        out.append(pen.shape(p("M-12 -27 L12 -27 L30 -14 Q0 -10 -30 -14 Z"), fill=metal))  # the hat
        out.append(pen.shape(p("M-22 -13 L22 -13 L18 24 L-18 24 Z"), fill=glass))  # glass body
        out.append(pen.shape(p("M-30 -14 Q0 -10 30 -14 L28 -8 Q0 -5 -28 -8 Z"), fill=cap))  # rim
        if not small:
            out.append(pen.stroke(p("M-8 -6 L-6.5 24"), p("M8 -6 L6.5 24")))
        if detail:
            out.append(pen.shape(arch(-4.5, 18, 9, 20, pointed=True), fill=cap))
            out.append(pen.shape(p("M-17 18 L-17 6 Q-15.5 -1 -12.5 -1 L-12.5 18 Z"), fill=cap))
            out.append(pen.shape(p("M17 18 L17 6 Q15.5 -1 12.5 -1 L12.5 18 Z"), fill=cap))
            out.append(pen.shape(c(-14, -20, 2.6), c(0, -21, 2.6), c(14, -20, 2.6), fill=WHITE))
        out.append(pen.shape(p("M-20 23 L20 23 L13 32 L-13 32 Z"), fill=metal))  # lower band
        out.append(pen.shape(p("M-13 31 L13 31 L3 42 Q0 44 -3 42 Z"), fill=cap))  # the cone
        if not small:
            out.append(pen.shape(c(0, 46, 3.6), fill=metal))  # the knob
        if ornate:  # extra ornament for a lantern drawn big (a close-up)
            out.append(
                pen.shape(
                    *[c(x, -5.5 + abs(x) * 0.06, 3.3) for x in (-18, -12, -6, 0, 6, 12, 18)], fill=metal
                )
            )
            out.append(pen.shape(p("M-30 -14 Q0 -10 30 -14 L28 -8 Q0 -5 -28 -8 Z"), fill=cap))
            out.append(pen.shape(p(star_d(0, 7, 3.4, 2.0, 8, -90)), fill=YELLOW))
            out.append(pen.stroke(p("M-12 27.5 L-8 25 L-4 27.5 L0 25 L4 27.5 L8 25 L12 27.5")))
            out.append(pen.shape(crescent(0, -31.5, 3.4, 0.5, -90), fill=metal))
    elif kind == "round":
        if not small:
            out.append(pen.shape(p("M-4 -36 Q-2.5 -41 0 -44 Q2.5 -41 4 -36 Z"), fill=metal))
        out.append(pen.shape(p("M-14 -24 C-14 -32 -7 -37 0 -37 C7 -37 14 -32 14 -24 Z"), fill=cap))
        out.append(pen.shape(rect(-17, -26, 34, 7, 3), fill=metal))
        out.append(pen.shape(c(0, 4, 25), fill=glass))  # the globe
        out.append(pen.stroke(p("M-10 -18 Q-17 4 -10 26"), p("M10 -18 Q17 4 10 26")))
        if detail:
            out.append(pen.shape(p(star_d(0, 4, 8, 5.2, 8, -90)), fill=cap))
            out.append(pen.shape(e(-17.5, 4, 3, 5.5), e(17.5, 4, 3, 5.5), fill=cap))
        out.append(pen.shape(rect(-15, 24, 30, 7, 3), fill=metal))
        out.append(pen.shape(p("M-11 31 L11 31 L3 41 Q0 43 -3 41 Z"), fill=cap))
        if not small:
            out.append(pen.shape(c(0, 45, 3.6), fill=metal))
    else:  # tall: a slim lantern with a pointed onion dome and arched windows
        if not small:
            out.append(pen.shape(p("M-3.5 -38 Q-2 -42 0 -45 Q2 -42 3.5 -38 Z"), fill=metal))
        out.append(pen.shape(p("M-14 -24 C-18 -30 -6 -33 0 -40 C6 -33 18 -30 14 -24 Z"), fill=cap))
        out.append(pen.shape(rect(-17, -25, 34, 6, 2.5), fill=metal))
        out.append(pen.shape(p("M-15 -19 L15 -19 L15 26 L-15 26 Z"), fill=glass))
        out.append(pen.stroke(p("M-5.5 -19 L-5.5 26"), p("M5.5 -19 L5.5 26")))
        if detail:
            out.append(pen.shape(arch(-3.2, 20, 6.4, 30, pointed=True), fill=cap))
            out.append(pen.shape(p("M-12.5 20 L-12.5 -4 Q-11 -10 -8.5 -12 L-8.5 20 Z"), fill=cap))
            out.append(pen.shape(p("M12.5 20 L12.5 -4 Q11 -10 8.5 -12 L8.5 20 Z"), fill=cap))
        out.append(pen.shape(rect(-18, 25, 36, 7, 2.5), fill=metal))
        out.append(pen.shape(p("M-12 32 L12 32 L4 41 Q0 43 -4 41 Z"), fill=cap))
        if not small:
            out.append(pen.shape(c(0, 45, 3.6), fill=metal))
    return "".join(out)


def hanging(pen: Pen, length: float, part_top: float = -54.0) -> str:
    """The cord a lantern hangs from: from the origin straight down `length` (draw before the lantern)."""
    return pen.stroke(seg(0, 0, 0, length), weight=FINE)


def _bezier(a: Point, ctrl: Point, b: Point, t: float) -> Point:
    u = 1 - t
    return (
        u * u * a[0] + 2 * u * t * ctrl[0] + t * t * b[0],
        u * u * a[1] + 2 * u * t * ctrl[1] + t * t * b[1],
    )


def garland_points(a: Point, b: Point, sag: float, n: int) -> list[Point]:
    """`n` evenly spread points along a cord hung from a to b that sags by `sag` (ends excluded)."""
    ctrl = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 2 * sag)
    return [_bezier(a, ctrl, b, (i + 1) / (n + 1)) for i in range(n)]


def cord(pen: Pen, a: Point, b: Point, sag: float) -> str:
    ctrl = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 2 * sag)
    return pen.stroke(
        p(f"M{fmt(a[0])} {fmt(a[1])} Q{fmt(ctrl[0])} {fmt(ctrl[1])} {fmt(b[0])} {fmt(b[1])}"), weight=FINE
    )


FLAG_FILLS = (RED, YELLOW, TEAL, PURPLE, ORANGE, GREEN, PINK, BLUE)


def bunting(
    pen: Pen, a: Point, b: Point, sag: float, n: int, *, size: float = 14.0, fills: Sequence[str] = FLAG_FILLS
) -> str:
    """A cord of triangular flags from a to b (in the caller's units)."""
    out = [cord(pen, a, b, sag)]
    pts = garland_points(a, b, sag, n)
    for i, (x, y) in enumerate(pts):
        w = size * 0.5
        out.append(
            pen.shape(
                p(f"M{fmt(x - w)} {fmt(y - 1)} L{fmt(x + w)} {fmt(y - 1)} L{fmt(x)} {fmt(y + size * 1.1)} Z"),
                fill=fills[i % len(fills)],
            )
        )
    return "".join(out)


# ---- buildings ---------------------------------------------------------------------------------------------


def onion_d(x: float, base: float, w: float, h: float) -> str:
    """An onion dome standing on (x, base): `w` wide at its belly, `h` tall to its point."""
    r = w / 2

    def side(k: int) -> str:
        return (
            f"C{fmt(x + k * r * 1.12)} {fmt(base - h * 0.12)} {fmt(x + k * r * 1.12)} {fmt(base - h * 0.52)} "
            f"{fmt(x + k * r * 0.55)} {fmt(base - h * 0.72)} "
            f"C{fmt(x + k * r * 0.22)} {fmt(base - h * 0.84)} {fmt(x + k * r * 0.06)} {fmt(base - h * 0.9)} "
            f"{fmt(x)} {fmt(base - h)}"
        )

    left = side(-1)
    # the right side runs back from the tip to the base
    right = (
        f"C{fmt(x + r * 0.06)} {fmt(base - h * 0.9)} {fmt(x + r * 0.22)} {fmt(base - h * 0.84)} "
        f"{fmt(x + r * 0.55)} {fmt(base - h * 0.72)} "
        f"C{fmt(x + r * 1.12)} {fmt(base - h * 0.52)} {fmt(x + r * 1.12)} {fmt(base - h * 0.12)} "
        f"{fmt(x + r * 0.8)} {fmt(base)}"
    )
    return f"M{fmt(x - r * 0.8)} {fmt(base)} {left} {right} Z"


def finial(pen: Pen, x: float, top: float, size: float = 1.0, fill: str = GOLD) -> str:
    """A rod with a ball and a small crescent, standing on (x, top)."""
    return pen.stroke(seg(x, top, x, top - 6 * size), weight=FINE) + pen.shape(
        c(x, top - 8 * size, 3 * size), crescent(x, top - 17 * size, 6.5 * size, 0.45, -90), fill=fill
    )


def minaret(
    pen: Pen, h: float = 140.0, w: float = 16.0, *, fill: str = STONE, cap: str = TEAL, balconies: int = 2
) -> str:
    """A slim minaret standing on the origin: a shaft, balconies with railings, a pointed cap and a finial."""
    out: list[str] = []
    top = -h + 26
    out.append(pen.shape(rect(-w / 2, top, w, h - 26 + 1), fill=fill))
    shaft_top = top
    for i in range(balconies):
        y = -h * (0.42 + 0.26 * i)
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-w / 2)} {fmt(y + 7)} L{fmt(w / 2)} {fmt(y + 7)} "
                    f"L{fmt(w / 2 + 5)} {fmt(y)} L{fmt(-w / 2 - 5)} {fmt(y)} Z"
                ),
                fill=cap,
            )
        )
        out.append(pen.shape(rect(-w / 2 - 5, y - 7, w + 10, 7, 1.5), fill=fill))
    out.append(pen.shape(arch(-w * 0.22, -h * 0.2, w * 0.44, w * 1.1), fill=SKY))
    cone = f"M{fmt(-w / 2 - 2)} {fmt(shaft_top)} L{fmt(w / 2 + 2)} {fmt(shaft_top)} L0 {fmt(-h)} Z"
    out.append(pen.shape(p(cone), fill=cap))
    out.append(pen.shape(rect(-w / 2 - 3, shaft_top - 1, w + 6, 6, 2), fill=GOLD))
    out.append(finial(pen, 0, -h, 0.8))
    return "".join(out)


def mosque(
    pen: Pen,
    *,
    wall: str = STONE,
    dome: str = TEAL,
    door: str = WOOD,
    window: str = SKY,
    minarets: int = 2,
) -> str:
    """A mosque seen from outside, about 160 mm wide and 150 mm tall, standing on the origin: a big dome on a
    drum, two small domes on the wings, arched door and windows and (1 or 2) minarets."""
    out: list[str] = []
    if minarets:
        out.append(_at(minaret(pen, 150, 15, fill=wall, cap=dome), 68, 0))
        if minarets > 1:
            out.append(_at(minaret(pen, 150, 15, fill=wall, cap=dome), -68, 0))
    # wings with small domes
    for sx in (-1, 1):
        x0 = 30 if sx > 0 else -58
        out.append(pen.shape(p(onion_d(sx * 44, -38, 22, 22)), fill=dome))
        out.append(pen.shape(rect(x0, -40, 28, 40), fill=wall))
        out.append(pen.shape(arch(sx * 44 - 6, -9, 12, 22), fill=window))
    # the drum and the big dome
    out.append(pen.shape(p(onion_d(0, -78, 62, 58)), fill=dome))
    out.append(finial(pen, 0, -136))
    out.append(pen.shape(rect(-30, -84, 60, 10, 2), fill=GOLD))
    out.append(pen.shape(rect(-32, -76, 64, 76), fill=wall))
    # crenellations along the main wall's top
    out.append(pen.shape(*[rect(-30 + 12 * i, -82, 8, 6, 1.5) for i in range(5)], fill=wall))
    out.append(pen.shape(arch(-12, 0, 24, 44, pointed=True), fill=door))
    out.append(pen.stroke(seg(0, -38, 0, 0)))
    out.append(
        pen.shape(arch(-26, -40, 10, 22, pointed=True), arch(16, -40, 10, 22, pointed=True), fill=window)
    )
    out.append(pen.shape(c(0, -60, 7), fill=window))
    return "".join(out)


def _at(markup: str, x: float, y: float) -> str:
    return f'<g transform="translate({fmt(x)} {fmt(y)})">{markup}</g>'


def house(
    pen: Pen,
    w: float = 60.0,
    h: float = 70.0,
    *,
    fill: str = STONE,
    door: bool = True,
    windows: int = 2,
    dome: bool = False,
    window_fill: str = SKY,
    door_fill: str = WOOD,
    lit: bool = False,
    rows: int = 1,
) -> str:
    """An old-town stone house standing on the origin: flat roof with a parapet, arched windows with
    shutters' lines (`rows` floors of them), an arched door; optionally a small roof dome. `lit` paints the
    windows warm (night)."""
    out: list[str] = []
    wf = GLOW if lit else window_fill
    if dome:
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-w * 0.22)} {fmt(-h)} A{fmt(w * 0.22)} {fmt(w * 0.2)} 0 0 1 "
                    f"{fmt(w * 0.22)} {fmt(-h)} Z"
                ),
                fill=fill,
            )
        )
    out.append(pen.shape(rect(-w / 2, -h, w, h + 1), fill=fill))
    out.append(pen.shape(rect(-w / 2 - 2, -h - 4, w + 4, 6, 1.5), fill=STONE_DEEP))
    if door:
        dw = min(18.0, w * 0.3)
        out.append(pen.shape(arch(-dw / 2, 0, dw, dw * 1.7), fill=door_fill))
        out.append(pen.solid(c(dw * 0.25, -dw * 0.7, 1.3)))
    ww = min(14.0, w * 0.22)
    for row in range(rows if windows else 0):
        row_y = -h + 10 + row * (ww * 1.5 + 14)
        xs = [0.0] if windows == 1 else [-w * 0.27, w * 0.27]
        for x in xs:
            out.append(pen.shape(arch(x - ww / 2, row_y + ww * 1.5, ww, ww * 1.5), fill=wf))
            out.append(pen.stroke(seg(x, row_y + 3, x, row_y + ww * 1.5)))
            out.append(pen.shape(rect(x - ww / 2 - 2, row_y + ww * 1.5, ww + 4, 3.5, 1), fill=STONE_DEEP))
    return "".join(out)


def frond_d(x: float, y: float, tip: Point, ctrl: Point, width: float) -> str:
    """A palm frond from (x, y): a long leaf whose centre line arcs through `ctrl` to `tip` (relative)."""
    a, k, b = (x, y), (x + ctrl[0], y + ctrl[1]), (x + tip[0], y + tip[1])
    side_a: list[Point] = []
    side_b: list[Point] = []
    n = 8
    for i in range(n + 1):
        t = i / n
        cx, cy = _bezier(a, k, b, t)
        tx = 2 * (1 - t) * (k[0] - a[0]) + 2 * t * (b[0] - k[0])
        ty = 2 * (1 - t) * (k[1] - a[1]) + 2 * t * (b[1] - k[1])
        ln = math.hypot(tx, ty) or 1.0
        half = width / 2 * (math.sin(math.pi * t) ** 0.7) + (1.5 if i == 0 else 0.0)
        nx, ny = -ty / ln, tx / ln
        side_a.append((cx + nx * half, cy + ny * half))
        side_b.append((cx - nx * half, cy - ny * half))
    return _d(smooth([*side_a[:-1], side_a[-1], *side_b[::-1][1:]], tension=0.7))


def palm(pen: Pen, h: float = 120.0, *, lean: float = 6.0, dates: bool = True) -> str:
    """A date palm standing on the origin: a gently curved trunk with rings and a crown of fronds."""
    out: list[str] = []
    top = (lean, -h)
    tw = 8.0
    trunk = (
        f"M{fmt(-tw)} 0 C{fmt(-tw * 0.6)} {fmt(-h * 0.45)} {fmt(lean - tw * 0.5)} {fmt(-h * 0.75)} "
        f"{fmt(lean - tw * 0.45)} {fmt(-h)} L{fmt(lean + tw * 0.45)} {fmt(-h)} "
        f"C{fmt(lean + tw * 0.5)} {fmt(-h * 0.75)} {fmt(tw * 0.6)} {fmt(-h * 0.45)} {fmt(tw)} 0 Z"
    )
    out.append(pen.shape(p(trunk), fill=TRUNK))
    rings = []
    for i in range(1, 9):
        t = i / 9
        y = -h * t
        x = lean * t**1.5
        half = tw * (1 - t * 0.5)
        rings.append(
            p(f"M{fmt(x - half + 1)} {fmt(y + 2)} Q{fmt(x)} {fmt(y - 1.5)} {fmt(x + half - 1)} {fmt(y + 2)}")
        )
    out.append(pen.stroke(*rings))
    shapes = (
        ((16, -42), (4, -36)),
        ((-16, -42), (-4, -36)),
        ((48, -6), (24, -32)),
        ((-48, -6), (-24, -32)),
        ((54, 24), (32, -20)),
        ((-54, 24), (-32, -20)),
        ((34, 42), (30, 4)),
        ((-34, 42), (-30, 4)),
    )
    fronds = [p(frond_d(top[0], top[1], tp, ct, 15)) for tp, ct in shapes]
    out.append(pen.shape(*fronds, fill=GRASS_DEEP))
    if dates:
        bunch = [(-7, 7), (7, 7), (0, 9), (-4, 14), (4, 14)]
        out.append(pen.shape(*[c(top[0] + dx, top[1] + dy, 3.6) for dx, dy in bunch], fill=DATE))
    return "".join(out)


# ---- the table: dishes, dates and water ------------------------------------------------------------------


def band_d(points: Sequence[Point], width: float) -> str:
    """A closed band of even `width` along a smooth line through `points` (handles, ribbons, ropes)."""
    side_a: list[Point] = []
    side_b: list[Point] = []
    n = len(points)
    for i, (x, y) in enumerate(points):
        x0, y0 = points[max(i - 1, 0)]
        x1, y1 = points[min(i + 1, n - 1)]
        ln = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / ln * width / 2, (x1 - x0) / ln * width / 2
        side_a.append((x + nx, y + ny))
        side_b.append((x - nx, y - ny))
    return _d(smooth(side_a + side_b[::-1], tension=0.7))


def date_fruit(x: float, y: float, angle: float, size: float = 1.0) -> str:
    """A date's outline: a long oval, a little narrower at its stalk end."""
    pts = [
        (-9.4, 0.0),
        (-6.0, -4.4),
        (0.5, -5.3),
        (6.5, -4.3),
        (9.6, 0.0),
        (6.5, 4.3),
        (0.5, 5.3),
        (-6.0, 4.4),
    ]
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    return smooth([(x + (px * ca - py * sa) * size, y + (px * sa + py * ca) * size) for px, py in pts])


def dates(pen: Pen, spots: Sequence[tuple[float, float, float]], size: float = 1.0, fill: str = DATE) -> str:
    """Dates at (x, y, angle) spots, back to front, each with the soft crease of its skin."""
    out = []
    for x, y, angle in spots:
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        x1, y1 = x + (-4.5 * ca + 1.2 * sa) * size, y + (-4.5 * sa - 1.2 * ca) * size
        x2, y2 = x + (4.5 * ca + 1.2 * sa) * size, y + (4.5 * sa - 1.2 * ca) * size
        out.append(pen.shape(date_fruit(x, y, angle, size), fill=fill))
        out.append(pen.stroke(seg(x1, y1, x2, y2)))
    return "".join(out)


Food = Literal["soup", "salad", "dates", "lentils", "hummus", "olives", "nuts", "none"]


def bowl(pen: Pen, w: float = 44.0, *, fill: str = BLUE, food: Food = "none", band: bool = True) -> str:
    """A round bowl seen from the front, standing on the origin, with its food."""
    h = w * 0.42
    ry = w * 0.12
    out: list[str] = []
    out.append(pen.shape(e(0, -h, w / 2, ry), fill=fill))  # the back of the rim
    if food in ("soup", "lentils", "hummus"):
        tone = {"soup": SOUP, "lentils": LENTIL, "hummus": CREAM}[food]
        out.append(pen.shape(e(0, -h + 0.5, w / 2 - 3, ry - 1.8), fill=tone))
        if food == "soup":
            out.append(
                pen.stroke(
                    p(f"M{fmt(-w * 0.18)} {fmt(-h - 8)} q-4 -6 0 -12 q4 -6 0 -12"),
                    p(f"M{fmt(w * 0.14)} {fmt(-h - 8)} q-4 -6 0 -12 q4 -6 0 -12"),
                )
            )
    elif food == "salad":
        out.append(pen.shape(scallop(0, -h - 4, w / 2 - 2, 9, 7, 0.7, -180), fill=GRASS))
        out.append(pen.shape(c(-w * 0.2, -h - 4, 5), c(w * 0.16, -h - 6, 5), fill=RED))
        out.append(pen.shape(e(0, -h - 2, 6, 3.5), fill=GREEN))
    elif food in ("dates", "olives", "nuts"):
        k = w / 44
        if food == "dates":
            spots = (
                (-14, 0, -20),
                (-5, 1, 10),
                (5, 1, -10),
                (14, 0, 25),
                (-9, -6, 30),
                (1, -7, -15),
                (10, -6, 15),
                (-4, -12, -30),
                (5, -12, 20),
                (0, -17, 75),
            )
            out.append(dates(pen, [(x * k, -h + y * k, a) for x, y, a in spots], k * 0.62))
        else:
            tone = "#6E7B3A" if food == "olives" else PASTRY_DEEP
            spots2 = ((-12, -1), (0, -2), (12, -1), (-6, -8), (6, -8), (0, -14))
            out.append(pen.shape(*[e(x * k, -h + y * k, 5.2 * k, 4.4 * k) for x, y in spots2], fill=tone))
    body = (
        f"M{fmt(-w / 2)} {fmt(-h)} A{fmt(w / 2)} {fmt(ry)} 0 0 0 {fmt(w / 2)} {fmt(-h)} "
        f"C{fmt(w / 2)} {fmt(-h * 0.35)} {fmt(w * 0.3)} -2 {fmt(w * 0.17)} -2 "
        f"L{fmt(-w * 0.17)} -2 C{fmt(-w * 0.3)} -2 {fmt(-w / 2)} {fmt(-h * 0.35)} {fmt(-w / 2)} {fmt(-h)} Z"
    )
    out.append(pen.shape(p(body), fill=fill))
    out.append(pen.shape(rect(-w * 0.17, -3, w * 0.34, 3.5, 1.2), fill=fill))
    if band and w >= 36:
        band_line = f"M{fmt(-w * 0.45)} {fmt(-h * 0.62)} Q0 {fmt(-h * 0.25)} {fmt(w * 0.45)} {fmt(-h * 0.62)}"
        out.append(pen.stroke(p(band_line)))
    return "".join(out)


def plate(pen: Pen, w: float = 56.0, *, fill: str = WHITE) -> str:
    """A flat plate seen from the front (an ellipse with its well), standing on the origin."""
    ry = w * 0.15
    return pen.shape(e(0, -ry, w / 2, ry), fill=fill) + pen.stroke(e(0, -ry + 0.6, w / 2 - 6, ry - 3.5))


def sambousek(x: float, y: float, size: float = 1.0, flip: bool = False) -> str:
    """A fried triangle pastry seen from the front, standing on (x, y)."""
    k = -1 if flip else 1
    s = size
    return p(
        f"M{fmt(x - k * 12 * s)} {fmt(y)} L{fmt(x + k * 1 * s)} {fmt(y - 16 * s)} "
        f"Q{fmt(x + k * 3 * s)} {fmt(y - 18 * s)} {fmt(x + k * 5 * s)} {fmt(y - 15 * s)} "
        f"L{fmt(x + k * 12 * s)} {fmt(y)} Q{fmt(x)} {fmt(y + 2.5 * s)} {fmt(x - k * 12 * s)} {fmt(y)} Z"
    )


def qatayef(x: float, y: float, size: float = 1.0) -> str:
    """A folded qatayef (a half-moon pancake) lying on (x, y), seen from the side."""
    s = size
    return p(
        f"M{fmt(x - 13 * s)} {fmt(y)} A{fmt(13 * s)} {fmt(12 * s)} 0 0 1 {fmt(x + 13 * s)} {fmt(y)} "
        f"Q{fmt(x)} {fmt(y + 3 * s)} {fmt(x - 13 * s)} {fmt(y)} Z"
    )


def qatayef_piece(pen: Pen, x: float, y: float, size: float = 1.0, fill: str = PASTRY) -> str:
    """A folded qatayef with the pinched seam along its round edge."""
    s = size
    y0 = fmt(y - 1.5 * s)
    seam = f"M{fmt(x - 9 * s)} {y0} A{fmt(9 * s)} {fmt(8 * s)} 0 0 1 {fmt(x + 9 * s)} {y0}"
    return pen.shape(qatayef(x, y, s), fill=fill) + pen.stroke(p(seam))


def food_plate(pen: Pen, food: str = "sambousek", w: float = 60.0, *, fill: str = WHITE) -> str:
    """A plate with sambousek, qatayef, bread, cheese or eggs on it, standing on the origin."""
    out = [plate(pen, w, fill=fill)]
    base = -w * 0.15
    if food == "sambousek":
        out.append(pen.shape(sambousek(-11, base - 1), sambousek(11, base - 1, flip=True), fill=PASTRY_DEEP))
        out.append(pen.shape(sambousek(0, base + 3, 1.1), fill=PASTRY))
    elif food == "qatayef":
        out.append(
            qatayef_piece(pen, -11, base - 1, 1.0, PASTRY_DEEP)
            + qatayef_piece(pen, 11, base - 1, 1.0, PASTRY_DEEP)
        )
        out.append(qatayef_piece(pen, 0, base + 3, 1.15))
    elif food == "bread":
        out.append(pen.shape(e(-6, base - 5, 18, 7), fill=PASTRY_DEEP))
        out.append(pen.shape(e(5, base - 1, 19, 7), fill=PASTRY))
    elif food == "cheese":
        out.append(
            pen.shape(
                p(f"M-21 {fmt(base)} L-17 {fmt(base - 13)} L1 {fmt(base - 13)} L-3 {fmt(base)} Z"),
                p(f"M1 {fmt(base + 1)} L4 {fmt(base - 10)} L20 {fmt(base - 10)} L18 {fmt(base + 1)} Z"),
                fill=CHEESE,
            )
        )
    elif food == "eggs":
        out.append(pen.shape(e(-9, base - 2, 9, 6), e(9, base - 1, 9, 6), fill=WHITE))
        out.append(pen.shape(c(-9, base - 3, 4.4), c(9, base - 2, 4.4), fill=YELLOW))
    return "".join(out)


def jug(pen: Pen, *, fill: str = WATER, metal: bool = False) -> str:
    """A water jug (a pitcher with a spout and a handle) about 70 mm tall, standing on the origin."""
    out: list[str] = []
    handle = band_d([(-13, -52), (-27, -50), (-30, -34), (-22, -20), (-16, -16)], 6)
    out.append(pen.shape(p(handle), fill=COPPER if metal else fill))
    tone = COPPER if metal else fill
    body = (
        "M-14 -1 C-26 -12 -27 -34 -15 -46 C-12 -50 -11 -55 -11 -60 L11 -60 C11 -55 12 -50 15 -46 "
        "C27 -34 26 -12 14 -1 Q0 2 -14 -1 Z"
    )
    out.append(pen.shape(p(body), fill=tone))
    out.append(pen.shape(p("M6 -63 Q16 -64 24 -70 Q22 -60 10 -56 Z"), fill=tone))  # the spout
    out.append(pen.shape(e(0, -61, 12.5, 4), fill=tone))  # the rim
    out.append(pen.stroke(p("M-14 -48 Q0 -44 14 -48"), p("M-21 -22 Q0 -14 21 -22")))
    return "".join(out)


def glass(pen: Pen, h: float = 34.0, *, fill: str = WATER, drink: str | None = None) -> str:
    """A tumbler standing on the origin, filled to two thirds (water, or a coloured `drink`)."""
    w = h * 0.62
    out = [
        pen.shape(
            p(f"M{fmt(-w * 0.4)} 0 L{fmt(-w / 2)} {fmt(-h)} L{fmt(w / 2)} {fmt(-h)} L{fmt(w * 0.4)} 0 Z"),
            fill=WHITE,
        )
    ]
    lvl = -h * 0.66
    lw = w * 0.4 + (w * 0.1) * 0.66
    out.append(
        pen.shape(
            p(
                f"M{fmt(-w * 0.4)} 0 L{fmt(-lw)} {fmt(lvl)} Q0 {fmt(lvl + 2.5)} {fmt(lw)} {fmt(lvl)} "
                f"L{fmt(w * 0.4)} 0 Z"
            ),
            fill=drink or fill,
        )
    )
    return "".join(out)


def teapot(pen: Pen, *, fill: str = TEAL) -> str:
    """A round teapot about 50 mm tall standing on the origin."""
    out: list[str] = []
    out.append(pen.shape(p(band_d([(-20, -32), (-31, -29), (-31, -16), (-21, -12)], 5.5)), fill=fill))
    out.append(pen.shape(p("M18 -16 Q30 -20 34 -36 Q37 -38 38 -35 Q34 -14 18 -8 Z"), fill=fill))
    out.append(pen.shape(p("M-22 -2 C-30 -14 -26 -36 0 -37 C26 -36 30 -14 22 -2 Q0 2 -22 -2 Z"), fill=fill))
    out.append(pen.shape(p("M-12 -36 Q0 -48 12 -36 Z"), fill=fill))
    out.append(pen.shape(c(0, -46, 3.4), fill=GOLD))
    out.append(pen.stroke(p("M-24 -20 Q0 -13 24 -20")))
    return "".join(out)


# ---- people ------------------------------------------------------------------------------------------------

Mood = Literal["smile", "sleepy", "yawn"]


def _eyes_closed(pen: Pen, cx: float, cy: float, r: float) -> str:
    ex = r * 0.36
    return pen.stroke(
        p(f"M{fmt(cx - ex - 2.6)} {fmt(cy)} Q{fmt(cx - ex)} {fmt(cy + 2.4)} {fmt(cx - ex + 2.6)} {fmt(cy)}"),
        p(f"M{fmt(cx + ex - 2.6)} {fmt(cy)} Q{fmt(cx + ex)} {fmt(cy + 2.4)} {fmt(cx + ex + 2.6)} {fmt(cy)}"),
    )


def _mirror(pts: Sequence[Point], cx: float, cy: float, r: float) -> str:
    """A closed outline symmetric about x = cx: `pts` (relative to r, left half from top to bottom) and their
    mirror image."""
    left = [(cx + x * r, cy + y * r) for x, y in pts]
    right = [(cx - x * r, cy + y * r) for x, y in reversed(pts)]
    return smooth(left + right, tension=0.85)


def _beard_d(pts: Sequence[Point], cx: float, cy: float, r: float, mouth: float) -> str:
    """A beard around the chin: `pts` its left edge (relative to r) down to the chin, open at the mouth."""
    left = [(cx + x * r, cy + y * r) for x, y in pts]
    right = [(cx - x * r, cy + y * r) for x, y in reversed(pts[:-1])]
    return smooth([*left, *right, (cx, cy + r * mouth)], tension=0.8)


def _head_cover(pen: Pen, who: Who, cx: float, cy: float, r: float, scarf: str) -> str:
    """A mother's or grandmother's headscarf: frames the face and falls to the shoulders."""
    pts = [(0.0, -1.22), (-1.0, -0.98), (-1.34, -0.2), (-1.32, 0.7), (-1.5, 1.3), (-1.4, 1.85), (-0.6, 2.0)]
    return pen.shape(_mirror(pts, cx, cy, r), fill=scarf if who == "mom" else "#F2EEE6")


def head(
    pen: Pen,
    who: Who,
    cx: float,
    cy: float,
    r: float,
    *,
    hair_color: str | None = None,
    scarf: str = "#E9D9B8",
    mood: Mood = "smile",
    look: float = 0.0,
    glasses: bool = False,
    hair: str | None = None,
    beard: bool = False,
) -> str:
    """A friendly head for `who` (hair, a mother's or grandmother's headscarf, a grandfather's keffiyeh;
    a father's short beard with `beard`)."""
    from qamra_workbook.coloring.parts.common import _hair_front

    out: list[str] = []
    face_r = r
    face_y = cy
    if who in ("mom", "grandma"):
        out.append(_head_cover(pen, who, cx, cy, r, scarf))
        face_r = r * 0.8
        face_y = cy + r * 0.08
        out.append(pen.shape(e(cx, face_y, face_r, face_r * 1.08), fill=SKIN))
        # the scarf's end wrapped across under the chin
        out.append(
            pen.stroke(
                p(
                    f"M{fmt(cx - r * 0.55)} {fmt(cy + r * 1.08)} Q{fmt(cx + r * 0.2)} {fmt(cy + r * 1.3)} "
                    f"{fmt(cx + r * 1.05)} {fmt(cy + r * 1.7)}"
                )
            )
        )
    elif who == "grandpa":
        cloth = [(0.0, -1.2), (-1.0, -0.95), (-1.32, -0.1), (-1.5, 1.0), (-1.3, 1.75), (-0.8, 1.9)]
        out.append(pen.shape(_mirror(cloth, cx, cy, r), fill=WHITE))
        out.append(pen.shape(c(cx, cy, r), fill=SKIN))
        whiskers = [(-0.88, 0.15), (-0.85, 0.85), (-0.45, 1.3), (0.0, 1.4)]
        out.append(pen.shape(_beard_d(whiskers, cx, cy, r, 0.62), fill="#E4E0D8"))
        out.append(
            pen.shape(
                p(
                    f"M{fmt(cx - r * 1.12)} {fmt(cy - r * 0.2)} C{fmt(cx - r * 1.2)} {fmt(cy - r * 1.5)} "
                    f"{fmt(cx + r * 1.2)} {fmt(cy - r * 1.5)} {fmt(cx + r * 1.12)} {fmt(cy - r * 0.2)} "
                    f"C{fmt(cx + r * 0.8)} {fmt(cy - r * 0.62)} {fmt(cx - r * 0.8)} {fmt(cy - r * 0.62)} "
                    f"{fmt(cx - r * 1.12)} {fmt(cy - r * 0.2)} Z"
                ),
                fill=WHITE,
            )
        )
        out.append(
            pen.shape(
                p(
                    f"M{fmt(cx - r * 1.08)} {fmt(cy - r * 0.78)} C{fmt(cx - r * 0.9)} {fmt(cy - r * 1.12)} "
                    f"{fmt(cx + r * 0.9)} {fmt(cy - r * 1.12)} {fmt(cx + r * 1.08)} {fmt(cy - r * 0.78)} "
                    f"L{fmt(cx + r * 1.1)} {fmt(cy - r * 0.48)} C{fmt(cx + r * 0.9)} {fmt(cy - r * 0.82)} "
                    f"{fmt(cx - r * 0.9)} {fmt(cy - r * 0.82)} {fmt(cx - r * 1.1)} {fmt(cy - r * 0.48)} Z"
                ),
                fill=HAIR_DARK,
            )
        )
    else:
        style = hair or {"girl": "pigtails", "boy": "short", "dad": "short"}[who]
        color = hair_color or (HAIR_DARK if who == "dad" else HAIR)
        if style == "ponytail":
            tail = [
                (cx + r * 0.6, cy - r * 0.7),
                (cx + r * 1.55, cy - r * 0.35),
                (cx + r * 1.6, cy + r * 0.6),
                (cx + r * 1.15, cy + r * 1.3),
                (cx + r * 1.0, cy + r * 0.3),
            ]
            out.append(pen.shape(smooth(tail, tension=0.8), fill=color))
        if style == "bob":
            bob = [(0.0, -1.2), (-1.0, -0.85), (-1.22, 0.1), (-1.15, 0.85), (-0.8, 0.95)]
            out.append(pen.shape(_mirror(bob, cx, cy, r), fill=color))
        out.append(pen.shape(c(cx, cy, r), fill=SKIN))
        out.append(f'<g transform="translate({fmt(cx)} 0)">{_hair_front(pen, style, cy, r, color)}</g>')
        if who == "dad" and beard:
            stubble = [(-0.95, 0.05), (-0.85, 0.8), (-0.45, 1.2), (0.0, 1.28)]
            out.append(pen.shape(_beard_d(stubble, cx, cy, r, 0.6), fill=color))
    adult = who in ("dad", "grandpa")
    eye_y = face_y - face_r * 0.05
    ex = face_r * 0.36
    dx = look * face_r * 0.18
    if mood == "smile":
        if adult:  # the smile sits above the beard
            out.append(pen.solid(e(cx - ex + dx, eye_y - 1, 1.7, 2.1), e(cx + ex + dx, eye_y - 1, 1.7, 2.1)))
            out.append(
                pen.stroke(
                    p(
                        f"M{fmt(cx + dx - 4)} {fmt(cy + r * 0.32)} Q{fmt(cx + dx)} {fmt(cy + r * 0.52)} "
                        f"{fmt(cx + dx + 4)} {fmt(cy + r * 0.32)}"
                    )
                )
            )
            out.append(
                pen.tint(
                    e(cx - r * 0.56, cy + r * 0.18, r * 0.16, r * 0.1),
                    e(cx + r * 0.56, cy + r * 0.18, r * 0.16, r * 0.1),
                    fill="#F08A7E",
                )
            )
        else:
            out.append(
                face(pen, cx, face_y + (1.5 if who not in ("mom", "grandma") else 0.5), face_r, look=look)
            )
    else:
        out.append(_eyes_closed(pen, cx, eye_y, face_r))
        my = face_y + face_r * 0.45
        if mood == "yawn":
            out.append(pen.shape(e(cx, my + 1, face_r * 0.17, face_r * 0.22), fill="#C2504A"))
        else:
            out.append(
                pen.stroke(p(f"M{fmt(cx - 3)} {fmt(my)} Q{fmt(cx)} {fmt(my + 2)} {fmt(cx + 3)} {fmt(my)}"))
            )
    if glasses:
        gx = face_r * 0.36
        out.append(
            pen.stroke(
                c(cx - gx, eye_y - 0.5, 4.8),
                c(cx + gx, eye_y - 0.5, 4.8),
                seg(cx - gx + 4.8, eye_y - 0.5, cx + gx - 4.8, eye_y - 0.5),
            )
        )
    return "".join(out)


KID: dict[str, float] = {"head_r": 14.0, "neck": 17.0, "sh_w": 10.0, "arm": 7.0, "hand": 3.9}
ADULT: dict[str, float] = {"head_r": 15.0, "neck": 20.0, "sh_w": 13.0, "arm": 9.0, "hand": 4.6}


def is_kid(who: Who) -> bool:
    return who in ("girl", "boy")


def _torso_d(sw: float, wide: float, sh_y: float, bottom: float) -> str:
    return (
        f"M{fmt(-sw)} {fmt(sh_y)} C{fmt(-sw * 0.4)} {fmt(sh_y - 3)} {fmt(sw * 0.4)} {fmt(sh_y - 3)} "
        f"{fmt(sw)} {fmt(sh_y)} C{fmt(wide)} {fmt(sh_y + 2)} {fmt(wide + 1)} {fmt(sh_y + 10)} "
        f"{fmt(wide + 1)} {fmt(sh_y + 16)} "
        f"L{fmt(wide + 1)} {fmt(bottom)} L{fmt(-wide - 1)} {fmt(bottom)} L{fmt(-wide - 1)} {fmt(sh_y + 16)} "
        f"C{fmt(-wide - 1)} {fmt(sh_y + 10)} {fmt(-wide)} {fmt(sh_y + 2)} {fmt(-sw)} {fmt(sh_y)} Z"
    )


def _neckline(pen: Pen, who: Who, sh_y: float) -> str:
    if is_kid(who):
        return pen.stroke(p(f"M-5 {fmt(sh_y - 1)} Q0 {fmt(sh_y + 4)} 5 {fmt(sh_y - 1)}"))
    if who in ("dad", "grandpa"):
        return pen.stroke(p(f"M0 {fmt(sh_y + 3)} L0 {fmt(sh_y + 22)}"))
    return ""


def arm(
    pen: Pen, shoulder: Point, hand: Point, width: float, sleeve: str, hand_r: float, bend: float = 1.0
) -> str:
    """An arm from the shoulder to the hand with a soft elbow bulging outward (away from the body's middle),
    and the hand on top."""
    (sx, sy), (hx, hy) = shoulder, hand
    out_dir = 1 if sx >= 0 else -1
    length = math.hypot(hx - sx, hy - sy)
    elbow = ((sx + hx) / 2 + out_dir * length * 0.16 * bend, (sy + hy) / 2 + length * 0.05)
    mid1 = ((sx + elbow[0]) / 2 + out_dir * 0.6, (sy + elbow[1]) / 2)
    mid2 = ((hx + elbow[0]) / 2 + out_dir * 0.6, (hy + elbow[1]) / 2)
    band = band_d([shoulder, mid1, elbow, mid2, hand], width)
    return pen.shape(p(band), fill=sleeve) + pen.shape(c(hx, hy, hand_r), fill=SKIN)


def bust(
    pen: Pen,
    who: Who,
    *,
    top: str = PINK,
    hands: tuple[Point, Point] | None = None,
    depth: float = 8.0,
    mood: Mood = "smile",
    **head_opts: object,
) -> str:
    """Head, shoulders and arms of `who` seen behind a table: the table's top edge is y = 0 (the torso goes
    `depth` below it, under the table drawn next). `hands` are the hands' places (default: on the table)."""
    k = KID if is_kid(who) else ADULT
    sh_y = -32.0 if is_kid(who) else -42.0
    sw = k["sh_w"]
    wide = sw + (7 if is_kid(who) else 9)
    out = [pen.shape(p(_torso_d(sw, wide, sh_y, depth)), fill=top), _neckline(pen, who, sh_y)]
    hs = hands or ((-wide + 7, -3.0), (wide - 7, -3.0))
    for sx, hand in zip((-1, 1), hs, strict=True):
        out.append(arm(pen, (sx * (wide - k["arm"] / 2 + 1), sh_y + 7), hand, k["arm"], top, k["hand"]))
    head_cy = sh_y - k["neck"] + (2 if who in ("mom", "grandma") else 0)
    out.append(head(pen, who, 0, head_cy, k["head_r"], mood=mood, **head_opts))  # type: ignore[arg-type]
    return "".join(out)


def seated(
    pen: Pen,
    who: Who,
    *,
    top: str = NAVY,
    hands: tuple[Point, Point] | None = None,
    shoes: str = WOOD_DARK,
    legs: str | None = None,
    **head_opts: object,
) -> str:
    """`who` sitting on a seat, seen from the front, feet on the floor at the origin. Grown-ups sit on a seat
    46 high in a long robe or thob, children on one 30 high (a girl in a dress, a boy in trousers)."""
    kid = is_kid(who)
    k = KID if kid else ADULT
    seat = 30.0 if kid else 46.0
    sh_y = -seat - (32 if kid else 46)
    sw = k["sh_w"]
    knee = 13.0 if kid else 17.0
    out: list[str] = []
    for sx in (-1, 1):
        x = sx * knee * 0.55
        if kid:
            out.append(
                pen.shape(limb(x, -seat + 2, x, -5, 7.5), fill=legs or (SKIN if who == "girl" else NAVY))
            )
        out.append(
            pen.shape(
                p(f"M{fmt(x - 6)} -0.5 C{fmt(x - 6)} -8 {fmt(x + 6)} -8 {fmt(x + 6 + sx * 3)} -0.5 Z"),
                fill=shoes,
            )
        )
    if not kid:
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-knee - 3)} {fmt(-seat)} L{fmt(knee + 3)} {fmt(-seat)} L{fmt(knee + 1)} -5 "
                    f"Q0 -2 {fmt(-knee - 1)} -5 Z"
                ),
                fill=top,
            )
        )
    elif who == "girl":
        out.append(
            pen.shape(
                p(
                    f"M{fmt(-knee - 2)} {fmt(-seat)} L{fmt(knee + 2)} {fmt(-seat)} L{fmt(knee + 3)} "
                    f"{fmt(-seat + 13)} Q0 {fmt(-seat + 16)} {fmt(-knee - 3)} {fmt(-seat + 13)} Z"
                ),
                fill=top,
            )
        )
    wide = sw + (6 if kid else 8)
    out.append(pen.shape(p(_torso_d(sw, wide, sh_y, -seat)), fill=top))
    out.append(_neckline(pen, who, sh_y))
    lap = NAVY if who == "boy" else top
    kw = knee * 0.55 + 3
    out.append(
        pen.shape(rect(-2 * kw + 1, -seat - 8, 2 * kw, 15, 7), rect(-1, -seat - 8, 2 * kw, 15, 7), fill=lap)
    )
    hs = hands or ((-kw + 1, -seat - 4), (kw - 1, -seat - 4))
    for sx, hand in zip((-1, 1), hs, strict=True):
        out.append(arm(pen, (sx * (wide - k["arm"] / 2 + 1), sh_y + 7), hand, k["arm"], top, k["hand"]))
    head_cy = sh_y - k["neck"] + (2 if who in ("mom", "grandma") else 0)
    out.append(head(pen, who, 0, head_cy, k["head_r"], **head_opts))  # type: ignore[arg-type]
    return "".join(out)


def hands_on(pen: Pen, *pts: Point, r: float = 3.9) -> str:
    """Hands redrawn on top of something a figure holds."""
    return pen.shape(*[c(x, y, r) for x, y in pts], fill=SKIN)


_UNUSED = (CREAM, EARTH, GREY, LAVENDER, MAIN, SAND, poly)


# ---- worship at home: the stand of the Quran, the prayer rug, the prayer beads -----------------------------


def quran_stand(pen: Pen, *, cover: str = GREEN, wood: str = WOOD) -> str:
    """A wooden folding stand (a rehal, its two boards crossed in an X) holding an open book whose pages are
    blank: the Quran is shown, never its text. About 100 mm wide and 100 mm tall, standing on the origin."""
    out: list[str] = []
    for sx in (-1, 1):  # the two boards, each with a round cut-out near its foot
        out.append(pen.shape(poly([(sx * -50, 0), (sx * -34, 0), (sx * 48, -66), (sx * 32, -66)]), fill=wood))
        out.append(pen.shape(c(sx * -27, -12, 3.6), fill=WHITE))
    out.append(pen.shape(c(0, -33.8, 4.2), fill=GOLD))
    # the cover under the pages, then the two pages fanning from the spine
    out.append(pen.shape(p("M0 -54 L-50 -62 L-52 -104 L0 -96 L52 -104 L50 -62 Z"), fill=cover))
    out.append(pen.shape(p("M0 -57 Q-22 -66 -46 -64 L-47 -104 Q-22 -106 0 -97 Z"), fill=WHITE))
    out.append(pen.shape(p("M0 -57 Q22 -66 46 -64 L47 -104 Q22 -106 0 -97 Z"), fill=WHITE))
    out.append(pen.shape(p("M-3 -58 L3 -58 L3 -42 L0 -45 L-3 -42 Z"), fill=RED))  # the ribbon
    return "".join(out)


def closed_book(pen: Pen, *, cover: str = GREEN, trim: str = GOLD) -> str:
    """A closed book lying flat seen from the front-above, its cover decorated with an eight-pointed star in a
    border (no letters). About 80 mm wide, standing on the origin."""
    out = [pen.shape(p("M-40 0 L40 0 L40 -8 L-40 -8 Z"), fill=WHITE)]
    out.append(pen.stroke(seg(-36, -4, 36, -4)))
    out.append(pen.shape(p("M-40 -8 L40 -8 L30 -46 L-30 -46 Z"), fill=cover))
    out.append(pen.stroke(p("M-31 -13 L31 -13 L24 -41 L-24 -41 Z")))
    out.append(pen.shape(p(star_d(0, -27, 11, 8, 8, -90)), fill=trim))
    return "".join(out)


def prayer_rug(pen: Pen, *, fill: str = RUG, border: str = GOLD, field: str = RUG_DEEP) -> str:
    """A prayer rug seen from above, 130 × 190 mm centred on its origin: a fringe at both ends, a border band
    of diamonds, and a pointed arch with a hanging lamp and a big star in the field."""
    out: list[str] = []
    fringe = [seg(x, y0, x, y0 + sy * 9) for x in range(-56, 60, 8) for y0, sy in ((-95, -1), (95, 1))]
    out.append(pen.stroke(*fringe))
    out.append(pen.shape(rect(-65, -95, 130, 190, 3), fill=fill))
    out.append(pen.shape(rect(-52, -82, 104, 164, 2), fill=field))
    diamonds = []
    for x in range(-48, 49, 16):
        for y in (-88.5, 88.5):
            diamonds.append(poly([(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)]))
    for row in range(-72, 73, 16):
        for side in (-58.5, 58.5):
            diamonds.append(poly([(side, row - 5), (side + 5, row), (side, row + 5), (side - 5, row)]))
    out.append(pen.shape(*diamonds, fill=border))
    out.append(pen.shape(arch(-40, 74, 80, 140, pointed=True), fill=fill))
    out.append(pen.stroke(p("M-34 74 L-34 -18 Q-34 -46 0 -60 Q34 -46 34 -18 L34 74")))
    out.append(pen.shape(p(star_d(0, 38, 20, 14, 8, -90)), fill=border))
    out.append(pen.shape(c(0, 38, 7), fill=fill))
    # the hanging lamp under the arch's point
    out.append(pen.stroke(seg(0, -60, 0, -40)))
    out.append(pen.shape(p("M-5 -41 L5 -41 L8 -36 L-8 -36 Z"), fill=border))
    out.append(pen.shape(p("M-8 -36 C-16 -30 -12 -18 0 -17 C12 -18 16 -30 8 -36 Z"), fill=YELLOW))
    out.append(pen.shape(c(0, -14, 3.2), fill=border))
    for sx in (-1, 1):  # stars in the corners above the arch
        out.append(pen.shape(rounded_star(sx * 38, -66, 7, 3.6), fill=YELLOW))
    return "".join(out)


def misbaha(pen: Pen, *, r: float = 36.0, beads: int = 33, fill: str = TEAL, tassel: str = GOLD) -> str:
    """Prayer beads lying in a loose loop centred on its origin, a longer bead and a tassel at the bottom."""
    out: list[str] = []
    bead_r = 3.6
    pts = []
    for i in range(beads):
        a = math.radians(90 + 14 + (360 - 28) * i / (beads - 1))
        pts.append((r * math.cos(a), r * 0.78 * math.sin(a)))
    top = r * 0.78
    # the tassel hangs from the bottom, under the beads
    out.append(
        pen.shape(
            p(
                f"M-4 {fmt(top + 12)} L4 {fmt(top + 12)} L9 {fmt(top + 34)} Q0 {fmt(top + 37)} "
                f"-9 {fmt(top + 34)} Z"
            ),
            fill=tassel,
        )
    )
    out.append(
        pen.stroke(
            seg(-3, top + 18, -5, top + 33), seg(3, top + 18, 5, top + 33), seg(0, top + 18, 0, top + 34)
        )
    )
    out.append(pen.shape(e(0, top + 6, 4.4, 7), fill=fill))
    out.append(pen.shape(*[c(x, y, bead_r) for x, y in pts], fill=fill))
    return "".join(out)


# ---- Eid: clothes, shoes, sweets, gifts and balloons -------------------------------------------------------


def hanger(pen: Pen, *, fill: str = WOOD) -> str:
    """A clothes hanger hanging from the origin (its hook's top); its bar's ends are at (±34, 22)."""
    hook = pen.stroke(p("M-4 2 Q-5 -4 0 -4 Q5 -4 5 2 Q5 6 0 9 L0 12"), weight=MAIN)
    bar = pen.shape(p("M0 10 L36 22 Q38 26 34 26 L-34 26 Q-38 26 -36 22 Z"), fill=fill)
    return hook + bar


def eid_dress(pen: Pen, *, fill: str = PINK, trim: str = YELLOW) -> str:
    """A girl's Eid dress hanging from a hanger at the origin: puff sleeves, a sash with a bow and an
    embroidered hem band of diamonds. About 120 mm long."""
    out = [hanger(pen)]
    out.append(pen.shape(e(-26, 34, 11, 9, -20), e(26, 34, 11, 9, 20), fill=fill))  # sleeves
    out.append(pen.shape(p("M-20 24 Q0 30 20 24 L22 62 L-22 62 Z"), fill=fill))  # bodice
    skirt = "M-22 62 L22 62 Q40 100 52 128 Q0 138 -52 128 Q-40 100 -22 62 Z"
    out.append(pen.shape(p(skirt), fill=fill))
    out.append(pen.shape(p("M-48 118 Q0 128 48 118 L52 128 Q0 138 -52 128 Z"), fill=trim))
    out.append(
        pen.shape(
            *[poly([(x, 118 + 4), (x + 4.5, 126), (x, 130), (x - 4.5, 126)]) for x in (-30, -15, 0, 15, 30)],
            fill=fill,
        )
    )
    out.append(pen.shape(rect(-23, 58, 46, 8, 3), fill=trim))
    out.append(pen.shape(e(-7, 62, 7, 5, -15), e(7, 62, 7, 5, 15), fill=trim))
    out.append(pen.shape(c(0, 62, 3.4), fill=trim))
    out.append(pen.stroke(p("M-8 25 Q0 33 8 25")))
    out.append(pen.stroke(p("M-16 72 Q-24 100 -30 120"), p("M16 72 Q24 100 30 120")))
    return "".join(out)


def eid_shirt(pen: Pen, *, fill: str = BLUE, trousers: str = NAVY) -> str:
    """A boy's Eid shirt (collar, buttons, a pocket) over trousers, hanging from a hanger at the origin. About
    125 mm long."""
    out = [hanger(pen)]
    for sx in (-1, 1):  # trousers' legs below the shirt
        out.append(
            pen.shape(
                p(f"M{fmt(sx * 2)} 70 L{fmt(sx * 22)} 70 L{fmt(sx * 22)} 126 L{fmt(sx * 4)} 126 Z"),
                fill=trousers,
            )
        )
    out.append(
        pen.shape(
            p(
                "M-22 24 L-42 34 L-48 64 L-36 67 L-30 48 L-30 86 L30 86 L30 48 L36 67 L48 64 L42 34 "
                "L22 24 Q0 30 -22 24 Z"
            ),
            fill=fill,
        )
    )
    out.append(pen.shape(p("M-14 22 L0 34 L-4 40 L-16 30 Z"), p("M14 22 L0 34 L4 40 L16 30 Z"), fill=WHITE))
    out.append(pen.stroke(seg(0, 34, 0, 86)))
    out.append(pen.solid(c(4, 46, 1.6), c(4, 58, 1.6), c(4, 70, 1.6)))
    out.append(pen.shape(rect(12, 46, 12, 12, 2), fill=fill))
    return "".join(out)


def shoe(pen: Pen, *, fill: str = RED, kind: Literal["girl", "boy"] = "girl") -> str:
    """A shoe seen from the side, its toe to the right, about 46 mm long, standing on the origin."""
    out: list[str] = []
    if kind == "girl":
        out.append(
            pen.shape(p("M-22 0 L-22 -14 Q-20 -18 -14 -16 Q-2 -12 6 -14 Q22 -16 24 -6 L24 0 Z"), fill=fill)
        )
        out.append(pen.shape(rect(-24, -4, 50, 5, 2), fill=WHITE))
        out.append(pen.shape(p("M-8 -15 Q-4 -24 2 -14 L-2 -13 Q-4 -18 -6 -14 Z"), fill=fill))
        out.append(pen.shape(e(-8, -18, 5, 3.5, -25), e(1, -18, 5, 3.5, 25), fill=YELLOW))
        out.append(pen.shape(c(-3.5, -18, 2.6), fill=YELLOW))
    else:
        out.append(
            pen.shape(p("M-22 0 L-22 -22 Q-16 -26 -8 -22 Q0 -16 12 -14 Q26 -12 26 -4 L26 0 Z"), fill=fill)
        )
        out.append(pen.shape(rect(-24, -5, 52, 6, 2.5), fill=WHITE))
        out.append(pen.stroke(seg(-8, -18, -2, -21), seg(-3, -15, 3, -18), seg(2, -13, 8, -16)))
        out.append(pen.shape(p("M14 -5 Q14 -12 22 -11 Q26 -9 26 -5 Z"), fill=WHITE))
    return "".join(out)


def tray(pen: Pen, r: float = 80.0, *, fill: str = BRASS, inner: str = "#F6D98F") -> str:
    """A round serving tray seen from above, centred on its origin, with a rim and two handles."""
    handles = [
        p(band_d([(sx * (r - 6), -14), (sx * (r + 10), -10), (sx * (r + 10), 10), (sx * (r - 6), 14)], 6))
        for sx in (-1, 1)
    ]
    return (
        pen.shape(*handles, fill=fill)
        + pen.shape(c(0, 0, r), fill=fill)
        + pen.shape(c(0, 0, r - 8), fill=inner)
    )


def kaak(pen: Pen, r: float = 15.0, *, fill: str = PASTRY, hole: str = "#F6D98F") -> str:
    """A ring-shaped Eid ka'ak seen from above, centred on its origin: a wavy pinched edge round a hole."""
    return pen.shape(scallop(0, 0, r * 0.9, r * 0.9, 12, 0.75), fill=fill) + pen.shape(
        c(0, 0, r * 0.4), fill=hole
    )


MaamoulStyle = Literal["star", "flower", "grooves"]


def maamoul(pen: Pen, r: float = 14.0, *, fill: str = PASTRY_DEEP, style: MaamoulStyle = "star") -> str:
    """A ma'amoul seen from above (a round domed sweet pressed in a carved wooden mould), centred on its
    origin: an eight-pointed star, a flower of six petals, or curved grooves."""
    out = [pen.shape(c(0, 0, r), fill=fill)]
    if style == "star":
        out.append(pen.stroke(p(star_d(0, 0, r * 0.72, r * 0.42, 8, -90))))
    elif style == "flower":
        petals = [e(*polar(0, 0, r * 0.45, a), r * 0.36, r * 0.2, a) for a in range(0, 360, 60)]
        out.append(pen.stroke(*petals))
    else:
        out.append(
            pen.stroke(
                *[
                    p(f"M{fmt(-r * 0.62)} {fmt(y)} Q0 {fmt(y - r * 0.3)} {fmt(r * 0.62)} {fmt(y)}")
                    for y in (-r * 0.25, r * 0.15, r * 0.55)
                ]
            )
        )
    return "".join(out)


GiftPattern = Literal["stripes", "dots", "stars", "none"]


def gift(
    pen: Pen,
    w: float = 50.0,
    h: float = 40.0,
    *,
    fill: str = PURPLE,
    ribbon: str = YELLOW,
    pattern: GiftPattern = "none",
    bow: bool = True,
) -> str:
    """A wrapped gift box seen from the front with a lid, a ribbon and a bow, standing on the origin."""
    out: list[str] = []
    lid_h = min(10.0, h * 0.25)
    if bow:
        out.append(pen.shape(e(-8, -h - lid_h - 5, 9, 6, -25), e(8, -h - lid_h - 5, 9, 6, 25), fill=ribbon))
    out.append(pen.shape(rect(-w / 2, -h, w, h), fill=fill))
    if pattern == "stripes":
        out.append(
            pen.stroke(
                *[seg(x, -h + 1, x + 12, -1) for x in (-w / 2 + 2, -w / 2 + 18) if x + 12 < -5],
                *[seg(x, -h + 1, x + 12, -1) for x in (w / 2 - 26, w / 2 - 14) if x > 5],
            )
        )
    elif pattern == "dots":
        out.append(
            pen.shape(*[c(x, y, 3.3) for x in (-w * 0.3, w * 0.3) for y in (-h * 0.3, -h * 0.72)], fill=WHITE)
        )
    elif pattern == "stars":
        out.append(pen.shape(*[rounded_star(x, -h * 0.5, 5, 2.6) for x in (-w * 0.3, w * 0.3)], fill=YELLOW))
    out.append(pen.shape(rect(-5, -h, 10, h), fill=ribbon))
    out.append(pen.shape(rect(-w / 2 - 3, -h - lid_h, w + 6, lid_h, 2), fill=fill))
    out.append(pen.shape(rect(-5, -h - lid_h, 10, lid_h), fill=ribbon))
    if bow:
        out.append(pen.shape(c(0, -h - lid_h - 3, 4), fill=ribbon))
    return "".join(out)


def balloon(pen: Pen, r: float = 16.0, *, fill: str = RED, string: float = 0.0) -> str:
    """A balloon centred on its origin, its knot under it and (with `string`) a wavy string that long."""
    out: list[str] = []
    bottom = r * 1.22
    if string:
        out.append(
            pen.stroke(
                p(
                    f"M0 {fmt(bottom + 4)} q-5 {fmt(string / 4)} 0 {fmt(string / 2)} "
                    f"q5 {fmt(string / 4)} 0 {fmt(string / 2)}"
                )
            )
        )
    out.append(
        pen.shape(p(f"M-3.5 {fmt(bottom + 4)} L3.5 {fmt(bottom + 4)} L0 {fmt(bottom - 1)} Z"), fill=fill)
    )
    out.append(
        pen.shape(
            p(
                f"M0 {fmt(-r * 1.15)} C{fmt(r * 1.35)} {fmt(-r * 1.15)} {fmt(r * 1.1)} {fmt(r * 0.9)} 0 "
                f"{fmt(bottom)} C{fmt(-r * 1.1)} {fmt(r * 0.9)} {fmt(-r * 1.35)} {fmt(-r * 1.15)} 0 "
                f"{fmt(-r * 1.15)} Z"
            ),
            fill=fill,
        )
    )
    out.append(
        pen.stroke(
            p(
                f"M{fmt(-r * 0.55)} {fmt(-r * 0.3)} Q{fmt(-r * 0.5)} {fmt(-r * 0.75)} "
                f"{fmt(-r * 0.15)} {fmt(-r * 0.85)}"
            )
        )
    )
    return "".join(out)


# ---- furniture and outdoor things --------------------------------------------------------------------------


def sofa(pen: Pen, w: float = 150.0, *, fill: str = TEAL, cushion: str = YELLOW) -> str:
    """A family sofa seen from the front, standing on the origin; its seat is 46 high (where `seated`
    grown-ups sit). Draw the people after it."""
    half = w / 2
    out = [pen.shape(rect(-half + 8, -6, 10, 7, 2), rect(half - 18, -6, 10, 7, 2), fill=WOOD_DARK)]
    out.append(
        pen.shape(
            p(
                f"M{fmt(-half + 10)} -46 L{fmt(-half + 10)} -96 Q{fmt(-half + 10)} -106 "
                f"{fmt(-half + 22)} -106 L{fmt(half - 22)} -106 Q{fmt(half - 10)} -106 {fmt(half - 10)} -96 "
                f"L{fmt(half - 10)} -46 Z"
            ),
            fill=fill,
        )
    )
    out.append(pen.stroke(seg(0, -102, 0, -50)))
    out.append(pen.shape(rect(-half + 12, -52, w - 24, 46, 6), fill=fill))
    out.append(pen.stroke(seg(-half + 14, -36, half - 14, -36)))
    for sx in (-1, 1):
        x = sx * (half - 9)
        out.append(pen.shape(rect(x - 11, -72, 22, 68, 8), fill=fill))
    out.append(pen.shape(rect(-half + 22, -92, 26, 24, 7), rect(half - 48, -92, 26, 24, 7), fill=cushion))
    return "".join(out)


def tree(pen: Pen, h: float = 90.0, *, fill: str = GRASS_DEEP) -> str:
    """A round leafy tree standing on the origin."""
    crown_r = h * 0.36
    trunk = p(f"M-6 0 Q-4 {fmt(-h * 0.35)} -5 {fmt(-h * 0.55)} L5 {fmt(-h * 0.55)} Q4 {fmt(-h * 0.35)} 6 0 Z")
    return pen.shape(trunk, fill=TRUNK) + pen.shape(
        scallop(0, -h + crown_r, crown_r, crown_r * 0.92, 9, 0.62), fill=fill
    )


def charity_box(pen: Pen, *, fill: str = GREEN, trim: str = GOLD) -> str:
    """The family's charity box (no writing on it): a box seen a little from above with a coin slot in its
    lid and a heart on its front. About 80 mm wide and 76 mm tall, standing on the origin."""
    out = [pen.shape(p("M34 0 L46 -12 L46 -64 L34 -52 Z"), fill=STONE_DEEP if pen.mode == "color" else fill)]
    out.append(pen.shape(p("M-34 -52 L-22 -64 L46 -64 L34 -52 Z"), fill=fill))
    out.append(pen.shape(rect(-34, -52, 68, 52, 3), fill=fill))
    out.append(pen.stroke(rect(-27, -45, 54, 38, 3)))
    out.append(pen.shape(p("M0 -12 C-26 -26 -16 -44 0 -34 C16 -44 26 -26 0 -12 Z"), fill=RED))
    out.append(pen.shape(p("M-6 -59 L24 -59 L21 -56 L-9 -56 Z"), fill=trim))
    out.append(pen.solid(p("M-3 -58.4 L19 -58.4 L17.5 -56.8 L-4.5 -56.8 Z")))
    return "".join(out)


def coin(pen: Pen, r: float = 6.5, *, fill: str = GOLD) -> str:
    return pen.shape(c(0, 0, r), fill=fill) + pen.stroke(c(0, 0, r * 0.55))


def frame_drum(pen: Pen, r: float = 16.0, *, fill: str = CREAM, rim: str = WOOD) -> str:
    """The musaharati's small drum seen from the front: a wooden rim and a skin, centred on its origin."""
    return pen.shape(c(0, 0, r), fill=rim) + pen.shape(c(0, 0, r - 4.5), fill=fill)


def clock(pen: Pen, r: float = 16.0, *, fill: str = WHITE, rim: str = GOLD) -> str:
    """A wall clock without numbers: a rim, twelve ticks and two hands, centred on its origin."""
    ticks = [seg(*polar(0, 0, r - 7.5, a), *polar(0, 0, r - 5, a)) for a in range(0, 360, 90)]
    return (
        pen.shape(c(0, 0, r), fill=rim)
        + pen.shape(c(0, 0, r - 3.5), fill=fill)
        + pen.stroke(*ticks, seg(0, 0, 0, -(r - 9)), seg(0, 0, r - 10, 3))
        + pen.solid(c(0, 0, 1.6))
    )


def covered_plate(pen: Pen, *, cloth: str = "#F7D5D9", plate_fill: str = WHITE) -> str:
    """A plate of food covered with a cloth tied in a knot on top (a gift to the neighbours), about 56 mm
    wide, standing on the origin."""
    out = [plate(pen, 56, fill=plate_fill)]
    out.append(pen.shape(p("M-25 -6 C-26 -24 -12 -32 0 -32 C12 -32 26 -24 25 -6 Q0 -2 -25 -6 Z"), fill=cloth))
    out.append(pen.shape(e(-6, -36, 7, 4.5, -30), e(6, -36, 7, 4.5, 30), fill=cloth))
    out.append(pen.shape(c(0, -33, 3.6), fill=cloth))
    out.append(pen.stroke(p("M-14 -26 Q-12 -14 -16 -6"), p("M12 -27 Q14 -14 12 -6")))
    return "".join(out)


def griddle(pen: Pen, *, fill: str = GREY) -> str:
    """A flat round pan with three small pancakes cooking (qatayef), about 90 mm wide, standing on the
    origin."""
    out = [pen.shape(p(band_d([(36, -8), (52, -14), (66, -18)], 7)), fill=WOOD_DARK)]
    out.append(pen.shape(p("M-40 -10 Q-40 0 -30 0 L30 0 Q40 0 40 -10 Z"), fill=fill))
    out.append(pen.shape(e(0, -10, 40, 10), fill=fill))
    out.append(pen.shape(e(-18, -10, 11, 4.5), e(4, -12, 11, 4.5), e(20, -8, 10, 4), fill=CREAM))
    return "".join(out)
