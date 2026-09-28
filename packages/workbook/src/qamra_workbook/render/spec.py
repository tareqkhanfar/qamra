"""What the page engine renders: a book of page specs for one child, independent of the product.

«رحلتي الأولى للتعلّم» pages come from `journey.JourneyPage` (`from_journey`), «مغامراتي مع عائلتي» pages from
`family.Placed` (`from_family`); «دوسية التأسيس» pages will come from `curriculum.Page` the same way. Titles
and instructions may use `{child}` for the name and `{masc/fem}` variants (the storybook theme convention),
resolved for the child's gender. A family book also resolves `{adult}`, `{member}`, `{family_name}` and
`{city}` from its `Family` (Addendum 7 §7).
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from qamra_workbook.family import SKILLS, FamilyPlan, Placed
from qamra_workbook.journey import JourneyPage

Lang = Literal["ar", "en"]
Gender = Literal["m", "f"]
Side = Literal["left", "right"]
Where = Literal["home", "outside"]
# how a family member is drawn until the illustrated-family add-on replaces the figures (A7 §7)
Figure = Literal["woman", "man", "grandma", "grandpa", "girl", "boy", "baby", "adult"]

_VARIANT = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")
_PLACEHOLDER = re.compile(r"\{[a-z_]+\}")
_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
_TASHKEEL = re.compile(r"[ً-ٰٟ]")
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


def minutes_ar(n: int) -> str:
    """«١٠ دقائق», «١٥ دقيقة»: the counted noun agrees with the number."""
    if n == 1:
        return "دقيقة"
    if n == 2:
        return "دقيقتان"
    return f"{arabic_digits(n)} {'دقائق' if 3 <= n <= 10 else 'دقيقة'}"


def leftover_placeholders(text: str) -> list[str]:
    """Placeholders that personalization did not resolve (a page never prints `{adult}`)."""
    return _PLACEHOLDER.findall(text)


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


# The trim of each product line: the workbooks are A4, the family book 21 × 28 cm portrait (A7 §3.6).
PRODUCT_GEOMETRY: dict[str, Geometry] = {
    "foundation": Geometry(),
    "journey": Geometry(),
    "family": Geometry(trim_w=210.0, trim_h=280.0),
}


def product_geometry(product: str) -> Geometry:
    return PRODUCT_GEOMETRY.get(product, Geometry())


@dataclass(frozen=True)
class Child:
    name: str
    gender: Gender
    character_sheet: Path | None = None  # front view + two poses on plain paper

    def personalize(self, text: str) -> str:
        text = _VARIANT.sub(lambda m: m.group(1 if self.gender == "m" else 2), text)
        return text.replace("{child}", self.name)


# The role a parent types → the placeholder figure (tashkeel ignored); anything else is drawn as "adult".
ROLE_FIGURES: dict[str, Figure] = {
    **dict.fromkeys(("ماما", "أمي", "امي", "الأم", "خالتو", "خالتي", "عمتو", "عمتي"), "woman"),
    **dict.fromkeys(("بابا", "أبي", "ابي", "الأب", "خالو", "خالي", "عمو", "عمي"), "man"),
    **dict.fromkeys(("ستي", "تيتا", "جدتي", "ستو", "نانا"), "grandma"),
    **dict.fromkeys(("سيدي", "جدي", "جدو", "سيدو"), "grandpa"),
    **dict.fromkeys(("أختي", "أخت", "اختي"), "girl"),
    **dict.fromkeys(("أخي", "أخ", "اخي", "أخوي"), "boy"),
    **dict.fromkeys(("البيبي", "بيبي", "الرضيع", "أخي الصغير", "أختي الصغيرة"), "baby"),
}
ADULT_FIGURES: frozenset[Figure] = frozenset({"woman", "man", "grandma", "grandpa", "adult"})
NO_ADULT = "أحد الكبار"  # {adult} when the family lists no grown-up


@dataclass(frozen=True)
class Member:
    """A family member as the parent entered them: the role the child calls them by, and maybe a name."""

    role: str  # ماما، بابا، ستّي، أخي…
    name: str = ""  # «كرم»; empty when the child calls them by the role
    figure: Figure | None = None  # the placeholder drawing; default from the role
    scarf: bool = False  # the family chose a headscarf for this member's figure

    @property
    def label(self) -> str:
        """What the page prints: the name when there is one, else the role."""
        return self.name or self.role

    @property
    def drawn_as(self) -> Figure:
        return self.figure or ROLE_FIGURES.get(_TASHKEEL.sub("", self.role).strip(), "adult")

    @property
    def is_adult(self) -> bool:
        return self.drawn_as in ADULT_FIGURES


MAX_MEMBERS = 6  # A7 §7


@dataclass(frozen=True)
class Family:
    """The child's family (A7 §7): who does the missions with them, and where they live."""

    name: str  # the family name: «عائلة {family_name}»
    members: tuple[Member, ...]
    city: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("the family needs a name")
        if not 1 <= len(self.members) <= MAX_MEMBERS:
            raise ValueError(f"a family lists 1–{MAX_MEMBERS} members, not {len(self.members)}")

    @property
    def adults(self) -> tuple[Member, ...]:
        return tuple(m for m in self.members if m.is_adult)

    def pick(self, among: tuple[Member, ...], key: int, prefer: str = "") -> Member | None:
        """`prefer` (a role or a name) when the family has them, else a member chosen by `key` (the page
        number), so the missions go round the family instead of always naming the same person."""
        if not among:
            return None
        wanted = _TASHKEEL.sub("", prefer).strip()
        for m in among:
            if wanted and wanted in (_TASHKEEL.sub("", m.role).strip(), _TASHKEEL.sub("", m.name).strip()):
                return m
        return among[key % len(among)]

    def personalize(self, text: str, key: int = 0, adult: str = "", member: str = "") -> str:
        grown_up = self.pick(self.adults, key, adult)
        anyone = self.pick(self.members, key, member)
        return (
            text.replace("{family_name}", self.name)
            .replace("{city}", self.city)
            .replace("{adult}", grown_up.label if grown_up else NO_ADULT)
            .replace("{member}", anyone.label if anyone else NO_ADULT)
        )


