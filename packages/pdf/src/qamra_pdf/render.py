"""HTML/CSS → print PDFs with Playwright Chromium (Addendum 3 §4).

Outputs, from one Chromium session:
- `interior.pdf`: 216 × 216 mm pages in reading order, fonts embedded;
- `cover.pdf`: one wrap sheet (front | spine | back for right-bound Arabic books);
- `proof.pdf`: the low-res web proof (front, interior, back as squares).

Story text that overflows its panel shrinks in 0.5 pt steps down to the age minimum (18 pt for ages 3–5,
15 pt for 6–8); anything still overflowing is reported for review. Chromium rounds page sizes to CSS pixels,
so the page boxes are rewritten to the exact size and TrimBox/BleedBox are added for the printer.
"""

import io
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from PIL import Image
from playwright.async_api import Browser, async_playwright
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from qamra_pdf.spec import BookSpec
from qamra_pdf.strings import STRINGS

logging.getLogger("pypdf").setLevel(logging.ERROR)  # Chromium's xref trailers trigger harmless warnings

PKG_DIR = Path(__file__).parent
FONTS_DIR = PKG_DIR / "fonts"
MM = 72 / 25.4  # points per millimetre
PROOF_MAX_PX = 900

_env = Environment(
    loader=FileSystemLoader(PKG_DIR / "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

_FIT_JS = """
(minPt) => {
  const out = [];
  for (const box of document.querySelectorAll('[data-panel]')) {
    const text = box.querySelector('.story-text');
    if (!text) continue;
    // computed sizes are CSS px (16 pt = 21.333… px): round to 0.01 pt so an unshrunk size compares equal
    let pt = Math.round(parseFloat(getComputedStyle(text).fontSize) * 75) / 100;
    const over = () => box.scrollHeight > box.clientHeight + 1;
    while (over() && pt > minPt) { pt -= 0.5; text.style.fontSize = pt + 'pt'; }
    out.push({page: Number(box.dataset.panel), pt: pt, overflow: over()});
  }
  return out;
}
"""


def qr_svg(url: str | None) -> Markup | None:
    """QR as an inline vector (sharp at any print size)."""
    if not url:
        return None
    qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    path = "".join(f"M{x} {y}h1v1h-1z" for y, row in enumerate(matrix) for x, on in enumerate(row) if on)
    return Markup(  # nosec B704 (built from a boolean matrix, no user text)
        f'<svg viewBox="0 0 {n} {n}" shape-rendering="crispEdges"><path d="{path}" fill="#16204A"/></svg>'
    )


def render_html(template: str, spec: BookSpec, img: Callable[[Path | None], str] | None = None) -> str:
    def uri(p: Path | None) -> str:
        return p.resolve().as_uri() if p else ""

    return _env.get_template(template).render(
        spec=spec,
        s=STRINGS[spec.lang],
        fonts=FONTS_DIR.as_uri(),
        img=img or uri,
        qr_svg=qr_svg(spec.cover.qr_url),
        qr=qr_svg,
    )


@dataclass(frozen=True)
class TextFit:
    page: int
    pt: float
    overflow: bool


@dataclass
class RenderedBook:
    interior_pdf: Path | None
    cover_pdf: Path | None
    proof_pdf: Path | None
    fit: list[TextFit] = field(default_factory=list)

    @property
    def overflowing_pages(self) -> list[int]:
        return [f.page for f in self.fit if f.overflow]

    @property
    def shrunk_pages(self) -> list[int]:
        return [f.page for f in self.fit if not f.overflow]


def _small_copy(src: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{src.stem}.jpg"
    if not dest.exists():
        with Image.open(src) as original:
            im = original.convert("RGB")
            im.thumbnail((PROOF_MAX_PX, PROOF_MAX_PX), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=78)
            dest.write_bytes(buf.getvalue())
    return dest


def set_boxes(pdf: Path, width_mm: float, height_mm: float, bleed_mm: float) -> None:
    """Exact MediaBox/BleedBox, TrimBox inset by the bleed (what printers expect)."""
    reader = PdfReader(pdf)
    writer = PdfWriter(clone_from=reader)
    w, h, b = width_mm * MM, height_mm * MM, bleed_mm * MM
    for page in writer.pages:
        box = RectangleObject([0, 0, w, h])
        page.mediabox = box
        page.cropbox = RectangleObject([0, 0, w, h])
        page.bleedbox = RectangleObject([0, 0, w, h])
        page.trimbox = RectangleObject([b, b, w - b, h - b])
    with pdf.open("wb") as f:
        writer.write(f)


async def _to_pdf(
    browser: Browser, html_path: Path, pdf_path: Path, width_mm: float, height_mm: float, fit_pt: float | None
) -> list[dict[str, Any]]:
    page = await browser.new_page()
    try:
        await page.goto(html_path.as_uri(), wait_until="load")
        await page.evaluate("document.fonts.ready.then(() => true)")
        fit: list[dict[str, Any]] = []
        if fit_pt is not None:
            fit = await page.evaluate(_FIT_JS, fit_pt)
        await page.pdf(
            path=str(pdf_path),
            width=f"{width_mm}mm",
            height=f"{height_mm}mm",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        return fit
    finally:
        await page.close()


async def render_book(
    spec: BookSpec, out_dir: Path, *, proof: bool = True, print_files: bool = True
) -> RenderedBook:
    out_dir.mkdir(parents=True, exist_ok=True)
    interior_html, cover_html = out_dir / "interior.html", out_dir / "cover.html"
    interior_html.write_text(render_html("interior.html.j2", spec), encoding="utf-8")
    cover_html.write_text(render_html("cover.html.j2", spec), encoding="utf-8")
    proof_html = out_dir / "proof.html"
    if proof:
        small_dir = out_dir / "proof-img"

        def small(p: Path | None) -> str:
            return _small_copy(p, small_dir).resolve().as_uri() if p else ""

        proof_html.write_text(render_html("proof.html.j2", spec, small), encoding="utf-8")

    interior_pdf, cover_pdf, proof_pdf = (
        out_dir / "interior.pdf",
        out_dir / "cover.pdf",
        out_dir / "proof.pdf",
    )
    fit: list[dict[str, Any]] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            if print_files:
                fit = await _to_pdf(
                    browser, interior_html, interior_pdf, spec.page_mm, spec.page_mm, spec.min_text_pt
                )
                await _to_pdf(browser, cover_html, cover_pdf, spec.wrap_width_mm, spec.page_mm, None)
            if proof:
                proof_fit = await _to_pdf(
                    browser, proof_html, proof_pdf, spec.page_mm, spec.page_mm, spec.min_text_pt
                )
                fit = fit or proof_fit
        finally:
            await browser.close()
    if print_files:
        set_boxes(interior_pdf, spec.page_mm, spec.page_mm, spec.bleed_mm)
        set_boxes(cover_pdf, spec.wrap_width_mm, spec.page_mm, spec.bleed_mm)
    fits = [
        TextFit(int(f["page"]), float(f["pt"]), bool(f["overflow"]))
        for f in fit
        if f["pt"] < spec.text_pt or f["overflow"]
    ]
    return RenderedBook(
        interior_pdf if print_files else None,
        cover_pdf if print_files else None,
        proof_pdf if proof else None,
        fits,
    )
