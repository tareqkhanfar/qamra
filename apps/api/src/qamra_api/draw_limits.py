"""Free character drawings that come back with time (owner, 2026-10-16).

Each child has `free_draws_per_window` free drawings in every rolling `free_draws_window_hours`
(defaults: 3 in 2 hours); a drawing comes back that many hours after it was asked for. On top, no child
and no account gets more than `free_draws_daily_cap` drawings in 24 hours (default 12), so one person
can't run up the cost (each drawing is a portrait and a sheet, about $0.30). Every drawing counts, the
first one too; a drawing that failed on our side never does, and reusing an approved character is not a
drawing. Staff accounts (`admin`) are never limited, in any flow.

The child's count comes from its characters (any status but `failed`, also the ones the cleanup removed).
The account's comes from the `character.drawn` audit rows, so deleting a child doesn't give its drawings
back. Every place that draws a child's character goes through `create.draw_character` (the story and
activity-book steps and the kindergarten invite), which checks and records here.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.app_settings import REGISTRY
from qamra_core.db.models import AppSetting, AuditLog, Character, CharacterStatus, Child, User, UserRole

DAY = timedelta(hours=24)
DRAWN = "character.drawn"  # the audit action of one drawing asked for, by the account that asked
KEYS = ("free_draws_per_window", "free_draws_window_hours", "free_draws_daily_cap")


@dataclass(frozen=True)
class Limits:
    per_window: int
    window_hours: int
    daily_cap: int  # per child and per account, in 24 hours

    @property
    def window(self) -> timedelta:
        return timedelta(hours=self.window_hours)


@dataclass(frozen=True)
class Allowance:
    left: int  # free drawings the parent may ask for now
    reset_at: datetime | None  # when one more comes back (None: all are there)
    per_window: int
    window_hours: int
    unlimited: bool = False


def is_unlimited(user: User | None) -> bool:
    """Staff (the owner's account among them) draw as much as they need, in every flow."""
    return user is not None and user.role == UserRole.admin


async def guardian_unlimited(db: AsyncSession, child_id: uuid.UUID) -> bool:
    """Whether the child's guardian is a staff account (e.g. the owner's own test children)."""
    role = await db.scalar(
        select(User.role).join(Child, Child.guardian_user_id == User.id).where(Child.id == child_id)
    )
    return role == UserRole.admin


def limits_from(values: dict[str, Any]) -> Limits:
    def num(key: str) -> int:
        value = values.get(key)
        return max(1, int(REGISTRY[key].default if value is None else value))

    return Limits(num(KEYS[0]), min(24, num(KEYS[1])), num(KEYS[2]))


async def load_limits(db: AsyncSession) -> Limits:
    """The three settings as the admin stored them (plain numbers: no decryption needed)."""
    rows = await db.execute(select(AppSetting.key, AppSetting.value).where(AppSetting.key.in_(KEYS)))
    return limits_from({k: v for k, v in rows})


def allowance(
    now: datetime, limits: Limits, child_times: Iterable[datetime], account_times: Iterable[datetime]
) -> Allowance:
    """What is left now and when the next drawing comes back, from the times of the counted drawings."""
    child = [t for t in child_times if t > now - DAY]
    account = [t for t in account_times if t > now - DAY]

    def left_at(at: datetime) -> int:
        in_window = sum(t > at - limits.window for t in child)
        child_day = sum(t > at - DAY for t in child)
        account_day = sum(t > at - DAY for t in account)
        return max(
            0,
            min(
                limits.per_window - in_window,
                limits.daily_cap - child_day,
                limits.daily_cap - account_day,
            ),
        )

    left = left_at(now)
    reset_at = None
    if left < limits.per_window:  # the first moment one more is free: a drawing leaving a window or a day
        for at in sorted({t + limits.window for t in child} | {t + DAY for t in [*child, *account]}):
            if at > now and left_at(at) > left:
                reset_at = at
                break
    return Allowance(left, reset_at, limits.per_window, limits.window_hours)


def unlimited_allowance(limits: Limits) -> Allowance:
    return Allowance(limits.per_window, None, limits.per_window, limits.window_hours, unlimited=True)


async def child_draw_times(db: AsyncSession, child_id: uuid.UUID, since: datetime) -> list[datetime]:
    rows = await db.execute(
        select(Character.created_at).where(
            Character.child_id == child_id,
            Character.status != CharacterStatus.failed,
            Character.created_at > since,
        )
    )
    return list(rows.scalars())


async def account_draw_times(db: AsyncSession, user_id: uuid.UUID, since: datetime) -> list[datetime]:
    """The account's drawings in the last day, also of children deleted since; not the ones that failed."""
    rows = await db.execute(
        select(AuditLog.created_at)
        .outerjoin(Character, cast(Character.id, String) == AuditLog.entity_id)
        .where(
            AuditLog.action == DRAWN,
            AuditLog.actor_user_id == user_id,
            AuditLog.created_at > since,
            (Character.id.is_(None)) | (Character.status != CharacterStatus.failed),
        )
    )
    return list(rows.scalars())


async def for_child(
    db: AsyncSession, child_id: uuid.UUID, account: User | None, now: datetime, limits: Limits | None = None
) -> Allowance:
    """The free drawings `account` (the child's guardian) has for this child now."""
    limits = limits or await load_limits(db)
    if is_unlimited(account):
        return unlimited_allowance(limits)
    since = now - DAY
    child = await child_draw_times(db, child_id, since)
    mine = await account_draw_times(db, account.id, since) if account is not None else []
    return allowance(now, limits, child, mine)


def drawn_log(user_id: uuid.UUID, character_id: uuid.UUID, child_id: uuid.UUID) -> AuditLog:
    return AuditLog(
        actor_user_id=user_id,
        action=DRAWN,
        entity_type="character",
        entity_id=str(character_id),
        data={"child_id": str(child_id)},
    )
