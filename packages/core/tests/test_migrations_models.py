from datetime import UTC, datetime, timedelta
from decimal import Decimal

from alembic import command
from qamra_core.db.models import (
    Book,
    BookPage,
    Character,
    Child,
    ChildPhoto,
    Companion,
    CompanionType,
    Consent,
    Currency,
    Gender,
    GenerationCost,
    Locale,
    Order,
    OrderItem,
    PaymentMethod,
    Product,
    Recording,
    ShareScope,
    ShareToken,
    Theme,
    User,
)
from qamra_core.migrations import alembic_config
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_models_match_migrations(migrated: str) -> None:
    command.check(alembic_config(migrated))  # raises if autogenerate would produce operations


def _family(db: Session) -> tuple[User, Child, Book]:
    parent = User(email="p@example.com", full_name="P", password_hash="x")
    db.add(parent)
    db.flush()
    child = Child(
        guardian_user_id=parent.id, first_name="سلمى", gender=Gender.f, birth_year=2021, interests=["الرسم"]
    )
    theme = Theme(slug="t", title_ar="ت", title_en="T", age_min=3, age_max=7, definition={"pages": []})
    db.add_all([child, theme])
    db.flush()
    character = Character(child_id=child.id, art_style="watercolor")
    db.add(character)
    db.flush()
    book = Book(
        child_id=child.id,
        character_id=character.id,
        theme_id=theme.id,
        theme_version=1,
        language=Locale.ar,
        art_style="watercolor",
    )
    db.add(book)
    db.flush()
    companion = Companion(child_id=child.id, book_id=book.id, name="بوبو", type_hint=CompanionType.creature)
    token = ShareToken(book_id=book.id, token="tok-" + str(book.id)[:8], scope=ShareScope.listen)
    db.add_all(
        [
            Consent(child_id=child.id, guardian_user_id=parent.id, consent_text_version="2026-09"),
            ChildPhoto(
                child_id=child.id,
                storage_key=f"children/{child.id}/photos/1.jpg",
                delete_after=datetime.now(UTC) + timedelta(hours=24),
            ),
            BookPage(book_id=book.id, index=1, text="نص"),
            companion,
            token,
        ]
    )
    db.flush()
    db.add(
        Recording(
            book_id=book.id,
            page_index=1,
            voice_label="ستّي",
            storage_key="k",
            duration_ms=4200,
            created_by_share_token_id=token.id,
        )
    )
    db.flush()
    return parent, child, book


def test_deleting_a_child_removes_all_child_data_but_keeps_orders(db: Session) -> None:
    parent, child, book = _family(db)
    order = Order(
        code="QM-000001",
        user_id=parent.id,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("120"),
        total=Decimal("135"),
    )
    db.add(order)
    db.flush()
    db.add_all(
        [
            OrderItem(
                order_id=order.id, book_id=book.id, product=Product.hardcover, unit_price=Decimal("120")
            ),
            GenerationCost(
                book_id=book.id,
                child_id=child.id,
                step="page:1",
                provider="gemini",
                model="m",
                usd=Decimal("0.101"),
            ),
        ]
    )
    db.commit()

    db.delete(child)
    db.commit()
    db.expire_all()

    for model in (ChildPhoto, Consent, Character, Companion, Book, BookPage, ShareToken, Recording):
        assert db.scalar(select(func.count()).select_from(model)) == 0, model.__name__
    item = db.scalars(select(OrderItem)).one()
    cost = db.scalars(select(GenerationCost)).one()
    assert item.book_id is None and cost.book_id is None and cost.child_id is None
    assert db.get(Order, order.id) is not None


def test_deleting_a_parent_removes_their_children(db: Session) -> None:
    parent, _, _ = _family(db)
    db.commit()
    db.delete(parent)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Child)) == 0
