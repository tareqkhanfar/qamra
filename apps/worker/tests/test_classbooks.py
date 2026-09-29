"""Acceptance (CLAUDE.md §9 Phase 4, Addendum 1 §2): a class of 30 is drawn in one batch with the offline
providers and exported as one print bundle: 30 personal copies (interior + cover, preflight passed), one
combined print file, every child on at least 2 shared pages, and nothing read from a child's photo."""

import io
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from PIL import Image, ImageDraw
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.pipeline.classbook import build_plan, load_class_template
from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Classroom,
    Gender,
    GenerationCost,
    Organization,
    OrgStatus,
    Theme,
)
from qamra_core.db.portal import ClassBook, ClassBookPage, ClassBookStatus
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.classbooks import copy_book, run_class_book

NAMES = [
    "يوسف", "جنى", "ليان", "آدم", "سلمى", "كرم", "تالا", "عمر", "ريم", "زيد",
    "مريم", "حمزة", "لين", "علي", "نور", "سيف", "هيا", "بشير", "دانة", "كنان",
    "ميار", "خالد", "رهف", "سامي", "جود", "أنس", "لمى", "فرح", "باسل", "تيم",
]  # fmt: skip


def _sheet(color: str) -> bytes:
    """A character-sheet stand-in: three views side by side (3:2)."""
    img = Image.new("RGB", (768, 512), "#FBF6EC")
    draw = ImageDraw.Draw(img)
    for i in range(3):
        draw.ellipse((40 + i * 256, 40, 216 + i * 256, 216), fill=color)
        draw.rectangle((70 + i * 256, 220, 186 + i * 256, 480), fill=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_class(db: Session, storage: ObjectStorage, n: int, *, line: str = "magic") -> ClassBook:
    org = Organization(name="روضة القمر", status=OrgStatus.approved, city="رام الله", address="شارع الإرسال")
    db.add(org)
    db.flush()
    room = Classroom(
        organization_id=org.id, name="صف الفراشات", school_year="2026-2027", teacher_name="أ. رنا"
    )
    raw = yaml.safe_load((CONTENT_DIR / "themes/graduation/theme.yaml").read_text(encoding="utf-8"))
    theme = Theme(
        slug="graduation", version=raw["version"], title_ar="t", title_en="t", age_min=5, age_max=6,
        companion_slot=True, definition=raw,
    )  # fmt: skip
    db.add_all([room, theme])
    db.flush()
    storage.put(f"orgs/{org.id}/logo.png", _sheet("#F2B33D"), "image/png")
    org.logo_key = f"orgs/{org.id}/logo.png"
    colors = ["#C98F63", "#E8B98F", "#8D5A3B", "#F3CFAE"]
    ids = []
    for i in range(n):
        child = Child(
            organization_id=org.id,
            classroom_id=room.id,
            first_name=NAMES[i % len(NAMES)],
            gender=Gender.f if i % 2 else Gender.m,
            birth_year=2021,
            wears_hijab=i % 3 == 1,
        )
        db.add(child)
        db.flush()
        key = f"children/{child.id}/characters/sheet.png"
        storage.put(key, _sheet(colors[i % 4]), "image/png")
        db.add(
            Character(
                child_id=child.id,
                art_style="watercolor",
                status=CharacterStatus.approved,
                sheet_image_key=key,
                approved_at=datetime.now(UTC),
            )
        )
        ids.append(str(child.id))
    template = load_class_template("graduation")
    plan = build_plan(template, ids, min_each=2, cap=3, line=line, seed=11)  # type: ignore[arg-type]
    cb = ClassBook(
        classroom_id=room.id,
        organization_id=org.id,
        theme_id=theme.id,
        line=line,
        art_style="watercolor",
        min_appearances=2,
        teacher_message="أحبائي الفراشات، كنتم نور صفّنا طوال السنة.",
        status=ClassBookStatus.generating,
        generation={"offline": "fake"},
        plan={
            "template": "graduation",
            "children": ids,
            "pages": [
                {"index": p.index, "key": p.key, "slots": p.slots, "children": list(p.children)} for p in plan
            ],
        },
    )
    db.add(cb)
    db.commit()
    return cb


async def test_a_class_of_30_is_drawn_in_one_batch_and_exported_as_one_bundle(
    db: Session, storage: ObjectStorage, tmp_path: Path
) -> None:
    cb = make_class(db, storage, 30)
    result = await run_class_book(db, storage, cb)
    assert result["status"] == "review" and result["copies"] == 30, (result, cb.error, cb.flags)
    db.refresh(cb)
    assert cb.progress["stage"] == "done" and cb.progress["pages"] == {"done": 20, "total": 20}

    pages = db.scalars(select(ClassBookPage).where(ClassBookPage.class_book_id == cb.id)).all()
    assert len(pages) == 20 and all(p.print_image_key and p.status.value == "ok" for p in pages)
    assert all(1 <= len(p.child_ids) <= 3 for p in pages)  # capped at 3 children per picture
    appearances: dict[str, int] = {}
    for p in pages:
        for c in p.child_ids:
            appearances[c] = appearances.get(c, 0) + 1
    assert len(appearances) == 30 and min(appearances.values()) >= 2

    combined = PdfReader(io.BytesIO(storage.get(cb.bundle["combined_key"])))
    copies = cb.bundle["copies"]
    assert len(copies) == 30 and len({c["stem"] for c in copies}) == 30
    assert all(c["stem"].startswith("روضة-القمر-صف-الفراشات-") for c in copies)
    interior_pages = None
    for c in copies:
        book = db.get(Book, uuid.UUID(c["book_id"]))
        assert book is not None and book.status == BookStatus.preview
        assert book.generation["line"] == "class" and book.generation["class_book_id"] == str(cb.id)
        assert book.preflight["interior"]["passed"] and book.preflight["cover"]["passed"], book.preflight
        assert book.qa_summary["appearances"] >= 2 and not book.flags
        interior = PdfReader(io.BytesIO(storage.get(str(book.pdf_interior_key))))
        interior_pages = len(interior.pages)
        assert len(PdfReader(io.BytesIO(storage.get(str(book.pdf_cover_key)))).pages) == 1
        assert str(book.pdf_interior_key).startswith(f"children/{book.child_id}/")  # deleted with the child
    assert interior_pages is not None and interior_pages % 4 == 0 and interior_pages >= 23
    assert len(combined.pages) == 30 * (1 + interior_pages)

    covers = db.scalars(select(BookPage).where(BookPage.index == 0)).all()
    assert len(covers) == 30 and all(p.print_image_key for p in covers)
    costs = db.scalars(select(GenerationCost)).all()
    assert any(c.units.get("class_book") == str(cb.id) for c in costs)  # shared pages, tagged
    assert sum(1 for c in costs if c.book_id is not None and c.step.startswith("cover")) == 30


async def test_a_second_run_draws_only_what_changed(db: Session, storage: ObjectStorage) -> None:
    cb = make_class(db, storage, 4)
    assert (await run_class_book(db, storage, cb))["status"] == "review"
    first = {p.index: p.image_key for p in db.scalars(select(ClassBookPage)).all()}
    drawn = len(db.scalars(select(GenerationCost)).all())
    page = db.scalars(select(ClassBookPage).where(ClassBookPage.index == 2)).one()
    page.redraw = True  # the school asked for one redraw
    db.commit()
    assert (await run_class_book(db, storage, cb))["status"] == "review"
    again = db.scalars(select(GenerationCost)).all()
    assert len(again) - drawn == 3  # one picture, its check and its print upscale; nothing else
    assert {p.index: p.image_key for p in db.scalars(select(ClassBookPage)).all()} == first
    child = db.get(Child, uuid.UUID(cb.plan["children"][0]))
    assert child is not None and copy_book(db, cb, child) is not None
