"""«صوت أهلي» without an account (design VoiceElder, VoiceListen):

- a grandparent's recording link (ShareToken scope `record`): 7 days, revocable, only the pages it covers;
- the page a printed QR opens (scope `listen`): the picture, the text and the family's voices;
- signed audio links (≤ 10 minutes), and the narrator fallback when a TTS provider is switched on.

Unknown, expired and revoked links get the same answer. Nothing here returns ids of the child or the parent;
only the book's own guardian, signed in, gets the link to its recording page (`record`).
"""

import re
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from qamra_ai.tts import TTSLang, make_tts
from qamra_api import ratelimit, runtime_settings
from qamra_api.auth.router import client_ip
from qamra_api.deps import OptionalUser, RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.theme_versions import book_title
from qamra_api.voice_common import (
    audio_ok,
    audio_url,
    read_audio,
    recording_bytes,
    recordings,
    save_recording,
    story_pages,
    stream,
)
from qamra_core import voice
from qamra_core.db.models import Book, BookPage, Child, Locale, Recording, ShareScope, ShareToken
from qamra_core.storage import ObjectNotFound

router = APIRouter(prefix="/api/voice", tags=["voice"])
TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex"}
VIEWS_PER_IP_PER_HOUR = 600
AUDIO_PER_IP_PER_HOUR = 3000
ELDER_UPLOADS_PER_HOUR = 120


