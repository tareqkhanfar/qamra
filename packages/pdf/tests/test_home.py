"""Home-print copies: every page cut to its TrimBox, the cover around the interior (a story's wrap split into
its front and back panels by the book's language; an activity book's front and back pages)."""

import io

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from qamra_pdf.home import home_book, home_sheets, page_sizes_mm

MM = 72 / 25.4


def print_pdf(pages: int, width_mm: float, height_mm: float, bleed_mm: float = 3.0) -> bytes:
    writer = PdfWriter()
    w, h, b = width_mm * MM, height_mm * MM, bleed_mm * MM
    for _ in range(pages):
        page = writer.add_blank_page(w, h)
        page.trimbox = RectangleObject([b, b, w - b, h - b])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _left_mm(data: bytes) -> list[float]:
    return [round(float(p.mediabox.left) / MM, 1) for p in PdfReader(io.BytesIO(data)).pages]


def test_a_story_wrap_is_split_into_its_front_and_back() -> None:
    interior = print_pdf(4, 216, 216)
    wrap = print_pdf(1, 433.8, 216)  # 3 + 210 + 7.8 spine + 210 + 3
    arabic = home_book(interior, wrap, front_left=True, title="يوم تخرّج ليان")
    assert list(page_sizes_mm(arabic)) == [(210.0, 210.0)] * 6
    # [front | spine | back]: the Arabic front is the wrap's left panel, the back its right one
    assert _left_mm(arabic) == [3.0, 3.0, 3.0, 3.0, 3.0, 220.8]
    english = home_book(interior, wrap, front_left=False)
    assert _left_mm(english) == [220.8, 3.0, 3.0, 3.0, 3.0, 3.0]
    assert PdfReader(io.BytesIO(arabic)).metadata.title == "يوم تخرّج ليان"


def test_an_activity_cover_is_two_pages() -> None:
    book = home_book(print_pdf(3, 216, 286), print_pdf(2, 216, 286))
    assert list(page_sizes_mm(book)) == [(210.0, 280.0)] * 5


def test_a_cover_of_another_shape_is_left_out() -> None:
    lone = home_book(print_pdf(3, 216, 286), print_pdf(1, 216, 286))  # one page: front or back?
    assert len(list(page_sizes_mm(lone))) == 3
    assert len(list(page_sizes_mm(home_book(print_pdf(2, 216, 216))))) == 2  # no cover at all


def test_other_sheets_lose_their_bleed() -> None:
    assert list(page_sizes_mm(home_sheets(print_pdf(2, 216, 303)))) == [(210.0, 297.0)] * 2
    with pytest.raises(ValueError):
        home_sheets(print_pdf(0, 216, 303))
