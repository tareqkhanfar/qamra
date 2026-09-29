"""/api/portal/classes/{id} — a class's children: the status board, the import from CSV, the invite links.

Each imported child gets one tokenized, expiring invite link for their parent. The parent opens it, signs in
and gives consent and the photo themselves (`routers/invite.py`); the school only sees the steps' states.
A child whose parent already accepted belongs to that parent: removing them only takes them out of the class.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, File, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_api import runtime_settings
from qamra_api.deps import SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.portal.access import SchoolAdmin, class_book_of, own_child, own_classroom
from qamra_api.portal.importer import MAX_CHILDREN, check_row, decode, parse_csv, preview, template_csv
from qamra_api.portal.status import (
    ChildState,
    class_states,
    invite_state,
    mask_email,
    mask_phone,
    stage_counts,
)
from qamra_api.uploads import read_upload
from qamra_core.db.models import AuditLog, Child, Classroom, Gender
from qamra_core.db.portal import ChildInvite

router = APIRouter(prefix="/api/portal/classes", tags=["portal"])


class InviteOut(BaseModel):
    path: str | None  # /invite/{token}: the web adds the origin and the language
    state: str  # none | ready | sent | claimed | expired
    expires_at: datetime | None


class ChildRow(BaseModel):
    id: uuid.UUID
    name: str
    gender: str
    age: int
    parent_name: str | None
    phone: str | None  # masked
    email: str | None  # masked
    stage: str
    steps: dict[str, bool]
    drawn: bool  # a character waits for the parent's approval
    character_id: uuid.UUID | None  # approved, in the class book's style (the drawing, never the photo)
    invite: InviteOut
    last_activity: datetime | None


class ClassDetail(BaseModel):
    id: uuid.UUID
    name: str
    teacher_name: str | None
    school_year: str | None
    stages: dict[str, int]
    children: list[ChildRow]
    book_status: str | None
    book_line: str | None
    art_style: str | None


def child_row(s: ChildState) -> ChildRow:
    invite = s.invite
    state = invite_state(invite)
    return ChildRow(
        id=s.child.id,
        name=s.child.first_name,
        gender=s.child.gender.value,
        age=s.age,
        parent_name=invite.parent_name if invite else None,
        phone=mask_phone(invite.parent_phone) if invite else None,
        email=mask_email(invite.parent_email) if invite else None,
        stage=s.stage,
        steps={
            "invited": s.invited,
            "consent": s.consent,
            "photo": s.photo,
            "drawing": s.drawing,
            "approved": s.character is not None,
        },
        drawn=s.drawn,
        character_id=s.character.id if s.character else None,
        invite=InviteOut(
            path=f"/invite/{invite.token}" if invite and state in ("ready", "sent") else None,
            state=state,
            expires_at=invite.expires_at if invite else None,
        ),
        last_activity=s.last,
    )


async def class_detail(db: SessionDep, room: Classroom) -> ClassDetail:
    cb = await class_book_of(db, room)
    states = await class_states(db, room, cb.art_style if cb else None)
    return ClassDetail(
        id=room.id,
        name=room.name,
        teacher_name=room.teacher_name,
        school_year=room.school_year,
        stages=stage_counts(states),
        children=[child_row(s) for s in states],
        book_status=cb.status.value if cb else None,
        book_line=cb.line if cb else None,
        art_style=cb.art_style if cb else None,
    )


@router.get("/{classroom_id}")
async def get_class(classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep) -> ClassDetail:
    return await class_detail(db, await own_classroom(db, school, classroom_id))


@router.get("/{classroom_id}/template.csv")
async def list_template(classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep) -> Response:
    await own_classroom(db, school, classroom_id)
    return Response(
        template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="qamra-class-list.csv"'},
    )


class PreviewOut(BaseModel):
    rows: list[dict[str, Any]]
    ok: int
    warnings: int
    errors: int


@router.post("/{classroom_id}/import/preview")
async def import_preview(
    classroom_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, file: Annotated[UploadFile, File()]
) -> PreviewOut:
    """The school's list, checked row by row; nothing is saved yet."""
    room = await own_classroom(db, school, classroom_id)
    name = (file.filename or "").lower()
    if name.endswith((".xlsx", ".xls", ".ods", ".numbers")):
        raise ApiError("import_format", 422)
    try:
        rows = parse_csv(decode(await read_upload(file)))
    except ValueError as e:
        raise ApiError("import_format", 422) from e
    if not rows:
        raise ApiError("import_empty", 422)
    existing = [
        c.first_name for c in (await db.execute(select(Child).where(Child.classroom_id == room.id))).scalars()
    ]
    if len(rows) + len(existing) > MAX_CHILDREN:
        raise ApiError("import_too_many", 422, {"max": MAX_CHILDREN})
    checked = preview(rows, existing)
    return PreviewOut(
        rows=[r.out() for r in checked],
        ok=sum(r.ok and not r.warnings for r in checked),
        warnings=sum(r.ok and bool(r.warnings) for r in checked),
        errors=sum(not r.ok for r in checked),
    )


class ImportIn(BaseModel):
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=MAX_CHILDREN)


class ImportOut(BaseModel):
    created: int
    skipped: list[dict[str, Any]]  # rows that still have errors, with their reasons
    detail: ClassDetail


def new_invite(child: Child, room: Classroom, days: int, contact: dict[str, Any]) -> ChildInvite:
    return ChildInvite(
        child_id=child.id,
        organization_id=room.organization_id,
        classroom_id=room.id,
        token=secrets.token_urlsafe(24),
        parent_name=contact.get("parent_name"),
        parent_phone=contact.get("phone"),
        parent_email=contact.get("email"),
        expires_at=datetime.now(UTC) + timedelta(days=days),
    )


