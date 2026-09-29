"""Letter stroke data for tracing pages: single-stroke paths in writing order, plus the letter's dots.

Arabic: every letter in each of its forms (isolated/initial/medial/final), plus ة ى ء and لا, in Qamra's
own kindergarten hand (`qamra_workbook.letters`). English: A–Z and a–z in print (`qamra_workbook.latin`; the
samples A and a below keep their original guides). Digits live in `qamra_workbook.digits`. An educator
signs off on the forms and stroke directions
(Addendum 5 §8, Addendum 6 §9) on the review sheet from `qamra_workbook.stroke_sheet`.
"""

from __future__ import annotations

from qamra_workbook.geometry import Stroke
from qamra_workbook.latin import LATIN
from qamra_workbook.letters import ARABIC
from qamra_workbook.letters.model import Guides, Letter

__all__ = ["BA", "CAPITAL_A", "LETTERS", "SMALL_A", "Guides", "Letter", "letter"]

# ب isolated: from the top of the right tooth down, along the bowl to the left, up into the tail; the dot
# below the middle comes last.
BA = ARABIC[("ب", "isolated")]

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

LETTERS: dict[tuple[str, str], Letter] = {
    **ARABIC,
    **LATIN,
    **{(x.char, x.form): x for x in (CAPITAL_A, SMALL_A)},
}


def letter(char: str, form: str) -> Letter:
    try:
        return LETTERS[(char, form)]
    except KeyError:
        raise KeyError(f"no stroke data yet for {char!r} ({form}); see qamra_workbook.strokes") from None
