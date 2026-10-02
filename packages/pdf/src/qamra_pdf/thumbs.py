"""Phone-thumbnail check for cover lettering (Addendum 11 §2 acceptance): the front cover in each title
treatment, rasterized from the print PDF at 300 × 300 px (trim only, as a parent sees it on a phone)."""

import asyncio
import dataclasses
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

from qamra_pdf.assets import prepare
from qamra_pdf.lettering import TITLE_STYLES
from qamra_pdf.render import _to_pdf, render_html
from qamra_pdf.spec import BookSpec


async def front_pdfs(spec: BookSpec, out_dir: Path, styles: tuple[str, ...] = TITLE_STYLES) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = prepare(None, None, out_dir)
    pdfs: list[Path] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            for style in styles:
                one = dataclasses.replace(spec, title_style=style)
                html = out_dir / f"front-{style}.html"
                html.write_text(render_html("front.html.j2", one, assets=assets), encoding="utf-8")
                pdf = out_dir / f"front-{style}.pdf"
                await _to_pdf(browser, html, pdf, spec.page_mm, spec.page_mm, None)
                pdfs.append(pdf)
        finally:
            await browser.close()
    return pdfs


def thumbnail(pdf: Path, px: int, bleed_mm: float, page_mm: float) -> Image.Image:
    doc = pdfium.PdfDocument(str(pdf))
    try:
        scale = px / ((page_mm - 2 * bleed_mm) / 25.4 * 72)
        im: Image.Image = doc[0].render(scale=scale).to_pil().convert("RGB")
    finally:
        doc.close()
    cut = round(bleed_mm / page_mm * im.width)
    return im.crop((cut, cut, im.width - cut, im.height - cut)).resize((px, px), Image.Resampling.LANCZOS)


async def cover_thumbs(spec: BookSpec, out_png: Path, *, px: int = 300) -> Path:
    """One sheet with the front cover in every title treatment at `px` × `px`, labelled."""
    pdfs = await front_pdfs(spec, out_png.parent / "fronts")
    thumbs = [thumbnail(p, px, spec.bleed_mm, spec.page_mm) for p in pdfs]
    gap, label = 16, 26
    sheet = Image.new("RGB", (len(thumbs) * (px + gap) + gap, px + 2 * gap + label), "#EDE6D8")
    draw = ImageDraw.Draw(sheet)
    for i, (im, style) in enumerate(zip(thumbs, TITLE_STYLES, strict=False)):
        x = gap + i * (px + gap)
        sheet.paste(im, (x, gap))
        draw.text((x, gap + px + 6), style, fill="#16204A")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return out_png


def cover_thumbs_sync(spec: BookSpec, out_png: Path, *, px: int = 300) -> Path:
    return asyncio.run(cover_thumbs(spec, out_png, px=px))
