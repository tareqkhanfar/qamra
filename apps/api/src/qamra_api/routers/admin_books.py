"""Admin: sample books, the approval queue (Addendum 3 §5) and the cost dashboard (§2.6).

Everything here needs an admin session that passed 2FA (and the optional IP allowlist). Images and PDFs
are streamed through the API, so object storage never needs a public address.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.cost import fal_cost, fal_unknown_price
from qamra_ai.pipeline.classic import edit_estimate_usd
from qamra_ai.pipeline.custom_story import screen_text
from qamra_ai.pipeline.theme import Theme, fill_title
from qamra_api import notify, runtime_settings
from qamra_api.deps import AdminUser, SessionDep, SettingsDep, StorageDep, require_admin, require_permission
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.uploads import clean_image, read_upload, require_face
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Character,
    Child,
    ChildPhoto,
    Companion,
    CompanionType,
    Consent,
    Gender,
    GenerationCost,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PageStatus,
    PhotoStatus,
    User,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.portal import ClassBook, ClassBookPage
from qamra_core.db.text_review import PAGE, STORY_FIELDS, BookTextEdit
from qamra_core.islamic_review import load_state
from qamra_core.printing import INSERT_LABELS
from qamra_core.storage import ObjectNotFound, ObjectStorage

LINE_JOBS = {  # activity books are drawn by their line's job from the order item, not the story pipeline
    "family": "qamra_worker.jobs.family_book.render_family_item",
    "journey": "qamra_worker.jobs.journey_book.render_journey_item",
    "islamic": "qamra_worker.jobs.islamic_book.render_islamic_item",  # «قلبي يعرف الله» (Addendum 10)
    "workbook": "qamra_worker.jobs.workbook_book.render_workbook_item",  # «دوسية التأسيس» (Addendum 5)
}
# what the book detail shows of `Book.generation` (the activity books: their variant and the English name)
GENERATION_KEYS = (
    *("mode", "progress", "models", "outfits", "offline", "public_example", "line", "pages"),
    *("level", "volume", "stage", "name_en"),
)
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

SAMPLE_CONSENT_VERSION = "sample-2026-09"
FINAL_STATUSES = (BookStatus.in_review, BookStatus.approved, BookStatus.ordered, BookStatus.printed)
CONFIRMED = (BookStatus.approved, BookStatus.ordered, BookStatus.printed)
CLASS_LINE = "class"  # a child's copy of a «كتاب الصف»: its story words are the class's, shown read-only
EMAILED_LINES = (None, "magic", "classic")  # the parent's "book ready" goes out at «تأكيد»
StoryField = Literal["title", "dedication", "parent_message", "parents_lesson", "parents_questions", "blurb"]
_enqueue = enqueue


# ---- samples (acceptance runs before the parent flow exists) ----------------------------------------


_clean_image, _read = clean_image, read_upload


class SampleOut(BaseModel):
    book_id: uuid.UUID


@router.post("/samples", status_code=201, dependencies=[Depends(require_permission("books.review"))])
async def create_sample(
    request: Request,
    admin: AdminUser,
    db: SessionDep,
    settings: SettingsDep,
    storage: StorageDep,
    queue: QueueDep,
    theme: Annotated[str, Form(max_length=64)],
    name: Annotated[str, Form(min_length=1, max_length=40)],
    gender: Annotated[Literal["m", "f"], Form()],
    age: Annotated[int, Form(ge=2, le=10)],
    consent: Annotated[bool, Form()],
    photos: Annotated[list[UploadFile], File()],
    hijab: Annotated[bool, Form()] = False,
    glasses: Annotated[bool, Form()] = False,
    lang: Annotated[Literal["ar", "en"], Form()] = "ar",
    style: Annotated[
        Literal["3d", "watercolor", "cartoon", "semi-realistic", "crayon", "papercut"], Form()
    ] = "watercolor",
    message: Annotated[str | None, Form(max_length=120)] = None,
    offline: Annotated[bool, Form()] = False,
    drawing: Annotated[UploadFile | None, File()] = None,
    companion_name: Annotated[str | None, Form(max_length=30)] = None,
    companion_type: Annotated[Literal["creature", "animal", "robot", "other"], Form()] = "creature",
    mode: Annotated[Literal["preview", "final"], Form()] = "final",
) -> SampleOut:
    """A test book end to end (Addendum 3 §7). Requires the guardian's written consent to be on file."""
    if not consent:
        raise ApiError("consent_required", 422)
    if not 1 <= len(photos) <= 3:
        raise ApiError("invalid_input", 422, {"fields": ["photos"]})
    row = (
        await db.execute(select(ThemeRow).where(ThemeRow.slug == theme, ThemeRow.active))
    ).scalar_one_or_none()
    if row is None or not Theme.model_validate(row.definition).available:
        raise ApiError("not_found", 404)
    cleaned = [_clean_image(await _read(p)) for p in photos]
    for data in cleaned:
        require_face(data)
    drawing_data = (
        _clean_image(await _read(drawing), 2400) if drawing is not None and drawing.filename else None
    )

    now = datetime.now(UTC)
    child = Child(
        guardian_user_id=admin.id,
        first_name=" ".join(name.split()),
        gender=Gender(gender),
        birth_year=date.today().year - age,
        wears_hijab=hijab,
        wears_glasses=glasses,
        is_sample=True,
    )
    db.add(child)
    await db.flush()
    db.add(
        Consent(
            child_id=child.id,
            guardian_user_id=admin.id,
            consent_text_version=SAMPLE_CONSENT_VERSION,
            scope="photo_processing",
            ip=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        )
    )
    for data in cleaned:
        photo = ChildPhoto(child_id=child.id, status=PhotoStatus.accepted)
        db.add(photo)
        await db.flush()
        photo.storage_key = f"children/{child.id}/photos/{photo.id}.jpg"
        storage.put(photo.storage_key, data, "image/jpeg")
    character = Character(child_id=child.id, art_style=style)
    db.add(character)
    companion_id = None
    if drawing_data is not None:
        comp = Companion(
            child_id=child.id,
            name=" ".join((companion_name or ("صاحبي" if lang == "ar" else "My friend")).split()),
            type_hint=CompanionType(companion_type),
            drawing_delete_after=now + timedelta(hours=24),
        )
        db.add(comp)
        await db.flush()
        comp.drawing_key = f"children/{child.id}/companions/{comp.id}/drawing.jpg"
        storage.put(comp.drawing_key, drawing_data, "image/jpeg")
        companion_id = comp.id
    await db.flush()
    values = (await runtime_settings.current(db, settings)).values
    book = Book(
        child_id=child.id,
        character_id=character.id,
        companion_id=companion_id,
        theme_id=row.id,
        theme_version=row.version,
        created_by_user_id=admin.id,
        language=Locale(lang),
        art_style=style,
        status=BookStatus.generating,
        is_sample=True,
        parent_message=" ".join(message.split()) if message else None,
        budget_usd=Decimal(str(values["book_budget_usd"])),
        generation={"offline": "sketch" if offline else False, "requested_by": str(admin.id)},
    )
    db.add(book)
    await db.flush()
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.sample_created",
            entity_type="book",
            entity_id=str(book.id),
            data={"offline": offline, "theme": theme},
        )
    )
    await db.commit()
    _enqueue(queue, "qamra_worker.jobs.books.generate_book", str(book.id), mode)
    return SampleOut(book_id=book.id)


