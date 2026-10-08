"""Digital delivery for parents (docs/plans/digital-delivery.md): the PDFs of the lines they bought as files.

- GET  /api/downloads[?order=QM-…]                         the parent's downloadable lines and their files
- GET  /api/downloads/{item}                               one line (the order page's button)
- POST /api/downloads/{item}/files/{book}/{kind}           make sure the home copy exists → ready | preparing
- GET  /api/downloads/{item}/files/{book}/{kind}           the copy's state → ready | preparing | failed
- GET  /api/downloads/{item}/files/{book}/{kind}/pdf       the file (attachment, UTF-8 name + ASCII fallback)

What is downloadable and when: `qamra_core.downloads`. Only the owning parent: the child's guardian, on an
order placed from their account (or as a guest). Someone else's line is 403; a line that isn't there is 404.

The file is a home-print copy without the printer's bleed, made once by the worker (`jobs.downloads`) and kept
under the child's storage prefix, so «حذف كل بيانات طفلي» removes it with everything else. It streams through
the API (the bucket stays private; no storage URL ever reaches the browser). Each download is in the audit log
with ids only.
"""

import uuid
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from rq import Queue
from sqlalchemy import ColumnElement, or_, select

from qamra_api import ratelimit
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, StorageDep
from qamra_api.errors import ApiError
from qamra_core import downloads as dl
from qamra_core.db.models import AuditLog, Book, Child, Order, OrderItem, User
from qamra_core.storage import ObjectNotFound, ObjectStorage

router = APIRouter(prefix="/api/downloads", tags=["downloads"])
PDF_QUEUE = "pdf"
PREPARE_JOB = "qamra_worker.jobs.downloads.prepare_file"
PREPARING_SECONDS = 15 * 60  # a copy asked for and not made by then can be asked for again
PREPARES_PER_USER_PER_HOUR = 120
FILES_PER_USER_PER_HOUR = 60
NO_STORE = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
Lang = Literal["ar", "en"]
Kind = Literal["book", "answer-key", "stickers", "card-money-recipes", "card-games-roles"]


class FileOut(BaseModel):
    book_id: uuid.UUID
    kind: Kind
    part: str  # V1…V5, R (islamic), 1–3 (journey stage, workbook volume); "" for a single book
    level: str  # kg1 / kg2 («دوسية التأسيس»), else ""
    name: str  # the name it downloads under


class LineOut(BaseModel):
    item_id: uuid.UUID
    order_code: str
    placed_at: str
    child_id: uuid.UUID
    child_name: str
    line: str
    sku: str | None
    name_ar: str
    name_en: str
    options: dict[str, str]
    book_title: str | None
    status: Literal["ready", "preparing"]  # ready: every book of the line can be downloaded
    parts_total: int
    parts_ready: int
    files: list[FileOut]  # the files of the books that are ready (a set: each volume as soon as it is)


class FileState(BaseModel):
    status: Literal["ready", "preparing", "failed"]
    name: str
    url: str | None = None  # the file, once ready


# ---- loading -----------------------------------------------------------------------------------------------


def _mine(user: User) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
    """The parent's lines: their child, on their order or a guest order (the guest checked out signed out)."""
    return (
        Child.guardian_user_id == user.id,
        or_(Order.user_id == user.id, Order.user_id.is_(None)),
    )


async def _books(db: SessionDep, items: list[OrderItem]) -> list[Book]:
    query = dl.books_query(items)
    return list((await db.execute(query)).scalars()) if query is not None else []


