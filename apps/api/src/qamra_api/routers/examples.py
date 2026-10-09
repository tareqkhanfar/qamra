"""Public examples (docs/decisions.md, "Public examples"): real books, made for synthetic sample children,
that an admin chose to show on the site, so parents can flip through real pages before they start.

- Only sample books (the book and its child both `is_sample`) can ever be published; anything else is refused,
  whatever the caller's role.
- A published book is public only while it stays approved: a redraw or a text edit sends it back to review,
  which hides it until it is approved again.
- Images are web-size copies watermarked «نموذج» (qamra_api.example_art), never print files, and their
  responses carry no names, child ids or storage keys.
The flag lives in `Book.generation["public_example"]` (no migration).
"""

import asyncio
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.layout import BookPlan, plan_book
from qamra_ai.pipeline.theme import Theme
from qamra_api import example_art
from qamra_api.deps import AdminUser, SessionDep, StorageDep, require_admin, require_permission
from qamra_api.errors import ApiError
from qamra_core.db.models import AuditLog, Book, BookPage, BookStatus, Character, Child, Gender, Locale
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.storage import ObjectNotFound, ObjectStorage
from qamra_pdf.arabic_names import case_forms, genitive

router = APIRouter(prefix="/api/examples", tags=["examples"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

Lang = Literal["ar", "en"]
Variant = Literal["girl", "girl_hijab", "boy"]
PUBLIC_STATUSES = (BookStatus.approved, BookStatus.ordered, BookStatus.printed)
IMAGE_HEADERS = {"Cache-Control": "public, max-age=86400"}
LIST_HEADERS = {"Cache-Control": "public, max-age=60"}
SIZES: tuple[example_art.Size, ...] = ("s", "m")
_TASHKEEL = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")  # as assemble.plain
_OPENERS: dict[str, tuple[str, ...]] = {"ar": ("إلى", "الى"), "en": ("to ", "for ", "dear ")}


class ExamplePage(BaseModel):
    beat: int  # 0 = the cover
    layout: str  # cover | full | split | spread
    aspect: str  # the art's shape: 1:1, 3:2 (split) or 16:9 (spread)
    text_area: str  # where the words sit in print: top, bottom, left, right, top-right…, none
    numbers: list[int]  # printed page numbers (none for the cover)
    text: str | None
    image: str  # about 1280 px, watermarked
    thumb: str  # about 560 px, watermarked


class ExampleParents(BaseModel):
    lesson: str
    questions: list[str]


class Example(BaseModel):
    id: uuid.UUID
    theme: str
    variant: Variant
    lang: Lang
    line: Literal["classic", "magic"]
    style: str
    child_name: str  # a synthetic sample child's name
    title: str
    title_name: str  # the cover's big line (the child's name) …
    title_rest: str  # … and the rest of the title, as the printed cover splits it
    dedication: str | None
    page_count: int  # interior pages of the printed book
    cover: str
    character: str | None  # the character sheet (watermarked), for "photo → character → book"
    pages: list[ExamplePage]  # the cover first, then the story in reading order
    parents: ExampleParents | None
    published_at: datetime | None


def variant_of(child: Child) -> Variant:
    if child.gender == Gender.m:
        return "boy"
    return "girl_hijab" if child.wears_hijab else "girl"


def _plain(text: str) -> str:
    return _TASHKEEL.sub("", text)


def split_title(title: str, name: str) -> tuple[str, str]:
    """As the printed cover: ("لَيان", "في أوّل يوم بالروضة") when the title starts with the name."""
    words, target = title.split(), _plain(name).split()
    for i in range(1, len(words) + 1):
        if [_plain(w).strip("،,:") for w in words[:i]] == target:
            return " ".join(words[:i]), " ".join(words[i:])
    return title, ""


def dedication_of(book: Book, name: str, lang: str) -> str | None:
    """The title page's dedication, as the PDF prints it (qamra_ai.pipeline.assemble.dedication_text)."""
    message = (book.parent_message or "").strip()
    if not message:
        story = (book.story or {}).get("dedication")
        return str(story) if story else None
    text = _plain(message).lower()
    named = any(_plain(form).strip().lower() in text for form in case_forms(name))
    if named or text.startswith(_OPENERS.get(lang, ())):
        return message
    return f"إلى {genitive(name)}… {message}" if lang == "ar" else f"To {name}… {message}"


def _public() -> tuple[ColumnElement[bool], ...]:
    """What makes a book visible: a published, approved sample book of a sample child, in an active theme."""
    return (
        Book.is_sample.is_(True),
        Child.is_sample.is_(True),
        Book.status.in_(PUBLIC_STATUSES),
        Book.generation.contains({"public_example": True}),
        ThemeRow.active.is_(True),
    )


def _source(page: BookPage) -> str | None:
    """The stored art a web copy is made from: the generated image (never needs the print upscale)."""
    return page.image_key or page.preview_image_key or page.print_image_key


def _book_theme(book: Book, row: ThemeRow) -> Theme:
    """The theme as the book was drawn (its pinned snapshot), like the worker's `book_theme`."""
    return Theme.model_validate((book.generation or {}).get("theme_def") or row.definition)


def _plan(book: Book, row: ThemeRow) -> BookPlan | None:
    try:
        return plan_book(
            _book_theme(book, row),
            "ar" if book.language == Locale.ar else "en",
            companion_page=bool(book.companion_id),
        )
    except ValueError:  # a malformed theme never takes the listing down
        return None


def _prefix(book: Book) -> str:
    return f"children/{book.child_id}/books/{book.id}/"


async def _derived(
    storage: ObjectStorage, book: Book, name: str, source: str, changed: datetime, size: example_art.Size
) -> bytes:
    """The stored web copy, made on first use (a redrawn page has a new version, so it is made again)."""
    ver = example_art.version(source, changed.isoformat())
    key = example_art.derived_key(_prefix(book), name, size, ver)
    try:
        return await asyncio.to_thread(storage.get, key)
    except ObjectNotFound:
        pass
    try:
        original = await asyncio.to_thread(storage.get, source)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    lang = "ar" if book.language == Locale.ar else "en"
    data = await asyncio.to_thread(example_art.watermarked, original, size, lang)
    await asyncio.to_thread(storage.put, key, data, "image/jpeg")
    return data


def _url(book: Book, path: str, source: str, changed: datetime) -> str:
    return f"/api/examples/{book.id}/{path}?v={example_art.version(source, changed.isoformat())}"


def _pages(book: Book, plan: BookPlan, pages: list[BookPage]) -> list[ExamplePage]:
    """The pages with art, in reading order (the cover, then the theme's beats)."""
    out = []
    for page in sorted(pages, key=lambda p: p.index):
        beat = plan.beats.get(page.index)
        source = _source(page)
        if beat is None or source is None:
            continue
        out.append(
            ExamplePage(
                beat=page.index,
                layout=str(beat.layout),
                aspect=str(beat.aspect),
                text_area=beat.text_area,
                numbers=list(beat.pages),
                text=page.text if page.index > 0 else None,
                image=_url(book, f"pages/{page.index}/m.jpg", source, page.updated_at),
                thumb=_url(book, f"pages/{page.index}/s.jpg", source, page.updated_at),
            )
        )
    return out


def _parents(book: Book) -> ExampleParents | None:
    story: dict[str, Any] = book.story or {}
    lesson, questions = story.get("parents_lesson"), story.get("parents_questions")
    if not lesson:
        return None
    return ExampleParents(lesson=str(lesson), questions=[str(q) for q in (questions or [])])


def build_example(
    book: Book, child: Child, row: ThemeRow, pages: list[BookPage], character: Character | None
) -> Example | None:
    plan = _plan(book, row)
    if plan is None:
        return None
    shown = _pages(book, plan, pages)
    if not shown or shown[0].beat != 0:
        return None  # no cover, no example
    lang: Lang = "ar" if book.language == Locale.ar else "en"
    title = book.title or str((book.story or {}).get("title") or "")
    title_name, title_rest = split_title(title, child.first_name)
    gen = book.generation or {}
    sheet = character.sheet_image_key if character else None
    return Example(
        id=book.id,
        theme=row.slug,
        variant=variant_of(child),
        lang=lang,
        line="classic" if gen.get("line") == "classic" else "magic",
        style=book.art_style,
        child_name=child.first_name,
        title=title,
        title_name=title_name,
        title_rest=title_rest,
        dedication=dedication_of(book, child.first_name, lang),
        page_count=len(gen.get("plan") or []) or plan.page_count,
        cover=shown[0].image,
        character=_url(book, "character/m.jpg", sheet, character.updated_at) if character and sheet else None,
        pages=shown,
        parents=_parents(book),
        published_at=datetime.fromisoformat(gen["public_example_at"])
        if gen.get("public_example_at")
        else None,
    )


async def _load(db: AsyncSession, rows: list[tuple[Book, Child, ThemeRow]]) -> list[Example]:
    ids = [b.id for b, _, _ in rows]
    pages: dict[uuid.UUID, list[BookPage]] = {}
    if ids:
        for p in (await db.execute(select(BookPage).where(BookPage.book_id.in_(ids)))).scalars():
            pages.setdefault(p.book_id, []).append(p)
    sheet_ids = [b.character_id for b, _, _ in rows if b.character_id]
    characters = (
        {c.id: c for c in (await db.execute(select(Character).where(Character.id.in_(sheet_ids)))).scalars()}
        if sheet_ids
        else {}
    )
    out = []
    for book, child, row in rows:
        character = characters.get(book.character_id) if book.character_id else None
        example = build_example(book, child, row, pages.get(book.id, []), character)
        if example is not None:
            out.append(example)
    return out


@router.get("")
async def list_examples(
    db: SessionDep, response: Response, theme: str | None = None, lang: Lang | None = None
) -> list[Example]:
    """Published examples, by theme then variant: what the story pages and the landing flip through."""
    q = (
        select(Book, Child, ThemeRow)
        .join(Child, Child.id == Book.child_id)
        .join(ThemeRow, ThemeRow.id == Book.theme_id)
        .where(*_public())
    )
    if theme:
        q = q.where(ThemeRow.slug == theme)
    if lang:
        q = q.where(Book.language == Locale(lang))
    rows = [(b, c, t) for b, c, t in (await db.execute(q.order_by(Book.approved_at, Book.id))).all()]
    order = {"girl": 0, "girl_hijab": 1, "boy": 2}
    examples = sorted(await _load(db, rows), key=lambda e: (e.theme, order[e.variant]))
    response.headers.update(LIST_HEADERS)
    return examples


async def _public_book(db: AsyncSession, example_id: uuid.UUID) -> Book:
    row = (
        await db.execute(
            select(Book)
            .join(Child, Child.id == Book.child_id)
            .join(ThemeRow, ThemeRow.id == Book.theme_id)
            .where(Book.id == example_id, *_public())
        )
    ).scalar_one_or_none()
    if row is None:
        raise ApiError("not_found", 404)
    return row


@router.get("/{example_id}/pages/{beat}/{size}.jpg")
async def example_page(
    example_id: uuid.UUID, beat: int, size: example_art.Size, db: SessionDep, storage: StorageDep
) -> Response:
    """One page of a published example: web size, watermarked, cacheable by anyone for a day."""
    book = await _public_book(db, example_id)
    page = (
        await db.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == beat))
    ).scalar_one_or_none()
    source = _source(page) if page is not None else None
    if page is None or source is None:
        raise ApiError("not_found", 404)
    data = await _derived(storage, book, f"{beat:02d}", source, page.updated_at, size)
    return Response(data, media_type="image/jpeg", headers=IMAGE_HEADERS)


