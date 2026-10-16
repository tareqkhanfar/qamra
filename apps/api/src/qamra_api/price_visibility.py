"""«إخفاء الأسعار» (Tareq, 2026-10-16): while the admin setting `show_prices` is off, customers see no price.

The prices stay in the system: orders still record them from the price list, and every `/api/admin/…` response
keeps them. Every other API response is customer-facing (the catalog, the shop, the cart and checkout, order
tracking, the kindergarten portal, public settings…), so it is enforced here, once, on the server:

- `price_visibility` (an app-wide dependency) resolves the switch for each customer-facing request and leaves
  it on the request state, through the request's own db session.
- `PriceGuardMiddleware` drops every price field from the JSON those requests answer with, however deep.

What is a price field is decided by the key (`is_price_key`): names that are always money, and a few general
names (`total`, `amount`, `fee`…) that are money only when they hold a decimal (the API writes `Decimal` as a
string): a count such as a voice invite's `total: 3` stays. Catalog wording that speaks of price («بنص السعر»,
«مجانية») is swapped, by the product's or add-on's slug, for the neutral texts in
content/store/no_price_wording.yaml. Non-JSON customer outputs (the portal's invoice PDF) and messages
(emails, WhatsApp) check `prices_shown` themselves.
"""

import contextlib
import json
import re
from functools import cache
from typing import Any

import yaml
from fastapi import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_api import runtime_settings
from qamra_api.deps import SessionDep, SettingsDep

SETTING = "show_prices"
STATE_KEY = "hide_prices"
# Staff screens keep every price; the e2e helpers exist only in the test environment.
UNGUARDED_PREFIXES = ("/api/admin/", "/api/e2e/", "/api/health")

# Keys that name money wherever they appear, besides any key with "price" or "discount" in it.
ALWAYS = frozenset(
    {
        "currency",
        "subtotal",
        "cod_fee",
        "delivery_fee",
        "free_over",
        "addons_total",
        "gift_card_amount",
        "class_book_from",
        "bundle_pct",
        "revenue",
    }
)
# General names: money only when their value is a decimal (or null), never a whole-number count.
WHEN_DECIMAL = frozenset({"total", "amount", "fee", "shipping", "base", "percent", "balance"})
# Not prices: the switch itself and the packing slip's own flag.
KEEP = frozenset({SETTING, "prices_hidden"})
MONEY_SUFFIXES = ("_ils", "_jod", "_usd")
_DECIMAL = re.compile(r"-?\d+(\.\d+)?")
WORDING_FILE = CONTENT_DIR / "store" / "no_price_wording.yaml"
WORDING_FIELDS = frozenset({"name_ar", "name_en", "description_ar", "description_en", "badge_ar", "badge_en"})


@cache
def no_price_wording() -> dict[str, dict[str, str | None]]:
    """slug → the fields said differently while prices are hidden (content/store/no_price_wording.yaml)."""
    data = yaml.safe_load(WORDING_FILE.read_text(encoding="utf-8")) or {}
    return {
        str(slug): {k: v for k, v in fields.items() if k in WORDING_FIELDS} for slug, fields in data.items()
    }


def is_price_key(key: str, value: Any) -> bool:
    k = key.lower()
    if k in KEEP:
        return False
    if k in ALWAYS or "price" in k or "discount" in k or k.endswith(MONEY_SUFFIXES):
        return True
    if k in WHEN_DECIMAL:
        return value is None or (isinstance(value, str) and _DECIMAL.fullmatch(value) is not None)
    return False


def strip_prices(data: Any) -> Any:
    """A copy of `data` without any price field, at any depth, and with the neutral wording of a product or
    add-on whose own texts speak of price."""
    if isinstance(data, dict):
        out = {k: strip_prices(v) for k, v in data.items() if not is_price_key(str(k), v)}
        wording = no_price_wording().get(out["slug"]) if isinstance(out.get("slug"), str) else None
        for field, text in (wording or {}).items():
            if field in out:
                out[field] = text
        return out
    if isinstance(data, list):
        return [strip_prices(v) for v in data]
    return data


def guarded(path: str) -> bool:
    return path.startswith("/api/") and not path.startswith(UNGUARDED_PREFIXES) and path != "/api/admin"


async def prices_shown(db: SessionDep, settings: SettingsDep) -> bool:
    """The admin switch (default off). Emails, WhatsApp and the invoice PDF ask it directly."""
    return bool((await runtime_settings.current(db, settings)).values.get(SETTING))


async def price_visibility(request: Request, db: SessionDep, settings: SettingsDep) -> None:
    """App-wide dependency: on customer-facing paths, note whether this response must lose its prices."""
    if guarded(request.url.path):
        request.state.hide_prices = not await prices_shown(db, settings)


def hidden(request: Request) -> bool:
    """For a handler on a customer path: True while prices are hidden (the dependency has run)."""
    return bool(getattr(request.state, STATE_KEY, True))


class PriceGuardMiddleware:
    """Drops the price fields from the JSON of customer-facing responses while prices are hidden. Fails
    closed: a guarded response whose request never resolved the switch (an early error) is stripped too."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not guarded(str(scope.get("path", ""))):
            await self.app(scope, receive, send)
            return
        state: dict[str, Any] = scope.setdefault("state", {})
        start: Message | None = None
        body: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                kind = dict(message.get("headers", [])).get(b"content-type", b"")
                if not kind.startswith(b"application/json"):
                    await send(message)  # files, redirects, streams: untouched
                    return
                start = message
                return
            if start is None or message["type"] != "http.response.body":
                await send(message)
                return
            body.append(message.get("body", b""))
            if message.get("more_body", False):
                return
            raw = b"".join(body)
            if state.get(STATE_KEY, True) and raw:
                with contextlib.suppress(ValueError):  # not JSON after all: left as it is
                    raw = json.dumps(
                        strip_prices(json.loads(raw)), ensure_ascii=False, separators=(",", ":")
                    ).encode()
            headers = [(k, v) for k, v in start.get("headers", []) if k.lower() != b"content-length"]
            headers.append((b"content-length", str(len(raw)).encode()))
            await send({**start, "headers": headers})
            await send({"type": "http.response.body", "body": raw, "more_body": False})

        await self.app(scope, receive, send_wrapper)
