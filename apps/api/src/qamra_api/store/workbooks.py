"""Activity books (Addendum 9, WorkbookProduct): who can order what.

`orderable` is a product flag in `CatalogProduct.features`, switched in Admin → الكتالوج (products tab).
Every product is on sale (Tareq reviewed every page himself, 2026-09-30), so a product with no flag is
orderable. The admin can close one; the cart then refuses it, whichever page sent it.
"""

import importlib
import re
import unicodedata
import uuid
from collections.abc import Callable, Iterable
from functools import cache
from types import ModuleType
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import Character
from qamra_core.db.store import ArtStyle, CatalogProduct

ACTIVITY = ("workbook", "journey", "family", "islamic")  # islamic: «قلبي يعرف الله» (Addendum 10)


def orderable(product: CatalogProduct) -> bool:
    flag = (product.features or {}).get("orderable")
    return True if flag is None else bool(flag)


# ---- what an activity book needs from the child (docs/plans/order-flows.md §c.3, chunk 8) ------------------
# The flow asks only what the book prints. These rules are the data the wizard's steps come from
# (`GET /api/shop/workbooks/needs`); the cart checks the same rules when a line gets its child.

# The Arabic name is traced letter by letter (the «اسمي» pages): «دوسية التأسيس» and «رحلتي الأولى».
TRACES_NAME = ("workbook", "journey")
# The English name page: the line → None (every variant) or (option, the values that have the page).
# «دوسية التأسيس»: every volume (content/workbook/curriculum/*.yaml, `name-trace` with `script: en`);
# «رحلتي الأولى»: stages 2 and 3, so the set too (packages/workbook journey_book).
NAME_EN: dict[str, tuple[str, frozenset[str]] | None] = {
    "workbook": None,
    "journey": ("stage", frozenset({"2", "3", "set"})),
}
FAMILY_LINES = ("family",)  # the «عائلة …» step: the family's name, city and members
# The ages each variant is made for (the review step's non-blocking check): the line → (option, value → ages);
# option None: one range for the whole line.
AGES: dict[str, tuple[str | None, dict[str, tuple[int, int]]]] = {
    "workbook": ("level", {"kg1": (4, 5), "kg2": (5, 6)}),
    "journey": ("stage", {"1": (3, 4), "2": (4, 5), "3": (5, 6), "set": (3, 6)}),
    "family": (None, {"": (3, 7)}),  # Addendum 7: ages 3–7
    "islamic": (
        "volume",
        {
            **dict.fromkeys(("V1", "V2", "L1"), (4, 6)),
            **dict.fromkeys(("V3", "V4", "V5", "L2"), (6, 8)),
            **dict.fromkeys(("R", "set"), (4, 8)),
        },
    ),
}


def needs_name_en(line: str, options: dict[str, str]) -> bool:
    if line not in NAME_EN:
        return False
    rule = NAME_EN[line]
    return rule is None or str(options.get(rule[0], "")) in rule[1]


def asks_family(line: str) -> bool:
    return line in FAMILY_LINES


def ages_for(line: str, options: dict[str, str]) -> tuple[int, int] | None:
    rule = AGES.get(line)
    if rule is None:
        return None
    option, ranges = rule
    return ranges.get("" if option is None else str(options.get(option, "")))


def accepted_styles(styles: Iterable[ArtStyle], line: str) -> list[str]:
    """The styles a character can be in for this line (`ArtStyle.lines`, active styles), in the site's order:
    the first is the one a new character is drawn in (3D)."""
    return [s.slug for s in sorted(styles, key=lambda s: (s.sort, s.slug)) if line in (s.lines or [])]


