"""/api/portal — the class order (CLAUDE.md §8): wholesale prices from the school's price list, one order and
one invoice per class, delivered to the school's address, cash on delivery. Our team then confirms the order
in the admin, and the print batch picks it up once every copy passed the print approval.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_api import runtime_settings
from qamra_api.deps import SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.portal.access import SchoolAdmin, class_book_of, own_classroom
from qamra_api.portal.ordering import ClassQuote, class_quote, item_costs
from qamra_api.routers.admin_orders import issue_invoice
from qamra_api.store.router import _new_code, _quote_json
from qamra_core.db.models import AuditLog, Order, OrderItem, OrderStatus, PaymentMethod
from qamra_core.db.portal import ClassBook, ClassBookStatus
from qamra_core.db.store import Invoice, OrderEvent

router = APIRouter(prefix="/api/portal", tags=["portal"])


class TierOut(BaseModel):
    min_qty: int
    unit_price: Decimal


class QuoteOut(BaseModel):
    currency: str
    product: str
    name_ar: str
    name_en: str
    copies: int
    children: list[str]
    tiers: list[TierOut]
    price_list: str | None
    unit_price: Decimal | None
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    total: Decimal
    delivery: dict[str, str | None]
    notes: list[str]
    ordered: str | None  # the order code when the class already ordered


def _quote_out(cq: ClassQuote, delivery: dict[str, str | None], code: str | None) -> QuoteOut:
    q = cq.quote
    return QuoteOut(
        currency=cq.currency.value,
        product=cq.product.slug,
        name_ar=cq.product.name_ar,
        name_en=cq.product.name_en,
        copies=len(cq.copies),
        children=[child.first_name for _, child in cq.copies],
        tiers=[TierOut(min_qty=n, unit_price=p) for n, p in cq.tiers],
        price_list=cq.price_list.name if cq.price_list else None,
        unit_price=q.items[0].unit_price if q.items else None,
        subtotal=q.subtotal,
        discount=q.discount,
        shipping=q.shipping + q.cod_fee,
        total=q.total,
        delivery=delivery,
        notes=q.notes,
        ordered=code,
    )


async def _class(db: SessionDep, school: SchoolAdmin, classroom_id: uuid.UUID) -> ClassBook:
    room = await own_classroom(db, school, classroom_id)
    cb = await class_book_of(db, room)
    if cb is None:
        raise ApiError("theme_required", 409)
    return cb


def _delivery(school: SchoolAdmin) -> dict[str, str | None]:
    org = school.org
    return {"name": org.name, "city": org.city, "address": org.address, "phone": org.phone}


@router.get("/classes/{classroom_id}/order/quote")
async def quote_class(classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep) -> QuoteOut:
    cb = await _class(db, school, classroom_id)
    order = await db.get(Order, cb.order_id) if cb.order_id else None
    return _quote_out(await class_quote(db, school.org, cb), _delivery(school), order.code if order else None)


class OrderIn(BaseModel):
    accept_terms: bool
    notes: str | None = Field(default=None, max_length=500)


class PlacedOut(BaseModel):
    code: str
    status: str
    currency: str
    total: Decimal
    invoice: str


@router.post("/classes/{classroom_id}/order", status_code=201)
async def place_order(
    classroom_id: uuid.UUID,
    body: OrderIn,
    school: SchoolAdmin,
    db: SessionDep,
    settings: SettingsDep,
    queue: QueueDep,
) -> PlacedOut:
    """One order for the class: an item per approved copy at the price list's tier, one invoice."""
    if not body.accept_terms:
        raise ApiError("terms_required", 422)
    cb = await _class(db, school, classroom_id)
    if cb.order_id is not None or cb.status in (ClassBookStatus.ordered, ClassBookStatus.printing):
        raise ApiError("already_ordered", 409)
    cq = await class_quote(db, school.org, cb)
    if not cq.copies:
        raise ApiError("nothing_to_order", 409)
    values = (await runtime_settings.current(db, settings)).values
    usd_ils = Decimal(str(values.get("usd_ils") or "3.70"))
    org, q = school.org, cq.quote
    order = Order(
        code=await _new_code(db),
        user_id=school.user.id,
        organization_id=org.id,
        status=OrderStatus.new,
        payment_method=PaymentMethod.cod,
        currency=cq.currency,
        subtotal=q.subtotal,
        discount=q.discount,
        delivery_fee=q.shipping + q.cod_fee,
        total=q.total,
        shipping={**_delivery(school), "notes": body.notes, "classroom": str(classroom_id)},
        phone=org.phone,
        zone_id=cq.zone.id if cq.zone else None,
        price_list_id=cq.price_list.id if cq.price_list else None,
        pricing=_quote_json(q),
        source="portal",
    )
    db.add(order)
    await db.flush()
    prices = {p.key: p for p in q.items}
    costs = item_costs(cq, usd_ils)
    for book, child in cq.copies:
        p = prices[str(book.id)]
        db.add(
            OrderItem(
                order_id=order.id,
                book_id=book.id,
                variant_id=cq.variant.id,
                sku=cq.variant.sku,
                line=cq.product.line.value,
                title={
                    "name_ar": cq.product.name_ar,
                    "name_en": cq.product.name_en,
                    "options": cq.variant.options,
                },
                style_slug=cb.art_style,
                child_id=child.id,
                personalization={"child_name": child.first_name, "gender": child.gender.value, "class": True},
                addons=[],
                quantity=1,
                unit_price=p.unit_price,
                discount=p.sale_discount + p.bundle_discount + p.coupon_discount,
                costs=costs,
            )
        )
    order.cost_ils = (
        Decimal(costs["total"]) * len(cq.copies) + (cq.zone.cost_ils if cq.zone else 0)
    ).quantize(Decimal("0.01"))
    db.add(
        OrderEvent(order_id=order.id, kind="status", to_status=OrderStatus.new, note="kindergarten portal")
    )
    db.add(
        AuditLog(
            actor_user_id=school.user.id, action="order.placed", entity_type="order", entity_id=str(order.id)
        )
    )
    invoice = await issue_invoice(db, order)
    cb.order_id, cb.status = order.id, ClassBookStatus.ordered
    await db.commit()
    enqueue(queue, "qamra_worker.jobs.invoices.render_invoice", str(invoice.id))
    return PlacedOut(
        code=order.code,
        status=order.status.value,
        currency=order.currency.value,
        total=order.total,
        invoice=invoice.number,
    )


