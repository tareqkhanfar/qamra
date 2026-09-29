"""/api/portal/classes/{id}/book — «كتاب الصف» (Addendum 1 §2, Addendum 4 §1C): one story and one line for
the class, the school page (teacher's message, logo, class photo), the page planner, the batch, the review
and the school's bulk approval. Drawing runs in the worker (`jobs.classbooks.generate_class_book`).
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_ai.pipeline.classbook import class_template_slugs, load_class_template
from qamra_api import runtime_settings
from qamra_api.deps import SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.portal import planning
from qamra_api.portal.access import School, SchoolAdmin, class_book_of, own_classroom
from qamra_api.portal.privacy import thumb_of
from qamra_api.store.catalog import load_catalog
from qamra_api.uploads import clean_image, read_upload
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Classroom,
    Order,
    PageStatus,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.portal import ClassBook, ClassBookPage, ClassBookStatus
from qamra_core.storage import ObjectNotFound

router = APIRouter(prefix="/api/portal/classes", tags=["portal"])
LOCKED = (ClassBookStatus.ordered, ClassBookStatus.printing)
SCHOOL_REDRAWS = 6  # free redraws per class book (pages and covers together)
JOB = "qamra_worker.jobs.classbooks.generate_class_book"
STALE_HOURS = 2  # a running batch commits its progress every picture


class ThemeChoice(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    pages: int


class StyleChoice(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    lines: list[str]


class BookOut(BaseModel):
    exists: bool
    status: str | None
    theme: str | None
    line: str
    style: str
    language: str
    min_appearances: int
    teacher_message: str | None
    class_photo: bool
    class_photo_permission_at: datetime | None
    logo: bool
    ready: int  # children with an approved character in the class style
    children: int
    pages: int
    plan_outdated: bool
    short: list[str]  # names below the minimum appearances
    progress: dict[str, Any]
    flags: list[str]
    redraws_left: int
    order_code: str | None
    themes: list[ThemeChoice]
    styles: list[StyleChoice]


async def _themes(db: SessionDep) -> list[ThemeChoice]:
    slugs = set(class_template_slugs())
    rows = (await db.execute(select(ThemeRow).where(ThemeRow.slug.in_(slugs), ThemeRow.active))).scalars()
    out = []
    for row in rows:
        catalog = (row.definition or {}).get("catalog") or {}
        template = load_class_template(row.slug)
        out.append(
            ThemeChoice(
                slug=row.slug,
                name_ar=str(catalog.get("name_ar") or row.title_ar),
                name_en=str(catalog.get("name_en") or row.title_en),
                pages=sum(not s.extra for s in template.scenes),
            )
        )
    return sorted(out, key=lambda t: t.slug)


async def _styles(db: SessionDep) -> list[StyleChoice]:
    catalog = await load_catalog(db, include_b2b=True)
    return [
        StyleChoice(slug=s.slug, name_ar=s.name_ar, name_en=s.name_en, lines=list(s.lines))
        for s in sorted(catalog.styles.values(), key=lambda x: x.sort)
    ]


async def _refresh_plan(db: SessionDep, settings: SettingsDep, cb: ClassBook, room: Classroom) -> bool:
    """An automatic plan follows the class; a teacher's plan is kept and reported as outdated instead."""
    template = await planning.template_of(db, cb)
    if template is None:
        return False
    ready = [str(c.id) for c in await planning.ready_children(db, room, cb.art_style)]
    if not planning.outdated(cb, template, ready):
        return False
    if (cb.plan or {}).get("manual"):
        return True
    values = (await runtime_settings.current(db, settings)).values
    cb.plan = planning.auto_plan(cb, template, ready, planning.cap_for(values))
    await db.commit()
    return False


