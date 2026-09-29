"""Order management (Addendum 4 §5): list, detail, status changes, notes, partial reprints, customer messages
and invoices. Every change is an order event (who, what, when) and an audit-log entry."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote as urlquote

import yaml
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_api import notify, runtime_settings
from qamra_api.classic import CLASSIC_JOB, start_classic_finals
from qamra_api.deps import AdminUser, SessionDep, SettingsDep, StorageDep, require_permission
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_core.db.models import AuditLog, Order, OrderItem, OrderStatus, User
from qamra_core.db.store import Counter, Invoice, OrderEvent

router = APIRouter(prefix="/api/admin/orders", tags=["admin"])
MESSAGES_FILE = CONTENT_DIR / "store" / "messages.yaml"
S = OrderStatus

# The allowed moves (Addendum 4 §5): new → confirmed → generating → review → printing → shipped → delivered,
# cancelled until printing starts, and a reprint from printing onwards.
TRANSITIONS: dict[OrderStatus, tuple[OrderStatus, ...]] = {
    S.new: (S.confirmed, S.cancelled),
    S.confirmed: (S.generating, S.cancelled),
    S.generating: (S.review, S.cancelled),
    S.review: (S.printing, S.generating, S.cancelled),
    S.printing: (S.shipped, S.reprint),
    S.shipped: (S.delivered, S.reprint),
    S.delivered: (S.reprint,),
    S.reprint: (S.printing,),
    S.cancelled: (),
}


class OrderRow(BaseModel):
    id: uuid.UUID
    code: str
    status: str
    created_at: datetime
    customer: str
    phone: str | None
    city: str | None
    items: int
    currency: str
    total: Decimal
    cost_ils: Decimal
    source: str
    gift: bool = False  # Addendum 9


class OrdersOut(BaseModel):
    orders: list[OrderRow]
    total: int
    counts: dict[str, int]


@router.get("", dependencies=[Depends(require_permission("orders.view"))])
async def list_orders(
    db: SessionDep, status: str | None = None, q: str | None = None, page: int = 1
) -> OrdersOut:
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == OrderStatus(status))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Order.code.ilike(like), Order.phone.ilike(like), Order.shipping["name"].astext.ilike(like))
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (await db.execute(stmt.order_by(Order.created_at.desc()).limit(50).offset(50 * (max(page, 1) - 1))))
        .scalars()
        .all()
    )
    items = dict(
        (
            await db.execute(
                select(OrderItem.order_id, func.sum(OrderItem.quantity))
                .where(OrderItem.order_id.in_([o.id for o in rows]))
                .group_by(OrderItem.order_id)
            )
        ).all()
    )
    counts = dict((await db.execute(select(Order.status, func.count()).group_by(Order.status))).all())
    return OrdersOut(
        orders=[
            OrderRow(
                id=o.id,
                code=o.code,
                status=o.status.value,
                created_at=o.created_at,
                customer=str(o.shipping.get("name", "")),
                phone=o.phone,
                city=o.shipping.get("city"),
                items=int(items.get(o.id, 0)),
                currency=o.currency.value,
                total=o.total,
                cost_ils=o.cost_ils,
                source=o.source,
                gift=o.gift,
            )
            for o in rows
        ],
        total=int(total),
        counts={k.value: int(v) for k, v in counts.items()},
    )


class ItemOut(BaseModel):
    id: uuid.UUID
    sku: str | None
    title: dict[str, Any]
    child_name: str | None
    theme: str | None
    style: str | None
    quantity: int
    unit_price: Decimal
    discount: Decimal
    addons: list[Any]
    costs: dict[str, Any]
    book_id: uuid.UUID | None


class EventOut(BaseModel):
    kind: str
    from_status: str | None
    to_status: str | None
    note: str | None
    data: dict[str, Any]
    actor: str | None
    at: datetime


class InvoiceOut(BaseModel):
    number: str
    issued_at: datetime
    ready: bool


class OrderOut(BaseModel):
    id: uuid.UUID
    code: str
    status: str
    next_statuses: list[str]
    created_at: datetime
    currency: str
    subtotal: Decimal
    discount: Decimal
    delivery_fee: Decimal
    total: Decimal
    cost_ils: Decimal
    pricing: dict[str, Any]
    shipping: dict[str, Any]
    payment_method: str
    payment_status: str
    items: list[ItemOut]
    events: list[EventOut]
    invoice: InvoiceOut | None
    messages: dict[str, str]  # ready-to-send WhatsApp links per status template
    revenue_ils: Decimal
    margin_pct: Decimal | None  # with the unit costs frozen at ordering (Addendum 4 §6)
    margin_floor_pct: int
    # Addendum 9: a gift order (its packing slip hides the prices) and the card message to print
    gift: bool = False
    gift_message: str | None = None


def load_messages() -> dict[str, dict[str, str]]:
    data = yaml.safe_load(Path(MESSAGES_FILE).read_text(encoding="utf-8")) or {}
    return {str(k): {str(lang): str(text) for lang, text in v.items()} for k, v in data.items()}


def _money(amount: Decimal, currency: str) -> str:
    value = f"{amount:.2f}".rstrip("0").rstrip(".")
    return f"{value} ₪" if currency == "ILS" else f"{value} JD"


def whatsapp_links(order: Order, base_url: str = "https://qamra.app") -> dict[str, str]:
    """wa.me links with each template filled in, in Arabic (the store's customers write Arabic first)."""
    phone = "".join(ch for ch in (order.phone or "") if ch.isdigit())
    if phone.startswith("0"):
        phone = ("962" if order.currency.value == "JOD" else "970") + phone[1:]
    values = {
        "name": str(order.shipping.get("name", "")),
        "code": order.code,
        "total": _money(order.total, order.currency.value),
        "track_url": f"{base_url}/ar/track",
    }
    return {
        status: f"https://wa.me/{phone}?text={urlquote(texts.get('ar', '').format(**values))}"
        for status, texts in load_messages().items()
    }


async def _order(db: SessionDep, order_id: uuid.UUID) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise ApiError("not_found", 404)
    return order


async def _detail(db: SessionDep, order: Order, values: dict[str, Any]) -> OrderOut:
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    events = (
        (
            await db.execute(
                select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.created_at)
            )
        )
        .scalars()
        .all()
    )
    actors = {
        u.id: u.full_name
        for u in (
            await db.execute(
                select(User).where(User.id.in_([e.actor_user_id for e in events if e.actor_user_id]))
            )
        ).scalars()
    }
    invoice = (await db.execute(select(Invoice).where(Invoice.order_id == order.id))).scalar_one_or_none()
    rate = Decimal(str(values.get("jod_ils") or "5.22")) if order.currency.value == "JOD" else Decimal("1")
    revenue = (order.total * rate).quantize(Decimal("0.01"))
    margin = ((revenue - order.cost_ils) / revenue * 100).quantize(Decimal("0.1")) if revenue > 0 else None
    return OrderOut(
        id=order.id,
        code=order.code,
        status=order.status.value,
        next_statuses=[s.value for s in TRANSITIONS[order.status]],
        created_at=order.created_at,
        currency=order.currency.value,
        subtotal=order.subtotal,
        discount=order.discount,
        delivery_fee=order.delivery_fee,
        total=order.total,
        cost_ils=order.cost_ils,
        pricing=order.pricing,
        shipping=order.shipping,
        payment_method=order.payment_method.value,
        payment_status=order.payment_status.value,
        items=[
            ItemOut(
                id=i.id,
                sku=i.sku,
                title=i.title,
                child_name=i.personalization.get("child_name"),
                theme=i.theme_slug,
                style=i.style_slug,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount,
                addons=i.addons,
                costs=i.costs,
                book_id=i.book_id,
            )
            for i in items
        ],
        events=[
            EventOut(
                kind=e.kind,
                from_status=e.from_status.value if e.from_status else None,
                to_status=e.to_status.value if e.to_status else None,
                note=e.note,
                data=e.data,
                actor=actors.get(e.actor_user_id) if e.actor_user_id else None,
                at=e.created_at,
            )
            for e in events
        ],
        invoice=InvoiceOut(number=invoice.number, issued_at=invoice.created_at, ready=bool(invoice.pdf_key))
        if invoice
        else None,
        messages=whatsapp_links(order),
        revenue_ils=revenue,
        margin_pct=margin,
        margin_floor_pct=int(values.get("margin_floor_pct") or 35),
        gift=order.gift,
        gift_message=order.gift_message,
    )


