"""English letters for tracing: print (ball-and-stick) capitals and small letters, single strokes in the usual
kindergarten writing order, with the dots of i and j last.

Units: the capital height is 100 (top line 10, base line 110), small letters reach the midline (60) and the
descender line (150). An educator signs off on the stroke directions with the Arabic letters.
"""

from __future__ import annotations

from qamra_workbook.geometry import Stroke, bounds
from qamra_workbook.letters.model import Guides, Letter

GUIDES = Guides(top=10, base=110, mid=60, low=150)
DOT_R = 7.0

# the circle of a, d, g, q: back from two o'clock, round to the left and up again
BALL = (
    "M67.68 67.32 C62.99 62.63 56.63 60 50 60 C36.19 60 25 71.19 25 85 C25 98.81 36.19 110 50 110 "
    "C63.81 110 75 98.81 75 85 C75 78.37 72.37 72.01 67.68 67.32"
)

CAPITALS: dict[str, tuple[str, ...]] = {  # draft: educator review (stroke order and direction)
    "A": ("M50 10 L18 110", "M50 10 L82 110", "M34 60 L66 60"),
    "B": (
        "M20 10 L20 110",
        "M20 10 L50 10 C66 10 74 20 74 35 C74 50 66 60 50 60 L20 60",
        "M20 60 L55 60 C72 60 80 71 80 85 C80 99 72 110 55 110 L20 110",
    ),
    "C": ("M82 28 C74 16 63 10 50 10 C29 10 14 32 14 60 C14 88 29 110 50 110 C63 110 74 104 82 92",),
    "D": ("M20 10 L20 110", "M20 10 L45 10 C70 10 84 32 84 60 C84 88 70 110 45 110 L20 110"),
    "E": ("M20 10 L20 110", "M20 10 L75 10", "M20 60 L65 60", "M20 110 L75 110"),
    "F": ("M20 10 L20 110", "M20 10 L75 10", "M20 60 L65 60"),
    "G": (
        "M82 28 C74 16 63 10 50 10 C29 10 14 32 14 60 C14 88 29 110 50 110 C68 110 82 98 84 80 L84 64 L58 64",
    ),
    "H": ("M20 10 L20 110", "M80 10 L80 110", "M20 60 L80 60"),
    "I": ("M50 10 L50 110", "M30 10 L70 10", "M30 110 L70 110"),
    "J": ("M66 10 L66 84 C66 101 57 110 44 110 C31 110 23 102 20 90",),
    "K": ("M20 10 L20 110", "M78 10 L20 70", "M40 50 L80 110"),
    "L": ("M22 10 L22 110 L76 110",),
    "M": ("M14 110 L14 10", "M14 10 L50 76 L86 10 L86 110"),
    "N": ("M20 110 L20 10", "M20 10 L80 110 L80 10"),
    "O": ("M50 10 C27 10 12 32 12 60 C12 88 27 110 50 110 C73 110 88 88 88 60 C88 32 73 10 50 10",),
    "P": ("M20 10 L20 110", "M20 10 L50 10 C68 10 78 21 78 37 C78 53 68 64 50 64 L20 64"),
    "Q": (
        "M50 10 C27 10 12 32 12 60 C12 88 27 110 50 110 C73 110 88 88 88 60 C88 32 73 10 50 10",
        "M60 86 L88 116",
    ),
    "R": ("M20 10 L20 110", "M20 10 L50 10 C68 10 78 21 78 37 C78 53 68 64 50 64 L20 64", "M48 64 L80 110"),
    "S": (
        "M80 26 C74 15 63 10 50 10 C33 10 22 19 22 33 C22 48 36 54 50 59 C66 64 80 71 80 87 "
        "C80 102 67 110 50 110 C35 110 24 104 18 94",
    ),
    "T": ("M50 10 L50 110", "M16 10 L84 10"),
    "U": ("M18 10 L18 74 C18 97 31 110 50 110 C69 110 82 97 82 74 L82 10",),
    "V": ("M14 10 L50 110 L86 10",),
    "W": ("M6 10 L27 110 L50 38 L73 110 L94 10",),
    "X": ("M16 10 L84 110", "M84 10 L16 110"),
    "Y": ("M14 10 L50 60", "M86 10 L50 60 L50 110"),
    "Z": ("M16 10 L84 10 L16 110 L84 110",),
}