def _line_out(item: OrderItem, order: Order, child: Child, books: list[Book], lang: Lang) -> LineOut:
    state = dl.line_state(item, order.status, books)
    mine = [b for b in books if dl.owned_by(b, item)]
    files = [
        FileOut(
            book_id=f.book_id,
            kind=f.kind,  # type: ignore[arg-type]
            part=f.part,
            level=f.level,
            name=dl.file_name(item, order.code, f, state.books[f.book_id], child.first_name, lang)[0],
        )
        for f in state.files
    ]
    return LineOut(
        item_id=item.id,
        order_code=order.code,
        placed_at=order.created_at.isoformat(),
        child_id=child.id,
        child_name=child.first_name,
        line=str(item.line),
        sku=item.sku,
        name_ar=str((item.title or {}).get("name_ar") or ""),
        name_en=str((item.title or {}).get("name_en") or ""),
        options=dl.options_of(item),
        book_title=next((b.title for b in mine if b.title), None) if item.line in dl.STORY_LINES else None,
        status="ready" if state.ready else "preparing",
        parts_total=state.parts_total,
        parts_ready=state.parts_ready,
        files=files,
    )


async def _line(db: SessionDep, user: User, item_id: uuid.UUID) -> tuple[OrderItem, Order, Child, list[Book]]:
    """One of the parent's lines: 404 when it doesn't exist or offers no file, 403 when it isn't theirs."""
    row = (
        await db.execute(
            select(OrderItem, Order, Child)
            .join(Order, Order.id == OrderItem.order_id)
            .outerjoin(Child, Child.id == OrderItem.child_id)
            .where(OrderItem.id == item_id)
        )
    ).one_or_none()
    if row is None:
        raise ApiError("not_found", 404)
    item, order, child = row
    if child is None or order.status not in dl.LISTED_ORDERS:
        raise ApiError("not_found", 404)  # the child's data was deleted, or the order was cancelled
    if child.guardian_user_id != user.id or order.user_id not in (user.id, None):
        raise ApiError("download_not_yours", 403)
    if not dl.offers_download(item.line, dl.options_of(item)):
        raise ApiError("not_found", 404)
    return item, order, child, await _books(db, [item])


def _lang(user: User, lang: Lang | None) -> Lang:
    return lang or ("en" if user.locale.value == "en" else "ar")


# ---- the lines ---------------------------------------------------------------------------------------------


@router.get("")
async def my_downloads(
    user: CurrentUser, db: SessionDep, order: str | None = None, lang: Lang | None = None
) -> list[LineOut]:
    """Every line the parent can download from (ready or still being made), newest order first."""
    query = (
        select(OrderItem, Order, Child)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Child, Child.id == OrderItem.child_id)
        .where(*_mine(user), Order.status.in_(dl.LISTED_ORDERS))
        .order_by(Order.created_at.desc(), OrderItem.id)
    )
    if order:
        query = query.where(Order.code == order.strip().upper())
    rows = [
        (i, o, c)
        for i, o, c in (await db.execute(query)).all()
        if dl.offers_download(i.line, dl.options_of(i))
    ]
    books = await _books(db, [i for i, _, _ in rows])
    return [_line_out(i, o, c, books, _lang(user, lang)) for i, o, c in rows]


@router.get("/{item_id}")
async def one_line(
    item_id: uuid.UUID, user: CurrentUser, db: SessionDep, lang: Lang | None = None
) -> LineOut:
    item, order, child, books = await _line(db, user, item_id)
    return _line_out(item, order, child, books, _lang(user, lang))


# ---- one file ----------------------------------------------------------------------------------------------


class _File:
    def __init__(
        self, item: OrderItem, order: Order, child: Child, book: Book, ref: dl.FileRef, lang: Lang
    ) -> None:
        self.item, self.order, self.child, self.book, self.ref = item, order, child, book, ref
        self.name, self.fallback = dl.file_name(item, order.code, ref, book, child.first_name, lang)
        self.url = f"/api/downloads/{item.id}/files/{book.id}/{ref.kind}/pdf?lang={lang}"

    def version(self, storage: ObjectStorage) -> str:
        sources = dl.sources_of(self.book, self.ref.kind)
        etags = [storage.etag(k) for k in sources]
        if not sources or any(e is None for e in etags):
            raise ApiError("download_not_ready", 409)  # the print files are missing: not made yet
        return dl.version_of([e for e in etags if e])


