"""«أضيفوا للسلة» puts every product in the cart with one tap, for a guest too (Tareq, 2026-10-02: "I choose a
book and it is not added to the cart"); the child's details are completed from the cart line."""

from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import pytest
from e2e_flow import BASE_URL, call, preview_book
from playwright.sync_api import Browser, Page, expect

# every activity book (web `ACTIVITY_LINES`): «قلبي يعرف الله» once completed as a story (2026-10-07)
WORKBOOKS = ("foundation-workbook", "learning-journey", "family-adventures", "islamic-series")
COMPLETE = "أكملوا بيانات الطفل"


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


def complete_links(page: Page) -> dict[str, dict[str, list[str]]]:
    """Each waiting line's «أكملوا بيانات الطفل» link, by cart line id: the create flow's query."""
    links = page.get_by_role("link", name=COMPLETE)
    expect(links.first).to_be_visible()
    hrefs: list[str] = links.evaluate_all("links => links.map((a) => a.getAttribute('href'))")
    queries = [parse_qs(urlsplit(href).query) for href in hrefs]
    return {q["item"][0]: q for q in queries}


def test_a_guest_adds_a_story_and_every_activity_book_in_one_tap_each(guest: Page) -> None:
    add(guest, "/ar/stories/graduation")
    for slug in WORKBOOKS:
        add(guest, f"/ar/workbooks/{slug}")

    cart = call(guest, "GET", "/api/store/cart")
    assert cart["count"] == 1 + len(WORKBOOKS), cart["count"]
    assert cart["items"][0]["sku"].split("-")[0] in ("magic", "classic")  # in the order added
    # every line waits for the child's details, and the cart says what each kind of book still needs
    expect(guest.get_by_role("link", name=COMPLETE).first).to_be_visible()
    expect(guest.get_by_text("ينقصه: بيانات الطفل والمعاينة")).to_have_count(1)  # the story
    expect(guest.get_by_text("ينقصه: اسم الطفل وشخصيته")).to_have_count(len(WORKBOOKS))  # no photo for these


def test_every_activity_line_completes_through_its_product(guest: Page) -> None:
    """An activity book's line opens the create flow with its product (`product=<sku>`): no story, theme or
    format to choose. «قلبي يعرف الله» was left out of the cart's own list and got `?item&format`: the story
    flow."""
    for slug in WORKBOOKS:
        add(guest, f"/ar/workbooks/{slug}")
    items = call(guest, "GET", "/api/store/cart")["items"]
    assert [i["product"] for i in items] == list(WORKBOOKS)

    links = complete_links(guest)
    for item in items:
        query = links[item["id"]]
        assert query["product"] == [item["sku"]], (item["product"], query)
        # its own flow: never a story line (no `line=magic` any more), story, style or format
        assert not {"line", "format", "theme", "style"} & query.keys(), (item["product"], query)


def test_completing_a_line_opens_the_create_flow_for_that_line(guest: Page) -> None:
    add(guest, "/ar/workbooks/family-adventures")
    guest.get_by_role("link", name=COMPLETE).first.click()
    guest.wait_for_url("**/create**")
    assert "item=" in guest.url


def test_a_known_child_completes_an_islamic_line_without_the_story_flow(page: Page) -> None:
    """«قلبي يعرف الله» from the cart: the parent picks a child whose character is approved, and the line
    is filled with it, back in the cart. No Classic/Magic choice, no story, nothing drawn (placeholders)."""
    child = preview_book(page, name="ضحى")["child_id"]  # consent and an approved character, no AI
    add(page, "/ar/workbooks/islamic-series")
    line = call(page, "GET", "/api/store/cart")["items"][0]
    assert line["line"] == "islamic" and line["needs_details"]

    page.get_by_role("link", name=COMPLETE).first.click()
    page.wait_for_url("**/create**")
    query = parse_qs(urlsplit(page.url).query)
    assert query["item"] == [line["id"]] and query["product"] == [line["sku"]], page.url
    page.get_by_role("button", name="ضحى", exact=True).click()
    page.wait_for_url("**/cart")

    cart = call(page, "GET", "/api/store/cart")
    assert [i["id"] for i in cart["items"]] == [line["id"]]  # filled, not a second line
    filled = cart["items"][0]
    assert filled["child_id"] == child and filled["sku"] == line["sku"] and not filled["needs_details"]
    assert filled["book_id"] is None  # no story book was started for it
    expect(page.get_by_role("link", name=COMPLETE)).to_have_count(0)
    # «تعديل» opens this line's review step (it went to /shop, then to the product page)
    edit = page.get_by_role("link", name="تعديل", exact=True).get_attribute("href") or ""
    query = parse_qs(urlsplit(edit).query)
    assert urlsplit(edit).path.endswith("/create"), edit
    assert (
        query["step"] == ["summary"] and query["item"] == [line["id"]] and query["product"] == [line["sku"]]
    )
