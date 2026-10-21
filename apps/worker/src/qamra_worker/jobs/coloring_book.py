"""«دفاتر التلوين والرسم» for an order item: one personalized copy of a coloring or drawing book (no AI cost).

    qamra_worker.jobs.coloring_book.render_coloring_item(item_id)       # one order item of the colorbook line
    qamra_worker.jobs.coloring_book.render_order_coloring_items(order_id)

The order item (from `POST /api/shop/workbooks/cart`) carries the child, the variant (`format`: softcover for
the stapled books, spiral for the Wire-O sketchbook, digital for the PDF) and, in its `personalization`, the
character the parent chose for the cover: `character_id` with `cover_character: true`, or no character with
`cover_character: false` (the character is optional on this line only). The product's slug comes from the
variant's SKU's product (`qamra_workbook.coloring.titles.BY_SLUG`), so the item knows which of the four books
it is.

The page engine (`qamra_workbook.render.coloring_order.render_order`) draws the fixed line art, the
child's title page and «عن قمرة» with the book code, and the cover (front and back on card) with the
child's name, and their character when the item carries one (`character_sheet=None` otherwise: a drawn
illustration). Every file gets its preflight. The files are stored like the other activity books'
(`children/<child>/books/<book>/files/…`) on one `Book` linked to the order item; the book waits
`in_review` for an admin's print approval (Addendum 3 §5), after which print batches pick up its interior
and cover. The digital PDF is the same files.

Flags for the reviewer, besides `preflight_failed`: `cutout_fallback` / `cutout_feet` (the character could
not be cut out cleanly, see `qamra_pdf.cutout`) and `character_missing` (the item names a character that is
gone or not approved: the cover is printed without it, for staff to check with the parent).
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.models import AuditLog, Book, BookStatus, Character, Child, Locale, OrderItem, Theme
from qamra_core.db.store import CatalogProduct, Variant
from qamra_core.storage import ObjectStorage
from qamra_pdf.arabic_names import genitive
from qamra_worker import context
from qamra_worker.imprint import book_imprint
from qamra_worker.jobs.books import file_key
from qamra_worker.jobs.family_book import NOT_FOR_ACTIVITY_BOOKS, cutout_flags, numerals_of
from qamra_worker.settings import get_settings

if TYPE_CHECKING:
    from qamra_workbook.coloring.titles import Title

log = structlog.get_logger("qamra.worker.coloring_book")
JOB = "qamra_worker.jobs.coloring_book.render_coloring_item"
LINE = "colorbook"
THEME_SLUG = "coloring-books"  # a hidden theme row: every Book needs one; not a story theme
CHARACTER_MISSING = "character_missing"  # book flag: the chosen character is gone, the cover has none


def coloring_theme(db: Session) -> Theme:
    theme = db.execute(select(Theme).where(Theme.slug == THEME_SLUG)).scalar_one_or_none()
    if theme is None:
        theme = Theme(
            slug=THEME_SLUG,
            title_ar="دفاتر التلوين والرسم",
            title_en="Coloring & drawing books",
            age_min=3,
            age_max=7,
            active=False,  # never listed as a story theme
            definition={"product": LINE, "engine": "qamra_workbook.render.coloring_order"},
        )
        db.add(theme)
        db.flush()
    return theme


def product_slug(db: Session, item: OrderItem) -> str | None:
    """The store product of the line (one of the four books): from its variant, else the SKU's own prefix."""
    if item.variant_id is not None:
        slug = db.execute(
            select(CatalogProduct.slug)
            .join(Variant, Variant.product_id == CatalogProduct.id)
            .where(Variant.id == item.variant_id)
        ).scalar_one_or_none()
        if slug:
            return str(slug)
    from qamra_workbook.coloring.titles import BY_SLUG

    sku = str(item.sku or "")
    return next((slug for slug in sorted(BY_SLUG, key=len, reverse=True) if sku.startswith(slug)), None)


def cover_character(db: Session, item: OrderItem, child: Child) -> tuple[Character | None, bool]:
    """The character on the cover, and whether one was asked for but can't be used (`character_missing`).

    Only the character the item carries: a line without one (`cover_character: false`) is printed without a
    character even when the child has one, so the parent's choice holds."""
    personalization = item.personalization or {}
    wanted = personalization.get("character_id")
    if personalization.get("cover_character") is False or not wanted:
        return None, False
    try:
        character = db.get(Character, uuid.UUID(str(wanted)))
    except ValueError:
        character = None
    usable = (
        character is not None
        and character.child_id == child.id
        and character.approved_at is not None
        and bool(character.sheet_image_key)
        and character.art_style not in NOT_FOR_ACTIVITY_BOOKS
    )
    return (character, False) if usable else (None, True)