@router.get("/{order_id}", dependencies=[Depends(require_permission("orders.view"))])
async def order_detail(order_id: uuid.UUID, db: SessionDep, settings: SettingsDep) -> OrderOut:
    return await _detail(db, await _order(db, order_id), await _values(db, settings))


async def _values(db: SessionDep, settings: SettingsDep) -> dict[str, Any]:
    return dict((await runtime_settings.current(db, settings)).values)


async def issue_invoice(db: SessionDep, order: Order) -> Invoice:
    """A gap-free number per year (INV-2026-00001), taken under a row lock on the year's counter."""
    existing = (await db.execute(select(Invoice).where(Invoice.order_id == order.id))).scalar_one_or_none()
    if existing is not None:
        return existing
    year = datetime.now(UTC).year
    name = f"invoice-{year}"
    await db.execute(
        insert(Counter).values(name=name, value=0).on_conflict_do_nothing(index_elements=["name"])
    )
    counter = (await db.execute(select(Counter).where(Counter.name == name).with_for_update())).scalar_one()
    counter.value += 1
    invoice = Invoice(
        order_id=order.id,
        number=f"INV-{year}-{counter.value:05d}",
        year=year,
        seq=counter.value,
        currency=order.currency,
        total=order.total,
    )
    db.add(invoice)
    await db.flush()
    return invoice


