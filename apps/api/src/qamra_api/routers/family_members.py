"""The illustrated-family add-on (Addendum 7 §7): up to four of the child's family drawn as characters from
their photos, with the child's privacy rules. For each person the parent gives consent (a versioned text,
with the time and IP), uploads one photo (checked for one clear face, re-encoded, private), asks for a drawing
(the approved providers only; 3 redraws) and approves it; the photo is deleted 24 h after approval and the
character is reused by every family book of the child. Behind the setting `family_characters_enabled` (off).
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, File, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from qamra_api import ratelimit, runtime_settings
from qamra_api.auth.router import client_ip
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.routers.create import UPLOADS_PER_HOUR, _my_child
from qamra_api.store.catalog import load_catalog
from qamra_api.store.workbooks import FamilyMemberIn
from qamra_api.uploads import clean_image, read_upload, require_face
from qamra_core.db.models import AuditLog, Character, FamilyMember, FamilyMemberStatus

router = APIRouter(prefix="/api/create", tags=["create"])
CONSENT_VERSION = "family-member-2026-09"  # the text shown for each person (messages: create.familyConsent)
MAX_MEMBERS = 4  # the add-on draws up to four (content/store/catalog.yaml: family-characters)
MAX_DRAWINGS = 4  # the first drawing and 3 free redraws, as for the child
JOB = "qamra_worker.jobs.family_members.generate_member"


class MemberOut(BaseModel):
    id: uuid.UUID
    relation: str
    first_name: str
    adult: bool
    scarf: bool
    consented: bool
    has_photo: bool
    status: FamilyMemberStatus
    approved: bool
    drawings_left: int


def _out(m: FamilyMember) -> MemberOut:
    return MemberOut(
        id=m.id,
        relation=m.relation,
        first_name=m.first_name,
        adult=m.adult,
        scarf=m.scarf,
        consented=m.consented_at is not None,
        has_photo=m.photo_key is not None,
        status=m.status,
        approved=m.approved_at is not None,
        drawings_left=max(0, MAX_DRAWINGS - m.regen_count),
    )


async def _enabled(db: SessionDep, settings: SettingsDep) -> None:
    if not (await runtime_settings.current(db, settings)).values.get("family_characters_enabled"):
        raise ApiError("family_characters_off", 409)


async def _member(db: SessionDep, user: CurrentUser, member_id: uuid.UUID) -> FamilyMember:
    member = await db.get(FamilyMember, member_id)
    if member is None or member.guardian_user_id != user.id:
        raise ApiError("not_found", 404)
    await _my_child(db, user, member.child_id)
    return member


@router.get("/children/{child_id}/family")
async def list_members(child_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> list[MemberOut]:
    child = await _my_child(db, user, child_id)
    rows = await db.execute(
        select(FamilyMember).where(FamilyMember.child_id == child.id).order_by(FamilyMember.created_at)
    )
    return [_out(m) for m in rows.scalars()]


@router.post("/children/{child_id}/family", status_code=201)
async def add_member(
    child_id: uuid.UUID, body: FamilyMemberIn, user: CurrentUser, db: SessionDep, settings: SettingsDep
) -> MemberOut:
    await _enabled(db, settings)
    child = await _my_child(db, user, child_id)
    count = await db.scalar(
        select(func.count()).select_from(FamilyMember).where(FamilyMember.child_id == child.id)
    )
    if (count or 0) >= MAX_MEMBERS:
        raise ApiError("invalid_input", 422, {"fields": ["members"], "max": MAX_MEMBERS})
    adult = body.adult if body.adult is not None else body.relation not in ("brother", "sister", "baby")
    member = FamilyMember(
        child_id=child.id,
        guardian_user_id=user.id,
        relation=body.relation,
        first_name=body.name,
        adult=adult,
        scarf=body.scarf,
        status=FamilyMemberStatus.draft,
        regen_count=0,
        params={},
    )
    db.add(member)
    await db.commit()
    return _out(member)


class ConsentIn(BaseModel):
    accept: Literal[True]
    version: str = Field(max_length=32)


@router.post("/family/{member_id}/consent")
async def give_consent(
    member_id: uuid.UUID, body: ConsentIn, request: Request, user: CurrentUser, db: SessionDep
) -> MemberOut:
    """The parent's consent to process this person's photo (they confirm they may give it)."""
    member = await _member(db, user, member_id)
    if body.version != CONSENT_VERSION:
        raise ApiError("consent_outdated", 409)
    member.consent_version, member.consented_at = CONSENT_VERSION, datetime.now(UTC)
    member.consent_ip = client_ip(request)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="family_member.consent",
            entity_type="family_member",
            entity_id=str(member.id),
            data={"version": CONSENT_VERSION},
        )
    )
    await db.commit()
    return _out(member)


@router.post("/family/{member_id}/photo")
async def upload_photo(
    member_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
    redis: RedisDep,
    settings: SettingsDep,
    photo: Annotated[UploadFile, File()],
) -> MemberOut:
    await _enabled(db, settings)
    member = await _member(db, user, member_id)
    if await ratelimit.hit(redis, f"rl:photos:{user.id}", 3600) > UPLOADS_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    if member.consented_at is None:
        raise ApiError("consent_required", 409)
    data = clean_image(await read_upload(photo))
    require_face(data)
    if member.photo_key:
        storage.delete(member.photo_key)  # a new photo replaces the old one at once
    member.photo_key = f"children/{member.child_id}/family/{member.id}/photo.jpg"
    storage.put(member.photo_key, data, "image/jpeg")
    retention = int((await runtime_settings.current(db, settings)).values["photo_retention_hours"])
    approved = member.approved_at is not None  # a new photo of an approved member: deleted on schedule
    member.photo_delete_after = datetime.now(UTC) + timedelta(hours=retention) if approved else None
    await db.commit()
    return _out(member)


class DrawIn(BaseModel):
    style: str | None = Field(default=None, max_length=40)  # none: the child's own character's style


async def _child_style(db: SessionDep, child_id: uuid.UUID) -> str | None:
    """The style of the child's approved character, so the family is drawn like the child (3D with 3D)."""
    return await db.scalar(
        select(Character.art_style)
        .where(Character.child_id == child_id, Character.approved_at.is_not(None))
        .order_by(Character.approved_at.desc())
        .limit(1)
    )