# ---- queue ------------------------------------------------------------------------------------------


class BookCard(BaseModel):
    id: uuid.UUID
    status: BookStatus
    title: str | None
    child_name: str
    theme_slug: str
    theme_title: str
    is_sample: bool
    created_at: datetime
    updated_at: datetime
    flags: list[str]
    cost_usd: float
    budget_usd: float | None
    avg_likeness: float | None
    needs_review: int
    progress: dict[str, Any]
    text_review: Literal["waiting", "confirmed"] | None  # «بانتظار مراجعة النص» for story books


def theme_label(row: ThemeRow, lang: Locale, child: Child | None) -> str:
    """The catalog name ("أوّل يوم في الروضة"); themes without one fall back to the title for the child
    (both {masc/fem} forms when there is no child)."""
    catalog = (row.definition or {}).get("catalog") or {}
    name = catalog.get("name_ar" if lang == Locale.ar else "name_en")
    if name:
        return str(name)
    title = row.title_ar if lang == Locale.ar else row.title_en
    if child is None:
        return fill_title(title, "…", None)
    return fill_title(title, child.first_name, "f" if child.gender.value == "f" else "m")


def _likeness(summary: dict[str, Any]) -> float | None:
    value = summary.get("avg_likeness")
    return float(value) if value is not None else None


def _line(book: Book) -> str | None:
    line = (book.generation or {}).get("line")
    return str(line) if line else None


def reviews_text(book: Book) -> bool:
    """Story books (Magic and custom stories, Classic, class copies) wait for staff to review their words
    before «تأكيد»; the activity books (LINE_JOBS) have no story words and keep their own gates."""
    return _line(book) not in LINE_JOBS


def text_review(book: Book) -> Literal["waiting", "confirmed"] | None:
    """`waiting` («بانتظار مراجعة النص») while a story book's final files are in review, then `confirmed`."""
    if not reviews_text(book):
        return None
    if book.status == BookStatus.in_review:
        return "waiting"
    return "confirmed" if book.status in CONFIRMED else None


def text_editable(book: Book) -> bool:
    """Staff edit the words of Magic, custom and Classic books; a class copy's words belong to its class."""
    return reviews_text(book) and _line(book) != CLASS_LINE and bool(book.story)


@router.get("/books", dependencies=[Depends(require_permission("books.view"))])
async def list_books(
    db: SessionDep,
    view: Literal["review", "flagged", "generating", "approved", "all"] = "review",
    limit: int = 100,
) -> list[BookCard]:
    q = (
        select(Book, Child, ThemeRow)
        .join(Child, Child.id == Book.child_id)
        .join(ThemeRow, ThemeRow.id == Book.theme_id)
    )
    if view == "review":
        q = q.where(Book.status == BookStatus.in_review)
    elif view == "generating":
        q = q.where(Book.status.in_((BookStatus.generating, BookStatus.preview, BookStatus.failed)))
    elif view == "approved":
        q = q.where(Book.status == BookStatus.approved)
    elif view == "flagged":
        q = q.where(func.jsonb_array_length(Book.flags) > 0)
    rows = (await db.execute(q.order_by(Book.updated_at.desc()).limit(min(limit, 200)))).all()
    return [
        BookCard(
            id=b.id,
            status=b.status,
            title=b.title,
            child_name=c.first_name,
            theme_slug=t.slug,
            theme_title=theme_label(t, b.language, c),
            is_sample=b.is_sample,
            created_at=b.created_at,
            updated_at=b.updated_at,
            flags=list(b.flags or []),
            cost_usd=float(b.cost_usd or 0),
            budget_usd=float(b.budget_usd) if b.budget_usd is not None else None,
            avg_likeness=_likeness(b.qa_summary or {}),
            needs_review=int((b.qa_summary or {}).get("needs_review", 0)),
            progress=dict((b.generation or {}).get("progress", {})),
            text_review=text_review(b),
        )
        for b, c, t in rows
    ]


