"""«مغامراتي مع عائلتي» for an order item: the family comes from the order (or one neutral grown-up, never an
assumed mother and father), the print files are stored on a Book linked to the item, with preflight, and the
book waits for an admin's print approval. The page engine itself is tested in packages/workbook; here the
render is replaced by a stand-in that writes small PDFs, so the job's storage and database work is fast."""

import datetime as dt
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter
from qamra_workbook.render.family_order import OrderFiles
from sqlalchemy.orm import Session

from qamra_core.db.models import (
    Book,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Currency,
    Gender,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    User,
)
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs import family_book


def _pdf(path: Path, pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=810)
    with path.open("wb") as fh:
        writer.write(fh)
    return path


def _item(db: Session, storage: ObjectStorage, personalization: dict[str, Any] | None = None) -> OrderItem:
    parent = User(email=f"p-{uuid.uuid4().hex[:6]}@example.com", full_name="P")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="ليان", gender=Gender.f, birth_year=2021)
    db.add(child)
    db.flush()
    character = Character(
        child_id=child.id,
        art_style="watercolor",
        status=CharacterStatus.approved,
        sheet_image_key=f"children/{child.id}/characters/sheet.png",
        approved_at=dt.datetime(2026, 9, 28, tzinfo=dt.UTC),
    )
    db.add(character)
    storage.put(character.sheet_image_key or "", b"png", "image/png")
    order = Order(
        code=f"QM-F{uuid.uuid4().hex[:5].upper()}",
        user_id=parent.id,
        status=OrderStatus.confirmed,
        payment_method=PaymentMethod.cod,
        payment_status=PaymentStatus.unpaid,
        currency=Currency.ILS,
        subtotal=Decimal("89"),
        total=Decimal("89"),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        sku="family-book",
        line="family",
        child_id=child.id,
        title={"options": {"size": "a4"}},
        personalization={"character_id": str(character.id), **(personalization or {})},
        unit_price=Decimal("89"),
    )
    db.add(item)
    db.commit()
    return item


def test_the_family_comes_from_the_order_or_is_one_neutral_grown_up(
    db: Session, storage: ObjectStorage
) -> None:
    item = _item(
        db,
        storage,
        {"family": {"name": "الكيلاني", "city": "الخليل", "members": [{"role": "ستّي", "scarf": True}]}},
    )
    child = db.get(Child, item.child_id)
    assert child is not None
    family = family_book.family_of(item, child)
    assert family.name == "الكيلاني" and [m.role for m in family.members] == ["ستّي"]
    assert family.members[0].scarf and family.city == "الخليل"
    bare = _item(db, storage)
    lone = family_book.family_of(bare, child)
    assert lone.name == "ليان" and [m.label for m in lone.members] == [family_book.NEUTRAL_ADULT]
    assert "ماما" not in {m.label for m in lone.members} and "بابا" not in {m.label for m in lone.members}
    assert family_book.size_of(item) == "a4" and family_book.numerals_of(item) == "hindi"


async def test_the_job_stores_the_print_files_on_a_book_for_approval(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = _item(db, storage)
    seen: dict[str, Any] = {}

    async def fake_render(child: Any, family: Any, out: Path, **kw: Any) -> OrderFiles:
        seen.update(child=child, family=family, **kw)
        files = OrderFiles(interior=_pdf(out / "interior.pdf", 3), cover=_pdf(out / "cover.pdf", 2), pages=3)
        files.inserts = {"stickers": _pdf(out / "inserts/stickers.pdf")}
        files.dies = {"stickers": _pdf(out / "inserts/stickers-die.pdf")}
        files.preflight = {"interior.pdf": {"passed": True}, "cover.pdf": {"passed": True}}
        return files

    monkeypatch.setattr("qamra_workbook.render.family_order.render_order", fake_render)
    result = await family_book.render_item(db, storage, item)
    assert result["status"] == "in_review" and result["preflight"] is True
    db.refresh(item)
    book = db.get(Book, item.book_id)
    assert book is not None and book.status == BookStatus.in_review
    assert seen["child"].name == "ليان" and seen["child"].gender == "f" and seen["size"] == "a4"
    assert seen["child"].character_sheet is not None  # cut-outs come from the approved character's sheet
    assert book.pdf_interior_key and storage.exists(book.pdf_interior_key)
    assert book.pdf_cover_key and storage.exists(book.pdf_cover_key)
    assert storage.exists(book.generation["files"]["stickers"]) and book.generation["line"] == "family"
    assert book.preflight["interior.pdf"]["passed"] and book.cost_usd == 0
    # rendering again reuses the same book (a retried job never makes a second one)
    assert (await family_book.render_item(db, storage, item))["book_id"] == str(book.id)
