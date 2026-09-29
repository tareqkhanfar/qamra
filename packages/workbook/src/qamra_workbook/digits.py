"""Digits for tracing: Hindi numerals (٠١٢٣٤٥٦٧٨٩, the book's default) and Latin numerals (0123456789, the
parent's option and English pages), single strokes with the writing order a kindergarten teaches.

The same lines as the English capitals: top 10, base 110 (a digit is as tall as a capital). The Hindi zero is
a small ring in the middle of the line, as children write it. An educator signs off on the directions.
"""

from __future__ import annotations

from typing import Literal

from qamra_workbook.geometry import Stroke, bounds
from qamra_workbook.letters.model import Guides, Letter

GUIDES = Guides(top=10, base=110, mid=60)

HINDI: dict[str, tuple[str, ...]] = {  # draft: educator review (stroke order and direction)
    # ٠: a small ring on the midline, round to the left from the top
    "٠": ("M50 44 C40 44 33 52 33 61 C33 70 40 78 50 78 C60 78 67 70 67 61 C67 52 60 44 50 44",),
    # ١: straight down
    "١": ("M50 10 L50 110",),
    # ٢: from the right tip down into the tooth, up to the left tip, then straight down
    "٢": ("M74 8 C72 22 64 29 55 27 C47 25 43 18 42 11 L42 110",),
    # ٣: the same with two teeth
    "٣": ("M80 8 C79 20 74 26 67 25 C61 24 58 18 57 12 C56 21 51 27 44 26 C38 25 35 19 35 12 L35 110",),
    # ٤: a small curve at the top, back to the middle, then a big curve down and out to the right
    "٤": ("M70 18 C58 6 34 12 34 29 C34 43 48 51 62 51 C44 51 27 63 27 81 C27 101 50 113 76 106",),
    # ٥: a teardrop on the base line: from its top point down the left side, round and up the right side
    "٥": ("M50 38 C39 50 26 64 26 83 C26 100 37 110 50 110 C63 110 74 100 74 83 C74 64 61 50 50 38",),
    # ٦: the little hook at the top from the left, then down the stem
    "٦": ("M26 16 C38 22 52 21 64 10 L64 110",),
    # ٧: down from the top left to the bottom, and up to the top right
    "٧": ("M20 10 L50 110 L80 10",),
    # ٨: up from the bottom left to the top, and down to the bottom right
    "٨": ("M20 110 L50 10 L80 110",),
    # ٩: the loop first, then down the stem
    "٩": ("M62 34 C62 20 53 11 42 11 C30 11 22 20 23 31 C24 42 34 49 46 48 C56 47 62 41 62 34 L62 110",),
}

LATIN: dict[str, tuple[str, ...]] = {
    "0": ("M50 10 C31 10 20 33 20 60 C20 87 31 110 50 110 C69 110 80 87 80 60 C80 33 69 10 50 10",),
    "1": ("M32 28 L50 10 L50 110",),
    "2": ("M24 32 C26 18 37 10 50 10 C64 10 76 19 76 34 C76 52 60 66 24 110 L80 110",),
    "3": (
        "M24 22 C30 14 40 10 50 10 C64 10 74 18 74 32 C74 46 63 56 48 56 C64 56 78 66 78 82 "
        "C78 99 65 110 49 110 C37 110 27 104 22 96",
    ),
    "4": ("M58 10 L20 78 L84 78", "M66 42 L66 110"),
    "5": (
        "M30 10 L28 52 C36 46 44 44 52 44 C68 44 78 56 78 76 C78 97 64 110 48 110 C36 110 27 104 22 96",
        "M30 10 L76 10",
    ),
    "6": (
        "M72 18 C66 12 58 10 50 10 C32 10 22 36 22 68 C22 94 34 110 50 110 C66 110 78 98 78 82 "
        "C78 66 66 56 51 56 C38 56 27 63 22 74",
    ),
    "7": ("M20 10 L80 10 L40 110",),
    "8": (
        "M72 30 C72 18 62 10 50 10 C38 10 28 18 28 30 C28 42 38 50 50 58 C63 66 76 74 76 88 "
        "C76 101 64 110 50 110 C36 110 24 101 24 88 C24 74 37 66 50 58 C62 50 72 42 72 30",
    ),
    "9": ("M76 36 C76 21 65 10 50 10 C35 10 24 21 24 36 C24 51 35 62 50 62 C65 62 76 51 76 36 L76 110",),
}


def _digit(char: str, strokes: tuple[str, ...]) -> Letter:
    parsed = tuple(Stroke(d) for d in strokes)
    x0, _, x1, _ = bounds(list(parsed))
    return Letter(char, "digit", x1 + x0, GUIDES, parsed)


DIGITS: dict[str, Letter] = {c: _digit(c, s) for c, s in (HINDI | LATIN).items()}


_HINDI = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def digit_shapes(value: int | str, numerals: Literal["hindi", "latin"] = "hindi") -> list[Letter]:
    """The digits of `value` in the page's numerals (as `render.spec.format_number` prints them), in reading
    order: numbers read left to right in both."""
    return [DIGITS[c] for c in str(value).translate(_HINDI if numerals == "hindi" else _LATIN)]