SMALL: dict[str, tuple[str, ...]] = {
    "a": (BALL, "M75 60 L75 110"),
    "b": (
        "M22 10 L22 110",
        "M22 85 C22 71 33 60 47 60 C61 60 72 71 72 85 C72 99 61 110 47 110 C33 110 22 99 22 85",
    ),
    "c": ("M70 68 C65 63 57 60 48 60 C34 60 23 71 23 85 C23 99 34 110 48 110 C57 110 65 107 70 102",),
    "d": (BALL, "M75 10 L75 110"),
    "e": ("M24 85 L73 85 C73 71 62 60 48 60 C34 60 24 71 24 85 C24 99 35 110 49 110 C59 110 67 106 72 99",),
    "f": ("M70 18 C66 12 60 10 54 10 C44 10 38 17 38 28 L38 110", "M22 60 L60 60"),
    "g": (BALL, "M75 60 L75 130 C75 144 65 150 50 150 C39 150 30 146 25 139"),
    "h": ("M22 10 L22 110", "M22 80 C26 68 35 60 47 60 C61 60 70 68 70 82 L70 110"),
    "i": ("M40 60 L40 110",),
    "j": ("M52 60 L52 132 C52 144 45 150 35 150 C28 150 22 147 18 141",),
    "k": ("M22 10 L22 110", "M66 58 L22 92", "M38 80 L70 110"),
    "l": ("M36 10 L36 110",),
    "m": (
        "M14 60 L14 110",
        "M14 77 C16 66 23 60 31 60 C41 60 47 66 47 77 L47 110",
        "M47 77 C49 66 56 60 64 60 C74 60 80 66 80 77 L80 110",
    ),
    "n": ("M22 60 L22 110", "M22 79 C25 67 34 60 46 60 C60 60 70 68 70 82 L70 110"),
    "o": ("M48 60 C34 60 23 71 23 85 C23 99 34 110 48 110 C62 110 73 99 73 85 C73 71 62 60 48 60",),
    "p": (
        "M22 60 L22 150",
        "M22 85 C22 71 33 60 47 60 C61 60 72 71 72 85 C72 99 61 110 47 110 C33 110 22 99 22 85",
    ),
    "q": (BALL, "M75 60 L75 150"),
    "r": ("M22 60 L22 110", "M22 81 C26 68 35 60 47 60 C55 60 61 63 65 68"),
    "s": (
        "M66 67 C62 62 56 60 48 60 C37 60 29 65 29 73 C29 81 38 84 48 86 C59 88 68 91 68 99 "
        "C68 106 60 110 48 110 C38 110 31 107 26 101",
    ),
    "t": ("M40 22 L40 99 C40 106 44 110 51 110 C57 110 61 108 64 105", "M22 60 L60 60"),
    "u": ("M22 60 L22 87 C22 101 32 110 46 110 C59 110 70 101 70 87", "M70 60 L70 110"),
    "v": ("M18 60 L45 110 L72 60",),
    "w": ("M8 60 L27 110 L46 70 L65 110 L84 60",),
    "x": ("M22 60 L70 110", "M70 60 L22 110"),
    "y": ("M18 60 L45 108", "M72 60 L32 150"),
    "z": ("M22 60 L70 60 L22 110 L70 110",),
}
SMALL_DOTS = {"i": ((40.0, 40.0),), "j": ((52.0, 40.0),)}


def _letter(char: str, form: str, strokes: tuple[str, ...]) -> Letter:
    parsed = tuple(Stroke(d) for d in strokes)
    x0, _, x1, _ = bounds(list(parsed))
    dots = SMALL_DOTS.get(char, ())
    return Letter(char, form, x1 + x0, GUIDES, parsed, dots, DOT_R if dots else 0.0)


LATIN: dict[tuple[str, str], Letter] = {
    **{(c, "capital"): _letter(c, "capital", s) for c, s in CAPITALS.items()},
    **{(c, "small"): _letter(c, "small", s) for c, s in SMALL.items()},
}


def latin(char: str) -> Letter:
    """The letter as written: a capital for A–Z, a small letter for a–z."""
    return LATIN[(char, "capital" if char.isupper() else "small")]