def _book(db: Session, item: OrderItem, child: Child, character: Character | None, title: Title) -> Book:
    """The item's book (reused when a job runs again)."""
    for book in db.execute(select(Book).where(Book.child_id == child.id)).scalars():
        gen = book.generation or {}
        if gen.get("line") == LINE and gen.get("order_item_id") == str(item.id):
            book.character_id = character.id if character else None
            book.art_style = character.art_style if character else ""
            return book
    book = Book(
        child_id=child.id,
        character_id=character.id if character else None,
        theme_id=coloring_theme(db).id,
        theme_version=1,
        language=Locale.ar,
        art_style=character.art_style if character else "",
        status=BookStatus.generating,
        title=f"{title.name_plain} — {genitive(child.first_name)}",
        generation={"line": LINE, "order_item_id": str(item.id), "title": title.key},
    )
    db.add(book)
    db.flush()
    if item.book_id is None:
        item.book_id = book.id
    return book


async def render_item(db: Session, storage: ObjectStorage, item: OrderItem) -> dict[str, Any]:
    """Render and store one coloring-book order item's print files (one book); a short summary."""
    from qamra_workbook.coloring.titles import BY_SLUG
    from qamra_workbook.render.coloring_order import render_order
    from qamra_workbook.render.spec import Child as BookChild

    if item.line != LINE:
        return {"status": "skipped", "reason": f"not «دفاتر التلوين والرسم» ({item.line})"}
    child = db.get(Child, item.child_id) if item.child_id else None
    if child is None:
        return {"status": "failed", "reason": "the order item has no child"}
    slug = product_slug(db, item)
    title = BY_SLUG.get(slug or "")
    if title is None:
        return {"status": "failed", "reason": f"the order item names no coloring book ({item.sku})"}
    character, missing = cover_character(db, item, child)
    book = _book(db, item, child, character, title)
    book.status = BookStatus.generating
    db.commit()
    with tempfile.TemporaryDirectory(prefix="qamra-coloring-") as tmp:
        sheet = None
        if character is not None and character.sheet_image_key:
            sheet = Path(tmp) / "character-sheet.png"
            sheet.write_bytes(storage.get(character.sheet_image_key))
        files = await render_order(
            BookChild(child.first_name, child.gender.value, sheet),
            title.slug,
            Path(tmp) / title.key,
            numerals=numerals_of(item),  # type: ignore[arg-type]
            domain=get_settings().brand_domain,
            imprint=book_imprint(db, book, child, line=LINE, part=title.name_plain),
        )
        book.pdf_interior_key = file_key(book, "interior.pdf")
        storage.put(book.pdf_interior_key, files.interior.read_bytes(), "application/pdf")
        book.pdf_cover_key = file_key(book, "cover.pdf")
        storage.put(book.pdf_cover_key, files.cover.read_bytes(), "application/pdf")
    book.preflight = files.preflight
    book.generation = {
        **(book.generation or {}),
        "title": title.key,
        "pages": files.pages,
        "files": {},
        "cover_character": character is not None,
    }
    kept = [f for f in (book.flags or []) if f not in ("preflight_failed", CHARACTER_MISSING)]
    book.flags = cutout_flags(
        kept + ([] if files.passed else ["preflight_failed"]) + ([CHARACTER_MISSING] if missing else []),
        files,
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
                "title": title.key,
                "order_item": str(item.id),
                "cover_character": character is not None,
                "preflight": files.passed,
                "cost_usd": 0.0,
            },
        )
    )
    db.commit()
    log.info(
        "coloring_book.ready", book=str(book.id), item=str(item.id), title=title.key, passed=files.passed
    )
    return {
        "status": BookStatus.in_review.value,
        "book_id": str(book.id),
        "title": title.key,
        "pages": files.pages,
        "preflight": files.passed,
        "cover_character": character is not None,
        "flags": list(book.flags),
    }


def render_coloring_item(item_id: str) -> dict[str, Any]:
    """RQ entry point: one order item of the colorbook line."""
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
            log.exception("coloring_book.failed", item=item_id)
            raise


def render_order_coloring_items(order_id: str) -> list[dict[str, Any]]:
    """RQ entry point: every coloring-book item of an order (when the order is confirmed)."""
    context.init_process()
    with context.db_session() as db:
        ids = [
            str(i)
            for i in db.execute(
                select(OrderItem.id).where(OrderItem.order_id == uuid.UUID(order_id), OrderItem.line == LINE)
            ).scalars()
        ]
    return [render_coloring_item(i) for i in ids]
