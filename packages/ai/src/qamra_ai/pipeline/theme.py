"""Theme + art style loading and gendered template rendering."""

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

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
    cover: ThemeScene
    pages: list[ThemePage]

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
    if indices != list(range(1, len(indices) + 1)):
        raise ValueError(f"theme {slug}: page indices must be 1..N in order, got {indices}")
    return theme


def theme_dir(slug: str, content_dir: Path = CONTENT_DIR) -> Path:
    return content_dir / "themes" / slug


def load_style(slug: str, content_dir: Path = CONTENT_DIR) -> ArtStyle:
    data = yaml.safe_load((content_dir / "styles" / "styles.yaml").read_text(encoding="utf-8"))
    if slug not in data:
        raise KeyError(f"unknown art style {slug!r}; available: {sorted(data)}")
    return ArtStyle(slug=slug, **data[slug])
