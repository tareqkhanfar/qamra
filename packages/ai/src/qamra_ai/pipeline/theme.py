"""Theme + art style loading and gendered template rendering.

Theme schema v2 (Addendum 3): every story page ("beat") declares its layout, where the text panel goes,
the location and time of day (visual continuity), the outfit it uses (locked once per book), who else is
in the picture (for the QA count check), and whether it is a child-free background plate (cached per theme).
"""

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from qamra_ai.pipeline.models import Gender, Lang

CONTENT_DIR = Path(os.environ.get("QAMRA_CONTENT_DIR") or Path(__file__).resolve().parents[5] / "content")

_VARIANT = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")
GENDERS: tuple[Gender, ...] = ("m", "f")

Layout = Literal["full", "split", "spread"]
TextPos = Literal["top", "bottom", "side"]
TimeOfDay = Literal["dawn", "morning", "noon", "afternoon", "sunset", "evening", "night"]

STORY_PAGES_MIN, STORY_PAGES_MAX = 16, 20  # physical story pages per book (Addendum 3 §4)
SPREADS_MIN, SPREADS_MAX = 2, 3
MAX_WORDS_YOUNG = 35  # ages 3–5
MAX_WORDS_OLDER = 50  # ages 6–8


class DefaultCompanion(BaseModel):
    name_ar: str
    name_en: str
    description_en: str
    image: str | None = None


class Outfit(BaseModel):
    """One clothing option. The book picks one option per outfit key and keeps it on every page."""

    key: str
    en: str  # visual description for the image model
    en_f: str | None = None  # girls' variant when it differs
    hijab_en: str | None = None  # hijab to pair with it when the parent chose hijab

    def describe(self, gender: Gender, hijab: bool) -> str:
        text = self.en_f if gender == "f" and self.en_f else self.en
        if hijab:
            text += (
                f"; {self.hijab_en or 'a simple soft hijab in a matching color, neatly covering the hair'}"
            )
        return text


class ThemeScene(BaseModel):
    scene: str
    companion_action: str | None = None
    location: str | None = None  # key into Theme.locations (fixed description, repeated verbatim)
    time: TimeOfDay = "morning"
    outfit: str = "day"  # key into Theme.outfits
    others: str | None = None  # other people in the picture, e.g. "a kind teacher and two other children"
    others_count: int = Field(default=0, ge=0, le=12)  # for the QA count check (0 = hero alone)


class ThemePage(ThemeScene):
    index: int
    layout: Layout = "full"
    text_pos: TextPos = "top"
    no_child: bool = False  # background plate: no hero, no companion → generated once per theme and cached
    beat: str
    text_ar: str
    text_en: str

    @property
    def physical_pages(self) -> int:
        return 2 if self.layout == "spread" else 1


class ForParents(BaseModel):
    lesson_ar: str
    lesson_en: str
    questions_ar: list[str] = Field(min_length=2, max_length=2)
    questions_en: list[str] = Field(min_length=2, max_length=2)


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
    setting: str | None = None  # overrides the house style's local setting cues when the story needs it
    locations: dict[str, str] = {}
    outfits: dict[str, list[Outfit]] = {}
    blurb_ar: str | None = None
    blurb_en: str | None = None
    for_parents: ForParents | None = None
    cover: ThemeScene | None = None
    pages: list[ThemePage] = []

    @model_validator(mode="after")
    def _story_complete(self) -> "Theme":
        if not self.available:
            return self
        if self.cover is None or not self.pages:
            raise ValueError(f"theme {self.slug}: an available theme needs a cover and pages")
        problems = theme_problems(self)
        if problems:
            raise ValueError(f"theme {self.slug}: " + "; ".join(problems))
        return self

    @property
    def available(self) -> bool:
        return self.catalog is None or self.catalog.status == "available"

    @property
    def story_page_count(self) -> int:
        return sum(p.physical_pages for p in self.pages)

    def title(self, lang: Lang, gender: Gender, name: str) -> str:
        return render_template(self.title_ar if lang == "ar" else self.title_en, gender, name, "")

    def base_text(self, page: ThemePage, lang: Lang, gender: Gender, name: str, comp: str) -> str:
        return render_template(page.text_ar if lang == "ar" else page.text_en, gender, name, comp)

    def location_text(self, scene: ThemeScene) -> str | None:
        return self.locations.get(scene.location) if scene.location else None


def word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", text) if re.search(r"\w", w)])


def max_words_for(age: int) -> int:
    return MAX_WORDS_YOUNG if age <= 5 else MAX_WORDS_OLDER


def theme_problems(theme: Theme) -> list[str]:
    """Addendum 3 rules for an available theme; empty when the theme is fine."""
    out: list[str] = []
    n = theme.story_page_count
    if not STORY_PAGES_MIN <= n <= STORY_PAGES_MAX:
        out.append(f"{n} story pages (need {STORY_PAGES_MIN}–{STORY_PAGES_MAX})")
    spreads = [p for p in theme.pages if p.layout == "spread"]
    if not SPREADS_MIN <= len(spreads) <= SPREADS_MAX:
        out.append(f"{len(spreads)} spreads (need {SPREADS_MIN}–{SPREADS_MAX})")
    page_no = 2  # physical page 1 is the title/dedication page
    for p in theme.pages:
        if p.layout == "spread" and page_no % 2:
            out.append(f"page {p.index}: a spread must start on an even page (starts on {page_no})")
        page_no += p.physical_pages
    scenes: list[ThemeScene] = [*theme.pages, *([theme.cover] if theme.cover else [])]
    for s in scenes:
        if s.outfit not in theme.outfits:
            out.append(f"unknown outfit {s.outfit!r}")
        if s.location and s.location not in theme.locations:
            out.append(f"unknown location {s.location!r}")
    for p in theme.pages:
        if p.no_child and p.companion_action:
            out.append(f"page {p.index}: a child-free plate cannot show the companion")
        limit = max_words_for(theme.age_range[0])
        for lang_text in (p.text_ar, p.text_en):
            for gender in GENDERS:
                words = word_count(render_template(lang_text, gender, "اسم", "صاحب"))
                if words > limit:
                    out.append(f"page {p.index}: {words} words (max {limit})")
    if theme.for_parents is None:
        out.append("missing for_parents (lesson + 2 questions)")
    if not (theme.blurb_ar and theme.blurb_en):
        out.append("missing back-cover blurb")
    return sorted(set(out))


class ArtStyle(BaseModel):
    slug: str
    title_ar: str
    title_en: str
    guide: str  # the painting medium; palette/setting/people/composition come from the house style


def render_template(template: str, gender: Gender, name: str, companion: str) -> str:
    """`{masc/fem}` → variant for gender, then `{name}` / `{companion}`."""
    text = _VARIANT.sub(lambda m: m.group(1 if gender == "m" else 2), template)
    return text.replace("{name}", name).replace("{companion}", companion)


def fill_title(template: str, name: str, gender: Gender | None) -> str:
    """A theme title for one child: `{masc/fem}` by gender, then `{name}`. With no child (staff lists, the
    catalog) both forms stay, «حارس/حارسة النجوم», so a title never shows a brace or the wrong gender."""
    if gender is None:
        text = _VARIANT.sub(lambda m: f"{m.group(1)}/{m.group(2)}", template)
        return text.replace("{name}", name).strip()
    return render_template(template, gender, name, "").strip()


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
