"""Arabic letters for tracing, in Qamra's own kindergarten hand (see `hand` for the lines and the writing
rules): every letter in each of its forms, with strokes in writing order, dots and join points.

- `ARABIC[(char, form)]`: the registry (`qamra_workbook.strokes.LETTERS` adds the English samples);
- `ALPHABET`, `NAMES`, `EXPECTED`, `HOW`: the letters in alphabet order, their Arabic names, their
  forms and how each is written (in Arabic, for the educator's review sheet);
- `word(text)`: the forms that spell a word; `placed(letters)`: where each box goes, right to left, so the
  join points meet.

One module per family of letters that share a body: ba (ب ت ث ن ي), jeem (ج ح خ), dal (د ذ), ra (ر ز),
seen (س ش), sad (ص ض), tah (ط ظ), ain (ع غ), fa (ف ق), kaf (ك ل), meem (م), ha (ه ة), waw (و),
alif (ا لا), hamza (ء ى).
"""

from __future__ import annotations

from qamra_workbook.letters import ain, alif, ba, dal, fa, ha, hamza, jeem, kaf, meem, ra, sad, seen, tah, waw
from qamra_workbook.letters.hand import FORMS, NON_CONNECTING
from qamra_workbook.letters.model import Letter

FAMILIES = (ba, jeem, dal, ra, seen, sad, tah, ain, fa, kaf, meem, ha, waw, alif, hamza)

ARABIC: dict[tuple[str, str], Letter] = {(x.char, x.form): x for f in FAMILIES for x in f.LETTERS}
HOW: dict[str, str] = {char: text for f in FAMILIES for char, text in f.HOW.items()}

ALPHABET = (*"ابتثجحخدذرزسشصضطظعغفقكلمنهوي", "ة", "ى", "ء", "لا")
NAMES = dict(
    zip(
        ALPHABET,
        (
            *("الألف", "الباء", "التاء", "الثاء", "الجيم", "الحاء", "الخاء", "الدال", "الذال", "الراء"),
            *("الزاي", "السين", "الشين", "الصاد", "الضاد", "الطاء", "الظاء", "العين", "الغين", "الفاء"),
            *("القاف", "الكاف", "اللام", "الميم", "النون", "الهاء", "الواو", "الياء", "التاء المربوطة"),
            *("الألف المقصورة", "الهمزة", "لام ألف"),
        ),
        strict=True,
    )
)
LEFT_OPEN = frozenset(("ا", "د", "ذ", "ر", "ز", "و", "ة", "ى", "ء", "لا"))  # never join the next letter
RIGHT_OPEN = frozenset(("ء",))  # never joins the previous letter either
EXPECTED: dict[str, tuple[str, ...]] = {
    c: ("isolated",) if c in RIGHT_OPEN else NON_CONNECTING if c in LEFT_OPEN else FORMS for c in ALPHABET
}
_FORM = {(False, False): "isolated", (False, True): "initial", (True, True): "medial", (True, False): "final"}


def word(text: str) -> list[Letter]:
    """The forms that spell `text` (letters only, no harakat): each letter joins its neighbours unless one
    of them never joins that side. ل followed by ا is the لا ligature."""
    chars: list[str] = []
    for c in text:
        if c == "ا" and chars and chars[-1] == "ل":
            chars[-1] = "لا"
        else:
            chars.append(c)
    out = []
    for i, c in enumerate(chars):
        joins_prev = i > 0 and chars[i - 1] not in LEFT_OPEN and c not in RIGHT_OPEN
        joins_next = i + 1 < len(chars) and c not in LEFT_OPEN and chars[i + 1] not in RIGHT_OPEN
        out.append(ARABIC[(c, _FORM[(joins_prev, joins_next)])])
    return out


def placed(letters: list[Letter], gap: float = 0.0) -> tuple[list[float], float]:
    """The x of each letter's box when they are written right to left, box to box (plus `gap` after a
    letter that does not join the next), and the total width. Join points meet: they sit on the box edges."""
    xs: list[float] = []
    right = 0.0
    for i, x in enumerate(letters):
        if i and letters[i - 1].join_left is None:
            right -= gap
        right -= x.width
        xs.append(right)
    return [x - right for x in xs], -right
