"""The activity books' reading font (owner's choice of 2026-10-17): Arabic text the child or a parent
reads prints in Scheherazade New (SIL OFL), Latin letters and digits stay in IBM Plex Sans Arabic, titles
in Qamra Display; every font embeds as TrueType, never Type 3."""

import asyncio
import datetime as dt
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import book_html, build_pages, print_pdf
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import BookSpec, Child, PageSpec

from qamra_pdf.render import FONTS_DIR

ASSETS = Assets(LibraryStore())


def _page(n: int, kind: str, section: str, **params: Any) -> PageSpec:
    lang = params.pop("lang", "ar")
    return PageSpec(
        id=f"font-p{n}",
        type=kind,
        number=n,
        section=section,
        title="{ساعد/ساعدي} {child}",
        instruction="{اُنْظُرْ/اُنْظُري} إِلى الصُّوَرِ، ثُمَّ {ضَعْ/ضَعي} دائِرَةً حَوْلَ المُخْتَلِفِ",
        lang=lang,
        instruction_en="Trace the letters." if lang == "en" else "",
        stage=1,
        audio=kind == "en-letter",
        params=params,
    )


def _fonts(pdf: Path) -> dict[str, str]:
    """Base font name (without the subset prefix) → its subtype, over every page."""
    out: dict[str, str] = {}
    for page in PdfReader(pdf).pages:
        resources: Any = page["/Resources"].get_object()
        fonts = resources.get("/Font", {})
        for ref in fonts.values():
            font = ref.get_object()
            name = str(font["/BaseFont"]).split("+")[-1]
            out[name] = str(font["/Subtype"])
    return out


def test_the_reading_font_ships_with_its_licence() -> None:
    for weight in ("Regular", "SemiBold", "Bold"):
        assert (FONTS_DIR / f"ScheherazadeNew-{weight}.ttf").is_file()
    licence = (FONTS_DIR / "OFL-ScheherazadeNew.txt").read_text(encoding="utf-8")
    assert "SIL Open Font License, Version 1.1" in licence and "Scheherazade" in licence


def test_arabic_prints_in_scheherazade_latin_in_plex_all_truetype(tmp_path: Path) -> None:
    book = BookSpec(
        "journey",
        "رحلتي الأولى للتعلّم",
        Child("ليان", "f"),
        (_page(6, "odd-one-out", "think", seed=6), _page(30, "en-letter", "english", lang="en", letter="A")),
        dt.date(2026, 10, 17),
    )
    pages = build_pages(book, ASSETS)
    html = book_html(book, pages, ASSETS)
    assert 'font-family: "Scheherazade New"' in html and "unicode-range" in html
    assert "overflow: clip visible" in html  # _reading_font.css.j2: labels clip sideways only
    pdf = asyncio.run(print_pdf(html, tmp_path / "b.html", tmp_path / "b.pdf", book.geometry))
    fonts = _fonts(pdf)
    assert any(name.startswith("ScheherazadeNew") for name in fonts), fonts  # the instructions
    assert any(name.startswith("IBMPlexSansArabic") for name in fonts), fonts  # «Trace the letters.», digits
    assert any(name.startswith("QamraDisplay") for name in fonts), fonts  # the titles
    assert all(subtype != "/Type3" for subtype in fonts.values()), fonts
