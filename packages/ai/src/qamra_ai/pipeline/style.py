"""The house illustration style (`prompts/style/qamra_style.md`) and the art-style guides beside it.

The house style holds what every book shares: setting, people, composition, safety and negatives. Each art
style (Addendum 4 §2) has its own guide, `prompts/style/<slug>.md`, with its look, look-specific negatives and
QA thresholds. The guides seed the `art_styles` table, where the admin edits them from then on.

A guide may also replace two house sections for its own style only (`## House style`, `## House negative`)
and add a line to its character-sheet prompt (`## Sheet`): «شبه حقيقي» v3 does, because the house's
picture-book wording pulls a realistic painting back to a cartoon. `## Character` is a line for both the
character portrait and the sheet (watercolor v4: clean, clear colour, never sepia). Every other style gets the
house as it is (`house_for`). Earlier guide versions live in `prompts/style/history/` (not loaded as styles).
"""

import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from qamra_ai.prompts import PROMPTS_DIR

if TYPE_CHECKING:
    from qamra_ai.pipeline.theme import ArtStyle

STYLE_FILE: Path = PROMPTS_DIR / "style" / "qamra_style.md"
HISTORY_DIR: Path = STYLE_FILE.parent / "history"  # earlier guide versions, e.g. semi-realistic.v2.md
SECTIONS = ("style", "setting", "people", "composition", "safety", "negative")
_HEADING = re.compile(r"^## +(.+?)\s*$", re.M)
_VERSION = re.compile(r"^version:\s*(\S+)\s*$", re.M)


@dataclass(frozen=True)
class HouseStyle:
    version: str
    style: str
    setting: str
    people: str
    composition: str
    safety: str
    negative: str

    @property
    def prompt_id(self) -> str:
        return f"qamra_style.v{self.version}"

    def for_style(self, art: "ArtStyle") -> "HouseStyle":
        """The house as one art style uses it: the style's guide may replace the Style section and the
        Negative list for itself. A style that replaces neither gets this same object, so its prompts stay
        byte-identical. The merged version names the guide («5+semi-realistic.v3»): what a book records, and
        the companion-sheet cache key, never mix the merged house with the plain one."""
        if not (art.house_style or art.house_negative):
            return self
        base = self.version.split("+", 1)[0]
        return replace(
            self,
            version=f"{base}+{art.slug}.v{art.version}",
            style=art.house_style or self.style,
            negative=art.house_negative or self.negative,
        )


def parse_style(text: str) -> HouseStyle:
    version = _VERSION.search(text)
    parts = _HEADING.split(text)
    # parts = [intro, heading1, body1, heading2, body2, ...]
    sections = {parts[i].strip().lower(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    missing = [s for s in SECTIONS if not sections.get(s)]
    if missing:
        raise ValueError(f"house style is missing sections: {missing}")
    return HouseStyle(version=version.group(1) if version else "0", **{s: sections[s] for s in SECTIONS})


@lru_cache
def house_style() -> HouseStyle:
    return parse_style(STYLE_FILE.read_text(encoding="utf-8"))


def house_for(art: "ArtStyle") -> HouseStyle:
    """The house style merged with one art style's own house sections (`HouseStyle.for_style`)."""
    return house_style().for_style(art)


def negatives(house: HouseStyle, style_negative: str = "") -> str:
    """The house's never-allowed list plus the art style's own (watercolor: no 3D-render look; 3D: no plastic
    dolls). The house list is style-neutral, so a 3D book is not told to avoid 3D."""
    extra = style_negative.strip()
    return f"{house.negative}\n{extra}" if extra else house.negative


# one line each: an empty value (`lines:`) must not swallow the next line
_FIELD = re.compile(r"^(slug|version|lines|qa_threshold|likeness_min):[ \t]*(.*?)[ \t]*$", re.M)
_TITLE = re.compile(r"^# +(.+?) — (.+?)\s*$", re.M)


@dataclass(frozen=True)
class StyleGuide:
    slug: str
    name_ar: str
    name_en: str
    version: int
    lines: tuple[str, ...]
    qa_threshold: float
    likeness_min: int
    look: str
    negative: str
    house_style: str = ""  # replaces the house's Style section for this style only
    house_negative: str = ""  # replaces the house's Negative list for this style only
    sheet: str = ""  # added to this style's character-sheet prompt
    character: str = ""  # added to this style's character portrait and sheet prompts (the child's colours)


def parse_style_guide(text: str) -> StyleGuide:
    title = _TITLE.search(text)
    fields = dict(_FIELD.findall(text))
    parts = _HEADING.split(text)
    sections = {parts[i].strip().lower(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    if title is None or not fields.get("slug") or not sections.get("look"):
        raise ValueError("a style guide needs a '# name_ar — name_en' title, a slug and a '## Look' section")
    return StyleGuide(
        slug=fields["slug"],
        name_ar=title.group(1),
        name_en=title.group(2),
        version=int(fields.get("version", "1")),
        lines=tuple(x.strip() for x in fields.get("lines", "").split(",") if x.strip()),
        qa_threshold=float(fields.get("qa_threshold", "0.75")),
        likeness_min=int(fields.get("likeness_min", "7")),
        look=sections["look"],
        negative=sections.get("negative", ""),
        house_style=sections.get("house style", ""),
        house_negative=sections.get("house negative", ""),
        sheet=sections.get("sheet", ""),
        character=sections.get("character", ""),
    )


def style_guides() -> list[StyleGuide]:
    """Every art-style guide under `prompts/style/` (all files except the house style; not `history/`)."""
    return [
        parse_style_guide(path.read_text(encoding="utf-8"))
        for path in sorted(STYLE_FILE.parent.glob("*.md"))
        if path != STYLE_FILE
    ]


def history_guide(slug: str, version: int) -> StyleGuide:
    """An earlier version of a guide (`prompts/style/history/<slug>.v<version>.md`), e.g. to draw a
    before/after comparison."""
    guide = parse_style_guide((HISTORY_DIR / f"{slug}.v{version}.md").read_text(encoding="utf-8"))
    if (guide.slug, guide.version) != (slug, version):
        raise ValueError(f"history/{slug}.v{version}.md says {guide.slug} v{guide.version}")
    return guide
