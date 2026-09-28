"""Read and write admin-managed settings (registry in `app_settings`), async (api) and sync (worker)."""

import uuid
from dataclasses import dataclass
from typing import Any

from cryptography.fernet import MultiFernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from qamra_core.app_settings import REGISTRY, Kind, SettingError, validate
from qamra_core.crypto import DecryptError, decrypt, encrypt
from qamra_core.db.models import AppSetting, AuditLog


@dataclass(frozen=True)
class Resolved:
    values: dict[str, Any]  # every registry key, defaults filled in, secrets decrypted ("" when unset)
    stored: frozenset[str]  # keys that have a stored (admin-set) value

    def public(self) -> dict[str, Any]:
        return {k: v for k, v in self.values.items() if REGISTRY[k].public}


def _resolve(rows: list[AppSetting], cipher: MultiFernet) -> Resolved:
    values = {k: d.default for k, d in REGISTRY.items()}
    stored: set[str] = set()
    for row in rows:
        d = REGISTRY.get(row.key)
        if d is None:  # a key removed from the registry: ignore
            continue
        if d.kind == Kind.secret:
            if row.secret_ciphertext:
                try:
                    values[row.key] = decrypt(cipher, row.secret_ciphertext)
                    stored.add(row.key)
                except DecryptError:
                    values[row.key] = ""  # unreadable (rotated key): behaves as unset, admin can re-enter
        elif row.value is not None:
            values[row.key] = row.value
            stored.add(row.key)
    return Resolved(values=values, stored=frozenset(stored))


def prepare_changes(changes: dict[str, Any]) -> dict[str, Any]:
    """Validate everything first so a bad field never half-applies a save."""
    unknown = [k for k in changes if k not in REGISTRY]
    if unknown:
        raise SettingError(unknown[0], "unknown setting")
    out: dict[str, Any] = {}
    for key, raw in changes.items():
        d = REGISTRY[key]
        out[key] = None if raw is None else validate(d, raw)
    return out


def _apply(
    row: AppSetting | None, key: str, value: Any, cipher: MultiFernet, actor: uuid.UUID | None
) -> AppSetting:
    row = row or AppSetting(key=key)
    if REGISTRY[key].kind == Kind.secret:
        row.value = None
        row.secret_ciphertext = encrypt(cipher, value) if value else None
    else:
        row.value = value
        row.secret_ciphertext = None
    row.updated_by_user_id = actor
    return row


def _audit(changed: list[str], actor: uuid.UUID | None) -> AuditLog:
    """Which keys changed and who changed them; never a value (secrets or not)."""
    return AuditLog(
        actor_user_id=actor,
        action="admin.settings_updated",
        entity_type="settings",
        entity_id=None,
        data={"keys": sorted(changed)},
    )


# ---- async (api) ---------------------------------------------------------------------------------


async def plain(db: AsyncSession, *keys: str) -> dict[str, Any]:
    """Non-secret settings, defaults filled in, read without the cipher (the storefront's pricing numbers)."""
    if any(REGISTRY[k].kind == Kind.secret for k in keys):
        raise SettingError(keys[0], "plain() reads non-secret settings only")
    values = {k: REGISTRY[k].default for k in keys}
    for row in (await db.execute(select(AppSetting).where(AppSetting.key.in_(keys)))).scalars():
        if row.value is not None:
            values[row.key] = row.value
    return values


async def load(db: AsyncSession, cipher: MultiFernet) -> Resolved:
    rows = list((await db.execute(select(AppSetting))).scalars().all())
    return _resolve(rows, cipher)


async def save(
    db: AsyncSession, cipher: MultiFernet, changes: dict[str, Any], actor: uuid.UUID | None
) -> list[str]:
    prepared = prepare_changes(changes)
    if not prepared:
        return []
    existing = {
        r.key: r for r in (await db.execute(select(AppSetting).where(AppSetting.key.in_(prepared)))).scalars()
    }
    for key, value in prepared.items():
        if value is None:  # reset to default
            if key in existing:
                await db.delete(existing[key])
            continue
        db.add(_apply(existing.get(key), key, value, cipher, actor))
    changed = sorted(prepared)
    db.add(_audit(changed, actor))
    await db.commit()
    return changed


# ---- sync (worker) --------------------------------------------------------------------------------


def load_sync(db: Session, cipher: MultiFernet) -> Resolved:
    rows = list(db.scalars(select(AppSetting)).all())
    return _resolve(rows, cipher)
