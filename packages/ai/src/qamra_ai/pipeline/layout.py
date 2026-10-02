"""Book plan: theme beats → physical pages in reading order (Addendum 3 §4).

Binding: Arabic books are bound on the right. The book opens with page 1 alone on the LEFT, then
spreads (2 right | 3 left), (4 right | 5 left) … The even page of a spread is read first. English books
mirror this: page 1 alone on the right, spreads (2 left | 3 right).

Interior order: 1 title+dedication → story pages → «وهكذا وُلد صاحبي» (drawing companion) → «للأهل» →
fillers (activity, memories, blank) up to a multiple of the printer's signature. The covers are a
separate wrap PDF; the spine width comes from the page count (`PrintSpec.spine_for`).

Page layouts (Addendum 11 §3): every story beat gets a layout from the library (`qamra_pdf.page_layouts`).
The theme may name one; otherwise the planner rotates so no layout repeats on consecutive pages. The
image geometry (full / split / spread) and the text area the image prompt keeps calm (`BeatPlan.text_area`)
do not depend on the rotation: they come from the theme's `layout` and `text_pos`, and every layout sets its
text inside that area, so the prompt, the busy check (`qamra_pdf.checks.AREAS`) and the page agree.
"""

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from qamra_ai.image.base import Aspect
from qamra_ai.pipeline.models import Lang
from qamra_ai.pipeline.theme import Layout, Theme, ThemePage
from qamra_pdf.lettering import DEFAULT_TITLE_STYLE
from qamra_pdf.page_layouts import PageLayout, choose

if TYPE_CHECKING:
    from qamra_ai.config import Settings

Side = Literal["left", "right"]
SlotKind = Literal["title", "story", "companion", "parents", "activity", "memories", "blank"]
FILLERS: tuple[SlotKind, ...] = ("activity", "memories")


@dataclass(frozen=True)
class PrintSpec:
    trim_mm: float = 210.0
    bleed_mm: float = 3.0
    safe_mm: float = 10.0
    dpi: int = 300
    signature: int = 4
    spine_mm: float = 0.0  # admin override; 0 = from the page count (`spine_for`)
    paper_caliper_mm: float = 0.15  # one leaf (2 pages) of the interior paper
    board_allowance_mm: float = 6.0  # hardcover boards + hinge, from the printer's formula
    split_art_mm: float = 126.0  # art height on split pages, below the top bleed

    @classmethod
    def from_settings(cls, settings: "Settings") -> "PrintSpec":
        """The print settings an operator controls (admin «الطباعة»)."""
        return cls(
            spine_mm=settings.print_spine_mm,
            paper_caliper_mm=settings.print_paper_caliper_mm,
            board_allowance_mm=settings.print_board_allowance_mm,
            signature=settings.print_signature,
            dpi=settings.print_dpi,
        )

    def spine_for(self, pages: int) -> float:
        """Spine width (mm): the admin's fixed value, else caliper × sheets + board allowance (0.1 mm)."""
        if self.spine_mm > 0:
            return self.spine_mm
        sheets = math.ceil(max(0, pages) / 2)
        return round(self.paper_caliper_mm * sheets + self.board_allowance_mm, 1)

    def px(self, mm: float) -> int:
        return round(mm / 25.4 * self.dpi)

    @property
    def page_mm(self) -> float:
        return self.trim_mm + 2 * self.bleed_mm

    @property
    def page_px(self) -> tuple[int, int]:
        side = self.px(self.page_mm)
        return side, side

    @property
    def spread_px(self) -> tuple[int, int]:
        return self.px(2 * self.trim_mm + 2 * self.bleed_mm), self.px(self.page_mm)

    @property
    def split_px(self) -> tuple[int, int]:
        return self.px(self.page_mm), self.px(self.bleed_mm + self.split_art_mm)


@dataclass(frozen=True)
class Slot:
    number: int  # physical page, 1-based, reading order
    kind: SlotKind
    side: Side
    beat: int | None = None  # theme page index for story pages
    spread_half: Literal["first", "second"] | None = None  # first = read first (the even page)


@dataclass(frozen=True)
class BeatPlan:
    beat: int  # theme page index; 0 = cover
    layout: Layout | Literal["cover"]
    pages: tuple[int, ...]
    aspect: Aspect
    print_px: tuple[int, int]
    text_area: str  # inside the image: top/bottom/left/right/top-right/…/none
    no_child: bool = False
    design: PageLayout | None = None  # the page layout from the library (None for the cover)

    @property
    def page_label(self) -> str:
        return "cover" if self.beat == 0 else "–".join(str(p) for p in self.pages)