class PageView(BaseModel):
    beat: int
    layout: str | None
    pages: list[int]
    status: PageStatus
    qa_score: float | None
    likeness: int | None
    flags: list[str]
    attempts: int
    regen_count: int
    cost_usd: float
    text: str | None
    original_text: str | None
    has_image: bool
    qa: dict[str, Any]


class TextEditOut(BaseModel):
    id: uuid.UUID
    field: str  # "page" or a story field
    beat: int | None
    kind: str  # edit | revert
    old_text: str | None
    new_text: str | None
    note: str | None
    screen: list[str]
    actor: str | None
    created_at: datetime


class ClassPageOut(BaseModel):
    index: int
    text: str | None


class InsertOut(BaseModel):
    name: str  # its key in `generation["files"]` (stickers, card-money-recipes, answer-key…)
    label: str  # what the printer is told it is


class BookDetail(BaseModel):
    id: uuid.UUID
    status: BookStatus
    title: str | None
    child: dict[str, Any]
    theme: dict[str, str]
    language: str
    art_style: str
    is_sample: bool
    created_at: datetime
    cost_usd: float
    budget_usd: float | None
    flags: list[str]
    qa_summary: dict[str, Any]
    preflight: dict[str, Any]
    error: str | None
    generation: dict[str, Any]
    files: dict[str, bool]
    inserts: list[InsertOut]  # files printed apart: a sticker sheet, card stock, an answer key
    pages: list[PageView]
    plan: list[dict[str, Any]]
    costs: dict[str, float]
    parent_message: str | None
    story: dict[str, Any]
    approved_at: datetime | None
    approved_by: str | None
    text_review: Literal["waiting", "confirmed"] | None
    text_editable: bool
    text_originals: dict[str, str | None]  # the generated words of each story field, for «استرجاع»
    text_edits: list[TextEditOut]  # newest first
    class_pages: list[ClassPageOut]  # a class copy's shared story words (read-only)


def _inserts(book: Book) -> list[InsertOut]:
    files = (book.generation or {}).get("files") or {}
    return [InsertOut(name=str(name), label=INSERT_LABELS.get(str(name), str(name))) for name in files]


async def _book(db: AsyncSession, book_id: uuid.UUID) -> Book:
    book = await db.get(Book, book_id)
    if book is None:
        raise ApiError("not_found", 404)
    return book


@router.get("/books/{book_id}", dependencies=[Depends(require_permission("books.view"))])
async def book_detail(book_id: uuid.UUID, db: SessionDep) -> BookDetail:
    book = await _book(db, book_id)
    child = await db.get(Child, book.child_id)
    theme = await db.get(ThemeRow, book.theme_id)
    if child is None or theme is None:
        raise ApiError("not_found", 404)
    plan = list((book.generation or {}).get("plan", []))
    pages_of: dict[int, list[int]] = {}
    for slot in plan:
        if slot.get("beat") is not None:
            pages_of.setdefault(int(slot["beat"]), []).append(int(slot["number"]))
    rows = (
        await db.execute(select(BookPage).where(BookPage.book_id == book.id).order_by(BookPage.index))
    ).scalars()
    pages = [
        PageView(
            beat=p.index,
            layout=p.layout,
            pages=pages_of.get(p.index, []),
            status=p.status,
            qa_score=float(p.qa_score) if p.qa_score is not None else None,
            likeness=int(p.qa["likeness"]) if p.qa and "likeness" in p.qa else None,
            flags=list(p.flags or []),
            attempts=len(p.attempts or []),
            regen_count=p.regen_count,
            cost_usd=float(p.cost_usd or 0),
            text=p.text,
            original_text=p.original_text,
            has_image=bool(p.image_key),
            qa=dict(p.qa or {}),
        )
        for p in rows
    ]
    group = func.split_part(GenerationCost.step, ":", 1).label("grp")
    groups = (
        await db.execute(
            select(group, func.sum(GenerationCost.usd))
            .where(GenerationCost.book_id == book.id)
            .group_by("grp")
        )
    ).all()
    gen = dict(book.generation or {})
    return BookDetail(
        id=book.id,
        status=book.status,
        title=book.title,
        child={
            "name": child.first_name,
            "gender": child.gender.value,
            "age": date.today().year - child.birth_year,
            "hijab": child.wears_hijab,
            "glasses": child.wears_glasses,
        },
        theme={"slug": theme.slug, "title": theme_label(theme, book.language, child)},
        language=book.language.value,
        art_style=book.art_style,
        is_sample=book.is_sample,
        created_at=book.created_at,
        cost_usd=float(book.cost_usd or 0),
        budget_usd=float(book.budget_usd) if book.budget_usd is not None else None,
        flags=list(book.flags or []),
        qa_summary=dict(book.qa_summary or {}),
        preflight=dict(book.preflight or {}),
        error=book.error,
        generation={k: gen.get(k) for k in GENERATION_KEYS},
        files={
            "interior": bool(book.pdf_interior_key),
            "cover": bool(book.pdf_cover_key),
            "proof": bool(book.proof_pdf_key),
            "mockup_hardcover": bool(_mockup_key(book, "hardcover")),
            "mockup_spread": bool(_mockup_key(book, "spread")),
        },
        inserts=_inserts(book),
        pages=pages,
        plan=plan,
        costs={str(k): round(float(v), 4) for k, v in groups},
        parent_message=book.parent_message,
        story={
            k: (book.story or {}).get(k)
            for k in ("title", "dedication", "parents_lesson", "parents_questions", "blurb")
        },
        approved_at=book.approved_at,
        approved_by=await _name(db, book.approved_by_user_id),
        text_review=text_review(book),
        text_editable=text_editable(book),
        text_originals={f: _original(book, f) for f in STORY_FIELDS},
        text_edits=await _text_edits(db, book.id),
        class_pages=await _class_pages(db, book),
    )


