"""«قلبي يعرف الله» for an order item, and the review previews (Addendum 10: no new AI cost).

    qamra_worker.jobs.islamic_book.render_islamic_item(item_id)        # one order item of the islamic line
    qamra_worker.jobs.islamic_book.render_order_islamic_items(order_id)
    qamra_worker.jobs.islamic_book.render_review_previews(volume, run_id)   # the scholar's review pages

The order item (from `POST /api/shop/workbooks/cart`) carries the child, the variant (its options: `volume`
V1…V5 or R, or a set L1 / L2 / set, and `format`) and, in its `personalization`, the approved character. The
page engine (`qamra_workbook.render.islamic_volume.render_volume`, a print build) draws each volume from its
plan and content with the child's character and name, in the child's gender. The files are stored like the
other activity books' on a `Book` per volume linked to the order item, with every file's preflight; the book
waits `in_review` for an admin's print approval (Addendum 3 §5), and that approval also needs the scholar's
approval of the volume (admin_books.approve).

P0 (Addendum 10 §3.3): a volume the scholar has not approved unit by unit is never rendered for an order. Its
book is kept `failed` with the reason, and the admin's retry renders it once the volume is approved. Before
every render the review export (`qamra_core.islamic_review.build_export`) is written next to the files and
`QAMRA_ISLAMIC_REVIEW_FILE` points at it: the engine reads the scholar's name and consent from there.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.islamic import IslamicReviewPreview
from qamra_core.db.models import AuditLog, Book, BookStatus, Child, Locale, OrderItem, Theme
from qamra_core.islamic_review import (
    CONTENT_DIR,
    EXPORT_ENV,
    VOLUME_NAMES_AR,
    build_export,
    content_units,
    load_state_sync,
    units_by_volume,
    volumes_of,
    write_export,
)
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.jobs.books import file_key
from qamra_worker.jobs.family_book import approved_character, numerals_of

log = structlog.get_logger("qamra.worker.islamic_book")
LINE = "islamic"
THEME_SLUG = "islamic-series"  # a hidden theme row: every Book needs one; the series is not a story theme
SIZES = ("21x28", "a4")
PREVIEW_PREFIX = "islamic/review"  # shop content in private storage, never a child's data
PREVIEW_DPI = 110
SAMPLE_CHILD = ("ليان", "f")  # the review previews are drawn for the sample child, never a real one
SAMPLE_SHEET = CONTENT_DIR / "workbook" / "samples" / "sample-character.png"


def volumes_wanted(item: OrderItem) -> list[str]:
    """The volumes an item orders: one, or every volume of a set."""
    options = (item.title or {}).get("options") or {}
    return list(volumes_of(str(options.get("volume") or (item.personalization or {}).get("volume") or "")))


def size_of(item: OrderItem) -> str:
    options = (item.title or {}).get("options") or {}
    size = str(options.get("size") or (item.personalization or {}).get("size") or SIZES[0]).lower()
    return size if size in SIZES else SIZES[0]


def islamic_theme(db: Session) -> Theme:
    theme = db.execute(select(Theme).where(Theme.slug == THEME_SLUG)).scalar_one_or_none()
    if theme is None:
        theme = Theme(
            slug=THEME_SLUG,
            title_ar="قلبي يعرف الله",
            title_en="My Heart Knows Allah",
            age_min=4,
            age_max=8,
            active=False,  # never listed as a story theme
            definition={"product": LINE, "engine": "qamra_workbook.render.islamic_volume"},
        )
        db.add(theme)
        db.flush()
    return theme


def _book(
    db: Session, item: OrderItem, child: Child, character_id: uuid.UUID, style: str, volume: str
) -> Book:
    """The item's book for `volume` (reused when a job runs again)."""
    for book in db.execute(select(Book).where(Book.child_id == child.id)).scalars():
        gen = book.generation or {}
        if (
            gen.get("line") == LINE
            and gen.get("order_item_id") == str(item.id)
            and gen.get("volume") == volume
        ):
            return book
    book = Book(
        child_id=child.id,
        character_id=character_id,
        theme_id=islamic_theme(db).id,
        theme_version=1,
        language=Locale.ar,
        art_style=style,
        status=BookStatus.generating,
        title=f"قلبي يعرف الله — {VOLUME_NAMES_AR.get(volume, volume)} — {child.first_name}",
        generation={"line": LINE, "order_item_id": str(item.id), "volume": volume},
    )
    db.add(book)
    db.flush()
    if item.book_id is None:
        item.book_id = book.id
    return book