async def book_out(db: SessionDep, settings: SettingsDep, school: School, room: Classroom) -> BookOut:
    cb = await class_book_of(db, room)
    children = len((await db.execute(select(Child.id).where(Child.classroom_id == room.id))).all())
    base: dict[str, Any] = {"themes": await _themes(db), "styles": await _styles(db), "children": children}
    if cb is None:
        return BookOut(
            exists=False, status=None, theme=None, line="magic", style="watercolor", language="ar",
            min_appearances=2, teacher_message=None, class_photo=False, class_photo_permission_at=None,
            logo=bool(school.org.logo_key), ready=0, pages=0, plan_outdated=False, short=[], progress={},
            flags=[], redraws_left=SCHOOL_REDRAWS, order_code=None, **base,
        )  # fmt: skip
    outdated = await _refresh_plan(db, settings, cb, room) if cb.status not in LOCKED else False
    ready = await planning.ready_children(db, room, cb.art_style)
    names = {str(c.id): c.first_name for c in ready}
    theme = await db.get(ThemeRow, cb.theme_id) if cb.theme_id else None
    order = await db.get(Order, cb.order_id) if cb.order_id else None
    return BookOut(
        exists=True,
        status=cb.status.value,
        theme=theme.slug if theme else None,
        line=cb.line,
        style=cb.art_style,
        language=cb.language,
        min_appearances=cb.min_appearances,
        teacher_message=cb.teacher_message,
        class_photo=bool(cb.class_photo_key),
        class_photo_permission_at=cb.class_photo_consent_at,
        logo=bool(school.org.logo_key),
        ready=len(ready),
        pages=len((cb.plan or {}).get("pages", [])),
        plan_outdated=outdated,
        short=[names.get(c, "") for c in planning.short(cb) if c in names],
        progress=dict(cb.progress or {}),
        flags=list(cb.flags or []),
        redraws_left=max(0, SCHOOL_REDRAWS - int((cb.generation or {}).get("school_redraws", 0))),
        order_code=order.code if order else None,
        **base,
    )


@router.get("/{classroom_id}/book")
async def get_book(
    classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, settings: SettingsDep
) -> BookOut:
    return await book_out(db, settings, school, await own_classroom(db, school, classroom_id))


class BookIn(BaseModel):
    theme: str | None = Field(default=None, max_length=64)
    line: Literal["classic", "magic"] | None = None
    style: str | None = Field(default=None, max_length=40)
    language: Literal["ar", "en"] | None = None
    min_appearances: int | None = Field(default=None, ge=1, le=6)
    teacher_message: str | None = Field(default=None, max_length=400)


async def editable(db: SessionDep, room: Classroom) -> ClassBook | None:
    """A drawing batch keeps its class book busy; one silent for hours (the queue was down) no longer does."""
    cb = await class_book_of(db, room)
    stale = datetime.now(UTC) - timedelta(hours=STALE_HOURS)
    if cb is not None and cb.status == ClassBookStatus.generating and cb.updated_at > stale:
        raise ApiError("class_book_busy", 409)
    if cb is not None and cb.status in LOCKED:
        raise ApiError("class_book_locked", 409)
    return cb


@router.put("/{classroom_id}/book")
async def setup_book(
    classroom_id: uuid.UUID, body: BookIn, school: SchoolAdmin, db: SessionDep, settings: SettingsDep
) -> BookOut:
    """One story, one line and one art style for the whole class; the school page's message."""
    room = await own_classroom(db, school, classroom_id)
    cb = await editable(db, room)
    if cb is None:
        values = (await runtime_settings.current(db, settings)).values
        cb = ClassBook(
            classroom_id=room.id,
            organization_id=room.organization_id,
            min_appearances=int(values.get("class_book_min_appearances") or 2),
            status=ClassBookStatus.setup,
            options={},
            plan={},
            progress={},
            generation={},
            flags=[],
            bundle={},
        )
        db.add(cb)
    if body.theme is not None:
        theme = (
            await db.execute(select(ThemeRow).where(ThemeRow.slug == body.theme, ThemeRow.active))
        ).scalar_one_or_none()
        if theme is None or body.theme not in class_template_slugs():
            raise ApiError("not_found", 404)
        cb.theme_id = theme.id
    if body.line is not None:
        cb.line = body.line
    if body.style is not None and body.style != cb.art_style:
        catalog = await load_catalog(db, include_b2b=True)
        style = catalog.styles.get(body.style)
        drawn = (
            await db.execute(
                select(Character.id)
                .join(Child, Child.id == Character.child_id)
                .where(Child.classroom_id == room.id, Character.status == CharacterStatus.approved)
            )
        ).first()
        if style is None or cb.line not in style.lines or drawn is not None:
            raise ApiError("invalid_style", 422)  # parents already approved drawings in the current style
        cb.art_style = body.style
    if body.language is not None:
        cb.language = body.language
    if body.min_appearances is not None:
        cb.min_appearances = body.min_appearances
    if body.teacher_message is not None:
        cb.teacher_message = body.teacher_message.strip() or None
    await db.commit()
    return await book_out(db, settings, school, room)


