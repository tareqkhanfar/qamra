"""The four books of «دفاتر التلوين والرسم» (the store's `colorbook` line) and how each prints.

Fixed content, personalized only on the cover (the child's name, and the child's character when the family
has one) plus the title page and «عن قمرة». No AI cost per order: the line art is drawn in code
(docs/plans/coloring-books.md).

Binding (decision 2026-10-21, docs/decisions.md):
- the three coloring books are saddle-stitched (stapled): A4 portrait, 32 / 28 / 24 pages on 160 g uncoated
  paper (pencils, coloured pencils and crayons; felt pens may show through a little), a 300 g card cover;
  a stapled book needs a page count that is a multiple of 4;
- «دَفْتَري» is Wire-O (it opens flat to draw on): A4 portrait, 48 pages on 160 g paper, a 300 g card cover;
  wire-o needs an even count (we keep a multiple of 4 too).

The store sells a printed copy (`format: softcover` for the stapled books, `format: spiral` for wire-o: the
formats every print path already knows) and a PDF to print at home (`format: digital`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LINE = "colorbook"  # the store's product line (≤ 16 characters)
TitleKey = Literal["letters", "palestine", "ramadan", "sketchbook"]
Binding = Literal["stapled", "wire-o"]


@dataclass(frozen=True)
class Title:
    key: TitleKey
    slug: str  # the store product
    name_ar: str  # vowelized, as on the cover
    name_plain: str  # as the store and the «عن قمرة» page print it
    name_en: str
    binding: Binding
    pages: int  # interior pages, the info page included
    signature: int = 4  # the page count is a multiple of this

    @property
    def printed_format(self) -> str:
        return "spiral" if self.binding == "wire-o" else "softcover"


TITLES: dict[str, Title] = {
    "letters": Title(
        "letters", "coloring-letters", "أُلَوِّنُ حُروفي", "ألوّن حروفي", "I Color My Letters", "stapled", 32
    ),
    "palestine": Title(
        "palestine", "coloring-palestine", "أُلَوِّنُ فِلَسْطينَ", "ألوّن فلسطين", "I Color Palestine", "stapled", 28
    ),
    "ramadan": Title(
        "ramadan", "coloring-ramadan", "أُلَوِّنُ رَمَضانَ", "ألوّن رمضان", "I Color Ramadan", "stapled", 24
    ),
    "sketchbook": Title("sketchbook", "sketchbook", "دَفْتَري", "دفتري", "My Sketchbook", "wire-o", 48),
}
BY_SLUG: dict[str, Title] = {t.slug: t for t in TITLES.values()}


def title_of(key_or_slug: str) -> Title:
    found = TITLES.get(key_or_slug) or BY_SLUG.get(key_or_slug)
    if found is None:
        raise KeyError(f"no coloring title {key_or_slug!r} (have {sorted(TITLES)})")
    return found
