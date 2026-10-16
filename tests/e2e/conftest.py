"""End-to-end tests of the order path (Addendum 9 §3) in a real browser, against a running site.

    E2E_BASE_URL=http://localhost:3000 uv run pytest tests/e2e -p no:cacheprovider

The site's API must run with `E2E_FIXTURES=true` (never in prod: the settings refuse it). The tests make
their preview books through `/api/e2e/*` with placeholder art, so no AI provider is ever called. How to run
the whole stack locally: docs/e2e.md.

The order flows (test_order_flows.py) go through the real photo, drawing and story steps. Those steps still
put jobs on the worker's `generation` queue; the fixtures finish them with placeholders and take the jobs off
the queue. So run the stack's worker on the `pdf` queue only (`rq worker pdf`: the parent's download needs
it), never on `generation`.

A whole run signs up and orders more from one address than the API's per-address limits allow in an hour:
each test first clears this machine's own counters (`/api/e2e/rate-limits/reset`).
"""

import uuid
from collections.abc import Iterator

import pytest
from e2e_flow import BASE_URL, call, show_prices
from playwright.sync_api import (
    Browser,
    BrowserContext,
    ConsoleMessage,
    Page,
    Playwright,
    expect,
    sync_playwright,
)

expect.set_options(timeout=30_000)  # a dev stack (or one on a remote database) can take a few seconds


@pytest.fixture(scope="session")
def playwright() -> Iterator[Playwright]:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session", autouse=True)
def prices_shown() -> Iterator[None]:
    """These tests check the prices, so the run shows them (the admin switch `show_prices` is off by default,
    Tareq 2026-10-16); test_prices_hidden.py hides them for its own tests and shows them again after."""
    show_prices(True)
    yield


# next-intl's errors in the browser: a message the page asked for and didn't get (the public pages ship only
# their own namespaces, and no price template while prices are hidden: src/lib/clientMessages.ts)
INTL_ERRORS = ("MISSING_MESSAGE", "INSUFFICIENT_PATH", "INVALID_MESSAGE", "FORMATTING_ERROR")
intl_errors: list[str] = []


def watch_intl_errors(context: BrowserContext) -> BrowserContext:
    def on_console(msg: ConsoleMessage) -> None:
        if any(code in msg.text for code in INTL_ERRORS):
            intl_errors.append(f"{msg.page.url if msg.page else '?'}: {msg.text[:300]}")

    context.on("console", on_console)
    return context


@pytest.fixture(scope="session")
def browser(playwright: Playwright) -> Iterator[Browser]:
    browser = playwright.chromium.launch()
    new_context = browser.new_context
    # every context a test opens (its own, a guest's, a second staff session) reports next-intl's errors
    browser.new_context = lambda *a, **k: watch_intl_errors(new_context(*a, **k))  # type: ignore[method-assign]
    yield browser
    browser.close()


@pytest.fixture(autouse=True)
def no_missing_messages() -> Iterator[None]:
    """Fails a test whose pages logged a next-intl error (a missing or broken message)."""
    intl_errors.clear()
    yield
    assert not intl_errors, "next-intl errors in the browser:\n" + "\n".join(intl_errors)


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    """A phone (390 px, Arabic) with its own cookies, signed in as a new parent."""
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="ar")
    context.set_default_timeout(30_000)
    page = context.new_page()
    page.goto(f"{BASE_URL}/ar/login")
    call(page, "POST", "/api/e2e/rate-limits/reset")  # this machine's sign-ups, checkouts and look-ups
    call(
        page,
        "POST",
        "/api/auth/register",
        {
            "email": f"e2e-{uuid.uuid4().hex[:10]}@example.com",
            "password": "moonlight-2026",
            "full_name": "أم ليان",
        },
    )
    yield page
    context.close()
