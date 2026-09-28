"""Settings: the public subset for the website, and the admin editor (role admin only)."""

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from qamra_api import runtime_settings
from qamra_api.deps import AdminUser, SessionDep, SettingsDep, require_admin
from qamra_api.errors import ApiError
from qamra_core import settings_store
from qamra_core.app_settings import GROUPS, REGISTRY, Kind, SettingError, mask
from qamra_core.crypto import cipher_for

public_router = APIRouter(prefix="/api/settings", tags=["settings"])
admin_router = APIRouter(prefix="/api/admin/settings", tags=["admin"], dependencies=[Depends(require_admin)])
Lang = Literal["ar", "en"]


@public_router.get("/public")
async def public_settings(db: SessionDep, settings: SettingsDep) -> dict[str, Any]:
    return (await runtime_settings.current(db, settings)).public()


class SettingView(BaseModel):
    key: str
    kind: Kind
    label: str
    help: str
    value: Any  # secrets: masked
    configured: bool  # has an admin-saved value
    is_example: bool  # still the example default
    public: bool
    choices: list[str]
    min: float | None
    max: float | None


class GroupView(BaseModel):
    id: str
    label: str
    settings: list[SettingView]


class SettingsView(BaseModel):
    groups: list[GroupView]


class SettingsUpdate(BaseModel):
    values: dict[str, Any]  # value, or null to restore the default / clear a secret


async def _view(db: SessionDep, settings: SettingsDep, lang: Lang) -> SettingsView:
    resolved = await settings_store.load(db, cipher_for(settings))
    groups = []
    for g in GROUPS:
        items = []
        for d in (d for d in REGISTRY.values() if d.group == g.id):
            value = resolved.values[d.key]
            secret = d.kind == Kind.secret
            items.append(
                SettingView(
                    key=d.key,
                    kind=d.kind,
                    label=d.label_ar if lang == "ar" else d.label_en,
                    help=d.help_ar if lang == "ar" else d.help_en,
                    value=mask(value) if secret else value,
                    configured=(bool(value) if secret else d.key in resolved.stored),
                    is_example=d.example and d.key not in resolved.stored,
                    public=d.public,
                    choices=list(d.choices),
                    min=d.min,
                    max=d.max,
                )
            )
        groups.append(GroupView(id=g.id, label=g.label_ar if lang == "ar" else g.label_en, settings=items))
    return SettingsView(groups=groups)


@admin_router.get("")
async def get_settings(db: SessionDep, settings: SettingsDep, lang: Lang = "ar") -> SettingsView:
    return await _view(db, settings, lang)


@admin_router.put("")
async def update_settings(
    body: SettingsUpdate, user: AdminUser, db: SessionDep, settings: SettingsDep, lang: Lang = "ar"
) -> SettingsView:
    try:
        await settings_store.save(db, cipher_for(settings), body.values, user.id)
    except SettingError as e:
        raise ApiError("invalid_setting", 422, {"fields": [e.key], "reason": e.reason}) from e
    runtime_settings.invalidate()
    return await _view(db, settings, lang)
