"""The coloring books' drawing kit: line art drawn in code, in millimetres at print size.

Every drawing is SVG built from *parts*. A part is a function that draws one thing (an olive tree, a sheep,
a lantern) in its own local units with a `Pen`, and a scene places parts on the page with `place`:

    def sheep(pen: Pen) -> str:          # local units: 1 = 1 mm when placed at s = 1
        return pen.shape(scallop(0, -30, 26, 18, 11), fill=WOOL) + pen.solid(c(-24, -34, 1.6))

    scene = place(pen, sheep, x=60, y=200, s=1.2)       # origin at the part's foot, y grows downward

The pen keeps the *printed* line widths whatever the scale: `pen.shape(...)` strokes at `MAIN` (2.6 mm on
paper), `pen.stroke(...)` at `FINE` (2.0 mm) for open inner lines, so a small sheep and a big sheep print the
same confident line (the owner's quality bar: 2–3 mm outlines for ages 3–6, rounded joins and caps).

The same drawing prints two ways (`Pen.mode`):

- ``line``: the coloring page: every area white, outlines pure black (#000, the press's K channel only);
- ``color``: the cover and the web previews: each area painted in its `fill` (a flat, CMYK-safe colour).

House rules for parts (docs/plans/coloring-books.md):

1. Closed shapes for everything a child colours; nothing smaller than ~6 mm across inside a scene.
2. No text, letters, numbers, flags or sacred text inside drawings; no faces of prophets or religious
   figures; people are simple friendly figures (dots for eyes, a smile).
3. Paint in back-to-front order: a later shape covers what is behind it with its white fill.
4. Origin convention: a standing thing has its origin at the middle of its base (the ground line, y = 0)
   and grows upward (negative y). A floating thing (a cloud, a lantern) has its origin at its centre.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

Mode = Literal["line", "color"]
Point = tuple[float, float]

INK = "#000000"  # pure black: the coloring pages print on the K plate alone
PAPER = "#FFFFFF"
MAIN = 2.6  # mm on paper: outlines of colourable shapes
FINE = 2.0  # mm on paper: open inner lines (folds, veins, mouths)
BOLD = 3.0  # mm on paper: the page frame and the biggest silhouettes

# A flat palette for the colour version (covers, previews). CMYK-safe mid tones.
SKY = "#BFE3F5"
SEA = "#5BA9D6"
SEA_DEEP = "#3E86BE"
CLOUD = "#FFFFFF"
SUN = "#FFCF4A"
GRASS = "#9CCB6B"
GRASS_DEEP = "#6FAE55"
HILL = "#C9DE8E"
HILL_FAR = "#DDE9B4"
EARTH = "#D9B27C"
SAND = "#F2DDAE"
STONE = "#EBDCC0"
STONE_DEEP = "#D8C29A"
WOOD = "#B9824F"
WOOD_DARK = "#8F5E36"
OLIVE_LEAF = "#7FA35A"
OLIVE_FRUIT = "#5E6E3A"
OLIVE_BLACK = "#4A3F4E"
TRUNK = "#9C7650"
RED = "#E5604E"
POPPY = "#E2463A"
PINK = "#F4A6B8"
ORANGE = "#F39A3D"
YELLOW = "#F7C84A"
GOLD = "#F2B33D"
CREAM = "#FFF4DC"
SKIN = "#F3C9A4"
SKIN_DEEP = "#D9A27A"
HAIR = "#5B3A29"
HAIR_DARK = "#2E2A33"
BLUE = "#5E86D6"
NAVY = "#2F3E7A"
TEAL = "#4FA89A"
GREEN = "#4FA36B"
PURPLE = "#9376CF"
LAVENDER = "#C3B5E8"
WHITE = "#FFFFFF"
GREY = "#C9CCD6"
NIGHT = "#2B3770"
NIGHT_SKY = "#3D4B8F"
WOOL = "#FFFFFF"


def fmt(x: float) -> str:
    """A coordinate as short SVG text."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