async def _name(db: AsyncSession, user_id: uuid.UUID | None) -> str | None:
    user = await db.get(User, user_id) if user_id else None
    return user.full_name or user.email if user else None


async def _text_edits(db: AsyncSession, book_id: uuid.UUID) -> list[TextEditOut]:
    rows = (
        await db.execute(
            select(BookTextEdit, User)
            .outerjoin(User, User.id == BookTextEdit.actor_user_id)
            .where(BookTextEdit.book_id == book_id)
            .order_by(BookTextEdit.created_at.desc())
            .limit(200)
        )
    ).all()
    return [
        TextEditOut(
            id=e.id,
            field=e.field,
            beat=e.beat,
            kind=e.kind,
            old_text=e.old_text,
            new_text=e.new_text,
            note=e.note,
            screen=list(e.screen or []),
            actor=(u.full_name or u.email) if u else None,
            created_at=e.created_at,
        )
        for e, u in rows
    ]


async def _class_pages(db: AsyncSession, book: Book) -> list[ClassPageOut]:
    """The class's story pages as the copy prints them (the same words in every child's copy)."""
    class_book_id = (book.generation or {}).get("class_book_id")
    if _line(book) != CLASS_LINE or not class_book_id:
        return []
    cb = await db.get(ClassBook, uuid.UUID(str(class_book_id)))
    if cb is None:
        return []
    planned = {int(p["index"]) for p in (cb.plan or {}).get("pages", [])}
    rows = (
        await db.execute(
            select(ClassBookPage).where(ClassBookPage.class_book_id == cb.id).order_by(ClassBookPage.index)
        )
    ).scalars()
    return [ClassPageOut(index=r.index, text=r.text) for r in rows if r.index in planned]


def _stream(
    storage: ObjectStorage, key: str | None, media_type: str, filename: str | None = None
) -> Response:
    if not key:
        raise ApiError("not_found", 404)
    try:
        data = storage.get(key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    headers = {"Cache-Control": "private, max-age=300"}
    if filename:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(data, media_type=media_type, headers=headers)


@router.get("/books/{book_id}/pages/{beat}/image", dependencies=[Depends(require_permission("books.view"))])
async def page_image(
    book_id: uuid.UUID,
    beat: int,
    db: SessionDep,
    storage: StorageDep,
    v: Literal["thumb", "raw", "print", "preview"] = "thumb",
) -> Response:
    book = await _book(db, book_id)
    page = (
        await db.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == beat))
    ).scalar_one_or_none()
    if page is None:
        raise ApiError("not_found", 404)
    if v == "thumb":
        key = f"children/{book.child_id}/books/{book.id}/thumb/{beat:02d}.jpg"
        return _stream(storage, key, "image/jpeg")
    stored = {"raw": page.image_key, "print": page.print_image_key, "preview": page.preview_image_key}[v]
    return _stream(storage, stored, "image/jpeg" if v == "print" else "image/png")


@router.get("/books/{book_id}/character", dependencies=[Depends(require_permission("books.view"))])
async def character_sheet(book_id: uuid.UUID, db: SessionDep, storage: StorageDep) -> Response:
    book = await _book(db, book_id)
    character = await db.get(Character, book.character_id) if book.character_id else None
    return _stream(storage, character.sheet_image_key if character else None, "image/png")


def _mockup_key(book: Book, which: str) -> str | None:
    """Product mockups rendered beside the print files (Addendum 11 §2.7)."""
    key = ((book.generation or {}).get("mockups") or {}).get(which)
    return str(key) if key else None


@router.get("/books/{book_id}/files/{name}", dependencies=[Depends(require_permission("books.view"))])
async def book_file(
    book_id: uuid.UUID,
    name: Literal["interior.pdf", "cover.pdf", "proof.pdf", "mockup-hardcover.png", "mockup-spread.png"],
    db: SessionDep,
    storage: StorageDep,
) -> Response:
    book = await _book(db, book_id)
    key = {
        "interior.pdf": book.pdf_interior_key,
        "cover.pdf": book.pdf_cover_key,
        "proof.pdf": book.proof_pdf_key,
        "mockup-hardcover.png": _mockup_key(book, "hardcover"),
        "mockup-spread.png": _mockup_key(book, "spread"),
    }[name]
    media = "image/png" if name.endswith(".png") else "application/pdf"
    return _stream(storage, key, media, f"qamra-{str(book.id)[:8]}-{name}")


@router.get("/books/{book_id}/inserts/{name}", dependencies=[Depends(require_permission("books.view"))])
async def book_insert(book_id: uuid.UUID, name: str, db: SessionDep, storage: StorageDep) -> Response:
    """A file the book's job rendered to print apart (`generation["files"]`): the sticker sheet with its die
    lines on their layer, the card stock, the answer key."""
    book = await _book(db, book_id)
    key = ((book.generation or {}).get("files") or {}).get(name)
    return _stream(
        storage, str(key) if key else None, "application/pdf", f"qamra-{str(book.id)[:8]}-{name}.pdf"
    )


# ---- review actions ---------------------------------------------------------------------------------


class RedrawIn(BaseModel):
    beats: list[int] = Field(min_length=1, max_length=24)


