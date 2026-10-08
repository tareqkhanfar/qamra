"""«مغامراتي مع عائلتي» for an order item (Addendum 9 §2: made once, then per order with no new AI cost).

    qamra_worker.jobs.family_book.render_family_item(item_id)     # one order item of the family line
    qamra_worker.jobs.family_book.render_order_family_items(order_id)

The order item (from `POST /api/shop/workbooks/cart`) carries the child, the variant and, in its
`personalization`, the approved character used (`character_id`). The page engine
(`qamra_workbook.render.family_order`) draws the whole book from the plan: the 112-page interior, the cover
and the insert sheets (stickers and card stock, die lines on their own layer), cut-outs of the child come
from the character sheet, exactly as the sample render does. The files are stored like the story books'
(`children/<child>/books/<book>/files/…`) on a `Book` row linked to the order item, with every file's
preflight; the book waits `in_review` for an admin's print approval (Addendum 3 §5), after which print
batches pick up its interior and cover. The insert sheets' keys are in `book.generation["files"]`.

The family (name, city, up to 6 members) comes from `personalization["family"]` when the order has it:
{"name": "…", "city": "…", "members": [{"role": "…", "name": "…", "scarf": false}]}. Without it the book is
drawn for the child with one neutral grown-up («أحد الكبار»), never an assumed mother and father (A7 §9).
The city is optional: without it the engine prints «مَدينَتِنا» / «مدينتكم» (`render.spec.Family.city_in`),
never «سوق » with nothing after it.

The helpers the other activity books' jobs share live here: `approved_character`, `numerals_of`,
`name_en_of` (the parent's English spelling), `name_flags` and `store_inserts` (the sticker and card sheets).
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

from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Character,
    Child,
    FamilyMember,
    Gender,
    Locale,
    OrderItem,
    Theme,
)
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.jobs.books import file_key

log = structlog.get_logger("qamra.worker.family_book")
JOB = "qamra_worker.jobs.family_book.render_family_item"
LINE = "family"
THEME_SLUG = "family-book"  # a hidden theme row: every Book needs one; the family book is not a story theme
NEUTRAL_ADULT = "أحد الكبار"
SIZES = ("21x28", "a4")
MAX_MEMBERS_IN_BOOK = 6  # A7 §7
NOT_FOR_ACTIVITY_BOOKS = ("coloring",)  # a coloring-book character is black and white
NAME_EN_GUESSED, NAME_NOT_TRACEABLE = "name_en_guessed", "name_not_traceable"  # book flags (name pages)


def family_of(item: OrderItem, child: Child) -> Any:
    """The order's family, or the child with one neutral grown-up when the order does not list it. A member
    the store marked grown-up or child (`adult`) is drawn that way when the relation alone says otherwise
    (an older brother, a young cousin), so a child never becomes the grown-up of a mission."""
    from qamra_workbook.render.spec import MAX_MEMBERS, Family, Member

    raw = (item.personalization or {}).get("family") or {}
    members = []
    for m in (raw.get("members") or [])[:MAX_MEMBERS]:
        if not isinstance(m, dict):
            continue
        role, name = str(m.get("role", "")).strip() or NEUTRAL_ADULT, str(m.get("name", "")).strip()
        member = Member(role, name, None, bool(m.get("scarf")))
        adult = m.get("adult")
        if isinstance(adult, bool) and adult != member.is_adult:
            member = Member(role, name, "adult" if adult else "child", member.scarf)
        members.append(member)
    name = str(raw.get("name") or "").strip() or child.first_name
    return Family(name, tuple(members) or (Member(NEUTRAL_ADULT),), str(raw.get("city") or "").strip())


def size_of(item: OrderItem) -> str:
    options = (item.title or {}).get("options") or {}
    size = str(options.get("size") or (item.personalization or {}).get("size") or SIZES[0]).lower()
    return size if size in SIZES else SIZES[0]


def numerals_of(item: OrderItem) -> str:
    value = str((item.personalization or {}).get("numerals") or "hindi")
    return value if value in ("hindi", "latin") else "hindi"


def org_of(item: OrderItem, storage: ObjectStorage, tmp: Path) -> dict[str, Any] | None:
    """An organization's copies (A7 §8): `personalization["org"] = {name, logo_key}` puts its logo on the back
    cover; the logo is fetched into the render's folder."""
    raw = (item.personalization or {}).get("org") or {}
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    org: dict[str, Any] = {"name": name}
    key = str(raw.get("logo_key") or "")
    if key and storage.exists(key):
        logo = tmp / "org-logo.png"
        logo.write_bytes(storage.get(key))
        org["logo"] = str(logo)
    return org