async def reusable_character(db: AsyncSession, child_id: uuid.UUID, styles: list[str]) -> Character | None:
    """The newest approved character of the child in one of `styles` (never a coloring one)."""
    if not styles:
        return None
    return (
        await db.execute(
            select(Character)
            .where(
                Character.child_id == child_id,
                Character.approved_at.is_not(None),
                Character.art_style.in_(styles),
            )
            .order_by(Character.approved_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


# ---- the child's names, as the tracing pages write them --------------------------------------------------
# The rules are the engine's (`qamra_workbook.names`, chunk 9: a light module, no page engine), so the order
# is refused for exactly the names the «اسمي» page could not trace. The local rules below are the fallback
# for an install without the engine: the hand's letters before chunk 9 (no ؤ or ئ).

LATIN_NAME = re.compile(r"[A-Za-z][A-Za-z' -]{0,39}")  # chunk 3's rule: English letters, space, ' and -
_MARKS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")  # tashkeel and the tatweel
_TRACEABLE = frozenset("ابتثجحخدذرزسشصضطظعغفقكلمنهويةىءأإآ")


@cache
def _names() -> ModuleType | None:
    try:
        return importlib.import_module("qamra_workbook.names")
    except ImportError:
        return None


def _engine(function: str) -> Callable[..., Any] | None:
    found = getattr(_names(), function, None)
    return found if callable(found) else None


def tracing_engine() -> bool:
    """Whether the engine's name rules are used (else the local fallback)."""
    return _engine("can_trace") is not None


def clean_latin(value: str) -> str:
    """The English name as the English name page traces it, tidied; ValueError unless in English letters."""
    tidy = _engine("clean_latin_name")
    if tidy is not None:
        cleaned = tidy(value)
        if not cleaned:
            raise ValueError("name_en")
        return str(cleaned)
    text = " ".join(value.split())
    if not LATIN_NAME.fullmatch(text):
        raise ValueError("name_en")
    return text


def _words(name: str) -> list[str]:
    clean = _engine("clean_arabic")
    text = str(clean(name)) if clean is not None else _MARKS.sub("", name).replace("-", " ")
    return text.split()


def arabic_letters_only(name: str) -> bool:
    letters = "".join(_words(name))
    return bool(letters) and all(unicodedata.name(c, "").startswith("ARABIC LETTER") for c in letters)


def can_trace(name: str) -> bool:
    """Whether the «اسمي» page can trace every word of the name."""
    check = _engine("can_trace")
    if check is not None:
        return bool(check(name))
    letters = "".join(_words(name))
    return bool(letters) and all(c in _TRACEABLE for c in letters)


NameProblem = Literal["not_arabic", "not_traceable"]


def name_problem(line: str, name: str) -> NameProblem | None:
    """Why this book can't trace the child's name: not Arabic letters, or a letter the pages don't write."""
    if line not in TRACES_NAME:
        return None
    if not arabic_letters_only(name):
        return "not_arabic"
    return None if can_trace(name) else "not_traceable"


def line_gaps(line: str, options: dict[str, str], personalization: dict[str, Any]) -> list[str]:
    """What a cart line that has its child still lacks for this book (the cart says «ينقصه…» and checkout
    waits): `name_en` (the English name page) or `name` (a name the tracing pages can't write)."""
    gaps = []
    name = str(personalization.get("child_name") or "")
    if name and name_problem(line, name):
        gaps.append("name")
    if needs_name_en(line, options) and not personalization.get("name_en"):
        gaps.append("name_en")
    return gaps


# ---- «مغامراتي مع عائلتي»: the family the parent gives with the book (A7 §7) -------------------------------
# Only first names and the relation the child calls them by (never photos): they appear in the missions,
# the parent boxes, «عائلتي», the scoreboard and the certificate. Everything is optional; without it the
# book is drawn for the child with one neutral grown-up (the worker's `family_book.family_of`).

# the relation → the word printed in the book (the engine draws the figure from it) and whether it is a
# grown-up (who does the missions with the child)
RELATIONS: dict[str, tuple[str, bool]] = {
    "mother": ("ماما", True),
    "father": ("بابا", True),
    "grandmother": ("ستّي", True),
    "grandfather": ("سيدي", True),
    "maternal-aunt": ("خالتي", True),
    "paternal-aunt": ("عمّتي", True),
    "maternal-uncle": ("خالي", True),
    "paternal-uncle": ("عمّي", True),
    "brother": ("أخي", False),
    "sister": ("أختي", False),
    "baby": ("البيبي", False),
    "other": ("من العائلة", True),
}
MAX_FAMILY = 6  # A7 §7, and what the book's pages hold (the family picture, the table, the scoreboard)
# a name is words: no links, addresses, numbers or template braces
_NOT_A_NAME = re.compile(r"https?:|www\.|://|@|\.[a-z]{2,}\b|[0-9٠-٩{}<>\\/\[\]]", re.IGNORECASE)


def _clean_name(value: str) -> str:
    text = " ".join(value.split())
    if _NOT_A_NAME.search(text):
        raise ValueError("letters only: a first name, a family name or a city")
    return text


Name = Annotated[str, AfterValidator(_clean_name)]


class FamilyMemberIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relation: Literal[
        "mother",
        "father",
        "grandmother",
        "grandfather",
        "maternal-aunt",
        "paternal-aunt",
        "maternal-uncle",
        "paternal-uncle",
        "brother",
        "sister",
        "baby",
        "other",
    ]
    name: Name = Field(default="", max_length=20)  # the first name only; empty: the book says the relation
    adult: bool | None = None  # grown-up or child; defaults from the relation
    scarf: bool = False  # draw a headscarf on this member's figure (the family's choice)


class FamilyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name = Field(default="", max_length=30)  # «عائلة …»
    city: Name = Field(default="", max_length=30)
    members: list[FamilyMemberIn] = Field(default_factory=list, max_length=MAX_FAMILY)


def family_personalization(family: FamilyIn) -> dict[str, Any]:
    """What the order item keeps for the book (`personalization["family"]`)."""
    return {
        "name": family.name,
        "city": family.city,
        "members": [
            {
                "relation": m.relation,
                "role": RELATIONS[m.relation][0],
                "name": m.name,
                "adult": RELATIONS[m.relation][1] if m.adult is None else m.adult,
                "scarf": m.scarf,
            }
            for m in family.members
        ],
    }
