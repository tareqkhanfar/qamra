"""Plain documents (invoices, proposals, guides): HTML → A4 PDF with the same Chromium as the books."""

from pathlib import Path

from playwright.async_api import async_playwright


async def html_to_pdf(html: str, out: Path, *, footer: str | None = None) -> Path:
    """Render `html` to an A4 PDF. `footer` is a Chromium footer template, e.g. with a pageNumber span."""
    source = out.with_suffix(".html")
    source.write_text(html, encoding="utf-8")
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                page = await browser.new_page()
                await page.goto(source.as_uri(), wait_until="load")
                await page.evaluate("document.fonts.ready.then(() => true)")
                await page.pdf(
                    path=str(out),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    display_header_footer=footer is not None,
                    header_template="<span></span>",
                    footer_template=footer or "<span></span>",
                )
            finally:
                await browser.close()
    finally:
        source.unlink(missing_ok=True)
    return out