def photo_key(room: Classroom) -> str:
    return f"orgs/{room.organization_id}/classes/{room.id}/class-photo.jpg"


@router.post("/{classroom_id}/book/photo")
async def upload_class_photo(
    classroom_id: uuid.UUID,
    school: SchoolAdmin,
    db: SessionDep,
    settings: SettingsDep,
    storage: StorageDep,
    photo: Annotated[UploadFile, File()],
    permission: Annotated[bool, Form()] = False,
) -> BookOut:
    """The real class photo for the school page, only with the school's confirmation that the parents agreed
    to it being printed. Stored privately, metadata (location) stripped."""
    room = await own_classroom(db, school, classroom_id)
    cb = await editable(db, room)
    if cb is None:
        raise ApiError("theme_required", 409)
    if not permission:
        raise ApiError("photo_permission_required", 422)
    key = photo_key(room)
    storage.put(key, clean_image(await read_upload(photo)), "image/jpeg")
    cb.class_photo_key = key
    cb.class_photo_consent_at, cb.class_photo_consent_by = datetime.now(UTC), school.user.id
    db.add(
        AuditLog(
            actor_user_id=school.user.id,
            action="class_photo.uploaded",
            entity_type="class_book",
            entity_id=str(cb.id),
            data={"parents_permission_confirmed": True},
        )
    )
    await db.commit()
    return await book_out(db, settings, school, room)


@router.delete("/{classroom_id}/book/photo")
async def delete_class_photo(
    classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, settings: SettingsDep, storage: StorageDep
) -> BookOut:
    room = await own_classroom(db, school, classroom_id)
    cb = await editable(db, room)
    if cb is not None and cb.class_photo_key:
        storage.delete(cb.class_photo_key)
        cb.class_photo_key = cb.class_photo_consent_at = cb.class_photo_consent_by = None
        await db.commit()
    return await book_out(db, settings, school, room)


@router.get("/{classroom_id}/book/photo")
async def class_photo(
    classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, storage: StorageDep
) -> Response:
    room = await own_classroom(db, school, classroom_id)
    cb = await class_book_of(db, room)
    if cb is None or not cb.class_photo_key:
        raise ApiError("not_found", 404)
    return Response(
        storage.get(cb.class_photo_key),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store"},
    )


class PlanKid(BaseModel):
    id: str
    name: str


class PlanPage(BaseModel):
    index: int
    key: str
    slots: int
    text: str
    children: list[PlanKid]


class PlanMember(BaseModel):
    id: str
    name: str
    count: int


class PlanOut(BaseModel):
    min_appearances: int
    line: str
    manual: bool
    outdated: bool
    pages: list[PlanPage]
    members: list[PlanMember]


async def plan_out(db: SessionDep, cb: ClassBook, room: Classroom, outdated: bool) -> PlanOut:
    template = await planning.template_of(db, cb)
    if template is None:
        raise ApiError("theme_required", 409)
    plan = cb.plan or {}
    ids = [uuid.UUID(c) for c in plan.get("children") or []]
    names = {
        str(c.id): c.first_name
        for c in (await db.execute(select(Child).where(Child.id.in_(ids)))).scalars()
        if c.classroom_id == room.id
    }
    lang: Literal["ar", "en"] = "ar" if cb.language == "ar" else "en"
    pages = []
    for p in plan.get("pages", []):
        kids = [PlanKid(id=c, name=names[c]) for c in p.get("children") or [] if c in names]
        text = template.page_text(str(p["key"]), lang, [k.name for k in kids], room.name)
        pages.append(
            PlanPage(
                index=int(p["index"]), key=str(p["key"]), slots=int(p["slots"]), text=text, children=kids
            )
        )
    counts = planning.plan_coverage(cb)
    members = sorted(
        (PlanMember(id=c, name=names[c], count=counts.get(c, 0)) for c in names),
        key=lambda m: (m.count, m.name),
    )
    return PlanOut(
        min_appearances=cb.min_appearances,
        line=cb.line,
        manual=bool(plan.get("manual")),
        outdated=outdated,
        pages=pages,
        members=members,
    )


