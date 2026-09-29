"""The free cover (Addendum 9): «شوف غلاف طفلك خلال دقيقة».

The parent uses the create flow's own steps for the child, the consent and the photo; this asks for one small
cover of a story, edited from its live Classic cover template and watermarked in the worker. One per account
and story, a few per IP per day, and only while the `free_cover` setting is on. The images are the parent's
own (streamed, never public); sharing sends the drawn cover only, never the photo.
"""

import hashlib
import uuid
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from qamra_ai.pipeline.theme import Theme
from qamra_api import ratelimit, runtime_settings
from qamra_api.auth.router import client_ip
from qamra_api.classic import live_template
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_core.db.classic import FreeCover, FreeCoverStatus
from qamra_core.db.models import Character, Child, ChildPhoto, Consent
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.storage import ObjectNotFound

router = APIRouter(prefix="/api/free-covers", tags=["free-cover"])
JOB = "qamra_worker.jobs.free_cover.draw_free_cover"
PER_IP_PER_DAY = 5
PHOTO_HOURS = 24
STYLE = "watercolor"  # the signature style: the free cover shows the Classic book as sold by default


class FreeCoverIn(BaseModel):
    child_id: uuid.UUID
    theme: str = Field(max_length=64)
    lang: Literal["ar", "en"] = "ar"


class FreeCoverOut(BaseModel):
    id: uuid.UUID
    status: str
    child_id: uuid.UUID
    child_name: str
    theme: str
    ready: bool


async def _out(db: SessionDep, cover: FreeCover) -> FreeCoverOut:
    child = await db.get(Child, cover.child_id)
    theme = await db.get(ThemeRow, cover.theme_id)
    return FreeCoverOut(
        id=cover.id,
        status=cover.status.value,
        child_id=cover.child_id,
        child_name=child.first_name if child else "",
        theme=theme.slug if theme else "",
        ready=cover.status == FreeCoverStatus.ready and bool(cover.image_key),
    )


async def _enabled(db: SessionDep, settings: SettingsDep) -> None:
    if not (await runtime_settings.current(db, settings)).values.get("free_cover"):
        raise ApiError("free_cover_off", 404)


@router.post("", status_code=202)
async def request_cover(
    body: FreeCoverIn,
    request: Request,
    user: CurrentUser,
    db: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    queue: QueueDep,
) -> FreeCoverOut:
    await _enabled(db, settings)
    child = await db.get(Child, body.child_id)
    if child is None or child.guardian_user_id != user.id:
        raise ApiError("not_found", 404)
    consent = await db.scalar(select(func.count()).select_from(Consent).where(Consent.child_id == child.id))
    if not consent:
        raise ApiError("consent_required", 409)
    photos = await db.scalar(
        select(func.count())
        .select_from(ChildPhoto)
        .where(ChildPhoto.child_id == child.id, ChildPhoto.storage_key.is_not(None))
    )
    sheets = await db.scalar(
        select(func.count())
        .select_from(Character)
        .where(Character.child_id == child.id, Character.approved_at.is_not(None))
    )
    if not photos and not sheets:
        raise ApiError("photo_required", 409)
    row = (
        await db.execute(select(ThemeRow).where(ThemeRow.slug == body.theme, ThemeRow.active))
    ).scalar_one_or_none()
    if row is None or not Theme.model_validate(row.definition).available:
        raise ApiError("not_found", 404)
    template = await live_template(db, row.id, STYLE, child)
    if template is None:
        raise ApiError("classic_unavailable", 409)
    cover = (
        await db.execute(select(FreeCover).where(FreeCover.user_id == user.id, FreeCover.theme_id == row.id))
    ).scalar_one_or_none()
    if cover is not None and cover.status != FreeCoverStatus.failed:
        if cover.child_id != child.id:
            raise ApiError("free_cover_used", 409)
        return await _out(db, cover)  # the same child's cover for this story: the one already made
    ip = hashlib.sha256(client_ip(request).encode()).hexdigest()[:24]
    if await ratelimit.hit(redis, f"rl:free-cover:{ip}", 86400) > PER_IP_PER_DAY:
        raise ApiError("too_many_attempts", 429)
    if cover is None:
        cover = FreeCover(user_id=user.id, child_id=child.id, theme_id=row.id)
        db.add(cover)
    # Addendum 9: a free cover's photo is deleted 24 hours after upload (the cleanup job), unless sooner
    for photo in (await db.execute(select(ChildPhoto).where(ChildPhoto.child_id == child.id))).scalars():
        due = photo.created_at + timedelta(hours=PHOTO_HOURS)
        if photo.delete_after is None or photo.delete_after > due:
            photo.delete_after = due
    cover.child_id, cover.template_id, cover.lang = child.id, template.id, body.lang
    cover.status, cover.error, cover.image_key, cover.story_key = FreeCoverStatus.drawing, None, None, None
    await db.commit()
    enqueue(queue, JOB, str(cover.id))
    return await _out(db, cover)


async def _mine(db: SessionDep, user: CurrentUser, cover_id: uuid.UUID) -> FreeCover:
    cover = await db.get(FreeCover, cover_id)
    if cover is None or cover.user_id != user.id:
        raise ApiError("not_found", 404)
    return cover


@router.get("/{cover_id}")
async def cover_status(cover_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> FreeCoverOut:
    return await _out(db, await _mine(db, user, cover_id))


@router.get("/{cover_id}/{name}")
async def cover_image(
    cover_id: uuid.UUID,
    name: Literal["cover.jpg", "story.jpg"],
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
    download: bool = False,
) -> Response:
    """The drawn, watermarked cover (or its story-size copy): never the photo."""
    cover = await _mine(db, user, cover_id)
    key = cover.image_key if name == "cover.jpg" else cover.story_key
    if not key:
        raise ApiError("not_ready", 409)
    try:
        data = storage.get(key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    headers = {"Cache-Control": "private, no-store"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="qamra-{name}"'
    return Response(data, media_type="image/jpeg", headers=headers)
