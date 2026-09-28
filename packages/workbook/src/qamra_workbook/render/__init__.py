"""The workbook page engine, shared by «دوسية التأسيس» (Addendum 5) and «رحلتي الأولى للتعلّم» (Addendum 6).

A `BookSpec` of product-independent `PageSpec`s goes through the page-type builders (`render.pages`, one per
type, each with a Jinja template in `render/templates/pages/`), then to HTML and a print PDF: A4 portrait
with 3 mm bleed, a 12 mm safe area, exact TrimBox/BleedBox and embedded fonts (the `qamra_pdf` pipeline).
Puzzle pages carry an answer key and automated checks; a page that fails its checks is never rendered.
"""

from qamra_workbook.render.engine import (
    PageProblems,
    RenderedPage,
    answer_key_html,
    book_html,
    build_pages,
    contact_sheet,
    previews,
    print_pdf,
)
from qamra_workbook.render.registry import REGISTRY, Assets, Built, PageContext, page_type
from qamra_workbook.render.spec import BookSpec, Child, Geometry, PageSpec, from_journey

__all__ = [
    "REGISTRY",
    "Assets",
    "BookSpec",
    "Built",
    "Child",
    "Geometry",
    "PageContext",
    "PageProblems",
    "PageSpec",
    "RenderedPage",
    "answer_key_html",
    "book_html",
    "build_pages",
    "contact_sheet",
    "from_journey",
    "page_type",
    "previews",
    "print_pdf",
]
