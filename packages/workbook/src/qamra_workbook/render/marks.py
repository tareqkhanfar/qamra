"""Small marks on traced letters, and the letters' dots: how every tracing page draws them so that a child of
3–6 reads them at every printed size (the big letter, the writing rows, a name).

A small mark is the hamza of أ إ ؤ ئ, the madda of آ, the little hamza inside ك, or the lone ء
(`Letter.small`). On a small writing row it is a few millimetres across: plain tracing dots (3.5 mm apart)
gave it four or five dots, and the green start dot sat on its head and hid what was left, so the hamza read
like a damma «ُ» (the owner's review of «دوسية التأسيس» KG1, p18). So a small mark gets:

- a pale ghost of its real shape under its dots (`ghost`), so the head and the tail of the hamza show even
  where the dots are few;
- smaller dots, evenly spaced along it: closer than on the body when the mark is short (at least
  `MIN_INTERVALS` gaps), but never closer than `MIN_PITCH` dot radii, centre to centre (`mark_points`);
- its numbered start dot beside it, never on it (`beside`), and its arrow outside the shape, never on the
  dots (`side_arrow`).

The letter's own dots (ب ت ث …) are clear round dots to fill in (`dot_to_fill`): a pale disc with a solid
ring, not a dashed one; their numbers sit beside them, clear of the other dots and of the strokes.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from qamra_workbook.geometry import Point, Stroke, bounds
from qamra_workbook.render import draw

GHOST = "#B4BAD3"  # a thin pale line under a small mark's dots: its shape, not written yet
FILL = "#ECEEF6"  # the inside of a letter's dot to fill in
MIN_INTERVALS = 6  # a small mark gets at least this many gaps between its dots (7 dots) when they fit
MIN_PITCH = 2.5  # centre to centre, in dot radii: two dots of a mark always keep half a dot between them
CLEAR = 0.35  # mm between a badge or an arrow and whatever it sits beside

Obstacle = tuple[Point, float]  # a centre and a radius (mm) that a badge must keep clear of


def mark_points(stroke: Stroke, spacing: float, r: float) -> list[Point]:
    """Evenly spaced points along a small mark, both ends included: `spacing` apart, closer on a short mark
    (at least `MIN_INTERVALS` gaps), never closer than `MIN_PITCH` × `r` along it. Where the shape comes back
    near itself (the hamza's head closing above its tail), a point too close to one already kept is left
    out, so no two dots ever touch."""
    length = stroke.length
    pitch = max(MIN_PITCH * r, min(spacing, length / MIN_INTERVALS))
    count = max(1, math.floor(length / pitch + 1e-6))
    kept: list[Point] = []
    for k in range(count + 1):
        p = stroke.at(k / count)[0]
        if all(math.dist(p, q) >= MIN_PITCH * r * 0.9 for q in kept):
            kept.append(p)
    return kept


def dotted_once(strokes: Sequence[Stroke], spacing: float) -> list[list[Point]]:
    """Tracing dots along each stroke (its start left for the start dot), each about `spacing` apart, never
    two closer than 0.8 × `spacing`: where the pen comes back along its own line (a tooth of س, the head of
    ـد) the way back adds no second, offset column of dots."""
    placed: list[Point] = []
    out = []
    for s in strokes:
        kept = []
        for p in s.dots(spacing)[1:]:
            if all(math.dist(p, q) >= spacing * 0.8 for q in placed):
                kept.append(p)
                placed.append(p)
        out.append(kept)
    return out


def dot_radius(dots: Sequence[Point], strokes: Sequence[Stroke], r: float, line: float) -> float:
    """The radius of a letter's dots to fill in: `r`, smaller where they would touch each other or the letter
    (`line` is the half width of its tracing dots), never under 0.7 mm."""
    gaps = [math.dist(a, b) / 2 - 0.25 for i, a in enumerate(dots) for b in dots[i + 1 :]]
    gaps += [min(math.dist(d, q) for s in strokes for q in s.dots(0.5)) - line - 0.3 for d in dots]
    return max(0.7, min([r, *gaps]))


def dot_size(strokes: Sequence[Stroke], small: Sequence[bool], most: float, least: float = 0.5) -> float:
    """The radius (mm) of a small mark's dots: `most`, smaller on a small row (about a ninth of the mark's
    size, never under `least`), so a hamza a few millimetres high still gets its head and tail in dots."""
    sizes = [
        max(b[2] - b[0], b[3] - b[1]) for s, m in zip(strokes, small, strict=True) if m for b in [bounds([s])]
    ]
    return max(least, min(most, 0.11 * min(sizes))) if sizes else most


def mark_dots(stroke: Stroke, spacing: float, r: float, color: str = draw.DOT) -> str:
    """The dots of a small mark (`mark_points`), the start one included: its start dot sits beside it."""
    return f'<g class="mark-dots">{draw.dots(mark_points(stroke, spacing, r), r, color)}</g>'


def ghost(stroke: Stroke, width: float, color: str = GHOST) -> str:
    """The mark's real shape as a pale line under its dots."""
    return draw.path(stroke.d, stroke=color, width=width, class_="mark-ghost")