def member_sheets_of(
    db: Session, item: OrderItem, child: Child, storage: ObjectStorage, tmp: Path
) -> dict[int, Path]:
    """The illustrated-family add-on: the child's approved family members, matched to the order's family by
    relation and first name, as the member's index → their character sheet (fetched into the render's
    folder). Nothing without the add-on on the item."""
    if not any(str(a.get("slug")) == "family-characters" for a in (item.addons or []) if isinstance(a, dict)):
        return {}
    approved = db.scalars(
        select(FamilyMember).where(
            FamilyMember.child_id == child.id,
            FamilyMember.approved_at.is_not(None),
            FamilyMember.sheet_key.is_not(None),
        )
    ).all()
    by_person = {(m.relation, m.first_name.strip()): m for m in approved}
    out: dict[int, Path] = {}
    members = ((item.personalization or {}).get("family") or {}).get("members") or []
    for index, raw in enumerate(members[:MAX_MEMBERS_IN_BOOK]):
        if not isinstance(raw, dict):
            continue
        member = by_person.get((str(raw.get("relation", "")), str(raw.get("name", "")).strip()))
        if member is None or not member.sheet_key or not storage.exists(member.sheet_key):
            continue
        path = tmp / f"member-{index}.png"
        path.write_bytes(storage.get(member.sheet_key))
        out[index] = path
    return out


def approved_character(db: Session, item: OrderItem, child: Child) -> Character | None:
    """The character the order chose (`personalization["character_id"]`), else the child's newest approved
    one, a coloring-book character (black and white) only when there is no other (order flows A16)."""
    wanted = (item.personalization or {}).get("character_id")
    if wanted:
        character = db.get(Character, uuid.UUID(str(wanted)))
        if character is not None and character.child_id == child.id and character.approved_at is not None:
            return character
    approved = db.execute(
        select(Character)
        .where(Character.child_id == child.id, Character.approved_at.is_not(None))
        .order_by(Character.approved_at.desc())
    ).scalars()
    found = list(approved)
    return next((c for c in found if c.art_style not in NOT_FOR_ACTIVITY_BOOKS), found[0] if found else None)


def name_en_of(item: OrderItem, child: Child) -> str:
    """The parent's English spelling of the child's name: the order line's `name_en`, else the one saved on
    the child (`Child.name_latin`), tidied; "" when there is none (the books then print a flagged guess)."""
    from qamra_workbook.names import clean_latin_name

    for raw in ((item.personalization or {}).get("name_en"), getattr(child, "name_latin", None)):
        clean = clean_latin_name(str(raw or ""))
        if clean:
            return clean
    return ""


def name_flags(flags: list[str] | None, *, guessed: bool, traceable: bool) -> list[str]:
    """The book's flags with the name checks of this render: `name_en_guessed` (the English name pages print
    a transliteration, the parent gave no spelling) and `name_not_traceable` (the Arabic name page could not
    trace the whole name), for the reviewer before print approval."""
    kept = [f for f in (flags or []) if f not in (NAME_EN_GUESSED, NAME_NOT_TRACEABLE)]
    return kept + ([NAME_EN_GUESSED] if guessed else []) + ([] if traceable else [NAME_NOT_TRACEABLE])


def store_inserts(storage: ObjectStorage, book: Book, files: Any) -> dict[str, str]:
    """The render's insert sheets (`files.inserts`, `files.dies`) stored beside the book's files:
    `inserts/<name>.pdf`, the layered print file whose key goes in `generation["files"]` (the print batch and
    the digital download read it there), and `inserts/<name>-die.pdf`, its die lines alone."""
    keys: dict[str, str] = {}
    dies = getattr(files, "dies", None) or {}
    for name, pdf in (getattr(files, "inserts", None) or {}).items():
        keys[name] = file_key(book, f"inserts/{name}.pdf")
        storage.put(keys[name], pdf.read_bytes(), "application/pdf")
        if name in dies:
            storage.put(file_key(book, f"inserts/{name}-die.pdf"), dies[name].read_bytes(), "application/pdf")
    return keys


