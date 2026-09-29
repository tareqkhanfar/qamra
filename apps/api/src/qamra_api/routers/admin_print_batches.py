"""Admin: print batches (CLAUDE.md §7 step 7, Phase 3), for staff with the `print` permission.

Collect the approved books of printed orders into batches → send a batch (its manifest is frozen, the orders
move to `printing`, the printer gets an email with file links) → the printer's progress (printing → done;
books become `printed`) → ship (the orders move to `shipped`). Every move is an order event and an email.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from qamra_api import notify, order_flow, runtime_settings
from qamra_api.deps import AdminUser, SessionDep, SettingsDep, require_permission
from qamra_api.errors import ApiError
from qamra_api.print_batches import Candidate, batch_candidates, build_manifest, collect, waiting_orders
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Notification,
    Order,
    OrderItem,
    OrderStatus,
    Organization,
    PrintBatch,
    PrintBatchStatus,
)
from qamra_core.printing import batch_code, item_copies, item_format, manifest_csv

router = APIRouter(
    prefix="/api/admin/print-batches", tags=["admin"], dependencies=[Depends(require_permission("print"))]
)
B = PrintBatchStatus
PAST_APPROVAL = (BookStatus.approved, BookStatus.ordered, BookStatus.printed)


class OrderBrief(BaseModel):
    id: uuid.UUID
    code: str
    status: str
    city: str | None
    organization: str | None
    books: int
    approved: int
    ready: bool


class BatchRow(BaseModel):
    id: uuid.UUID
    code: str
    batch_date: str
    status: str
    organization: str | None
    orders: int
    books: int
    copies: int
    sent_at: datetime | None
    printer_notified_at: datetime | None
    done_at: datetime | None


class BatchesOut(BaseModel):
    ready: list[OrderBrief]
    waiting: list[OrderBrief]
    batches: list[BatchRow]
    printer_email_set: bool


class ItemRow(BaseModel):
    n: int | None
    book_id: uuid.UUID | None
    title: str
    child_name: str | None
    format: str
    copies: int
    book_status: str | None
    files: bool


class BatchOrder(BaseModel):
    id: uuid.UUID
    code: str
    status: str
    city: str | None
    items: list[ItemRow]


class BatchDetail(BatchRow):
    orders_list: list[OrderBrief]
    items: list[BatchOrder]
    email: str | None  # the last printer email's outcome: sent | logged | skipped | failed | pending
    link_expires_at: datetime | None
    actions: list[str]


async def _org_names(db: SessionDep, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    real = {i for i in ids if i}
    if not real:
        return {}
    rows = (
        await db.execute(select(Organization.id, Organization.name).where(Organization.id.in_(real)))
    ).all()
    return {i: n for i, n in rows}


def _brief(c: Candidate, orgs: dict[uuid.UUID, str]) -> OrderBrief:
    approved = sum(1 for i in c.items if i.book_id in c.books and c.books[i.book_id].status in PAST_APPROVAL)
    return OrderBrief(
        id=c.order.id,
        code=c.order.code,
        status=c.order.status.value,
        city=c.order.shipping.get("city"),
        organization=orgs.get(c.order.organization_id) if c.order.organization_id else None,
        books=len(c.items),
        approved=approved,
        ready=c.ready,
    )


def _actions(batch: PrintBatch) -> list[str]:
    if batch.status == B.done:
        return [] if batch.manifest.get("shipped_at") else ["ship"]
    return {B.open: ["send"], B.sent: ["printing", "resend"], B.printing: ["done", "resend"]}[batch.status]


async def _row(db: SessionDep, batch: PrintBatch, orgs: dict[uuid.UUID, str]) -> BatchRow:
    candidates = await batch_candidates(db, batch)
    if batch.manifest.get("items"):
        books, copies = len(batch.manifest["items"]), sum(int(i["copies"]) for i in batch.manifest["items"])
    else:
        books = sum(len(c.items) for c in candidates)
        copies = sum(item_copies(i.quantity, i.addons or []) for c in candidates for i in c.items)
    return BatchRow(
        id=batch.id,
        code=batch_code(batch.id, batch.batch_date),
        batch_date=batch.batch_date.isoformat(),
        status=batch.status.value,
        organization=orgs.get(batch.organization_id) if batch.organization_id else None,
        orders=len(candidates),
        books=books,
        copies=copies,
        sent_at=batch.sent_at,
        printer_notified_at=batch.printer_notified_at,
        done_at=batch.done_at,
    )


async def _values(db: SessionDep, settings: SettingsDep) -> dict[str, Any]:
    return dict((await runtime_settings.current(db, settings)).values)


async def _overview(db: SessionDep, settings: SettingsDep) -> BatchesOut:
    candidates = await waiting_orders(db)
    batches = (
        (
            await db.execute(
                select(PrintBatch)
                .order_by(PrintBatch.batch_date.desc(), PrintBatch.created_at.desc())
                .limit(60)
            )
        )
        .scalars()
        .all()
    )
    orgs = await _org_names(
        db, {c.order.organization_id for c in candidates} | {b.organization_id for b in batches}
    )
    return BatchesOut(
        ready=[_brief(c, orgs) for c in candidates if c.ready],
        waiting=[_brief(c, orgs) for c in candidates if not c.ready],
        batches=[await _row(db, b, orgs) for b in batches],
        printer_email_set=bool(str((await _values(db, settings)).get("printer_email") or "").strip()),
    )


@router.get("")
async def list_batches(db: SessionDep, settings: SettingsDep) -> BatchesOut:
    return await _overview(db, settings)


@router.post("/collect")
async def collect_batches(admin: AdminUser, db: SessionDep, settings: SettingsDep) -> BatchesOut:
    """Today's batches: every ready order joins its organization's (or the families') open batch."""
    for batch in await collect(db):
        db.add(
            AuditLog(
                actor_user_id=admin.id,
                action="print_batch.collected",
                entity_type="print_batch",
                entity_id=str(batch.id),
            )
        )
    await db.commit()
    return await _overview(db, settings)


async def _batch(db: SessionDep, batch_id: uuid.UUID) -> PrintBatch:
    batch = await db.get(PrintBatch, batch_id)
    if batch is None:
        raise ApiError("not_found", 404)
    return batch


async def _detail(db: SessionDep, batch: PrintBatch) -> BatchDetail:
    candidates = await batch_candidates(db, batch)
    orgs = await _org_names(db, {batch.organization_id, *(c.order.organization_id for c in candidates)})
    numbers = {i["item_id"]: int(i["n"]) for i in batch.manifest.get("items", [])}
    email = (
        await db.execute(
            select(Notification.status)
            .where(Notification.print_batch_id == batch.id)
            .order_by(Notification.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    row = await _row(db, batch, orgs)
    return BatchDetail(
        **row.model_dump(),
        orders_list=[_brief(c, orgs) for c in candidates],
        items=[
            BatchOrder(
                id=c.order.id,
                code=c.order.code,
                status=c.order.status.value,
                city=c.order.shipping.get("city"),
                items=[_item_row(c, i, numbers) for i in c.items],
            )
            for c in candidates
        ],
        email=email.value if email is not None else None,
        link_expires_at=batch.printer_token_expires_at,
        actions=_actions(batch),
    )


def _item_row(c: Candidate, item: OrderItem, numbers: dict[str, int]) -> ItemRow:
    book = c.books.get(item.book_id) if item.book_id else None
    return ItemRow(
        n=numbers.get(str(item.id)),
        book_id=item.book_id,
        title=str(item.title.get("name_ar") or item.sku or ""),
        child_name=item.personalization.get("child_name"),
        format=item_format(item.title.get("options") or {}, item.addons or []),
        copies=item_copies(item.quantity, item.addons or []),
        book_status=book.status.value if book else None,
        files=bool(book and book.pdf_interior_key and book.pdf_cover_key),
    )


@router.get("/{batch_id}")
async def batch_detail(batch_id: uuid.UUID, db: SessionDep) -> BatchDetail:
    return await _detail(db, await _batch(db, batch_id))


def _audit(admin: AdminUser, action: str, batch: PrintBatch, **data: Any) -> AuditLog:
    return AuditLog(
        actor_user_id=admin.id,
        action=f"print_batch.{action}",
        entity_type="print_batch",
        entity_id=str(batch.id),
        data=data,
    )


@router.post("/{batch_id}/send")
async def send_batch(batch_id: uuid.UUID, request: Request, admin: AdminUser, db: SessionDep) -> BatchDetail:
    """Freeze the manifest, move the orders to `printing` and email the printer the file links."""
    batch = await _batch(db, batch_id)
    if batch.status != B.open:
        raise ApiError("invalid_transition", 409, details={"from": batch.status.value, "to": "sent"})
    candidates = await batch_candidates(db, batch)
    if not candidates:
        raise ApiError("batch_empty", 409)
    blocked = [
        c.order.code
        for c in candidates
        if not c.ready or order_flow.path(c.order.status, OrderStatus.printing) is None
    ]
    if blocked:
        raise ApiError("batch_not_ready", 409, details={"orders": blocked})
    code = batch_code(batch.id, batch.batch_date)
    batch.manifest = build_manifest(candidates, sends=1)
    batch.status, batch.sent_at = B.sent, datetime.now(UTC)
    moved: dict[uuid.UUID, list[OrderStatus]] = {}
    for c in candidates:
        moved[c.order.id] = order_flow.move(
            db, c.order, OrderStatus.printing, admin.id, f"print batch {code}", {"print_batch": code}
        )
        for book in c.books.values():
            book.status = BookStatus.ordered  # «قيد الطباعة» on the parent's shelf
    db.add(_audit(admin, "sent", batch, books=len(batch.manifest["items"])))
    await db.commit()
    connection = request.app.state.rq_redis
    notify.print_batch_sent(connection, batch.id)
    for order_id, steps in moved.items():
        notify.order_statuses(connection, order_id, steps)
    return await _detail(db, batch)


@router.post("/{batch_id}/resend")
async def resend_batch(
    batch_id: uuid.UUID, request: Request, admin: AdminUser, db: SessionDep
) -> BatchDetail:
    """A new printer email with a new link (the previous link stops working)."""
    batch = await _batch(db, batch_id)
    if batch.status not in (B.sent, B.printing):
        raise ApiError("invalid_transition", 409, details={"from": batch.status.value, "to": "sent"})
    batch.manifest = {**batch.manifest, "sends": int(batch.manifest.get("sends") or 1) + 1}
    batch.printer_token_hash = batch.printer_token_expires_at = None
    db.add(_audit(admin, "resent", batch))
    await db.commit()
    notify.print_batch_sent(request.app.state.rq_redis, batch.id)
    return await _detail(db, batch)


class PrinterStatusIn(BaseModel):
    to: Literal["printing", "done"]


@router.post("/{batch_id}/status")
async def printer_status(
    batch_id: uuid.UUID, body: PrinterStatusIn, admin: AdminUser, db: SessionDep
) -> BatchDetail:
    """The printer's progress, as they report it: sent → printing → done (the books are then printed)."""
    batch = await _batch(db, batch_id)
    goal = B(body.to)
    if {B.sent: B.printing, B.printing: B.done}.get(batch.status) != goal:
        raise ApiError("invalid_transition", 409, details={"from": batch.status.value, "to": goal.value})
    now = datetime.now(UTC)
    batch.status = goal
    if goal == B.printing:
        batch.printing_at = now
    else:
        batch.done_at = now
        ids = [uuid.UUID(i["book_id"]) for i in batch.manifest.get("items", []) if i.get("book_id")]
        for book in (await db.execute(select(Book).where(Book.id.in_(ids)))).scalars() if ids else []:
            if book.status == BookStatus.ordered:
                book.status = BookStatus.printed
    db.add(_audit(admin, goal.value, batch))
    await db.commit()
    return await _detail(db, batch)


@router.post("/{batch_id}/ship")
async def ship_batch(batch_id: uuid.UUID, request: Request, admin: AdminUser, db: SessionDep) -> BatchDetail:
    """The printed parcels left with the courier: every order still `printing` moves to `shipped`."""
    batch = await _batch(db, batch_id)
    if batch.status != B.done or batch.manifest.get("shipped_at"):
        raise ApiError("invalid_transition", 409, details={"from": batch.status.value, "to": "shipped"})
    code = batch_code(batch.id, batch.batch_date)
    moved: dict[uuid.UUID, list[OrderStatus]] = {}
    for c in await batch_candidates(db, batch):
        if c.order.status == OrderStatus.printing:
            moved[c.order.id] = order_flow.move(
                db, c.order, OrderStatus.shipped, admin.id, f"print batch {code}", {"print_batch": code}
            )
    batch.manifest = {**batch.manifest, "shipped_at": datetime.now(UTC).isoformat()}
    db.add(_audit(admin, "shipped", batch, orders=len(moved)))
    await db.commit()
    for order_id, steps in moved.items():
        notify.order_statuses(request.app.state.rq_redis, order_id, steps)
    return await _detail(db, batch)


@router.delete("/{batch_id}/orders/{order_id}")
async def remove_order(
    batch_id: uuid.UUID, order_id: uuid.UUID, admin: AdminUser, db: SessionDep
) -> BatchDetail:
    """Take an order out of a batch that hasn't been sent (e.g. cancelled, or to print it later)."""
    batch = await _batch(db, batch_id)
    order = await db.get(Order, order_id)
    if order is None or order.print_batch_id != batch.id:
        raise ApiError("not_found", 404)
    if batch.status != B.open:
        raise ApiError("invalid_transition", 409, details={"from": batch.status.value, "to": "open"})
    order.print_batch_id = None
    db.add(_audit(admin, "order_removed", batch, order=order.code))
    await db.commit()
    return await _detail(db, batch)


@router.get("/{batch_id}/manifest.csv")
async def batch_manifest(batch_id: uuid.UUID, db: SessionDep) -> Response:
    batch = await _batch(db, batch_id)
    manifest = (
        batch.manifest
        if batch.manifest.get("items")
        else build_manifest(await batch_candidates(db, batch), 0)
    )
    return Response(
        manifest_csv(manifest),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{batch_code(batch.id, batch.batch_date)}.csv"',
            "Cache-Control": "no-store",
        },
    )
