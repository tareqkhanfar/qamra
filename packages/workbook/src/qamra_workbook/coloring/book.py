"""The page lists of the four books of «دفاتر التلوين والرسم», as engine page specs for one child.

- «أُلَوِّنُ حُروفي» (32): the title page, «اسْمي», the 28 letters, «أَحْسَنْتَ!», «عن قمرة»;
- «أُلَوِّنُ فِلَسْطين» (28) and «أُلَوِّنُ رَمَضان» (24): the title page, the scenes of
  content/coloring/<book>.yaml, a free drawing page, «عن قمرة»;
- «دَفْتَري» (48): the title page, the 46 pages of content/coloring/sketchbook.yaml, «عن قمرة».

Each count is a multiple of 4 (stapled books are printed on folded sheets of four pages; the wire-o
sketchbook keeps whole sheets too); `page_problems` checks it.
"""

from __future__ import annotations

import datetime as dt
import functools
from pathlib import Path
from typing import Any

import yaml

from qamra_pdf.imprint import Imprint
from qamra_workbook.coloring.letters import load as load_letters
from qamra_workbook.coloring.titles import LINE, Title, title_of
from qamra_workbook.render.pages.about_qamra import ABOUT
from qamra_workbook.render.spec import BookSpec, Child, Numerals, PageSpec, product_geometry

PRODUCT = LINE  # BookSpec.product: the engine's styles and the «عن قمرة» look follow the store line
CONTENT = Path(__file__).resolve().parents[5] / "content" / "coloring"
OWNER = "{صاحِبُ/صاحِبَةُ} هذا الدَّفْتَرِ"

# the free drawing page at the end of a scene book (its frame from `coloring.sketch`)
FREE_PAGE: dict[str, dict[str, str]] = {
    "palestine": {"title": "{ارْسُمْ/ارْسُمي} فِلَسْطينَ كَما {تُحِبُّها/تُحِبّينَها}", "art": "frame-tatreez"},
    "ramadan": {"title": "{ارْسُمْ/ارْسُمي} فانوسَ{كَ/كِ}", "art": "frame-stars"},
}


@functools.cache
def content(book: str) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((CONTENT / f"{book}.yaml").read_text(encoding="utf-8"))
    return data


def _page(n: int, type_: str, heading: str = "", instruction: str = "", **params: Any) -> PageSpec:
    return PageSpec(
        id=f"p{n}",
        type=type_,
        number=n,
        section="colorbook",
        title=heading,
        instruction=instruction,
        params=params,
    )


def interior_pages(key: str) -> list[PageSpec]:
    """The book's pages in order, «عن قمرة» last."""
    t = title_of(key)
    pages: list[PageSpec] = [_page(1, "cb-title", t.name_ar, "", title=t.key, owner=OWNER)]

    def add(type_: str, heading: str = "", instruction: str = "", **params: Any) -> None:
        pages.append(_page(len(pages) + 1, type_, heading, instruction, **params))

    if t.key == "letters":
        add("cb-me", "اسْمي", "{ارْسُمْ/ارْسُمي} نَفْسَ{كَ/كِ} هُنا")
        for letter in load_letters().letters:
            add("cb-letter", letter.name_ar, "", char=letter.char)
        add("cb-certificate", "{أَحْسَنْتَ/أَحْسَنْتِ} يا {child}!", "{لَوَّنْتَ/لَوَّنْتِ} الحُروفَ كُلَّها")
    elif t.key in ("palestine", "ramadan"):
        for scene in content(t.key)["pages"]:
            add("cb-scene", str(scene["caption_ar"]), "", book=t.key, scene=str(scene["id"]))
        free = FREE_PAGE[t.key]
        add("cb-draw", free["title"], "", art=free["art"])
    else:
        for page in content("sketchbook")["pages"]:
            add(
                "cb-draw",
                str(page.get("prompt_ar") or ""),
                "",
                art=str(page["art"]),
                kind=str(page.get("kind", "")),
                labels=[str(x) for x in page.get("lines_ar", []) or []],  # the date page's line labels
            )
    add(ABOUT, "عن قمرة", "معلومات الكتاب والتواصل")
    return [_with_id(p, t) for p in pages]


def _with_id(p: PageSpec, t: Title) -> PageSpec:
    import dataclasses

    return dataclasses.replace(p, id=f"{t.key}-p{p.number:02d}")


def page_problems(key: str, pages: list[PageSpec]) -> list[str]:
    t = title_of(key)
    out = []
    if len(pages) != t.pages:
        out.append(f"{t.key}: {len(pages)} pages, the book has {t.pages}")
    if len(pages) % t.signature:
        out.append(f"{t.key}: {len(pages)} pages is not a multiple of {t.signature}")
    return out


def cover_pages(key: str) -> list[PageSpec]:
    t = title_of(key)
    return [
        PageSpec(
            id=f"{t.key}-cover-{side}",
            type=f"cb-cover-{side}",
            number=0,
            section="colorbook",
            title=t.name_ar,
            instruction="",
            params={"title": t.key, "pages": t.pages},
        )
        for side in ("front", "back")
    ]


def book_spec(
    key: str,
    child: Child,
    pages: list[PageSpec],
    *,
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    imprint: Imprint | None = None,
) -> BookSpec:
    t = title_of(key)
    return BookSpec(
        product=PRODUCT,
        title_ar=t.name_ar,
        child=child,
        pages=tuple(pages),
        date=day or dt.date.today(),
        numerals=numerals,
        geometry=product_geometry(PRODUCT),
        imprint=imprint,
    )
