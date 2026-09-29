"""The packing slip of an order (Addendum 9 §1.4): what goes in the parcel, printed from the admin.

For a gift order it carries no price at all (not the books, the add-ons, the discounts or the total) and it
prints the parent's card message; the courier's waybill carries the cash-on-delivery amount. Anything else
the recipient would see (the invoice) stays out of a gift parcel.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from qamra_api.deps import SessionDep, require_permission
from qamra_api.errors import ApiError
from qamra_core.db.models import Book, Order, OrderItem
from qamra_core.printing import item_copies, item_format

router = APIRouter(prefix="/api/admin/orders", tags=["admin"])


class SlipAddOn(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    qty: int


class SlipItem(BaseModel):
    name_ar: str
    name_en: str
    book_title: str | None
    child_name: str | None
    format: str
    options: dict[str, str]
    theme: str | None
    qty: int
    copies: int  # extra copies included
    addons: list[SlipAddOn]
    unit_price: Decimal | None  # None on a gift slip
    total: Decimal | None


class Recipient(BaseModel):
    name: str
    phone: str | None
    city: str | None
    address: str | None
    notes: str | None


class PackingSlipOut(BaseModel):
    code: str
    created_at: datetime
    status: str
    gift: bool
    gift_message: str | None
    recipient: Recipient
    items: list[SlipItem]
    currency: str
    prices_hidden: bool
    subtotal: Decimal | None
    discount: Decimal | None
    delivery_fee: Decimal | None
    gift_card: Decimal | None
    total: Decimal | None
    payment_method: str | None


def _addons(addons: list[Any]) -> list[SlipAddOn]:
    return [
        SlipAddOn(
            slug=str(a.get("slug")),
            name_ar=str(a.get("name_ar") or a.get("slug")),
            name_en=str(a.get("name_en") or a.get("slug")),
            qty=int(a.get("qty", 1)),
        )
        for a in addons
        if isinstance(a, dict) and a.get("slug")
    ]


@router.get("/{order_id}/packing-slip", dependencies=[Depends(require_permission("orders.view"))])
async def packing_slip(order_id: uuid.UUID, db: SessionDep) -> PackingSlipOut:
    order = await db.get(Order, order_id)
    if order is None:
        raise ApiError("not_found", 404)
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    ids = [i.book_id for i in items if i.book_id]
    titles = (
        {b.id: b.title for b in (await db.execute(select(Book).where(Book.id.in_(ids)))).scalars()}
        if ids
        else {}
    )
    hide = order.gift
    lines = []
    for i in items:
        options = {str(k): str(v) for k, v in (i.title.get("options") or {}).items()}
        addon_total = sum(
            (
                Decimal(str(a.get("unit_price") or 0)) * int(a.get("qty", 1))
                for a in i.addons
                if isinstance(a, dict)
            ),
            Decimal("0"),
        )
        lines.append(
            SlipItem(
                name_ar=str(i.title.get("name_ar", "")),
                name_en=str(i.title.get("name_en", "")),
                book_title=titles.get(i.book_id) if i.book_id else None,
                child_name=i.personalization.get("child_name"),
                format=item_format(options, i.addons or []),
                options=options,
                theme=i.theme_slug,
                qty=i.quantity,
                copies=item_copies(i.quantity, i.addons or []),
                addons=_addons(i.addons or []),
                unit_price=None if hide else i.unit_price,
                total=None if hide else (i.unit_price * i.quantity + addon_total - i.discount),
            )
        )
    card = Decimal(str(order.pricing.get("gift_card_amount") or 0))
    return PackingSlipOut(
        code=order.code,
        created_at=order.created_at,
        status=order.status.value,
        gift=order.gift,
        gift_message=order.gift_message if order.gift else None,
        recipient=Recipient(
            name=str(order.shipping.get("name") or ""),
            phone=order.shipping.get("phone"),
            city=order.shipping.get("city"),
            address=order.shipping.get("address"),
            notes=None if hide else order.shipping.get("notes"),  # a note to the courier, not the recipient
        ),
        items=lines,
        currency=order.currency.value,
        prices_hidden=hide,
        subtotal=None if hide else order.subtotal,
        discount=None if hide else order.discount,
        delivery_fee=None if hide else order.delivery_fee,
        gift_card=None if hide or not card else card,
        total=None if hide else order.total,
        payment_method=None if hide else order.payment_method.value,
    )