def _redraw_estimate(values: dict[str, Any], n: int) -> float:
    """What n manual redraws may cost (image + QA + upscale), for the budget pre-check."""
    model = str(values["fal_image_model"])
    tier = "2K" if values["final_mode"] == "2k_upscale" else "1K"
    image = fal_cost(f"{model.removesuffix('/edit')}/edit", resolution=tier)
    per_page = (image if image is not None else fal_unknown_price()) + 0.02
    return round(per_page * n, 4)


@router.post(
    "/books/{book_id}/redraw", status_code=202, dependencies=[Depends(require_permission("books.review"))]
)
async def redraw(
    book_id: uuid.UUID,
    body: RedrawIn,
    admin: AdminUser,
    db: SessionDep,
    settings: SettingsDep,
    queue: QueueDep,
) -> dict[str, Any]:
    """One-click regenerate for the selected pages. Counts toward the book's budget cap."""
    book = await _book(db, book_id)
    if book.status == BookStatus.generating:
        raise ApiError("busy", 409)
    values = (await runtime_settings.current(db, settings)).values
    estimate = (
        0.0 if (book.generation or {}).get("offline") else _redraw_estimate(values, len(set(body.beats)))
    )
    if (book.generation or {}).get("line") == "classic" and estimate:  # a klein hero edit, not a new page
        estimate = round(edit_estimate_usd(str(values["classic_fal_model"])) * len(set(body.beats)), 4)
    remaining = float(book.budget_usd or 0) - float(book.cost_usd or 0)
    if estimate > remaining:
        raise ApiError(
            "budget_exceeded", 409, {"remaining_usd": round(remaining, 2), "estimate_usd": estimate}
        )
    book.status = BookStatus.generating
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.pages_redraw",
            entity_type="book",
            entity_id=str(book.id),
            data={"beats": sorted(set(body.beats))},
        )
    )
    await db.commit()
    _enqueue(queue, "qamra_worker.jobs.books.redraw", str(book.id), sorted(set(body.beats)))
    return {"queued": sorted(set(body.beats)), "estimate_usd": estimate}


# ---- the words: staff review and edit them before «تأكيد» (docs/plans/admin-story-text-review.md) ------


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    note: str | None = Field(default=None, max_length=300)  # keeps words the instant screen flagged


class StoryTextIn(BaseModel):
    field: StoryField
    text: str = Field(max_length=1200)
    note: str | None = Field(default=None, max_length=300)


class TextSaved(BaseModel):
    status: BookStatus
    flags: list[str]
    beat: int | None = None
    text: str | None  # the page's words, or the story field's (questions one per line)


STORY_LIMITS = {"title": 200, "parent_message": 120}  # the columns' lengths; the other fields up to 1200
OPTIONAL_FIELDS = ("parent_message",)  # may be emptied: the book then prints no message from the family


def _set_flags(book: Book, add: list[str], remove: tuple[str, ...] = ()) -> None:
    kept = [f for f in (book.flags or []) if f not in remove]
    book.flags = list(dict.fromkeys([*kept, *add]))


def _editable(book: Book) -> None:
    if book.status == BookStatus.generating:
        raise ApiError("busy", 409)
    if not text_editable(book):
        raise ApiError("not_found", 404)


async def _story_page(db: AsyncSession, book: Book, beat: int) -> BookPage:
    page = (
        await db.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == beat))
    ).scalar_one_or_none()
    if page is None or beat == 0:  # the cover's words are the title (PATCH …/story)
        raise ApiError("not_found", 404)
    return page


def _record(
    db: AsyncSession,
    book: Book,
    admin: User,
    *,
    field: str,
    beat: int | None,
    old: str | None,
    new: str,
    kind: Literal["edit", "revert"],
    note: str | None,
) -> bool:
    """Keep one change of the words: the history row (old and new text, who, when), an id-only audit entry
    and the flag `text_changed` (the PDFs are older than the words until «إعادة إخراج الملفات»). A confirmed
    book goes back to review. Words the instant screen flags need the editor's note (`text_unsafe`)."""
    if new == (old or ""):
        return False
    screen = screen_text(new) if kind == "edit" else []
    reason = " ".join((note or "").split()) or None
    if screen and not reason:
        raise ApiError("text_unsafe", 422, {"reasons": screen})
    db.add(
        BookTextEdit(
            book_id=book.id,
            field=field,
            beat=beat,
            old_text=old,
            new_text=new,
            kind=kind,
            actor_user_id=admin.id,
            note=reason,
            screen=screen,
            created_at=datetime.now(UTC),  # not the transaction's start: several edits keep their order
        )
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.page_text_edited" if field == PAGE else "admin.story_text_edited",
            entity_type="book",
            entity_id=str(book.id),
            data={"field": field, "beat": beat, "kind": kind, "screen_override": screen},
        )
    )
    _set_flags(book, ["text_changed"])
    if book.status in CONFIRMED:
        book.status = BookStatus.in_review  # the confirmed words changed: they need «تأكيد» again
    return True


def _mark_page(page: BookPage) -> None:
    others = [f for f in (page.flags or []) if f != "admin_edited"]
    page.flags = others if page.text == page.original_text else sorted([*others, "admin_edited"])


@router.patch("/books/{book_id}/pages/{beat}", dependencies=[Depends(require_permission("books.review"))])
async def edit_text(
    book_id: uuid.UUID, beat: int, body: TextIn, admin: AdminUser, db: SessionDep
) -> TextSaved:
    """Save one page's words at once (no render): the PDFs follow with «إعادة إخراج الملفات»."""
    book = await _book(db, book_id)
    _editable(book)
    page = await _story_page(db, book, beat)
    text = " ".join(body.text.split())  # tashkeel stays: only runs of spaces and line breaks fold
    if _record(db, book, admin, field=PAGE, beat=beat, old=page.text, new=text, kind="edit", note=body.note):
        page.text = text
        _mark_page(page)
    await db.commit()
    return TextSaved(status=book.status, flags=list(book.flags or []), beat=beat, text=page.text)


