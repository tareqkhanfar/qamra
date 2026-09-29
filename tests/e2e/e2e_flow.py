"""Helpers of the order-path E2E tests: the site's API from the page, and the checkout form."""

import os
from typing import Any

from playwright.sync_api import Page

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:3000").rstrip("/")
FETCH = """async ([method, path, body]) => {
  const r = await fetch(path, {method, credentials: 'same-origin',
    headers: {'X-Qamra-Client': 'web', 'Content-Type': 'application/json'},
    body: body === null ? undefined : JSON.stringify(body)});
  return {status: r.status, body: await r.json().catch(() => null)};
}"""


def call(page: Page, method: str, path: str, body: Any = None) -> Any:
    """The site's own API, from the page (same origin, the parent's cookies)."""
    r = page.evaluate(FETCH, [method, path, body])
    assert r["status"] < 300, f"{method} {path} → {r}"
    return r["body"]


def preview_book(page: Page, **body: Any) -> dict[str, Any]:
    """A book waiting at its preview, with an approved character (placeholder art, no AI)."""
    return call(page, "POST", "/api/e2e/books", body)  # type: ignore[no-any-return]


def to_cart(page: Page, book: dict[str, Any], sku: str) -> None:
    call(page, "POST", f"/api/create/books/{book['book_id']}/cart", {"sku": sku, "addons": []})


def order(page: Page, code: str) -> dict[str, Any]:
    return call(page, "GET", f"/api/e2e/orders/{code}")  # type: ignore[no-any-return]


def checkout(page: Page, *, name: str = "أم ليان", city: str = "البيرة") -> str:
    """Create10: the address, cash on delivery, and the order page's code."""
    page.get_by_label("اسم المستلم").fill(name)
    page.get_by_label("رقم الجوال").fill("059 123 4567")
    with page.expect_response(lambda r: "/api/store/cart/zone" in r.url):
        page.get_by_label("المدينة").select_option(city)
    page.get_by_label("الحي والشارع وأقرب معلم").fill("البالوع، قرب المسجد")
    page.get_by_role("button", name="أكّد الطلب").click()
    page.wait_for_url("**/order/QM-*")
    return page.url.split("/order/")[1].split("?")[0]
