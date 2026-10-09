"""The child's name on the activity books' name pages: which Arabic names can be traced in Qamra's hand, and
which English spellings the English name page can trace (order-flows plan §d chunk 9).

Light on purpose (no page engine, no fonts): the API checks a name at order time with `can_trace` and
`clean_latin_name`, and the name pages (`render.pages.workbook_front`) use the same rules when they draw.

**Arabic (the «اسمي» tracing page):**
- The tracing hand has the 28 letters, ة ى ء and the لا ligature, plus أ إ آ ؤ ئ (the alif, waw and the
  dotless ya with a small hamza or madda mark). Those are the traceable letters (`TRACEABLE_AR`).
- A name is cleaned before it is checked: tashkeel and the tatweel (ـ) go, presentation forms become plain
  letters (NFKC), the Persian ی and ک become ي and ك, and spaces collapse. A hyphen counts as a space.
- A name is traceable (`can_trace`) when it has at least one word and every letter of every word is
  traceable. Compound names («نور الهدى», «عبد الرحمن») are traced word by word with a gap between them.
- Long names: the row traces as many parts of the name, from the start, as fit at a cap height of at least
  `MIN_CAP_MM`. A part is a word, or a compound kept whole (`name_parts`: «عبد الرحمن», «أبو بكر», «نور
  الهدى», «سيف الدين»). The first part is always traced; a single long part shrinks to fit, never overflows.
- Never a crash: a word with a letter the hand does not have (Latin «Sara», digits, emoji) is left out of the
  tracing. When no word is left, the page prints the name as a model in the book's type and gives empty
  writing lines; the order job flags the book `name_not_traceable` for the reviewer.

**Printed names (every page and cover):** the name prints as typed. A box it does not fit even at its
smallest size shows its shorter forms in turn (`shorter_names`: the last parts dropped, a compound never cut),
a page whose work area overflows while it names the child does the same on the whole page, and the family's
game tables use the name the family calls the child by (`call_name`). The word limits count a name as one
word (`render.spec.instruction_words`). A long or compound name never refuses an order.

**English (the English name page):** the parent's spelling, `^[A-Za-z][A-Za-z' -]{0,39}$` after accents are
dropped (é → e). Spaces and hyphens leave a gap; apostrophes are not traced. A long English name is traced
like an Arabic one: as many words from the start as fit at `MIN_CAP_MM`, at least the first.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# the letters of Qamra's tracing hand (qamra_workbook.letters.ALPHABET) and the hamza seats drawn with a mark
BASE_LETTERS = frozenset("ابتثجحخدذرزسشصضطظعغفقكلمنهويةىء")
HAMZA_SEATS = frozenset("أإآؤئ")
TRACEABLE_AR = BASE_LETTERS | HAMZA_SEATS
MIN_CAP_MM = 14.0  # the smallest letters a 4–6-year-old traces comfortably (cap height on the name row)
MAX_NAME_EN = 40

_TASHKEEL = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")  # marks, tatweel
_INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")  # joiners, direction marks
_PERSIAN = str.maketrans({"ی": "ي", "ک": "ك", "ە": "ه", "ۀ": "ه", "ٱ": "ا"})  # Persian letters, alif wasla
_LATIN_NAME = re.compile(r"^[A-Za-z][A-Za-z' -]{0,39}$")


def clean_arabic(name: str) -> str:
    """The name as the tracing hand reads it: no tashkeel or tatweel, plain letters, single spaces."""
    text = unicodedata.normalize("NFKC", name or "")
    text = _INVISIBLE.sub("", text).translate(_PERSIAN)
    text = _TASHKEEL.sub("", text).replace("-", " ").replace("\u2010", " ")
    return " ".join(text.split())


@dataclass(frozen=True)
class NameCheck:
    """What the Arabic name page can do with a name."""

    name: str  # cleaned
    words: tuple[str, ...]  # every word of the cleaned name
    traceable_words: tuple[str, ...]  # the words made only of traceable letters, in order
    unsupported: tuple[str, ...]  # the characters the hand cannot trace, once each

    @property
    def traceable(self) -> bool:
        """Every word can be traced (what the API checks at order time)."""
        return bool(self.words) and not self.unsupported


def check_name(name: str) -> NameCheck:
    cleaned = clean_arabic(name)
    words = tuple(cleaned.split())
    unsupported = sorted({c for w in words for c in w if c not in TRACEABLE_AR})
    traceable = tuple(w for w in words if all(c in TRACEABLE_AR for c in w))
    return NameCheck(cleaned, words, traceable, tuple(unsupported))


# a word that always goes with the next one («عبد الله», «أبو بكر», «أم كلثوم»)
_JOINS_NEXT = frozenset({"عبد", "أبو", "ابو", "أبي", "ابي", "أم", "ام"})


def name_parts(words: tuple[str, ...] | list[str]) -> list[str]:
    """The words grouped into the parts a name is never cut inside: «عبد» and «أبو» take the next word, and a
    word with «ال» joins the one before it («نور الهدى», «سيف الدين»)."""
    parts: list[list[str]] = []
    for w in words:
        if parts and (w.startswith("ال") or parts[-1][-1] in _JOINS_NEXT):
            parts[-1].append(w)
        else:
            parts.append([w])
    return [" ".join(p) for p in parts]


def shorter_names(name: str) -> list[str]:
    """The name with its last parts dropped one at a time, longest first, never cutting a compound
    («محمد عبد الرحمن أحمد محمود العلي» → «محمد عبد الرحمن أحمد», «محمد عبد الرحمن», «محمد»). The print
    engine falls back to them, in order, in a box the full name does not fit even at its smallest size
    (`render.engine._FIT_JS`), so a long name shows as many whole parts as fit and never refuses an order."""
    parts = name_parts(name.split())
    return [" ".join(parts[:n]) for n in range(len(parts) - 1, 0, -1)]


CALL_NAME_LETTERS = 12  # the most letters a short label (a game's score table) shows of a long name


def call_name(name: str, letters: int = CALL_NAME_LETTERS) -> str:
    """The name the family calls the child by, for narrow labels (the game tables): whole parts from the start
    while they fit in `letters` letters, at least the first part («محمد عبد الرحمن أحمد العلي» → «محمد»,
    «عبد الرحمن» and «نور الهدى» stay whole). Spaces and tashkeel are kept as typed."""
    parts = name_parts(name.split())
    if not parts:
        return name.strip()
    taken = parts[:1]
    for part in parts[1:]:
        if len(clean_arabic(" ".join([*taken, part])).replace(" ", "")) > letters:
            break
        taken.append(part)
    return " ".join(taken)


def can_trace(name: str) -> bool:
    """True when the «اسمي» page can trace every word of the name in Arabic letters (a long name may be traced
    by its first parts only; that is still traceable). The API refuses an untraceable name for the books with
    a name-tracing page, with «اكتبوا الاسم بالحروف العربية فقط، لأن طفلكم سيتتبّعه حرفًا حرفًا.»"""
    return check_name(name).traceable


def clean_latin_name(value: str | None) -> str | None:
    """The parent's English spelling, tidied (accents dropped, single spaces), or None when it is not a name
    in English letters (digits, symbols, Arabic letters, longer than 40)."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = " ".join(text.replace("’", "'").split())
    return text if _LATIN_NAME.fullmatch(text) else None


def latin_words(name: str) -> list[str]:
    """The words the English name page traces: the letters A–Z and a–z only (accents dropped), split at spaces
    and hyphens."""
    text = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return [w for w in (re.sub("[^A-Za-z]", "", part) for part in re.split(r"[\s-]+", text)) if w]
