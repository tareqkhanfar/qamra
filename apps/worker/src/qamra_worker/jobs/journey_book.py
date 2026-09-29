"""«رحلتي الأولى للتعلّم» for an order item: one stage for one child (Addendum 9 §2: no new AI cost).

    qamra_worker.jobs.journey_book.render_journey_item(item_id)      # one order item of the journey line
    qamra_worker.jobs.journey_book.render_order_journey_items(order_id)

The order item (from `POST /api/shop/workbooks/cart`) carries the child, the variant (its options: `stage`
1/2/3 or `set`, `format`) and, in its `personalization`, the approved character used. The page engine
(`qamra_workbook.render.journey_order`) draws the stage from the plan and its print layer: the interior, the
cover and the parents' answer key, with cut-outs of the child from the character sheet, exactly as the sample
render does. Audio QR codes point to `https://{BRAND_DOMAIN}/a/{code}`. The files are stored like the story
books' (`children/<child>/books/<book>/files/…`) on a `Book` row linked to the order item, with every file's
preflight; the book waits `in_review` for an admin's print approval (Addendum 3 §5), after which print batches
pick up its interior and cover. A set gets one book per built stage; a stage that is not built yet is skipped.

The product stays «قريبًا» (not orderable) until the educator signs the plan (Tareq's decision, 2026-09-29).
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.models import AuditLog, Book, BookStatus, Child, Locale, OrderItem, Theme
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.jobs.books import file_key
from qamra_worker.jobs.family_book import approved_character, numerals_of
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.journey_book")
LINE = "journey"
THEME_SLUG = "learning-journey"  # a hidden theme row: every Book needs one; the journey is not a story theme
STAGES = (1, 2, 3)


def stages_of(item: OrderItem) -> list[int]:
    """The stages an item orders: one, or all three for a set."""
    options = (item.title or {}).get("options") or {}
    raw = str(options.get("stage") or (item.personalization or {}).get("stage") or "1").strip().lower()
    if raw == "set":
        return list(STAGES)
    return [int(raw)] if raw.isdigit() and int(raw) in STAGES else [1]


def built_stages() -> list[int]:
    from qamra_workbook.journey_book import built_stages as built

    return built()


def journey_theme(db: Session) -> Theme:
    theme = db.execute(select(Theme).where(Theme.slug == THEME_SLUG)).scalar_one_or_none()
    if theme is None:
        theme = Theme(
            slug=THEME_SLUG,
            title_ar="رحلتي الأولى للتعلّم",
            title_en="My First Learning Journey",
            age_min=3,
            age_max=6,
            active=False,  # never listed as a story theme
            definition={"product": LINE, "engine": "qamra_workbook.render.journey_order"},
        )
        db.add(theme)
        db.flush()
    return theme


def _book(
    db: Session, item: OrderItem, child: Child, character_id: uuid.UUID, style: str, stage: int
) -> Book:
    """The item's book for `stage` (reused when a job runs again)."""
    for book in db.execute(select(Book).where(Book.child_id == child.id)).scalars():
        gen = book.generation or {}
        if gen.get("line") == LINE and gen.get("order_item_id") == str(item.id) and gen.get("stage") == stage:
            return book
    book = Book(
        child_id=child.id,
        character_id=character_id,
        theme_id=journey_theme(db).id,
        theme_version=1,
        language=Locale.ar,
        art_style=style,
        status=BookStatus.generating,
        title=f"رحلة {child.first_name} الأولى للتعلّم — المحطة {stage}",
        generation={"line": LINE, "order_item_id": str(item.id), "stage": stage},
    )
    db.add(book)
    db.flush()
    if item.book_id is None:
        item.book_id = book.id
    return book


