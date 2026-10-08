"""Digital delivery (docs/plans/digital-delivery.md): the home-print copies and the "ready to download" email.

    qamra_worker.jobs.downloads.prepare_file(book_id, kind)   one home copy, when the parent taps «تنزيل PDF»
    qamra_worker.jobs.downloads.scan_ready_lines()            cron, every 5 minutes: digital lines now ready
    qamra_worker.jobs.downloads.deliver_line(item_id)         a ready line's copies, then its email (once)

A home copy is the print file without the printer's bleed (`qamra_pdf.home`), the book with its cover
around it. It is cut from the print files, so it costs no AI and no render: a second or two for a 120-page
volume. It is stored at `children/{child}/books/{book}/home/{kind}/{version}.pdf`, the version being the print
files' ETags: a re-render makes a new copy and the old one is deleted. «حذف كل بيانات طفلي» deletes the
child's prefix, these copies with it.

The email links to the account page, never to the file: the file opens only for the signed-in parent.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from redis import Redis
from rq import Queue, Retry, get_current_job
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core import downloads as dl
from qamra_core.db.models import Book, Child, Locale, Notification, NotificationStatus, Order, OrderItem
from qamra_core.storage import ObjectStorage
from qamra_pdf.home import home_book, home_sheets
from qamra_worker import context
from qamra_worker.jobs.notify import _recipient, base_values, sender_and_values
from qamra_worker.notify.email import EmailSender
from qamra_worker.notify.ledger import claim, deliver, finish
from qamra_worker.notify.templates import render
from qamra_worker.queues import PDF
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.downloads")
FAILED_SECONDS = 3600  # the parent's «حاولوا مرة أخرى» clears it sooner
SCAN_DAYS = 60  # older orders were delivered long ago (or their emails went out)
DELIVER_GUARD_SECONDS = 30 * 60
TEMPLATE = "download_ready"


def notice_key(item_id: uuid.UUID | str) -> str:
    return f"download:{item_id}"


# ---- the home copies ---------------------------------------------------------------------------------------


def copy_version(storage: ObjectStorage, book: Book, kind: str) -> str | None:
    """The version of the copy the current print files make; None while a print file is missing."""
    sources = dl.sources_of(book, kind)
    etags = [storage.etag(k) for k in sources]
    if not sources or any(e is None for e in etags):
        return None
    return dl.version_of([e for e in etags if e])


def make_copy(storage: ObjectStorage, book: Book, kind: str) -> str:
    """The home copy's key, made now unless it exists. Raises when the print files are missing or broken."""
    version = copy_version(storage, book, kind)
    if version is None:
        raise FileNotFoundError(f"book {book.id}: no print file for {kind}")
    key = dl.home_key(book, kind, version)
    if storage.exists(key):
        return key
    if kind == dl.BOOK:
        assert book.pdf_interior_key  # nosec B101 (copy_version found it)
        cover = storage.get(book.pdf_cover_key) if book.pdf_cover_key else None
        data = home_book(
            storage.get(book.pdf_interior_key),
            cover,
            front_left=book.language != Locale.en,  # an Arabic book's wrap has its front on the left
            title=book.title,
        )
    else:
        data = home_sheets(storage.get(dl.sources_of(book, kind)[0]), title=book.title)
    storage.delete_prefix(f"{dl.home_prefix(book)}{kind}/")  # the copy of an older render
    storage.put(key, data, "application/pdf")
    log.info("downloads.copy_made", book=str(book.id), kind=kind, kb=len(data) // 1024)
    return key


def prepare(db: Session, storage: ObjectStorage, conn: Redis | None, book_id: str, kind: str) -> str:
    """One copy; its Redis state for the API: `prep` cleared when done, `failed` set when it can't be made."""
    book = db.get(Book, uuid.UUID(book_id))
    if book is None or kind not in dl.KINDS:
        return "missing"
    version = copy_version(storage, book, kind) or "none"
    try:
        make_copy(storage, book, kind)
    except Exception:
        log.exception("downloads.copy_failed", book=book_id, kind=kind)
        if conn is not None:
            conn.set(dl.state_key(book_id, kind, version, "failed"), "1", ex=FAILED_SECONDS)
        return "failed"  # not raised: the parent sees «تعذّر تجهيز الملف» and taps again
    finally:
        if conn is not None:
            conn.delete(dl.state_key(book_id, kind, version, "prep"))
    return "ready"


def prepare_file(book_id: str, kind: str) -> str:
    """RQ entry point (queue `pdf`): asked for by the API when the parent taps «تنزيل PDF»."""
    context.init_process()
    job = get_current_job()
    with context.db_session() as db:
        return prepare(db, context.storage(), job.connection if job else None, book_id, kind)


# ---- which lines became downloadable ----------------------------------------------------------------------


def line_books(db: Session, items: list[OrderItem]) -> list[Book]:
    query = dl.books_query(items)
    return list(db.scalars(query)) if query is not None else []


def ready_lines(db: Session, now: datetime | None = None) -> list[uuid.UUID]:
    """Digital lines of live orders, every book ready, whose parent has not been emailed about them yet."""
    since = (now or datetime.now(UTC)) - timedelta(days=SCAN_DAYS)
    rows = db.execute(
        select(OrderItem, Order)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.status.in_(dl.LIVE_ORDERS),
            Order.created_at >= since,
            OrderItem.child_id.is_not(None),
            OrderItem.title["options"]["format"].astext == dl.DIGITAL,
        )
    ).all()
    if not rows:
        return []
    told = set(
        db.scalars(
            select(Notification.dedupe_key).where(
                Notification.dedupe_key.in_([notice_key(i.id) for i, _ in rows])
            )
        )
    )
    waiting = [(i, o) for i, o in rows if notice_key(i.id) not in told]
    books = line_books(db, [i for i, _ in waiting])
    return [i.id for i, o in waiting if dl.line_state(i, o.status, books).ready]