@router.post("/family/{member_id}/draw", status_code=202)
async def draw_member(
    member_id: uuid.UUID,
    body: DrawIn,
    user: CurrentUser,
    db: SessionDep,
    settings: SettingsDep,
    queue: QueueDep,
) -> MemberOut:
    await _enabled(db, settings)
    member = await _member(db, user, member_id)
    style = body.style or await _child_style(db, member.child_id) or "3d"
    if style not in (await load_catalog(db)).styles:
        raise ApiError("invalid_style", 422)
    if not member.photo_key:
        raise ApiError("photo_required", 409)
    if member.regen_count >= MAX_DRAWINGS:
        raise ApiError("redraws_used", 429)
    member.regen_count += 1
    member.art_style, member.status, member.approved_at = style, FamilyMemberStatus.generating, None
    await db.commit()
    enqueue(queue, JOB, str(member.id))
    return _out(member)


@router.get("/family/{member_id}/image")
async def member_image(
    member_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    member = await _member(db, user, member_id)
    if not member.sheet_key:
        raise ApiError("not_ready", 409)
    return Response(
        storage.get(member.sheet_key), media_type="image/png", headers={"Cache-Control": "private, no-store"}
    )


@router.post("/family/{member_id}/approve")
async def approve_member(
    member_id: uuid.UUID, user: CurrentUser, db: SessionDep, settings: SettingsDep
) -> MemberOut:
    member = await _member(db, user, member_id)
    if member.status not in (FamilyMemberStatus.ready, FamilyMemberStatus.approved) or not member.sheet_key:
        raise ApiError("not_ready", 409)
    now = datetime.now(UTC)
    member.status, member.approved_at = FamilyMemberStatus.approved, member.approved_at or now
    retention = int((await runtime_settings.current(db, settings)).values["photo_retention_hours"])
    if member.photo_key:
        member.photo_delete_after = member.photo_delete_after or now + timedelta(
            hours=retention
        )  # CLAUDE.md §3.1
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="family_member.approved",
            entity_type="family_member",
            entity_id=str(member.id),
        )
    )
    await db.commit()
    return _out(member)


@router.delete("/family/{member_id}", status_code=204)
async def delete_member(
    member_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    """Forget this person now: their photo, drawings and record."""
    member = await _member(db, user, member_id)
    storage.delete_prefix(f"children/{member.child_id}/family/{member.id}/")  # files first
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="family_member.deleted",
            entity_type="family_member",
            entity_id=str(member.id),
        )
    )
    await db.delete(member)
    await db.commit()
    return Response(status_code=204)
