"""Page specs → HTML (Jinja2) → print PDF (Playwright Chromium), previews and a contact sheet.

Follows `qamra_pdf.render`: static fonts from qamra_pdf (embedded as TrueType, never Type 3), CSS page size
with the bleed included, then exact MediaBox/TrimBox/BleedBox via `qamra_pdf.render.set_boxes`. Text that
changes with the child and family (names, the parent box) is marked `data-fit="<min pt>"`: it shrinks in
0.5 pt steps until it fits its box, and a page where it still overflows is never printed.
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
from qamra_workbook.render.covers import COVER_FIT_JS
from qamra_workbook.render.registry import Assets, Built, PageContext, PageType, lookup
from qamra_workbook.render.sections import PATTERNS, SectionStyle, section_style, tab_top
from qamra_workbook.render.spec import (
    BookSpec,
    Geometry,
    Numerals,
    PageSpec,
    Side,
    format_number,
    leftover_placeholders,
    minutes_ar,
)

logging.getLogger("pypdf").setLevel(logging.ERROR)

TEMPLATES = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.globals.update(
    icon=art.icon,
    mascot=art.mascot,
    stars=art.stars,
    minutes_ar=minutes_ar,
    patterns=PATTERNS,
    tab_top=tab_top,
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
    parent: tuple[str, ...] = ()  # the «للأهل» box, personalized
    section_name: str = ""  # the section's name as printed for this child
    numerals: Numerals = "hindi"  # the page's numerals: the book's choice, or Latin on an English page
    skill: str = ""  # the skill line for grown-ups, as printed
    instruction_en: str = ""  # an English page's instruction, as printed

    def num(self, value: int | str) -> str:
        """A number in the page's work area (templates: `p.num(n)`); `book.num` for the book's furniture."""
        return format_number(value, self.numerals)


MAX_PARENT_LINES = 3  # A7 §5


def build_pages(book: BookSpec, assets: Assets) -> list[RenderedPage]:
    """Run every page's builder and checks; raise when any check fails."""
    rendered, failures = [], []
    for spec in book.pages:
        kind = lookup(spec.type)
        ctx = PageContext(spec, book, assets)
        built = kind.build(ctx)
        title, instruction = ctx.text(spec.title), ctx.text(spec.instruction)
        parent = tuple(ctx.text(line) for line in spec.parent)
        problems = list(built.problems)
        if len(parent) > MAX_PARENT_LINES:
            problems.append(f"the parent box has {len(parent)} lines (max {MAX_PARENT_LINES})")
        for text in (title, instruction, *parent):
            if leftover_placeholders(text):
                problems.append(f"unresolved {leftover_placeholders(text)} in {text!r}")
        failures += [f"{spec.id} ({spec.type}): {p}" for p in problems]
        rendered.append(
            RenderedPage(
                spec,
                kind,
                built,
                section_style(spec.section, book.product),
                book.side(spec.number),
                title,
                instruction,
                book.folio(spec.number),
                qr_svg(book.audio_url(spec)) if spec.audio else None,
                parent,
                ctx.text(ctx.style.name_ar),
                ctx.numerals,
                ctx.text(spec.skill),
                ctx.text(spec.instruction_en),
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


# Shrink every `[data-fit]` box's text until it fits (down to its minimum), then list what still overflows:
# one-line text (white-space: nowrap) by its width, a box of lines by its height, and the work area of every
# page that lays out its content in the frame (so nothing runs into the footer or out of the safe area).
_FIT_JS = """
() => {
  const over = (el) => getComputedStyle(el).whiteSpace.startsWith('nowrap')
    ? el.scrollWidth > el.clientWidth + 1
    : el.scrollHeight > el.clientHeight + 1;
  const pageOf = (el) => { const page = el.closest('[data-page]'); return page ? page.dataset.page : '?'; };
  const out = [];
  for (const el of document.querySelectorAll('[data-fit]')) {
    const min = parseFloat(el.dataset.fit);
    let pt = Math.round(parseFloat(getComputedStyle(el).fontSize) * 75) / 100;
    while (over(el) && pt > min) { pt -= 0.5; el.style.fontSize = pt + 'pt'; }
    if (over(el)) out.push(pageOf(el) + ': ' + el.textContent.trim().slice(0, 60));
  }
  const works = document.querySelectorAll('.frame-mission > .safe > .work, .frame-sheet > .safe > .work');
  for (const work of works) {
    if (work.scrollHeight > work.clientHeight + 2) out.push(pageOf(work) + ': taller than its work area');
  }
  return out;
}
"""


async def print_pdf(html: str, html_path: Path, pdf_path: Path, geometry: Geometry) -> Path:
    """HTML → PDF with the exact page size and print boxes. Raises `PageProblems` (and prints nothing)
    when personalized text overflows its box even at its smallest size, or a page's content is taller than
    its work area."""
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(html_path.resolve().as_uri(), wait_until="load")
            await page.evaluate("document.fonts.ready.then(() => true)")
            overflowing: list[str] = await page.evaluate(COVER_FIT_JS)  # the covers' lettering first
            overflowing += await page.evaluate(_FIT_JS)
            if overflowing:
                raise PageProblems("does not fit: " + "; ".join(overflowing))
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


def contact_sheet(
    pngs: Sequence[Path], out: Path, labels: Sequence[str], columns: int = 4, *, rtl: bool = False
) -> Path:
    """All pages on one image, in reading order (right to left with `rtl`, so a spread's two pages sit
    side by side as in the open book)."""
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
        column = columns - 1 - i % columns if rtl else i % columns
        x = gap + column * (thumb_w + gap)
        y = gap + (i // columns) * (thumb_h + label_h + gap)
        with Image.open(png) as img:
            thumb = img.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        draw.rectangle((x - 1, y - 1, x + thumb_w, y + thumb_h), outline="#D8C9AC")
        sheet.paste(thumb, (x, y))
        draw.text((x + 2, y + thumb_h + 8), label, fill="#1C2140", font=font)
    sheet.save(out, optimize=True)
    return out
