"""Book jobs end to end with offline providers (fake text + fake images): database rows, private storage
objects, cost rows, print files, preflight, manual redraw and the budget stop."""

import io
from decimal import Decimal
from pathlib import Path

import yaml
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    ChildPhoto,
    Gender,
    GenerationCost,
    Locale,
    PageStatus,
    PhotoStatus,
    Theme,
    User,
)
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.books import _beat_of, page_key, redraw_pages, run_book_job

FIXTURE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


def _png(color: str = "tan", size: tuple[int, int] = (300, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _book(db: Session, storage: ObjectStorage, *, budget: str = "3.00", offline: str = "fake") -> Book:
    admin = User(email="admin@example.com", full_name="A")
    db.add(admin)
    db.flush()
    child = Child(
        guardian_user_id=admin.id,
        first_name="سلمى",
        gender=Gender.f,
        birth_year=2021,
        wears_hijab=True,
        is_sample=True,
    )
    raw = yaml.safe_load((CONTENT_DIR / "themes/first-day/theme.yaml").read_text(encoding="utf-8"))
    theme = Theme(
        slug="first-day",
        version=raw["version"],
        title_ar="t",
        title_en="t",
        age_min=3,
        age_max=7,
        companion_slot=True,
        definition=raw,
    )
    db.add_all([child, theme])
    db.flush()
    key = f"children/{child.id}/photos/p1.jpg"
    storage.put(key, FIXTURE.read_bytes(), "image/png")
    db.add(ChildPhoto(child_id=child.id, storage_key=key, status=PhotoStatus.accepted))
    character = Character(child_id=child.id, art_style="watercolor")
    db.add(character)
    db.flush()
    book = Book(
        child_id=child.id,
        character_id=character.id,
        theme_id=theme.id,
        theme_version=raw["version"],
        language=Locale.ar,
        art_style="watercolor",
        status=BookStatus.generating,
        is_sample=True,
        budget_usd=Decimal(budget),
        generation={"offline": offline},
        parent_message="نحبّكِ",
    )
    db.add(book)
    db.commit()
    return book


def test_step_names_map_to_pages() -> None:
    assert _beat_of("cover:a1") == 0 and _beat_of("qa:cover:a2") == 0 and _beat_of("upscale:cover") == 0
    assert _beat_of("page:7:a1") == 7 and _beat_of("qa:7:a3") == 7 and _beat_of("upscale:page:12") == 12
    assert _beat_of("story") is None and _beat_of("character:1") is None


async def test_final_book_job_end_to_end(db: Session, storage: ObjectStorage) -> None:
    book = _book(db, storage)
    result = await run_book_job(db, storage, book, "final")
    assert result["status"] == "in_review", (result, book.error, book.flags)

    db.refresh(book)
    character = db.get(Character, book.character_id)
    assert (
        character is not None and character.status == CharacterStatus.approved and character.sheet_image_key
    )
    assert book.story["title"] and len(book.story["parents_questions"]) == 2
    assert (
        book.generation["seed"] and book.generation["outfits"]["day"] and len(book.generation["plan"]) == 24
    )
    assert "hijab" in book.generation["outfits"]["day"]
    assert book.generation["theme_def"]["slug"] == "first-day"  # pinned: later content edits can't move it

    pages = {p.index: p for p in db.scalars(select(BookPage).where(BookPage.book_id == book.id))}
    assert sorted(pages) == list(range(0, 18))
    assert all(
        p.status == PageStatus.ok and p.print_image_key and p.qa_score is not None for p in pages.values()
    )
    assert storage.exists(page_key(book, 3, "thumb"))
    assert pages[1].text and pages[1].original_text == pages[1].text

    for key in (book.pdf_interior_key, book.pdf_cover_key, book.proof_pdf_key):
        assert key and key.startswith(f"children/{book.child_id}/") and storage.exists(key)
    assert book.preflight["interior"]["passed"] and book.preflight["cover"]["passed"]
    assert book.qa_summary["pages"] == 18 and book.qa_summary["recognizable_ratio"] == 1.0

    costs = db.scalars(select(GenerationCost).where(GenerationCost.child_id == book.child_id)).all()
    steps = {c.step.split(":")[0] for c in costs}
    assert {"character", "story", "cover", "page", "qa", "upscale"} <= steps
    photos = db.scalars(select(ChildPhoto).where(ChildPhoto.child_id == book.child_id)).all()
    assert all(p.delete_after is not None for p in photos)  # originals scheduled for deletion

    # resuming does no new work
    before = len(costs)
    again = await run_book_job(db, storage, book, "final")
    assert again["status"] == "in_review"
    assert (
        len(db.scalars(select(GenerationCost).where(GenerationCost.child_id == book.child_id)).all())
        == before + 0
    )

    # one manual redraw adds an attempt with a new seed and re-renders the files
    old_attempts = len(pages[4].attempts)
    redone = await redraw_pages(db, storage, book, [4])
    assert redone["redrawn"] == [4]
    page4 = db.scalar(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 4))
    assert page4 is not None and page4.regen_count == 1 and len(page4.attempts) == old_attempts + 1
    assert page4.attempts[-1]["seed"] != page4.attempts[0]["seed"]
    assert page4.attempts[-1]["why"] == "manual"


async def test_book_gets_the_default_budget_cap(db: Session, storage: ObjectStorage) -> None:
    book = _book(db, storage)
    book.budget_usd = None
    db.commit()
    await run_book_job(db, storage, book, "preview")
    db.refresh(book)
    assert book.budget_usd == Decimal("3.00") and book.status == BookStatus.preview
    assert book.proof_pdf_key and not book.pdf_interior_key  # previews get only the watermarked proof
    pages = db.scalars(
        select(BookPage).where(BookPage.book_id == book.id, BookPage.preview_image_key.is_not(None))
    ).all()
    assert sorted(p.index for p in pages) == [0, 1, 2, 3]

    # ordering redraws the preview pages at print resolution: an upgrade, not a regeneration
    await run_book_job(db, storage, book, "final")
    db.refresh(book)
    page1 = db.scalar(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 1))
    assert page1 is not None and len(page1.attempts) == 2
    assert book.qa_summary["redraws"] == 0 and book.qa_summary["manual_redraws"] == 0
