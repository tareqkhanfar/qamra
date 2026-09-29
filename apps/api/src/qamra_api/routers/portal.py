"""/api/portal — the kindergarten portal (CLAUDE.md §8 B2B): sign-up, the dashboard, the school logo, classes.

A school signs up with its details and gets a `school_admin` account right away; the organization stays
`pending` until our team approves it in the admin, and until then only the dashboard answers.
"""

import io
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Request, Response, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select

from qamra_api import ratelimit, runtime_settings
from qamra_api.auth import service as auth
from qamra_api.auth.router import client_ip, set_session_cookies
from qamra_api.deps import RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.portal.access import School, SchoolAdmin, SchoolMember, class_book_of, own_classroom
from qamra_api.portal.status import class_states, stage_counts
from qamra_api.uploads import read_upload
from qamra_api.validation import PHONE
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Classroom,
    Locale,
    Organization,
    OrgStatus,
    UserRole,
)

router = APIRouter(prefix="/api/portal", tags=["portal"])
SIGNUPS_PER_IP_PER_HOUR = 5
LOGO_MAX_SIDE = 1200


def _squash(v: str) -> str:
    v = " ".join(v.split())
    if not v:
        raise ValueError("empty")
    return v


class SignupIn(BaseModel):
    school_name: str = Field(min_length=2, max_length=200)
    contact_name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=100)
    phone: str = Field(max_length=32)
    email: EmailStr
    password: str = Field(max_length=128)
    address: str | None = Field(default=None, max_length=300)
    country: Literal["PS", "JO"] = "PS"
    locale: Locale = Locale.ar

    _names = field_validator("school_name", "contact_name", "city")(_squash)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE.match(v):
            raise ValueError("invalid phone")
        return v


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    country: str
    city: str | None
    phone: str | None
    address: str | None
    has_logo: bool
    approved_at: datetime | None


class ClassSummary(BaseModel):
    id: uuid.UUID
    name: str
    teacher_name: str | None
    school_year: str | None
    children: int
    stages: dict[str, int]
    book_status: str | None
    book_line: str | None


class MeOut(BaseModel):
    name: str
    email: str
    org: OrgOut
    classes: list[ClassSummary]
    kpis: dict[str, int]


def _org_out(org: Organization) -> OrgOut:
    return OrgOut(
        id=org.id,
        name=org.name,
        status=org.status.value,
        country=org.country,
        city=org.city,
        phone=org.phone,
        address=org.address,
        has_logo=bool(org.logo_key),
        approved_at=org.approved_at,
    )


async def _summary(db: SessionDep, room: Classroom) -> tuple[ClassSummary, int]:
    cb = await class_book_of(db, room)
    states = await class_states(db, room, cb.art_style if cb else None)
    ready = 0
    if cb is not None:
        ready = len(
            (
                await db.execute(
                    select(Book.id).where(
                        Book.generation["class_book_id"].astext == str(cb.id),
                        Book.status.in_((BookStatus.in_review, BookStatus.approved)),
                    )
                )
            ).all()
        )
    summary = ClassSummary(
        id=room.id,
        name=room.name,
        teacher_name=room.teacher_name,
        school_year=room.school_year,
        children=len(states),
        stages=stage_counts(states),
        book_status=cb.status.value if cb else None,
        book_line=cb.line if cb else None,
    )
    return summary, ready


async def _me(db: SessionDep, school: School) -> MeOut:
    rooms = (
        (
            await db.execute(
                select(Classroom).where(Classroom.organization_id == school.org.id).order_by(Classroom.name)
            )
        )
        .scalars()
        .all()
    )
    classes, ready = [], 0
    if school.org.status == OrgStatus.approved:
        for room in rooms:
            summary, n = await _summary(db, room)
            classes.append(summary)
            ready += n
    kpis = {
        "children": sum(c.children for c in classes),
        "consent": sum(c.stages["consent"] + c.stages["photo"] + c.stages["approved"] for c in classes),
        "approved": sum(c.stages["approved"] for c in classes),
        "books_ready": ready,
    }
    return MeOut(
        name=school.user.full_name,
        email=school.user.email,
        org=_org_out(school.org),
        classes=classes,
        kpis=kpis,
    )


