"""The house illustration style (`prompts/style/qamra_style.md`) and the art-style guides beside it.

The house style holds what every book shares: setting, people, composition, safety and negatives. Each art
style (Addendum 4 §2) has its own guide, `prompts/style/<slug>.md`, with its look, look-specific negatives and
QA thresholds. The guides seed the `art_styles` table, where the admin edits them from then on.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from qamra_ai.prompts import PROMPTS_DIR

STYLE_FILE: Path = PROMPTS_DIR / "style" / "qamra_style.md"
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


def negatives(house: HouseStyle, style_negative: str = "") -> str:
    """The house's never-allowed list plus the art style's own (watercolor: no 3D-render look; 3D: no plastic
    dolls). The house list is style-neutral, so a 3D book is not told to avoid 3D."""
    extra = style_negative.strip()
    return f"{house.negative}\n{extra}" if extra else house.negative


_FIELD = re.compile(r"^(slug|version|lines|qa_threshold|likeness_min):\s*(.+?)\s*$", re.M)
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
    )


def style_guides() -> list[StyleGuide]:
    """Every art-style guide under `prompts/style/` (all files except the house style)."""
    return [
        parse_style_guide(path.read_text(encoding="utf-8"))
        for path in sorted(STYLE_FILE.parent.glob("*.md"))
        if path != STYLE_FILE
    ]
