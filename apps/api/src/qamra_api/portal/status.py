"""The teacher's status board (Addendum 1 §2): per child, invited → consent → photo → drawing → approved.

Only states leave the database here, never a photo or a photo's address: the school sees that a photo was
uploaded, not the photo (CLAUDE.md §3.1). Photos count as uploaded even after the 24-hour deletion.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import Character, CharacterStatus, Child, ChildPhoto, Classroom, Companion, Consent
from qamra_core.db.portal import ChildInvite

Stage = Literal["not_invited", "invited", "consent", "photo", "approved"]
STAGES: tuple[Stage, ...] = ("not_invited", "invited", "consent", "photo", "approved")


@dataclass
class ChildState:
    child: Child
    invite: ChildInvite | None
    consent: bool
    photo: bool
    drawing: bool
    character: Character | None  # approved, in the class book's style
    drawn: bool  # a character is drawn and waits for the parent's approval
    last: datetime | None

    @property
    def invited(self) -> bool:
        i = self.invite
        return i is not None and (i.sent_at is not None or i.claimed_at is not None)

    @property
    def stage(self) -> Stage:
        if self.character is not None:
            return "approved"
        if self.photo:
            return "photo"
        if self.consent:
            return "consent"
        return "invited" if self.invited else "not_invited"

    @property
    def age(self) -> int:
        return date.today().year - self.child.birth_year


def mask_phone(phone: str | None) -> str | None:
    """ "0599 ••• 456": enough for the teacher to recognize the family."""
    if not phone:
        return None
    return f"{phone[:4]} ••• {phone[-3:]}" if len(phone) > 7 else "•••"


def mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    user, _, host = email.partition("@")
    return f"{user[:1]}•••@{host}"


def invite_state(invite: ChildInvite | None, now: datetime | None = None) -> str:
    if invite is None:
        return "none"
    now = now or datetime.now(UTC)
    if invite.claimed_at is not None:
        return "claimed"
    if invite.revoked_at is not None or invite.expires_at <= now:
        return "expired"
    return "sent" if invite.sent_at else "ready"


async def class_states(db: AsyncSession, room: Classroom, style: str | None) -> list[ChildState]:
    """Every child of the class with their steps, in a handful of queries (no per-child round trips)."""
    children = (
        (await db.execute(select(Child).where(Child.classroom_id == room.id).order_by(Child.first_name)))
        .scalars()
        .all()
    )
    ids = [c.id for c in children]
    if not ids:
        return []
    invites = {
        i.child_id: i
        for i in (await db.execute(select(ChildInvite).where(ChildInvite.child_id.in_(ids)))).scalars()
    }
    consents = set((await db.execute(select(Consent.child_id).where(Consent.child_id.in_(ids)))).scalars())
    photos: dict[uuid.UUID, datetime] = {}
    for child_id, created in await db.execute(
        select(ChildPhoto.child_id, ChildPhoto.created_at).where(ChildPhoto.child_id.in_(ids))
    ):
        photos[child_id] = max(created, photos.get(child_id, created))
    drawings = set(
        (await db.execute(select(Companion.child_id).where(Companion.child_id.in_(ids)))).scalars()
    )
    approved: dict[uuid.UUID, Character] = {}
    drawn: set[uuid.UUID] = set()
    for c in (await db.execute(select(Character).where(Character.child_id.in_(ids)))).scalars():
        if c.status == CharacterStatus.approved and c.approved_at and (style is None or c.art_style == style):
            if c.child_id not in approved or c.approved_at > approved[c.child_id].approved_at:  # type: ignore[operator]
                approved[c.child_id] = c
        elif c.status == CharacterStatus.ready:
            drawn.add(c.child_id)
    out = []
    for child in children:
        invite = invites.get(child.id)
        character = approved.get(child.id)
        moments = [
            invite.sent_at if invite else None,
            invite.claimed_at if invite else None,
            photos.get(child.id),
            character.approved_at if character else None,
        ]
        out.append(
            ChildState(
                child=child,
                invite=invite,
                consent=child.id in consents,
                photo=child.id in photos or character is not None,
                drawing=child.id in drawings,
                character=character,
                drawn=child.id in drawn,
                last=max((m for m in moments if m is not None), default=None),
            )
        )
    return out


def stage_counts(states: list[ChildState]) -> dict[str, int]:
    counts: dict[str, int] = dict.fromkeys(STAGES, 0)
    for s in states:
        counts[s.stage] += 1
    return counts
