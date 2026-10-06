"""The web reader (CLAUDE.md §8) and share links: a finished book (or its preview), page by page.

- The owner (the child's guardian) reads with their session: GET /api/books/{id}/reader. The finished book
  opens once staff confirmed its words (docs/plans/admin-story-text-review.md); until then it is not readable.
- A share link (ShareToken, scope read) opens the finished book without an account: GET /api/shared/{token}.
  It carries the book only (title, page texts, pictures): never the child's id, the parent or the order.
- Pictures stream through the API, so the bucket stays private. Shared views are rate-limited per IP.
"""

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from qamra_api import ratelimit
from qamra_api.auth.router import client_ip
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.theme_versions import book_title
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Child,
    Locale,
    SafetyStatus,
    ShareScope,
    ShareToken,
)
from qamra_core.storage import ObjectNotFound, ObjectStorage

router = APIRouter(prefix="/api", tags=["reader"])
# Final = staff confirmed the words («تأكيد» in the admin review). A book whose files wait in review
# (`in_review`) is neither readable nor shareable yet: its words may still change.
FINAL = (BookStatus.approved, BookStatus.ordered, BookStatus.printed)
READABLE = (BookStatus.preview, *FINAL)
SHARE_DAYS = (7, 30, 90)
SHARES_PER_USER_PER_HOUR = 20
SHARED_VIEWS_PER_IP_PER_HOUR = 120
SHARED_IMAGES_PER_IP_PER_HOUR = 3000
TOKEN = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class ReaderPage(BaseModel):
    beat: int  # 0 = the cover
    text: str | None
    layout: str | None
    image: str | None  # the picture's API path; None for a text-only page


class ReaderOut(BaseModel):
    title: str
    language: Locale
    kind: Literal["preview", "final"]
    pages: list[ReaderPage]


class ShareOut(BaseModel):
    id: uuid.UUID
    token: str
    expires_at: datetime | None
    created_at: datetime


class OwnerReaderOut(ReaderOut):
    id: uuid.UUID
    child_id: uuid.UUID  # the owner's own child: the preview's "continue" link opens the create flow
    child_name: str
    can_share: bool
    share: ShareOut | None


class SharedOut(ReaderOut):
    expires_at: datetime | None


def _kind(book: Book) -> Literal["preview", "final"]:
    return "preview" if book.status == BookStatus.preview else "final"


def _image_key(page: BookPage, kind: str) -> str | None:
    return page.preview_image_key if kind == "preview" else page.image_key


async def _pages(db: SessionDep, book: Book) -> list[BookPage]:
    """What a reader may show: no page that failed the safety check; a preview shows its drawn pages only."""
    kind = _kind(book)
    rows = (
        (await db.execute(select(BookPage).where(BookPage.book_id == book.id).order_by(BookPage.index)))
        .scalars()
        .all()
    )
    return [
        p
        for p in rows
        if p.safety_status != SafetyStatus.failed
        and (_image_key(p, kind) or (kind == "final" and p.index > 0 and p.text))
    ]


async def _title(db: SessionDep, book: Book) -> str:
    return await book_title(db, book)


def _reader_pages(pages: list[BookPage], kind: str, base: str) -> list[ReaderPage]:
    return [
        ReaderPage(
            beat=p.index,
            text=p.text,
            layout=p.layout,
            image=f"{base}/pages/{p.index}?v={int(p.updated_at.timestamp())}"
            if _image_key(p, kind)
            else None,
        )
        for p in pages
    ]


def _mime(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _picture(storage: ObjectStorage, page: BookPage | None, kind: str, cache: str) -> Response:
    key = _image_key(page, kind) if page is not None and page.safety_status != SafetyStatus.failed else None
    if not key:
        raise ApiError("not_found", 404)
    try:
        data = storage.get(key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    return Response(data, media_type=_mime(data), headers={"Cache-Control": cache})


async def _page(db: SessionDep, book: Book, beat: int) -> BookPage | None:
    return (
        await db.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == beat))
    ).scalar_one_or_none()


# ---- the owner ------------------------------------------------------------------------------------------


async def _owned(db: SessionDep, user: CurrentUser, book_id: uuid.UUID) -> tuple[Book, Child]:
    row = (
        await db.execute(
            select(Book, Child)
            .join(Child, Child.id == Book.child_id)
            .where(Book.id == book_id, Child.guardian_user_id == user.id)
        )
    ).one_or_none()
    if row is None:
        raise ApiError("not_found", 404)  # someone else's book looks exactly like a missing one
    return row[0], row[1]


async def _active_share(db: SessionDep, book: Book) -> ShareToken | None:
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(ShareToken)
            .where(
                ShareToken.book_id == book.id,
                ShareToken.scope == ShareScope.read,
                ShareToken.revoked_at.is_(None),
            )
            .order_by(ShareToken.created_at.desc())
        )
    ).scalars()
    return next((t for t in rows if t.expires_at is None or t.expires_at > now), None)