class OrderRow(BaseModel):
    code: str
    status: str
    currency: str
    total: Decimal
    copies: int
    placed_at: datetime
    invoice: str | None
    invoice_ready: bool


@router.get("/orders")
async def orders(school: SchoolAdmin, db: SessionDep) -> list[OrderRow]:
    rows = (
        (
            await db.execute(
                select(Order).where(Order.organization_id == school.org.id).order_by(Order.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    out = []
    for order in rows:
        invoice = (await db.execute(select(Invoice).where(Invoice.order_id == order.id))).scalar_one_or_none()
        items = (await db.execute(select(OrderItem.quantity).where(OrderItem.order_id == order.id))).scalars()
        out.append(
            OrderRow(
                code=order.code,
                status=order.status.value,
                currency=order.currency.value,
                total=order.total,
                copies=sum(items),
                placed_at=order.created_at,
                invoice=invoice.number if invoice else None,
                invoice_ready=bool(invoice and invoice.pdf_key),
            )
        )
    return out


@router.get("/orders/{code}/invoice.pdf")
async def invoice_pdf(code: str, school: SchoolAdmin, db: SessionDep, storage: StorageDep) -> Response:
    order = (await db.execute(select(Order).where(Order.code == code.strip().upper()))).scalar_one_or_none()
    if order is None or order.organization_id != school.org.id:
        raise ApiError("not_found", 404)
    invoice = (await db.execute(select(Invoice).where(Invoice.order_id == order.id))).scalar_one_or_none()
    if invoice is None or not invoice.pdf_key:
        raise ApiError("not_ready", 409)
    return Response(
        storage.get(invoice.pdf_key),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{invoice.number}.pdf"',
            "Cache-Control": "no-store",
        },
    )
