"""Home-print PDFs (docs/plans/digital-delivery.md): the print files without the printer's bleed.

The print files carry a 3 mm bleed on every side, with exact TrimBox/BleedBox (`render.set_boxes`) and no crop
marks. A family printing at home wants the page as the reader sees it, so every page here is cut to its
TrimBox (MediaBox = CropBox = TrimBox): nothing is re-rendered, the pages keep their vector text, fonts and
300 DPI pictures.

`home_book` also puts the cover around the interior: the front first and the back last.
- Activity books keep their cover as two pages of the interior's size: front, then back.
- A story's cover is one wrap laid out as the printer sees the flat sheet: [front | spine | back] for an
  Arabic book (bound on the right), [back | spine | front] for an English one. Each panel is the interior's
  trim width; the spine is whatever is left in the middle, so the formula behind it (pages, paper, boards)
  never matters here.
"""

import io
from collections.abc import Iterable

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import RectangleObject

MM = 72 / 25.4
SAME_SIZE_PT = 2 * MM  # a cover page this close to the interior's trim width is a page, not a wrap


def _box(page: PageObject) -> RectangleObject:
    """The page as the reader sees it: its TrimBox (pypdf falls back to the CropBox, then the MediaBox)."""
    box: RectangleObject = page.trimbox
    return box


def _cut(page: PageObject, rect: tuple[float, float, float, float]) -> None:
    box = RectangleObject(rect)
    page.mediabox = box
    page.cropbox = box
    page.bleedbox = box
    page.trimbox = box
    page.artbox = box


def _trim(page: PageObject) -> None:
    t = _box(page)
    _cut(page, (float(t.left), float(t.bottom), float(t.right), float(t.top)))


def _panel(page: PageObject, width: float, *, left: bool) -> None:
    """Cut a wrap down to its left or right panel (the trim's outer `width`)."""
    t = _box(page)
    x0 = float(t.left) if left else float(t.right) - width
    _cut(page, (x0, float(t.bottom), x0 + width, float(t.top)))


def _write(writer: PdfWriter, title: str | None) -> bytes:
    writer.compress_identical_objects()  # merges the two wrap panels' identical pictures
    meta = {"/Producer": "Qamra"}
    if title:
        meta["/Title"] = title
    writer.add_metadata(meta)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _cover_pages(
    cover: bytes, trim_width: float, *, front_left: bool
) -> tuple[PageObject, PageObject] | None:
    """The cover's front and back, each cut to one panel; None when the file is neither shape."""
    first = PdfReader(io.BytesIO(cover)).pages
    if not first:
        return None
    width = float(_box(first[0]).width)
    if abs(width - trim_width) <= SAME_SIZE_PT:  # front and back as pages (the activity books)
        front, back = first[0], first[-1]
        if len(first) < 2:
            return None
        _trim(front)
        _trim(back)
        return front, back
    if len(first) != 1 or width < 2 * trim_width:
        return None
    # one wrap: two readers, so the two panels are two page objects (identical pictures are merged on write)
    front = first[0]
    back = PdfReader(io.BytesIO(cover)).pages[0]
    _panel(front, trim_width, left=front_left)
    _panel(back, trim_width, left=not front_left)
    return front, back


def home_book(
    interior: bytes, cover: bytes | None = None, *, front_left: bool = True, title: str | None = None
) -> bytes:
    """The book for home printing: the front cover, every interior page, the back cover, all without bleed.

    `front_left`: the wrap's front panel is on the left (Arabic books); False for English books.
    A cover that is neither a wrap nor front/back pages is left out rather than printed wrong.
    """
    reader = PdfReader(io.BytesIO(interior))
    if not reader.pages:
        raise ValueError("the interior has no pages")
    trim_width = float(_box(reader.pages[0]).width)
    panels = _cover_pages(cover, trim_width, front_left=front_left) if cover else None
    writer = PdfWriter()
    pages: list[PageObject] = []
    if panels:
        pages.append(writer.add_page(panels[0]))
    for page in reader.pages:
        added = writer.add_page(page)
        _trim(added)
        pages.append(added)
    if panels:
        pages.append(writer.add_page(panels[1]))
    return _write(writer, title)


def home_sheets(pdf: bytes, *, title: str | None = None) -> bytes:
    """Any other print file (an answer key, a sticker or card sheet) without its bleed."""
    reader = PdfReader(io.BytesIO(pdf))
    if not reader.pages:
        raise ValueError("the file has no pages")
    writer = PdfWriter()
    for page in reader.pages:
        _trim(writer.add_page(page))
    return _write(writer, title)


def page_sizes_mm(pdf: bytes) -> Iterable[tuple[float, float]]:
    """Each page's visible size in mm (tests and the job's log)."""
    for page in PdfReader(io.BytesIO(pdf)).pages:
        box = page.cropbox
        yield round(float(box.width) / MM, 1), round(float(box.height) / MM, 1)
