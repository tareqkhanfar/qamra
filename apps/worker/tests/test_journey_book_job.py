"""«رحلتي الأولى للتعلّم» for an order item: each ordered stage that is built becomes a Book with its interior,
cover, answer key and sticker sheet, the preflight of each file, and waits for an admin's print approval. The
page engine is tested in packages/workbook; here the render is a stand-in that writes small PDFs."""

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
from qamra_core.printing import INSERT_LABELS, item_inserts
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs import journey_book
from qamra_worker.jobs.print_batches import _items as printer_rows


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
        # the stage's sticker sheet, as `journey_order.render_order` adds it
        files.inserts = {"stickers": _pdf(out / "inserts" / "stickers.pdf")}
        files.dies = {"stickers": _pdf(out / "inserts" / "stickers-die.pdf")}
        files.preflight["inserts/stickers.pdf"] = {"passed": True, "die_ink": [0.04]}
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


async def test_the_stages_sticker_sheet_reaches_the_printer_with_the_book(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    """The sheet is stored beside the book's files (and its die beside it); the print batch's manifest
    lists it as an insert of every copy, the answer key only when the line bought it; the printer's email
    links it."""
    item = _item(db, storage)
    await journey_book.render_item(db, storage, item)
    db.refresh(item)
    book = db.get(Book, item.book_id)
    assert book is not None
    key = book.generation["files"]["stickers"]
    assert key == f"children/{book.child_id}/books/{book.id}/files/inserts/stickers.pdf"
    assert storage.exists(key) and storage.exists(key.replace("stickers.pdf", "stickers-die.pdf"))
    assert "stickers-die" not in str(book.generation["files"])  # the die is on the sheet's layer too
    assert book.preflight["inserts/stickers.pdf"]["passed"] and "preflight_failed" not in (book.flags or [])
    inserts = item_inserts(book.generation["files"], item.addons or [])
    assert inserts == {"stickers": key}  # included in every copy; the answer key is an add-on
    bought = item_inserts(book.generation["files"], [{"slug": "printed-answer-key"}])
    assert set(bought) == {"answer-key", "stickers"}
    line = {"n": 1, "order": "QM-1", "format": "spiral", "size": None, "copies": 1, "inserts": inserts}
    manifest = {"items": [line]}
    rows = printer_rows(manifest, "https://qamra.app/api/printer/T")
    sticker_rows = [r for r in rows if r.url and r.url.endswith("/files/1/inserts/stickers")]
    assert len(sticker_rows) == 1 and INSERT_LABELS["stickers"] in sticker_rows[0].label


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


@pytest.mark.parametrize("stage", [2, 3])
async def test_stages_two_and_three_render_through_the_order_job(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]], stage: int
) -> None:
    item = _item(db, storage, stage=str(stage))
    item.personalization = {**(item.personalization or {}), "name_en": "Adam"}
    db.commit()
    result = await journey_book.render_item(db, storage, item)
    assert result["status"] == "in_review" and [b["stage"] for b in result["books"]] == [stage]
    assert fake_render[0]["stage"] == stage and fake_render[0]["name_en"] == "Adam"
    book = db.get(Book, uuid.UUID(result["books"][0]["book_id"]))
    assert book is not None and book.generation["stage"] == stage and book.status == BookStatus.in_review
    assert stage in journey_book.built_stages()


class _Borrowed:
    """The test's session as the job's `with context.db_session() as db:` (the fixture closes it)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, *exc: object) -> bool:
        return False


@pytest.mark.parametrize(("variant", "stages"), [("1", [1]), ("2", [2]), ("3", [3]), ("set", [1, 2, 3])])
def test_the_order_entry_point_renders_each_stage_and_a_set_gets_all_three(
    db: Session,
    storage: ObjectStorage,
    fake_render: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
    stages: list[int],
) -> None:
    from qamra_worker import context

    item = _item(db, storage, stage=variant)
    monkeypatch.setattr(context, "init_process", lambda: None)
    monkeypatch.setattr(context, "db_session", lambda: _Borrowed(db))
    monkeypatch.setattr(context, "storage", lambda: storage)
    results = journey_book.render_order_journey_items(str(item.order_id))
    assert len(results) == 1 and results[0]["status"] == "in_review" and results[0]["skipped"] == []
    assert [b["stage"] for b in results[0]["books"]] == stages
    assert [c["stage"] for c in fake_render] == stages  # one render per stage, in order
    db.expire_all()
    for entry in results[0]["books"]:
        book = db.get(Book, uuid.UUID(entry["book_id"]))
        assert book is not None and book.status == BookStatus.in_review
        assert book.generation["stage"] == entry["stage"] and book.pdf_interior_key and book.pdf_cover_key
        assert storage.exists(book.generation["files"]["answer-key"])


def test_the_stage_comes_from_the_variant() -> None:
    item = OrderItem(title={"options": {"stage": "2"}}, personalization={})
    assert journey_book.stages_of(item) == [2]
    assert journey_book.stages_of(OrderItem(title={"options": {"stage": "set"}})) == [1, 2, 3]
    assert journey_book.stages_of(OrderItem(title={}, personalization={})) == [1]
    assert journey_book.built_stages() == [1, 2, 3]


@pytest.mark.parametrize(
    ("stage", "name_en", "flagged", "printed"),
    [
        ("2", "", True, "Adam"),
        ("2", " Adam ", False, "Adam"),
        ("3", "ضحى", True, "Adam"),
        ("1", "", False, None),
    ],
)
async def test_the_english_name_is_the_parents_and_a_guess_is_flagged(
    db: Session,
    storage: ObjectStorage,
    fake_render: list[dict[str, Any]],
    stage: str,
    name_en: str,
    flagged: bool,
    printed: str | None,
) -> None:
    """Stages 2 and 3 print the child's English name: the parent's spelling from the order, else a
    transliteration that the reviewer sees flagged (`name_en_guessed`). Stage 1 prints none."""
    item = _item(db, storage, stage=stage)
    item.personalization = {**(item.personalization or {}), "name_en": name_en}
    db.commit()
    result = await journey_book.render_item(db, storage, item)
    assert result["status"] == "in_review"
    assert fake_render[0]["name_en"] == ("Adam" if name_en.strip() == "Adam" else "")
    book = db.get(Book, uuid.UUID(result["books"][0]["book_id"]))
    assert book is not None and ("name_en_guessed" in (book.flags or [])) is flagged
    assert book.generation.get("name_en") == printed
    assert "name_not_traceable" not in (book.flags or [])