async def _book_with_theme(
    db: SessionDep, school: School, classroom_id: uuid.UUID
) -> tuple[ClassBook, Classroom]:
    room = await own_classroom(db, school, classroom_id)
    cb = await class_book_of(db, room)
    if cb is None or cb.theme_id is None:
        raise ApiError("theme_required", 409)
    return cb, room


@router.get("/{classroom_id}/book/plan")
async def get_plan(
    classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, settings: SettingsDep
) -> PlanOut:
    cb, room = await _book_with_theme(db, school, classroom_id)
    outdated = await _refresh_plan(db, settings, cb, room) if cb.status not in LOCKED else False
    return await plan_out(db, cb, room, outdated)


@router.post("/{classroom_id}/book/plan/auto")
async def auto_plan(
    classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, settings: SettingsDep
) -> PlanOut:
    """«وزّع تلقائيًا»: every ready child the same number of times, spread over the book."""
    cb, room = await _book_with_theme(db, school, classroom_id)
    await editable(db, room)
    template = await planning.template_of(db, cb)
    if template is None:
        raise ApiError("theme_required", 409)
    ready = [str(c.id) for c in await planning.ready_children(db, room, cb.art_style)]
    values = (await runtime_settings.current(db, settings)).values
    cb.plan = planning.auto_plan(cb, template, ready, planning.cap_for(values), seed=None)
    await db.commit()
    return await plan_out(db, cb, room, False)


class PlanPageIn(BaseModel):
    index: int = Field(ge=1, le=99)
    children: list[uuid.UUID] = Field(max_length=6)


class PlanIn(BaseModel):
    pages: list[PlanPageIn] = Field(min_length=1, max_length=99)


@router.put("/{classroom_id}/book/plan")
async def save_plan(classroom_id: uuid.UUID, body: PlanIn, school: SchoolAdmin, db: SessionDep) -> PlanOut:
    """The planner: the teacher moves children between pages (the pages and their places stay)."""
    cb, room = await _book_with_theme(db, school, classroom_id)
    await editable(db, room)
    plan = planning.apply_edits(cb, [planning.PlanEdit(p.index, p.children) for p in body.pages])
    if plan is None:
        raise ApiError("invalid_plan", 422)
    cb.plan = plan
    await db.commit()
    return await plan_out(db, cb, room, False)


@router.post("/{classroom_id}/book/generate", status_code=202)
async def generate(
    classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, settings: SettingsDep, queue: QueueDep
) -> BookOut:
    """«ارسم كتب الصف»: every ready child's copy in one batch. The school approves the result again."""
    cb, room = await _book_with_theme(db, school, classroom_id)
    await editable(db, room)
    if await _refresh_plan(db, settings, cb, room):
        raise ApiError("plan_outdated", 409)
    if not (cb.plan or {}).get("children"):
        raise ApiError("class_not_ready", 409)
    if planning.short(cb):
        raise ApiError("coverage_low", 409)
    cb.status, cb.error = ClassBookStatus.generating, None
    cb.school_approved_at = cb.school_approved_by = None
    cb.progress = {"stage": "queued"}
    db.add(
        AuditLog(
            actor_user_id=school.user.id,
            action="class_book.generate",
            entity_type="class_book",
            entity_id=str(cb.id),
            data={"children": len(cb.plan["children"]), "pages": len(cb.plan.get("pages", []))},
        )
    )
    await db.commit()
    enqueue(queue, JOB, str(cb.id))
    return await book_out(db, settings, school, room)


class ReviewPage(BaseModel):
    index: int
    text: str | None
    children: list[str]  # names
    status: str
    flags: list[str]
    unrecognized: list[str]  # names the check couldn't find or recognize
    image: bool


class ReviewCopy(BaseModel):
    child_id: uuid.UUID
    name: str
    status: str  # waiting | drawing | ready | approved | failed
    cover: bool
    flags: list[str]
    appearances: int
    recognized: int


class ReviewOut(BaseModel):
    status: str
    progress: dict[str, Any]
    pages: list[ReviewPage]
    copies: list[ReviewCopy]
    redraws_left: int
    combined: bool


def _copy_status(cb: ClassBook, book: Book | None, cover: BookPage | None) -> str:
    if book is not None and book.status in (BookStatus.in_review, BookStatus.approved, BookStatus.printed):
        return "approved"
    if book is not None and book.status == BookStatus.preview and book.pdf_interior_key:
        return "ready"
    if cover is not None and cover.status == PageStatus.failed:
        return "failed"
    return "drawing" if cb.status == ClassBookStatus.generating and book is not None else "waiting"


