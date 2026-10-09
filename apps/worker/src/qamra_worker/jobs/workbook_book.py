"""«دوسية التأسيس» for an order item: each ordered volume for one child (Addendum 9 §2: no new AI cost).

    qamra_worker.jobs.workbook_book.render_workbook_item(item_id)       # one order item of the workbook line
    qamra_worker.jobs.workbook_book.render_order_workbook_items(order_id)

The order item (from `POST /api/shop/workbooks/cart`) carries the child, the variant (its options: `level`
kg1/kg2, `volume` 1/2/3 or `set`, `interior` color/bw, `format` spiral/digital) and, in its
`personalization`, the approved character used and the parent's English spelling of the name (`name_en`, else
the child's saved `name_latin`) for the English name page. The page engine
(`qamra_workbook.render.workbook.render_order`) draws the volume from its curriculum plan with the child's
name, gender and character, digits ١٢٣ (owner decision 2026-10-07): the interior, the cover (front and back
on card) and the parents' answer key, with every file's preflight. The files are stored like the other
activity books' (`children/<child>/books/<book>/files/…`) on a `Book` per volume linked to the order item; the
book waits `in_review` for an admin's print approval (Addendum 3 §5), after which print batches pick up its
interior and cover. A set gets one book per volume (all three). The digital PDF is the same files.

Flags for the reviewer, besides `preflight_failed`: `name_en_guessed` (no English spelling was given, the
English name page prints a transliteration) and `name_not_traceable` (the Arabic name page could not trace the
whole name; see `qamra_workbook.names`).

The black-and-white interior is not built yet (the B&W variants are off sale, owner decision 2026-10-07): an
item that orders it is refused, and its books are kept `failed` with the reason, for staff to sort out with
the parent.
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
from qamra_pdf.arabic_names import genitive
from qamra_worker import context
from qamra_worker.jobs.books import file_key
from qamra_worker.jobs.family_book import approved_character, name_en_of, name_flags, numerals_of
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.workbook_book")
JOB = "qamra_worker.jobs.workbook_book.render_workbook_item"
LINE = "workbook"
THEME_SLUG = "foundation-workbook"  # a hidden theme row: every Book needs one; not a story theme
LEVELS = ("kg1", "kg2")
VOLUMES = (1, 2, 3)
VOLUME_AR = {1: "الجزء الأول", 2: "الجزء الثاني", 3: "الجزء الثالث"}
BW_REFUSED = (
    "black-and-white interior is not built yet (owner decision 2026-10-07: the B&W variants are off sale); "
    "offer the parent the colour volume or a refund"
)


def _options(item: OrderItem) -> dict[str, Any]:
    return dict((item.title or {}).get("options") or {})


def _option(item: OrderItem, name: str) -> str:
    """A variant option, or the same key in the personalization (older items)."""
    return str(_options(item).get(name) or (item.personalization or {}).get(name) or "").strip().lower()


def level_of(item: OrderItem) -> str | None:
    raw = _option(item, "level")
    return raw if raw in LEVELS else None


def volumes_of(item: OrderItem) -> list[int]:
    """The volumes an item orders: one, or all three for a set."""
    raw = _option(item, "volume")
    if raw == "set":
        return list(VOLUMES)
    return [int(raw)] if raw.isdigit() and int(raw) in VOLUMES else []


def interior_of(item: OrderItem) -> str:
    return str(_options(item).get("interior") or "color").strip().lower()


def workbook_theme(db: Session) -> Theme:
    theme = db.execute(select(Theme).where(Theme.slug == THEME_SLUG)).scalar_one_or_none()
    if theme is None:
        theme = Theme(
            slug=THEME_SLUG,
            title_ar="دوسية التأسيس",
            title_en="Foundation workbook",
            age_min=4,
            age_max=6,
            active=False,  # never listed as a story theme
            definition={"product": LINE, "engine": "qamra_workbook.render.workbook"},
        )
        db.add(theme)
        db.flush()
    return theme


def _book(
    db: Session,
    item: OrderItem,
    child: Child,
    character_id: uuid.UUID | None,
    style: str,
    level: str,
    volume: int,
) -> Book:
    """The item's book for `volume` (reused when a job runs again)."""
    for book in db.execute(select(Book).where(Book.child_id == child.id)).scalars():
        gen = book.generation or {}
        if (
            gen.get("line") == LINE
            and gen.get("order_item_id") == str(item.id)
            and gen.get("level") == level
            and gen.get("volume") == volume
        ):
            return book
    book = Book(
        child_id=child.id,
        character_id=character_id,
        theme_id=workbook_theme(db).id,
        theme_version=1,
        language=Locale.ar,
        art_style=style,
        status=BookStatus.generating,
        title=f"دوسية {genitive(child.first_name)} — {level.upper()} — {VOLUME_AR[volume]}",
        generation={"line": LINE, "order_item_id": str(item.id), "level": level, "volume": volume},
    )
    db.add(book)
    db.flush()
    if item.book_id is None:
        item.book_id = book.id
    return book


