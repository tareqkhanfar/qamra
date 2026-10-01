"""/api/invite/{token} — the parent's side of a kindergarten invite link (CLAUDE.md §8).

The parent opens the link the school sent, signs in (or creates an account), and the child the school listed
becomes theirs: they are its guardian from then on, with every right of the create flow, including "delete
all my child's data". Consent, the photo, the character and its approval then use the create flow's own
handlers and checks; only the consent text (it also covers the class book) and the art style (the class's)
come from the invite. The school never sees the photo, only the steps' states.
"""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_ai.pipeline.theme import fill_title
from qamra_api import ratelimit
from qamra_api.auth.router import client_ip
from qamra_api.consent import record_consent
from qamra_api.deps import CurrentUser, OptionalUser, RedisDep, SessionDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep
from qamra_api.routers import create
from qamra_core.db.models import AuditLog, Child, Classroom, Organization, UserRole
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.portal import ChildInvite, ClassBook

router = APIRouter(prefix="/api/invite", tags=["invite"])
INVITE_CONSENT_VERSION = "school-2026-09"  # the text on the invite page (messages: invite.consent)
LOOKUPS_PER_IP_PER_HOUR = 60
DEFAULT_STYLE = "watercolor"


class InviteOut(BaseModel):
    state: Literal["open", "mine", "taken", "expired"]
    school: str
    classroom: str
    child_name: str
    child_gender: Literal["m", "f"]  # the page's wording agrees with the child («ابنكم»/«ابنتكم»)
    theme_ar: str | None
    theme_en: str | None
    style: str
    consent_version: str
    child: create.ChildOut | None  # only for the parent who accepted


async def _invite(db: SessionDep, token: str) -> tuple[ChildInvite, Child]:
    invite = (
        await db.execute(select(ChildInvite).where(ChildInvite.token == token[:64]))
    ).scalar_one_or_none()
    child = await db.get(Child, invite.child_id) if invite else None
    if invite is None or child is None:
        raise ApiError("not_found", 404)
    return invite, child


def _expired(invite: ChildInvite) -> bool:
    return invite.claimed_at is None and (
        invite.revoked_at is not None or invite.expires_at <= datetime.now(UTC)
    )


async def _class_book(db: SessionDep, invite: ChildInvite) -> ClassBook | None:
    return (
        await db.execute(select(ClassBook).where(ClassBook.classroom_id == invite.classroom_id))
    ).scalar_one_or_none()


@router.get("/{token}")
async def open_invite(
    token: str, request: Request, db: SessionDep, redis: RedisDep, user: OptionalUser
) -> InviteOut:
    """What the parent sees before signing in: the school, the class and the child's first name."""
    if await ratelimit.hit(redis, f"rl:invite:{client_ip(request)}", 3600) > LOOKUPS_PER_IP_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    invite, child = await _invite(db, token)
    mine = user is not None and child.guardian_user_id == user.id
    state: Literal["open", "mine", "taken", "expired"] = (
        "mine" if mine else "taken" if invite.claimed_at else "expired" if _expired(invite) else "open"
    )
    return await _out(db, invite, child, state)


async def _mine(db: SessionDep, user: CurrentUser, token: str) -> tuple[ChildInvite, Child]:
    invite, child = await _invite(db, token)
    if child.guardian_user_id != user.id:
        raise ApiError("not_found", 404)
    return invite, child


@router.post("/{token}/claim")
async def claim(token: str, request: Request, user: CurrentUser, db: SessionDep) -> InviteOut:
    """The signed-in parent accepts: the child becomes theirs. A link works for one account only."""
    invite, child = await _invite(db, token)
    if child.guardian_user_id != user.id:
        if user.role != UserRole.parent:
            raise ApiError("forbidden", 403)  # a school or staff account can't become a guardian by link
        if invite.claimed_at is not None or child.guardian_user_id is not None:
            raise ApiError("invite_claimed", 409)
        if _expired(invite):
            raise ApiError("invite_expired", 410)
        child.guardian_user_id = user.id
        invite.claimed_at, invite.claimed_by_user_id = datetime.now(UTC), user.id
        db.add(
            AuditLog(
                actor_user_id=user.id, action="invite.claimed", entity_type="child", entity_id=str(child.id)
            )
        )
        await db.commit()
    return await _out(db, invite, child, "mine")


async def _out(
    db: SessionDep, invite: ChildInvite, child: Child, state: Literal["open", "mine", "taken", "expired"]
) -> InviteOut:
    room = await db.get(Classroom, invite.classroom_id)
    org = await db.get(Organization, invite.organization_id)
    cb = await _class_book(db, invite)
    theme = await db.get(ThemeRow, cb.theme_id) if cb and cb.theme_id else None
    gender: Literal["m", "f"] = "f" if child.gender.value == "f" else "m"
    catalog = ((theme.definition or {}).get("catalog") or {}) if theme else {}
    return InviteOut(
        state=state,
        school=org.name if org else "",
        classroom=room.name if room else "",
        child_name=child.first_name,
        child_gender=gender,
        theme_ar=str(catalog.get("name_ar") or fill_title(theme.title_ar, child.first_name, gender))
        if theme
        else None,
        theme_en=str(catalog.get("name_en") or fill_title(theme.title_en, child.first_name, gender))
        if theme
        else None,
        style=cb.art_style if cb else DEFAULT_STYLE,
        consent_version=INVITE_CONSENT_VERSION,
        child=await create._child_out(db, child) if state == "mine" else None,
    )


class ConsentIn(BaseModel):
    accept: Literal[True]
    version: str = Field(max_length=32)


@router.post("/{token}/consent")
async def consent(
    token: str, body: ConsentIn, request: Request, user: CurrentUser, db: SessionDep
) -> InviteOut:
    """The guardian's consent for the photo and the class book, stored with this text's version."""
    invite, child = await _mine(db, user, token)
    if body.version != INVITE_CONSENT_VERSION:
        raise ApiError("consent_outdated", 409)
    record_consent(
        db, request, user_id=user.id, child_id=child.id, version=INVITE_CONSENT_VERSION, scope="class_book"
    )
    await db.commit()
    return await _out(db, invite, child, "mine")


class DrawIn(BaseModel):
    fixes: list[Literal["skin", "face", "hair", "age"]] = Field(default_factory=list, max_length=4)


@router.post("/{token}/character", status_code=202)
async def draw(
    token: str, body: DrawIn, user: CurrentUser, db: SessionDep, queue: QueueDep
) -> create.CharacterOut:
    """The character in the class book's art style, through the create flow's own drawing step."""
    invite, child = await _mine(db, user, token)
    cb = await _class_book(db, invite)
    style = cb.art_style if cb else DEFAULT_STYLE
    return await create.draw_character(
        child.id, create.CharacterIn(style=style, fixes=body.fixes), user, db, queue
    )
