# End-to-end tests of the order path (Addendum 9 §3)

`tests/e2e/` drives a real browser (Python Playwright, already a dependency) through the order path on a
390 px phone, in Arabic:

| Test | Flow |
| --- | --- |
| `test_classic_softcover_with_two_add_ons_to_a_cod_order` | preview (Create9) → softcover → «الإضافات» with 2 add-ons → «السلة» → address + cash on delivery → order |
| `test_magic_hardcover_to_the_cart` | Magic preview → hardcover → add-ons step → cart (and the «شخصية … جاهزة» cross-sell) |
| `test_the_gift_toggle_and_card_message` | cart → «هذا الطلب هدية» + card message (kept by the server across a reload) → gift order |
| `test_a_sibling_bundle_with_a_coupon` | two children's books → «باقة الإخوة» → discount code → order with both discounts |

The shop → quiz and workbook flows of §3 belong to the site pages and are not covered here.

## No AI, no paid calls

The tests never draw anything. Their preview books come from test-only fixtures, `/api/e2e/*`
(`apps/api/src/qamra_api/routers/e2e.py`): a child with the guardian's consent, an approved character and a
book at its preview, all with placeholder art. The router is mounted only when **`E2E_FIXTURES=true`**, and
the API refuses to start with it in prod. Everything after the preview (cart, add-ons, codes, checkout) is
the real API.

## Run

1. A running stack whose API has `E2E_FIXTURES=true` (for docker compose, put it in `.env`; the app services
   read it), with the themes and the store seeded (`qamra seed-themes`, `qamra seed-store`).
2. Chromium for Playwright, once: `uv run playwright install chromium`.
3. Point the tests at the site (the web app; it proxies `/api`):

   ```sh
   E2E_BASE_URL=http://localhost:3000 uv run pytest tests/e2e -p no:cacheprovider
   ```

Each test signs up a new parent (`e2e-…@example.com`), so they can run again on the same database. They
create orders, coupons and gift cards there: use a development or test database, never production.

When the dev server is opened as `127.0.0.1`, Next.js blocks its dev resources for that origin: use
`localhost` in `E2E_BASE_URL`.
