"""Palestinian heritage patterns drawn from geometry: tatreez (cross-stitch) motifs and the keffiyeh's bands.

Tatreez is stitched on a grid, so a motif here is a set of grid *cells* and is drawn as the stepped outline of
their union (`cells_d`): the stair-stepped edge of a cross-stitch star, diamond or cypress tree, but as one
big closed area a small hand can colour. A motif is painted in *layers* (an outer star, a smaller star on top,
a heart in the middle), each layer a closed shape in its own colour.

    from qamra_workbook.coloring.parts.heritage import star8, motif
    place(pen, motif, 93, 116, 1.0, layers=[(star8(4, 6), RED), (star8(2, 3), GOLD), (diamond(1), NAVY)], cell=7)

The keffiyeh's three classic bands are here too: the fishnet field (`fishnet`), the olive-leaf chain
(`leaf_chain`) and the bold lines (`bold_lines`), and a whole keffiyeh square (`keffiyeh`).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from qamra_workbook.coloring.ink import GOLD, NAVY, Pen, Point, fmt, p, rect
from qamra_workbook.coloring.parts.common import leaf_d

Cell = tuple[int, int]
Layer = tuple[set[Cell], str]

TATREEZ_RED = "#C8343F"
TATREEZ_WINE = "#8E2A3A"
TATREEZ_GREEN = "#3F8A5A"
TATREEZ_GOLD = "#F2B33D"
TATREEZ_NAVY = "#2F3E7A"
LINEN = "#FBF3E2"
KEFFIYEH_WHITE = "#FFFFFF"
KEFFIYEH_BLACK = "#2E2A33"

# ---- cells → stepped outlines ----------------------------------------------------------------------------------


def cells_d(cells: Iterable[Cell], cell: float, x0: float = 0.0, y0: float = 0.0) -> str:
    """Path data of the outline of the union of grid cells (cell (i, j) spans x0 + i·cell … and y0 + j·cell …,
    centred so cell (0, 0) sits on (x0, y0)). Holes come out as reversed loops (nonzero fill keeps them)."""
    cs = set(cells)
    edges: dict[tuple[Cell, Cell], None] = {}
    for i, j in cs:
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]  # clockwise on screen (y down)
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]
            if (b, a) in edges:
                del edges[(b, a)]
            else:
                edges[(a, b)] = None
    nxt: dict[Cell, list[Cell]] = {}
    for a, b in edges:
        nxt.setdefault(a, []).append(b)
    d = []
    while nxt:
        start = next(iter(nxt))
        loop = [start]
        cur = start
        while True:
            outs = nxt[cur]
            b = outs.pop()
            if not outs:
                del nxt[cur]
            if b == start:
                break
            loop.append(b)
            cur = b
        loop = _corners_only(loop)
        h = cell / 2
        d.append(
            "M" + " L".join(f"{fmt(x0 + x * cell - h)} {fmt(y0 + y * cell - h)}" for x, y in loop) + " Z"
        )
    return " ".join(d)


def _corners_only(loop: list[Cell]) -> list[Cell]:
    n = len(loop)
    keep = []
    for k in range(n):
        a, b, c = loop[k - 1], loop[k], loop[(k + 1) % n]
        if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) != 0:
            keep.append(b)
    return keep


# ---- motifs as cell sets (centred on cell (0, 0)) --------------------------------------------------------------


def square(a: int) -> set[Cell]:
    return {(i, j) for i in range(-a, a + 1) for j in range(-a, a + 1)}


def diamond(n: int) -> set[Cell]:
    return {(i, j) for i in range(-n, n + 1) for j in range(-n, n + 1) if abs(i) + abs(j) <= n}


def star8(a: int, b: int) -> set[Cell]:
    """The eight-pointed star of Bethlehem's embroidery: a square of half-side `a` and a diamond of radius `b`."""
    return square(a) | diamond(b)


