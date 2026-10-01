"""Activity books (Addendum 9, WorkbookProduct): who can order what.

`orderable` is a product flag in `CatalogProduct.features`, switched in Admin → الكتالوج (products tab).
Every product is on sale (Tareq reviewed every page himself, 2026-09-30), so a product with no flag is
orderable. The admin can close one; the cart then refuses it, whichever page sent it.
"""

import re
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from qamra_core.db.store import CatalogProduct

ACTIVITY = ("workbook", "journey", "family")


def orderable(product: CatalogProduct) -> bool:
    flag = (product.features or {}).get("orderable")
    return True if flag is None else bool(flag)


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