@contextmanager
def review_export(db: Session, folder: Path) -> Iterator[dict[str, Any]]:
    """The review export next to the render, with `QAMRA_ISLAMIC_REVIEW_FILE` pointing at it meanwhile."""
    data = build_export(load_state_sync(db))
    path = write_export(data, folder / "review-status.json")
    before = os.environ.get(EXPORT_ENV)
    os.environ[EXPORT_ENV] = str(path)
    try:
        yield data
    finally:
        if before is None:
            os.environ.pop(EXPORT_ENV, None)
        else:
            os.environ[EXPORT_ENV] = before


async def _render(volume: str, child: Any, out: Path, **kw: Any) -> Any:
    from qamra_workbook.render.islamic_volume import render_volume

    result = render_volume(volume, child, out, **kw)
    return await result if inspect.isawaitable(result) else result


def _held(db: Session, book: Book, volume: str, review: dict[str, Any]) -> dict[str, Any]:
    """A volume the scholar has not approved: nothing is rendered, the book says why (P0)."""
    waiting = [
        uid
        for uid in review["volumes"].get(volume, {}).get("units", [])
        if review["units"][uid]["status"] != "approved"
    ]
    book.status = BookStatus.failed
    book.error = (
        f"awaiting the scholar's approval of {volume}: {len(waiting)} unit(s) not approved "
        f"({', '.join(waiting[:6])})"
    )
    book.flags = [f for f in (book.flags or []) if f != "scholar_review"] + ["scholar_review"]
    db.commit()
    log.warning("islamic_book.held", book=str(book.id), volume=volume, waiting=len(waiting))
    return {"volume": volume, "book_id": str(book.id), "status": "held", "waiting": waiting}


async def render_one(
    db: Session,
    storage: ObjectStorage,
    item: OrderItem,
    child: Child,
    sheet: Path,
    volume: str,
    tmp: Path,
    review: dict[str, Any],
) -> dict[str, Any]:
    from qamra_workbook.render.spec import Child as BookChild

    character = approved_character(db, item, child)
    if character is None:  # the store only sells it with an approved character
        raise RuntimeError("the child has no approved character")
    book = _book(db, item, child, character.id, character.art_style, volume)
    if not review["volumes"].get(volume, {}).get("approved"):
        return _held(db, book, volume, review)
    book.status = BookStatus.generating
    book.flags = [f for f in (book.flags or []) if f != "scholar_review"]
    db.commit()
    files = await _render(
        volume,
        BookChild(child.first_name, child.gender.value, sheet),
        tmp / f"volume-{volume.lower()}",
        size=size_of(item),
        numerals=numerals_of(item),
        print_build=True,  # the digital copy too: only approved sources, no placeholder
    )
    book.pdf_interior_key = file_key(book, "interior.pdf")
    storage.put(book.pdf_interior_key, files.interior.read_bytes(), "application/pdf")
    book.pdf_cover_key = file_key(book, "cover.pdf")
    storage.put(book.pdf_cover_key, files.cover.read_bytes(), "application/pdf")
    extra = {}
    if files.answer_key is not None:  # the parents' file: also what the printed parent guide add-on prints
        extra["answer-key"] = file_key(book, "answer-key.pdf")
        storage.put(extra["answer-key"], files.answer_key.read_bytes(), "application/pdf")
    book.preflight = files.preflight
    credit = review["volumes"][volume].get("credit_name")
    book.generation = {
        **(book.generation or {}),
        "size": size_of(item),
        "pages": files.pages,
        "files": extra,
        "scholar": {"approved_on": review["volumes"][volume].get("approved_on"), "credit_name": credit},
    }
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
                "volume": volume,
                "order_item": str(item.id),
                "preflight": files.passed,
                "cost_usd": 0.0,
            },
        )
    )
    db.commit()
    log.info("islamic_book.ready", book=str(book.id), item=str(item.id), volume=volume, passed=files.passed)
    return {
        "volume": volume,
        "book_id": str(book.id),
        "status": "in_review",
        "pages": files.pages,
        "preflight": files.passed,
    }


async def render_item(db: Session, storage: ObjectStorage, item: OrderItem) -> dict[str, Any]:
    """Render and store one order item's print files (one book per volume); returns a short summary."""
    if item.line != LINE:
        return {"status": "skipped", "reason": f"not «قلبي يعرف الله» ({item.line})"}
    child = db.get(Child, item.child_id) if item.child_id else None
    if child is None:
        return {"status": "failed", "reason": "the order item has no child"}
    character = approved_character(db, item, child)
    if character is None or not character.sheet_image_key:
        return {"status": "failed", "reason": "the child has no approved character"}
    wanted = volumes_wanted(item)
    if not wanted:
        return {"status": "failed", "reason": "the order item names no volume"}
    done = []
    with tempfile.TemporaryDirectory(prefix="qamra-islamic-") as tmp:
        sheet = Path(tmp) / "character-sheet.png"
        sheet.write_bytes(storage.get(character.sheet_image_key))
        with review_export(db, Path(tmp)) as review:
            for volume in wanted:
                done.append(await render_one(db, storage, item, child, sheet, volume, Path(tmp), review))
    held = [d["volume"] for d in done if d["status"] == "held"]
    return {
        "status": "held" if held else BookStatus.in_review.value,
        "books": done,
        "held": held,
        "preflight": all(d.get("preflight", False) for d in done),
    }


