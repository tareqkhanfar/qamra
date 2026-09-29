"""«رحلتي الأولى للتعلّم» for an order item: each ordered stage that is built becomes a Book with its interior,
cover and answer key, the preflight of each file, and waits for an admin's print approval. The page engine is
tested in packages/workbook; here the render is a stand-in that writes small PDFs."""

import datetime as dt
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter
from qamra_workbook.render.journey_order import OrderFiles
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
from qamra_worker.jobs import journey_book


def _pdf(path: Path, pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=859)
    with path.open("wb") as fh:
        writer.write(fh)
    return path


def _item(db: Session, storage: ObjectStorage, stage: str = "1", line: str = "journey") -> OrderItem:
    parent = User(email=f"p-{uuid.uuid4().hex[:6]}@example.com", full_name="P")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="آدم", gender=Gender.m, birth_year=2022)
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
        code=f"QM-J{uuid.uuid4().hex[:5].upper()}",
        user_id=parent.id,
        status=OrderStatus.confirmed,
        payment_method=PaymentMethod.cod,
        payment_status=PaymentStatus.unpaid,
        currency=Currency.ILS,
        subtotal=Decimal("69"),
        total=Decimal("69"),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        sku=f"journey-s{stage}-spiral",
        line=line,
        child_id=child.id,
        title={"options": {"stage": stage, "format": "spiral"}},
        personalization={"character_id": str(character.id), "numerals": "latin"},
        unit_price=Decimal("69"),
    )
    db.add(item)
    db.commit()
    return item


@pytest.fixture
def fake_render(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def render(child: Any, stage: int, out: Path, **kw: Any) -> OrderFiles:
        calls.append({"child": child, "stage": stage, **kw})
        files = OrderFiles(
            _pdf(out / "interior.pdf", 3), _pdf(out / "cover.pdf", 2), _pdf(out / "answer-key.pdf")
        )
        files.pages = 118
        files.preflight = {"interior.pdf": {"passed": True}, "cover.pdf": {"passed": True}}
        return files

    monkeypatch.setattr("qamra_workbook.render.journey_order.render_order", render)
    return calls


async def test_a_stage_becomes_a_book_waiting_for_print_approval(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    item = _item(db, storage)
    result = await journey_book.render_item(db, storage, item)
    assert result["status"] == "in_review" and result["preflight"] is True
    call = fake_render[0]
    assert (
        call["stage"] == 1 and call["numerals"] == "latin" and call["domain"]
    )  # QR links on the brand domain
    assert call["child"].name == "آدم" and call["child"].gender == "m" and call["child"].character_sheet
    db.refresh(item)
    book = db.get(Book, item.book_id)
    assert book is not None and book.status == BookStatus.in_review
    assert book.generation["line"] == "journey" and book.generation["stage"] == 1
    assert book.pdf_interior_key and storage.exists(book.pdf_interior_key)
    assert book.pdf_cover_key and storage.exists(book.pdf_cover_key)
    assert storage.exists(book.generation["files"]["answer-key"]) and book.cost_usd == 0
    assert book.preflight["interior.pdf"]["passed"] and "preflight_failed" not in (book.flags or [])
    again = await journey_book.render_item(db, storage, item)  # a retried job reuses the same book
    assert again["books"][0]["book_id"] == str(book.id)


async def test_a_set_renders_the_built_stages_and_skips_the_rest(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(journey_book, "built_stages", lambda: [1])
    item = _item(db, storage, stage="set")
    result = await journey_book.render_item(db, storage, item)
    assert [b["stage"] for b in result["books"]] == [1] and result["skipped"] == [2, 3]
    later = _item(db, storage, stage="3")
    assert (await journey_book.render_item(db, storage, later))["status"] == "skipped"
    other = _item(db, storage, line="family")
    assert (await journey_book.render_item(db, storage, other))["status"] == "skipped"
    assert len(fake_render) == 1


def test_the_stage_comes_from_the_variant() -> None:
    item = OrderItem(title={"options": {"stage": "2"}}, personalization={})
    assert journey_book.stages_of(item) == [2]
    assert journey_book.stages_of(OrderItem(title={"options": {"stage": "set"}})) == [1, 2, 3]
    assert journey_book.stages_of(OrderItem(title={}, personalization={})) == [1]
    assert 1 in journey_book.built_stages()
