"""«عن قمرة»: the info page at the end of every activity book (owner, 2026-10-19), and how a book gets it.

The page itself is `qamra_pdf.imprint.about_html` (the same design as the story books', in the product's own
colours and ornament), printed without the section tab and page number (frame `sheet`). `with_about` adds it
to an order's interior as the book's last printed page:

- «دوسية التأسيس», «رحلتي الأولى للتعلّم», «مغامراتي مع عائلتي» (wire-o, printed sheets need an even count):
  the info page goes after the last page; an even book also gets a plain closing page behind it
  (`closing-blank`), so the count stays even and the info page faces the reader after the certificate;
- «قلبي يعرف الله» (perfect-bound in sheets of four): the volume's last page, «إِلَى اللِّقَاءِ» (`back-page`),
  becomes the info page with its farewell above it (`render.pages.islamic_frame.back_page`), so the volume
  keeps its page count; «رَمَضَانُ وَالْعِيدُ» has its own closing page for it (content/islamic/volumes/r.yaml).
"""

from __future__ import annotations

import dataclasses

from markupsafe import Markup

from qamra_pdf.imprint import Imprint, about_html, look_for, product_name
from qamra_workbook.render.registry import Built, PageContext, page_type
from qamra_workbook.render.spec import BookSpec, PageSpec

ABOUT = "about-qamra"
CLOSING = "closing-blank"
# the products whose interior is printed on sheets of two pages (wire-o): an even page count
EVEN_COUNT = ("foundation", "journey", "family")
_LINES = {"foundation": "workbook"}  # BookSpec.product → the store's line (qamra_pdf.imprint.PRODUCTS)


def imprint_of(book: BookSpec) -> Imprint:
    """The book's imprint, or a sample's: the child and the product, no code (its QR opens /hello)."""
    if book.imprint is not None:
        return book.imprint
    return Imprint(
        child_name=book.child.name,
        gender=book.child.gender,
        product=product_name(_LINES.get(book.product, book.product)),
    )


def about_block(ctx: PageContext, lead: Markup | str | None = None) -> Markup:
    """The block for this page: the book's imprint in its product's look, the child's waving character beside
    «صُنِعَ هذا الكتابُ…» (smaller under a farewell)."""
    figure = ctx.assets.wave or ctx.assets.character
    return about_html(
        imprint_of(ctx.book),
        look_for(ctx.book.product),
        lead=lead,
        compact=lead is not None,  # the farewell takes the top of the page: a little smaller
        hero=figure.resolve().as_uri() if figure else "",
        hero_mm=30.0 if lead else 42.0,
    )


@page_type(ABOUT, frame="sheet")
def about_qamra(ctx: PageContext) -> Built:
    """Qamra's info and the book code (see the module)."""
    return Built({"html": about_block(ctx)})


@page_type(CLOSING, frame="sheet")
def closing_blank(ctx: PageContext) -> Built:
    """The back of the info page's sheet: plain paper with the small moon of Qamra."""
    return Built({})


def with_about(book: BookSpec, imprint: Imprint | None) -> BookSpec:
    """`book` with its «عن قمرة» page (and, for an even wire-o book, the plain page behind it) at the end, and
    the imprint the pages and the back cover print. The Islamic volumes print it on their closing page."""
    if imprint is None:
        return book
    book = dataclasses.replace(book, imprint=imprint)
    if book.product not in EVEN_COUNT or not book.pages:
        return book
    last = book.pages[-1]
    n = last.number
    pages = [
        PageSpec(
            id=f"{book.product}-about",
            type=ABOUT,
            number=n + 1,
            section=last.section,
            title="عن قمرة",
            instruction="معلومات الكتاب والتواصل",
        )
    ]
    if (n + 1) % 2:  # keep the sheet whole: a plain page behind the info page
        pages.append(
            PageSpec(
                id=f"{book.product}-closing",
                type=CLOSING,
                number=n + 2,
                section=last.section,
                title="صفحة الختام",
                instruction="صفحة فارغة",
            )
        )
    return dataclasses.replace(book, pages=(*book.pages, *pages))
