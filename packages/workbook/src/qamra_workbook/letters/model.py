"""The letter model shared by every script: writing lines, strokes in writing order, dots and join points.

Lives here (not in `qamra_workbook.strokes`, which re-exports it) so the letter families can import it
without an import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from qamra_workbook.geometry import Point, Stroke


@dataclass(frozen=True)
class Guides:
    """Writing lines in the letter's own units (y grows downwards). `low` is the descender line: how far
    tails and bowls may go below the base line."""

    top: float
    base: float
    mid: float | None = None
    low: float | None = None


@dataclass(frozen=True)
class Letter:
    char: str
    form: str  # Arabic: isolated|initial|medial|final; English: capital|small
    width: float  # design box width; the box starts at x = 0
    guides: Guides
    strokes: tuple[Stroke, ...]  # in writing order; the first is the letter's body, later ones its marks
    dots: tuple[Point, ...] = ()  # written after every stroke, in this order
    dot_r: float = 0.0
    # Connected Arabic forms: where the line from the previous letter arrives (right side) and where it
    # leaves for the next one (left side), both on the base line at the edge of the box. Placing forms
    # box to box (right to left) makes these meet.
    join_right: Point | None = None
    join_left: Point | None = None

    @property
    def rtl(self) -> bool:
        return "؀" <= self.char <= "ۿ"
