"""Qamra's kindergarten hand for Arabic: one simple naskh-like print style with the same lines and
proportions for every letter. Every path is our own hand-placed control points; nothing comes from a font.

Units are the letter's own, y grows downwards (as in SVG). The lines:

- TOP  = -25: the ascender line; ا ل ك ط ظ and لا reach it;
- MID  =  36: the tooth line; the teeth of ب ت ث ن ي and the tallest heads reach it;
- BASE =  97: the base line; letters sit on it and connected forms join on it;
- LOW  = 158: the descender line; tails and bowls stay above it.

How the letters are written (the educator confirms these on the review sheet):

- isolated and initial forms start at the letter's own start: the top of the first tooth or stem, the
  head of ج ح خ ع غ, the neck of a loop;
- medial and final forms start at the right join: the pen arrives along the line from the previous letter;
- in medial and final forms a tooth or a stem goes up and comes back down (a narrow spike);
- loops go up from their neck and turn clockwise;
- marks (the stick of ط ظ, the head of the medial kaf, the kaf mark, the hamza) come after the body, then
  the dots, right to left.

Join points sit on the base line at the edges of the box: (width, BASE) on the right, (0, BASE) on the left,
so forms placed box to box meet exactly.
"""

from __future__ import annotations

from collections.abc import Iterable

from qamra_workbook.geometry import Point, Stroke
from qamra_workbook.letters.model import Guides, Letter

TOP = -25.0
MID = 36.0
BASE = 97.0
LOW = 158.0
GUIDES = Guides(top=TOP, base=BASE, mid=MID, low=LOW)

DOT_R = 8.0
DOT_GAP = 28.0  # centre to centre: two dots never touch, even drawn big for finger tracing
ABOVE = BASE - 30  # dots above a flat body (ت ث isolated and final, ق ف heads use their own)
OVER_TOOTH = MID - 22  # dots above a tooth
BELOW = BASE + 27  # dots below a flat body or a tooth

FORMS = ("isolated", "initial", "medial", "final")
NON_CONNECTING = ("isolated", "final")  # ا د ذ ر ز و (and ة ى لا): they never join on their left


def one(x: float, y: float) -> tuple[Point, ...]:
    return ((x, y),)


def two(x: float, y: float) -> tuple[Point, ...]:
    """Two dots side by side, right one first."""
    return ((x + DOT_GAP / 2, y), (x - DOT_GAP / 2, y))


def three(x: float, y: float) -> tuple[Point, ...]:
    """Two dots side by side (right one first), then one on top of them."""
    return (*two(x, y), (x, y - DOT_GAP * 0.85))


def _letter(
    char: str,
    form: str,
    width: float,
    strokes: Iterable[str],
    dots: tuple[Point, ...],
    *,
    right: bool,
    left: bool,
) -> Letter:
    return Letter(
        char,
        form,
        width,
        GUIDES,
        tuple(Stroke(d) for d in strokes),
        dots,
        DOT_R,
        join_right=(width, BASE) if right else None,
        join_left=(0.0, BASE) if left else None,
    )


def isolated(char: str, width: float, *strokes: str, dots: tuple[Point, ...] = ()) -> Letter:
    return _letter(char, "isolated", width, strokes, dots, right=False, left=False)


def initial(char: str, width: float, *strokes: str, dots: tuple[Point, ...] = ()) -> Letter:
    """Joins the next letter on its left."""
    return _letter(char, "initial", width, strokes, dots, right=False, left=True)


def medial(char: str, width: float, *strokes: str, dots: tuple[Point, ...] = ()) -> Letter:
    """Joins on both sides; the first stroke starts at the right join."""
    return _letter(char, "medial", width, strokes, dots, right=True, left=True)


def final(char: str, width: float, *strokes: str, dots: tuple[Point, ...] = ()) -> Letter:
    """Joins the previous letter on its right; the first stroke starts at the right join."""
    return _letter(char, "final", width, strokes, dots, right=True, left=False)
