"""Kindergarten demo requests (public form)."""

import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from qamra_api import ratelimit
from qamra_api.auth.router import client_ip
from qamra_api.deps import RedisDep, SessionDep, SettingsDep
from qamra_api.errors import ApiError
from qamra_core.db.models import AuditLog, Lead, Locale

router = APIRouter(prefix="/api/leads", tags=["leads"])
_PHONE = re.compile(r"^\+?[0-9 ()-]{7,20}$")
Text = Annotated[str, Field(min_length=1, max_length=200)]


class LeadIn(BaseModel):
    org_name: Text
    city: str | None = Field(default=None, max_length=100)
    contact_name: Text
    contact_role: str | None = Field(default=None, max_length=120)
    phone: str = Field(max_length=32)
    children_count: int | None = Field(default=None, ge=1, le=500)
    event_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    locale: Locale = Locale.ar

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = v.strip()
        if not _PHONE.match(v):
            raise ValueError("invalid phone")
        return v

    @field_validator("org_name", "contact_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("empty")
        return v


class LeadOut(BaseModel):
    ok: bool = True


@router.post("", status_code=201)
async def create_lead(
    body: LeadIn, request: Request, db: SessionDep, redis: RedisDep, settings: SettingsDep
) -> LeadOut:
    if await ratelimit.hit(redis, f"rl:leads:{client_ip(request)}", 3600) > settings.leads_per_ip_per_hour:
        raise ApiError("too_many_attempts", 429)
    lead = Lead(**body.model_dump())
    db.add(lead)
    await db.flush()
    db.add(AuditLog(actor_user_id=None, action="lead.created", entity_type="lead", entity_id=str(lead.id)))
    await db.commit()
    return LeadOut()
