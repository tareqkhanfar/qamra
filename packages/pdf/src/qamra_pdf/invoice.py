"""Arabic invoices (Addendum 4 §5): A4, with the book fonts, rendered by the same Chromium as the books."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

PKG_DIR = Path(__file__).parent
FONTS_DIR = PKG_DIR / "fonts"
_env = Environment(
    loader=FileSystemLoader(PKG_DIR / "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True)
class InvoiceLine:
    name: str
    detail: str
    qty: int
    unit_price: Decimal
    total: Decimal


@dataclass(frozen=True)
class InvoiceSpec:
    number: str
    issued: date
    order_code: str
    company: str
    customer: str
    currency: str  # ILS | JOD
    lines: list[InvoiceLine]
    subtotal: Decimal
    discount: Decimal
    delivery: Decimal
    total: Decimal
    payment: str
    company_details: list[str] = field(default_factory=list)  # address, phone, tax number
    customer_details: list[str] = field(default_factory=list)  # phone, city, address


def money(amount: Decimal, currency: str) -> str:
    value = f"{amount:.2f}"
    return f"{value} ₪" if currency == "ILS" else f"{value} د.أ"


def invoice_html(spec: InvoiceSpec) -> str:
    return _env.get_template("invoice.html.j2").render(spec=spec, fonts=FONTS_DIR.as_uri(), money=money)


async def render_invoice(spec: InvoiceSpec, out: Path) -> Path:
    html = out.with_suffix(".html")
    html.write_text(invoice_html(spec), encoding="utf-8")
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                page = await browser.new_page()
                await page.goto(html.as_uri(), wait_until="load")
                await page.evaluate("document.fonts.ready.then(() => true)")
                await page.pdf(path=str(out), format="A4", print_background=True, prefer_css_page_size=True)
            finally:
                await browser.close()
    finally:
        html.unlink(missing_ok=True)
    return out