def _refused(db: Session, item: OrderItem, child: Child, level: str, volumes: list[int]) -> dict[str, Any]:
    """A black-and-white item: its books stay `failed` with the reason, so staff see it in the admin."""
    character = approved_character(db, item, child)
    books = []
    for volume in volumes:
        book = _book(
            db,
            item,
            child,
            character.id if character else None,
            character.art_style if character else "",
            level,
            volume,
        )
        book.status, book.error = BookStatus.failed, f"{BW_REFUSED} ({level} volume {volume})"
        books.append(str(book.id))
    db.commit()
    log.warning("workbook_book.bw_refused", item=str(item.id), level=level, volumes=volumes)
    return {"status": "refused", "reason": BW_REFUSED, "books": books}


async def render_volume(
    db: Session,
    storage: ObjectStorage,
    item: OrderItem,
    child: Child,
    sheet: Path,
    level: str,
    volume: int,
    tmp: Path,
) -> dict[str, Any]:
    from qamra_workbook.render.spec import Child as BookChild
    from qamra_workbook.render.workbook import render_order

    character = approved_character(db, item, child)
    if character is None:  # the store only sells it with an approved character
        raise RuntimeError("the child has no approved character")
    book = _book(db, item, child, character.id, character.art_style, level, volume)
    book.status = BookStatus.generating
    db.commit()
    files = await render_order(
        BookChild(child.first_name, child.gender.value, sheet),
        level,
        volume,
        tmp / f"{level}-v{volume}",
        interior="color",
        name_en=name_en_of(item, child),
        numerals=numerals_of(item),  # type: ignore[arg-type]
        domain=get_settings().brand_domain,
    )
    book.pdf_interior_key = file_key(book, "interior.pdf")
    storage.put(book.pdf_interior_key, files.interior.read_bytes(), "application/pdf")
    book.pdf_cover_key = file_key(book, "cover.pdf")
    storage.put(book.pdf_cover_key, files.cover.read_bytes(), "application/pdf")
    extra = {}
    if files.answer_key is not None:  # the parents' answer key (free download)
        extra["answer-key"] = file_key(book, "answer-key.pdf")
        storage.put(extra["answer-key"], files.answer_key.read_bytes(), "application/pdf")
    book.preflight = files.preflight
    book.generation = {
        **(book.generation or {}),
        "pages": files.pages,
        "files": extra,
        "name_en": files.name_en,
    }
    book.flags = [f for f in (book.flags or []) if f != "preflight_failed"] + (
        [] if files.passed else ["preflight_failed"]
    )
    book.flags = name_flags(book.flags, guessed=files.name_en_guessed, traceable=files.name_traceable)
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
                "level": level,
                "volume": volume,
                "order_item": str(item.id),
                "preflight": files.passed,
                "cost_usd": 0.0,
            },
        )
    )
    db.commit()
    log.info("workbook_book.ready", book=str(book.id), item=str(item.id), volume=volume, passed=files.passed)
    return {
        "level": level,
        "volume": volume,
        "book_id": str(book.id),
        "pages": files.pages,
        "preflight": files.passed,
        "flags": list(book.flags),
    }


async def render_item(db: Session, storage: ObjectStorage, item: OrderItem) -> dict[str, Any]:
    """Render and store one workbook order item's print files (one book per volume); a short summary."""
    if item.line != LINE:
        return {"status": "skipped", "reason": f"not «دوسية التأسيس» ({item.line})"}
    child = db.get(Child, item.child_id) if item.child_id else None
    if child is None:
        return {"status": "failed", "reason": "the order item has no child"}
    level, volumes = level_of(item), volumes_of(item)
    if level is None or not volumes:
        return {"status": "failed", "reason": f"the order item names no level and volume ({_options(item)})"}
    if interior_of(item) != "color":
        return _refused(db, item, child, level, volumes)
    character = approved_character(db, item, child)
    if character is None or not character.sheet_image_key:
        return {"status": "failed", "reason": "the child has no approved character"}
    done = []
    with tempfile.TemporaryDirectory(prefix="qamra-workbook-") as tmp:
        sheet = Path(tmp) / "character-sheet.png"
        sheet.write_bytes(storage.get(character.sheet_image_key))
        for volume in volumes:
            done.append(await render_volume(db, storage, item, child, sheet, level, volume, Path(tmp)))
    return {
        "status": BookStatus.in_review.value,
        "books": done,
        "preflight": all(d["preflight"] for d in done),
    }


def render_workbook_item(item_id: str) -> dict[str, Any]:
    """RQ entry point: one order item of the workbook line."""
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
            log.exception("workbook_book.failed", item=item_id)
            raise


def render_order_workbook_items(order_id: str) -> list[dict[str, Any]]:
    """RQ entry point: every workbook item of an order (when the order is confirmed)."""
    context.init_process()
    with context.db_session() as db:
        ids = [
            str(i)
            for i in db.execute(
                select(OrderItem.id).where(OrderItem.order_id == uuid.UUID(order_id), OrderItem.line == LINE)
            ).scalars()
        ]
    return [render_workbook_item(i) for i in ids]