@dataclass
class BookPlan:
    lang: Lang
    spec: PrintSpec
    slots: list[Slot] = field(default_factory=list)
    beats: dict[int, BeatPlan] = field(default_factory=dict)  # includes 0 = cover
    title_style: str = DEFAULT_TITLE_STYLE  # the theme's cover lettering (`cover_title_style`)
    memories: Literal["school", "default"] = "default"  # «ذكرياتنا» prompts: first/last day for school themes

    @property
    def rtl(self) -> bool:
        return self.lang == "ar"

    @property
    def page_count(self) -> int:
        return len(self.slots)

    @property
    def spine_mm(self) -> float:
        return self.spec.spine_for(self.page_count)

    def spreads(self) -> list[tuple[Slot | None, Slot | None]]:
        """Open-book views in reading order: (right, left) pairs as a reader sees them."""
        views: list[tuple[Slot | None, Slot | None]] = []
        first = self.slots[0]
        views.append((None, first) if first.side == "left" else (first, None))
        rest = self.slots[1:]
        for i in range(0, len(rest), 2):
            pair = rest[i : i + 2]
            right = next((s for s in pair if s.side == "right"), None)
            left = next((s for s in pair if s.side == "left"), None)
            views.append((right, left))
        return views


def side_of(page: int, rtl: bool) -> Side:
    odd = page % 2 == 1
    if rtl:
        return "left" if odd else "right"
    return "right" if odd else "left"


def _text_area(page: ThemePage, first_page: int, rtl: bool) -> str:
    if page.layout == "split":
        return "none"
    if page.layout == "spread":
        # the text panel sits on the page read first (the even page): right half in RTL, left in LTR
        vertical = "bottom" if page.text_pos == "bottom" else "top"
        return f"{vertical}-{'right' if rtl else 'left'}"
    if page.text_pos == "side":
        return side_of(first_page, rtl)  # the outer edge of that page, away from the fold
    return page.text_pos


SCHOOL_OCCASIONS = ("first_day", "graduation")


def plan_book(theme: Theme, lang: Lang, *, companion_page: bool, spec: PrintSpec | None = None) -> BookPlan:
    spec = spec or PrintSpec()
    rtl = lang == "ar"
    occasions = theme.catalog.occasions if theme.catalog else []
    plan = BookPlan(
        lang=lang,
        spec=spec,
        title_style=theme.cover_title_style,
        memories="school" if any(o in SCHOOL_OCCASIONS for o in occasions) else "default",
    )
    plan.slots.append(Slot(1, "title", side_of(1, rtl)))
    plan.beats[0] = BeatPlan(0, "cover", (), "1:1", spec.page_px, "top")
    n = 2
    previous: list[PageLayout] = []
    used: dict[PageLayout, int] = {}
    for page in theme.pages:
        if page.layout == "spread":
            if n % 2:
                raise ValueError(f"theme {theme.slug}: spread at page {page.index} starts on odd page {n}")
            pages: tuple[int, ...] = (n, n + 1)
            plan.slots.append(Slot(n, "story", side_of(n, rtl), page.index, "first"))
            plan.slots.append(Slot(n + 1, "story", side_of(n + 1, rtl), page.index, "second"))
            aspect: Aspect = "16:9"
            px = spec.spread_px
        else:
            pages = (n,)
            plan.slots.append(Slot(n, "story", side_of(n, rtl), page.index))
            aspect = "3:2" if page.layout == "split" else "1:1"
            px = spec.split_px if page.layout == "split" else spec.page_px
        area = _text_area(page, pages[0], rtl)
        design = choose(
            page.layout,
            area,
            page.text_ar if lang == "ar" else page.text_en,
            wanted=page.design,
            previous=previous,
            used=used,
        )
        previous.append(design)
        used[design] = used.get(design, 0) + 1
        plan.beats[page.index] = BeatPlan(
            page.index, page.layout, pages, aspect, px, area, page.no_child, design
        )
        n += len(pages)
    if companion_page:
        plan.slots.append(Slot(n, "companion", side_of(n, rtl)))
        n += 1
    plan.slots.append(Slot(n, "parents", side_of(n, rtl)))
    n += 1
    fillers = iter(FILLERS)
    while (n - 1) % spec.signature:
        plan.slots.append(Slot(n, next(fillers, "blank"), side_of(n, rtl)))
        n += 1
    return plan
