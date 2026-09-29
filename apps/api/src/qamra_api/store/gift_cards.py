"""Gift cards (Addendum 9 §1.4): stored value that staff issue (never sold on the site), redeemed at checkout.

- A code is "QG" and 12 random characters from an alphabet without 0/O or 1/I (60 bits: not guessable,
  and the code field is rate-limited). Stored bare, shown as QG-XXXX-XXXX-XXXX; dashes and spaces typed by
  the parent are ignored.
- It pays in its own currency only, after every discount, delivery included (`pricing` step 7).
- Redemption is one conditional UPDATE: the balance goes down only if it still covers the amount, so two
  orders placed at the same moment can never spend the same money (the second one is asked to look again).
"""

import secrets
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.errors import ApiError
from qamra_core.db.models import Currency
from qamra_core.db.store import GiftCard, GiftCardRedemption
from qamra_core.pricing import GiftCardRule

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PREFIX = "QG"
LENGTH = 12


def new_code() -> str:
    return PREFIX + "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def normalize(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def looks_like_card(code: str) -> bool:
    bare = normalize(code)
    return bare.startswith(PREFIX) and len(bare) == len(PREFIX) + LENGTH


def pretty(code: str) -> str:
    body = code[len(PREFIX) :]
    return "-".join([PREFIX, *(body[i : i + 4] for i in range(0, len(body), 4))])


def masked(code: str) -> str:
    """What the cart shows back: enough to recognise the card, not enough to spend it."""
    return f"{PREFIX}-••••-••••-{code[-4:]}"


def status(card: GiftCard, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if not card.active:
        return "disabled"
    if card.expires_at is not None and card.expires_at <= now:
        return "expired"
    if card.balance <= 0:
        return "used"
    return "active"


async def find(db: AsyncSession, code: str) -> GiftCard | None:
    fresh = select(GiftCard).where(GiftCard.code == normalize(code)).execution_options(populate_existing=True)
    return (await db.execute(fresh)).scalar_one_or_none()  # the balance as it is now, never a cached one


async def card_rule(
    db: AsyncSession, code: str, currency: Currency
) -> tuple[GiftCardRule | None, GiftCard | None, str | None]:
    """The card as the pricing engine sees it, or why it can't pay this cart."""
    card = await find(db, code)
    if card is None:
        return None, None, "unknown"
    state = status(card)
    if state != "active":
        return None, card, {"disabled": "disabled", "expired": "expired", "used": "empty"}[state]
    if card.currency != currency:
        return None, card, "currency"
    return GiftCardRule(code=masked(card.code), balance=card.balance), card, None


async def redeem(db: AsyncSession, card_id: uuid.UUID, amount: Decimal) -> GiftCardRedemption:
    """Take `amount` off the card, atomically, before the order is written (the caller sets its order_id).
    Raises `gift_card_changed` when the card no longer covers it."""
    left = (
        await db.execute(
            update(GiftCard)
            .where(
                GiftCard.id == card_id,
                GiftCard.active.is_(True),
                GiftCard.balance >= amount,
                or_(GiftCard.expires_at.is_(None), GiftCard.expires_at > func.now()),
            )
            .values(balance=GiftCard.balance - amount, updated_at=func.now())
            .returning(GiftCard.balance)
            .execution_options(synchronize_session=False)  # the row lock decides, not the loaded object
        )
    ).scalar_one_or_none()
    if left is None:
        raise ApiError("gift_card_changed", 409)  # spent or switched off meanwhile: the cart shows it
    redemption = GiftCardRedemption(gift_card_id=card_id, amount=amount)
    db.add(redemption)
    return redemption
