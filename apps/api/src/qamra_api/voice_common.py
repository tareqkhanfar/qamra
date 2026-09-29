"""«صوت أهلي» helpers for the owner, grandparent and listener routes (routers/voice*.py).

Audio stays in private storage. Browsers get same-origin API links signed with an HMAC that expires within
10 minutes (the privacy rules allow ≤ 15); the API streams the bytes, with HTTP ranges (Safari needs them).
"""

import hashlib
import hmac
import re
import time
import uuid

from fastapi import Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.errors import MESSAGES, ApiError
from qamra_core import voice
from qamra_core.db.models import Book, BookPage, Recording, SafetyStatus, ShareToken
from qamra_core.storage import ObjectNotFound, ObjectStorage

AUDIO_TTL_SECONDS = 600
RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")

MESSAGES.update(
    {
        "voice_not_included": (
            "هذا الكتاب بلا إضافة «أصوات العائلة». أضيفوها مع الطلب القادم.",
            "This book doesn't have the Family voice add-on.",
        ),
        "voice_limit": (
            "لكل صفحة ثلاثة أصوات على الأكثر. احذفوا صوتًا ثم سجّلوا.",
            "Each page holds up to three voices. Delete one, then record.",
        ),
        "invalid_audio": (
            "تعذّر حفظ التسجيل. سجّلوا مرة أخرى من فضلكم.",
            "We couldn't save the recording. Please record again.",
        ),
        "audio_too_long": (
            "التسجيل طويل جدًّا: الحدّ ثلاث دقائق للصفحة.",
            "The recording is too long: three minutes per page at most.",
        ),
        "invalid_label": ("اكتبوا اسم الصوت (حتى 30 حرفًا).", "Write the voice's name (up to 30 characters)."),
        "invite_unavailable": (
            "انتهت صلاحية رابط التسجيل أو أُلغي. اطلبوا رابطًا جديدًا من العائلة.",
            "This recording link has expired or was cancelled. Ask the family for a new one.",
        ),
        "listen_unavailable": (
            "الاستماع لهذا الكتاب غير متاح الآن.",
            "Listening isn't available for this book right now.",
        ),
    }
)


# ---- signed audio links -----------------------------------------------------------------------------------


def _sig(secret: str, rec_id: uuid.UUID, exp: int) -> str:
    msg = f"voice-audio:{rec_id}:{exp}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()[:32]


def audio_url(secret: str, rec: Recording, now: float | None = None) -> str:
    exp = int((now or time.time()) + AUDIO_TTL_SECONDS)
    return f"/api/voice/audio/{rec.id}?exp={exp}&sig={_sig(secret, rec.id, exp)}"


def audio_ok(secret: str, rec_id: uuid.UUID, exp: int, sig: str, now: float | None = None) -> bool:
    fresh = 0 < exp - (now or time.time()) <= AUDIO_TTL_SECONDS
    return fresh and hmac.compare_digest(sig, _sig(secret, rec_id, exp))


def stream(data: bytes, mime: str, range_header: str | None) -> Response:
    """The whole file, or the byte range asked for (206)."""
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, no-store",
        "Referrer-Policy": "no-referrer",
    }
    m = RANGE.match(range_header or "")
    if not m or not (m[1] or m[2]):
        return Response(data, media_type=mime, headers=headers)
    size = len(data)
    start, end = (int(m[1]), int(m[2] or size - 1)) if m[1] else (max(0, size - int(m[2])), size - 1)
    if start >= size or start > end:
        return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"})
    end = min(end, size - 1)
    headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return Response(data[start : end + 1], status_code=206, media_type=mime, headers=headers)


def recording_bytes(storage: ObjectStorage, rec: Recording) -> tuple[bytes, str]:
    try:
        data = storage.get(rec.storage_key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    return data, voice.EXT_TYPES.get(rec.storage_key.rsplit(".", 1)[-1], "application/octet-stream")


# ---- books, pages and recordings --------------------------------------------------------------------------


async def has_voice(db: AsyncSession, book: Book) -> bool:
    return bool((await db.execute(voice.addon_query(book.id))).scalar())


async def story_pages(db: AsyncSession, book: Book) -> list[BookPage]:
    """The pages a family reads aloud: story pages with text that passed the safety check."""
    rows = await db.execute(select(BookPage).where(BookPage.book_id == book.id).order_by(BookPage.index))
    return [p for p in rows.scalars() if p.index > 0 and p.text and p.safety_status != SafetyStatus.failed]


async def recordings(db: AsyncSession, book: Book) -> list[Recording]:
    rows = await db.execute(
        select(Recording)
        .where(Recording.book_id == book.id)
        .order_by(Recording.page_index, Recording.created_at)
    )
    return list(rows.scalars())


async def listen_token(db: AsyncSession, book: Book, *, create: bool = True) -> ShareToken | None:
    token = (await db.execute(voice.listen_token_query(book.id))).scalar_one_or_none()
    if token is None and create:
        token = voice.new_listen_token(book.id)
        db.add(token)
        await db.flush()
    return token


async def read_audio(file: UploadFile, duration_ms: int) -> tuple[bytes, str]:
    if duration_ms < 300:
        raise ApiError("invalid_audio", 422)
    if duration_ms > voice.MAX_AUDIO_MS:
        raise ApiError("audio_too_long", 422)
    data = await file.read(voice.MAX_AUDIO_BYTES + 1)
    if len(data) > voice.MAX_AUDIO_BYTES:
        raise ApiError("audio_too_long", 413)
    mime = voice.sniff_audio(data)
    if mime is None or len(data) < 200:
        raise ApiError("invalid_audio", 422)
    return data, mime


async def save_recording(
    db: AsyncSession,
    storage: ObjectStorage,
    book: Book,
    page: int,
    label: str,
    audio: tuple[bytes, str],
    duration_ms: int,
    *,
    user_id: uuid.UUID | None = None,
    token_id: uuid.UUID | None = None,
) -> Recording:
    """A new voice on a page, or a re-recording of the same voice (the old file goes after the commit)."""
    data, mime = audio
    on_page = [r for r in await recordings(db, book) if r.page_index == page]
    same = next((r for r in on_page if r.voice_label == label), None)
    if same is None and len(on_page) >= voice.MAX_VOICES_PER_PAGE:
        raise ApiError("voice_limit", 409)
    rec_id = uuid.uuid4()
    key = voice.recording_key(book.child_id, book.id, page, rec_id, voice.AUDIO_TYPES[mime])
    storage.put(key, data, mime)
    old = None
    if same is None:
        rec = Recording(id=rec_id, book_id=book.id, page_index=page, voice_label=label, storage_key=key)
        db.add(rec)
    else:
        rec, old = same, same.storage_key
        rec.storage_key = key
    rec.duration_ms, rec.created_by_user_id, rec.created_by_share_token_id = duration_ms, user_id, token_id
    await db.commit()
    if old:
        storage.delete(old)
    return rec