async def _file(
    db: SessionDep, user: User, item_id: uuid.UUID, book_id: uuid.UUID, kind: Kind, lang: Lang | None
) -> _File:
    item, order, child, books = await _line(db, user, item_id)
    book = next((b for b in books if b.id == book_id and dl.owned_by(b, item)), None)
    if book is None or kind not in dl.kinds_of(item.line, dl.is_digital(dl.options_of(item)), book):
        raise ApiError("not_found", 404)  # not this line's book, or a file the line doesn't include
    ref = dl.find_file(dl.line_state(item, order.status, books), book_id, kind)
    if ref is None:  # not ready yet (a story before staff confirmed its words, a render still running)
        raise ApiError("download_not_ready", 409)
    return _File(item, order, child, book, ref, _lang(user, lang))


async def _limit(redis: RedisDep, key: str, per_hour: int) -> None:
    if await ratelimit.hit(redis, key, 3600) > per_hour:
        raise ApiError("too_many_attempts", 429)


@router.post("/{item_id}/files/{book_id}/{kind}")
async def prepare(
    item_id: uuid.UUID,
    book_id: uuid.UUID,
    kind: Kind,
    request: Request,
    user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
    lang: Lang | None = None,
) -> FileState:
    """The home copy: ready now, or asked of the worker (once; a failed copy is asked for again)."""
    await _limit(redis, f"rl:dl-prep:{user.id}", PREPARES_PER_USER_PER_HOUR)
    f = await _file(db, user, item_id, book_id, kind, lang)
    version = f.version(storage)
    if storage.exists(dl.home_key(f.book, kind, version)):
        return FileState(status="ready", name=f.name, url=f.url)
    await redis.delete(dl.state_key(book_id, kind, version, "failed"))
    if await redis.set(dl.state_key(book_id, kind, version, "prep"), "1", nx=True, ex=PREPARING_SECONDS):
        Queue(PDF_QUEUE, connection=request.app.state.rq_redis).enqueue(
            PREPARE_JOB, str(book_id), kind, job_timeout=600
        )
    return FileState(status="preparing", name=f.name)


@router.get("/{item_id}/files/{book_id}/{kind}")
async def file_state(
    item_id: uuid.UUID,
    book_id: uuid.UUID,
    kind: Kind,
    user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
    lang: Lang | None = None,
) -> FileState:
    """Where a copy asked for with POST stands: ready, still being made, or failed (POST again to retry)."""
    f = await _file(db, user, item_id, book_id, kind, lang)
    version = f.version(storage)
    if storage.exists(dl.home_key(f.book, kind, version)):
        return FileState(status="ready", name=f.name, url=f.url)
    if await redis.exists(dl.state_key(book_id, kind, version, "prep")):
        return FileState(status="preparing", name=f.name)
    return FileState(status="failed", name=f.name)  # it failed, or nobody is making it any more


@router.get("/{item_id}/files/{book_id}/{kind}/pdf")
async def download(
    item_id: uuid.UUID,
    book_id: uuid.UUID,
    kind: Kind,
    user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
    lang: Lang | None = None,
) -> StreamingResponse:
    await _limit(redis, f"rl:dl-file:{user.id}", FILES_PER_USER_PER_HOUR)
    f = await _file(db, user, item_id, book_id, kind, lang)
    key = dl.home_key(f.book, kind, f.version(storage))
    try:
        chunks, size = storage.stream(key)
    except ObjectNotFound as e:
        raise ApiError("download_preparing", 409) from e
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="download.file",
            entity_type="order_item",
            entity_id=str(f.item.id),
            data={"order": str(f.order.id), "book": str(f.book.id), "kind": kind},
        )
    )
    await db.commit()
    headers = {
        **NO_STORE,
        "Content-Disposition": f"attachment; filename=\"{f.fallback}\"; filename*=UTF-8''{quote(f.name)}",
    }
    if size:
        headers["Content-Length"] = str(size)
    return StreamingResponse(chunks, media_type="application/pdf", headers=headers)
