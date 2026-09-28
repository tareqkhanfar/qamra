"""Theme + art style loading and gendered template rendering."""

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

from qamra_ai.pipeline.models import Gender, Lang

CONTENT_DIR = Path(os.environ.get("QAMRA_CONTENT_DIR") or Path(__file__).resolve().parents[5] / "content")

_VARIANT = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")


class DefaultCompanion(BaseModel):
    name_ar: str
    name_en: str
    description_en: str
    image: str | None = None


class ThemeScene(BaseModel):
    scene: str
    companion_action: str | None = None


class ThemePage(ThemeScene):
    index: int
    layout: Literal["illustration-textbox", "split", "text-only"] = "illustration-textbox"
    beat: str
    text_ar: str
    text_en: str


Occasion = Literal["first_day", "graduation", "new_sibling", "adventure", "bedtime", "birthday", "values"]


class CatalogArt(BaseModel):
    """Placeholder illustration for catalog cards (design parts `Scene` + `Kid`), until real art exists."""

    scene: Literal["night", "garden", "sea", "space", "grad"]
    outfit: str = "#5B6FC0"
    skin: str = "#E8B98F"
    hair: str = "#3A2A22"
    hair_style: Literal["short", "long", "curly"] = "short"
    hijab: bool = False
    hijab_color: str = "#A99BD6"
    cap: bool = False
    pose: Literal["front", "wave", "tilt"] = "front"
    companion: Literal["", "blob", "cat", "robot"] = ""
    kid_scale: float = 0.7


class SampleChild(BaseModel):
    name_ar: str
    name_en: str
    gender: Gender


class ThemeCatalog(BaseModel):
    status: Literal["available", "coming_soon"] = "available"
    name_ar: str  # catalog title without the child's name
    name_en: str
    tagline_ar: str
    tagline_en: str
    description_ar: str
    description_en: str
    occasions: list[Occasion] = []
    values_ar: list[str] = []
    values_en: list[str] = []
    tag: Literal["popular", "new", "kindergarten"] | None = None
    rank: int = 100  # lower first ("most requested" sort)
    planned_pages: int | None = None  # coming-soon worlds have no pages yet
    art: CatalogArt
    peek: list[CatalogArt] = []  # illustrations between the text peeks on the detail page
    sample_child: SampleChild | None = None  # renders peek texts (never ship "[name]")


class Theme(BaseModel):
    slug: str
    version: int
    title_ar: str
    title_en: str
    age_range: tuple[int, int]
    is_b2b: bool = False
    active: bool = True
    companion_slot: bool
    default_companion: DefaultCompanion | None = None
    catalog: ThemeCatalog | None = None
    cover: ThemeScene | None = None
    pages: list[ThemePage] = []

    @model_validator(mode="after")
    def _story_complete(self) -> "Theme":
        available = self.catalog is None or self.catalog.status == "available"
        if available and (self.cover is None or not self.pages):
            raise ValueError(f"theme {self.slug}: an available theme needs a cover and pages")
        return self

    @property
    def available(self) -> bool:
        return self.catalog is None or self.catalog.status == "available"

    def title(self, lang: Lang, gender: Gender, name: str) -> str:
        return render_template(self.title_ar if lang == "ar" else self.title_en, gender, name, "")

    def base_text(self, page: ThemePage, lang: Lang, gender: Gender, name: str, comp: str) -> str:
        return render_template(page.text_ar if lang == "ar" else page.text_en, gender, name, comp)


class ArtStyle(BaseModel):
    slug: str
    title_ar: str
    title_en: str
    guide: str


def render_template(template: str, gender: Gender, name: str, companion: str) -> str:
    """`{masc/fem}` → variant for gender, then `{name}` / `{companion}`."""
    text = _VARIANT.sub(lambda m: m.group(1 if gender == "m" else 2), template)
    return text.replace("{name}", name).replace("{companion}", companion)


def load_theme(slug: str, content_dir: Path = CONTENT_DIR) -> Theme:
    path = content_dir / "themes" / slug / "theme.yaml"
    theme = Theme.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    indices = [p.index for p in theme.pages]
    if theme.pages and indices != list(range(1, len(indices) + 1)):
        raise ValueError(f"theme {slug}: page indices must be 1..N in order, got {indices}")
    return theme


def theme_dir(slug: str, content_dir: Path = CONTENT_DIR) -> Path:
    return content_dir / "themes" / slug


def load_style(slug: str, content_dir: Path = CONTENT_DIR) -> ArtStyle:
    data = yaml.safe_load((content_dir / "styles" / "styles.yaml").read_text(encoding="utf-8"))
    if slug not in data:
        raise KeyError(f"unknown art style {slug!r}; available: {sorted(data)}")
    return ArtStyle(slug=slug, **data[slug])
