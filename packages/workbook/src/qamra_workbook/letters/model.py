"""The letter model shared by every script: writing lines, strokes in writing order, dots and join points.

Lives here (not in `qamra_workbook.strokes`, which re-exports it) so the letter families can import it
without an import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from qamra_workbook.geometry import Point, Stroke, bounds

# A stroke written after the body that fits in a box this size (letter units) is a small mark: the hamza of
# أ إ ؤ ئ, the madda of آ, the little hamza inside ك. The stick of ط and the head of the medial ك are taller.
MARK_BOX = 60.0


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

    @cached_property
    def marks(self) -> tuple[bool, ...]:
        """For each stroke, whether it is a small mark written after the body (`MARK_BOX`). Marks are drawn
        thinner than the body, so they stay open shapes."""
        out = []
        for i, s in enumerate(self.strokes):
            x0, y0, x1, y1 = bounds([s])
            out.append(self.rtl and i > 0 and max(x1 - x0, y1 - y0) <= MARK_BOX)
        return tuple(out)

    @property
    def small(self) -> tuple[bool, ...]:
        """For each stroke, whether tracing dots alone would not show its shape: the marks, and the lone hamza
        ء (its whole body is that small curl). The tracing pages lay a pale ghost of the shape under fewer,
        evenly spaced dots and put its start dot and arrow beside it, never on it."""
        return tuple(m or self.char == "ء" for m in self.marks)