def render_islamic_item(item_id: str) -> dict[str, Any]:
    """RQ entry point: one order item of the islamic line."""
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
            log.exception("islamic_book.failed", item=item_id)
            raise


def render_order_islamic_items(order_id: str) -> list[dict[str, Any]]:
    """RQ entry point: every islamic item of an order (when the order is confirmed)."""
    context.init_process()
    with context.db_session() as db:
        ids = [
            str(i)
            for i in db.execute(
                select(OrderItem.id).where(OrderItem.order_id == uuid.UUID(order_id), OrderItem.line == LINE)
            ).scalars()
        ]
    return [render_islamic_item(i) for i in ids]


# ---- the review previews ------------------------------------------------------------------------------


def rasterize(pdf: Path, out: Path, dpi: int = PREVIEW_DPI) -> list[Path]:
    """One PNG per page of a PDF (the page as printed, bleed included)."""
    import pypdfium2 as pdfium

    out.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf))
    paths = []
    try:
        for i in range(len(doc)):
            path = out / f"{i + 1:03d}.png"
            doc[i].render(scale=dpi / 72).to_pil().convert("RGB").save(path, optimize=True)
            paths.append(path)
    finally:
        doc.close()
    return paths


async def previews(db: Session, storage: ObjectStorage, volume: str, run_id: str) -> dict[str, Any]:
    """Render the volume for the sample child (a preview build: placeholders allowed, no print checks) and
    store one PNG per page for the review page; a newer request supersedes this one."""
    from qamra_workbook.render.spec import Child as BookChild

    row = db.get(IslamicReviewPreview, volume)
    if row is None or row.run_id != run_id:
        return {"status": "superseded"}
    if volume not in units_by_volume(content_units()):
        row.status, row.error = "failed", f"no units for {volume} in content/islamic/units.yaml"
        db.commit()
        return {"status": "failed"}
    old = [*(row.pages or []), *([row.cover_key] if row.cover_key else [])]
    with tempfile.TemporaryDirectory(prefix="qamra-islamic-review-") as tmp:
        folder = Path(tmp)
        sheet = SAMPLE_SHEET if SAMPLE_SHEET.is_file() else None
        with review_export(db, folder):
            files = await _render(
                volume,
                BookChild(SAMPLE_CHILD[0], SAMPLE_CHILD[1], sheet),  # type: ignore[arg-type]
                folder / "out",
                size=SIZES[0],
                numerals="hindi",
                print_build=False,
            )
        base = f"{PREVIEW_PREFIX}/{volume}/{run_id}"
        keys = []
        for n, png in enumerate(rasterize(files.interior, folder / "png"), start=1):
            keys.append(f"{base}/p{n:03d}.png")
            storage.put(keys[-1], png.read_bytes(), "image/png")
        covers = rasterize(files.cover, folder / "cover")
        cover_key = f"{base}/cover.png" if covers else None
        if cover_key:
            storage.put(cover_key, covers[0].read_bytes(), "image/png")
    db.refresh(row)
    if row.run_id != run_id:  # asked again meanwhile: keep the newer run, drop these files
        for key in [*keys, *([cover_key] if cover_key else [])]:
            storage.delete(key)
        return {"status": "superseded"}
    row.pages, row.cover_key, row.status, row.error = keys, cover_key, "ready", None
    row.problems = sorted(name for name, report in files.preflight.items() if not report.get("passed"))
    row.rendered_at = datetime.now(UTC)
    db.commit()
    for key in old:
        if key not in keys and key != cover_key:
            storage.delete(key)
    log.info("islamic_book.previews_ready", volume=volume, run=run_id, pages=len(keys))
    return {"status": "ready", "pages": len(keys)}


def render_review_previews(volume: str, run_id: str) -> dict[str, Any]:
    """RQ entry point: the review pages of one volume."""
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        try:
            return asyncio.run(previews(db, storage, volume, run_id))
        except Exception as e:
            db.rollback()
            row = db.get(IslamicReviewPreview, volume)
            if row is not None and row.run_id == run_id:
                row.status, row.error = "failed", f"{type(e).__name__}: {str(e)[:400]}"
                db.commit()
            log.exception("islamic_book.previews_failed", volume=volume, run=run_id)
            raise
