"""Helpers of the order-path E2E tests: the site's API from the page, the create flow's steps (with the test
fixtures standing in for the image model and the worker), and the checkout form."""

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:3000").rstrip("/")
# a public-domain photo with one clear face: the API's photo check (local, no AI) accepts it
FACE = Path(__file__).resolve().parents[2] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
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


def confirm(page: Page, code: str, *, render: bool = False) -> dict[str, Any]:
    """Staff confirm the order (and, with `render`, its activity books are "rendered" as placeholder PDFs)."""
    return call(page, "POST", f"/api/e2e/orders/{code}/confirm", {"render": render})  # type: ignore[no-any-return]


def query(page: Page) -> dict[str, str]:
    """The current URL's query, one value per key."""
    return {k: v[0] for k, v in parse_qs(urlsplit(page.url).query).items()}


# ---- the create flow ---------------------------------------------------------------------------------------


def step_is(page: Page, n: int, total: int) -> None:
    """The header's real «الخطوة n من N» (lib/flows.ts), as text and as the progress bar."""
    bar = page.get_by_role("progressbar")
    expect(bar).to_have_attribute("aria-valuenow", str(n))
    expect(bar).to_have_attribute("aria-valuemax", str(total))
    expect(page.get_by_text(f"الخطوة {n} من {total}", exact=True)).to_be_visible()


def fits(page: Page) -> None:
    """Nothing scrolls sideways on the phone (390 px)."""
    width, viewport = page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
    assert width <= viewport, f"{page.url}: the page is {width} px wide on a {viewport} px screen"


def new_child(page: Page, *, label: str, name: str, gender: str, age: int) -> None:
    """The child step's form for a new child: the name (under its product's label), girl or boy, the age."""
    page.get_by_label(label, exact=True).fill(name)
    page.get_by_label("بنت" if gender == "f" else "ولد", exact=True).check()
    page.get_by_role("button", name=str(age), exact=True).click()


def give_consent(page: Page) -> None:
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="أوافق، لنكمل").click()


def upload_photo(page: Page) -> None:
    """The photo step: one clear face, checked by the API (no AI), then «استخدموا هذه الصورة»."""
    page.locator('input[type="file"]').set_input_files(FACE)
    use = page.get_by_role("button", name="استخدموا هذه الصورة")
    expect(use).to_be_enabled()
    use.click()


def approve_placeholder_character(page: Page, approve: str) -> str:
    """The drawing the flow asked for is finished with placeholder art (no image model), then the parent
    approves it on the character step (`approve`: «نعم، تشبه ضحى»). Returns the character's id."""
    page.wait_for_url(re.compile(r"[?&]character=[0-9a-f-]{36}"))
    character = query(page)["character"]
    call(page, "POST", f"/api/e2e/characters/{character}/ready")
    page.get_by_role("button", name=approve).click()
    return character


def finish_preview(page: Page) -> str:
    """The story preview the flow started, finished with placeholder pages (no AI). Returns the book's id."""
    page.wait_for_url(re.compile(r"[?&]book=[0-9a-f-]{36}"))
    book = query(page)["book"]
    call(page, "POST", f"/api/e2e/books/{book}/preview")
    return book


def checkout(page: Page, *, name: str = "أم ليان", city: str = "البيرة") -> str:
    """Create10: the address, cash on delivery, and the order page's code."""
    page.get_by_label("اسم المستلم").fill(name)
    page.get_by_label("رقم الجوال").fill("059 123 4567")
    with page.expect_response(lambda r: "/api/store/cart/zone" in r.url):
        page.get_by_label("المدينة").select_option(city)
    page.get_by_label("الحي والشارع وأقرب معلم").fill("البالوع، قرب المسجد")
    page.get_by_role("button", name="أكّدوا الطلب").click()
    page.wait_for_url("**/order/QM-*")
    return page.url.split("/order/")[1].split("?")[0]
