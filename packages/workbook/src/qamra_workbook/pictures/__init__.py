"""The workbook picture library: tagged vocabulary pictures in color and line-art (for coloring).

Pages ask a `PictureStore` for a picture by id. `LibraryStore` draws the programmatic SVG placeholders;
`ImageDirStore` serves approved AI pictures from `content/workbook/images/<id>.<style>.png` (Addendum 5 §4)
and falls back to the placeholder, so AI pictures can replace placeholders one at a time. Puzzles that edit
or compose pictures (spot-the-difference, scenes) always use the vector drawings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from markupsafe import Markup, escape

from qamra_workbook.pictures.household import HOUSEHOLD
from qamra_workbook.pictures.icons import PICTURES as VOCABULARY
from qamra_workbook.pictures.journey_words import JOURNEY_WORDS
from qamra_workbook.pictures.model import OUTLINE, Part, Picture, Style, strip_tashkeel
from qamra_workbook.pictures.workbook_words import WORKBOOK_WORDS
from qamra_workbook.pictures.workbook_words_2 import WORKBOOK_WORDS_2

# the vocabulary pictures (Addenda 5–6) and the family book's kitchen, market and home things (Addendum 7),
# and the letter words of «دوسية التأسيس» (Addendum 5)
PICTURES: dict[str, Picture] = VOCABULARY | HOUSEHOLD | WORKBOOK_WORDS | WORKBOOK_WORDS_2
# «رحلتي الأولى» stage 1's extra words (Addendum 6): a picture drawn elsewhere under the same id wins
for _id, _picture in JOURNEY_WORDS.items():
    PICTURES.setdefault(_id, _picture)

__all__ = [
    "OUTLINE",
    "PICTURES",
    "ImageDirStore",
    "LibraryStore",
    "Part",
    "Picture",
    "PictureStore",
    "Style",
    "by_category",
    "find_ar",
    "get",
]


def get(picture_id: str) -> Picture:
    try:
        return PICTURES[picture_id]
    except KeyError:
        raise KeyError(f"no picture {picture_id!r} in the library") from None


def by_category(category: str) -> list[Picture]:
    return [pic for pic in PICTURES.values() if pic.category == category]


def find_ar(word: str) -> Picture | None:
    """Look a picture up by its Arabic word, with or without tashkeel."""
    bare = strip_tashkeel(word)
    return next((pic for pic in PICTURES.values() if strip_tashkeel(pic.word_ar) == bare), None)


class PictureStore(Protocol):
    def markup(self, picture_id: str, style: Style = "color", css_class: str = "pic") -> Markup: ...


class LibraryStore:
    """The programmatic SVG pictures."""

    def markup(self, picture_id: str, style: Style = "color", css_class: str = "pic") -> Markup:
        return get(picture_id).svg(style, css_class=css_class)


class ImageDirStore:
    """Approved raster pictures (300 DPI at their printed size) with the SVG library as the fallback."""

    def __init__(self, root: Path, fallback: PictureStore | None = None) -> None:
        self.root = root
        self.fallback = fallback or LibraryStore()

    def path(self, picture_id: str, style: Style) -> Path | None:
        found = self.root / f"{picture_id}.{style}.png"
        return found if found.is_file() else None

    def markup(self, picture_id: str, style: Style = "color", css_class: str = "pic") -> Markup:
        found = self.path(picture_id, style)
        if found is None:
            return self.fallback.markup(picture_id, style, css_class)
        return Markup('<img class="{}" src="{}" alt="">').format(escape(css_class), found.resolve().as_uri())
