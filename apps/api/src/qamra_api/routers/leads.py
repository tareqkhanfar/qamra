"""Kindergarten demo requests (public form), and the family book's quote requests from organizations
(Addendum 7 §8): a request, never an order, with a private back-cover logo; staff price it from the printer's
tiers once the real prices are in."""

import io
import re
import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from qamra_api import ratelimit, runtime_settings
from qamra_api.auth.router import client_ip
from qamra_api.deps import AdminUser, RedisDep, SessionDep, SettingsDep, StorageDep, require_permission
from qamra_api.errors import ApiError
from qamra_api.store.catalog import BULK_MIN_QTY, load_catalog, quantity_table, tiers_estimated
from qamra_api.validation import PHONE
from qamra_core.db.models import AuditLog, Lead, LeadStatus, Locale

router = APIRouter(prefix="/api/leads", tags=["leads"])
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
        if not PHONE.match(v):
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


# ---- «مغامراتي مع عائلتي»: quotes for organizations (A7 §8) ------------------------------------------------

QUOTE_KIND = "family_quote"
QUOTE_SKU = "family-wireo"  # the printed family book
LOGO_MAX_BYTES = 5 * 1024 * 1024
LOGO_MIN_SIDE = 300  # px on the long side: sharp at the back cover's logo size (~25 mm at 300 DPI)
LOGO_MAX_SIDE = 2400
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def logo_key(lead_id: uuid.UUID) -> str:
    """The organization's logo, private like every upload (read through the staff endpoint only)."""
    return f"leads/{lead_id}/logo.png"


def clean_logo(data: bytes) -> tuple[bytes, tuple[int, int]]:
    """PNG or JPG only, big enough to print; re-encoded as PNG (keeps transparency, drops metadata)."""
    if len(data) > LOGO_MAX_BYTES:
        raise ApiError("file_too_large", 413)
    try:
        with Image.open(io.BytesIO(data)) as original:
            if original.format not in ("PNG", "JPEG"):
                raise ApiError("invalid_logo", 422, {"reason": "format"})
            im = ImageOps.exif_transpose(original).convert("RGBA")
    except (UnidentifiedImageError, OSError) as e:
        raise ApiError("invalid_logo", 422, {"reason": "unreadable"}) from e
    if max(im.size) < LOGO_MIN_SIDE:
        raise ApiError("invalid_logo", 422, {"reason": "small"})
    im.thumbnail((LOGO_MAX_SIDE, LOGO_MAX_SIDE), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), im.size


def _text(value: str | None, field: str, *, required: bool = False) -> str | None:
    text = " ".join((value or "").split()) or None
    if required and not text:
        raise ApiError("invalid_input", 422, {"fields": [field]})
    return text


class QuoteRequestOut(BaseModel):
    ok: bool = True
    request_only: bool = True  # a request for a quote, not an order: staff reply with a price


@router.post("/family-quote", status_code=201)
async def request_family_quote(
    request: Request,
    db: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    storage: StorageDep,
    org_name: Annotated[str, Form(max_length=200)],
    contact_name: Annotated[str, Form(max_length=120)],
    phone: Annotated[str, Form(max_length=32)],
    quantity: Annotated[int, Form(ge=BULK_MIN_QTY, le=5000)],
    city: Annotated[str | None, Form(max_length=100)] = None,
    contact_role: Annotated[str | None, Form(max_length=120)] = None,
    email: Annotated[str | None, Form(max_length=200)] = None,
    desired_date: Annotated[date | None, Form()] = None,
    notes: Annotated[str | None, Form(max_length=2000)] = None,
    locale: Annotated[Locale, Form()] = Locale.ar,
    logo: Annotated[UploadFile | None, File()] = None,
) -> QuoteRequestOut:
    """An organization asks for a price for many copies, with its logo for the back cover (optional)."""
    if await ratelimit.hit(redis, f"rl:leads:{client_ip(request)}", 3600) > settings.leads_per_ip_per_hour:
        raise ApiError("too_many_attempts", 429)
    if not PHONE.match(phone.strip()):
        raise ApiError("invalid_input", 422, {"fields": ["phone"]})
    mail = _text(email, "email")
    if mail and not EMAIL.match(mail):
        raise ApiError("invalid_input", 422, {"fields": ["email"]})
    if desired_date is not None and desired_date < date.today():
        raise ApiError("invalid_input", 422, {"fields": ["desired_date"]})
    cleaned = clean_logo(await logo.read(LOGO_MAX_BYTES + 1)) if logo is not None and logo.filename else None
    lead = Lead(
        kind=QUOTE_KIND,
        org_name=_text(org_name, "org_name", required=True),
        city=_text(city, "city"),
        contact_name=_text(contact_name, "contact_name", required=True),
        contact_role=_text(contact_role, "contact_role"),
        phone=phone.strip(),
        event_date=desired_date,
        notes=(notes or "").strip() or None,
        locale=locale,
    )
    db.add(lead)
    await db.flush()
    details: dict[str, Any] = {
        "product": "family-adventures",
        "sku": QUOTE_SKU,
        "quantity": quantity,
        "email": mail,
    }
    if cleaned is not None:
        details |= {"logo_key": logo_key(lead.id), "logo_px": list(cleaned[1])}
        storage.put(logo_key(lead.id), cleaned[0], "image/png")
    lead.details = details
    db.add(
        AuditLog(
            actor_user_id=None, action="lead.quote_requested", entity_type="lead", entity_id=str(lead.id)
        )
    )
    await db.commit()
    return QuoteRequestOut()


