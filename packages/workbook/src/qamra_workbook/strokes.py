"""Letter stroke data for tracing pages: single-stroke paths in writing order, plus the letter's dots.

Hand-authored for the samples (ب isolated, A, a). Every letter and form (Arabic isolated/initial/medial/
final, English A–Z and a–z, digits) needs the same data before the full books; an educator signs off on
the forms and stroke directions (Addendum 5 §8, Addendum 6 §9).
"""

from __future__ import annotations

from dataclasses import dataclass

from qamra_workbook.geometry import Point, Stroke


@dataclass(frozen=True)
class Guides:
    """Writing lines in the letter's own units (y grows downwards)."""

    top: float
    base: float
    mid: float | None = None


@dataclass(frozen=True)
class Letter:
    char: str
    form: str  # Arabic: isolated|initial|medial|final; English: capital|small
    width: float  # design box width; the box starts at x = 0
    guides: Guides
    strokes: tuple[Stroke, ...]
    dots: tuple[Point, ...] = ()
    dot_r: float = 0.0

    @property
    def rtl(self) -> bool:
        return "؀" <= self.char <= "ۿ"


# ب isolated: from the top of the right tooth down, along the bowl to the left, up into the tail; the dot
# below the middle comes last.
BA = Letter(
    "ب",
    "isolated",
    200,
    Guides(top=30, base=97),
    (Stroke("M176 36 C177 56 180 78 169 88 C159 96 147 97 130 97 L62 97 C42 97 27 93 22 70"),),
    dots=((100, 124),),
    dot_r=8,
)

# A: left slant down, right slant down, crossbar left to right on the midline.
CAPITAL_A = Letter(
    "A",
    "capital",
    100,
    Guides(top=10, base=110, mid=60),
    (Stroke("M50 10 L18 110"), Stroke("M50 10 L82 110"), Stroke("M34 60 L66 60")),
)

# a (print): circle back from two o'clock, then the stem from the midline down to the base line.
SMALL_A = Letter(
    "a",
    "small",
    100,
    Guides(top=10, base=110, mid=60),
    (
        Stroke(
            "M67.68 67.32 C62.99 62.63 56.63 60 50 60 C36.19 60 25 71.19 25 85 C25 98.81 36.19 110 50 110 "
            "C63.81 110 75 98.81 75 85 C75 78.37 72.37 72.01 67.68 67.32"
        ),
        Stroke("M75 60 L75 110"),
    ),
)

LETTERS: dict[tuple[str, str], Letter] = {(x.char, x.form): x for x in (BA, CAPITAL_A, SMALL_A)}


def letter(char: str, form: str) -> Letter:
    try:
        return LETTERS[(char, form)]
    except KeyError:
        raise KeyError(f"no stroke data yet for {char!r} ({form}); see qamra_workbook.strokes") from None