@router.post(
    "/books/{book_id}/pages/{beat}/revert", dependencies=[Depends(require_permission("books.review"))]
)
async def revert_text(book_id: uuid.UUID, beat: int, admin: AdminUser, db: SessionDep) -> TextSaved:
    """«استرجاع النص المولَّد»: the page's words as the story was written (before any edit)."""
    book = await _book(db, book_id)
    _editable(book)
    page = await _story_page(db, book, beat)
    if not page.original_text:
        raise ApiError("not_found", 404)
    original = page.original_text
    if _record(db, book, admin, field=PAGE, beat=beat, old=page.text, new=original, kind="revert", note=None):
        page.text = original
        _mark_page(page)
    await db.commit()
    return TextSaved(status=book.status, flags=list(book.flags or []), beat=beat, text=page.text)


def _clean(field: str, text: str) -> str:
    if field == "parents_questions":  # one question per line
        return "\n".join(line for line in (" ".join(raw.split()) for raw in text.splitlines()) if line)
    return " ".join(text.split())


def _story_value(book: Book, field: str) -> str:
    if field == "parent_message":
        return book.parent_message or ""
    value = (book.story or {}).get(field)
    if field == "parents_questions":
        return "\n".join(str(q) for q in value or [])
    return str(value or "")


def _original(book: Book, field: str) -> str | None:
    """The field's words before staff first changed them (kept at the first edit)."""
    originals = (book.generation or {}).get("text_originals") or {}
    return str(originals[field]) if field in originals else _story_value(book, field) or None


async def _apply_story(db: AsyncSession, book: Book, field: str, text: str) -> None:
    """Where each field lives: the story (what the PDF prints), and the title and dedication columns."""
    if field == "parent_message":
        book.parent_message = text or None
        return
    book.story = {**book.story, field: text.split("\n") if field == "parents_questions" else text}
    if field == "dedication":
        book.dedication = text
    if field == "title":
        book.title = text[:200]
        cover = (
            await db.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 0))
        ).scalar_one_or_none()
        if cover is not None:
            cover.text = text


async def _save_story(
    db: AsyncSession,
    book: Book,
    admin: User,
    field: str,
    text: str,
    kind: Literal["edit", "revert"],
    note: str | None,
) -> TextSaved:
    old = _story_value(book, field)
    if _record(db, book, admin, field=field, beat=None, old=old, new=text, kind=kind, note=note):
        originals = dict((book.generation or {}).get("text_originals") or {})
        originals.setdefault(field, old)
        book.generation = {**book.generation, "text_originals": originals}
        await _apply_story(db, book, field, text)
    await db.commit()
    return TextSaved(status=book.status, flags=list(book.flags or []), text=_story_value(book, field))


@router.patch("/books/{book_id}/story", dependencies=[Depends(require_permission("books.review"))])
async def edit_story_text(
    book_id: uuid.UUID, body: StoryTextIn, admin: AdminUser, db: SessionDep
) -> TextSaved:
    """The title (also on the cover), the dedication, the family's message, «للأهل» and the back blurb."""
    book = await _book(db, book_id)
    _editable(book)
    text = _clean(body.field, body.text)
    if (not text and body.field not in OPTIONAL_FIELDS) or len(text) > STORY_LIMITS.get(body.field, 1200):
        raise ApiError("invalid_input", 422, {"fields": ["text"]})
    return await _save_story(db, book, admin, body.field, text, "edit", body.note)


@router.post(
    "/books/{book_id}/story/{field}/revert", dependencies=[Depends(require_permission("books.review"))]
)
async def revert_story_text(
    book_id: uuid.UUID, field: StoryField, admin: AdminUser, db: SessionDep
) -> TextSaved:
    book = await _book(db, book_id)
    _editable(book)
    originals = (book.generation or {}).get("text_originals") or {}
    if field not in originals:
        raise ApiError("not_found", 404)  # never edited: nothing to restore
    return await _save_story(db, book, admin, field, str(originals[field] or ""), "revert", None)


@router.post(
    "/books/{book_id}/rerender", status_code=202, dependencies=[Depends(require_permission("books.review"))]
)
async def rerender(book_id: uuid.UUID, admin: AdminUser, db: SessionDep, queue: QueueDep) -> dict[str, str]:
    """«إعادة إخراج الملفات»: the PDFs again from the stored pictures and the current words (no AI cost).
    The book comes back to review (`in_review`, or `preview` for a preview) and needs «تأكيد» again."""
    book = await _book(db, book_id)
    if book.status == BookStatus.generating:
        raise ApiError("busy", 409)
    if not text_editable(book):
        raise ApiError("not_found", 404)
    if book.status not in (BookStatus.preview, BookStatus.in_review, *CONFIRMED):
        raise ApiError("not_ready", 409)  # a stopped book continues with «متابعة التوليد»
    book.status = BookStatus.generating
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.book_rerender",
            entity_type="book",
            entity_id=str(book.id),
            data={"text_changed": "text_changed" in (book.flags or [])},
        )
    )
    await db.commit()
    _enqueue(queue, "qamra_worker.jobs.books.rerender", str(book.id))
    return {"status": "queued"}


class BudgetIn(BaseModel):
    budget_usd: Decimal = Field(gt=0, le=20, decimal_places=2)


