"""Admin: staff roles (Addendum 4 §3.6) and the audit-log viewer.

- Staff are accounts with the admin role (2FA required); their roles come from qamra_core.permissions.
  Adding, changing and removing staff is for admins (the `users` permission) and every change is audited.
  Only an owner grants or takes away the owner role, and nobody changes their own roles, so an owner
  always remains.
- The audit log: filter by actor, action, entity and date, newest first, a page at a time. It returns what
  the log holds (ids, action names, data) and nothing more.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.deps import AdminUser, SessionDep, require_admin, require_permission
from qamra_api.errors import ApiError
from qamra_core.db.models import AuditLog, User, UserRole
from qamra_core.db.store import StaffRole, UserStaffRole
from qamra_core.permissions import PERMISSIONS

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class RoleInfo(BaseModel):
    role: str
    permissions: list[str]


class StaffOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    roles: list[str]
    mfa: bool
    active: bool
    last_login_at: datetime | None


class StaffList(BaseModel):
    me: uuid.UUID
    roles: list[RoleInfo]
    staff: list[StaffOut]


async def _roles(db: AsyncSession, user_id: uuid.UUID) -> set[StaffRole]:
    rows = await db.execute(select(UserStaffRole.role).where(UserStaffRole.user_id == user_id))
    return set(rows.scalars())


async def _staff_out(db: AsyncSession, user: User) -> StaffOut:
    roles = await _roles(db, user.id)
    return StaffOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=[r.value for r in StaffRole if r in roles],
        mfa=user.totp_enabled_at is not None,
        active=user.is_active,
        last_login_at=user.last_login_at,
    )


@router.get("/staff", dependencies=[Depends(require_permission("users"))])
async def list_staff(admin: AdminUser, db: SessionDep) -> StaffList:
    users = (
        await db.execute(select(User).where(User.role == UserRole.admin).order_by(User.full_name))
    ).scalars()
    return StaffList(
        me=admin.id,
        roles=[RoleInfo(role=r.value, permissions=sorted(PERMISSIONS[r])) for r in StaffRole],
        staff=[await _staff_out(db, u) for u in users],
    )


async def _set_roles(db: AsyncSession, admin: AdminUser, user: User, wanted: set[StaffRole]) -> None:
    """Grant and revoke to reach `wanted`, with the owner rules; one audit entry per change."""
    if user.id == admin.id:
        raise ApiError("self_change", 409)
    before = await _roles(db, user.id)
    touches_owner = (StaffRole.owner in before) != (StaffRole.owner in wanted)
    if touches_owner and StaffRole.owner not in await _roles(db, admin.id):
        raise ApiError("forbidden", 403)
    now = datetime.now(UTC)
    for role in sorted(wanted - before):
        db.add(UserStaffRole(user_id=user.id, role=role, granted_at=now, granted_by=admin.id))
        db.add(_audit(admin, "staff.role_granted", user, role=role.value))
    for role in sorted(before - wanted):
        await db.execute(
            delete(UserStaffRole).where(UserStaffRole.user_id == user.id, UserStaffRole.role == role)
        )
        db.add(_audit(admin, "staff.role_revoked", user, role=role.value))


def _audit(admin: AdminUser, action: str, user: User, **data: Any) -> AuditLog:
    return AuditLog(
        actor_user_id=admin.id, action=action, entity_type="user", entity_id=str(user.id), data=data
    )


async def _staff_member(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None or user.role != UserRole.admin:
        raise ApiError("not_found", 404)
    return user


class StaffIn(BaseModel):
    email: EmailStr
    roles: list[StaffRole] = Field(min_length=1, max_length=len(StaffRole))


@router.post("/staff", status_code=201, dependencies=[Depends(require_permission("users"))])
async def add_staff(body: StaffIn, admin: AdminUser, db: SessionDep) -> StaffOut:
    """An existing account joins the staff with these roles; it must set up 2FA before the admin opens."""
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if user is None:
        raise ApiError("not_found", 404)
    if user.role != UserRole.admin:
        user.role = UserRole.admin
        db.add(_audit(admin, "staff.added", user))
    await _set_roles(db, admin, user, set(body.roles))
    await db.commit()
    return await _staff_out(db, user)


class RolesIn(BaseModel):
    roles: list[StaffRole] = Field(min_length=1, max_length=len(StaffRole))


@router.put("/staff/{user_id}/roles", dependencies=[Depends(require_permission("users"))])
async def set_roles(user_id: uuid.UUID, body: RolesIn, admin: AdminUser, db: SessionDep) -> StaffOut:
    user = await _staff_member(db, user_id)
    await _set_roles(db, admin, user, set(body.roles))
    await db.commit()
    return await _staff_out(db, user)


@router.delete("/staff/{user_id}", status_code=204, dependencies=[Depends(require_permission("users"))])
async def remove_staff(user_id: uuid.UUID, admin: AdminUser, db: SessionDep) -> None:
    """Every role goes and the account becomes a regular one (its admin access ends on the next request)."""
    user = await _staff_member(db, user_id)
    await _set_roles(db, admin, user, set())
    user.role = UserRole.parent
    db.add(_audit(admin, "staff.removed", user))
    await db.commit()


# ---- the audit log ----------------------------------------------------------------------------------------


class AuditItem(BaseModel):
    id: uuid.UUID
    at: datetime
    actor: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    data: dict[str, Any]


class AuditPage(BaseModel):
    items: list[AuditItem]
    total: int
    page: int
    pages: int
    per_page: int


class AuditFacets(BaseModel):
    actions: list[str]
    entity_types: list[str]


@router.get("/audit", dependencies=[Depends(require_permission("users.audit"))])
async def audit_log(
    db: SessionDep,
    actor: uuid.UUID | None = None,
    action: Annotated[str | None, Query(max_length=64)] = None,  # a prefix: "theme." finds every theme action
    entity_type: Annotated[str | None, Query(max_length=32)] = None,
    entity_id: Annotated[str | None, Query(max_length=64)] = None,
    since: datetime | None = None,
    until: datetime | None = None,  # exclusive
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
    per_page: Annotated[int, Query(ge=10, le=200)] = 50,
) -> AuditPage:
    where: list[Any] = []
    if actor is not None:
        where.append(AuditLog.actor_user_id == actor)
    if action:
        where.append(AuditLog.action.startswith(action.strip(), autoescape=True))
    if entity_type:
        where.append(AuditLog.entity_type == entity_type)
    if entity_id:
        where.append(AuditLog.entity_id == entity_id.strip())
    if since is not None:
        where.append(AuditLog.created_at >= (since if since.tzinfo else since.replace(tzinfo=UTC)))
    if until is not None:
        where.append(AuditLog.created_at < (until if until.tzinfo else until.replace(tzinfo=UTC)))
    total = int((await db.execute(select(func.count()).select_from(AuditLog).where(*where))).scalar_one())
    q = select(AuditLog).where(*where).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    rows = (await db.execute(q.offset((page - 1) * per_page).limit(per_page))).scalars()
    return AuditPage(
        items=[
            AuditItem(
                id=r.id,
                at=r.created_at,
                actor=r.actor_user_id,
                action=r.action,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                data=r.data or {},
            )
            for r in rows
        ],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
        per_page=per_page,
    )


@router.get("/audit/facets", dependencies=[Depends(require_permission("users.audit"))])
async def audit_facets(db: SessionDep) -> AuditFacets:
    """The action names and entity types in the log, for the filters."""
    actions = (
        await db.execute(select(AuditLog.action).distinct().order_by(AuditLog.action).limit(500))
    ).scalars()
    types = (
        await db.execute(select(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type).limit(100))
    ).scalars()
    return AuditFacets(actions=list(actions), entity_types=list(types))