async def copies_of(db: SessionDep, cb: ClassBook) -> dict[str, tuple[Book, BookPage | None]]:
    books = (
        (await db.execute(select(Book).where(Book.generation["class_book_id"].astext == str(cb.id))))
        .scalars()
        .all()
    )
    covers = {
        p.book_id: p
        for p in (
            await db.execute(
                select(BookPage).where(BookPage.book_id.in_([b.id for b in books]), BookPage.index == 0)
            )
        ).scalars()
    }
    return {str(b.child_id): (b, covers.get(b.id)) for b in books}


@router.get("/{classroom_id}/book/review")
async def review(classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep) -> ReviewOut:
    """The batch board and the review: shared pages with who is on them, each child's copy and coverage."""
    cb, room = await _book_with_theme(db, school, classroom_id)
    members = [uuid.UUID(c) for c in (cb.plan or {}).get("children") or []]
    names = {
        str(c.id): c.first_name
        for c in (await db.execute(select(Child).where(Child.id.in_(members)))).scalars()
        if c.classroom_id == room.id
    }
    rows = (
        await db.execute(
            select(ClassBookPage).where(ClassBookPage.class_book_id == cb.id).order_by(ClassBookPage.index)
        )
    ).scalars()
    planned = {int(p["index"]) for p in (cb.plan or {}).get("pages", [])}
    pages = [
        ReviewPage(
            index=r.index,
            text=r.text,
            children=[names.get(c, "") for c in r.child_ids or []],
            status=r.status.value,
            flags=list(r.flags or []),
            unrecognized=[names.get(c, "") for c in (r.qa or {}).get("unrecognized") or []],
            image=bool(r.image_key),
        )
        for r in rows
        if r.index in planned
    ]
    copies = await copies_of(db, cb)
    out = []
    for child_id, name in sorted(names.items(), key=lambda kv: kv[1]):
        book, cover = copies.get(child_id, (None, None))
        summary = (book.qa_summary if book else None) or {}
        out.append(
            ReviewCopy(
                child_id=uuid.UUID(child_id),
                name=name,
                status=_copy_status(cb, book, cover),
                cover=bool(cover and cover.image_key),
                flags=list(book.flags or []) if book else [],
                appearances=int(summary.get("appearances", 0)),
                recognized=int(summary.get("recognized", 0)),
            )
        )
    return ReviewOut(
        status=cb.status.value,
        progress=dict(cb.progress or {}),
        pages=pages,
        copies=out,
        redraws_left=max(0, SCHOOL_REDRAWS - int((cb.generation or {}).get("school_redraws", 0))),
        combined=bool((cb.bundle or {}).get("combined_key")),
    )


def _jpeg(storage: StorageDep, key: str) -> Response:
    try:
        data = storage.get(key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})


@router.get("/{classroom_id}/book/pages/{index}/image")
async def page_image(
    classroom_id: uuid.UUID, index: int, school: SchoolAdmin, db: SessionDep, storage: StorageDep
) -> Response:
    cb, _ = await _book_with_theme(db, school, classroom_id)
    row = (
        await db.execute(
            select(ClassBookPage).where(ClassBookPage.class_book_id == cb.id, ClassBookPage.index == index)
        )
    ).scalar_one_or_none()
    if row is None or not row.image_key:
        raise ApiError("not_found", 404)
    return _jpeg(storage, thumb_of(row.image_key))


async def _copy(
    db: SessionDep, cb: ClassBook, room: Classroom, child_id: uuid.UUID
) -> tuple[Book, BookPage | None]:
    child = await db.get(Child, child_id)
    found = (await copies_of(db, cb)).get(str(child_id))
    if child is None or child.classroom_id != room.id or found is None:
        raise ApiError("not_found", 404)
    return found


@router.get("/{classroom_id}/book/copies/{child_id}/cover")
async def cover_image(
    classroom_id: uuid.UUID, child_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, storage: StorageDep
) -> Response:
    cb, room = await _book_with_theme(db, school, classroom_id)
    _, cover = await _copy(db, cb, room, child_id)
    if cover is None or not cover.image_key:
        raise ApiError("not_found", 404)
    return _jpeg(storage, thumb_of(cover.image_key))