@dataclass(frozen=True)
class ActivityTags:
    """The family book's activity icons (A7 §5): at home or outside, with the family, minutes, levels."""

    where: Where = "home"
    together: bool = False  # «هيا نفعلها معاً!»
    minutes: int | None = None
    challenge: bool = False  # a ⭐⭐ version (ages 5–7) next to the ⭐ one (ages 3–4)


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
    parent: tuple[str, ...] = ()  # the «للأهل» box (A7 §5): 1–3 short lines for the grown-up
    activity: ActivityTags | None = None  # the activity icons (family book)

    @property
    def seed(self) -> int | str:
        seed = self.params.get("seed", self.id)
        return seed if isinstance(seed, int | str) else str(seed)

    @property
    def dir(self) -> str:
        return "rtl" if self.lang == "ar" else "ltr"


@dataclass(frozen=True)
class BookSpec:
    product: str  # "journey" | "foundation" | "family"
    title_ar: str
    child: Child
    pages: tuple[PageSpec, ...]
    date: dt.date
    binding: Side = "right"  # Arabic books open from the right: page 1 is a left-hand page
    digits: Lang = "ar"  # page numbers: Arabic-Indic (٠١٢٣) or Western (0123), a parent's choice (A5 §5)
    audio_base: str = "https://qamra.app/a/"
    geometry: Geometry = field(default_factory=Geometry)
    family: Family | None = None  # the family book's family (A7 §7)

    def side(self, number: int) -> Side:
        """Which hand the page is on in the open book (its outer edge carries the section tab)."""
        first: Side = "left" if self.binding == "right" else "right"
        other: Side = "right" if first == "left" else "left"
        return first if number % 2 else other

    def folio(self, number: int) -> str:
        return arabic_digits(number) if self.digits == "ar" else str(number)

    def audio_url(self, page: PageSpec) -> str:
        return f"{self.audio_base}{page.id}"

    def personalize(self, text: str, page: PageSpec | None = None) -> str:
        """The text as printed for this child (and family): a page may name the grown-up (`adult`) or the
        member (`member`) its mission is with; otherwise they go round the family by page number."""
        if self.family is not None:
            params = page.params if page is not None else {}
            text = self.family.personalize(
                text,
                page.number if page is not None else 0,
                str(params.get("adult", "")),
                str(params.get("member", "")),
            )
        return self.child.personalize(text)


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


def family_page_id(number: int) -> str:
    return f"family-p{number}"


def from_family(placed: Placed, plan: FamilyPlan) -> PageSpec:
    """A family plan page as an engine page: the activity's icons, skills and safety note come along, and an
    opening spread gets its adventure number and passport stamp from the section."""
    page, activity = placed.page, placed.activity
    params = dict(page.params)
    order = [s.id for s in plan.sections]
    if placed.section in order:
        section = plan.sections[order.index(placed.section)]
        params.setdefault("badge", section.badge)
        params.setdefault("adventure", order.index(section.id) + 1)
    tags = None
    if activity is not None:
        tags = ActivityTags(
            activity.where, activity.together, activity.minutes, activity.levels.challenge is not None
        )
        if activity.safety:
            params.setdefault("safety", activity.safety)
    return PageSpec(
        id=family_page_id(placed.n),
        type=page.type,
        number=placed.n,
        section=placed.section,
        title=page.title,
        instruction=page.instruction,
        skill="، ".join(SKILLS[k] for k in activity.skills if k in SKILLS) if activity else "",
        params=params,
        parent=tuple(page.parent),
        activity=tags,
    )
