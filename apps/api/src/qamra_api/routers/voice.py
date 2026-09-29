"""«صوت أهلي» for the parent (design VoiceRecord, VoiceInvite): record per page, invite a grandparent,
pause listening. Only the child's guardian reaches a book here, and only one with the family-voice add-on."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_api import ratelimit
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.voice_common import (
    audio_url,
    has_voice,
    listen_token,
    read_audio,
    recordings,
    save_recording,
    story_pages,
)
from qamra_core import voice
from qamra_core.db.models import Book, Child, Locale, Recording, ShareScope, ShareToken
from qamra_core.db.models import Theme as ThemeRow

router = APIRouter(tags=["voice"])
BOOK = "/api/books/{book_id}/voice"
UPLOADS_PER_HOUR = 200
INVITES_PER_BOOK = 10


class RecordingOut(BaseModel):
    id: uuid.UUID
    voice: str
    duration_ms: int
    audio: str  # a signed same-origin link, valid 10 minutes
    by_invite: bool


class VoicePage(BaseModel):
    beat: int
    text: str
    image: str
    recordings: list[RecordingOut]


class InviteOut(BaseModel):
    id: uuid.UUID
    label: str
    path: str  # the grandparent's page, e.g. /r/<token>
    pages: list[int] | None
    expires_at: datetime | None
    opened_at: datetime | None
    active: bool
    recorded: int  # pages this voice has recorded
    total: int


class VoiceBookOut(BaseModel):
    book_id: uuid.UUID
    title: str
    child_name: str
    language: Locale
    max_voices: int
    voices: list[str]  # names used in this book, first used first
    listening: bool
    listen_url: str  # printed in the QR codes, one per page: <listen_url>/<page>
    pages: list[VoicePage]
    invites: list[InviteOut]


async def _book(db: SessionDep, user: CurrentUser, book_id: uuid.UUID) -> tuple[Book, Child]:
    row = (
        await db.execute(
            select(Book, Child)
            .join(Child, Child.id == Book.child_id)
            .where(Book.id == book_id, Child.guardian_user_id == user.id)
        )
    ).one_or_none()
    if row is None:
        raise ApiError("not_found", 404)  # someone else's book looks exactly like a missing one
    if not await has_voice(db, row[0]):
        raise ApiError("voice_not_included", 403)
    return row[0], row[1]


def invite_out(t: ShareToken, recs: list[Recording], total: int, now: datetime) -> InviteOut:
    live = t.revoked_at is None and (t.expires_at is None or t.expires_at > now)
    done = {r.page_index for r in recs if r.created_by_share_token_id == t.id or r.voice_label == t.label}
    wanted = set(t.pages) if t.pages else None
    return InviteOut(
        id=t.id,
        label=t.label or "",
        path=f"/r/{t.token}",
        pages=t.pages,
        expires_at=t.expires_at,
        opened_at=t.opened_at,
        active=live,
        recorded=len(done & wanted) if wanted is not None else len(done),
        total=len(wanted) if wanted is not None else total,
    )


async def _out(db: SessionDep, settings: SettingsDep, book: Book, child: Child) -> VoiceBookOut:
    secret = settings.jwt_secret.get_secret_value()
    pages, recs = await story_pages(db, book), await recordings(db, book)
    listen = await listen_token(db, book)
    assert listen is not None  # nosec B101 (created on first use)
    invites = (
        await db.execute(
            select(ShareToken)
            .where(ShareToken.book_id == book.id, ShareToken.scope == ShareScope.record)
            .order_by(ShareToken.created_at.desc())
        )
    ).scalars()
    theme = await db.get(ThemeRow, book.theme_id)
    title = book.title or (
        (theme.title_ar if book.language == Locale.ar else theme.title_en) if theme else ""
    )
    now = datetime.now(UTC)
    out = VoiceBookOut(
        book_id=book.id,
        title=title,
        child_name=child.first_name,
        language=book.language,
        max_voices=voice.MAX_VOICES_PER_PAGE,
        voices=list(dict.fromkeys(r.voice_label for r in sorted(recs, key=lambda r: r.created_at))),
        listening=listen.revoked_at is None,
        listen_url=voice.listen_base_url(settings.brand_domain, listen.token),
        pages=[
            VoicePage(
                beat=p.index,
                text=p.text or "",
                image=f"/api/books/{book.id}/reader/pages/{p.index}",
                recordings=[
                    RecordingOut(
                        id=r.id,
                        voice=r.voice_label,
                        duration_ms=r.duration_ms,
                        audio=audio_url(secret, r),
                        by_invite=r.created_by_share_token_id is not None,
                    )
                    for r in recs
                    if r.page_index == p.index
                ],
            )
            for p in pages
        ],
        invites=[invite_out(t, recs, len(pages), now) for t in invites if t.revoked_at is None],
    )
    await db.commit()  # the listening link, when this was the first visit
    return out


@router.get(BOOK)
async def voice_book(
    book_id: uuid.UUID, user: CurrentUser, db: SessionDep, settings: SettingsDep
) -> VoiceBookOut:
    book, child = await _book(db, user, book_id)
    return await _out(db, settings, book, child)


@router.post(BOOK + "/pages/{beat}", status_code=201)
async def record_page(
    book_id: uuid.UUID,
    beat: int,
    user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    voice_name: Annotated[str, Form(alias="voice", max_length=60)],
    duration_ms: Annotated[int, Form(ge=0, le=3_600_000)],
) -> VoiceBookOut:
    """Record (or re-record) one voice on one page. Up to three voices per page."""
    book, child = await _book(db, user, book_id)
    if await ratelimit.hit(redis, f"rl:voice-up:{user.id}", 3600) > UPLOADS_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    if beat not in {p.index for p in await story_pages(db, book)}:
        raise ApiError("not_found", 404)
    try:
        label = voice.clean_label(voice_name)
    except ValueError as e:
        raise ApiError("invalid_label", 422) from e
    audio = await read_audio(file, duration_ms)
    await save_recording(db, storage, book, beat, label, audio, duration_ms, user_id=user.id)
    return await _out(db, settings, book, child)


@router.delete(BOOK + "/recordings/{recording_id}")
async def delete_recording(
    book_id: uuid.UUID,
    recording_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> VoiceBookOut:
    book, child = await _book(db, user, book_id)
    rec = await db.get(Recording, recording_id)
    if rec is None or rec.book_id != book.id:
        raise ApiError("not_found", 404)
    key = rec.storage_key
    await db.delete(rec)
    await db.commit()
    storage.delete(key)
    return await _out(db, settings, book, child)


class InviteIn(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    pages: list[int] | None = Field(default=None, max_length=64)


@router.post(BOOK + "/invites", status_code=201)
async def invite(
    book_id: uuid.UUID,
    body: InviteIn,
    user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> InviteOut:
    """A private recording link for a grandparent: no account, 7 days, revocable."""
    book, _ = await _book(db, user, book_id)
    if await ratelimit.hit(redis, f"rl:voice-invite:{user.id}", 3600) > 30:
        raise ApiError("too_many_attempts", 429)
    try:
        label = voice.clean_label(body.label)
    except ValueError as e:
        raise ApiError("invalid_label", 422) from e
    beats = {p.index for p in await story_pages(db, book)}
    if body.pages is not None and (not body.pages or not set(body.pages) <= beats):
        raise ApiError("invalid_input", 422, details={"fields": ["pages"]})
    now = datetime.now(UTC)
    live = [
        t
        for t in (
            await db.execute(
                select(ShareToken).where(
                    ShareToken.book_id == book.id,
                    ShareToken.scope == ShareScope.record,
                    ShareToken.revoked_at.is_(None),
                )
            )
        ).scalars()
        if t.expires_at is None or t.expires_at > now
    ]
    if len(live) >= INVITES_PER_BOOK:
        raise ApiError("too_many_attempts", 429)
    token = voice.new_invite(book.id, label, body.pages, now)
    db.add(token)
    await db.commit()
    return invite_out(token, [], len(beats), now)


@router.delete(BOOK + "/invites/{invite_id}", status_code=204)
async def revoke_invite(
    book_id: uuid.UUID, invite_id: uuid.UUID, user: CurrentUser, db: SessionDep
) -> Response:
    book, _ = await _book(db, user, book_id)
    token = await db.get(ShareToken, invite_id)
    if token is None or token.book_id != book.id or token.scope != ShareScope.record:
        raise ApiError("not_found", 404)
    token.revoked_at = token.revoked_at or datetime.now(UTC)
    await db.commit()
    return Response(status_code=204)


class ListeningIn(BaseModel):
    on: bool


@router.put(BOOK + "/listening")
async def set_listening(
    book_id: uuid.UUID, body: ListeningIn, user: CurrentUser, db: SessionDep, settings: SettingsDep
) -> VoiceBookOut:
    """Pause or resume the printed QR codes (the link itself never changes: it is printed in the book)."""
    book, child = await _book(db, user, book_id)
    token = await listen_token(db, book)
    assert token is not None  # nosec B101
    token.revoked_at = None if body.on else (token.revoked_at or datetime.now(UTC))
    await db.commit()
    return await _out(db, settings, book, child)


@router.get("/api/voice/books")
async def voice_books(user: CurrentUser, db: SessionDep) -> list[uuid.UUID]:
    """The parent's books bought with the family-voice add-on (the account page shows «سجّلوا أصواتكم»)."""
    rows = await db.execute(
        select(Book.id).join(Child, Child.id == Book.child_id).where(Child.guardian_user_id == user.id)
    )
    return [book_id for book_id in rows.scalars() if (await db.execute(voice.addon_query(book_id))).scalar()]