@router.get("/{classroom_id}/book/copies/{child_id}/book.pdf")
async def copy_pdf(
    classroom_id: uuid.UUID, child_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, storage: StorageDep
) -> Response:
    """One child's whole copy (the interior print file), to read before approving."""
    cb, room = await _book_with_theme(db, school, classroom_id)
    book, _ = await _copy(db, cb, room, child_id)
    if not book.pdf_interior_key:
        raise ApiError("not_ready", 409)
    return Response(
        storage.get(book.pdf_interior_key),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline", "Cache-Control": "private, no-store"},
    )


class RedrawIn(BaseModel):
    pages: list[int] = Field(default_factory=list, max_length=SCHOOL_REDRAWS)
    covers: list[uuid.UUID] = Field(default_factory=list, max_length=SCHOOL_REDRAWS)


@router.post("/{classroom_id}/book/redraw", status_code=202)
async def redraw(
    classroom_id: uuid.UUID,
    body: RedrawIn,
    school: SchoolAdmin,
    db: SessionDep,
    settings: SettingsDep,
    queue: QueueDep,
) -> BookOut:
    """«طلب إعادة رسم»: new drawings of chosen pages or covers (a few free ones per class), then the files."""
    cb, room = await _book_with_theme(db, school, classroom_id)
    await editable(db, room)
    wanted = len(set(body.pages)) + len(set(body.covers))
    used = int((cb.generation or {}).get("school_redraws", 0))
    if not wanted:
        raise ApiError("invalid_input", 422)
    if used + wanted > SCHOOL_REDRAWS:
        raise ApiError("class_redraws_used", 429)
    rows = (
        await db.execute(
            select(ClassBookPage).where(
                ClassBookPage.class_book_id == cb.id, ClassBookPage.index.in_(body.pages)
            )
        )
    ).scalars()
    marked = 0
    for row in rows:
        row.redraw, marked = True, marked + 1
    copies = await copies_of(db, cb)
    for child_id in set(body.covers):
        _, cover = copies.get(str(child_id), (None, None))
        if cover is not None:
            cover.review, marked = {**(cover.review or {}), "redraw": True}, marked + 1
    if not marked:
        raise ApiError("not_found", 404)
    cb.generation = {**(cb.generation or {}), "school_redraws": used + marked}
    cb.status, cb.school_approved_at = ClassBookStatus.generating, None
    cb.progress = {"stage": "queued"}
    db.add(
        AuditLog(
            actor_user_id=school.user.id,
            action="class_book.redraw",
            entity_type="class_book",
            entity_id=str(cb.id),
            data={"pages": sorted(set(body.pages)), "covers": len(set(body.covers))},
        )
    )
    await db.commit()
    enqueue(queue, JOB, str(cb.id))
    return await book_out(db, settings, school, room)


class ApproveIn(BaseModel):
    children: list[uuid.UUID] | None = Field(default=None, max_length=100)  # None = every ready copy


@router.post("/{classroom_id}/book/approve")
async def approve(classroom_id: uuid.UUID, body: ApproveIn, school: SchoolAdmin, db: SessionDep) -> ReviewOut:
    """The school's bulk approval: the chosen copies go to our reviewers' queue for print approval."""
    cb, _ = await _book_with_theme(db, school, classroom_id)
    if cb.status not in (ClassBookStatus.review, ClassBookStatus.approved):
        raise ApiError("not_ready", 409)
    members = set((cb.plan or {}).get("children") or [])
    chosen = {str(c) for c in body.children} if body.children is not None else members
    approved = 0
    for child_id, (book, _) in (await copies_of(db, cb)).items():
        if (
            child_id in chosen
            and child_id in members
            and book.status == BookStatus.preview
            and book.pdf_interior_key
        ):
            book.status, approved = BookStatus.in_review, approved + 1
    copies = await copies_of(db, cb)
    if all(c in copies and copies[c][0].status != BookStatus.preview for c in members):
        cb.status = ClassBookStatus.approved
        cb.school_approved_at, cb.school_approved_by = datetime.now(UTC), school.user.id
    db.add(
        AuditLog(
            actor_user_id=school.user.id,
            action="class_book.school_approved",
            entity_type="class_book",
            entity_id=str(cb.id),
            data={"copies": approved},
        )
    )
    await db.commit()
    return await review(classroom_id, school, db)