def _share_out(share: ShareToken | None) -> ShareOut | None:
    if share is None:
        return None
    return ShareOut(id=share.id, token=share.token, expires_at=share.expires_at, created_at=share.created_at)


@router.get("/books/{book_id}/reader")
async def read_book(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> OwnerReaderOut:
    book, child = await _owned(db, user, book_id)
    if book.status not in READABLE:
        raise ApiError("book_not_ready", 409)
    kind = _kind(book)
    return OwnerReaderOut(
        id=book.id,
        child_id=child.id,
        child_name=child.first_name,
        title=await _title(db, book),
        language=book.language,
        kind=kind,
        pages=_reader_pages(await _pages(db, book), kind, f"/api/books/{book.id}/reader"),
        can_share=book.status in FINAL,
        share=_share_out(await _active_share(db, book)) if book.status in FINAL else None,
    )


@router.get("/books/{book_id}/reader/pages/{beat}")
async def read_picture(
    book_id: uuid.UUID, beat: int, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    book, _ = await _owned(db, user, book_id)
    if book.status not in READABLE:
        raise ApiError("not_found", 404)
    return _picture(storage, await _page(db, book, beat), _kind(book), "private, max-age=300")


class ShareIn(BaseModel):
    days: Literal[7, 30, 90] = 30


@router.post("/books/{book_id}/share", status_code=201)
async def create_share(
    book_id: uuid.UUID, body: ShareIn, user: CurrentUser, db: SessionDep, redis: RedisDep
) -> ShareOut:
    """A new private link to the finished book; the previous link (if any) stops working."""
    book, _ = await _owned(db, user, book_id)
    if book.status not in FINAL:
        raise ApiError("book_not_ready", 409)
    if await ratelimit.hit(redis, f"rl:share:{user.id}", 3600) > SHARES_PER_USER_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    now = datetime.now(UTC)
    for old in (
        await db.execute(
            select(ShareToken).where(
                ShareToken.book_id == book.id,
                ShareToken.scope == ShareScope.read,
                ShareToken.revoked_at.is_(None),
            )
        )
    ).scalars():
        old.revoked_at = now
    share = ShareToken(
        book_id=book.id,
        token=secrets.token_urlsafe(24),
        scope=ShareScope.read,
        expires_at=now + timedelta(days=body.days),
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    return ShareOut(id=share.id, token=share.token, expires_at=share.expires_at, created_at=share.created_at)


@router.delete("/books/{book_id}/share/{share_id}", status_code=204)
async def revoke_share(
    book_id: uuid.UUID, share_id: uuid.UUID, user: CurrentUser, db: SessionDep
) -> Response:
    book, _ = await _owned(db, user, book_id)
    share = await db.get(ShareToken, share_id)
    if share is None or share.book_id != book.id or share.scope != ShareScope.read:
        raise ApiError("not_found", 404)
    share.revoked_at = share.revoked_at or datetime.now(UTC)
    await db.commit()
    return Response(status_code=204)


# ---- a share link -----------------------------------------------------------------------------------------


async def _shared_book(db: SessionDep, token: str) -> tuple[Book, ShareToken]:
    """The same answer for an unknown, revoked or expired link: it doesn't say which."""
    if not TOKEN.match(token):
        raise ApiError("share_unavailable", 404)
    share = (
        await db.execute(
            select(ShareToken).where(ShareToken.token == token, ShareToken.scope == ShareScope.read)
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if (
        share is None
        or share.revoked_at is not None
        or (share.expires_at is not None and share.expires_at <= now)
    ):
        raise ApiError("share_unavailable", 404)
    book = await db.get(Book, share.book_id)
    if book is None or book.status not in FINAL:
        raise ApiError("share_unavailable", 404)
    return book, share


@router.get("/shared/{token}")
async def read_shared(
    token: str, request: Request, response: Response, db: SessionDep, redis: RedisDep
) -> SharedOut:
    if await ratelimit.hit(redis, f"rl:shared:{client_ip(request)}", 3600) > SHARED_VIEWS_PER_IP_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    book, share = await _shared_book(db, token)
    response.headers.update(NO_STORE)
    return SharedOut(
        title=await _title(db, book),
        language=book.language,
        kind="final",
        pages=_reader_pages(await _pages(db, book), "final", f"/api/shared/{token}"),
        expires_at=share.expires_at,
    )


@router.get("/shared/{token}/pages/{beat}")
async def shared_picture(
    token: str, beat: int, request: Request, db: SessionDep, redis: RedisDep, storage: StorageDep
) -> Response:
    if (
        await ratelimit.hit(redis, f"rl:shared-img:{client_ip(request)}", 3600)
        > SHARED_IMAGES_PER_IP_PER_HOUR
    ):
        raise ApiError("too_many_attempts", 429)
    book, _ = await _shared_book(db, token)
    picture = _picture(storage, await _page(db, book, beat), "final", "private, max-age=300")
    picture.headers["Referrer-Policy"] = "no-referrer"
    return picture
