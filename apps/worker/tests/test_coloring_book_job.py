"""«دفاتر التلوين والرسم» for an order item (2026-10-21).

One personalized copy becomes a Book with its interior and cover, drawn for the child (name, gender, and the
character only when the line carries one), with every file's preflight, waiting for an admin's print
approval. No AI is called; the page engine is a stand-in that writes small PDFs (the real one is tested in
packages/workbook)."""

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
from qamra_worker.jobs import coloring_book


def _pdf(path: Path, pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    with path.open("wb") as fh:
        writer.write(fh)
    return path


def _item(
    db: Session,
    storage: ObjectStorage,
    *,
    sku: str = "coloring-letters-print",
    fmt: str = "softcover",
    with_character: bool = True,
    approved: bool = True,
) -> OrderItem:
    parent = User(email=f"p-{uuid.uuid4().hex[:6]}@example.com", full_name="P")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="سلمى", gender=Gender.f, birth_year=2021)
    db.add(child)
    db.flush()
    character = Character(
        child_id=child.id,
        art_style="3d",
        status=CharacterStatus.approved if approved else CharacterStatus.ready,
        sheet_image_key=f"children/{child.id}/characters/sheet.png",
        approved_at=dt.datetime(2026, 10, 20, tzinfo=dt.UTC) if approved else None,
    )
    db.add(character)
    db.flush()
    storage.put(character.sheet_image_key or "", b"png", "image/png")
    order = Order(
        code=f"QM-C{uuid.uuid4().hex[:5].upper()}",
        user_id=parent.id,
        status=OrderStatus.confirmed,
        payment_method=PaymentMethod.cod,
        payment_status=PaymentStatus.unpaid,
        currency=Currency.ILS,
        subtotal=Decimal("35"),
        total=Decimal("35"),
    )
    db.add(order)
    db.flush()
    personalization: dict[str, Any] = {"child_name": "سلمى", "gender": "f", "cover_character": with_character}
    if with_character:
        personalization["character_id"] = str(character.id)
    item = OrderItem(
        order_id=order.id,
        sku=sku,
        line="colorbook",
        child_id=child.id,
        title={"name_ar": "ألوّن حروفي", "options": {"format": fmt}},
        personalization=personalization,
        unit_price=Decimal("35"),
    )
    db.add(item)
    db.commit()
    return item


@pytest.fixture
def fake_render(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def render(child: Any, title: str, out: Path, **kw: Any) -> OrderFiles:
        calls.append({"child": child, "title": title, "sheet": child.character_sheet, **kw})
        files = OrderFiles(_pdf(out / "interior.pdf", 4), _pdf(out / "cover.pdf", 2), pages=32)
        files.preflight = {"interior.pdf": {"passed": True}, "cover.pdf": {"passed": True}}
        return files

    monkeypatch.setattr("qamra_workbook.render.coloring_order.render_order", render)
    return calls


async def test_a_coloring_book_with_the_character_waits_for_print_approval(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    item = _item(db, storage)
    result = await coloring_book.render_item(db, storage, item)
    assert result["status"] == "in_review" and result["cover_character"] is True
    [call] = fake_render
    assert call["title"] == "coloring-letters"
    assert call["child"].name == "سلمى" and call["child"].gender == "f"
    assert call["sheet"] is not None and call["sheet"].name == "character-sheet.png"
    assert call["imprint"].part == "ألوّن حروفي"
    book = db.get(Book, uuid.UUID(result["book_id"]))
    assert book is not None and book.status == BookStatus.in_review
    assert book.character_id is not None and book.art_style == "3d"
    assert book.generation["line"] == "colorbook" and book.generation["title"] == "letters"
    assert book.generation["cover_character"] is True and book.generation["pages"] == 32
    assert storage.exists(book.pdf_interior_key or "") and storage.exists(book.pdf_cover_key or "")
    assert item.book_id == book.id  # the print batch finds the book through the line
    again = await coloring_book.render_item(db, storage, item)  # a retried job reuses the same book
    assert again["book_id"] == result["book_id"]


async def test_a_cover_without_the_character_never_uses_the_childs_drawing(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    """The child has an approved character, but the parent chose a cover without it."""
    item = _item(db, storage, sku="sketchbook-print", fmt="spiral", with_character=False)
    result = await coloring_book.render_item(db, storage, item)
    assert result["status"] == "in_review" and result["cover_character"] is False
    assert fake_render[0]["sheet"] is None and fake_render[0]["title"] == "sketchbook"
    book = db.get(Book, uuid.UUID(result["book_id"]))
    assert book is not None and book.character_id is None and book.art_style == ""
    assert book.generation["cover_character"] is False and "character_missing" not in (book.flags or [])


async def test_a_character_that_cant_be_used_is_flagged_and_left_off(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    item = _item(db, storage, sku="coloring-ramadan-pdf", fmt="digital", approved=False)
    result = await coloring_book.render_item(db, storage, item)
    assert result["cover_character"] is False and "character_missing" in result["flags"]
    assert fake_render[0]["sheet"] is None and fake_render[0]["title"] == "coloring-ramadan"


async def test_a_failed_preflight_is_flagged(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def render(child: Any, title: str, out: Path, **kw: Any) -> OrderFiles:
        files = OrderFiles(
            _pdf(out / "interior.pdf"), _pdf(out / "cover.pdf"), pages=28, cutout_fallback=True
        )
        files.preflight = {"interior.pdf": {"passed": False}, "cover.pdf": {"passed": True}}
        return files

    monkeypatch.setattr("qamra_workbook.render.coloring_order.render_order", render)
    item = _item(db, storage, sku="coloring-palestine-print")
    result = await coloring_book.render_item(db, storage, item)
    assert result["preflight"] is False
    assert {"preflight_failed", "cutout_fallback"} <= set(result["flags"])


async def test_other_lines_and_incomplete_items_are_not_rendered(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    other = _item(db, storage)
    other.line = "journey"
    assert (await coloring_book.render_item(db, storage, other))["status"] == "skipped"
    unknown = _item(db, storage, sku="coloring-unknown-print")
    assert (await coloring_book.render_item(db, storage, unknown))["status"] == "failed"
    assert fake_render == []


class _Borrowed:
    """The test's session as the job's `with context.db_session() as db:` (the fixture closes it)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, *exc: object) -> bool:
        return False


def test_the_order_entry_point_renders_each_coloring_item(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from qamra_worker import context

    item = _item(db, storage, sku="coloring-palestine-print")
    monkeypatch.setattr(context, "init_process", lambda: None)
    monkeypatch.setattr(context, "db_session", lambda: _Borrowed(db))
    monkeypatch.setattr(context, "storage", lambda: storage)
    results = coloring_book.render_order_coloring_items(str(item.order_id))
    assert len(results) == 1 and results[0]["status"] == "in_review"
    assert [c["title"] for c in fake_render] == ["coloring-palestine"]


def test_the_cover_character_comes_only_from_the_line() -> None:
    child = Child(id=uuid.uuid4(), first_name="سلمى", gender=Gender.f, birth_year=2021)

    class NoDb:
        def get(self, *_: object) -> None:
            raise AssertionError("no character is looked up for a plain cover")

    plain = OrderItem(personalization={"cover_character": False, "character_id": str(uuid.uuid4())})
    assert coloring_book.cover_character(NoDb(), plain, child) == (None, False)  # type: ignore[arg-type]
    older = OrderItem(personalization={})  # no character named: none (never the child's newest)
    assert coloring_book.cover_character(NoDb(), older, child) == (None, False)  # type: ignore[arg-type]
