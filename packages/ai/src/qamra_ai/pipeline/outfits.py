"""What the child wears on the character sheet: the outfit catalogue (`content/outfits.yaml`).

The parent picks one before the character is drawn (owner, 2026-10-20). The id is stored on the character;
the sheet prompt gets the look's `prompt`, the portrait its `top`, and a girl's hijab follows the outfit.
Story books wear it on the theme's everyday scene groups (`everyday_groups`); scene costumes stay. The
default («الأساسي») is the neutral reference outfit drawn before, unchanged, and books keep their own
everyday clothes for it.
"""

import re
from functools import cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from qamra_ai.pipeline.models import Gender
from qamra_ai.pipeline.theme import CONTENT_DIR

OUTFITS_FILE = "outfits.yaml"
DEFAULT_OUTFIT = "classic"
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

Shape = Literal["tee", "shirt", "hoodie", "cardigan", "stripes", "pinafore", "dress", "thobe", "vest"]


def _hex(v: str | None) -> str | None:
    if v is not None and not _HEX.match(v):
        raise ValueError(f"not a #RRGGBB colour: {v!r}")
    return v


class Swatch(BaseModel):
    """The picker's drawn swatch (web `lib/outfits.ts`): a shape and its colours."""

    shape: Shape
    top: str
    bottom: str
    shoes: str
    accent: str | None = None
    pattern: str | None = None

    @field_validator("top", "bottom", "shoes", "accent", "pattern")
    @classmethod
    def _colour(cls, v: str | None) -> str | None:
        return _hex(v)


class Look(BaseModel):
    prompt: str  # the sheet's words, and the books' outfit line
    top: str  # what the head-and-shoulders portrait shows
    swatch: Swatch

    @field_validator("prompt", "top")
    @classmethod
    def _one_line(cls, v: str) -> str:
        return " ".join(v.split())


class Outfit(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,31}$")
    name_ar: str
    name_en: str
    lines: list[str]
    hijab: str | None = None  # a girl's hijab with this outfit (None: the default sheet hijab)
    hijab_color: str | None = None
    hijab_trim: str | None = None
    looks: dict[Gender, Look]

    @field_validator("hijab_color", "hijab_trim")
    @classmethod
    def _colour(cls, v: str | None) -> str | None:
        return _hex(v)

    def look(self, gender: Gender) -> Look | None:
        return self.looks.get(gender)


class OutfitCatalog(BaseModel):
    version: int
    default: str
    outfits: list[Outfit]
    themes: dict[str, list[str]] = {}  # theme slug → the scene groups that wear the parent's outfit

    @model_validator(mode="after")
    def _check(self) -> "OutfitCatalog":
        ids = [o.id for o in self.outfits]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate outfit id")
        default = self.get(self.default)
        if default is None or set(default.looks) != {"f", "m"}:
            raise ValueError("the default outfit must exist for girls and boys")
        for gender in ("f", "m"):
            if sum(gender in o.looks for o in self.outfits) < 2:
                raise ValueError(f"fewer than two outfits for {gender}")
        return self

    def get(self, outfit_id: str | None) -> Outfit | None:
        return next((o for o in self.outfits if o.id == outfit_id), None)

    def for_child(self, gender: Gender, line: str | None = None) -> list[Outfit]:
        """The outfits offered to a girl or a boy (and, when given, on one product line), in file order."""
        return [o for o in self.outfits if gender in o.looks and (line is None or line in o.lines)]

    def resolve(self, outfit_id: str | None, gender: Gender) -> Outfit:
        """The outfit a character is drawn in: its id when it fits this child, else the default."""
        found = self.get(outfit_id)
        if found is None or gender not in found.looks:
            found = self.get(self.default)
        assert found is not None  # checked when loaded
        return found

    def everyday_groups(self, theme_slug: str) -> list[str]:
        return list(self.themes.get(theme_slug, []))


def read_catalog(path: Path) -> OutfitCatalog:
    return OutfitCatalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@cache
def _cached(path: Path) -> OutfitCatalog:
    return read_catalog(path)


def load_outfits(content_dir: Path = CONTENT_DIR) -> OutfitCatalog:
    """The catalogue of `content_dir`, else the repository's (a test's own content folder has none)."""
    path = content_dir / OUTFITS_FILE
    return _cached(path if path.is_file() else CONTENT_DIR / OUTFITS_FILE)


def is_default(outfit_id: str | None) -> bool:
    return outfit_id is None or outfit_id == load_outfits().default


def hijab_line(outfit: Outfit) -> str | None:
    """A girl's hijab with this outfit, as the sheet and the portrait say it; None: the default wording."""
    return outfit.hijab if outfit.hijab and outfit.id != load_outfits().default else None