@router.post("/books/{book_id}/budget", dependencies=[Depends(require_permission("books.review"))])
async def set_budget(
    book_id: uuid.UUID, body: BudgetIn, admin: AdminUser, db: SessionDep
) -> dict[str, float]:
    book = await _book(db, book_id)
    book.budget_usd = body.budget_usd
    book.flags = (
        [f for f in (book.flags or []) if f != "budget_exceeded"]
        if body.budget_usd > (book.cost_usd or 0)
        else book.flags
    )
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.budget_changed",
            entity_type="book",
            entity_id=str(book.id),
            data={"budget_usd": float(body.budget_usd)},
        )
    )
    await db.commit()
    return {"budget_usd": float(body.budget_usd)}


class GenerateIn(BaseModel):
    mode: Literal["preview", "final"] = "final"


@router.post(
    "/books/{book_id}/generate", status_code=202, dependencies=[Depends(require_permission("books.review"))]
)
async def generate(
    book_id: uuid.UUID, body: GenerateIn, admin: AdminUser, db: SessionDep, queue: QueueDep
) -> dict[str, str]:
    """(Re)start generation: resume a failed or budget-stopped book, or turn a preview into the full book."""
    book = await _book(db, book_id)
    if book.status == BookStatus.generating:
        raise ApiError("busy", 409)
    if book.status in (BookStatus.approved, BookStatus.ordered, BookStatus.printed):
        raise ApiError("forbidden", 403)
    book.status = BookStatus.generating
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.book_generate",
            entity_type="book",
            entity_id=str(book.id),
            data={"mode": body.mode},
        )
    )
    await db.commit()
    line_job = LINE_JOBS.get(str((book.generation or {}).get("line")))
    item_id = (book.generation or {}).get("order_item_id")
    if line_job and item_id:  # an activity book: its own job draws it again from the plan (no AI cost)
        _enqueue(queue, line_job, str(item_id))
    else:
        _enqueue(queue, "qamra_worker.jobs.books.generate_book", str(book.id), body.mode)
    return {"status": "queued"}


def _passed(preflight: dict[str, Any], name: str) -> bool:
    """A print file's preflight: story books key it `interior`, the activity books `interior.pdf`."""
    report = preflight.get(name) or preflight.get(f"{name}.pdf") or {}
    return bool(report.get("passed"))


async def approve_book(book_id: uuid.UUID, admin: User, db: AsyncSession) -> Book:
    """The last gate (Addendum 3 §5), which is also the review of the story's words: only a reviewed book
    whose print files pass preflight and carry its current words (`text_not_rendered` after an unrendered
    edit). Records who and when; print batches and the parent's reader and share link open only after it."""
    book = await _book(db, book_id)
    preflight = book.preflight or {}
    ready = (
        book.status == BookStatus.in_review
        and book.pdf_interior_key
        and book.pdf_cover_key
        and _passed(preflight, "interior")
        and _passed(preflight, "cover")
        and all(bool(r.get("passed")) for r in preflight.values() if isinstance(r, dict))
        and "pages_missing" not in (book.flags or [])
    )
    if not ready:
        raise ApiError("not_ready", 409)
    if "text_changed" in (book.flags or []):
        raise ApiError("text_not_rendered", 409)
    volume = str((book.generation or {}).get("volume") or "")
    if (book.generation or {}).get("line") == "islamic" and volume not in (
        await load_state(db)
    ).approved_volumes():  # P0 (Addendum 10 §3.3): nothing prints before the scholar approves every unit
        raise ApiError("scholar_not_approved", 409, {"volume": volume})
    edits = await db.scalar(
        select(func.count()).select_from(BookTextEdit).where(BookTextEdit.book_id == book.id)
    )
    book.status = BookStatus.approved
    book.approved_at = datetime.now(UTC)
    book.approved_by_user_id = admin.id
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.book_approved",
            entity_type="book",
            entity_id=str(book.id),
            data={
                "flags": list(book.flags or []),
                "cost_usd": float(book.cost_usd or 0),
                "text_reviewed": reviews_text(book),
                "text_edits": int(edits or 0),
            },
        )
    )
    await db.commit()
    return book


@router.post("/books/{book_id}/approve", dependencies=[Depends(require_permission("books.review"))])
async def approve(book_id: uuid.UUID, admin: AdminUser, db: SessionDep, queue: QueueDep) -> dict[str, Any]:
    """«تأكيد النص واعتماد الكتاب». The family hears "book ready" now (not when the files were rendered)."""
    book = await approve_book(book_id, admin, db)
    if not book.is_sample and _line(book) in EMAILED_LINES:
        notify.book_ready(queue.connection, book.id)
    assert book.approved_at is not None  # nosec B101 (set just above)
    return {"status": book.status.value, "approved_at": book.approved_at.isoformat()}


# ---- cost dashboard ---------------------------------------------------------------------------------


