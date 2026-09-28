"""The house illustration style (`prompts/style/qamra_style.md`), split into its sections."""

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
