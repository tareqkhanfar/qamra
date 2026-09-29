"""«ارسم صاحبك» and «حكاية خاصة» in the worker with the fake providers: the options drawn for the parent, the
chosen companion in the book, and a custom story's text and pictures written from the family's brief."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.pipeline.companion import DrawingRejected
from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Companion,
    CompanionStatus,
    CompanionType,
    Gender,
    GenerationCost,
    Locale,
    Theme,
    User,
)
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs import companions as job
from qamra_worker.jobs.books import run_book_job

AI_FIXTURES = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures"
FACE = AI_FIXTURES / "face-astronaut-public-domain.png"
DRAWING = sorted((AI_FIXTURES / "drawings").glob("drawing-*.jpg"))[0]
BRIEF = {
    "occasion": "عيد ميلادها الخامس",
    "place": "بيت ستّي في نابلس",
    "loves": ["الكنافة", "الأرجوحة تحت الزيتونة"],
    "wish": "أن تبقى تحب مشاركة ألعابها",
    "family": [{"role": "ستّي", "name": "فاطمة"}],
}


def _child(db: Session) -> Child:
    parent = User(email="mom@example.com", full_name="أم ليان")
    db.add(parent)
    db.flush()
    child = Child(
        guardian_user_id=parent.id, first_name="ليان", gender=Gender.f, birth_year=datetime.now(UTC).year - 5
    )
    db.add(child)
    db.flush()
    return child


def _companion(db: Session, storage: ObjectStorage, child: Child, **kw: Any) -> Companion:
    comp = Companion(
        child_id=child.id,
        name="نونو",
        type_hint=CompanionType.creature,
        traits="funny, kind",
        status=kw.pop("status", CompanionStatus.generating),
        regen_count=1,
        params={"style": "watercolor"},
        options=[],
        **kw,
    )
    db.add(comp)
    db.flush()
    comp.cleaned_key = f"children/{child.id}/companions/{comp.id}/cleaned.png"
    storage.put(comp.cleaned_key, DRAWING.read_bytes(), "image/jpeg")
    db.commit()
    return comp


async def test_two_options_are_drawn_for_the_parent_and_costed_to_the_child(
    db: Session, storage: ObjectStorage
) -> None:
    child = _child(db)
    comp = _companion(db, storage, child)
    assert await job.draw_options(db, storage, comp, offline="fake") == {"status": "ready", "options": 2}
    db.refresh(comp)
    base = f"children/{child.id}/companions/{comp.id}/"
    assert comp.status == CompanionStatus.ready and comp.description_en
    assert [o["key"] for o in comp.options] == [f"{base}option-1-1.png", f"{base}option-1-2.png"]
    assert all(storage.exists(o["key"]) and o["fidelity"] == 4 for o in comp.options)
    costs = db.scalars(select(GenerationCost).where(GenerationCost.child_id == child.id)).all()
    steps = {c.step for c in costs}
    assert {"companion:review", "companion:option1", "companion:option2", "companion:fidelity"} <= steps
    assert all(c.book_id is None for c in costs)  # a child's companion is reused by all their books

    comp.status, comp.regen_count = CompanionStatus.generating, 2  # «ارسمه من جديد»
    db.commit()
    await job.draw_options(db, storage, comp, offline="fake")
    assert [o["round"] for o in comp.options] == [1, 1, 2, 2] and comp.options[2]["key"].endswith(
        "option-2-1.png"
    )


async def test_a_rejected_drawing_is_not_one_of_the_free_redraws(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def reject(*_: object, **__: object) -> None:
        raise DrawingRejected("not a drawing")

    monkeypatch.setattr(job, "generate_companion_options", reject)
    comp = _companion(db, storage, _child(db))
    result = await job.draw_options(db, storage, comp, offline="fake")
    assert result == {"status": "failed", "reason": "drawing_rejected"}
    db.refresh(comp)
    assert comp.status == CompanionStatus.failed and comp.params["failed_rounds"] == 1
    assert comp.params["error"]["ar"].startswith("هذه الرسمة") and comp.options == []


def _book(db: Session, storage: ObjectStorage, child: Child, slug: str, **generation: Any) -> Book:
    raw = yaml.safe_load((CONTENT_DIR / f"themes/{slug}/theme.yaml").read_text(encoding="utf-8"))
    theme = Theme(
        slug=slug,
        version=raw["version"],
        title_ar="t",
        title_en="t",
        age_min=3,
        age_max=8,
        companion_slot=True,
        definition=raw,
    )
    db.add(theme)
    character = Character(child_id=child.id, art_style="watercolor", status=CharacterStatus.approved)
    db.add(character)
    db.flush()
    character.sheet_image_key = f"children/{child.id}/characters/{character.id}.png"
    character.approved_at = datetime.now(UTC)
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    book = Book(
        child_id=child.id,
        character_id=character.id,
        theme_id=theme.id,
        theme_version=raw["version"],
        language=Locale.ar,
        art_style="watercolor",
        status=BookStatus.generating,
        budget_usd=Decimal("3.00"),
        generation={"offline": "fake", "line": "magic", **generation},
    )
    db.add(book)
    db.commit()
    return book


async def test_the_book_is_drawn_with_the_chosen_companion(db: Session, storage: ObjectStorage) -> None:
    child = _child(db)
    comp = _companion(db, storage, child, status=CompanionStatus.approved, description_en="a purple blob")
    comp.sheet_key = f"children/{child.id}/companions/{comp.id}/option-1-2.png"
    comp.approved_at = datetime.now(UTC)
    storage.put(comp.sheet_key, FACE.read_bytes(), "image/png")
    book = _book(db, storage, child, "first-day")
    book.companion_id = comp.id
    db.commit()

    result = await run_book_job(db, storage, book, "preview")
    assert result["status"] == "preview", (result, book.error, book.flags)
    db.refresh(book)
    texts = [p.text or "" for p in db.scalars(select(BookPage).where(BookPage.book_id == book.id))]
    assert any("نونو" in t for t in texts) and not any("قَمّور" in t for t in texts)  # not the theme's
    assert any(s["kind"] == "companion" for s in book.generation["plan"])  # «وهكذا وُلد صاحبي»
    db.refresh(comp)
    assert comp.sheet_key.endswith("option-1-2.png")  # the parent's choice is kept, never redrawn


async def test_a_custom_story_is_written_and_drawn_from_the_brief(
    db: Session, storage: ObjectStorage
) -> None:
    book = _book(db, storage, _child(db), "custom", custom=BRIEF)
    result = await run_book_job(db, storage, book, "preview")
    assert result["status"] == "preview", (result, book.error, book.flags)
    db.refresh(book)
    pages = book.story["pages"]
    assert len(pages) == 14 and "الكنافة" in pages[5]["text"] and "بيت ستّي" in pages[0]["text"]
    pinned = book.generation["theme_def"]  # the pages are drawn from the story's own scenes
    assert pinned["slug"] == "custom" and "main_place" in pinned["locations"]
    assert pinned["pages"][5]["scene"].startswith("The hero at بيت ستّي في نابلس")
    drawn = db.scalars(
        select(BookPage).where(BookPage.book_id == book.id, BookPage.preview_image_key.is_not(None))
    )
    assert len(drawn.all()) >= 3


async def test_an_unsafe_brief_stops_the_book_before_anything_is_written(
    db: Session, storage: ObjectStorage
) -> None:
    book = _book(db, storage, _child(db), "custom", custom={**BRIEF, "place": "اتصلوا على 0599123456"})
    assert await run_book_job(db, storage, book, "preview") == {"status": "brief_unsafe"}
    db.refresh(book)
    assert book.status == BookStatus.failed and "brief_unsafe" in book.flags and not book.story


def test_a_redraw_gets_new_seeds_and_the_first_round_keeps_the_old_ones() -> None:
    from qamra_ai.pipeline.companion import companion_request
    from qamra_ai.pipeline.models import CompanionSpec, DrawingReview
    from qamra_ai.pipeline.theme import load_style

    review = DrawingReview(safe=True, is_drawing=True, description_en="d", key_features=[], reasons=[])
    spec, style = CompanionSpec(name="نونو"), load_style("watercolor")
    seeds = [companion_request(spec, review, b"png", style, n, r).seed for r in (1, 2) for n in (1, 2)]
    assert seeds == [1001, 1002, 2001, 2002]
