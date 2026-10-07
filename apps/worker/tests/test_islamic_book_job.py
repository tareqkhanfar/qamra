"""«قلبي يعرف الله» for an order item: a volume the scholar approved becomes a Book with its interior, cover
and parents' file, waiting for an admin's print approval; a volume the scholar has not approved is never
rendered (P0). The review previews are one PNG per page. The page engine is tested in packages/workbook; here
`render_volume` is a stand-in that writes small PDFs and records what it was given."""

import datetime as dt
import json
import os
import sys
import types
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter
from sqlalchemy import delete
from sqlalchemy.orm import Session

from qamra_core.db.islamic import IslamicReviewEvent, IslamicReviewPreview, IslamicUnitReview, ReviewStatus
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
from qamra_core.islamic_review import EXPORT_ENV, content_units
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs import islamic_book


def _pdf(path: Path, pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=170, height=226)
    with path.open("wb") as fh:
        writer.write(fh)
    return path


@dataclass
class VolumeFiles:  # the engine's `islamic_volume.VolumeFiles`
    interior: Path
    cover: Path
    answer_key: Path | None = None
    pages: int = 0
    preflight: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(r.get("passed") for r in self.preflight.values())


@pytest.fixture(autouse=True)
def _before_the_owner_decision(db: Session) -> None:
    """Start from a review with nothing decided: migration 0c695b89fde0 (the owner's decision of 2026-10-07)
    approves every unit; its rows are removed inside the test's rolled-back transaction."""
    db.execute(delete(IslamicReviewEvent))
    db.execute(delete(IslamicUnitReview))
    db.flush()


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def render_volume(volume: str, child: Any, out: Path, **kw: Any) -> VolumeFiles:
        review = json.loads(Path(os.environ[EXPORT_ENV]).read_text(encoding="utf-8"))  # what the engine reads
        calls.append({"volume": volume, "child": child, "review": review, **kw})
        files = VolumeFiles(
            _pdf(out / "interior.pdf", 3), _pdf(out / "cover.pdf"), _pdf(out / "answer-key.pdf")
        )
        files.pages = 3
        files.preflight = {"interior.pdf": {"passed": True}, "cover.pdf": {"passed": True}}
        return files

    module = types.ModuleType("qamra_workbook.render.islamic_volume")
    module.render_volume = render_volume  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "qamra_workbook.render.islamic_volume", module)
    return calls


def _approve(db: Session, volume: str, *, but: tuple[str, ...] = ()) -> None:
    for u in content_units():
        if u.volume == volume and u.id not in but:
            db.merge(
                IslamicUnitReview(
                    unit_id=u.id,
                    volume=volume,
                    status=ReviewStatus.approved,
                    reviewer_name="الشيخ أحمد",
                    approved_at=dt.datetime(2026, 10, 3, tzinfo=dt.UTC),
                )
            )
    db.commit()


def _item(db: Session, storage: ObjectStorage, volume: str = "R", fmt: str = "softcover") -> OrderItem:
    parent = User(email=f"p-{uuid.uuid4().hex[:6]}@example.com", full_name="P")
    db.add(parent)
    db.flush()
    child = Child(
        guardian_user_id=parent.id, first_name="مريم", gender=Gender.f, birth_year=2021, wears_hijab=True
    )
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
        code=f"QM-I{uuid.uuid4().hex[:6].upper()}",
        user_id=parent.id,
        status=OrderStatus.confirmed,
        payment_method=PaymentMethod.cod,
        payment_status=PaymentStatus.unpaid,
        currency=Currency.ILS,
        subtotal=Decimal("79"),
        total=Decimal("79"),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        sku=f"islamic-{volume.lower()}-{fmt}",
        line="islamic",
        child_id=child.id,
        title={"options": {"volume": volume, "format": fmt}},
        personalization={"character_id": str(character.id), "numerals": "latin"},
        unit_price=Decimal("79"),
    )
    db.add(item)
    db.commit()
    return item


