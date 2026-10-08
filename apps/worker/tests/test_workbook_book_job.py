"""«دوسية التأسيس» for an order item (order flows §d chunk 10): each ordered volume becomes a Book with
its interior, cover and answer key, drawn for the child (name, gender, the approved character, the parent's
English spelling, digits ١٢٣), with every file's preflight, waiting for an admin's print approval. No AI is
called: the page engine draws everything. One test renders real pages with the sample character sheet; the
others use a stand-in that writes small PDFs."""

import datetime as dt
import functools
import io
import uuid
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pypdf import PdfReader, PdfWriter
from qamra_workbook.render import workbook as engine
from qamra_workbook.render.workbook import WorkbookFiles
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
from qamra_worker.jobs import family_book, workbook_book

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_SHEET = ROOT / "content/workbook/samples/sample-character.png"  # AI-drawn sample, not a real child


def _pdf(path: Path, pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=859)
    with path.open("wb") as fh:
        writer.write(fh)
    return path


def _item(
    db: Session,
    storage: ObjectStorage,
    *,
    level: str = "kg2",
    volume: str = "1",
    interior: str = "color",
    name: str = "رؤى",
    personalization: dict[str, Any] | None = None,
    sheet: bytes = b"png",
) -> OrderItem:
    parent = User(email=f"p-{uuid.uuid4().hex[:6]}@example.com", full_name="P")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name=name, gender=Gender.f, birth_year=2021)
    db.add(child)
    db.flush()
    character = Character(
        child_id=child.id,
        art_style="3d",
        status=CharacterStatus.approved,
        sheet_image_key=f"children/{child.id}/characters/sheet.png",
        approved_at=dt.datetime(2026, 10, 7, tzinfo=dt.UTC),
    )
    db.add(character)
    storage.put(character.sheet_image_key or "", sheet, "image/png")
    order = Order(
        code=f"QM-W{uuid.uuid4().hex[:5].upper()}",
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
    tag = "set" if volume == "set" else f"v{volume}"
    item = OrderItem(
        order_id=order.id,
        sku=f"wb-{level}-{tag}-{interior}-spiral",
        line="workbook",
        child_id=child.id,
        title={
            "name_ar": "دوسية التأسيس",
            "options": {"level": level, "volume": volume, "interior": interior, "format": "spiral"},
        },
        personalization={"character_id": str(character.id), **(personalization or {})},
        unit_price=Decimal("69"),
    )
    db.add(item)
    db.commit()
    return item


@pytest.fixture
def fake_render(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def render(child: Any, level: str, volume: int, out: Path, **kw: Any) -> WorkbookFiles:
        calls.append({"child": child, "level": level, "volume": volume, **kw})
        files = WorkbookFiles(
            _pdf(out / "interior.pdf", 3),
            _pdf(out / "cover.pdf", 2),
            _pdf(out / "answer-key.pdf"),
            pages=128,
            name_en=kw.get("name_en") or "Rua",
            name_en_guessed=not kw.get("name_en"),
            name_traceable=True,
        )
        files.preflight = {"interior.pdf": {"passed": True}, "cover.pdf": {"passed": True}}
        return files

    monkeypatch.setattr("qamra_workbook.render.workbook.render_order", render)
    return calls


async def test_a_foundation_order_renders_a_volume_for_the_child(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real page engine (no AI): the first pages of KG2 volume 1 and the cover, for «رؤى» with the sample
    character sheet and the parent's English spelling."""
    seen: dict[str, str] = {}
    real = engine.render_order

    async def first_pages(child: Any, level: str, volume: int, out: Path, **kw: Any) -> WorkbookFiles:
        specs = functools.partial(engine.volume_specs, pages=range(1, 5))  # owner, اسمي, My name, contents
        monkeypatch.setattr(engine, "volume_specs", specs)
        files = await real(child, level, volume, out, **kw)
        seen["interior"] = (out / "interior.html").read_text("utf-8")
        seen["cover"] = (out / "cover.html").read_text("utf-8")
        return files

    monkeypatch.setattr("qamra_workbook.render.workbook.render_order", first_pages)
    item = _item(db, storage, personalization={"name_en": "Roua"}, sheet=SAMPLE_SHEET.read_bytes())
    result = await workbook_book.render_item(db, storage, item)
    assert result["status"] == "in_review" and result["preflight"] is True, result
    db.refresh(item)
    book = db.get(Book, item.book_id)
    assert book is not None and book.status == BookStatus.in_review and book.cost_usd == 0
    assert book.title == "دوسية رؤى — KG2 — الجزء الأول"
    gen = book.generation
    assert (gen["line"], gen["level"], gen["volume"], gen["name_en"]) == ("workbook", "kg2", 1, "Roua")
    assert book.pdf_interior_key and book.pdf_cover_key
    assert len(PdfReader(io.BytesIO(storage.get(book.pdf_interior_key))).pages) == 4
    assert len(PdfReader(io.BytesIO(storage.get(book.pdf_cover_key))).pages) == 2  # front and back
    assert book.preflight["interior.pdf"]["passed"] and book.preflight["cover.pdf"]["passed"]
    assert not {"preflight_failed", "name_en_guessed", "name_not_traceable"} & set(book.flags or [])
    # the child's name on the owner page and the tracing page, the character cut out of the sheet
    assert "رؤى" in seen["interior"] and "character-" in seen["interior"]
    assert "دوسية رؤى" in seen["cover"] and "KG2" in seen["cover"] and "character-" in seen["cover"]
    assert "١" in seen["interior"]  # the page numbers in ١٢٣


async def test_a_volume_becomes_a_book_waiting_for_print_approval(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    item = _item(db, storage, level="kg1", volume="2", personalization={"name_en": " Roua "})
    result = await workbook_book.render_item(db, storage, item)
    assert result["status"] == "in_review" and [b["volume"] for b in result["books"]] == [2]
    call = fake_render[0]
    assert (call["level"], call["volume"], call["interior"]) == ("kg1", 2, "color")
    assert call["name_en"] == "Roua" and call["numerals"] == "hindi" and call["domain"]  # ١٢٣ by default
    assert call["child"].name == "رؤى" and call["child"].gender == "f" and call["child"].character_sheet
    db.refresh(item)
    book = db.get(Book, item.book_id)
    assert book is not None and book.status == BookStatus.in_review
    assert storage.exists(book.generation["files"]["answer-key"]) and book.pdf_cover_key
    again = await workbook_book.render_item(db, storage, item)  # a retried job reuses the same book
    assert again["books"][0]["book_id"] == str(book.id)


async def test_a_set_renders_all_three_volumes(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    item = _item(db, storage, volume="set", personalization={"name_en": "Roua"})
    result = await workbook_book.render_item(db, storage, item)
    assert [b["volume"] for b in result["books"]] == [1, 2, 3] and [c["volume"] for c in fake_render] == [
        1,
        2,
        3,
    ]
    ids = {b["book_id"] for b in result["books"]}
    assert len(ids) == 3
    for book_id in ids:
        book = db.get(Book, uuid.UUID(book_id))
        assert book is not None and book.status == BookStatus.in_review and book.generation["level"] == "kg2"


async def test_without_an_english_spelling_the_book_is_flagged_for_the_reviewer(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    item = _item(db, storage)
    await workbook_book.render_item(db, storage, item)
    assert fake_render[0]["name_en"] == ""
    db.refresh(item)
    book = db.get(Book, item.book_id)
    assert book is not None and "name_en_guessed" in book.flags and book.status == BookStatus.in_review


async def test_black_and_white_is_refused_with_a_clear_reason(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    item = _item(db, storage, volume="set", interior="bw")
    result = await workbook_book.render_item(db, storage, item)
    assert result["status"] == "refused" and "black-and-white" in result["reason"] and fake_render == []
    assert len(result["books"]) == 3
    for book_id in result["books"]:
        book = db.get(Book, uuid.UUID(book_id))
        assert (
            book is not None and book.status == BookStatus.failed and "black-and-white" in (book.error or "")
        )


async def test_other_lines_and_incomplete_items_are_not_rendered(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]]
) -> None:
    other = _item(db, storage)
    other.line = "journey"
    assert (await workbook_book.render_item(db, storage, other))["status"] == "skipped"
    broken = _item(db, storage, level="kg3")
    assert (await workbook_book.render_item(db, storage, broken))["status"] == "failed"
    assert fake_render == []


class _Borrowed:
    """The test's session as the job's `with context.db_session() as db:` (the fixture closes it)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, *exc: object) -> bool:
        return False


def test_the_order_entry_point_renders_each_workbook_item(
    db: Session, storage: ObjectStorage, fake_render: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from qamra_worker import context

    item = _item(db, storage, volume="3", personalization={"name_en": "Roua"})
    monkeypatch.setattr(context, "init_process", lambda: None)
    monkeypatch.setattr(context, "db_session", lambda: _Borrowed(db))
    monkeypatch.setattr(context, "storage", lambda: storage)
    results = workbook_book.render_order_workbook_items(str(item.order_id))
    assert len(results) == 1 and results[0]["status"] == "in_review"
    assert [c["volume"] for c in fake_render] == [3]


def test_the_variant_comes_from_the_item() -> None:
    item = OrderItem(
        title={"options": {"level": "KG1", "volume": "set", "interior": "bw"}}, personalization={}
    )
    assert workbook_book.level_of(item) == "kg1" and workbook_book.volumes_of(item) == [1, 2, 3]
    assert workbook_book.interior_of(item) == "bw"
    assert workbook_book.volumes_of(OrderItem(title={"options": {"volume": "4"}})) == []
    assert workbook_book.interior_of(OrderItem(title={})) == "color"


def test_the_english_spelling_comes_from_the_item_then_the_child() -> None:
    item = OrderItem(personalization={"name_en": "  Duha "})
    child = SimpleNamespace(name_latin="Doha")
    assert family_book.name_en_of(item, child) == "Duha"  # type: ignore[arg-type]
    assert family_book.name_en_of(OrderItem(personalization={}), child) == "Doha"  # type: ignore[arg-type]
    bad = OrderItem(personalization={"name_en": "ضحى"})
    assert family_book.name_en_of(bad, SimpleNamespace()) == ""  # type: ignore[arg-type]
    flags = family_book.name_flags(["preflight_failed", "name_en_guessed"], guessed=False, traceable=False)
    assert flags == ["preflight_failed", "name_not_traceable"]


def test_a_coloring_character_is_used_only_when_there_is_no_other(
    db: Session, storage: ObjectStorage
) -> None:
    item = _item(db, storage)
    item.personalization = {}
    child = db.get(Child, item.child_id)
    assert child is not None
    coloring = Character(
        child_id=child.id,
        art_style="coloring",
        status=CharacterStatus.approved,
        sheet_image_key="x.png",
        approved_at=dt.datetime(2026, 10, 8, tzinfo=dt.UTC),  # newer than the 3D one
    )
    db.add(coloring)
    db.commit()
    chosen = family_book.approved_character(db, item, child)
    assert chosen is not None and chosen.art_style == "3d"
