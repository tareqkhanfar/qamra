"""What the page engine renders: a book of page specs for one child, independent of the product.

«رحلتي الأولى للتعلّم» pages come from `journey.JourneyPage` (`from_journey`), «مغامراتي مع عائلتي» pages from
`family.Placed` (`from_family`); «دوسية التأسيس» pages will come from `curriculum.Page` the same way. Titles
and instructions may use `{child}` for the name and `{masc/fem}` variants (the storybook theme convention),
resolved for the child's gender. A family book also resolves `{adult}`, `{member}`, `{family_name}` and
`{city}` from its `Family` (Addendum 7 §7).

Numerals (decision 2026-09-28 §4): a book prints Hindi numerals (١٢٣) on its Arabic and math pages by default,
or Latin numerals (123) when the parent asks (`BookSpec.numerals`); English pages always print 123. Every
number a page prints goes through `BookSpec.num` (builders: `PageContext.num`, templates: `p.num`, or
`book.num` for the book's Arabic furniture), which calls `format_number`.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from qamra_pdf.arabic_names import fill_name
from qamra_workbook.family import SKILLS, FamilyPlan, Placed, book_pages
from qamra_workbook.journey import JourneyPage

Lang = Literal["ar", "en"]
Gender = Literal["m", "f"]
Side = Literal["left", "right"]
Where = Literal["home", "outside"]
Numerals = Literal["hindi", "latin"]  # ١٢٣ or 123
# how a family member is drawn until the illustrated-family add-on replaces the figures (A7 §7)
Figure = Literal["woman", "man", "grandma", "grandpa", "girl", "boy", "baby", "adult", "child"]

_VARIANT = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")
_PLACEHOLDER = re.compile(r"\{[a-z_]+(?::acc|:gen)?\}")  # `{child}`, `{child:acc}`, `{child:gen}`
_HINDI = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
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


#: The placeholders the parent's own words fill: the child's name (Arabic and English), a family member, the
#: family's name, the city. Whatever the parent typed counts as one word for the word limits. A name in the
#: accusative is marked `{child:acc}` (`qamra_pdf.arabic_names`: «ساعِدْ أبا بكر»), after «يا» it needs no mark;
#: a name in the genitive is marked `{child:gen}` («لِأبي بكر», «رِحْلَةُ أبي بكر»).
NAME_SLOTS = (
    "{child}",
    "{child:acc}",
    "{child:gen}",
    "{name_en}",
    "{adult}",
    "{adult:acc}",
    "{adult:gen}",
    "{member}",
    "{member:acc}",
    "{member:gen}",
    "{family_name}",
    "{city}",
)
_NAME_UNIT = "اسم"  # one word standing in for a name while counting


def instruction_words(text: str, gender: Gender) -> int:
    """How many words a child-facing text has as printed, for the word limits (≤ 7 in an instruction): the
    book's own words in the child's gender, and each name one unit however many words the parent typed
    («عبد الرحمن», «نور الهدى», «أبو بكر», a 20-letter name, «أم أحمد»). The limit keeps the book's own
    sentences short; a long or compound name never makes a page too long, so it never refuses an order."""
    for slot in NAME_SLOTS:
        text = text.replace(slot, _NAME_UNIT)
    return len(_VARIANT.sub(lambda m: m.group(1 if gender == "m" else 2), text).split())


def format_number(value: int | str, numerals: Numerals = "hindi") -> str:
    """The one place digits are written: every digit of `value` (a number, or a text with numbers in it) as
    Hindi numerals (١٢٣) or Latin numerals (123), whichever way it was written."""
    return str(value).translate(_HINDI if numerals == "hindi" else _LATIN)


def arabic_date(day: dt.date, numerals: Numerals = "hindi") -> str:
    return (
        f"{format_number(day.day, numerals)} {MONTHS_AR[day.month - 1]} {format_number(day.year, numerals)}"
    )


def minutes_ar(n: int, numerals: Numerals = "hindi") -> str:
    """«١٠ دقائق», «١٥ دقيقة»: the counted noun agrees with the number."""
    if n == 1:
        return "دقيقة"
    if n == 2:
        return "دقيقتان"
    return f"{format_number(n, numerals)} {'دقائق' if 3 <= n <= 10 else 'دقيقة'}"


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


# The sizes a product can print at, chosen by one setting: the family book follows the printer's wire-o and
# cutting templates, 21 × 28 cm or A4, with the same templates (Tareq's decision 5, 28 Sep 2026).
PRODUCT_SIZES: dict[str, dict[str, Geometry]] = {
    "family": {"21x28": Geometry(trim_w=210.0, trim_h=280.0), "a4": Geometry(trim_w=210.0, trim_h=297.0)},
}


def product_geometry(product: str, size: str | None = None) -> Geometry:
    """The product's print size: its default, or one of its `PRODUCT_SIZES` by name."""
    if size is None:
        return PRODUCT_GEOMETRY.get(product, Geometry())
    sizes = PRODUCT_SIZES.get(product, {})
    if size not in sizes:
        raise ValueError(f"{product} prints at {sorted(sizes) or 'its default size'}, not {size!r}")
    return sizes[size]


