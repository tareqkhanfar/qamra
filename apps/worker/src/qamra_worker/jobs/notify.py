"""Customer emails (Phase 2): the order placed, its status changes (confirmed, printing, shipped, delivered),
a book's preview and its finished files with the reader link (once staff confirmed its words); and the staff
alert that a story waits for its text review.

Enqueued by the API (checkout, the order status change, print batches) and by the book job. The recipient is
the account that owns the order or the book; guest orders have no email address, so nothing is sent.
"""

import uuid
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.models import Book, Child, NotificationStatus, Order, OrderItem, User
from qamra_worker import context
from qamra_worker.jobs.books import brand, resolved_settings
from qamra_worker.notify.email import EmailSender, sender_from_settings
from qamra_worker.notify.ledger import claim, deliver, finish
from qamra_worker.notify.templates import Item, render
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.notify")
ORDER_EVENTS = ("placed", "confirmed", "printing", "shipped", "delivered")
BOOK_EVENTS = ("preview_ready", "book_ready")
FORMATS = {
    "ar": {
        "digital": "نسخة رقمية",
        "softcover": "غلاف ورقي",
        "hardcover": "غلاف مقوّى",
        "spiral": "تجليد حلزوني",
    },
    "en": {
        "digital": "digital copy",
        "softcover": "softcover",
        "hardcover": "hardcover",
        "spiral": "spiral-bound",
    },
}


def money(amount: Decimal, currency: str) -> str:
    value = f"{amount:.2f}".rstrip("0").rstrip(".")
    return f"{value} ₪" if currency == "ILS" else f"{value} JD"


def base_values(values: dict[str, Any], lang: str) -> dict[str, Any]:
    b = brand()
    return {
        "brand": b.name_ar if lang == "ar" else b.name_en,
        "support_email": values.get("support_email") or "",
    }


def _item_label(item: OrderItem, lang: str) -> str:
    name = str(item.title.get("name_ar" if lang == "ar" else "name_en") or item.sku or "")
    fmt = FORMATS[lang].get(str(item.title.get("options", {}).get("format", "")))
    child = item.personalization.get("child_name")
    parts = [name, fmt, (f"كتاب {child}" if lang == "ar" else f"{child}'s book") if child else None]
    qty = f" × {item.quantity}" if item.quantity > 1 else ""
    return " · ".join(p for p in parts if p) + qty


def _recipient(db: Session, user_id: uuid.UUID | None) -> User | None:
    user = db.get(User, user_id) if user_id else None
    return user if user is not None and user.is_active else None


def order_email(
    db: Session, sender: EmailSender, order_id: str, event: str, base_url: str, values: dict[str, Any]
) -> str:
    if event not in ORDER_EVENTS:
        return "unknown_event"
    order = db.get(Order, uuid.UUID(order_id))
    if order is None:
        return "missing"
    note = claim(db, f"order:{order.id}:{event}", f"order_{event}", order_id=order.id, user_id=order.user_id)
    if note is None:
        return "duplicate"
    user = _recipient(db, order.user_id)
    if user is None or not values.get("email_notifications_enabled", True):
        finish(db, note, NotificationStatus.skipped, "no_recipient" if user is None else "disabled")
        return NotificationStatus.skipped.value
    lang = user.locale.value
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    rendered = render(
        f"order_{event}",
        lang,
        {
            **base_values(values, lang),
            "name": str(order.shipping.get("name") or user.full_name),
            "code": order.code,
            "total": money(order.total, order.currency.value),
            "track_url": f"{base_url}/{lang}/order/{order.code}",
        },
        [Item(_item_label(i, lang)) for i in items],
    )
    return deliver(db, sender, note, user.email, rendered).value


def book_email(
    db: Session, sender: EmailSender, book_id: str, event: str, base_url: str, values: dict[str, Any]
) -> str:
    if event not in BOOK_EVENTS:
        return "unknown_event"
    book = db.get(Book, uuid.UUID(book_id))
    if book is None or book.is_sample:
        return "missing"
    child = db.get(Child, book.child_id)
    owner = (
        child.guardian_user_id if child is not None and child.guardian_user_id else book.created_by_user_id
    )
    note = claim(db, f"book:{book.id}:{event}", event, book_id=book.id, user_id=owner)
    if note is None:
        return "duplicate"
    user = _recipient(db, owner)
    if user is None or child is None or not values.get("email_notifications_enabled", True):
        finish(db, note, NotificationStatus.skipped, "no_recipient" if user is None else "disabled")
        return NotificationStatus.skipped.value
    lang = user.locale.value
    rendered = render(
        event,
        lang,
        {
            **base_values(values, lang),
            "child": child.first_name,
            "title": book.title or child.first_name,
            "reader_url": f"{base_url}/{lang}/books/{book.id}",
            "create_url": f"{base_url}/{lang}/create?child={child.id}&book={book.id}",
        },
    )
    return deliver(db, sender, note, user.email, rendered).value


def review_alert(
    db: Session, sender: EmailSender, book_id: str, base_url: str, values: dict[str, Any]
) -> str:
    """Staff: a story's final files are ready and its words wait for review and «تأكيد». Once per book (a
    re-render after an edit does not repeat it), to `review_alert_email`; nothing when that is empty."""
    book = db.get(Book, uuid.UUID(book_id))
    if book is None or book.is_sample:
        return "missing"
    note = claim(db, f"book:{book.id}:text_review", "text_review_waiting", book_id=book.id)
    if note is None:
        return "duplicate"
    to = str(values.get("review_alert_email") or "").strip()
    if not to:
        finish(db, note, NotificationStatus.skipped, "no_review_email")
        return NotificationStatus.skipped.value
    lang = "ar"  # staff read Arabic; the admin opens in Arabic
    child = db.get(Child, book.child_id)
    rendered = render(
        "text_review_waiting",
        lang,
        {
            **base_values(values, lang),
            "title": book.title or (child.first_name if child else ""),
            "queue_url": f"{base_url}/{lang}/admin/queue",
        },
    )
    return deliver(db, sender, note, to, rendered).value


# ---- RQ entry points ------------------------------------------------------------------------------------


def sender_and_values(db: Session) -> tuple[EmailSender, dict[str, Any]]:
    values = dict(resolved_settings(db).values)
    return sender_from_settings(values, brand().name_ar), values


def send_order_email(order_id: str, event: str) -> str:
    context.init_process()
    with context.db_session() as db:
        sender, values = sender_and_values(db)
        return order_email(db, sender, order_id, event, get_settings().web_base_url.rstrip("/"), values)


def send_book_email(book_id: str, event: str) -> str:
    context.init_process()
    with context.db_session() as db:
        sender, values = sender_and_values(db)
        return book_email(db, sender, book_id, event, get_settings().web_base_url.rstrip("/"), values)


def send_review_alert(book_id: str) -> str:
    context.init_process()
    with context.db_session() as db:
        sender, values = sender_and_values(db)
        return review_alert(db, sender, book_id, get_settings().web_base_url.rstrip("/"), values)
