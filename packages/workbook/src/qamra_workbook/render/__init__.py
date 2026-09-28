"""The workbook page engine, shared by «دوسية التأسيس» (Addendum 5), «رحلتي الأولى للتعلّم» (Addendum 6) and
«مغامراتي مع عائلتي» (Addendum 7).

A `BookSpec` of product-independent `PageSpec`s goes through the page-type builders (`render.pages`, one per
type, each with a Jinja template in `render/templates/pages/`), then to HTML and a print PDF with 3 mm bleed,
a 12 mm safe area, exact TrimBox/BleedBox and embedded fonts (the `qamra_pdf` pipeline): A4 portrait for the
workbooks, 21 × 28 cm for the family book (`product_geometry`). A family book also carries the child's
`Family` (names, roles, city) for its placeholders, the parent box and the activity icons. Puzzle pages carry
an answer key and automated checks; a page that fails its checks, or whose text or layout overflows, is
never rendered.
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
from qamra_workbook.render.spec import (
    ActivityTags,
    BookSpec,
    Child,
    Family,
    Geometry,
    Member,
    PageSpec,
    from_family,
    from_journey,
    product_geometry,
)

__all__ = [
    "REGISTRY",
    "ActivityTags",
    "Assets",
    "BookSpec",
    "Built",
    "Child",
    "Family",
    "Geometry",
    "Member",
    "PageContext",
    "PageProblems",
    "PageSpec",
    "RenderedPage",
    "answer_key_html",
    "book_html",
    "build_pages",
    "contact_sheet",
    "from_family",
    "from_journey",
    "page_type",
    "previews",
    "print_pdf",
    "product_geometry",
]