def scan(db: Session, conn: Redis) -> dict[str, int]:
    ids = ready_lines(db)
    queued = 0
    for item_id in ids:
        if conn.set(f"dl:deliver:{item_id}", "1", nx=True, ex=DELIVER_GUARD_SECONDS):
            Queue(PDF, connection=conn).enqueue(
                "qamra_worker.jobs.downloads.deliver_line",
                str(item_id),
                job_timeout=1800,
                retry=Retry(max=3, interval=[60, 300, 900]),  # an SMTP failure: `claim` lets the retry send
            )
            queued += 1
    return {"ready": len(ids), "queued": queued}


def scan_ready_lines() -> dict[str, int]:
    """RQ cron entry point (`cron_config`)."""
    context.init_process()
    job = get_current_job()
    if job is None:
        return {"ready": 0, "queued": 0}
    with context.db_session() as db:
        return scan(db, job.connection)


# ---- the email -------------------------------------------------------------------------------------------


def deliver_email(
    db: Session,
    storage: ObjectStorage,
    sender: EmailSender,
    item_id: str,
    base_url: str,
    values: dict[str, Any],
) -> str:
    """Make the line's copies (so the first tap downloads at once), then tell the parent, once per line."""
    item = db.get(OrderItem, uuid.UUID(item_id))
    order = db.get(Order, item.order_id) if item else None
    child = db.get(Child, item.child_id) if item and item.child_id else None
    if item is None or order is None or child is None:
        return "missing"
    books = line_books(db, [item])
    state = dl.line_state(item, order.status, books)
    if not state.ready or not dl.sold_as_file(item):
        return "not_ready"
    for ref in state.files:
        try:
            make_copy(storage, state.books[ref.book_id], ref.kind)
        except Exception:  # the parent's tap asks again; the email still goes
            log.exception("downloads.copy_failed", book=str(ref.book_id), kind=ref.kind)
    owner = order.user_id or child.guardian_user_id
    note = claim(db, notice_key(item.id), TEMPLATE, order_id=order.id, user_id=owner)
    if note is None:
        return "duplicate"
    user = _recipient(db, owner)
    parent = user is not None and child.guardian_user_id == user.id
    if user is None or not parent or not values.get("email_notifications_enabled", True):
        finish(db, note, NotificationStatus.skipped, "disabled" if parent else "no_recipient")
        return NotificationStatus.skipped.value
    lang: dl.Lang = "en" if user.locale == Locale.en else "ar"
    rendered = render(
        TEMPLATE,
        lang,
        {
            **base_values(values, lang),
            "name": str(order.shipping.get("name") or user.full_name),
            "child": child.first_name,
            "title": dl.line_title(item, child.first_name, list(state.books.values()), lang),
            "account_url": f"{base_url}/{lang}/account#downloads",
        },
    )
    return deliver(db, sender, note, user.email, rendered).value


def deliver_line(item_id: str) -> str:
    """RQ entry point (queue `pdf`), enqueued by the scan."""
    context.init_process()
    with context.db_session() as db:
        sender, values = sender_and_values(db)
        return deliver_email(
            db, context.storage(), sender, item_id, get_settings().web_base_url.rstrip("/"), values
        )
