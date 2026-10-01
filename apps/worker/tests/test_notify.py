"""Customer emails: templates in both languages, one email per order status and book stage (no duplicates),
guests and switched-off emails skipped, logged without SMTP, retried after an SMTP failure."""

import smtplib
import uuid
from collections.abc import Iterator
from decimal import Decimal
from typing import Any, ClassVar

import pytest
from fakeredis import FakeRedis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import Session

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
from qamra_worker.jobs.notify import BOOK_EVENTS, ORDER_EVENTS, book_email, order_email
from qamra_worker.notify import queue as notify_queue
from qamra_worker.notify.email import (
    EmailMessage,
    FakeEmailSender,
    LogEmailSender,
    SmtpEmailSender,
    sender_from_settings,
)
from qamra_worker.notify.templates import Item, messages, render

BASE = "https://qamra.test"
VALUES: dict[str, Any] = {"email_notifications_enabled": True, "support_email": "help@qamra.test"}


@pytest.fixture(autouse=True)
def _no_queue() -> Iterator[None]:
    yield
    notify_queue.set_connection(None)


def _parent(db: Session, email: str = "salma.mom@example.com", locale: Locale = Locale.ar) -> User:
    user = User(email=email, full_name="أم سلمى", password_hash="x", locale=locale)
    db.add(user)
    db.flush()
    return user


def _order(db: Session, user: User | None, code: str = "QM-MAIL01") -> Order:
    order = Order(
        code=code,
        user_id=user.id if user else None,
        status=OrderStatus.new,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("119"),
        total=Decimal("139"),
        delivery_fee=Decimal("20"),
        shipping={"name": "أم سلمى", "phone": "0591234567", "city": "البيرة", "address": "حي الجنان"},
        phone="0591234567",
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            sku="magic-hard-21",
            title={"name_ar": "قمرة سحري", "name_en": "Qamra Magic", "options": {"format": "hardcover"}},
            personalization={"child_name": "سلمى"},
            quantity=1,
            unit_price=Decimal("119"),
        )
    )
    db.commit()
    return order


def _book(db: Session, user: User, *, sample: bool = False) -> Book:
    child = Child(guardian_user_id=user.id, first_name="سلمى", gender=Gender.f, birth_year=2021)
    theme = Theme(
        slug=f"t-{uuid.uuid4().hex[:8]}",
        title_ar="يومي الأول",
        title_en="My first day",
        age_min=3,
        age_max=7,
        definition={},
    )
    db.add_all([child, theme])
    db.flush()
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=1,
        created_by_user_id=user.id,
        language=Locale.ar,
        art_style="watercolor",
        status=BookStatus.in_review,
        title="سلمى ويومها الأول",
        is_sample=sample,
    )
    db.add(book)
    db.commit()
    return book


def _notes(db: Session) -> list[Notification]:
    return list(db.scalars(select(Notification).order_by(Notification.created_at)).all())


def test_every_template_renders_in_both_languages() -> None:
    values = {
        "brand": "قمرة",
        "support_email": "help@qamra.test",
        "name": "<b>أم سلمى</b>",
        "code": "QM-ABC123",
        "total": "139 ₪",
        "child": "سلمى",
        "title": "سلمى ويومها الأول",
        "track_url": f"{BASE}/ar/order/QM-ABC123",
        "reader_url": f"{BASE}/ar/books/1",
        "create_url": f"{BASE}/ar/create?child=1&book=1",
        "manifest_url": f"{BASE}/api/printer/t/manifest.csv",
        "date": "2026-09-29",
        "books": 2,
        "copies": 3,
        "expires": "2026-10-13",
    }
    for template, langs in messages().items():
        assert set(langs) == {"ar", "en"}, template
        for lang in ("ar", "en"):
            out = render(template, lang, values, [Item("001 · QM-ABC123", f"{BASE}/x")])
            assert out.subject and "\n" not in out.subject and out.text.strip()
            assert f'dir="{"rtl" if lang == "ar" else "ltr"}"' in out.html
            assert "<b>أم سلمى</b>" not in out.html  # values are escaped in the HTML part
            assert "help@qamra.test" in out.text and f"{BASE}/x" in out.html
    assert "{{" not in render("order_placed", "ar", values).text


def test_the_printer_email_counts_in_good_english() -> None:
    values = {"brand": "قمرة", "code": "B1", "date": "2026-10-01", "expires": "2026-10-13"}
    values["manifest_url"] = BASE
    one = render("printer_batch", "en", {**values, "books": 1, "copies": 1})
    assert "1 book, 1 copy." in one.text and one.subject.endswith("— 1 copy")
    assert "2 books, 3 copies." in render("printer_batch", "en", {**values, "books": 2, "copies": 3}).text


def test_order_emails_go_once_per_status(db: Session) -> None:
    user = _parent(db)
    order = _order(db, user)
    sender = FakeEmailSender()
    for event in ORDER_EVENTS:
        assert order_email(db, sender, str(order.id), event, BASE, VALUES) == "sent"
    assert [m.to for m in sender.outbox] == ["salma.mom@example.com"] * len(ORDER_EVENTS)
    placed = sender.outbox[0]
    assert "QM-MAIL01" in placed.subject and "139 ₪" in placed.text
    assert f"{BASE}/ar/order/QM-MAIL01" in placed.text and "غلاف مقوّى" in placed.text
    # a retried or duplicated job never emails twice
    for event in ORDER_EVENTS:
        assert order_email(db, sender, str(order.id), event, BASE, VALUES) == "duplicate"
    assert len(sender.outbox) == len(ORDER_EVENTS)
    notes = _notes(db)
    assert {n.dedupe_key for n in notes} == {f"order:{order.id}:{e}" for e in ORDER_EVENTS}
    assert all(n.status == NotificationStatus.sent and n.sent_at and n.user_id == user.id for n in notes)
    assert order_email(db, sender, str(order.id), "generating", BASE, VALUES) == "unknown_event"