@router.get("/metrics", dependencies=[Depends(require_permission("reports"))])
async def metrics(db: SessionDep, days: int = 30) -> dict[str, Any]:
    """Average cost per book and per page, regeneration and fallback rates per theme (Addendum 3 §2.6)."""
    since = datetime.now(UTC) - timedelta(days=max(1, min(days, 365)))
    rows = (
        await db.execute(
            select(Book, ThemeRow)
            .join(ThemeRow, ThemeRow.id == Book.theme_id)
            .where(Book.created_at >= since, Book.status.in_(FINAL_STATUSES))
        )
    ).all()
    # placeholder-art books cost $0 and would drag the averages the cap is judged by (§7)
    books = [(b, t) for b, t in rows if not (b.generation or {}).get("offline")]
    book_ids = [b.id for b, _ in books]
    page_rows = (
        (await db.execute(select(BookPage).where(BookPage.book_id.in_(book_ids)))).scalars().all()
        if book_ids
        else []
    )
    pages_by_book: dict[uuid.UUID, list[BookPage]] = {}
    for p in page_rows:
        pages_by_book.setdefault(p.book_id, []).append(p)

    per_theme: dict[str, dict[str, Any]] = {}
    costs, per_page = [], []
    lines: dict[str, dict[str, Any]] = {}  # Addendum 4: Classic and Magic are judged by their own targets
    for b, t in books:
        pages = [p for p in pages_by_book.get(b.id, []) if p.status != PageStatus.pending]
        cost = float(b.cost_usd or 0)
        line = lines.setdefault(_line_of(b), {"books": 0, "cost": 0.0, "pages": 0})
        line["books"], line["cost"], line["pages"] = (
            line["books"] + 1,
            line["cost"] + cost,
            line["pages"] + len(pages),
        )
        if _line_of(b) != "magic":
            continue  # the top-level figures and the per-theme rates are Magic's ($2 target, $2.50 cap)
        costs.append(cost)
        if pages:
            per_page.append(cost / len(pages))
        th = per_theme.setdefault(
            t.slug,
            {
                "slug": t.slug,
                "title": theme_label(t, Locale.ar, None),
                "books": 0,
                "cost": 0.0,
                "pages": 0,
                "redraws": 0,
                "fallbacks": 0,
                "needs_review": 0,
                "budget_stops": 0,
            },
        )
        th["books"] += 1
        th["cost"] += cost
        th["pages"] += len(pages)
        th["redraws"] += sum(a.get("why") == "qa" for p in pages for a in (p.attempts or []))
        th["fallbacks"] += sum("fallback_used" in (p.flags or []) for p in pages)
        th["needs_review"] += sum(p.status == PageStatus.needs_review for p in pages)
        th["budget_stops"] += int("budget_exceeded" in (b.flags or []))
    themes = []
    for th in per_theme.values():
        n, n_pages = th["books"], max(1, th["pages"])
        themes.append(
            {
                "slug": th["slug"],
                "title": th["title"],
                "books": n,
                "avg_cost": round(th["cost"] / n, 3),
                "avg_page_cost": round(th["cost"] / n_pages, 4),
                "redraw_rate": round(th["redraws"] / n_pages, 3),
                "fallback_rate": round(th["fallbacks"] / n_pages, 3),
                "needs_review_rate": round(th["needs_review"] / n_pages, 3),
                "budget_stops": th["budget_stops"],
            }
        )
    themes.sort(key=lambda x: -x["redraw_rate"])
    group = func.split_part(GenerationCost.step, ":", 1).label("grp")
    groups = (
        await db.execute(
            select(group, func.sum(GenerationCost.usd))
            .where(GenerationCost.created_at >= since)
            .group_by("grp")
        )
    ).all()
    day = func.date_trunc("day", GenerationCost.created_at).label("day")
    daily = (
        await db.execute(
            select(day, func.sum(GenerationCost.usd))
            .where(GenerationCost.created_at >= since)
            .group_by("day")
            .order_by("day")
        )
    ).all()
    status_counts = dict(
        (
            await db.execute(
                select(Book.status, func.count()).where(Book.created_at >= since).group_by(Book.status)
            )
        ).all()
    )
    avg = round(sum(costs) / len(costs), 3) if costs else None
    return {
        "days": days,
        "books": len(costs),
        "avg_cost_per_book": avg,
        "avg_cost_per_page": round(sum(per_page) / len(per_page), 4) if per_page else None,
        "target_usd": 2.0,
        "cap_usd": 2.5,
        "within_cap_ratio": round(sum(c <= 2.5 for c in costs) / len(costs), 3) if costs else None,
        "themes": themes,
        "by_step": {str(k): round(float(v), 4) for k, v in groups},
        "daily": [{"date": d.date().isoformat(), "usd": round(float(v), 4)} for d, v in daily],
        "status_counts": {str(getattr(k, "value", k)): int(v) for k, v in status_counts.items()},
        "lines": await _line_metrics(db, since, lines),
    }


def _line_of(book: Book) -> str:
    return str((book.generation or {}).get("line") or "magic")


async def _line_metrics(
    db: AsyncSession, since: datetime, lines: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Per line: the average AI cost per finished book and per page, and preview → purchase for books made
    through the create flow in the period (bought = in an order that was not cancelled)."""
    made = (
        await db.execute(
            select(Book.id, Book.generation["line"].astext).where(
                Book.created_at >= since,
                Book.is_sample.is_(False),
                Book.generation["line"].astext.is_not(None),
            )
        )
    ).all()
    bought = {
        b
        for (b,) in (
            await db.execute(
                select(OrderItem.book_id)
                .join(Order, Order.id == OrderItem.order_id)
                .where(OrderItem.book_id.in_([m[0] for m in made]), Order.status != OrderStatus.cancelled)
            )
        ).all()
    } if made else set()  # fmt: skip
    out: dict[str, Any] = {}
    for name in sorted({*lines, *(str(m[1]) for m in made)}):
        stats = lines.get(name, {"books": 0, "cost": 0.0, "pages": 0})
        previews = [m for m in made if m[1] == name]
        n, got = len(previews), sum(m[0] in bought for m in previews)
        out[name] = {
            "books": stats["books"],
            "avg_cost_per_book": round(stats["cost"] / stats["books"], 4) if stats["books"] else None,
            "avg_cost_per_page": round(stats["cost"] / stats["pages"], 4) if stats["pages"] else None,
            "previews": n,
            "bought": got,
            "preview_to_purchase": round(got / n, 3) if n else None,
        }
    return out