async def _token(db: SessionDep, token: str, scope: ShareScope, missing: str) -> tuple[ShareToken, Book]:
    if not TOKEN.match(token):
        raise ApiError(missing, 404)
    row = (
        await db.execute(select(ShareToken).where(ShareToken.token == token, ShareToken.scope == scope))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if row is None or row.revoked_at is not None or (row.expires_at is not None and row.expires_at <= now):
        raise ApiError(missing, 404)
    book = await db.get(Book, row.book_id)
    if book is None:
        raise ApiError(missing, 404)
    return row, book


async def _title(db: SessionDep, book: Book) -> str:
    return await book_title(db, book)


async def _limit(redis: RedisDep, request: Request, name: str, most: int) -> None:
    if await ratelimit.hit(redis, f"rl:{name}:{client_ip(request)}", 3600) > most:
        raise ApiError("too_many_attempts", 429)


# ---- a grandparent's recording link ------------------------------------------------------------------------


class ElderPage(BaseModel):
    beat: int
    text: str
    audio: str | None  # this voice's recording of the page, when there is one


class ElderOut(BaseModel):
    label: str
    child_name: str
    title: str
    language: Locale
    expires_at: datetime | None
    pages: list[ElderPage]


async def _elder_out(db: SessionDep, settings: SettingsDep, invite: ShareToken, book: Book) -> ElderOut:
    child = await db.get(Child, book.child_id)
    secret = settings.jwt_secret.get_secret_value()
    mine = {r.page_index: r for r in await recordings(db, book) if r.voice_label == invite.label}
    wanted = set(invite.pages) if invite.pages else None
    pages = [p for p in await story_pages(db, book) if wanted is None or p.index in wanted]
    return ElderOut(
        label=invite.label or "",
        child_name=child.first_name if child else "",
        title=await _title(db, book),
        language=book.language,
        expires_at=invite.expires_at,
        pages=[
            ElderPage(
                beat=p.index,
                text=p.text or "",
                audio=audio_url(secret, mine[p.index]) if p.index in mine else None,
            )
            for p in pages
        ],
    )


@router.get("/invites/{token}")
async def elder_book(
    token: str, request: Request, response: Response, db: SessionDep, redis: RedisDep, settings: SettingsDep
) -> ElderOut:
    await _limit(redis, request, "voice-elder", VIEWS_PER_IP_PER_HOUR)
    invite, book = await _token(db, token, ShareScope.record, "invite_unavailable")
    if invite.opened_at is None:
        invite.opened_at = datetime.now(UTC)  # the parent sees «فتح الرابط»
        await db.commit()
    response.headers.update(NO_STORE)
    return await _elder_out(db, settings, invite, book)


@router.post("/invites/{token}/pages/{beat}", status_code=201)
async def elder_record(
    token: str,
    beat: int,
    request: Request,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    duration_ms: Annotated[int, Form(ge=0, le=3_600_000)],
) -> ElderOut:
    invite, book = await _token(db, token, ShareScope.record, "invite_unavailable")
    if await ratelimit.hit(redis, f"rl:voice-elder-up:{invite.id}", 3600) > ELDER_UPLOADS_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    allowed = {p.index for p in await story_pages(db, book)}
    if beat not in allowed or (invite.pages and beat not in invite.pages):
        raise ApiError("not_found", 404)
    audio = await read_audio(file, duration_ms)
    label = invite.label or "صوت"
    await save_recording(db, storage, book, beat, label, audio, duration_ms, token_id=invite.id)
    return await _elder_out(db, settings, invite, book)


# ---- the page a printed QR opens ---------------------------------------------------------------------------


class ListenVoice(BaseModel):
    label: str
    audio: str
    duration_ms: int


class ListenOut(BaseModel):
    title: str
    language: Locale
    beat: int
    number: int  # 1-based position among the story pages
    total: int
    prev: int | None
    next: int | None
    text: str
    image: str | None
    voices: list[ListenVoice]
    narrator: str | None  # the TTS fallback's audio link, only without recordings and with a provider on
    # the book's recording page at this page, only for its guardian signed in (anyone else gets None)
    record: str | None = None


async def _listen_page(db: SessionDep, token: str, beat: int) -> tuple[ShareToken, Book, list[BookPage], int]:
    listen, book = await _token(db, token, ShareScope.listen, "listen_unavailable")
    pages = await story_pages(db, book)
    at = next((i for i, p in enumerate(pages) if p.index == beat), None)
    if at is None:
        raise ApiError("not_found", 404)
    return listen, book, pages, at


@router.get("/listen/{token}/{beat}")
async def listen(
    token: str,
    beat: int,
    request: Request,
    response: Response,
    db: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    user: OptionalUser,
) -> ListenOut:
    await _limit(redis, request, "voice-listen", VIEWS_PER_IP_PER_HOUR)
    _, book, pages, at = await _listen_page(db, token, beat)
    child = await db.get(Child, book.child_id) if user is not None else None
    owner = child is not None and user is not None and child.guardian_user_id == user.id
    page, secret = pages[at], settings.jwt_secret.get_secret_value()
    recs = [r for r in await recordings(db, book) if r.page_index == beat]
    values = (await runtime_settings.current(db, settings)).values
    narrator = None
    if not recs and make_tts(str(values.get("tts_provider") or "none")) is not None:
        narrator = f"/api/voice/listen/{token}/{beat}/narrator"
    response.headers.update(NO_STORE)
    return ListenOut(
        title=await _title(db, book),
        language=book.language,
        beat=beat,
        number=at + 1,
        total=len(pages),
        prev=pages[at - 1].index if at > 0 else None,
        next=pages[at + 1].index if at + 1 < len(pages) else None,
        text=page.text or "",
        image=f"/api/voice/listen/{token}/{beat}/image" if page.image_key else None,
        voices=[
            ListenVoice(label=r.voice_label, audio=audio_url(secret, r), duration_ms=r.duration_ms)
            for r in recs
        ],
        narrator=narrator,
        record=f"/books/{book.id}/voice?page={beat}" if owner else None,
    )


@router.get("/listen/{token}/{beat}/image")
async def listen_image(
    token: str, beat: int, request: Request, db: SessionDep, redis: RedisDep, storage: StorageDep
) -> Response:
    """The page's small picture (the worker's 520 px thumbnail), else the drawn image."""
    await _limit(redis, request, "voice-img", AUDIO_PER_IP_PER_HOUR)
    _, book, pages, at = await _listen_page(db, token, beat)
    thumb = f"children/{book.child_id}/books/{book.id}/thumb/{beat:02d}.jpg"  # worker: jobs/books.page_key
    for key in (thumb, pages[at].image_key):
        if not key:
            continue
        try:
            data = storage.get(key)
        except ObjectNotFound:
            continue
        mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
        return Response(data, media_type=mime, headers={**NO_STORE, "Cache-Control": "private, max-age=600"})
    raise ApiError("not_found", 404)


@router.get("/listen/{token}/{beat}/narrator")
async def narrator(
    token: str,
    beat: int,
    request: Request,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> Response:
    """The TTS fallback, made once per page and kept with the book's files (deleted with the child's data)."""
    await _limit(redis, request, "voice-tts", VIEWS_PER_IP_PER_HOUR)
    _, book, pages, at = await _listen_page(db, token, beat)
    values = (await runtime_settings.current(db, settings)).values
    tts = make_tts(str(values.get("tts_provider") or "none"))
    if tts is None:
        raise ApiError("not_found", 404)
    lang: TTSLang = "ar" if book.language == Locale.ar else "en"
    key = voice.tts_key(book.child_id, book.id, beat, tts.name, "wav")
    try:
        data = storage.get(key)
    except ObjectNotFound:
        speech = await tts.speak(text=pages[at].text or "", lang=lang, step=f"tts:{beat}")
        data = speech.audio
        storage.put(key, data, speech.mime)
    return stream(data, "audio/wav", request.headers.get("range"))


@router.get("/audio/{recording_id}")
async def audio(
    recording_id: uuid.UUID,
    exp: int,
    sig: str,
    request: Request,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> Response:
    """A recording through its signed link (≤ 10 minutes), for the owner, the grandparent and listeners."""
    await _limit(redis, request, "voice-audio", AUDIO_PER_IP_PER_HOUR)
    if not audio_ok(settings.jwt_secret.get_secret_value(), recording_id, exp, sig[:64]):
        raise ApiError("not_found", 404)
    rec = await db.get(Recording, recording_id)
    if rec is None:
        raise ApiError("not_found", 404)
    data, mime = recording_bytes(storage, rec)
    return stream(data, mime, request.headers.get("range"))


class ListenStart(BaseModel):
    first: int
    language: Locale


@router.get("/listen/{token}")
async def listen_start(
    token: str, request: Request, response: Response, db: SessionDep, redis: RedisDep
) -> ListenStart:
    """The back cover's QR has no page: it opens the first story page."""
    await _limit(redis, request, "voice-listen", VIEWS_PER_IP_PER_HOUR)
    _, book = await _token(db, token, ShareScope.listen, "listen_unavailable")
    pages = await story_pages(db, book)
    if not pages:
        raise ApiError("listen_unavailable", 404)
    response.headers.update(NO_STORE)
    return ListenStart(first=pages[0].index, language=book.language)