def centroid(points: Sequence[Point]) -> Point:
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def outline(strokes: Iterable[Stroke], r: float, step: float = 0.6) -> list[Obstacle]:
    """The strokes as obstacles: points every `step` mm along them, each `r` wide (the dots on them)."""
    return [(p, r) for s in strokes for p in s.dots(step)]


def clear_of(c: Point, radius: float, obstacles: Iterable[Obstacle]) -> bool:
    return all(math.dist(c, q) >= radius + rq + CLEAR - 1e-6 for q, rq in obstacles)


def beside(point: Point, away: float, radius: float, reach: float, obstacles: Sequence[Obstacle]) -> Point:
    """Where a badge of `radius` goes next to `point` (a dot `reach` wide sits there): just clear of that dot,
    in the direction `away` (degrees) when nothing is there, else in the nearest clear direction, a little
    further out if it must."""
    for push in (1.0, 1.35, 1.8):
        d = reach + CLEAR + radius * push
        for turn in (0, 25, -25, 50, -50, 75, -75, 100, -100, 130, -130, 160, -160, 180):
            a = math.radians(away + turn)
            c = (point[0] + math.cos(a) * d, point[1] + math.sin(a) * d)
            if clear_of(c, radius, obstacles):
                return c
    a = math.radians(away)
    d = reach + CLEAR + radius
    return point[0] + math.cos(a) * d, point[1] + math.sin(a) * d


def away_from_shape(stroke: Stroke) -> float:
    """The direction (degrees) from the middle of a mark out through its start: where its badge goes."""
    cx, cy = centroid(stroke.polyline)
    x, y = stroke.start
    if math.dist((cx, cy), (x, y)) < 1e-6:
        return -45.0
    return math.degrees(math.atan2(y - cy, x - cx))


def start_badge(
    stroke: Stroke, radius: float, reach: float, obstacles: Sequence[Obstacle], away: float | None = None
) -> Point:
    """The centre of a small mark's numbered start dot: beside its first dot, out of the shape (or towards
    `away`, in degrees)."""
    return beside(stroke.start, away_from_shape(stroke) if away is None else away, radius, reach, obstacles)


def side_arrow(
    stroke: Stroke,
    size: float,
    reach: float,
    obstacles: Sequence[Obstacle],
    color: str = draw.ARROW,
    at: tuple[float, ...] = (0.16, 0.3, 0.42, 0.55),
) -> tuple[str, Point]:
    """One arrowhead for a small mark, outside its shape (on the side away from its middle) near its
    start, pointing the way the pen goes; the first of the fractions `at` where it is clear of the
    obstacles. Returns the arrow and its centre."""
    cx, cy = centroid(stroke.polyline)
    best: tuple[Point, float] | None = None
    for f in at:
        (x, y), angle = stroke.at(f)
        a = math.radians(angle)
        nx, ny = -math.sin(a), math.cos(a)
        if math.dist((x + nx, y + ny), (cx, cy)) < math.dist((x - nx, y - ny), (cx, cy)):
            nx, ny = -nx, -ny  # the outer side
        d = reach + CLEAR + size * 0.55
        c = (x + nx * d, y + ny * d)
        if best is None:
            best = (c, angle)
        if clear_of(c, size * 0.5, obstacles):
            best = (c, angle)
            break
    assert best is not None
    return draw.arrow(best[0], best[1], size, color), best[0]


