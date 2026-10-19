"""«عن قمرة» in every activity book (owner, 2026-10-19): the last printed page carries the book's code, the
child's name, the product and part, Qamra's contacts and a QR to `https://qamra.app/b/<code>`; the back cover
prints the code small. The page counts stay whole: the wire-o books stay even (the info page, then a plain
page behind it when needed), the Islamic volumes stay multiples of four (the info page is their closing page,
«إِلَى اللِّقَاءِ», with the farewell above it; «رمضان والعيد» has its own closing page for it).
"""

import dataclasses
import datetime as dt
import re

import pytest
from printed_qr import about_urls, route
from qamra_workbook import islamic
from qamra_workbook.family import book_pages
from qamra_workbook.family import load as load_family
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render import islamic_volume as iv
from qamra_workbook.render.engine import book_html, build_pages
from qamra_workbook.render.family import PLAN as FAMILY_PLAN
from qamra_workbook.render.family import cover_specs as family_covers
from qamra_workbook.render.family import plan_pages
from qamra_workbook.render.family_order import family_spec
from qamra_workbook.render.islamic_content import IslamicContext
from qamra_workbook.render.islamic_figures import Kit
from qamra_workbook.render.journey_order import stage_specs
from qamra_workbook.render.pages.about_qamra import ABOUT, CLOSING, with_about
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import BookSpec, Child, Family, Member
from qamra_workbook.render.workbook import volume_specs
from test_islamic_pages import DATE, fake_resolver

from qamra_pdf.imprint import Imprint, phone_text

ASSETS = Assets(LibraryStore())
GIRL = Child("ليان", "f")
BOY = Child("يوسف", "m")
FAMILY = Family("الخطيب", (Member("ماما", scarf=True), Member("بابا")), "رام الله")
DAY = dt.date(2026, 10, 19)


def imprint(child: Child, code: str, product: str, part: str = "") -> Imprint:
    return Imprint(code, child.name, child.gender, product, part, made_on=DAY)


def html_of(book: BookSpec) -> str:
    return book_html(book, build_pages(book, ASSETS), ASSETS)


def check_info(html: str, im: Imprint) -> None:
    """The code (large, exact), the child, the product, every contact, a QR that opens the book's page."""
    assert html.count(f'data-book-code="{im.code}"') >= 1 and f'<span class="val">{im.code}</span>' in html
    assert "صُنِعَ هذا الكتابُ خِصّيصًا" in html and im.product in html
    for value in (phone_text("+970595870228"), phone_text("+972595870228"), "info@qamra.app", "qamra.app"):
        assert value in html
    assert "facebook.com/qamrabooks" in html and "@qamra.app" in html
    assert "جميع الحقوق محفوظة © قمرة" in html and "تاريخ الإعداد: تشرين الأول ٢٠٢٦" in html
    urls = about_urls(html)
    assert urls == [f"https://qamra.app/b/{im.code}"], urls
    assert route(urls[0]) == ("book", {"code": im.code})


def back_code(html: str, code: str) -> None:
    assert re.search(rf'class="qab-back-code"[^>]*data-book-code="{code}"', html), "no code on the back cover"


@pytest.mark.parametrize("child", [GIRL, BOY])
def test_the_foundation_volume_ends_with_its_info_page(child: Child) -> None:
    interior, cover, _, _ = volume_specs(child, "kg1", 1, name_en="Layan")
    n = len(interior.pages)
    im = imprint(child, "QB-7K4M2", "دوسية التأسيس", "KG1 · الجزء الأول")
    book = with_about(interior, im)
    assert [p.type for p in book.pages[n:]] == ([ABOUT, CLOSING] if n % 2 == 0 else [ABOUT])
    assert len(book.pages) % 2 == 0 and [p.number for p in book.pages] == list(range(1, len(book.pages) + 1))
    last = dataclasses.replace(book, pages=book.pages[n:])
    html = html_of(last)
    check_info(html, im)
    assert f"خِصّيصًا لِـ{child.name}" in html  # «صُنِعَ هذا الكتابُ خِصّيصًا لِـليان» (as the title page)
    back_code(html_of(dataclasses.replace(cover, imprint=im)), im.code)


def test_the_journey_stage_ends_with_its_info_page() -> None:
    interior, cover = stage_specs(GIRL, 1, name_en="Layan")
    n = len(interior.pages)
    im = imprint(GIRL, "QB-4TPE8", "رحلتي الأولى للتعلّم", "المرحلة الأولى")
    book = with_about(interior, im)
    assert book.pages[n].type == ABOUT and len(book.pages) % 2 == 0
    check_info(html_of(dataclasses.replace(book, pages=book.pages[n:])), im)
    back_code(html_of(dataclasses.replace(cover, imprint=im)), im.code)


def test_the_family_book_ends_with_its_info_page() -> None:
    plan = load_family(FAMILY_PLAN)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    im = imprint(BOY, "QB-W5NK2", "مغامراتي مع عائلتي")
    book = with_about(family_spec(tuple(specs), BOY, FAMILY), im)
    assert book.pages[len(specs)].type == ABOUT and len(book.pages) % 2 == 0
    check_info(html_of(dataclasses.replace(book, pages=book.pages[len(specs) :])), im)
    cover = dataclasses.replace(family_spec(tuple(family_covers(plan)), BOY, FAMILY), imprint=im)
    back_code(html_of(cover), im.code)


@pytest.mark.parametrize("vid", ["V1", "R"])
def test_the_islamic_volume_closes_on_its_info_page(vid: str) -> None:
    plan, resolver = islamic.load(), fake_resolver()
    context = IslamicContext(resolver, Kit(), "preview", DATE)
    content = iv.check_volume(plan, vid, resolver)
    book = iv.volume_book(plan, content, context, GIRL)
    assert len(book.pages) % 4 == 0 and len(book.pages) == (120 if vid == "V1" else 76)
    im = imprint(GIRL, "QB-HX7RD", "قلبي يعرف الله", "المجلد الأول")
    with_info = with_about(book, im)
    assert len(with_info.pages) == len(book.pages)  # the closing page carries it: no page added
    last = dataclasses.replace(with_info, pages=with_info.pages[-1:])
    html = html_of(last)
    check_info(html, im)
    assert "أَحْسَنْتِ يَا ليان" in html  # the farewell stays, above the info
    assert 'class="qab-lead"' in html
    plain = html_of(dataclasses.replace(book, pages=book.pages[-1:]))
    assert "data-book-code" not in plain  # a sample (no code): the farewell page as before
    cover = dataclasses.replace(iv.cover_book(plan, vid, context, book), imprint=im)
    back_code(html_of(cover), im.code)


def test_a_book_without_a_code_gets_no_info_page() -> None:
    interior, _, _, _ = volume_specs(GIRL, "kg1", 1, name_en="Layan")
    assert with_about(interior, None) is interior
