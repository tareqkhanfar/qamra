"""What the page engine renders: a book of page specs for one child, independent of the product.

«رحلتي الأولى للتعلّم» pages come from `journey.JourneyPage` (`from_journey`); «دوسية التأسيس» pages will
come from `curriculum.Page` the same way. Titles and instructions may use `{child}` for the name and
`{masc/fem}` variants (the storybook theme convention), resolved for the child's gender.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from qamra_workbook.journey import JourneyPage

Lang = Literal["ar", "en"]
Gender = Literal["m", "f"]
Side = Literal["left", "right"]

_VARIANT = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")
_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
MONTHS_AR = (
    "كانون الثاني",
    "شباط",
    "آذار",
    "نيسان",
    "أيار",
    "حزيران",
    "تموز",
    "آب",
    "أيلول",
    "تشرين الأول",
    "تشرين الثاني",
    "كانون الأول",
)


def arabic_digits(value: int | str) -> str:
    return str(value).translate(_DIGITS)


def arabic_date(day: dt.date) -> str:
    return f"{arabic_digits(day.day)} {MONTHS_AR[day.month - 1]} {arabic_digits(day.year)}"


@dataclass(frozen=True)
class Geometry:
    """A4 portrait with bleed (Addendum 5 §4): sizes in mm."""

    trim_w: float = 210.0
    trim_h: float = 297.0
    bleed: float = 3.0
    safe: float = 12.0  # inside the trim
    dpi: int = 300

    @property
    def page_w(self) -> float:
        return self.trim_w + 2 * self.bleed

    @property
    def page_h(self) -> float:
        return self.trim_h + 2 * self.bleed

    @property
    def inset(self) -> float:
        """Safe area from the page (bleed) edge."""
        return self.bleed + self.safe


@dataclass(frozen=True)
class Child:
    name: str
    gender: Gender
    character_sheet: Path | None = None  # front view + two poses on plain paper

    def personalize(self, text: str) -> str:
        text = _VARIANT.sub(lambda m: m.group(1 if self.gender == "m" else 2), text)
        return text.replace("{child}", self.name)


@dataclass(frozen=True)
class PageSpec:
    id: str  # stable: seeds, QR links and file names come from it
    type: str
    number: int  # the printed page number
    section: str
    title: str
    instruction: str
    lang: Lang = "ar"
    instruction_en: str = ""  # English pages carry the instruction in both languages
    stage: int | None = None
    skill: str = ""
    audio: bool = False
    example: bool = False
    params: Mapping[str, Any] = field(default_factory=dict)

    @property
    def seed(self) -> int | str:
        seed = self.params.get("seed", self.id)
        return seed if isinstance(seed, int | str) else str(seed)

    @property
    def dir(self) -> str:
        return "rtl" if self.lang == "ar" else "ltr"


@dataclass(frozen=True)
class BookSpec:
    product: str  # "journey" | "foundation"
    title_ar: str
    child: Child
    pages: tuple[PageSpec, ...]
    date: dt.date
    binding: Side = "right"  # Arabic books open from the right: page 1 is a left-hand page
    digits: Lang = "ar"  # page numbers: Arabic-Indic (٠١٢٣) or Western (0123), a parent's choice (A5 §5)
    audio_base: str = "https://qamra.app/a/"
    geometry: Geometry = field(default_factory=Geometry)

    def side(self, number: int) -> Side:
        """Which hand the page is on in the open book (its outer edge carries the section tab)."""
        first: Side = "left" if self.binding == "right" else "right"
        other: Side = "right" if first == "left" else "left"
        return first if number % 2 else other

    def folio(self, number: int) -> str:
        return arabic_digits(number) if self.digits == "ar" else str(number)

    def audio_url(self, page: PageSpec) -> str:
        return f"{self.audio_base}{page.id}"


def journey_page_id(stage: int, number: int) -> str:
    return f"journey-s{stage}-p{number}"


def from_journey(page: JourneyPage, stage: int) -> PageSpec:
    """A journey plan page as an engine page. Engine-only keys ride in params: `lang` and `instruction_en`
    for English pages, `seed` for puzzles (default: the page id)."""
    params = dict(page.params)
    lang = params.pop("lang", "ar")
    if lang not in ("ar", "en"):
        raise ValueError(f"page {page.n}: lang must be ar or en")
    return PageSpec(
        id=journey_page_id(stage, page.n),
        type=page.type,
        number=page.n,
        section=page.section,
        title=page.title,
        instruction=page.instruction,
        lang=lang,
        instruction_en=str(params.pop("instruction_en", "")),
        stage=stage,
        skill=page.skill,
        audio=page.audio,
        example=page.example,
        params=params,
    )