def cypress(h: int) -> set[Cell]:
    """A stepped cypress tree in tiers, about `h` cells tall on a one-cell trunk (its foot at row 0)."""
    out = {(0, 0)}
    tiers = max(1, h // 3)
    row = -1
    for t in reversed(range(tiers)):  # the widest tier at the bottom
        for k in reversed(range(3)):
            half = t + k
            for i in range(-half, half + 1):
                out.add((i, row))
            row -= 1
    out.add((0, row))
    return out


def tooth(n: int) -> set[Cell]:
    """A stepped triangle «سِنّ» `n` cells tall, its base on row 0 (the «old man's teeth» border)."""
    return {(i, -k) for k in range(n) for i in range(-(n - 1 - k), n - k)}


def shift(cells: Iterable[Cell], di: int, dj: int) -> set[Cell]:
    return {(i + di, j + dj) for i, j in cells}


def ring(outer: set[Cell], inner: set[Cell]) -> set[Cell]:
    return outer - inner


# ---- drawing --------------------------------------------------------------------------------------------------


def motif(pen: Pen, *, layers: Sequence[Layer], cell: float = 6.0) -> str:
    """Layers of cells painted back to front, centred on the origin."""
    return "".join(pen.shape(p(cells_d(cells, cell)), fill=fill) for cells, fill in layers if cells)


def star_motif(
    pen: Pen,
    *,
    size: int = 6,
    cell: float = 6.0,
    colors: Sequence[str] = (TATREEZ_RED, TATREEZ_GOLD, TATREEZ_NAVY),
) -> str:
    """An eight-pointed star in three layers (outer star, inner star, heart), centred on the origin."""
    a = max(1, round(size * 0.66))
    inner_a, inner_b = max(1, a // 2), max(1, size // 2)
    return motif(
        pen,
        layers=[
            (star8(a, size), colors[0]),
            (star8(inner_a, inner_b), colors[1]),
            (diamond(max(0, inner_b - 2)), colors[2]),
        ],
        cell=cell,
    )


def band_of(
    pen: Pen,
    *,
    w: float,
    h: float,
    unit: str = "diamonds",
    cell: float = 5.0,
    fill: str = LINEN,
    colors: Sequence[str] = (TATREEZ_RED, TATREEZ_GOLD),
) -> str:
    """A horizontal embroidered band from x = 0 to w, from y = 0 down to h: a strip with a row of motifs
    (`diamonds`, `teeth`, `stars` or `cypress`) between two border lines."""
    out = [pen.shape(rect(0, 0, w, h), fill=fill)]
    rows = int(h // cell)
    mid_j = rows // 2
    y0 = (h - rows * cell) / 2 + cell / 2
    if unit == "teeth":
        n = max(2, rows - 1)
        width = 2 * n - 1
        count = int((w / cell) // width)
        x_first = (w - count * width * cell) / 2 + (n - 0.5) * cell
        cells: set[Cell] = set()
        for k in range(count):
            cells |= shift(tooth(n), k * width, rows - 1)
        out.append(pen.shape(p(cells_d(cells, cell, x_first, y0)), fill=colors[0]))
        return "".join(out)
    size = max(1, (rows - 1) // 2)
    unit_cells: dict[str, set[Cell]] = {
        "diamonds": diamond(size),
        "stars": star8(max(1, size * 2 // 3), size),
        "cypress": shift(cypress(rows - 3), 0, size + 1),
    }
    one = unit_cells[unit]
    span = 2 * size + 2
    count = int((w / cell) // span)
    x_first = (w - count * span * cell) / 2 + (size + 1) * cell
    shapes_a: set[Cell] = set()
    shapes_b: set[Cell] = set()
    for k in range(count):
        (shapes_a if k % 2 == 0 else shapes_b).update(shift(one, k * span, mid_j))
    out.append(pen.shape(p(cells_d(shapes_a, cell, x_first, y0)), fill=colors[0]))
    if shapes_b:
        out.append(pen.shape(p(cells_d(shapes_b, cell, x_first, y0)), fill=colors[1 % len(colors)]))
    if unit in ("diamonds", "stars") and size >= 3:
        hearts: set[Cell] = set()
        for k in range(count):
            hearts |= shift(diamond(size - 2), k * span, mid_j)
        out.append(pen.shape(p(cells_d(hearts, cell, x_first, y0)), fill=colors[-1]))
    return "".join(out)


# ---- keffiyeh ---------------------------------------------------------------------------------------------------


def _clip_segment(
    x0: float, y0: float, x1: float, y1: float, box: tuple[float, float, float, float]
) -> tuple[Point, Point] | None:
    """Liang–Barsky: the part of segment (x0, y0)–(x1, y1) inside box (left, top, right, bottom)."""
    left, top, right, bottom = box
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - left), (dx, right - x0), (-dy, y0 - top), (dy, bottom - y0)):
        if pp == 0:
            if qq < 0:
                return None
            continue
        t = qq / pp
        if pp < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return (x0 + dx * t0, y0 + dy * t0), (x0 + dx * t1, y0 + dy * t1)


def fishnet(
    pen: Pen, *, box: tuple[float, float, float, float], step: float = 18.0, fill: str = KEFFIYEH_WHITE
) -> str:
    """The keffiyeh's fishnet field: a lattice of diagonal lines over `box` (left, top, right, bottom) making
    big diamond cells, with a small knot (a round dot area) where the lines cross."""
    left, top, right, bottom = box
    out = [pen.shape(rect(left, top, right - left, bottom - top), fill=fill)]
    lines = []
    span = (right - left) + (bottom - top)
    n = int(span / step) + 2
    for k in range(-n, n + 1):
        x = left + k * step
        for sgn in (1, -1):
            seg = _clip_segment(x, top, x + sgn * (bottom - top) * 1.0, bottom, box)
            if seg:
                (a, b), (c2, d2) = seg
                lines.append(p(f"M{fmt(a)} {fmt(b)} L{fmt(c2)} {fmt(d2)}"))
    out.append(pen.stroke(*lines))
    return "".join(out)


def leaf_chain(
    pen: Pen,
    *,
    x0: float,
    x1: float,
    y: float,
    h: float,
    fill: str = KEFFIYEH_WHITE,
    leaf: str = KEFFIYEH_WHITE,
) -> str:
    """The olive-leaf band: a strip (h tall, centred on y) with a chain of leaves along it, alternately tilted."""
    out = [pen.shape(rect(x0, y - h / 2, x1 - x0, h), fill=fill)]
    length = h * 0.78
    step = length * 0.62
    n = int((x1 - x0 - length * 0.4) // step)
    first = x0 + ((x1 - x0) - (n - 1) * step) / 2
    leaves = []
    for k in range(n):
        x = first + k * step
        ang = -50 if k % 2 == 0 else 50
        base = (x - math.cos(math.radians(ang)) * length / 2, y - math.sin(math.radians(ang)) * length / 2)
        leaves.append(p(leaf_d(base[0], base[1], length, length * 0.36, ang)))
    out.append(pen.shape(*leaves, fill=leaf))
    return "".join(out)


def bold_lines(pen: Pen, *, x0: float, x1: float, y: float, h: float, fill: str = KEFFIYEH_BLACK) -> str:
    """The bold-line band: one strong stripe h tall centred on y, from x0 to x1."""
    return pen.shape(rect(x0, y - h / 2, x1 - x0, h), fill=fill)


def keffiyeh(pen: Pen, *, size: float = 160.0, step: float = 20.0) -> str:
    """A keffiyeh laid flat, centred on its origin: a fishnet field framed by an olive-leaf chain and a bold
    stripe on every side, with tassels along the top and bottom edges."""
    s = size / 2
    bl = size * 0.06
    lc = size * 0.12
    out = []
    tassels = []
    n = 13
    for k in range(n):
        x = -s + 8 + (2 * s - 16) * k / (n - 1)
        for sy in (-1, 1):
            y = sy * s
            tassels.append(
                p(
                    f"M{fmt(x - 2.6)} {fmt(y)} L{fmt(x - 3.4)} {fmt(y + sy * 7)} Q{fmt(x)} {fmt(y + sy * 13)} {fmt(x + 3.4)} {fmt(y + sy * 7)} L{fmt(x + 2.6)} {fmt(y)} Z"
                )
            )
    out.append(pen.shape(*tassels, fill=KEFFIYEH_BLACK))
    inner = s - bl - lc
    out.append(fishnet(pen, box=(-inner, -inner, inner, inner), step=step))
    for sy in (-1, 1):
        out.append(bold_lines(pen, x0=-s, x1=s, y=sy * (s - bl / 2), h=bl))
        out.append(leaf_chain(pen, x0=-s + bl, x1=s - bl, y=sy * (s - bl - lc / 2), h=lc))
    for sx in (-1, 1):
        out.append(
            f'<g transform="translate({fmt(sx * (s - bl / 2))} 0) rotate(90)">{bold_lines(pen, x0=-s + bl, x1=s - bl, y=0, h=bl)}</g>'
        )
        out.append(
            f'<g transform="translate({fmt(sx * (s - bl - lc / 2))} 0) rotate(90)">{leaf_chain(pen, x0=-inner, x1=inner, y=0, h=lc)}</g>'
        )
    return "".join(out)


__all__ = [
    "GOLD",
    "NAVY",
    "band_of",
    "bold_lines",
    "cells_d",
    "cypress",
    "diamond",
    "fishnet",
    "keffiyeh",
    "leaf_chain",
    "motif",
    "ring",
    "shift",
    "square",
    "star8",
    "star_motif",
    "tooth",
]