@router.post("/{classroom_id}/import")
async def import_children(
    classroom_id: uuid.UUID, body: ImportIn, school: SchoolAdmin, db: SessionDep, settings: SettingsDep
) -> ImportOut:
    """The rows the school confirmed (checked again here), each child with its parent's invite link."""
    room = await own_classroom(db, school, classroom_id)
    existing = len((await db.execute(select(Child.id).where(Child.classroom_id == room.id))).all())
    if existing + len(body.rows) > MAX_CHILDREN:
        raise ApiError("import_too_many", 422, {"max": MAX_CHILDREN})
    days = int((await runtime_settings.current(db, settings)).values.get("portal_invite_days") or 30)
    created, skipped = 0, []
    for i, values in enumerate(body.rows):
        row = check_row(values, int(values.get("row") or i + 2))
        if not row.ok or row.gender is None or row.birth_year is None:
            skipped.append(row.out())
            continue
        child = Child(
            organization_id=room.organization_id,
            classroom_id=room.id,
            first_name=row.name,
            gender=Gender(row.gender),
            birth_year=row.birth_year,
        )
        db.add(child)
        await db.flush()
        db.add(
            new_invite(
                child, room, days, {"parent_name": row.parent_name, "phone": row.phone, "email": row.email}
            )
        )
        created += 1
    db.add(
        AuditLog(
            actor_user_id=school.user.id,
            action="portal.children_imported",
            entity_type="classroom",
            entity_id=str(room.id),
            data={"created": created, "skipped": len(skipped)},
        )
    )
    await db.commit()
    return ImportOut(created=created, skipped=skipped, detail=await class_detail(db, room))


@router.delete("/{classroom_id}/children/{child_id}")
async def remove_child(
    classroom_id: uuid.UUID, child_id: uuid.UUID, school: SchoolAdmin, db: SessionDep
) -> ClassDetail:
    """Before the parent accepts, the school's row is deleted; afterwards the child (and everything the
    parent made) stays the parent's, and only leaves the class."""
    room = await own_classroom(db, school, classroom_id)
    child = await own_child(db, room, child_id)
    cb = await class_book_of(db, room)
    if cb is not None and cb.status.value in ("ordered", "printing"):
        raise ApiError("class_book_locked", 409)
    invite = (
        await db.execute(select(ChildInvite).where(ChildInvite.child_id == child.id))
    ).scalar_one_or_none()
    if child.guardian_user_id is None:
        await db.delete(child)  # the invite goes with it
    else:
        child.classroom_id = child.organization_id = None
        if invite is not None:
            await db.delete(invite)
    db.add(
        AuditLog(
            actor_user_id=school.user.id,
            action="portal.child_removed",
            entity_type="child",
            entity_id=str(child_id),
            data={"claimed": child.guardian_user_id is not None},
        )
    )
    await db.commit()
    return await class_detail(db, room)


class SentIn(BaseModel):
    children: list[uuid.UUID] = Field(min_length=1, max_length=MAX_CHILDREN)


@router.post("/{classroom_id}/invites/sent")
async def invites_sent(
    classroom_id: uuid.UUID, body: SentIn, school: SchoolAdmin, db: SessionDep
) -> ClassDetail:
    """The school copied or shared these links (WhatsApp from its own phone): the board shows «مدعو»."""
    room = await own_classroom(db, school, classroom_id)
    now = datetime.now(UTC)
    for invite in (
        await db.execute(
            select(ChildInvite).where(
                ChildInvite.classroom_id == room.id, ChildInvite.child_id.in_(body.children)
            )
        )
    ).scalars():
        invite.sent_at = invite.sent_at or now
    await db.commit()
    return await class_detail(db, room)


@router.post("/{classroom_id}/children/{child_id}/invite")
async def renew_invite(
    classroom_id: uuid.UUID, child_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, settings: SettingsDep
) -> ClassDetail:
    """A new link (the old one stops working): for an expired or lost link, before the parent accepts."""
    room = await own_classroom(db, school, classroom_id)
    child = await own_child(db, room, child_id)
    invite = (
        await db.execute(select(ChildInvite).where(ChildInvite.child_id == child.id))
    ).scalar_one_or_none()
    if child.guardian_user_id is not None or (invite is not None and invite.claimed_at is not None):
        raise ApiError("invite_claimed", 409)
    days = int((await runtime_settings.current(db, settings)).values.get("portal_invite_days") or 30)
    if invite is None:
        db.add(new_invite(child, room, days, {}))
    else:
        invite.token = secrets.token_urlsafe(24)
        invite.expires_at = datetime.now(UTC) + timedelta(days=days)
        invite.revoked_at = invite.sent_at = None
    await db.commit()
    return await class_detail(db, room)


@router.get("/{classroom_id}/children/{child_id}/character")
async def character_image(
    classroom_id: uuid.UUID, child_id: uuid.UUID, school: SchoolAdmin, db: SessionDep, storage: StorageDep
) -> Response:
    """The parent-approved drawing that will appear in the class book (never a photo)."""
    room = await own_classroom(db, school, classroom_id)
    await own_child(db, room, child_id)
    cb = await class_book_of(db, room)
    states = {s.child.id: s for s in await class_states(db, room, cb.art_style if cb else None)}
    state = states.get(child_id)
    if state is None or state.character is None or not state.character.sheet_image_key:
        raise ApiError("not_found", 404)
    return Response(
        storage.get(state.character.sheet_image_key),
        media_type="image/png",
        headers={"Cache-Control": "private, no-store"},
    )
