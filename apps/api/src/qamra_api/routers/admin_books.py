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
from qamra_ai.pipeline.theme import Theme
from qamra_api import runtime_settings
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
    PageStatus,
    PhotoStatus,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.storage import ObjectNotFound, ObjectStorage

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

SAMPLE_CONSENT_VERSION = "sample-2026-09"
FINAL_STATUSES = (BookStatus.in_review, BookStatus.approved, BookStatus.ordered, BookStatus.printed)
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
    style: Annotated[Literal["watercolor", "crayon", "papercut"], Form()] = "watercolor",
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


def theme_label(row: ThemeRow, lang: Locale, child_name: str) -> str:
    """The catalog name ("أوّل يوم في الروضة"); themes without one fall back to the rendered title."""
    catalog = (row.definition or {}).get("catalog") or {}
    name = catalog.get("name_ar" if lang == Locale.ar else "name_en")
    if name:
        return str(name)
    title = row.title_ar if lang == Locale.ar else row.title_en
    return title.replace("{name}", child_name).strip()


def _likeness(summary: dict[str, Any]) -> float | None:
    value = summary.get("avg_likeness")
    return float(value) if value is not None else None


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
            theme_title=theme_label(t, b.language, c.first_name),
            is_sample=b.is_sample,
            created_at=b.created_at,
            updated_at=b.updated_at,
            flags=list(b.flags or []),
            cost_usd=float(b.cost_usd or 0),
            budget_usd=float(b.budget_usd) if b.budget_usd is not None else None,
            avg_likeness=_likeness(b.qa_summary or {}),
            needs_review=int((b.qa_summary or {}).get("needs_review", 0)),
            progress=dict((b.generation or {}).get("progress", {})),
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
    pages: list[PageView]
    plan: list[dict[str, Any]]
    costs: dict[str, float]
    parent_message: str | None
    story: dict[str, Any]
    approved_at: datetime | None


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
        theme={"slug": theme.slug, "title": theme_label(theme, book.language, child.first_name)},
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
        generation={
            k: gen.get(k) for k in ("mode", "progress", "models", "outfits", "offline", "public_example")
        },
        files={
            "interior": bool(book.pdf_interior_key),
            "cover": bool(book.pdf_cover_key),
            "proof": bool(book.proof_pdf_key),
        },
        pages=pages,
        plan=plan,
        costs={str(k): round(float(v), 4) for k, v in groups},
        parent_message=book.parent_message,
        story={
            k: (book.story or {}).get(k)
            for k in ("title", "dedication", "parents_lesson", "parents_questions", "blurb")
        },
        approved_at=book.approved_at,
    )


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


@router.get("/books/{book_id}/files/{name}", dependencies=[Depends(require_permission("books.view"))])
async def book_file(
    book_id: uuid.UUID,
    name: Literal["interior.pdf", "cover.pdf", "proof.pdf"],
    db: SessionDep,
    storage: StorageDep,
) -> Response:
    book = await _book(db, book_id)
    key = {
        "interior.pdf": book.pdf_interior_key,
        "cover.pdf": book.pdf_cover_key,
        "proof.pdf": book.proof_pdf_key,
    }[name]
    return _stream(storage, key, "application/pdf", f"qamra-{str(book.id)[:8]}-{name}")


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


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=600)


@router.patch("/books/{book_id}/pages/{beat}", dependencies=[Depends(require_permission("books.review"))])
async def edit_text(
    book_id: uuid.UUID, beat: int, body: TextIn, admin: AdminUser, db: SessionDep, queue: QueueDep
) -> dict[str, Any]:
    book = await _book(db, book_id)
    if book.status == BookStatus.generating:
        raise ApiError("busy", 409)
    page = (
        await db.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == beat))
    ).scalar_one_or_none()
    if page is None or beat == 0:
        raise ApiError("not_found", 404)
    page.text = " ".join(body.text.split())
    book.status = BookStatus.generating
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.page_text_edited",
            entity_type="book",
            entity_id=str(book.id),
            data={"beat": beat},
        )
    )
    await db.commit()
    _enqueue(queue, "qamra_worker.jobs.books.rerender", str(book.id))
    return {"beat": beat, "text": page.text}


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
    _enqueue(queue, "qamra_worker.jobs.books.generate_book", str(book.id), body.mode)
    return {"status": "queued"}


@router.post("/books/{book_id}/approve", dependencies=[Depends(require_permission("books.review"))])
async def approve(book_id: uuid.UUID, admin: AdminUser, db: SessionDep) -> dict[str, Any]:
    """The last gate (Addendum 3 §5): only a reviewed book with print files that pass preflight."""
    book = await _book(db, book_id)
    preflight = book.preflight or {}
    ready = (
        book.status == BookStatus.in_review
        and book.pdf_interior_key
        and book.pdf_cover_key
        and preflight.get("interior", {}).get("passed")
        and preflight.get("cover", {}).get("passed")
        and "pages_missing" not in (book.flags or [])
    )
    if not ready:
        raise ApiError("not_ready", 409)
    book.status = BookStatus.approved
    book.approved_at = datetime.now(UTC)
    book.approved_by_user_id = admin.id
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.book_approved",
            entity_type="book",
            entity_id=str(book.id),
            data={"flags": list(book.flags or []), "cost_usd": float(book.cost_usd or 0)},
        )
    )
    await db.commit()
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
    for b, t in books:
        pages = [p for p in pages_by_book.get(b.id, []) if p.status != PageStatus.pending]
        cost = float(b.cost_usd or 0)
        costs.append(cost)
        if pages:
            per_page.append(cost / len(pages))
        th = per_theme.setdefault(
            t.slug,
            {
                "slug": t.slug,
                "title": theme_label(t, Locale.ar, ""),
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
    }
