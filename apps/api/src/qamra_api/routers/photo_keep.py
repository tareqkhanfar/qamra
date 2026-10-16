"""«احتفظوا بالصورة»: the guardian's optional choice to keep the child's original photo for later books
(owner, 2026-10-16; the rules are in qamra_core.photo_keep).

Off by default and never pre-ticked: it is its own versioned consent (scope `photo_keep`, with time, IP
and user agent), offered on the photo step and in «أطفالي», where it can be turned off again. While it is
on, the cleanup leaves the photo alone until `kept_photo_retention_months` after its last use; turning it
off schedules the deletion within `photo_retention_hours`. «احذفوا الصورة الآن» deletes the originals at
once (and ends the choice); "delete all my child's data" removes everything, the choice included. Only the
guardian, as everywhere in the create flow.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from qamra_api import runtime_settings
from qamra_api.consent import record_consent
from qamra_api.deps import CurrentUser, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.routers.create import _my_child
from qamra_core.db.models import AuditLog, Child, ChildPhoto, Consent, PhotoStatus
from qamra_core.photo_keep import (
    KEEP_CONSENT_VERSION,
    KEEP_SCOPE,
    RETENTION_SETTING,
    kept_until,
    schedule_after_opt_out,
)

router = APIRouter(prefix="/api/create", tags=["create"])


class KeptPhotoOut(BaseModel):
    id: uuid.UUID
    # when the cleanup deletes it as things stand: a kept photo, its retention after the last use; otherwise
    # its 24-hour date (None: not set yet, i.e. 24 hours after the character's approval)
    deletes_at: datetime | None


class KeepOut(BaseModel):
    keep: bool
    since: datetime | None  # when the guardian chose it
    version: str  # the text version to send when turning it on
    months: int  # the kept photo's retention after its last use (admin setting)
    photo: KeptPhotoOut | None  # the newest original we still hold


class KeepIn(BaseModel):
    keep: bool
    version: str | None = Field(default=None, max_length=32)  # required to turn it on


async def _active(db: SessionDep, child: Child) -> list[Consent]:
    rows = await db.execute(
        select(Consent)
        .where(Consent.child_id == child.id, Consent.scope == KEEP_SCOPE, Consent.withdrawn_at.is_(None))
        .order_by(Consent.accepted_at)
    )
    return list(rows.scalars())


async def _live_photos(db: SessionDep, child: Child) -> list[ChildPhoto]:
    rows = await db.execute(
        select(ChildPhoto)
        .where(ChildPhoto.child_id == child.id, ChildPhoto.storage_key.is_not(None))
        .order_by(ChildPhoto.created_at.desc(), ChildPhoto.id)
    )
    return list(rows.scalars())


async def _out(db: SessionDep, settings: SettingsDep, child: Child) -> KeepOut:
    resolved = (await runtime_settings.current(db, settings)).values
    months = int(resolved[RETENTION_SETTING])
    active = await _active(db, child)
    photos = await _live_photos(db, child)
    photo = None
    if photos:
        newest = photos[0]
        photo = KeptPhotoOut(
            id=newest.id, deletes_at=kept_until(newest, months) if active else newest.delete_after
        )
    return KeepOut(
        keep=bool(active),
        since=active[0].accepted_at if active else None,
        version=KEEP_CONSENT_VERSION,
        months=months,
        photo=photo,
    )


@router.get("/children/{child_id}/photo-keep")
async def photo_keep(
    child_id: uuid.UUID, response: Response, user: CurrentUser, db: SessionDep, settings: SettingsDep
) -> KeepOut:
    response.headers["Cache-Control"] = "private, no-store"
    return await _out(db, settings, await _my_child(db, user, child_id))


@router.put("/children/{child_id}/photo-keep")
async def set_photo_keep(
    child_id: uuid.UUID,
    body: KeepIn,
    request: Request,
    user: CurrentUser,
    db: SessionDep,
    settings: SettingsDep,
) -> KeepOut:
    """On: records the choice's consent (the text version the page showed) and starts the retention from now.
    Off: takes the choice back and schedules the originals' deletion within `photo_retention_hours`."""
    child = await _my_child(db, user, child_id)
    resolved = (await runtime_settings.current(db, settings)).values
    now = datetime.now(UTC)
    active = await _active(db, child)
    if body.keep:
        if body.version != KEEP_CONSENT_VERSION:
            raise ApiError("consent_outdated", 409)  # the page showed another text: reload it
        processing = await db.scalar(
            select(func.count())
            .select_from(Consent)
            .where(Consent.child_id == child.id, Consent.scope != KEEP_SCOPE)
        )
        if not processing:
            raise ApiError("consent_required", 409)  # the photo consent comes first
        if not active:
            record_consent(
                db,
                request,
                user_id=user.id,
                child_id=child.id,
                version=KEEP_CONSENT_VERSION,
                scope=KEEP_SCOPE,
                data={"months": int(resolved[RETENTION_SETTING])},
            )
            for photo in await _live_photos(db, child):
                photo.last_used_at = now  # the retention counts from the choice
    elif active:
        for consent in active:
            consent.withdrawn_at = now
        hours = int(resolved["photo_retention_hours"])
        for photo in await _live_photos(db, child):
            schedule_after_opt_out(photo, now, hours)
        db.add(
            AuditLog(
                actor_user_id=user.id,
                action="consent.withdrawn",
                entity_type="child",
                entity_id=str(child.id),
                data={"scope": KEEP_SCOPE},
            )
        )
    await db.commit()
    return await _out(db, settings, child)


@router.delete("/children/{child_id}/photos", status_code=204)
async def delete_photos(
    child_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    """«احذفوا الصورة الآن»: the child's originals, now (the drawings and books stay). The keep choice ends
    with them; a later upload asks again."""
    child = await _my_child(db, user, child_id)
    now = datetime.now(UTC)
    photos = await _live_photos(db, child)
    for photo in photos:
        storage.delete(str(photo.storage_key))  # storage first: a crash leaves a row to retry, never a file
        photo.storage_key, photo.crop, photo.status, photo.deleted_at = None, None, PhotoStatus.deleted, now
    for consent in await _active(db, child):
        consent.withdrawn_at = now
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="photo.deleted_by_guardian",
            entity_type="child",
            entity_id=str(child.id),
            data={"photos": len(photos)},
        )
    )
    await db.commit()
    return Response(status_code=204)
