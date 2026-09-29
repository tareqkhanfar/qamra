"""The audio QR codes of «رحلتي الأولى للتعلّم» (Addendum 6 §4.8).

Public, no account and no child data (the QR opens `https://{BRAND_DOMAIN}/a/{code}`):
- `GET /api/a/{code}`: the item for the player (its title, the words or letters it shows, and a signed audio
  link when it has a recording, or when the TTS fallback is switched on and the item may be read aloud);
- `GET /api/a/{code}/audio?exp&sig`: the audio through its signed link (≤ 10 minutes), with HTTP ranges.

Staff (`journey.audio`: editors and owners): the items of a stage with their recordings, and upload/replace.
Until an item has audio the player shows its words, with no error.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from qamra_ai.tts import TTSProvider, make_tts
from qamra_api import journey_audio as catalog
from qamra_api import ratelimit, runtime_settings
from qamra_api.auth.router import client_ip
from qamra_api.deps import RedisDep, SessionDep, SettingsDep, StorageDep, require_permission
from qamra_api.errors import ApiError
from qamra_api.voice_common import read_audio, stream
from qamra_core import voice
from qamra_core.db.audio import AudioClip, clip_key
from qamra_core.db.models import AuditLog, User
from qamra_core.storage import ObjectNotFound

router = APIRouter(prefix="/api/a", tags=["journey-audio"])
admin_router = APIRouter(prefix="/api/admin/journey/audio", tags=["journey-audio"])
Staff = Annotated[User, Depends(require_permission("journey.audio"))]
NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex"}
VIEWS_PER_IP_PER_HOUR = 600
AUDIO_PER_IP_PER_HOUR = 3000


async def _limit(redis: RedisDep, request: Request, name: str, most: int) -> None:
    if await ratelimit.hit(redis, f"rl:{name}:{client_ip(request)}", 3600) > most:
        raise ApiError("too_many_attempts", 429)


async def _narrator(db: SessionDep, settings: SettingsDep, item: dict[str, Any]) -> TTSProvider | None:
    """The TTS fallback, for items that may be read aloud (words and letters), when a provider is on."""
    if not item.get("tts"):
        return None
    values = (await runtime_settings.current(db, settings)).values
    return make_tts(str(values.get("tts_provider") or "none"))


def _item(code: str) -> dict[str, Any]:
    found = catalog.item(code)
    if found is None:
        raise ApiError("audio_item_unknown", 404)
    return found


class PlayerOut(BaseModel):
    code: str
    lang: str
    title: str
    show: list[str]
    audio: str | None  # a signed link, or none yet (the player shows the words)
    source: Literal["recording", "narrator"] | None


@router.get("/{code}")
async def player(
    code: str, request: Request, response: Response, db: SessionDep, redis: RedisDep, settings: SettingsDep
) -> PlayerOut:
    await _limit(redis, request, "audio-item", VIEWS_PER_IP_PER_HOUR)
    item = _item(code)
    clip = await db.get(AudioClip, code)
    secret = settings.jwt_secret.get_secret_value()
    audio: str | None = None
    source: Literal["recording", "narrator"] | None = None
    if clip is not None:
        audio, source = (
            catalog.audio_link(secret, code),
            "recording" if clip.source == "upload" else "narrator",
        )
    elif await _narrator(db, settings, item) is not None:
        audio, source = catalog.audio_link(secret, code), "narrator"
    response.headers.update(NO_STORE)
    return PlayerOut(
        code=code, lang=item["lang"], title=item["title"], show=list(item["show"]), audio=audio, source=source
    )


@router.get("/{code}/audio")
async def audio(
    code: str,
    exp: int,
    sig: str,
    request: Request,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> Response:
    """The item's recording (or its narration, made once and kept) through its signed link."""
    await _limit(redis, request, "audio-file", AUDIO_PER_IP_PER_HOUR)
    if not catalog.link_ok(settings.jwt_secret.get_secret_value(), code, exp, sig[:64]):
        raise ApiError("not_found", 404)
    item = _item(code)
    clip = await db.get(AudioClip, code)
    if clip is None:
        tts = await _narrator(db, settings, item)
        if tts is None:
            raise ApiError("not_found", 404)
        speech = await tts.speak(text=str(item["say"]), lang=item["lang"], step=f"tts:journey:{code}")
        key = clip_key(code, f"tts-{tts.name}", "wav")
        storage.put(key, speech.audio, speech.mime)
        clip = AudioClip(code=code, storage_key=key, mime=speech.mime, duration_ms=speech.duration_ms)
        clip.source = f"tts:{tts.name}"
        db.add(clip)
        try:
            await db.commit()
        except IntegrityError:  # another request made it first
            await db.rollback()
            clip = await db.get(AudioClip, code)
            if clip is None:
                raise ApiError("not_found", 404) from None
    try:
        data = storage.get(clip.storage_key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    return stream(data, clip.mime, request.headers.get("range"))


# ---- staff: the recordings of a stage ----------------------------------------------------------------------


class ClipOut(BaseModel):
    code: str
    stage: int
    page: int
    title: str
    say: str
    show: list[str]
    lang: str
    tts: bool
    url: str  # what the printed QR opens
    has_audio: bool
    source: str | None
    duration_ms: int | None
    updated_at: datetime | None
    audio: str | None  # a signed link to play it


class ClipsOut(BaseModel):
    stage: int
    stages: list[int]
    items: list[ClipOut]


def _out(item: dict[str, Any], clip: AudioClip | None, secret: str, domain: str) -> ClipOut:
    return ClipOut(
        code=item["code"],
        stage=int(item["stage"]),
        page=int(item["page"]),
        title=item["title"],
        say=item["say"],
        show=list(item["show"]),
        lang=item["lang"],
        tts=bool(item.get("tts")),
        url=catalog.public_url(domain, item["code"]),
        has_audio=clip is not None,
        source=clip.source if clip else None,
        duration_ms=clip.duration_ms if clip else None,
        updated_at=clip.updated_at if clip else None,
        audio=catalog.audio_link(secret, item["code"]) if clip else None,
    )


@admin_router.get("")
async def stage_clips(
    staff: Staff, db: SessionDep, settings: SettingsDep, stage: Annotated[int, Query(ge=1, le=3)] = 1
) -> ClipsOut:
    items = catalog.catalog().values()
    secret = settings.jwt_secret.get_secret_value()
    out = []
    for it in sorted((i for i in items if int(i["stage"]) == stage), key=lambda i: int(i["page"])):
        out.append(_out(it, await db.get(AudioClip, it["code"]), secret, settings.brand_domain))
    return ClipsOut(stage=stage, stages=sorted({int(i["stage"]) for i in items}), items=out)


@admin_router.post("/{code}")
async def upload_clip(
    code: str,
    staff: Staff,
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    duration_ms: Annotated[int, Form(ge=0, le=3_600_000)],
) -> ClipOut:
    """Upload a recording for an item, or replace it (the old file goes after the commit)."""
    item = _item(code)
    data, mime = await read_audio(file, duration_ms)
    key = clip_key(code, uuid.uuid4().hex, voice.AUDIO_TYPES[mime])
    storage.put(key, data, mime)
    clip = await db.get(AudioClip, code)
    old = clip.storage_key if clip is not None else None
    if clip is None:
        clip = AudioClip(code=code, storage_key=key, mime=mime)
        db.add(clip)
    clip.storage_key, clip.mime, clip.duration_ms = key, mime, duration_ms
    clip.source, clip.uploaded_by_user_id = "upload", staff.id
    db.add(
        AuditLog(
            actor_user_id=staff.id,
            action="journey.audio_uploaded",
            entity_type="audio",
            entity_id=code,
            data={"replaced": old is not None, "bytes": len(data), "mime": mime},
        )
    )
    await db.commit()
    await db.refresh(clip)
    if old and old != key:
        storage.delete(old)
    return _out(item, clip, settings.jwt_secret.get_secret_value(), settings.brand_domain)
