"""HTML/CSS → print PDF with Playwright Chromium. Fonts are embedded (local OFL TTFs)."""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

from qamra_pdf.spec import BookSpec
from qamra_pdf.strings import STRINGS

PKG_DIR = Path(__file__).parent
FONTS_DIR = PKG_DIR / "fonts"

_env = Environment(
    loader=FileSystemLoader(PKG_DIR / "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_html(template: str, spec: BookSpec) -> str:
    return _env.get_template(template).render(spec=spec, s=STRINGS[spec.lang], fonts=FONTS_DIR.as_uri())


@dataclass(frozen=True)
class RenderedBook:
    interior_pdf: Path
    cover_pdf: Path
    interior_html: Path
    cover_html: Path


async def _html_to_pdf(html_path: Path, pdf_path: Path, page_mm: float) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(html_path.as_uri(), wait_until="load")
            await page.evaluate("document.fonts.ready.then(() => true)")
            await page.pdf(
                path=str(pdf_path),
                width=f"{page_mm}mm",
                height=f"{page_mm}mm",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
        finally:
            await browser.close()


async def render_book(spec: BookSpec, out_dir: Path) -> RenderedBook:
    """Writes interior.pdf (title, story pages, keepsake) and cover.pdf (front + back)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    interior_html = out_dir / "interior.html"
    cover_html = out_dir / "cover.html"
    interior_html.write_text(render_html("interior.html.j2", spec), encoding="utf-8")
    cover_html.write_text(render_html("cover.html.j2", spec), encoding="utf-8")
    interior_pdf, cover_pdf = out_dir / "interior.pdf", out_dir / "cover.pdf"
    await _html_to_pdf(interior_html, interior_pdf, spec.page_mm)
    await _html_to_pdf(cover_html, cover_pdf, spec.page_mm)
    return RenderedBook(interior_pdf, cover_pdf, interior_html, cover_html)
