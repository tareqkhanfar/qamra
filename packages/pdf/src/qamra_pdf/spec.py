"""What the renderer needs to lay out a book (Addendum 3 §4, Addendum 11 §2–§5). Paths are local files.

Pages come in reading order with their side in the open book already decided (Arabic books are bound on the
right: page 1 is a left-hand page). A spread is two `PageSpec`s, each carrying its own half of the image
(cut with bleed), and the text sits on the half read first. Story pages name their layout from the library
(`page_layouts.LAYOUTS`); the legacy values full/split/spread still render.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PageKind = Literal["title", "story", "companion", "parents", "activity", "memories", "blank"]
Side = Literal["left", "right"]
PanelArea = Literal["top", "bottom", "left", "right"]
# Story text size and its shrink-to-fit floor (pt): 24–28 pt for ages 3–5, 20–22 pt for 6–8 (Addendum 11 §3).
STORY_PT: dict[str, tuple[float, float]] = {"young": (26.0, 24.0), "older": (21.0, 20.0)}


@dataclass(frozen=True)
class Panel:
    """Where the text sits and how solid its backing is. Opacity rises over busy or low-contrast art
    (see `checks.panel_for`); `tone` is dark when the art under the text area is dark (night scenes)."""

    area: PanelArea = "top"
    opacity: float = 0.88
    busy: bool = False
    contrast: float | None = None
    tone: Literal["light", "dark"] = "light"


@dataclass(frozen=True)
class PageSpec:
    number: int  # physical page, reading order
    kind: PageKind
    side: Side
    layout: str | None = None  # a `page_layouts.PageLayout` (or legacy full/split/spread)
    image: Path | None = None
    text: str | None = None
    panel: Panel | None = None  # None: no text panel on this page (e.g. the second half of a spread)
    is_last_story: bool = False
    qr_url: str | None = None  # «صوت أهلي»: this page's listen link, printed as a QR in the outer corner


@dataclass(frozen=True)
class TitleSpec:
    """Page 1: title + «إلى {child}…» dedication with the parent's optional message (≤ 120 chars)."""

    name: str
    subtitle: str  # the rest of the title
    made_for: str  # "a story written and illustrated especially for …"
    dedication: str
    portrait: Path | None = None


@dataclass(frozen=True)
class KeepsakeSpec:
    """Addendum 1 page «وهكذا وُلد صاحبي»: the original drawing beside the final companion."""

    drawing: Path
    companion: Path
    child_name: str
    companion_name: str
    date_text: str


@dataclass(frozen=True)
class ParentsSpec:
    lesson: str
    questions: list[str]


@dataclass(frozen=True)
class CoverSpec:
    front_image: Path
    name: str
    subtitle: str
    blurb: str
    qr_url: str | None = None  # family voice (Addendum 1 §3): the back shows a QR only when this is set


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
    child_name: str
    child_age: int
    gender: Literal["m", "f"]
    brand: Brand
    title_page: TitleSpec
    cover: CoverSpec
    pages: list[PageSpec]
    parents: ParentsSpec | None = None
    keepsake: KeepsakeSpec | None = None
    watermark: bool = False  # preview copies
    trim_mm: float = 210.0
    bleed_mm: float = 3.0
    safe_mm: float = 10.0
    spine_mm: float = 8.0  # from the page count and the printer's formula (`PrintSpec.spine_for`)
    title_style: str = "gold-magic"  # cover lettering treatment (`lettering.TITLE_STYLES`)
    companion: Path | None = None  # the companion's front view (peeks on the drawing page)
    memories: Literal["school", "default"] = "default"  # «ذكرياتنا» prompts: first/last day for school books
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def page_mm(self) -> float:
        return self.trim_mm + 2 * self.bleed_mm

    @property
    def wrap_width_mm(self) -> float:
        return 2 * self.trim_mm + self.spine_mm + 2 * self.bleed_mm

    @property
    def dir(self) -> str:
        return "rtl" if self.lang == "ar" else "ltr"

    @property
    def text_pt(self) -> float:
        """Story text size: 26 pt for ages 3–5, 21 pt for 6–8 (Addendum 11 §3)."""
        return STORY_PT["young" if self.child_age <= 5 else "older"][0]

    @property
    def min_text_pt(self) -> float:
        return STORY_PT["young" if self.child_age <= 5 else "older"][1]

    def folio(self, n: int) -> str:
        """Arabic-Indic digits in Arabic books (١، ٢، ٣)."""
        text = str(n)
        return text.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")) if self.lang == "ar" else text