@dataclass(frozen=True)
class Pen:
    """Draws in a part's local units; `scale` is how many mm one local unit prints at."""

    scale: float = 1.0
    mode: Mode = "line"

    def w(self, mm: float) -> str:
        """A printed width in mm as a width in local units."""
        return fmt(mm / self.scale)

    def paint(self, fill: str) -> str:
        return PAPER if self.mode == "line" else fill

    def shape(self, *elements: str, fill: str = PAPER, weight: float = MAIN) -> str:
        """Closed, colourable shapes: white on the coloring page, `fill` in colour."""
        return (
            f'<g fill="{self.paint(fill)}" stroke="{INK}" stroke-width="{self.w(weight)}" '
            f'stroke-linejoin="round" stroke-linecap="round">{"".join(elements)}</g>'
        )

    def stroke(self, *elements: str, weight: float = FINE) -> str:
        """Open lines (no fill): folds, veins, mouths, grass blades."""
        return (
            f'<g fill="none" stroke="{INK}" stroke-width="{self.w(weight)}" '
            f'stroke-linejoin="round" stroke-linecap="round">{"".join(elements)}</g>'
        )

    def solid(self, *elements: str) -> str:
        """Small solid-black details: eyes, nostrils (keep them few and small)."""
        return f'<g fill="{INK}" stroke="none">{"".join(elements)}</g>'

    def tint(self, *elements: str, fill: str) -> str:
        """Colour only (no outline), only in the colour version: cheeks, a glow. Nothing on the page."""
        if self.mode == "line":
            return ""
        return f'<g fill="{fill}" stroke="none">{"".join(elements)}</g>'

    def at(self, s: float) -> Pen:
        return Pen(self.scale * s, self.mode)


Part = Callable[..., str]


def place(
    pen: Pen,
    part: Part,
    x: float,
    y: float,
    s: float = 1.0,
    *,
    flip: bool = False,
    rotate: float = 0.0,
    **options: Any,
) -> str:
    """`part` drawn at (x, y) in the caller's units, `s` times its natural size, mirrored with `flip`."""
    inner = part(pen.at(s), **options)
    sx = -s if flip else s
    turn = f" rotate({fmt(rotate)})" if rotate else ""
    return f'<g transform="translate({fmt(x)} {fmt(y)}){turn} scale({fmt(sx)} {fmt(s)})">{inner}</g>'


# ---- SVG element helpers (no paint: the pen's group paints them) -------------------------------------------


def c(cx: float, cy: float, r: float) -> str:
    return f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}"/>'


def e(cx: float, cy: float, rx: float, ry: float, rotate: float = 0.0) -> str:
    turn = f' transform="rotate({fmt(rotate)} {fmt(cx)} {fmt(cy)})"' if rotate else ""
    return f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rx)}" ry="{fmt(ry)}"{turn}/>'


def p(d: str) -> str:
    return f'<path d="{d}"/>'


def rect(x: float, y: float, w: float, h: float, rx: float = 0.0) -> str:
    return f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rx)}"/>'


def poly(points: Iterable[Point], closed: bool = True) -> str:
    pts = list(points)
    d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
    return p(d + (" Z" if closed else ""))


def seg(x1: float, y1: float, x2: float, y2: float) -> str:
    return p(f"M{fmt(x1)} {fmt(y1)} L{fmt(x2)} {fmt(y2)}")


def polar(cx: float, cy: float, r: float, deg: float) -> Point:
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def smooth(points: Sequence[Point], closed: bool = True, tension: float = 1.0) -> str:
    """A smooth curve through `points` (Catmull-Rom as cubic Béziers): organic outlines from a few points."""
    pts = list(points)
    n = len(pts)
    if n < 3:
        return poly(pts, closed)
    d = f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"
    last = n if closed else n - 1
    for i in range(last):
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[0]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else pts[-1]
        k = tension / 6
        c1 = (p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k)
        c2 = (p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k)
        d += f" C{fmt(c1[0])} {fmt(c1[1])} {fmt(c2[0])} {fmt(c2[1])} {fmt(p2[0])} {fmt(p2[1])}"
    return p(d + (" Z" if closed else ""))


def scallop_d(
    cx: float, cy: float, rx: float, ry: float, bumps: int, bulge: float = 0.62, start: float = -90
) -> str:
    """Path data of a cloud-like closed outline: `bumps` arcs around an ellipse (fleece, clouds, crowns)."""
    turns = [math.radians(start + 360 * i / bumps) for i in range(bumps)]
    pts = [(cx + math.cos(a) * rx, cy + math.sin(a) * ry) for a in turns]
    d = f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"
    for i in range(bumps):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % bumps]
        radius = math.dist((x1, y1), (x2, y2)) * bulge
        d += f" A{fmt(radius)} {fmt(radius)} 0 0 1 {fmt(x2)} {fmt(y2)}"
    return d + " Z"


