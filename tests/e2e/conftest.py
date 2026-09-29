"""End-to-end tests of the order path (Addendum 9 §3) in a real browser, against a running site.

    E2E_BASE_URL=http://localhost:3000 uv run pytest tests/e2e -p no:cacheprovider

The site's API must run with `E2E_FIXTURES=true` (never in prod: the settings refuse it). The tests make
their preview books through `/api/e2e/*` with placeholder art, so no AI provider is ever called. How to run
the whole stack locally: docs/e2e.md.
"""

import uuid
from collections.abc import Iterator

import pytest
from e2e_flow import BASE_URL, call
from playwright.sync_api import Browser, Page, Playwright, expect, sync_playwright

expect.set_options(timeout=30_000)  # a dev stack (or one on a remote database) can take a few seconds


@pytest.fixture(scope="session")
def playwright() -> Iterator[Playwright]:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright: Playwright) -> Iterator[Browser]:
    browser = playwright.chromium.launch()
    yield browser
    browser.close()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    """A phone (390 px, Arabic) with its own cookies, signed in as a new parent."""
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="ar")
    context.set_default_timeout(30_000)
    page = context.new_page()
    page.goto(f"{BASE_URL}/ar/login")
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