@dataclass(frozen=True)
class Child:
    name: str
    gender: Gender
    character_sheet: Path | None = None  # front view + two poses on plain paper

    def personalize(self, text: str) -> str:
        """`{masc/fem}` for the child's gender, then the name: «يا {child}» and `{child:acc}` print the
        accusative («يا أبا بكر», `qamra_pdf.arabic_names`), `{child:gen}` the genitive («لِأبي بكر»), every
        other `{child}` the name as typed."""
        text = _VARIANT.sub(lambda m: m.group(1 if self.gender == "m" else 2), text)
        return fill_name(text, "child", self.name)


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
GRANDPARENT = "grandparent"  # a page's `adult`/`member` param: a grandparent, by whatever name, when there is one


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
_WOMEN: frozenset[Figure] = frozenset({"woman", "grandma", "girl"})
_MEN: frozenset[Figure] = frozenset({"man", "grandpa", "boy"})


def you_suffix(member: Member | None) -> str:
    """The «you» suffix said to `member`: «كِ» to a woman, «كَ» to a man, a bare «ك» when the role does not say."""
    if member is None:
        return "ك"
    return "كِ" if member.drawn_as in _WOMEN else "كَ" if member.drawn_as in _MEN else "ك"


# The family's city is optional (the order flow's family step). Without it a text never prints «سوق » with
# nothing after it: the child's vowelized texts say «مَدينَتِنا» (the book speaks with the family), the
# parents' plain texts «مدينتكم». The passport's city field stays empty, to fill in by hand.
CITY_FALLBACK_VOWELIZED = "مَدينَتِنا"
CITY_FALLBACK_PLAIN = "مدينتكم"
# A text is the child's vowelized register when it carries short vowels or sukun. The parents' plain texts
# carry tanween and shadda too («طريقًا آمنًا»، «تحبّهم») and the odd helping vowel («نفَسًا»).
_SHORT_VOWELS = re.compile(r"[َُِْ]")
VOWELIZED_MIN = 3


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
        if wanted == GRANDPARENT:  # whatever the family calls them: ستّي، تيتا، سيدو، جدّي…
            elders = [m for m in among if m.drawn_as in ("grandma", "grandpa")]
            if elders:
                return elders[key % len(elders)]
        return among[key % len(among)]

    def city_in(self, text: str) -> str:
        """The city as `text` prints it: the family's, else the fallback in the text's own register."""
        if self.city.strip():
            return self.city.strip()
        vowelized = len(_SHORT_VOWELS.findall(text)) >= VOWELIZED_MIN
        return CITY_FALLBACK_VOWELIZED if vowelized else CITY_FALLBACK_PLAIN

    def personalize(self, text: str, key: int = 0, adult: str = "", member: str = "") -> str:
        grown_up = self.pick(self.adults, key, adult)
        anyone = self.pick(self.members, key, member)
        # a member's name takes the accusative after «يا» and at `{adult:acc}` («نُخْبِرُ أبا أحمد»), the
        # genitive at `{adult:gen}` («مَعَ أبي أحمد»); the family's name is a surname and prints as typed
        # («عائلة أبو غوش»)
        text = text.replace("{family_name}", self.name).replace("{city}", self.city_in(text))
        # `{adult:k}`: «you» said to that grown-up («طُفولَتُ{adult:k}» → «طُفولَتُكِ» to تيتا, «طُفولَتُكَ» to سيدو)
        text = text.replace("{adult:k}", you_suffix(grown_up))
        text = fill_name(text, "adult", grown_up.label if grown_up else NO_ADULT)
        return fill_name(text, "member", anyone.label if anyone else NO_ADULT)