async def render_stage(
    db: Session, storage: ObjectStorage, item: OrderItem, child: Child, sheet: Path, stage: int, tmp: Path
) -> dict[str, Any]:
    from qamra_workbook.render.journey_order import render_order
    from qamra_workbook.render.spec import Child as BookChild

    character = approved_character(db, item, child)
    if character is None:  # the store only sells it with an approved character
        raise RuntimeError("the child has no approved character")
    book = _book(db, item, child, character.id, character.art_style, stage)
    book.status = BookStatus.generating
    db.commit()
    files = await render_order(
        BookChild(child.first_name, child.gender.value, sheet),
        stage,
        tmp / f"stage-{stage}",
        numerals=numerals_of(item),  # type: ignore[arg-type]
        domain=get_settings().brand_domain,
    )
    book.pdf_interior_key = file_key(book, "interior.pdf")
    storage.put(book.pdf_interior_key, files.interior.read_bytes(), "application/pdf")
    book.pdf_cover_key = file_key(book, "cover.pdf")
    storage.put(book.pdf_cover_key, files.cover.read_bytes(), "application/pdf")
    extra = {}
    if files.answer_key is not None:
        extra["answer-key"] = file_key(book, "answer-key.pdf")
        storage.put(extra["answer-key"], files.answer_key.read_bytes(), "application/pdf")
    book.preflight = files.preflight
    book.generation = {**(book.generation or {}), "pages": files.pages, "files": extra}
    book.flags = [f for f in (book.flags or []) if f != "preflight_failed"] + (
        [] if files.passed else ["preflight_failed"]
    )
    book.status = BookStatus.in_review  # an admin approves it for print, as every printed book (A3 §5)
    book.error = None
    db.add(
        AuditLog(
            actor_user_id=None,
            action="book.final_ready",
            entity_type="book",
            entity_id=str(book.id),
            data={
                "line": LINE,
                "stage": stage,
                "order_item": str(item.id),
                "preflight": files.passed,
                "cost_usd": 0.0,
            },
        )
    )
    db.commit()
    log.info("journey_book.ready", book=str(book.id), item=str(item.id), stage=stage, passed=files.passed)
    return {"stage": stage, "book_id": str(book.id), "pages": files.pages, "preflight": files.passed}


async def render_item(db: Session, storage: ObjectStorage, item: OrderItem) -> dict[str, Any]:
    """Render and store one journey order item's print files (one book per stage); returns a short summary."""
    if item.line != LINE:
        return {"status": "skipped", "reason": f"not the learning journey ({item.line})"}
    child = db.get(Child, item.child_id) if item.child_id else None
    if child is None:
        return {"status": "failed", "reason": "the order item has no child"}
    character = approved_character(db, item, child)
    if character is None or not character.sheet_image_key:
        return {"status": "failed", "reason": "the child has no approved character"}
    ready = built_stages()
    wanted = stages_of(item)
    todo = [s for s in wanted if s in ready]
    if not todo:
        return {"status": "skipped", "reason": f"stage {wanted} is not built yet"}
    done = []
    with tempfile.TemporaryDirectory(prefix="qamra-journey-") as tmp:
        sheet = Path(tmp) / "character-sheet.png"
        sheet.write_bytes(storage.get(character.sheet_image_key))
        for stage in todo:
            done.append(await render_stage(db, storage, item, child, sheet, stage, Path(tmp)))
    return {
        "status": BookStatus.in_review.value,
        "books": done,
        "skipped": [s for s in wanted if s not in ready],
        "preflight": all(d["preflight"] for d in done),
    }


def render_journey_item(item_id: str) -> dict[str, Any]:
    """RQ entry point: one order item of the journey line."""
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        item = db.get(OrderItem, uuid.UUID(item_id))
        if item is None:
            return {"status": "missing"}
        try:
            return asyncio.run(render_item(db, storage, item))
        except Exception as e:
            db.rollback()
            for book in db.execute(select(Book).where(Book.status == BookStatus.generating)).scalars():
                if (book.generation or {}).get("order_item_id") == item_id:
                    book.status = BookStatus.failed
                    book.error = f"{type(e).__name__}: {str(e)[:400]}"
            db.commit()
            log.exception("journey_book.failed", item=item_id)
            raise


def render_order_journey_items(order_id: str) -> list[dict[str, Any]]:
    """RQ entry point: every journey item of an order (e.g. when the order is confirmed)."""
    context.init_process()
    with context.db_session() as db:
        ids = [
            str(i)
            for i in db.execute(
                select(OrderItem.id).where(OrderItem.order_id == uuid.UUID(order_id), OrderItem.line == LINE)
            ).scalars()
        ]
    return [render_journey_item(i) for i in ids]
