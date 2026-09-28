"""The page-type registry: each page type is a builder plus a template.

    @page_type("maze")
    def maze(ctx: PageContext) -> Built: ...        # → templates/pages/maze.html.j2

A builder turns the page spec into template data, an answer key (for puzzle pages) and the results of the
page's automated checks. Pages whose checks fail are never rendered.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from markupsafe import Markup

from qamra_workbook.pictures import PictureStore, Style
from qamra_workbook.puzzles.base import rng
from qamra_workbook.render.sections import SectionStyle, section_style
from qamra_workbook.render.spec import BookSpec, Numerals, PageSpec

# mission: title + instruction + work area; full: the page lays itself out; sheet: an insert printed on its
# own paper (sticker sheet, card stock), without section tab or page number
Frame = Literal["mission", "full", "sheet"]


@dataclass(frozen=True)
class Assets:
    pictures: PictureStore
    character: Path | None = None  # the cut-out front view (render.character.front_view)
    character_aspect: float = 0.47  # width / height
    wave: Path | None = None  # the waving pose, when the sheet has one (render.character.pose)
    wave_aspect: float = 0.6


@dataclass
class Built:
    data: dict[str, Any]
    answer: list[str] | None = None  # the answer in words, for the parents' answer key
    problems: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PageContext:
    page: PageSpec
    book: BookSpec
    assets: Assets

    @property
    def style(self) -> SectionStyle:
        return section_style(self.page.section, self.book.product)

    def rng(self, salt: str = "") -> random.Random:
        return rng(self.page.seed, salt)

    def pic(self, picture_id: str, style: Style = "color", css_class: str = "pic") -> Markup:
        return self.assets.pictures.markup(picture_id, style, css_class)

    def text(self, value: str) -> str:
        """A text as printed on this page: personalized, with its numbers in the page's numerals."""
        return self.num(self.book.personalize(value, self.page))

    @property
    def numerals(self) -> Numerals:
        """This page's numerals: the book's choice, or Latin (123) on an English page."""
        return self.book.numerals_for(self.page.lang)

    def num(self, value: int | str) -> str:
        """A number on this page, in its numerals (`BookSpec.num`)."""
        return self.book.num(value, self.page.lang)


Builder = Callable[[PageContext], Built]


@dataclass(frozen=True)
class PageType:
    name: str
    build: Builder
    frame: Frame = "mission"

    @property
    def template(self) -> str:
        return f"pages/{self.name}.html.j2"


REGISTRY: dict[str, PageType] = {}


def page_type(name: str, *, frame: Frame = "mission") -> Callable[[Builder], Builder]:
    def register(build: Builder) -> Builder:
        if name in REGISTRY:
            raise ValueError(f"page type {name!r} is registered twice")
        REGISTRY[name] = PageType(name, build, frame)
        return build

    return register


def lookup(name: str) -> PageType:
    try:
        return REGISTRY[name]
    except KeyError:
        known = ", ".join(sorted(REGISTRY))
        raise KeyError(f"page type {name!r} is not in the engine yet (have: {known})") from None