async def test_an_approved_volume_becomes_a_book_waiting_for_print_approval(
    db: Session, storage: ObjectStorage, engine: list[dict[str, Any]]
) -> None:
    _approve(db, "R")
    item = _item(db, storage)
    result = await islamic_book.render_item(db, storage, item)
    assert result["status"] == "in_review" and result["preflight"] is True and result["held"] == []
    call = engine[0]
    assert call["volume"] == "R" and call["print_build"] is True and call["numerals"] == "latin"
    assert call["size"] == "21x28" and call["child"].name == "مريم" and call["child"].gender == "f"
    assert call["child"].character_sheet  # the child's approved character, no new AI cost
    assert call["review"]["volumes"]["R"]["approved"] is True  # the engine reads the scholar's review
    assert EXPORT_ENV not in os.environ  # pointed at the render's own copy only while it runs
    db.refresh(item)
    book = db.get(Book, item.book_id)
    assert book is not None and book.status == BookStatus.in_review and book.cost_usd == 0
    assert book.generation["line"] == "islamic" and book.generation["volume"] == "R"
    assert book.generation["scholar"]["approved_on"] == "2026-10-03"
    assert book.pdf_interior_key and storage.exists(book.pdf_interior_key)
    assert book.pdf_cover_key and storage.exists(book.pdf_cover_key)
    assert storage.exists(book.generation["files"]["answer-key"])
    again = await islamic_book.render_item(db, storage, item)  # a retried job reuses the same book
    assert again["books"][0]["book_id"] == str(book.id)


async def test_a_volume_the_scholar_has_not_approved_is_never_rendered(
    db: Session, storage: ObjectStorage, engine: list[dict[str, Any]]
) -> None:
    _approve(db, "R", but=("u-eid2",))
    item = _item(db, storage)
    result = await islamic_book.render_item(db, storage, item)
    assert result["status"] == "held" and result["held"] == ["R"] and engine == []
    book = db.get(Book, uuid.UUID(result["books"][0]["book_id"]))
    assert book is not None and book.status == BookStatus.failed and "scholar_review" in book.flags
    assert book.error and "u-eid2" in book.error and not book.pdf_interior_key
    _approve(db, "R")  # the admin's retry, once the scholar approved the last unit
    result = await islamic_book.render_item(db, storage, item)
    db.refresh(book)
    assert result["status"] == "in_review" and book.status == BookStatus.in_review
    assert "scholar_review" not in book.flags and len(engine) == 1


async def test_a_set_renders_its_approved_volumes_and_holds_the_rest(
    db: Session, storage: ObjectStorage, engine: list[dict[str, Any]]
) -> None:
    _approve(db, "V1")
    item = _item(db, storage, volume="L1")
    result = await islamic_book.render_item(db, storage, item)
    assert [(b["volume"], b["status"]) for b in result["books"]] == [("V1", "in_review"), ("V2", "held")]
    assert result["status"] == "held" and [c["volume"] for c in engine] == ["V1"]
    assert islamic_book.volumes_wanted(OrderItem(title={"options": {"volume": "set"}})) == [
        "V1",
        "V2",
        "V3",
        "V4",
        "V5",
    ]
    other = _item(db, storage)
    other.line = "journey"
    assert (await islamic_book.render_item(db, storage, other))["status"] == "skipped"


async def test_the_review_previews_are_one_png_per_page(
    db: Session, storage: ObjectStorage, engine: list[dict[str, Any]]
) -> None:
    db.add(
        IslamicReviewPreview(
            volume="R", run_id="run1", status="queued", pages=["islamic/review/R/old/p001.png"]
        )
    )
    db.commit()
    storage.put("islamic/review/R/old/p001.png", b"old", "image/png")
    assert (await islamic_book.previews(db, storage, "R", "older"))["status"] == "superseded"
    result = await islamic_book.previews(db, storage, "R", "run1")
    assert result == {"status": "ready", "pages": 3}
    call = engine[0]
    assert call["print_build"] is False and call["child"].name == "ليان"  # the sample child, never a real one
    row = db.get(IslamicReviewPreview, "R")
    assert row is not None and row.status == "ready" and row.rendered_at and row.problems == []
    assert row.pages == [f"islamic/review/R/run1/p00{n}.png" for n in (1, 2, 3)]
    assert (
        storage.get(row.pages[0]).startswith(b"\x89PNG") and row.cover_key and storage.exists(row.cover_key)
    )
    assert not storage.exists("islamic/review/R/old/p001.png")  # the previous run's files are gone


class _Borrowed:
    """The test's session as the job's `with context.db_session() as db:` (the fixture closes it)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, *exc: object) -> bool:
        return False


def test_the_order_entry_point_renders_each_item(
    db: Session, storage: ObjectStorage, engine: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from qamra_worker import context

    _approve(db, "R")
    item = _item(db, storage, fmt="digital")
    monkeypatch.setattr(context, "init_process", lambda: None)
    monkeypatch.setattr(context, "db_session", lambda: _Borrowed(db))
    monkeypatch.setattr(context, "storage", lambda: storage)
    results = islamic_book.render_order_islamic_items(str(item.order_id))
    assert len(results) == 1 and results[0]["status"] == "in_review"
    assert [c["volume"] for c in engine] == ["R"] and engine[0]["print_build"] is True  # the PDF too