class StatusIn(BaseModel):
    to: OrderStatus
    note: str | None = Field(default=None, max_length=1000)
    items: list[uuid.UUID] = Field(default_factory=list, max_length=50)  # a reprint's items


@router.post("/{order_id}/status", dependencies=[Depends(require_permission("orders"))])
async def change_status(
    order_id: uuid.UUID,
    body: StatusIn,
    admin: AdminUser,
    db: SessionDep,
    queue: QueueDep,
    settings: SettingsDep,
) -> OrderOut:
    order = await _order(db, order_id)
    if body.to not in TRANSITIONS[order.status]:
        raise ApiError("invalid_transition", 409, details={"from": order.status.value, "to": body.to.value})
    data: dict[str, Any] = {}
    if body.to == S.reprint:
        own = {
            i.id
            for i in (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars()
        }
        chosen = [i for i in body.items if i in own]
        if not chosen:
            raise ApiError("reprint_needs_items", 422)
        data["items"] = [str(i) for i in chosen]
    before = order.status
    order.status = body.to
    db.add(
        OrderEvent(
            order_id=order.id,
            actor_user_id=admin.id,
            kind="reprint" if body.to == S.reprint else "status",
            from_status=before,
            to_status=body.to,
            note=body.note,
            data=data,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="order.status_changed",
            entity_type="order",
            entity_id=str(order.id),
            data={"from": before.value, "to": body.to.value},
        )
    )
    render = None
    classic_finals: list[str] = []
    if body.to == S.confirmed:
        render = await issue_invoice(db, order)
        classic_finals = await start_classic_finals(db, order.id)  # Classic books: the whole book now
    await db.commit()
    if render is not None and not render.pdf_key:
        enqueue(queue, "qamra_worker.jobs.invoices.render_invoice", str(render.id))
    for book_id in classic_finals:
        enqueue(queue, CLASSIC_JOB, book_id, "final")
    if body.to == S.confirmed and await db.scalar(
        select(OrderItem.id).where(OrderItem.order_id == order.id, OrderItem.line == "family").limit(1)
    ):  # «مغامراتي مع عائلتي»: its print files, drawn from the plan with the child's character (no AI cost)
        enqueue(queue, "qamra_worker.jobs.family_book.render_order_family_items", str(order.id))
    notify.order_statuses(queue.connection, order.id, [body.to])  # customer email (once per status)
    return await _detail(db, order, await _values(db, settings))


class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


@router.post("/{order_id}/notes", dependencies=[Depends(require_permission("orders"))])
async def add_note(
    order_id: uuid.UUID, body: NoteIn, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> OrderOut:
    order = await _order(db, order_id)
    db.add(OrderEvent(order_id=order.id, actor_user_id=admin.id, kind="note", note=body.note.strip()))
    await db.commit()
    return await _detail(db, order, await _values(db, settings))


class MessageIn(BaseModel):
    template: str = Field(max_length=32)
    channel: Literal["whatsapp"] = "whatsapp"


@router.post("/{order_id}/messages", dependencies=[Depends(require_permission("orders"))])
async def log_message(
    order_id: uuid.UUID, body: MessageIn, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> OrderOut:
    """Staff opened the prepared WhatsApp message: keep a record on the order."""
    order = await _order(db, order_id)
    if body.template not in load_messages():
        raise ApiError("not_found", 404)
    db.add(
        OrderEvent(
            order_id=order.id,
            actor_user_id=admin.id,
            kind="message",
            data={"template": body.template, "channel": body.channel},
        )
    )
    await db.commit()
    return await _detail(db, order, await _values(db, settings))


@router.get("/{order_id}/invoice.pdf", dependencies=[Depends(require_permission("orders.view"))])
async def invoice_pdf(order_id: uuid.UUID, db: SessionDep, storage: StorageDep) -> Response:
    invoice = (await db.execute(select(Invoice).where(Invoice.order_id == order_id))).scalar_one_or_none()
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
