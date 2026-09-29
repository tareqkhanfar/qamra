"""The print files get the family-voice link only when an order bought the add-on for the book."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from qamra_core.db.models import (
    Book,
    Child,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    ShareScope,
    ShareToken,
    Theme,
)
from qamra_worker.voice import voice_url


def _book(db: Session) -> Book:
    child = Child(first_name="ليان", gender=Gender.f, birth_year=2021)
    theme = Theme(
        slug=f"t-{uuid.uuid4().hex[:8]}", title_ar="ت", title_en="T", age_min=3, age_max=7, definition={}
    )
    db.add_all([child, theme])
    db.flush()
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=1,
        language=Locale.ar,
        art_style="watercolor",
    )
    db.add(book)
    db.flush()
    return book


def _order(db: Session, book: Book, addons: list[dict[str, object]], status: OrderStatus) -> None:
    order = Order(
        code=f"QM-{uuid.uuid4().hex[:6].upper()}",
        status=status,
        payment_method=PaymentMethod.cod,
        currency=Currency.JOD,
        subtotal=Decimal("30"),
        total=Decimal("30"),
    )
    db.add(order)
    db.flush()
    db.add(OrderItem(order_id=order.id, book_id=book.id, addons=addons, quantity=1, unit_price=Decimal("27")))
    db.flush()


def test_only_the_add_on_prints_the_listening_link(db: Session) -> None:
    book = _book(db)
    assert voice_url(db, book, "qamra.app") is None  # not ordered yet
    _order(db, book, [{"slug": "gift-box", "qty": 1}], OrderStatus.confirmed)
    assert voice_url(db, book, "qamra.app") is None  # another add-on
    _order(db, book, [{"slug": "family-voice", "qty": 1}], OrderStatus.cancelled)
    assert voice_url(db, book, "qamra.app") is None  # a cancelled order doesn't count
    _order(db, book, [{"slug": "family-voice", "qty": 1, "unit_price": "3.00"}], OrderStatus.new)
    url = voice_url(db, book, "qamra.app")
    assert url is not None and url.startswith("https://qamra.app/v/") and len(url.rsplit("/", 1)[1]) == 20
    assert voice_url(db, book, "qamra.app") == url  # printed once, never changes
    tokens = db.execute(
        select(func.count()).select_from(ShareToken).where(ShareToken.scope == ShareScope.listen)
    ).scalar_one()
    assert tokens == 1
