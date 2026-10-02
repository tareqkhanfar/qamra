"""«أضيفوا للسلة» puts every product in the cart with one tap, for a guest too (Tareq, 2026-10-02: "I choose a
book and it is not added to the cart"); the child's details are completed from the cart line."""

from collections.abc import Iterator

import pytest
from e2e_flow import BASE_URL, call
from playwright.sync_api import Browser, Page, expect

WORKBOOKS = ("foundation-workbook", "learning-journey", "family-adventures")


@pytest.fixture
def guest(browser: Browser) -> Iterator[Page]:
    """An anonymous phone (390 px, Arabic): no account, no cart."""
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="ar")
    context.set_default_timeout(30_000)
    yield context.new_page()
    context.close()


def add(page: Page, path: str) -> None:
    page.goto(f"{BASE_URL}{path}", wait_until="load")
    page.get_by_role("button", name="أضيفوا للسلة").first.click()
    page.wait_for_url("**/cart")


def test_a_guest_adds_a_story_and_every_activity_book_in_one_tap_each(guest: Page) -> None:
    add(guest, "/ar/stories/graduation")
    for slug in WORKBOOKS:
        add(guest, f"/ar/workbooks/{slug}")

    cart = call(guest, "GET", "/api/store/cart")
    assert cart["count"] == 4, cart["count"]
    assert cart["items"][0]["sku"].split("-")[0] in ("magic", "classic")  # in the order added
    # every line waits for the child's details, and the cart says how to finish them
    expect(guest.get_by_role("link", name="أكملوا بيانات الطفل").first).to_be_visible()
    assert guest.get_by_text("ينقصه: بيانات الطفل وصورته").count() == 4


def test_completing_a_line_opens_the_create_flow_for_that_line(guest: Page) -> None:
    add(guest, "/ar/workbooks/family-adventures")
    guest.get_by_role("link", name="أكملوا بيانات الطفل").first.click()
    guest.wait_for_url("**/create**")
    assert "item=" in guest.url
