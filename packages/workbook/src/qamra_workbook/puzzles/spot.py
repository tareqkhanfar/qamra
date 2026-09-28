"""Spot the difference (Addendum 6 §5): one scene composed from the picture library, then exactly N
controlled edits (remove, recolor, swap, resize, add) on well-separated objects.

Checks: comparing the two scenes object by object finds exactly the edited objects, their count equals the
answer key, and every difference sits in its own area of the picture so each one can be circled alone.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Literal

from qamra_workbook.pictures import get as picture
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.puzzles.base import Box, any_overlap, place, rng

EditKind = Literal["remove", "recolor", "swap", "resize", "add"]
EDIT_KINDS: tuple[EditKind, ...] = ("remove", "recolor", "swap", "resize", "add")
REGION_MARGIN = 2.5  # mm around a difference; regions never touch


@dataclass(frozen=True)
class Placed:
    key: str
    picture: str
    box: Box
    colors: Mapping[str, str] = field(default_factory=dict)
    flip: bool = False


@dataclass(frozen=True)
class Scene:
    w: float
    h: float
    horizon: float  # where the sky meets the grass
    objects: tuple[Placed, ...]

    def by_key(self) -> dict[str, Placed]:
        return {o.key: o for o in self.objects}


@dataclass(frozen=True)
class Difference:
    kind: EditKind
    key: str
    region: Box
    text: str  # for the answer key


@dataclass(frozen=True)
class SpotPuzzle:
    a: Scene
    b: Scene
    differences: tuple[Difference, ...]
    count: int

    def changed_keys(self) -> set[str]:
        a, b = self.a.by_key(), self.b.by_key()
        return {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}

    def problems(self) -> list[str]:
        out = []
        changed = self.changed_keys()
        if len(changed) != self.count:
            out.append(f"the scenes differ in {len(changed)} objects, the page promises {self.count}")
        if len(self.differences) != self.count:
            out.append(f"the answer key lists {len(self.differences)} differences, not {self.count}")
        if changed != {d.key for d in self.differences}:
            out.append("the answer key does not match the edited objects")
        regions = [d.region for d in self.differences]
        if any_overlap(regions):
            out.append("two differences share an area")
        frame = Box(0, 0, self.a.w, self.a.h)
        for scene, name in ((self.a, "first"), (self.b, "second")):
            if any(not o.box.inside(frame) for o in scene.objects):
                out.append(f"an object leaves the {name} picture")
            if any_overlap([o.box for o in scene.objects], margin=1.0):
                out.append(f"objects overlap in the {name} picture")
        return out


# what can go where in the garden scene: (picture, size in mm); every scene has the fixed ones
SKY_FIXED = (("sun", 23.0), ("cloud", 27.0))
SKY_EXTRA = (("cloud", 23.0), ("bird", 17.0), ("butterfly", 16.0), ("balloon", 19.0))
GROUND_FIXED = (("tree", 38.0), ("house", 36.0))
GROUND_EXTRA = (
    ("flower", 17.0),
    ("flower", 15.0),
    ("cat", 19.0),
    ("duck", 18.0),
    ("ball", 14.0),
    ("rabbit", 18.0),
)
SWAPS = {
    "cat": "dog",
    "dog": "cat",
    "duck": "rabbit",
    "rabbit": "duck",
    "flower": "strawberry",
    "ball": "apple",
    "bird": "butterfly",
    "butterfly": "bird",
    "balloon": "star",
    "sun": "moon",
    "cloud": "raindrop",
}
RECOLORS = ("#5E86D6", "#7DB46C", "#9376CF", "#E5604E", "#F7C84A", "#4FA89A")
ADDITIONS = (("butterfly", 14.0), ("star", 13.0), ("ball", 13.0), ("flower", 14.0), ("bird", 14.0))


def _word(pic_id: str) -> str:
    return strip_tashkeel(picture(pic_id).word_ar)


def compose(w: float, h: float, seed: int | str) -> Scene:
    """A calm garden: sun and clouds over a house, a tree and a few small friends (never crowded)."""
    r = rng(seed, "scene")
    horizon = h * 0.46
    sky_zone = Box(3, 3, w - 6, horizon - 4)
    ground_zone = Box(3, horizon - 12, w - 6, h - horizon + 9)
    ground = [*GROUND_FIXED, *r.sample(GROUND_EXTRA, 3)]
    sky = [*SKY_FIXED, *r.sample(SKY_EXTRA, 2)]
    taken: list[Box] = []
    objects: list[Placed] = []
    for zone, pool in ((ground_zone, ground), (sky_zone, sky)):
        for pic, size in pool:
            box = place(r, zone, size, size, taken, margin=6.0)
            if box is None:
                raise ValueError(f"the scene has no room for {pic} (seed {seed})")
            taken.append(box)
            objects.append(Placed(f"{pic}-{len(objects)}", pic, box, flip=r.random() < 0.5))
    objects.sort(key=lambda o: (o.box.bottom, o.key))  # nearer (lower) objects are drawn on top
    return Scene(w, h, horizon, tuple(objects))


def _edit(kind: EditKind, obj: Placed, r: random.Random) -> tuple[Placed | None, str]:
    word = _word(obj.picture)
    match kind:
        case "remove":
            return None, f"ناقص: {word}"
        case "recolor":
            pic = picture(obj.picture)
            key = "main" if "main" in pic.palette else next(iter(pic.palette))
            new = r.choice([c for c in RECOLORS if c.lower() != pic.palette[key].lower()])
            return replace(obj, colors={key: new}), f"اللون: {word}"
        case "swap":
            other = SWAPS[obj.picture]
            return replace(obj, picture=other), f"تبديل: {word} ← {_word(other)}"
        case "resize":
            b = obj.box
            s = b.w * 0.6
            return replace(obj, box=Box(b.x + (b.w - s) / 2, b.bottom - s, s, s)), f"الحجم: {word} أصغر"
        case "add":
            raise ValueError("additions are not edits of an existing object")


def generate_spot(w: float, h: float, seed: int | str, count: int = 5) -> SpotPuzzle:
    """Two scenes of w × h mm that differ in exactly `count` places (one edit per kind up to five)."""
    if not 1 <= count <= len(EDIT_KINDS) + 2:
        raise ValueError("spot-the-difference supports 1–7 differences")
    for attempt in range(50):  # a crowded draw is retried with the next derived seed (still deterministic)
        try:
            return _generate(w, h, f"{seed}/{attempt}", count)
        except ValueError:
            continue
    raise ValueError(f"could not fit {count} differences in a {w} × {h} mm scene (seed {seed})")


def _generate(w: float, h: float, seed: str, count: int) -> SpotPuzzle:
    a = compose(w, h, seed)
    r = rng(seed, "edits")
    kinds: list[EditKind] = [*EDIT_KINDS, "recolor", "remove"][:count]
    r.shuffle(kinds)
    candidates = list(a.objects)
    r.shuffle(candidates)
    b_objects = {o.key: o for o in a.objects}
    diffs: list[Difference] = []
    for kind in kinds:
        if kind == "add":
            continue
        obj = next(
            (o for o in candidates if (kind != "swap" or o.picture in SWAPS) and o.picture != "cloud"),
            None,
        )
        if obj is None:
            raise ValueError(f"no object left for a {kind} difference")
        new, text = _edit(kind, obj, r)
        candidates.remove(obj)
        if new is None:
            del b_objects[obj.key]
        else:
            b_objects[obj.key] = new
        diffs.append(Difference(kind, obj.key, obj.box.grow(REGION_MARGIN), text))
    if "add" in kinds:
        taken = [o.box.grow(REGION_MARGIN) for o in a.objects]
        pic, size = r.choice(ADDITIONS)
        box = place(r, Box(4, 4, w - 8, h - 8), size, size, taken, margin=REGION_MARGIN * 2)
        if box is None:
            raise ValueError("no free space for an added object")
        key = f"{pic}-extra"
        b_objects[key] = Placed(key, pic, box)
        diffs.append(Difference("add", key, box.grow(REGION_MARGIN), f"زيادة: {_word(pic)}"))
    b = Scene(w, h, a.horizon, tuple(sorted(b_objects.values(), key=lambda o: (o.box.bottom, o.key))))
    diffs.sort(key=lambda d: (d.region.center[1] > h / 2, -d.region.center[0]))  # read in rows, right first
    puzzle = SpotPuzzle(a, b, tuple(diffs), count)
    if puzzle.problems():
        raise ValueError("; ".join(puzzle.problems()))
    return puzzle
