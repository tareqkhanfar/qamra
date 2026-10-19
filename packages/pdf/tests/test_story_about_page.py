"""«عن قمرة» (qamra_pdf.imprint): the info page at the end of every story book, and the code on its back.

The page prints the book code (as stored on the book), the child and the product, Qamra's contacts and a QR
that a phone reads as `https://qamra.app/b/<code>`; it fits its page (nothing overflows), passes the print
preflight, and an English book prints it in English.
"""

import asyncio
import dataclasses
import datetime as dt
import re
import unicodedata
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
import pytest
from playwright.async_api import async_playwright
from pypdf import PdfReader
from test_render import _spec

from qamra_pdf import PageSpec, preflight, render_book
from qamra_pdf.imprint import Contact, Imprint, about_html, look_for, phone_text, product_name
from qamra_pdf.render import RenderedBook

DAY = dt.date(2026, 10, 19)
CODE = "QB-7K4M2"


def test_contacts_print_as_the_owner_gave_them() -> None:
    c = Contact()
    assert phone_text(c.phone) == "+970 59 587 0228" and phone_text(c.whatsapp) == "+972 59 587 0228"
    assert phone_text("00970595870228") == "+970 59 587 0228"
    assert c.email == "info@qamra.app" and c.site == "qamra.app"
    assert c.facebook_text == "facebook.com/qamrabooks" and c.instagram_text == "@qamra.app"
    assert Contact(instagram="https://instagram.com/qamra.app").instagram_text == "@qamra.app"


def test_the_page_names_the_child_and_opens_the_book_page() -> None:
    im = Imprint(CODE, "أبو بكر", "m", product_name("magic"), made_on=DAY)
    assert im.url == f"https://qamra.app/b/{CODE}"
    assert im.made_for() == "صُنِعَ هذا الكتابُ خِصّيصًا لِأبي بكر"  # the genitive after «لِـ»
    assert Imprint(child_name="المعتصم").made_for().endswith("لِلمعتصم")
    assert im.month() == "تشرين الأول ٢٠٢٦" and im.year() == "٢٠٢٦"
    assert Imprint().url == "https://qamra.app/hello"  # a sample: the general contact page
    en = Imprint(CODE, "Salma", "f", product_name("magic", "en"), lang="en", made_on=DAY)
    assert en.made_for() == "This book was made especially for Salma" and en.month() == "October 2026"
    html = about_html(im, look_for("magic"))
    assert f'<span class="val">{CODE}</span>' in html and 'data-about-qr="https://qamra.app/b/' in html
    assert "data-book-code" not in about_html(Imprint(child_name="سلمى"), look_for("magic"))


@pytest.fixture(scope="module", params=["ar", "en"])
def story(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, RenderedBook]:
    lang = request.param
    tmp = tmp_path_factory.mktemp(f"about-{lang}")
    spec = _spec(tmp)
    if lang == "ar":
        im = Imprint(CODE, "سَلْمَى", "f", "قمرة سحري", "سلمى في أوّل يوم بالروضة", made_on=DAY)
    else:
        im = Imprint(CODE, "Salma", "f", "Qamra Magic", "Salma's First Day", lang="en", made_on=DAY)
    pages = [*spec.pages[:-1], PageSpec(8, "about", "right")]  # the last page of the signature
    spec = dataclasses.replace(spec, pages=pages, imprint=im, series="magic", lang=lang)
    return tmp, asyncio.run(render_book(spec, tmp, proof=False))


def _text(pdf: Path, page: int) -> str:
    raw = PdfReader(pdf).pages[page].extract_text()
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", raw))  # the code is letter-spaced


def test_the_last_page_prints_the_code_and_a_working_qr(story: tuple[Path, RenderedBook]) -> None:
    _, files = story
    assert files.interior_pdf is not None and files.cover_pdf is not None
    last = len(PdfReader(files.interior_pdf).pages) - 1
    text = _text(files.interior_pdf, last)
    # (a PDF reader drops the «+» and «@» of the left-to-right runs inside Arabic; the picture has them)
    assert CODE in text and "info@qamra.app" in text and "970595870228" in text and "972595870228" in text
    assert "facebook.com/qamrabooks" in text and "qamra.app" in text
    assert CODE in _text(files.cover_pdf, 0)  # small on the back cover
    page = pdfium.PdfDocument(str(files.interior_pdf))[last]
    image = np.asarray(page.render(scale=300 / 72).to_pil().convert("L"))  # the print resolution
    assert cv2.QRCodeDetector().detectAndDecode(image)[0] == f"https://qamra.app/b/{CODE}"


def test_the_page_fits_and_passes_preflight(story: tuple[Path, RenderedBook]) -> None:
    tmp, files = story
    assert files.interior_pdf is not None
    report = preflight(files.interior_pdf, width_mm=216, height_mm=216, bleed_mm=3, safe_mm=10)
    assert report.passed, report.to_dict()

    async def overflow() -> list[str]:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page()
            await page.goto((tmp / "interior.html").as_uri())
            await page.evaluate("document.fonts.ready.then(() => true)")
            out: list[str] = await page.evaluate(
                """() => {
                  const box = document.querySelector('.qab');
                  const outer = box.getBoundingClientRect();
                  const out = [];
                  if (box.scrollHeight > box.clientHeight + 1) out.push('the block');
                  const parts = '.qab-head, .qab-who, .qab-code, .qab-warm, .qab-contact, .qab-foot';
                  for (const el of box.querySelectorAll(parts)) {
                    const r = el.getBoundingClientRect();
                    if (r.bottom > outer.bottom + 0.5 || r.top < outer.top - 0.5) out.push(el.className);
                  }
                  for (const el of box.querySelectorAll('.qab-list .val, .qab-code .val')) {
                    if (el.scrollWidth > el.clientWidth + 1) out.push(el.textContent);
                  }
                  return out;
                }"""
            )
            await browser.close()
            return out

    assert asyncio.run(overflow()) == []
