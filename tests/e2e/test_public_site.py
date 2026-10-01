"""The public site at launch, on a phone: what we sell, what it costs, and nothing "coming soon".

Read-only: an anonymous visitor, no orders, no AI. Run with the others (docs/e2e.md); these tests need only a
running site with the store seeded, not the E2E fixtures.
"""

import re
from collections.abc import Iterator

import pytest
from e2e_flow import BASE_URL
from playwright.sync_api import Browser, Page, expect

PAGES = [
    "",
    "/stories",
    "/stories/first-day",
    "/workbooks",
    "/workbooks/foundation-workbook",
    "/workbooks/learning-journey",
    "/workbooks/family-adventures",
    "/pricing",
    "/how-it-works",
    "/shop",
    "/quiz",
    "/kindergartens",
    "/privacy",
]
BOOKS = {
    "foundation-workbook": "دوسية التأسيس",
    "learning-journey": "رحلتي الأولى للتعلّم",
    "family-adventures": "مغامراتي مع عائلتي",
}
# nothing in a store is "coming", nothing waits for a sign-off, and the old name for the stories is gone
NOT_ON_A_STORE = re.compile(
    r"(?<!ت)(?:قريب[اًٌ]|قريبًا|قريباً)|coming soon|العوالم|after the educator|tell me when|تنبيه عند",
    re.IGNORECASE,
)


@pytest.fixture
def visitor(browser: Browser) -> Iterator[Page]:
    """An anonymous phone (390 px, Arabic): no account, no cart."""
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="ar")
    context.set_default_timeout(30_000)
    yield context.new_page()
    context.close()


def test_every_public_page_fits_a_phone_and_promises_nothing_that_is_not_for_sale(visitor: Page) -> None:
    for path in PAGES:
        response = visitor.goto(f"{BASE_URL}/ar{path}", wait_until="load")
        assert response is not None and response.ok, path
        text = visitor.inner_text("body")
        assert not NOT_ON_A_STORE.search(text), f"{path}: {NOT_ON_A_STORE.search(text)}"
        wide = visitor.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        assert not wide, f"{path} scrolls sideways on a 390 px phone"


def test_the_menu_and_the_footer_are_the_launch_structure(visitor: Page) -> None:
    visitor.goto(f"{BASE_URL}/ar", wait_until="load")
    visitor.get_by_role("button", name="القائمة").or_(visitor.locator("summary[aria-label]")).first.click()
    menu = visitor.locator("header details a")
    expect(menu.nth(0)).to_have_text("الحكايات")
    labels = menu.all_inner_texts()[:5]
    assert labels == ["الحكايات", "كتب الأنشطة", "للروضات", "الأسعار", "كيف نعمل"]
    hrefs = [h for h in menu.evaluate_all("els => els.map(e => e.getAttribute('href'))")][:5]
    assert hrefs == ["/ar/stories", "/ar/workbooks", "/ar/kindergartens", "/ar/pricing", "/ar/how-it-works"]
    footer = visitor.locator("footer")
    for name in (
        "دوسية التأسيس",
        "رحلتي الأولى للتعلّم",
        "مغامراتي مع عائلتي",
        "كل الكتب",
        "الأسعار",
        "كيف نعمل",
    ):
        expect(footer.get_by_role("link", name=name)).to_be_visible()


def test_the_home_shows_the_four_offers_with_prices(visitor: Page) -> None:
    visitor.goto(f"{BASE_URL}/ar", wait_until="load")
    expect(visitor.get_by_role("heading", level=1)).to_have_text("كتب مطبوعة باسم طفلكم")
    for href in ("/ar/stories?line=classic", "/ar/stories?line=magic", "/ar/workbooks", "/ar/kindergartens"):
        card = visitor.locator(f'a[data-reveal][href="{href}"]')  # the offer cards, not the menu links
        expect(card).to_be_visible()
    expect(visitor.locator('a[data-reveal][href="/ar/stories?line=classic"]')).to_contain_text("من")


def test_the_activity_books_hub_lists_three_books_each_orderable(visitor: Page) -> None:
    visitor.goto(f"{BASE_URL}/ar/workbooks", wait_until="load")
    for slug, name in BOOKS.items():
        card = visitor.locator("article", has=visitor.get_by_role("heading", name=name))
        expect(card).to_have_count(1)
        expect(card).to_contain_text("من")  # the price it starts from
        expect(card.get_by_role("link", name=re.compile("اطلب")).first).to_have_attribute(
            "href", f"/ar/workbooks/{slug}"
        )
        visitor.goto(f"{BASE_URL}/ar/workbooks/{slug}", wait_until="load")
        expect(visitor.get_by_role("button", name="أضيفوا للسلة")).to_be_enabled()
        visitor.goto(f"{BASE_URL}/ar/workbooks", wait_until="load")


def test_the_pricing_page_has_every_kind_of_price(visitor: Page) -> None:
    visitor.goto(f"{BASE_URL}/ar/pricing", wait_until="load")
    for heading in ("كتب الحكايات", "الإضافات", "كتب الأنشطة", "للروضات", "التوصيل والدفع"):
        expect(visitor.get_by_role("heading", name=heading, exact=True).first).to_be_visible()
    expect(visitor.get_by_role("heading", name="قمرة كلاسيك")).to_be_visible()
    expect(visitor.get_by_role("heading", name="الدفع عند الاستلام")).to_be_visible()
    assert visitor.locator("table tbody tr").count() >= 1  # a delivery zone


def test_the_english_site_has_the_same_structure(browser: Browser) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="en")
    context.set_default_timeout(30_000)
    page = context.new_page()
    try:
        page.goto(f"{BASE_URL}/en", wait_until="load")
        nav = page.locator("header nav")
        for label in ("Stories", "Activity books", "Kindergartens", "Pricing", "How it works"):
            expect(nav.get_by_role("link", name=label, exact=True)).to_be_visible()
        assert not NOT_ON_A_STORE.search(page.inner_text("body"))
        page.goto(f"{BASE_URL}/en/workbooks", wait_until="load")
        expect(page.get_by_role("heading", name="Foundation workbook")).to_be_visible()
    finally:
        context.close()