def family_theme(db: Session) -> Theme:
    theme = db.execute(select(Theme).where(Theme.slug == THEME_SLUG)).scalar_one_or_none()
    if theme is None:
        theme = Theme(
            slug=THEME_SLUG,
            title_ar="مغامراتي مع عائلتي",
            title_en="My Adventures with My Family",
            age_min=3,
            age_max=7,
            active=False,  # never listed as a story theme
            definition={"product": LINE, "engine": "qamra_workbook.render.family_order"},
        )
        db.add(theme)
        db.flush()
    return theme


async def render_item(db: Session, storage: ObjectStorage, item: OrderItem) -> dict[str, Any]:
    """Render and store one family-book order item's print files; returns a short summary."""
    from qamra_workbook.render.family_order import render_order
    from qamra_workbook.render.spec import Child as BookChild

    if item.line != LINE:
        return {"status": "skipped", "reason": f"not a family book ({item.line})"}
    child = db.get(Child, item.child_id) if item.child_id else None
    if child is None:
        return {"status": "failed", "reason": "the order item has no child"}
    character = approved_character(db, item, child)
    if character is None or not character.sheet_image_key:
        return {"status": "failed", "reason": "the child has no approved character"}
    book = db.get(Book, item.book_id) if item.book_id else None
    if book is None:
        book = Book(
            child_id=child.id,
            character_id=character.id,
            theme_id=family_theme(db).id,
            theme_version=1,
            language=Locale.ar,
            art_style=character.art_style,
            status=BookStatus.generating,
            title=f"مغامرات {child.first_name} مع {'عائلتها' if child.gender == Gender.f else 'عائلته'}",
            generation={"line": LINE, "order_item_id": str(item.id)},
        )
        db.add(book)
        db.flush()
        item.book_id = book.id
    book.status = BookStatus.generating
    db.commit()
    with tempfile.TemporaryDirectory(prefix="qamra-family-") as tmp:
        sheet = Path(tmp) / "character-sheet.png"
        sheet.write_bytes(storage.get(character.sheet_image_key))
        family = family_of(item, child)
        files = await render_order(
            BookChild(child.first_name, child.gender.value, sheet),
            family,
            Path(tmp) / "files",
            size=size_of(item),
            numerals=numerals_of(item),  # type: ignore[arg-type]
            org=org_of(item, storage, Path(tmp)),
            member_sheets=member_sheets_of(db, item, child, storage, Path(tmp)),
        )
        book.pdf_interior_key = file_key(book, "interior.pdf")
        storage.put(book.pdf_interior_key, files.interior.read_bytes(), "application/pdf")
        book.pdf_cover_key = file_key(book, "cover.pdf")
        storage.put(book.pdf_cover_key, files.cover.read_bytes(), "application/pdf")
        inserts = store_inserts(storage, book, files)
    book.preflight = files.preflight
    book.generation = {
        **(book.generation or {}),
        "size": size_of(item),
        "pages": files.pages,
        "files": inserts,
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
            data={"line": LINE, "order_item": str(item.id), "preflight": files.passed, "cost_usd": 0.0},
        )
    )
    db.commit()
    log.info("family_book.ready", book=str(book.id), item=str(item.id), passed=files.passed)
    return {
        "status": book.status.value,
        "book_id": str(book.id),
        "pages": files.pages,
        "preflight": files.passed,
    }


def render_family_item(item_id: str) -> dict[str, Any]:
    """RQ entry point: one order item of the family line."""
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
            item = db.get(OrderItem, uuid.UUID(item_id))
            book = db.get(Book, item.book_id) if item is not None and item.book_id else None
            if book is not None:
                book.status = BookStatus.failed
                book.error = f"{type(e).__name__}: {str(e)[:400]}"
                db.commit()
            log.exception("family_book.failed", item=item_id)
            raise


def render_order_family_items(order_id: str) -> list[dict[str, Any]]:
    """RQ entry point: every family-book item of an order (e.g. when the order is confirmed)."""
    context.init_process()
    with context.db_session() as db:
        ids = [
            str(i)
            for i in db.execute(
                select(OrderItem.id).where(OrderItem.order_id == uuid.UUID(order_id), OrderItem.line == LINE)
            ).scalars()
        ]
    return [render_family_item(i) for i in ids]
