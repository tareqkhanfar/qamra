"""Print batches (CLAUDE.md §7 step 7, Phase 3): which orders are ready to print, grouping them, the manifest.

An order is ready when it is confirmed (or further, up to `review`), not in a batch yet, and every printed
item in it has a book an admin approved (Addendum 3 §5: the only way to print) with its interior and cover
PDFs. Items without a personalized book (e.g. workbooks) keep an order out of batches: they have their own
production path. Families' orders share a batch per day; each kindergarten gets its own batch per day.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import Book, BookStatus, Order, OrderItem, OrderStatus, PrintBatch, PrintBatchStatus
from qamra_core.printing import PRINTED_FORMATS, item_copies, item_extras, item_format, item_inserts

READY_FROM = (OrderStatus.confirmed, OrderStatus.generating, OrderStatus.review)


@dataclass
class Candidate:
    order: Order
    items: list[OrderItem] = field(default_factory=list)  # the printed items
    books: dict[uuid.UUID, Book] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return bool(self.items) and all(
            i.book_id in self.books and printable(self.books[i.book_id]) for i in self.items
        )


def printed(item: OrderItem) -> bool:
    return item_format(item.title.get("options") or {}, item.addons or []) in PRINTED_FORMATS


def printable(book: Book) -> bool:
    return book.status == BookStatus.approved and bool(book.pdf_interior_key and book.pdf_cover_key)


async def _candidates(db: AsyncSession, orders: list[Order]) -> list[Candidate]:
    ids = [o.id for o in orders]
    items = (
        (await db.execute(select(OrderItem).where(OrderItem.order_id.in_(ids)))).scalars().all()
        if ids
        else []
    )
    book_ids = {i.book_id for i in items if i.book_id}
    books = (
        {b.id: b for b in (await db.execute(select(Book).where(Book.id.in_(book_ids)))).scalars()}
        if book_ids
        else {}
    )
    out = {o.id: Candidate(o) for o in orders}
    for item in items:
        if printed(item):
            c = out[item.order_id]
            c.items.append(item)
            if item.book_id in books:
                c.books[item.book_id] = books[item.book_id]
    return [c for c in out.values() if c.items]


async def waiting_orders(db: AsyncSession, limit: int = 500) -> list[Candidate]:
    """Printed orders not in a batch yet, ready or still waiting for their books' approval."""
    orders = (
        (
            await db.execute(
                select(Order)
                .where(Order.status.in_(READY_FROM), Order.print_batch_id.is_(None))
                .order_by(Order.created_at, Order.code)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return await _candidates(db, list(orders))


async def collect(db: AsyncSession, today: date | None = None) -> list[PrintBatch]:
    """Put every ready order into today's open batch for its organization (or the families' batch)."""
    today = today or datetime.now(UTC).date()
    touched: dict[uuid.UUID | None, PrintBatch] = {}
    for c in await waiting_orders(db):
        if not c.ready:
            continue
        org = c.order.organization_id
        batch = touched.get(org)
        if batch is None:
            batch = (
                await db.execute(
                    select(PrintBatch).where(
                        PrintBatch.status == PrintBatchStatus.open,
                        PrintBatch.batch_date == today,
                        PrintBatch.organization_id.is_(None)
                        if org is None
                        else PrintBatch.organization_id == org,
                    )
                )
            ).scalar_one_or_none()
            if batch is None:
                batch = PrintBatch(
                    organization_id=org, batch_date=today, status=PrintBatchStatus.open, manifest={}
                )
                db.add(batch)
                await db.flush()
            touched[org] = batch
        c.order.print_batch_id = batch.id
    return list(touched.values())


async def batch_candidates(db: AsyncSession, batch: PrintBatch) -> list[Candidate]:
    orders = (
        (
            await db.execute(
                select(Order).where(Order.print_batch_id == batch.id).order_by(Order.created_at, Order.code)
            )
        )
        .scalars()
        .all()
    )
    return await _candidates(db, list(orders))


def build_manifest(candidates: list[Candidate], sends: int) -> dict[str, Any]:
    """Frozen when the batch is sent: what the printer prints, one line per book, with its files."""
    items: list[dict[str, Any]] = []
    for c in candidates:
        for item in c.items:
            book = c.books.get(item.book_id) if item.book_id else None
            options = item.title.get("options") or {}
            items.append(
                {
                    "n": len(items) + 1,
                    "order": c.order.code,
                    "order_id": str(c.order.id),
                    "item_id": str(item.id),
                    "book_id": str(item.book_id),
                    "sku": item.sku,
                    "format": item_format(options, item.addons or []),
                    "size": options.get("size"),
                    "copies": item_copies(item.quantity, item.addons or []),
                    "extras": item_extras(item.addons or []),
                    "interior_key": book.pdf_interior_key if book else None,
                    "cover_key": book.pdf_cover_key if book else None,
                    # the sheets printed apart (name → key): a sticker sheet, card stock, a bought answer key
                    "inserts": item_inserts((book.generation or {}).get("files") or {}, item.addons or [])
                    if book
                    else {},
                    # Addendum 9: a gift parcel has no prices inside and carries the parent's card message
                    "gift": bool(c.order.gift),
                    "gift_message": c.order.gift_message if c.order.gift else None,
                }
            )
    return {
        "sends": sends,
        "built_at": datetime.now(UTC).isoformat(),
        "orders": [c.order.code for c in candidates],
        "items": items,
    }