def dot_to_fill(
    cx: float, cy: float, r: float, *, ring: float, fill: str = FILL, color: str = draw.DOT
) -> str:
    """A letter's dot to fill in: a clear round dot, a pale disc with a solid ring `ring` mm wide."""
    return draw.el(
        "circle", cx=cx, cy=cy, r=r, fill=fill, stroke=color, stroke_width=ring, class_="dot-to-fill"
    )


def badge_points(
    strokes: Sequence[Stroke],
    small: Sequence[bool],
    radius: float,
    *,
    mark_radius: float,
    reach: float,
    obstacles: Sequence[Obstacle] = (),
    away: float | None = None,
) -> list[Point]:
    """Where each stroke's numbered start dot goes. A stroke of the body: on its start, or a little along it
    when an earlier dot already sits there (both slants of A start at the apex) or a small mark is that
    close (the hamza over the alif). A small mark: beside its first dot (`start_badge`, `mark_radius`,
    towards `away` when given), clear of the `obstacles` and of the other start dots."""
    near_marks = outline([s for s, m in zip(strokes, small, strict=True) if m], reach)
    out: list[Point] = []
    for s, is_small in zip(strokes, small, strict=True):
        if is_small:
            near = [*obstacles, *((p, radius) for p in out)]
            out.append(start_badge(s, mark_radius, reach, near, away))
            continue
        point = s.start
        earlier = [q for e, m in zip(strokes[: len(out)], small, strict=False) if not m for q in e.dots(0.5)]
        on_earlier = any(math.dist(point, q) < radius * 1.2 for q in earlier)
        if on_earlier or any(math.dist(point, q) < radius * 1.9 for q in out):
            # it starts on a line already drawn (the hump of n on its stem): the dot goes a little along it
            step = radius * 2.9 / max(s.length, 1e-6)
            for k in range(1, 4):  # far enough along that the two numbered dots do not touch
                point = s.at(min(0.45, step * k))[0]
                if all(math.dist(point, q) >= radius * 2.2 for q in out):
                    break
        elif not clear_of(point, radius, near_marks):
            for k in range(1, 16):  # slide down the stroke, at most 30 % of it, until clear of the mark
                point = s.at(0.02 * k)[0]
                if clear_of(point, radius, near_marks):
                    break
        out.append(point)
    return out


def dot_badges(
    dots: Sequence[Point],
    r: float,
    radius: float,
    obstacles: Sequence[Obstacle],
    strokes: Sequence[Stroke] = (),
) -> list[Point]:
    """Where the numbered badges of a letter's dots go: beside each dot, on its free side (the right dot's
    to its right, the left one's to its left; a lone or middle dot's away from the letter: above the dot of
    ن, under the dot of ب), clear of the other dots, the strokes and the badges already placed."""
    placed: list[Point] = []
    others = [(d, r) for d in dots]
    middle = sum(d[0] for d in dots) / len(dots) if dots else 0.0
    for d in dots:
        if abs(d[0] - middle) > r:
            away = 180.0 if d[0] < middle else 0.0
        else:
            body = [q for st in strokes for q in st.polyline] or [q for q, _ in obstacles]
            near = min(body, key=lambda q: math.dist(q, d), default=(d[0], d[1] + 1))
            away = math.degrees(math.atan2(d[1] - near[1], d[0] - near[0]))
        placed.append(beside(d, away, radius, r, [*obstacles, *others, *((p, radius) for p in placed)]))
    return placed