@router.get("/{example_id}/character/{size}.jpg")
async def example_character(
    example_id: uuid.UUID, size: example_art.Size, db: SessionDep, storage: StorageDep
) -> Response:
    """The example's character sheet (a synthetic child's), for the "photo → character → book" steps."""
    book = await _public_book(db, example_id)
    character = await db.get(Character, book.character_id) if book.character_id else None
    if character is None or not character.sheet_image_key:
        raise ApiError("not_found", 404)
    data = await _derived(storage, book, "character", character.sheet_image_key, character.updated_at, size)
    return Response(data, media_type="image/jpeg", headers=IMAGE_HEADERS)


# ---- admin: publish / unpublish ------------------------------------------------------------------------


class PublishIn(BaseModel):
    # The admin confirms the sample child is invented (a synthetic face), as for Classic templates: a real
    # child's likeness is never shown to the public, even a volunteer's with written consent.
    synthetic_child: Literal[True]


class PublishedOut(BaseModel):
    id: uuid.UUID
    public: bool
    pages: int


@admin_router.post("/books/{book_id}/example", dependencies=[Depends(require_permission("books.review"))])
async def publish_example(
    book_id: uuid.UUID, body: PublishIn, admin: AdminUser, db: SessionDep, storage: StorageDep
) -> PublishedOut:
    """Show an approved sample book on the site. Real children's books can never be published (privacy)."""
    book = await db.get(Book, book_id)
    if book is None:
        raise ApiError("not_found", 404)
    child = await db.get(Child, book.child_id)
    if child is None or not book.is_sample or not child.is_sample:
        raise ApiError("example_not_sample", 403)
    if book.status not in PUBLIC_STATUSES:
        raise ApiError("example_not_approved", 409)
    row = await db.get(ThemeRow, book.theme_id)
    plan = _plan(book, row) if row is not None else None
    pages = (await db.execute(select(BookPage).where(BookPage.book_id == book.id))).scalars().all()
    shown = [p for p in pages if plan is not None and p.index in plan.beats and _source(p)]
    if not any(p.index == 0 for p in shown):
        raise ApiError("example_not_approved", 409)
    for page in shown:  # made now, so the first visitors don't wait for them
        for size in SIZES:
            await _derived(storage, book, f"{page.index:02d}", _source(page) or "", page.updated_at, size)
    now = datetime.now(UTC)
    book.generation = {
        **(book.generation or {}),
        "public_example": True,
        "public_example_at": now.isoformat(),
    }
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.example_published",
            entity_type="book",
            entity_id=str(book.id),
            data={"theme": row.slug if row else None, "pages": len(shown), "synthetic": body.synthetic_child},
        )
    )
    await db.commit()
    return PublishedOut(id=book.id, public=True, pages=len(shown))


@admin_router.delete("/books/{book_id}/example", dependencies=[Depends(require_permission("books.review"))])
async def unpublish_example(book_id: uuid.UUID, admin: AdminUser, db: SessionDep) -> PublishedOut:
    """Take an example off the site (its web copies stay with the sample child's files)."""
    book = await db.get(Book, book_id)
    if book is None:
        raise ApiError("not_found", 404)
    book.generation = {**(book.generation or {}), "public_example": False}
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.example_unpublished",
            entity_type="book",
            entity_id=str(book.id),
            data={},
        )
    )
    await db.commit()
    return PublishedOut(id=book.id, public=False, pages=0)
