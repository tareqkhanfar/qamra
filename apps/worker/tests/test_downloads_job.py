"""Digital delivery, the worker's side: the home copies (made once, renewed after a re-render, a failure the
parent can retry) and the "ready to download" email (once per line, only when every book is ready, linking to
the account page and never to the file)."""

import io
import uuid
from decimal import Decimal
from typing import Any

from fakeredis import FakeRedis
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
from rq import Queue
from sqlalchemy.orm import Session

from qamra_core import downloads as dl
from qamra_core.db.models import (
    Book,
    BookStatus,
    Child,
    Currency,
    Gender,
    Locale,
    Notification,
    NotificationStatus,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Theme,
    User,
)
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs import downloads
from qamra_worker.notify.email import FakeEmailSender

MM = 72 / 25.4
BASE = "https://qamra.test"
VALUES: dict[str, Any] = {"email_notifications_enabled": True, "support_email": "help@qamra.test"}
PASSED = {"interior.pdf": {"passed": True}, "cover.pdf": {"passed": True}}


def print_pdf(pages: int, width_mm: float, height_mm: float, bleed_mm: float = 3.0) -> bytes:
    writer = PdfWriter()
    w, h, b = width_mm * MM, height_mm * MM, bleed_mm * MM
    for _ in range(pages):
        page = writer.add_blank_page(w, h)
        page.trimbox = RectangleObject([b, b, w - b, h - b])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _sizes(data: bytes) -> list[tuple[float, float]]:
    return [
        (round(float(p.cropbox.width) / MM, 1), round(float(p.cropbox.height) / MM, 1))
        for p in PdfReader(io.BytesIO(data)).pages
    ]


def _family(db: Session, locale: Locale = Locale.ar) -> tuple[User, Child, Theme]:
    user = User(
        email=f"p{uuid.uuid4().hex[:6]}@example.com", full_name="أم ضحى", password_hash="x", locale=locale
    )
    db.add(user)
    db.flush()
    child = Child(guardian_user_id=user.id, first_name="ضحى", gender=Gender.f, birth_year=2021)
    theme = Theme(
        slug=f"t-{uuid.uuid4().hex[:8]}", title_ar="ث", title_en="t", age_min=3, age_max=8, definition={}
    )
    db.add_all([child, theme])
    db.flush()
    return user, child, theme


def _line(db: Session, user: User, child: Child, options: dict[str, str], line: str = "islamic") -> OrderItem:
    order = Order(
        code=f"QM-W{uuid.uuid4().hex[:6].upper()}",
        user_id=user.id,
        status=OrderStatus.confirmed,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("35"),
        total=Decimal("35"),
        shipping={"name": "أم ضحى", "phone": "0591234567"},
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        sku="islamic-v1-digital",
        line=line,
        title={"name_ar": "قلبي يعرف الله", "name_en": "My Heart Knows Allah", "options": options},
        child_id=child.id,
        quantity=1,
        unit_price=Decimal("35"),
    )
    db.add(item)
    db.flush()
    return item


def _book(
    db: Session,
    storage: ObjectStorage,
    child: Child,
    theme: Theme,
    item: OrderItem,
    volume: str,
    status: BookStatus = BookStatus.in_review,
) -> Book:
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=1,
        language=Locale.ar,
        art_style="3d",
        status=status,
        title=f"قلبي يعرف الله — {volume} — ضحى",
        generation={"line": item.line, "order_item_id": str(item.id), "volume": volume},
        preflight=PASSED,
    )
    db.add(book)
    db.flush()
    base = f"children/{child.id}/books/{book.id}/files/"
    book.pdf_interior_key, book.pdf_cover_key = base + "interior.pdf", base + "cover.pdf"
    storage.put(book.pdf_interior_key, print_pdf(5, 216, 286), "application/pdf")
    storage.put(book.pdf_cover_key, print_pdf(2, 216, 286), "application/pdf")
    answers = base + "answer-key.pdf"
    storage.put(answers, print_pdf(2, 216, 286), "application/pdf")
    book.generation = {**book.generation, "files": {"answer-key": answers}}
    db.commit()
    return book


def test_a_home_copy_is_made_once_and_renewed_after_a_re_render(db: Session, storage: ObjectStorage) -> None:
    user, child, theme = _family(db)
    item = _line(db, user, child, {"volume": "V1", "format": "digital"})
    book = _book(db, storage, child, theme, item, "V1")

    key = downloads.make_copy(storage, book, "book")
    assert key.startswith(f"children/{child.id}/books/{book.id}/home/book/")
    copy = storage.get(key)
    assert _sizes(copy) == [(210.0, 280.0)] * 7  # front, five pages, back: all without the bleed
    assert downloads.make_copy(storage, book, "book") == key  # made once
    answers = downloads.make_copy(storage, book, "answer-key")
    assert _sizes(storage.get(answers)) == [(210.0, 280.0)] * 2

    assert book.pdf_interior_key
    storage.put(book.pdf_interior_key, print_pdf(6, 216, 286), "application/pdf")  # the admin's retry
    renewed = downloads.make_copy(storage, book, "book")
    assert renewed != key and not storage.exists(key)  # the old copy is gone
    assert len(_sizes(storage.get(renewed))) == 8
    assert storage.exists(answers)  # the other files' copies stay


