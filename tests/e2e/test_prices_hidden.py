"""«إخفاء الأسعار» (Tareq, 2026-10-16): with the admin switch «إظهار الأسعار للزبائن» (`show_prices`) off, a
customer meets no price anywhere: not on the public pages, nor from the format step to the cart, the checkout
and the order page. The order still records its price (the staff see it), and /pricing leads to the shop.

The other E2E tests run with the prices shown (conftest.py); these hide them and show them again after.
"""

import re
from collections.abc import Iterator
from decimal import Decimal

import pytest
from e2e_flow import BASE_URL, checkout, order, preview_book, show_prices
from playwright.sync_api import Page, expect

# what a price looks like on the page: the currency, the words for price, total and discount, a comparison
PRICE = re.compile(r"₪|شيكل|JOD|\bJD\b|ILS|د\.أ|سعر|أسعار|المجموع|خصم|أوفر")
PUBLIC = [
    "",
    "/stories",
    "/stories/olive-season",
    "/shop",
    "/workbooks",
    "/workbooks/foundation-workbook",
    "/workbooks/family-adventures",
    "/how-it-works",
    "/kindergartens",
    "/quiz",
]


@pytest.fixture(autouse=True)
def prices_hidden() -> Iterator[None]:
    show_prices(False)
    yield
    show_prices(True)


def no_price(page: Page) -> None:
    """Nothing the visitor can read on the screen is a price."""
    page.wait_for_load_state("networkidle")
    text = page.locator("body").inner_text()
    found = sorted({m.group(0) for m in PRICE.finditer(text)})
    assert not found, f"{page.url}: {found}"


def test_the_public_pages_show_no_price(page: Page) -> None:
    for path in PUBLIC:
        page.goto(f"{BASE_URL}/ar{path}")
        no_price(page)
    nav = page.get_by_role("navigation").first
    expect(nav.get_by_role("link", name="الأسعار")).to_have_count(0)  # no prices page in the menu
    expect(page.locator("footer").get_by_role("link", name="الأسعار")).to_have_count(0)
    page.goto(f"{BASE_URL}/ar/pricing")
    page.wait_for_url("**/ar/shop")  # the prices page leads to the shop


def test_an_order_from_the_format_to_the_order_page_without_a_price(page: Page) -> None:
    book = preview_book(page, name="ليان", gender="f", hijab=True, line="classic", theme="olive-season")
    page.goto(f"{BASE_URL}/ar/create?step=format&child={book['child_id']}&book={book['book_id']}")
    page.get_by_text("غلاف ورقي", exact=True).click()
    no_price(page)
    page.get_by_role("button", name="متابعة للطلب").click()

    expect(page.get_by_role("heading", name="بدكم تزيدوا الفرحة؟")).to_be_visible()  # the add-ons, no amounts
    page.get_by_role("button", name="ترقية إلى غلاف مقوّى").click()
    no_price(page)
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    expect(page.get_by_text("ليان في موسم الزيتون")).to_be_visible()
    expect(page.get_by_text("نسخة رقمية مع المطبوع")).to_be_visible()  # not «مجانية» while prices are hidden
    expect(page.get_by_placeholder("كود خصم أو بطاقة هدية")).to_have_count(0)  # no discount codes either
    no_price(page)
    page.get_by_role("link", name="متابعة للعنوان والدفع").click()

    expect(page.get_by_text("الخطوة الأخيرة: العنوان والدفع")).to_be_visible()
    # cash on delivery, and we call to confirm the details
    expect(page.get_by_text("نتواصل معكم لتأكيد التفاصيل")).to_be_visible()
    no_price(page)
    code = checkout(page)
    expect(page.get_by_text(code).first).to_be_visible()
    no_price(page)
    assert Decimal(order(page, code)["total"]) > 0  # the order keeps its price for the staff