@dataclass(frozen=True)
class ActivityTags:
    """The family book's activity icons (A7 §5): at home or outside, with the family, minutes, levels."""

    where: Where = "home"
    together: bool = False  # «هيا نفعلها معًا!»
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
    # Hindi numerals (١٢٣) by default; a parent may ask for Latin ones (123) (A5 §5, decision 2026-09-28 §4)
    numerals: Numerals = "hindi"
    audio_base: str = "https://qamra.app/a/"
    geometry: Geometry = field(default_factory=Geometry)
    family: Family | None = None  # the family book's family (A7 §7)

    def side(self, number: int) -> Side:
        """Which hand the page is on in the open book (its outer edge carries the section tab)."""
        first: Side = "left" if self.binding == "right" else "right"
        other: Side = "right" if first == "left" else "left"
        return first if number % 2 else other

    def numerals_for(self, lang: Lang = "ar") -> Numerals:
        """The numerals text in `lang` prints: English is always 123; Arabic (and math) follows the book."""
        return "latin" if lang == "en" else self.numerals

    def num(self, value: int | str, lang: Lang = "ar") -> str:
        """A number as printed in text of language `lang` (the page's language for its content, Arabic for
        the book's own furniture: page numbers, the section chip, the answer key)."""
        return format_number(value, self.numerals_for(lang))

    def folio(self, number: int) -> str:
        """The page number: one style for the whole book, English pages included."""
        return self.num(number)

    def date_ar(self) -> str:
        return arabic_date(self.date, self.numerals)

    def audio_url(self, page: PageSpec) -> str:
        """The page's QR link: its audio item's code (the journey's `journey_book`), else its id."""
        return f"{self.audio_base}{page.params.get('audio_code') or page.id}"

    def words(self, text: str) -> int:
        """`instruction_words` for this child's gender."""
        return instruction_words(text, self.child.gender)

    def personalize(self, text: str, page: PageSpec | None = None) -> str:
        """The text as printed for this child (and family): a page may name the grown-up (`adult`) or the
        member (`member`) its mission is with; otherwise they go round the family by page number. The
        `{masc/fem}` variants are chosen first, so a name sees the word before it («{اسْأَلْ/اسْأَلي} {adult}»:
        «اسْأَلِ الحاجَّ», the helping vowel of `arabic_names.fill_name`)."""
        text = _VARIANT.sub(lambda m: m.group(1 if self.child.gender == "m" else 2), text)
        if self.family is not None:
            params = page.params if page is not None else {}
            text = self.family.personalize(
                text,
                page.number if page is not None else 0,
                str(params.get("adult", "")),
                str(params.get("member", "")),
            )
        text = self.child.personalize(text)
        if page is not None and "{name_en}" in text:  # an English page greets the child by their Latin name
            text = text.replace("{name_en}", str(page.params.get("name_en") or self.child.name))
        return text


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


# the icon an opening spread shows for an activity, by the type of its first page
OPENER_ICONS = {
    "scavenger-hunt": "magnifier",
    "drawing": "crayon",
    "counting": "abacus",
    "sort-choose": "puzzle",
    "observation-journal": "eye",
    "conversation-cards": "talk",
    "price-tags": "shop",
    "shopping-list": "cart",
    "recipe-steps": "chef",
    # the whole family book's page types (W7)
    "sequence-cards": "pattern",
    "routine-builder": "clock",
    "picture-talk": "eye",
    "feelings-faces": "heart",
    "situation-feeling-match": "puzzle",
    "feelings-thermometer": "heart",
    "story-finish": "book",
    "chore-chart": "check-list",
    "nature-bingo": "leaf",
    "interview-template": "speaker",
    "family-game-cards": "dice",
}


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
        if page.type == "section-opener":  # «في هذه المغامرة»: the adventure's first activities
            ahead = [
                a for a in plan.activities if a.section == section.id and a.pages[0].type != "memory-page"
            ]
            # each title names the grown-up of the activity's own first page («مُقابَلَةٌ مَعَ {adult:gen}»
            # previews the interview with the person the interview page names, a man or a woman alike)
            first: dict[str, Placed] = {}
            for placed_page in book_pages(plan):
                if placed_page.activity is not None:
                    first.setdefault(placed_page.activity.id, placed_page)
            params.setdefault(
                "inside",
                [
                    {
                        "icon": OPENER_ICONS.get(a.pages[0].type, "star"),
                        "text": a.title,
                        "page": first[a.id].n if a.id in first else 0,
                        **{k: v for k, v in a.pages[0].params.items() if k in ("adult", "member")},
                    }
                    for a in ahead[:3]
                ],
            )
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