@router.post("/signup", status_code=201)
async def signup(
    body: SignupIn,
    request: Request,
    response: Response,
    db: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> MeOut:
    """A kindergarten asks to join: the organization waits for our approval; the account works at once."""
    if not (await runtime_settings.current(db, settings)).values.get("registration_open", True):
        raise ApiError("registration_closed", 403)
    if await ratelimit.hit(redis, f"rl:portal-signup:{client_ip(request)}", 3600) > SIGNUPS_PER_IP_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    org = Organization(
        name=body.school_name,
        status=OrgStatus.pending,
        country=body.country,
        city=body.city,
        phone=body.phone,
        address=" ".join(body.address.split()) if body.address else None,
    )
    db.add(org)
    await db.flush()
    user = await auth.register(
        db,
        email=body.email,
        password=body.password,
        full_name=body.contact_name,
        locale=body.locale,
        role=UserRole.school_admin,
    )
    user.organization_id, user.phone = org.id, body.phone
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="organization.signup",
            entity_type="organization",
            entity_id=str(org.id),
        )
    )
    session = await auth.start_session(db, user, settings, request.headers.get("user-agent"), "register")
    set_session_cookies(response, session, settings)
    return await _me(db, School(user, org))


@router.get("/me")
async def me(school: SchoolMember, db: SessionDep) -> MeOut:
    return await _me(db, school)


class OrgIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=300)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v is not None and not PHONE.match(v.strip()):
            raise ValueError("invalid phone")
        return v.strip() if v else v


@router.patch("/org")
async def update_org(body: OrgIn, school: SchoolAdmin, db: SessionDep) -> MeOut:
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(school.org, field, " ".join(str(value).split()))
    await db.commit()
    return await _me(db, school)


def clean_logo(data: bytes) -> bytes:
    """PNG with its transparency, metadata dropped, at most 1200 px."""
    try:
        with Image.open(io.BytesIO(data)) as original:
            if original.format not in ("PNG", "JPEG", "WEBP"):
                raise ApiError("invalid_image", 422)
            img = original.convert("RGBA")
    except (UnidentifiedImageError, OSError) as e:
        raise ApiError("invalid_image", 422) from e
    img.thumbnail((LOGO_MAX_SIDE, LOGO_MAX_SIDE), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@router.post("/logo")
async def upload_logo(
    school: SchoolAdmin, db: SessionDep, storage: StorageDep, logo: Annotated[UploadFile, File()]
) -> MeOut:
    """The school logo for its class books' school page (private storage, like everything else)."""
    key = f"orgs/{school.org.id}/logo.png"
    storage.put(key, clean_logo(await read_upload(logo)), "image/png")
    school.org.logo_key = key
    await db.commit()
    return await _me(db, school)


@router.get("/logo")
async def logo(school: SchoolAdmin, storage: StorageDep) -> Response:
    if not school.org.logo_key:
        raise ApiError("not_found", 404)
    return Response(
        storage.get(school.org.logo_key),
        media_type="image/png",
        headers={"Cache-Control": "private, no-store"},
    )


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    teacher_name: str | None = Field(default=None, max_length=120)
    school_year: str | None = Field(default=None, max_length=16)

    _name = field_validator("name")(_squash)


@router.get("/classes")
async def classes(school: SchoolAdmin, db: SessionDep) -> list[ClassSummary]:
    return (await _me(db, school)).classes


@router.post("/classes", status_code=201)
async def create_class(body: ClassIn, school: SchoolAdmin, db: SessionDep) -> ClassSummary:
    room = Classroom(
        organization_id=school.org.id,
        name=body.name,
        teacher_name=" ".join(body.teacher_name.split()) if body.teacher_name else None,
        school_year=body.school_year.strip() if body.school_year else None,
    )
    db.add(room)
    await db.commit()
    return (await _summary(db, room))[0]


@router.patch("/classes/{classroom_id}")
async def update_class(
    classroom_id: uuid.UUID, body: ClassIn, school: SchoolAdmin, db: SessionDep
) -> ClassSummary:
    room = await own_classroom(db, school, classroom_id)
    room.name = body.name
    room.teacher_name = " ".join(body.teacher_name.split()) if body.teacher_name else None
    room.school_year = body.school_year.strip() if body.school_year else None
    await db.commit()
    return (await _summary(db, room))[0]