def test_english_accounts_get_english(db: Session) -> None:
    order = _order(db, _parent(db, "dad@example.com", Locale.en))
    sender = FakeEmailSender()
    order_email(db, sender, str(order.id), "shipped", BASE, VALUES)
    assert sender.outbox[0].subject == "Order QM-MAIL01 is on its way 🚚"
    assert f"{BASE}/en/order/QM-MAIL01" in sender.outbox[0].text and 'dir="ltr"' in sender.outbox[0].html


def test_guest_orders_and_switched_off_emails_are_skipped(db: Session) -> None:
    sender = FakeEmailSender()
    guest = _order(db, None, "QM-GUEST1")
    assert order_email(db, sender, str(guest.id), "placed", BASE, VALUES) == "skipped"
    off = _order(db, _parent(db), "QM-OFF001")
    assert (
        order_email(db, sender, str(off.id), "placed", BASE, {"email_notifications_enabled": False})
        == "skipped"
    )
    assert sender.outbox == []
    assert sorted(n.error or "" for n in _notes(db)) == ["disabled", "no_recipient"]
    assert order_email(db, sender, str(guest.id), "placed", BASE, VALUES) == "duplicate"


def test_without_smtp_the_message_is_only_logged(db: Session) -> None:
    sender = sender_from_settings({"smtp_host": "", "mail_from": "no-reply@example.com"}, "قمرة")
    assert isinstance(sender, LogEmailSender)
    order = _order(db, _parent(db))
    assert order_email(db, sender, str(order.id), "confirmed", BASE, VALUES) == "logged"
    assert _notes(db)[0].status == NotificationStatus.logged


def test_an_smtp_failure_is_retried_then_sent_once(db: Session) -> None:
    order = _order(db, _parent(db))
    broken = FakeEmailSender(fail=True)
    with pytest.raises(smtplib.SMTPServerDisconnected):
        order_email(db, broken, str(order.id), "confirmed", BASE, VALUES)
    note = _notes(db)[0]
    assert note.status == NotificationStatus.failed and note.error == "SMTPServerDisconnected"
    working = FakeEmailSender()
    assert order_email(db, working, str(order.id), "confirmed", BASE, VALUES) == "sent"
    assert order_email(db, working, str(order.id), "confirmed", BASE, VALUES) == "duplicate"
    db.refresh(note)
    assert len(working.outbox) == 1 and note.attempts == 2 and note.status == NotificationStatus.sent


def test_book_emails_link_to_the_preview_and_the_reader(db: Session) -> None:
    user = _parent(db)
    book = _book(db, user)
    sender = FakeEmailSender()
    for event in BOOK_EVENTS:
        assert book_email(db, sender, str(book.id), event, BASE, VALUES) == "sent"
        assert book_email(db, sender, str(book.id), event, BASE, VALUES) == "duplicate"
    preview, ready = sender.outbox
    assert (
        "سلمى" in preview.subject and f"{BASE}/ar/create?child={book.child_id}&book={book.id}" in preview.text
    )
    assert f"{BASE}/ar/books/{book.id}" in ready.text and "سلمى ويومها الأول" in ready.text
    sample = _book(db, _parent(db, "admin@example.com"), sample=True)
    assert book_email(db, sender, str(sample.id), "book_ready", BASE, VALUES) == "missing"  # admin samples


def test_a_ready_book_enqueues_its_email(db: Session) -> None:
    user = _parent(db)
    book, sample = _book(db, user), _book(db, _parent(db, "admin@example.com"), sample=True)
    redis = FakeRedis()
    notify_queue.book_ready(book, "final")  # outside a job and without a connection: nothing, no error
    notify_queue.set_connection(redis)
    notify_queue.book_ready(book, "preview")
    notify_queue.book_ready(book, "final")
    notify_queue.book_ready(sample, "final")
    jobs = Queue("default", connection=redis).jobs
    assert [(j.func_name, j.args) for j in jobs] == [
        ("qamra_worker.jobs.notify.send_book_email", (str(book.id), "preview_ready")),
        ("qamra_worker.jobs.notify.send_book_email", (str(book.id), "book_ready")),
    ]


class _FakeSMTP:
    calls: ClassVar[list[tuple[str, Any]]] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.calls.append(("connect", (host, port)))

    def __enter__(self) -> "_FakeSMTP":
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append(("quit", None))

    def starttls(self, context: object) -> None:
        self.calls.append(("starttls", None))

    def login(self, user: str, password: str) -> None:
        self.calls.append(("login", user))

    def send_message(self, msg: Any) -> None:
        self.calls.append(("send", msg))


def test_the_smtp_sender_uses_starttls_and_sends_text_and_html(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    values = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "mailer",
        "smtp_password": "secret",
        "smtp_security": "starttls",
        "mail_from": "hello@qamra.test",
        "mail_from_name": "",
    }
    sender = sender_from_settings(values, "قمرة")
    assert isinstance(sender, SmtpEmailSender) and sender.from_name == "قمرة"
    sender.send(EmailMessage(to="salma.mom@example.com", subject="مرحبًا", text="نص", html="<p>نص</p>"))
    kinds = [c[0] for c in _FakeSMTP.calls]
    assert kinds == ["connect", "starttls", "login", "send", "quit"]
    msg = _FakeSMTP.calls[3][1]
    assert msg["To"] == "salma.mom@example.com" and "hello@qamra.test" in msg["From"]
    assert [p.get_content_type() for p in msg.iter_parts()] == ["text/plain", "text/html"]