def test_a_copy_that_cannot_be_made_is_marked_failed(db: Session, storage: ObjectStorage) -> None:
    user, child, theme = _family(db)
    item = _line(db, user, child, {"volume": "V1", "format": "digital"})
    book = _book(db, storage, child, theme, item, "V1")
    redis = FakeRedis()
    assert book.pdf_interior_key
    storage.put(book.pdf_interior_key, b"not a pdf", "application/pdf")
    version = downloads.copy_version(storage, book, "book")
    assert version is not None
    redis.set(dl.state_key(book.id, "book", version, "prep"), "1")
    assert downloads.prepare(db, storage, redis, str(book.id), "book") == "failed"
    assert redis.exists(dl.state_key(book.id, "book", version, "failed"))
    assert not redis.exists(dl.state_key(book.id, "book", version, "prep"))
    storage.put(book.pdf_interior_key, print_pdf(5, 216, 286), "application/pdf")
    version = downloads.copy_version(storage, book, "book")
    assert version is not None
    assert downloads.prepare(db, storage, redis, str(book.id), "book") == "ready"
    assert storage.exists(dl.home_key(book, "book", version))
    assert downloads.prepare(db, storage, redis, str(uuid.uuid4()), "book") == "missing"


def test_a_ready_line_is_emailed_once_with_the_account_link(db: Session, storage: ObjectStorage) -> None:
    user, child, theme = _family(db)
    item = _line(db, user, child, {"volume": "V2", "format": "digital"})
    sender = FakeEmailSender()
    assert downloads.ready_lines(db) == []  # nothing rendered yet
    assert downloads.deliver_email(db, storage, sender, str(item.id), BASE, VALUES) == "not_ready"

    book = _book(db, storage, child, theme, item, "V2")
    assert downloads.ready_lines(db) == [item.id]
    redis = FakeRedis()
    assert downloads.scan(db, redis) == {"ready": 1, "queued": 1}
    assert downloads.scan(db, redis) == {"ready": 1, "queued": 0}  # already on its way
    [job] = Queue("pdf", connection=redis).jobs
    assert (job.func_name, job.args) == ("qamra_worker.jobs.downloads.deliver_line", (str(item.id),))

    assert downloads.deliver_email(db, storage, sender, str(item.id), BASE, VALUES) == "sent"
    assert downloads.deliver_email(db, storage, sender, str(item.id), BASE, VALUES) == "duplicate"
    [mail] = sender.outbox
    assert mail.to == user.email and "قلبي يعرف الله · المجلد الثاني · ضحى" in mail.subject
    assert f"{BASE}/ar/account#downloads" in mail.text and "/api/" not in mail.text  # never the file itself
    assert storage.exists(dl.home_key(book, "book", downloads.copy_version(storage, book, "book") or ""))
    assert downloads.ready_lines(db) == []  # told
    [note] = db.query(Notification).filter(Notification.dedupe_key == f"download:{item.id}").all()
    assert note.status == NotificationStatus.sent and note.template == "download_ready"


def test_a_set_is_emailed_when_every_volume_is_ready(db: Session, storage: ObjectStorage) -> None:
    user, child, theme = _family(db, Locale.en)
    item = _line(db, user, child, {"volume": "L1", "format": "digital"})
    _book(db, storage, child, theme, item, "V1")
    held = _book(db, storage, child, theme, item, "V2")
    held.flags = ["scholar_review"]
    db.commit()
    assert downloads.ready_lines(db) == []
    held.flags = []
    held.status = BookStatus.approved
    db.commit()
    assert downloads.ready_lines(db) == [item.id]
    sender = FakeEmailSender()
    assert downloads.deliver_email(db, storage, sender, str(item.id), BASE, VALUES) == "sent"
    [mail] = sender.outbox
    assert mail.subject == "“My Heart Knows Allah · ضحى” is ready to download 📄"
    assert f"{BASE}/en/account#downloads" in mail.text


def test_printed_lines_are_not_emailed(db: Session, storage: ObjectStorage) -> None:
    user, child, theme = _family(db)
    item = _line(db, user, child, {"stage": "1", "format": "spiral"}, line="journey")
    book = _book(db, storage, child, theme, item, "")
    book.generation = {**book.generation, "stage": 1}
    db.commit()
    assert downloads.ready_lines(db) == []  # its free answer key is on the account page, without an email