def scallop(
    cx: float, cy: float, rx: float, ry: float, bumps: int, bulge: float = 0.62, start: float = -90
) -> str:
    return p(scallop_d(cx, cy, rx, ry, bumps, bulge, start))


def star_d(cx: float, cy: float, outer: float, inner: float, points: int = 5, turn: float = -90) -> str:
    pts = [polar(cx, cy, outer if i % 2 == 0 else inner, turn + 180 * i / points) for i in range(2 * points)]
    return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + " Z"


def star(cx: float, cy: float, outer: float, inner: float | None = None, points: int = 5) -> str:
    return p(star_d(cx, cy, outer, inner if inner is not None else outer * 0.48, points))


def rounded_star(cx: float, cy: float, outer: float, inner: float | None = None, points: int = 5) -> str:
    """A soft star (rounded points) through `smooth`: friendlier for small hands."""
    inner = inner if inner is not None else outer * 0.52
    pts = [polar(cx, cy, outer if i % 2 == 0 else inner, -90 + 180 * i / points) for i in range(2 * points)]
    return smooth(pts, tension=0.55)


def crescent_d(cx: float, cy: float, r: float, cut: float = 0.62, turn: float = 0.0) -> str:
    """A crescent moon (horns to the right at turn 0): an outer circle minus an offset inner circle."""
    a1, a2 = math.radians(turn - 62), math.radians(turn + 62)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
    ri = r * (0.5 + cut * 0.4)
    return (
        f"M{fmt(x1)} {fmt(y1)} A{fmt(r)} {fmt(r)} 0 1 0 {fmt(x2)} {fmt(y2)} "
        f"A{fmt(ri)} {fmt(ri)} 0 1 1 {fmt(x1)} {fmt(y1)} Z"
    )


def crescent(cx: float, cy: float, r: float, cut: float = 0.62, turn: float = 0.0) -> str:
    return p(crescent_d(cx, cy, r, cut, turn))


def arch_d(x: float, y: float, w: float, h: float, *, pointed: bool = False) -> str:
    """A door or window opening standing on (x, y) (its bottom-left), w wide and h tall, round or pointed."""
    r = w / 2
    top = y - h + r
    if pointed:
        tip = y - h
        return (
            f"M{fmt(x)} {fmt(y)} L{fmt(x)} {fmt(top)} Q{fmt(x)} {fmt(tip + r * 0.25)} "
            f"{fmt(x + r)} {fmt(tip)} "
            f"Q{fmt(x + w)} {fmt(tip + r * 0.25)} {fmt(x + w)} {fmt(top)} L{fmt(x + w)} {fmt(y)} Z"
        )
    return (
        f"M{fmt(x)} {fmt(y)} L{fmt(x)} {fmt(top)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + w)} {fmt(top)} "
        f"L{fmt(x + w)} {fmt(y)} Z"
    )


def arch(x: float, y: float, w: float, h: float, *, pointed: bool = False) -> str:
    return p(arch_d(x, y, w, h, pointed=pointed))


def wave_d(x0: float, x1: float, y: float, amp: float, n: int) -> str:
    """An open wavy line from x0 to x1 at height y: `n` humps of height `amp` (sea, grass edges)."""
    step = (x1 - x0) / n
    d = f"M{fmt(x0)} {fmt(y)}"
    for i in range(n):
        xa = x0 + step * i
        d += f" Q{fmt(xa + step / 4)} {fmt(y - amp)} {fmt(xa + step / 2)} {fmt(y)}"
        d += f" T{fmt(xa + step)} {fmt(y)}"
    return d


def clip(uid: str, d_or_rect: str, body: str) -> str:
    """`body` clipped to a shape (an element string): scenes end cleanly at their frame."""
    return f'<clipPath id="{uid}">{d_or_rect}</clipPath><g clip-path="url(#{uid})">{body}</g>'


def svg(w: float, h: float, body: str, *, css_class: str = "", pad: float = 0.0) -> str:
    """An SVG drawing w × h mm whose user units are millimetres (`pad`: room for the outline at the edge)."""
    cls = f' class="{css_class}"' if css_class else ""
    return (
        f'<svg{cls} xmlns="http://www.w3.org/2000/svg" viewBox="{fmt(-pad)} {fmt(-pad)} {fmt(w + 2 * pad)} '
        f'{fmt(h + 2 * pad)}" width="{fmt(w + 2 * pad)}mm" height="{fmt(h + 2 * pad)}mm" '
        f'aria-hidden="true">{body}</svg>'
    )
