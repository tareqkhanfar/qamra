"""Page specs → HTML (Jinja2) → print PDF (Playwright Chromium), previews and a contact sheet.

Follows `qamra_pdf.render`: static fonts from qamra_pdf (embedded as TrueType, never Type 3), CSS page size
with the bleed included, then exact MediaBox/TrimBox/BleedBox via `qamra_pdf.render.set_boxes`.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

import qamra_workbook.render.pages  # noqa: F401  (importing the builders registers every page type)
from qamra_pdf.render import FONTS_DIR, qr_svg, set_boxes
from qamra_workbook.render import art
from qamra_workbook.render.registry import Assets, Built, PageContext, PageType, lookup
from qamra_workbook.render.sections import PATTERNS, SectionStyle, section_style, tab_top
from qamra_workbook.render.spec import BookSpec, Geometry, PageSpec, Side, arabic_digits

logging.getLogger("pypdf").setLevel(logging.ERROR)

TEMPLATES = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.globals.update(
    icon=art.icon, mascot=art.mascot, arabic_digits=arabic_digits, patterns=PATTERNS, tab_top=tab_top
)


class PageProblems(Exception):
    """A page failed its automated checks; nothing is rendered."""


@dataclass(frozen=True)
class RenderedPage:
    spec: PageSpec
    kind: PageType
    built: Built
    style: SectionStyle
    side: Side
    title: str
    instruction: str
    folio: str
    qr: Markup | None


def build_pages(book: BookSpec, assets: Assets) -> list[RenderedPage]:
    """Run every page's builder and checks; raise when any check fails."""
    rendered, failures = [], []
    for spec in book.pages:
        kind = lookup(spec.type)
        ctx = PageContext(spec, book, assets)
        built = kind.build(ctx)
        failures += [f"{spec.id} ({spec.type}): {p}" for p in built.problems]
        rendered.append(
            RenderedPage(
                spec,
                kind,
                built,
                section_style(spec.section),
                book.side(spec.number),
                ctx.text(spec.title),
                ctx.text(spec.instruction),
                book.folio(spec.number),
                qr_svg(book.audio_url(spec)) if spec.audio else None,
            )
        )
    if failures:
        raise PageProblems("\n".join(failures))
    return rendered


def _render(template: str, **context: Any) -> str:
    return _env.get_template(template).render(fonts=FONTS_DIR.as_uri(), **context)


def book_html(book: BookSpec, pages: Sequence[RenderedPage], assets: Assets, *, solved: bool = False) -> str:
    return _render("book.html.j2", book=book, pages=pages, assets=assets, g=book.geometry, solved=solved)


def answer_key_html(book: BookSpec, pages: Sequence[RenderedPage], assets: Assets) -> str:
    keyed = [p for p in pages if p.built.answer]
    per_sheet = 4
    sheets = [keyed[i : i + per_sheet] for i in range(0, len(keyed), per_sheet)]
    return _render(
        "answer-key.html.j2", book=book, sheets=sheets, assets=assets, g=book.geometry, solved=True
    )


async def print_pdf(html: str, html_path: Path, pdf_path: Path, geometry: Geometry) -> Path:
    """HTML → PDF with the exact page size and print boxes."""
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(html_path.resolve().as_uri(), wait_until="load")
            await page.evaluate("document.fonts.ready.then(() => true)")
            await page.pdf(
                path=str(pdf_path),
                width=f"{geometry.page_w}mm",
                height=f"{geometry.page_h}mm",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
        finally:
            await browser.close()
    set_boxes(pdf_path, geometry.page_w, geometry.page_h, geometry.bleed)
    return pdf_path


def previews(
    pdf_path: Path, out_dir: Path, names: Sequence[str], geometry: Geometry, dpi: int = 100
) -> list[Path]:
    """One PNG per page, cropped to the trim (what the reader sees)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(pdf_path)
    paths = []
    try:
        for i, name in enumerate(names):
            image = doc[i].render(scale=dpi / 72).to_pil()
            b = round(geometry.bleed / 25.4 * dpi)
            image = image.crop((b, b, image.width - b, image.height - b)).convert("RGB")
            path = out_dir / f"{name}.png"
            image.save(path, optimize=True)
            paths.append(path)
    finally:
        doc.close()
    return paths


def contact_sheet(pngs: Sequence[Path], out: Path, labels: Sequence[str], columns: int = 4) -> Path:
    """All pages on one image, in reading order."""
    thumb_w, gap, label_h = 300, 24, 34
    with Image.open(pngs[0]) as first:
        thumb_h = round(first.height * thumb_w / first.width)
    rows = (len(pngs) + columns - 1) // columns
    sheet = Image.new(
        "RGB", (columns * (thumb_w + gap) + gap, rows * (thumb_h + label_h + gap) + gap), "#F3EAD8"
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansArabic-SemiBold.ttf"), 15)
    for i, (png, label) in enumerate(zip(pngs, labels, strict=True)):
        x = gap + (i % columns) * (thumb_w + gap)
        y = gap + (i // columns) * (thumb_h + label_h + gap)
        with Image.open(png) as img:
            thumb = img.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        draw.rectangle((x - 1, y - 1, x + thumb_w, y + thumb_h), outline="#D8C9AC")
        sheet.paste(thumb, (x, y))
        draw.text((x + 2, y + thumb_h + 8), label, fill="#1C2140", font=font)
    sheet.save(out, optimize=True)
    return out
