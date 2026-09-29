"""Who may use the kindergarten portal: a `school_admin` user of an approved organization (CLAUDE.md §8).

Every portal query goes through these helpers, which only ever return rows of the caller's organization:
someone else's class or child gets the same 404 as one that doesn't exist.
"""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from qamra_api.deps import CurrentUser, SessionDep
from qamra_api.errors import ApiError
from qamra_core.db.models import Child, Classroom, Organization, OrgStatus, User, UserRole
from qamra_core.db.portal import ClassBook


@dataclass(frozen=True)
class School:
    user: User
    org: Organization


async def school_member(user: CurrentUser, db: SessionDep) -> School:
    """A signed-in school admin, whatever the organization's status (the dashboard shows «pending»)."""
    if user.role != UserRole.school_admin or user.organization_id is None:
        raise ApiError("not_school", 403)
    org = await db.get(Organization, user.organization_id)
    if org is None:
        raise ApiError("not_school", 403)
    return School(user, org)


SchoolMember = Annotated[School, Depends(school_member)]


async def school_admin(member: SchoolMember) -> School:
    """Everything else in the portal needs an organization our team approved."""
    if member.org.status == OrgStatus.pending:
        raise ApiError("org_pending", 403)
    if member.org.status != OrgStatus.approved:
        raise ApiError("org_rejected", 403)
    return member


SchoolAdmin = Annotated[School, Depends(school_admin)]


async def own_classroom(db: SessionDep, school: School, classroom_id: uuid.UUID) -> Classroom:
    room = await db.get(Classroom, classroom_id)
    if room is None or room.organization_id != school.org.id:
        raise ApiError("not_found", 404)
    return room


async def own_child(db: SessionDep, room: Classroom, child_id: uuid.UUID) -> Child:
    child = await db.get(Child, child_id)
    if child is None or child.classroom_id != room.id or child.organization_id != room.organization_id:
        raise ApiError("not_found", 404)
    return child


async def class_book_of(db: SessionDep, room: Classroom) -> ClassBook | None:
    return (await db.execute(select(ClassBook).where(ClassBook.classroom_id == room.id))).scalar_one_or_none()
