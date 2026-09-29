"""Gift cards in the admin (Addendum 9 §1.4): issue, list and switch off. Staff issue them (e.g. a present
from a school, or to make up for a late order); the site never sells them. Every change is audited."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from qamra_api.deps import AdminUser, SessionDep, require_permission
from qamra_api.errors import ApiError
from qamra_api.store import gift_cards
from qamra_core.db.models import AuditLog, Currency
from qamra_core.db.store import GiftCard, GiftCardRedemption

router = APIRouter(prefix="/api/admin/gift-cards", tags=["admin"])


class GiftCardRow(BaseModel):
    id: uuid.UUID
    code: str  # QG-XXXX-XXXX-XXXX: staff give it to the customer
    currency: str
    amount: Decimal
    balance: Decimal
    expires_at: datetime | None
    active: bool
    status: str  # active | used | expired | disabled
    note: str | None
    uses: int
    created_at: datetime


class GiftCardIn(BaseModel):
    amount: Decimal = Field(gt=0, le=10_000, max_digits=9, decimal_places=2)
    currency: Currency = Currency.ILS
    expires_at: datetime | None = None
    note: str | None = Field(default=None, max_length=200)


class GiftCardPatch(BaseModel):
    active: bool | None = None
    expires_at: datetime | None = None


def _row(card: GiftCard, uses: int) -> GiftCardRow:
    return GiftCardRow(
        id=card.id,
        code=gift_cards.pretty(card.code),
        currency=card.currency.value,
        amount=card.amount,
        balance=card.balance,
        expires_at=card.expires_at,
        active=card.active,
        status=gift_cards.status(card),
        note=card.note,
        uses=uses,
        created_at=card.created_at,
    )


async def _uses(db: SessionDep, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    rows = await db.execute(
        select(GiftCardRedemption.gift_card_id, func.count())
        .where(GiftCardRedemption.gift_card_id.in_(ids))
        .group_by(GiftCardRedemption.gift_card_id)
    )
    return {k: int(v) for k, v in rows.all()}


def _audit(db: SessionDep, admin: AdminUser, card: GiftCard, action: str, data: dict[str, object]) -> None:
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action=f"gift_card.{action}",
            entity_type="gift_card",
            entity_id=str(card.id),
            data={"code": gift_cards.masked(card.code), **data},  # never the full code in the log
        )
    )


@router.get("", dependencies=[Depends(require_permission("prices"))])
async def list_cards(db: SessionDep) -> list[GiftCardRow]:
    newest = select(GiftCard).order_by(GiftCard.created_at.desc()).limit(300)
    cards = (await db.execute(newest)).scalars().all()
    uses = await _uses(db, [c.id for c in cards])
    return [_row(c, uses.get(c.id, 0)) for c in cards]


@router.post("", status_code=201, dependencies=[Depends(require_permission("prices"))])
async def issue_card(body: GiftCardIn, admin: AdminUser, db: SessionDep) -> GiftCardRow:
    if body.expires_at is not None and body.expires_at <= datetime.now(UTC):
        raise ApiError("invalid_input", 422, {"fields": ["expires_at"]})
    for _ in range(5):
        code = gift_cards.new_code()
        if await gift_cards.find(db, code) is None:
            break
    else:
        raise ApiError("gift_card_exists", 409)
    card = GiftCard(
        code=code,
        currency=body.currency,
        amount=body.amount,
        balance=body.amount,
        expires_at=body.expires_at,
        note=" ".join(body.note.split()) if body.note else None,
        created_by_user_id=admin.id,
        active=True,
    )
    db.add(card)
    await db.flush()
    _audit(db, admin, card, "issued", {"amount": str(body.amount), "currency": body.currency.value})
    await db.commit()
    return _row(card, 0)


@router.patch("/{card_id}", dependencies=[Depends(require_permission("prices"))])
async def edit_card(card_id: uuid.UUID, body: GiftCardPatch, admin: AdminUser, db: SessionDep) -> GiftCardRow:
    card = await db.get(GiftCard, card_id)
    if card is None:
        raise ApiError("not_found", 404)
    before = {"active": card.active, "expires_at": card.expires_at.isoformat() if card.expires_at else None}
    if body.active is not None:
        card.active = body.active
    if body.expires_at is not None:
        card.expires_at = body.expires_at
    after = {"active": card.active, "expires_at": card.expires_at.isoformat() if card.expires_at else None}
    _audit(db, admin, card, "updated", {"before": before, "after": after})
    await db.commit()
    return _row(card, (await _uses(db, [card.id])).get(card.id, 0))
