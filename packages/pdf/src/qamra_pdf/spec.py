"""What the renderer needs to lay out a book. Paths are local files (object storage is downloaded first)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class PageSpec:
    index: int
    image: Path
    text: str
    layout: Literal["illustration-textbox", "split", "text-only"] = "illustration-textbox"


@dataclass(frozen=True)
class KeepsakeSpec:
    """Addendum 1 last page «وهكذا وُلد صاحبي»: the original drawing beside the final companion."""

    drawing: Path
    companion: Path
    child_name: str
    companion_name: str
    date_text: str


@dataclass(frozen=True)
class Brand:
    name_ar: str
    name_en: str
    domain: str
    tagline_ar: str
    tagline_en: str


@dataclass(frozen=True)
class BookSpec:
    lang: Literal["ar", "en"]
    title: str
    dedication: str
    child_name: str
    cover_image: Path
    pages: list[PageSpec]
    brand: Brand
    keepsake: KeepsakeSpec | None = None
    watermark: bool = False  # preview copies
    trim_mm: float = 210.0
    bleed_mm: float = 3.0
    safe_mm: float = 10.0
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def page_mm(self) -> float:
        return self.trim_mm + 2 * self.bleed_mm

    @property
    def dir(self) -> str:
        return "rtl" if self.lang == "ar" else "ltr"
