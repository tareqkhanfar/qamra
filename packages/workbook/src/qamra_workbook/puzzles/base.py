"""Shared puzzle helpers: seeded randomness and non-overlapping placement."""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass


def rng(seed: int | str, salt: str = "") -> random.Random:
    """A generator that gives the same sequence for the same seed on every run and machine."""
    key = f"{seed}:{salt}".encode()
    return random.Random(zlib.crc32(key))


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h / 2

    def grow(self, by: float) -> Box:
        return Box(self.x - by, self.y - by, self.w + 2 * by, self.h + 2 * by)

    def overlaps(self, other: Box, margin: float = 0) -> bool:
        return not (
            self.right + margin <= other.x
            or other.right + margin <= self.x
            or self.bottom + margin <= other.y
            or other.bottom + margin <= self.y
        )

    def inside(self, other: Box) -> bool:
        return (
            self.x >= other.x - 1e-6
            and self.y >= other.y - 1e-6
            and self.right <= other.right + 1e-6
            and self.bottom <= other.bottom + 1e-6
        )


def place(
    r: random.Random, zone: Box, w: float, h: float, taken: list[Box], margin: float, tries: int = 400
) -> Box | None:
    """A random w × h box inside `zone` that keeps `margin` from every box in `taken`."""
    if w > zone.w or h > zone.h:
        return None
    for _ in range(tries):
        box = Box(zone.x + r.uniform(0, zone.w - w), zone.y + r.uniform(0, zone.h - h), w, h)
        if not any(box.overlaps(t, margin) for t in taken):
            return box
    return None


def any_overlap(boxes: list[Box], margin: float = 0) -> bool:
    return any(a.overlaps(b, margin) for i, a in enumerate(boxes) for b in boxes[i + 1 :])
