"""«دفاتر التلوين والرسم»: the four books' page lists, the letters book's content, black-only line art, the
personalized pages (gender, name, the info page with the book code), and one real print with its preflight.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import pytest
from qamra_workbook.coloring.book import cover_pages, interior_pages, page_problems
from qamra_workbook.coloring.checks import line_problems
from qamra_workbook.coloring.cover_art import cover_scene
from qamra_workbook.coloring.glyphs import letter
from qamra_workbook.coloring.letters import letter_panel, load, picture_svg
from qamra_workbook.coloring.parts.qamra import medal_svg, title_vignette
from qamra_workbook.coloring.titles import BY_SLUG, LINE, TITLES, title_of
from qamra_workbook.pictures import PICTURES, LibraryStore, strip_tashkeel
from qamra_workbook.pictures import get as picture
from qamra_workbook.render.engine import book_html, build_pages
from qamra_workbook.render.pages.about_qamra import ABOUT
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import Child

from qamra_pdf.imprint import Imprint

GIRL = Child("ليان", "f")
BOY = Child("يوسف", "m")
ASSETS = Assets(LibraryStore())
ALPHABET = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
READY = list(TITLES)  # every book has its content


def test_titles_and_store_slugs() -> None:
    assert LINE == "colorbook" and len(LINE) <= 16
    assert set(BY_SLUG) == {"coloring-letters", "coloring-palestine", "coloring-ramadan", "sketchbook"}
    for t in TITLES.values():
        assert t.pages % t.signature == 0, t.key
        assert title_of(t.slug) is t
        assert t.printed_format == ("spiral" if t.binding == "wire-o" else "softcover")


def test_the_letters_book_has_every_letter_with_pictures_that_start_with_it() -> None:
    book = load()
    assert "".join(x.char for x in book.letters) == ALPHABET
    for page in book.letters:
        assert 2 <= len(page.pictures) <= 3, page.char
        assert strip_tashkeel(page.name_ar).startswith("حرف ")
        for shown in page.pictures:
            assert shown.picture in PICTURES
            word = strip_tashkeel(shown.word_ar)
            first = (word[2:] if word.startswith("ال") else word)[:1]
            expected = {"ا": "اأإآ"}.get(page.char, page.char)
            assert first in expected, (page.char, shown.picture, shown.word_ar)


@pytest.mark.parametrize("char", list(ALPHABET))
def test_each_letter_is_clean_line_art(char: str) -> None:
    g = letter(char, 100)
    assert g.d and g.w > 5
    assert line_problems(letter_panel(char)) == []


def test_the_pictures_and_front_pages_are_black_and_white() -> None:
    for page in load().letters:
        for shown in page.pictures:
            markup = picture_svg(shown.picture, 52)
            assert line_problems(markup) == [], shown.picture
            assert "#2B2E4A" not in markup  # the library's navy outline is redrawn in black
    assert line_problems(title_vignette()) == [] and line_problems(medal_svg()) == []
    assert line_problems(title_vignette("color"))  # the colour version is colour (the cover)
    assert picture("apple").word_ar


@pytest.mark.parametrize("key", READY)
def test_page_counts_are_whole_sheets_and_end_with_the_info_page(key: str) -> None:
    pages = interior_pages(key)
    assert page_problems(key, pages) == []
    assert pages[0].type == "cb-title" and pages[-1].type == ABOUT
    assert [p.number for p in pages] == list(range(1, len(pages) + 1))
    assert len({p.id for p in pages}) == len(pages)
    assert [p.type for p in cover_pages(key)] == ["cb-cover-front", "cb-cover-back"]


def _book(key: str, child: Child, imprint: Imprint | None = None):  # type: ignore[no-untyped-def]
    from qamra_workbook.coloring.book import book_spec

    return book_spec(key, child, interior_pages(key), day=dt.date(2026, 10, 21), imprint=imprint)


@pytest.mark.parametrize("child", [GIRL, BOY], ids=["girl", "boy"])
def test_the_letters_book_speaks_to_the_child_in_their_gender(child: Child) -> None:
    im = Imprint("QB-7K4M2", child.name, child.gender, "ألوّن حروفي", made_on=dt.date(2026, 10, 21))
    book = _book("letters", child, im)
    html = book_html(book, build_pages(book, ASSETS), ASSETS)
    girl = child.gender == "f"
    assert ("ارْسُمي نَفْسَكِ هُنا" in html) is girl and ("ارْسُمْ نَفْسَكَ هُنا" in html) is not girl
    assert (f"أَحْسَنْتِ يا {child.name}!" in html) is girl
    assert ("صاحِبَةُ هذا الدَّفْتَرِ" in html) is girl
    assert "{" not in html.split("<body", 1)[1].split("<script", 1)[0].replace(
        "{ ", ""
    )  # no placeholder left
    assert 'data-book-code="QB-7K4M2"' in html and "ألوّن حروفي" in html
    assert html.count(child.name) >= 4


def test_the_cover_scene_works_with_and_without_the_character() -> None:
    with_child = cover_scene("letters", 216, 303, hero=True)
    without = cover_scene("letters", 216, 303, hero=False)
    assert "<svg" in with_child and len(without) > len(with_child)  # a drawn centrepiece instead
    assert "<text" not in without


def test_a_printed_copy_passes_preflight_and_its_interior_is_black_and_white(tmp_path: Path) -> None:
    """One real print (Chromium): «أُلَوِّنُ حُروفي» for a boy without a character."""
    from qamra_workbook.render.coloring_order import render_order

    files = asyncio.run(render_order(BOY, "coloring-letters", tmp_path, day=dt.date(2026, 10, 21)))
    assert files.passed, files.preflight
    assert files.pages == 32
    checks = {c["name"]: c["ok"] for c in files.preflight["interior.pdf"]["checks"]}
    assert checks["page_count"] and checks["fonts_embedded"] and checks["bleed_size"]
    doc = pdfium.PdfDocument(files.interior)
    try:
        assert len(doc) == 32
        for i in (0, 1, 5, 30):  # the title page, «اسمي», a letter, the certificate: no colour at all
            image = doc[i].render(scale=40 / 72).to_pil().convert("RGB")
            px = np.asarray(image).astype(int)
            assert int(np.abs(px - px.mean(axis=2, keepdims=True)).max()) < 6, i
    finally:
        doc.close()
