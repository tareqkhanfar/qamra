"""Smart coloring (Addendum 6 §4.5): a scene built from simple shapes; the child colors by a rule.

Each object in the scene (house, tree, car, balloons…) is made of tagged shapes, so the answer key counts
exactly how many shapes the rule selects. Checks: the count matches the key, there are distractor shapes
of at least two other kinds, everything stays inside the picture, and objects do not overlap.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from qamra_workbook.puzzles.base import Box, any_overlap, rng

ShapeKind = Literal["circle", "triangle", "square", "rectangle", "star", "heart", "diamond"]
SHAPE_AR: dict[str, str] = {
    "circle": "الدوائر",
    "triangle": "المثلثات",
    "square": "المربعات",
    "rectangle": "المستطيلات",
    "star": "النجوم",
    "heart": "القلوب",
    "diamond": "المعيّنات",
}


@dataclass(frozen=True)
class Shape:
    kind: ShapeKind
    cx: float
    cy: float
    w: float
    h: float
    rotate: float = 0.0

    @property
    def box(self) -> Box:
        if self.rotate % 180 and self.kind not in ("circle",):
            r = math.hypot(self.w, self.h) / 2
            return Box(self.cx - r, self.cy - r, 2 * r, 2 * r)
        return Box(self.cx - self.w / 2, self.cy - self.h / 2, self.w, self.h)


@dataclass(frozen=True)
class Thing:
    name: str
    box: Box
    shapes: tuple[Shape, ...]
    lines: tuple[str, ...] = ()  # strings, stems and rays: drawn, never colored or counted


Maker = Callable[[float, float], Thing]  # (left, top) → the object


def _house(x: float, y: float) -> Thing:
    return Thing(
        "house",
        Box(x, y, 46, 50),
        (
            Shape("square", x + 23, y + 34, 32, 32),
            Shape("triangle", x + 23, y + 9.5, 46, 19),
            Shape("rectangle", x + 16, y + 41, 9, 18),
            Shape("square", x + 31, y + 30, 9, 9),
            Shape("circle", x + 23, y + 12, 6.5, 6.5),
        ),
    )


def _tree(x: float, y: float) -> Thing:
    return Thing(
        "tree",
        Box(x, y, 32, 50),
        (Shape("rectangle", x + 16, y + 40, 7, 20), Shape("circle", x + 16, y + 16, 32, 32)),
    )


def _car(x: float, y: float) -> Thing:
    return Thing(
        "car",
        Box(x, y, 50, 32),
        (
            Shape("rectangle", x + 25, y + 10, 26, 13),
            Shape("rectangle", x + 25, y + 21, 50, 14),
            Shape("circle", x + 12, y + 27, 10, 10),
            Shape("circle", x + 38, y + 27, 10, 10),
        ),
    )


def _balloons(x: float, y: float) -> Thing:
    return Thing(
        "balloons",
        Box(x, y, 34, 50),
        (
            Shape("circle", x + 8, y + 12, 14, 16),
            Shape("circle", x + 26, y + 10, 14, 16),
            Shape("heart", x + 17, y + 26, 13, 12),
        ),
        (
            f"M{x + 8} {y + 20} C{x + 10} {y + 34} {x + 15} {y + 40} {x + 17} {y + 49}",
            f"M{x + 26} {y + 18} C{x + 24} {y + 34} {x + 19} {y + 40} {x + 17} {y + 49}",
            f"M{x + 17} {y + 32} L{x + 17} {y + 49}",
        ),
    )


def _sun(x: float, y: float) -> Thing:
    cx, cy = x + 15, y + 15
    rays = tuple(
        f"M{cx + 11 * math.cos(a):.1f} {cy + 11 * math.sin(a):.1f} "
        f"L{cx + 15 * math.cos(a):.1f} {cy + 15 * math.sin(a):.1f}"
        for a in (i * math.pi / 4 for i in range(8))
    )
    return Thing("sun", Box(x, y, 30, 30), (Shape("circle", cx, cy, 17, 17),), rays)


def _kite(x: float, y: float) -> Thing:
    return Thing(
        "kite",
        Box(x, y, 26, 48),
        (
            Shape("diamond", x + 13, y + 12, 24, 24),
            Shape("triangle", x + 9, y + 33, 7, 6, 90),
            Shape("triangle", x + 16, y + 42, 7, 6, -90),
        ),
        (f"M{x + 13} {y + 24} C{x + 6} {y + 30} {x + 20} {y + 36} {x + 12} {y + 47}",),
    )


def _ice_cream(x: float, y: float) -> Thing:
    return Thing(
        "ice-cream",
        Box(x, y, 20, 40),
        (Shape("triangle", x + 10, y + 27, 18, 24, 180), Shape("circle", x + 10, y + 9, 17, 17)),
    )


def _star(x: float, y: float) -> Thing:
    return Thing("star", Box(x, y, 18, 18), (Shape("star", x + 9, y + 9, 18, 18),))


def _heart(x: float, y: float) -> Thing:
    return Thing("heart", Box(x, y, 16, 15), (Shape("heart", x + 8, y + 7.5, 16, 15),))


def _flag(x: float, y: float) -> Thing:
    return Thing(
        "flag",
        Box(x, y, 22, 40),
        (Shape("triangle", x + 12, y + 9, 16, 14, 90),),
        (f"M{x + 3} {y + 1} L{x + 3} {y + 40}",),
    )


SKY_THINGS: tuple[Maker, ...] = (_sun, _balloons, _kite)
GROUND_THINGS: tuple[Maker, ...] = (_house, _tree, _car, _ice_cream, _flag)
FILLERS: tuple[Maker, ...] = (_star, _heart, _star)


@dataclass(frozen=True)
class ColoringScene:
    w: float
    h: float
    ground: float  # y of the ground line
    target: ShapeKind
    things: tuple[Thing, ...]
    count: int  # the answer key: shapes the rule selects

    @property
    def shapes(self) -> list[Shape]:
        return [s for t in self.things for s in t.shapes]

    def problems(self) -> list[str]:
        out = []
        kinds = Counter(s.kind for s in self.shapes)
        if kinds[self.target] != self.count:
            out.append(f"{kinds[self.target]} {self.target} shapes on the page, the key says {self.count}")
        if len([k for k in kinds if k != self.target]) < 2:
            out.append("the scene needs distractors of at least two other shapes")
        frame = Box(0, 0, self.w, self.h)
        if any(not s.box.inside(frame) for s in self.shapes):
            out.append("a shape leaves the picture")
        if any_overlap([t.box for t in self.things], margin=2):
            out.append("objects overlap")
        return out


def generate_coloring(w: float, h: float, seed: int | str, target: ShapeKind = "circle") -> ColoringScene:
    """Three sky objects over three ground objects, in seeded slots, with small fillers between. A draw that
    fails its checks is retried with the next derived seed, so the result stays deterministic."""
    for attempt in range(50):
        scene = _compose(w, h, f"{seed}/{attempt}", target)
        if not scene.problems():
            return scene
    raise ValueError(f"no valid coloring scene fits {w} × {h} mm (seed {seed})")


def _compose(w: float, h: float, seed: str, target: ShapeKind) -> ColoringScene:
    r = rng(seed, "coloring")
    ground = h * 0.9
    sky = r.sample(SKY_THINGS, 3)
    land = [_house, *r.sample([m for m in GROUND_THINGS if m is not _house], 2)]
    r.shuffle(land)
    things: list[Thing] = []
    slot_w = w / 3
    for makers, top in ((sky, h * 0.04), (land, None)):
        for i, make in enumerate(makers):
            probe = make(0, 0).box
            left = slot_w * i + (slot_w - probe.w) / 2 + r.uniform(-3, 3)
            left = max(2.0, min(w - probe.w - 2, left))
            y = top + r.uniform(0, 6) if top is not None else ground - probe.h
            things.append(make(left, y))
    taken = [t.box for t in things]
    for make in FILLERS:
        probe = make(0, 0).box
        for _ in range(200):
            x, y = r.uniform(3, w - probe.w - 3), r.uniform(3, ground - probe.h - 3)
            box = Box(x, y, probe.w, probe.h)
            if not any(box.overlaps(t, 4) for t in taken):
                things.append(make(x, y))
                taken.append(box)
                break
    count = sum(1 for t in things for s in t.shapes if s.kind == target)
    return ColoringScene(w, h, ground, target, tuple(things), count)