# ---- staff: the requests, the logo, the status and the price ---------------------------------------------

admin_router = APIRouter(prefix="/api/admin/leads", tags=["admin"])


class LeadAdminOut(BaseModel):
    id: uuid.UUID
    kind: str
    created_at: datetime
    status: LeadStatus
    org_name: str
    city: str | None
    contact_name: str
    contact_role: str | None
    phone: str
    email: str | None
    quantity: int | None
    children_count: int | None
    event_date: date | None
    notes: str | None
    has_logo: bool
    logo_px: list[int] | None
    quote: dict[str, Any] | None


def _lead_out(lead: Lead) -> LeadAdminOut:
    d = lead.details or {}
    return LeadAdminOut(
        id=lead.id,
        kind=lead.kind,
        created_at=lead.created_at,
        status=lead.status,
        org_name=lead.org_name,
        city=lead.city,
        contact_name=lead.contact_name,
        contact_role=lead.contact_role,
        phone=lead.phone,
        email=d.get("email"),
        quantity=d.get("quantity"),
        children_count=lead.children_count,
        event_date=lead.event_date,
        notes=lead.notes,
        has_logo=bool(d.get("logo_key")),
        logo_px=d.get("logo_px"),
        quote=d.get("quote"),
    )


async def _lead(db: SessionDep, lead_id: uuid.UUID) -> Lead:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise ApiError("not_found", 404)
    return lead


@admin_router.get("", dependencies=[Depends(require_permission("orders.view"))])
async def list_leads(db: SessionDep, kind: str | None = None) -> list[LeadAdminOut]:
    query = select(Lead).order_by(Lead.created_at.desc()).limit(200)
    if kind:
        query = query.where(Lead.kind == kind)
    return [_lead_out(lead) for lead in (await db.execute(query)).scalars()]


@admin_router.get("/{lead_id}/logo", dependencies=[Depends(require_permission("orders.view"))])
async def lead_logo(lead_id: uuid.UUID, db: SessionDep, storage: StorageDep) -> Response:
    key = ((await _lead(db, lead_id)).details or {}).get("logo_key")
    if not key or not storage.exists(key):
        raise ApiError("not_found", 404)
    return Response(storage.get(key), media_type="image/png", headers={"Cache-Control": "private, no-store"})


class LeadStatusIn(BaseModel):
    status: LeadStatus


@admin_router.patch("/{lead_id}", dependencies=[Depends(require_permission("orders.view"))])
async def set_lead_status(
    lead_id: uuid.UUID, body: LeadStatusIn, admin: AdminUser, db: SessionDep
) -> LeadAdminOut:
    lead = await _lead(db, lead_id)
    before, lead.status = lead.status, body.status
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="lead.status_changed",
            entity_type="lead",
            entity_id=str(lead.id),
            data={"from": before.value, "to": body.status.value},
        )
    )
    await db.commit()
    return _lead_out(lead)


@admin_router.post("/{lead_id}/quote", dependencies=[Depends(require_permission("prices"))])
async def price_quote(
    lead_id: uuid.UUID, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> LeadAdminOut:
    """The price per copy and the total from the printer's tiers and the margin rules. From 10 copies the
    tiers must be the printer's real prices: while they are estimates the quote waits (Tareq, 2026-09-28)."""
    lead = await _lead(db, lead_id)
    details = dict(lead.details or {})
    qty = int(details.get("quantity") or 0)
    catalog = await load_catalog(db, include_inactive=True)  # a quote may come before the book is on sale
    variant = catalog.variants.get(str(details.get("sku") or QUOTE_SKU))
    if lead.kind != QUOTE_KIND or variant is None or qty < 1:
        raise ApiError("not_found", 404)
    if qty >= BULK_MIN_QTY and (not variant.print_cost_tiers or tiers_estimated(variant)):
        raise ApiError("bulk_price_pending", 409, {"min_qty": BULK_MIN_QTY})
    values = (await runtime_settings.current(db, settings)).values
    [row] = quantity_table(catalog, variant, values, [qty])
    quote = {
        "sku": variant.sku,
        "quantity": qty,
        "currency": "ILS",
        "unit_price": str(row.unit_price),
        "total": str(row.total),
        "unit_cost": str(row.unit_cost),
        "margin_pct": str(row.margin_pct),
        "priced_at": datetime.now(UTC).isoformat(),
        "priced_by": str(admin.id),
    }
    lead.details = {**details, "quote": quote}
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="lead.quoted",
            entity_type="lead",
            entity_id=str(lead.id),
            data=quote,
        )
    )
    await db.commit()
    return _lead_out(lead)
