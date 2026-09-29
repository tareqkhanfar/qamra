"""/api/admin/portal — kindergartens in the admin (CLAUDE.md §8 Admin: "organizations and pricing"):
sign-up approval with an audit entry, and every class book with its per-child coverage and print bundle.

The bundle of a class (Addendum 1 §2): each child's interior and cover as `{school}-{class}-{child}.pdf`, and
one combined print file (cover then interior, child after child). Files stay in private storage and are
streamed from here to staff only.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from qamra_api.deps import AdminUser, SessionDep, StorageDep, require_admin, require_permission
from qamra_api.errors import ApiError
from qamra_api.portal.ordering import currency_of, price_list_for
from qamra_api.routers import admin_books
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Child,
    Classroom,
    Order,
    Organization,
    OrgStatus,
    PrintBatch,
    User,
    UserRole,
)
from qamra_core.db.portal import ClassBook
from qamra_core.storage import ObjectNotFound

router = APIRouter(prefix="/api/admin/portal", tags=["admin"], dependencies=[Depends(require_admin)])


class Contact(BaseModel):
    name: str
    email: str
    phone: str | None


class OrgRow(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    country: str
    city: str | None
    phone: str | None
    address: str | None
    created_at: datetime
    approved_at: datetime | None
    contacts: list[Contact]
    classes: int
    children: int
    price_list: str | None


async def _org_row(db: SessionDep, org: Organization) -> OrgRow:
    users = (
        await db.execute(
            select(User).where(User.organization_id == org.id, User.role == UserRole.school_admin)
        )
    ).scalars()
    classes = (
        await db.execute(
            select(func.count()).select_from(Classroom).where(Classroom.organization_id == org.id)
        )
    ).scalar_one()
    children = (
        await db.execute(select(func.count()).select_from(Child).where(Child.organization_id == org.id))
    ).scalar_one()
    price_list = await price_list_for(db, org, currency_of(org))
    return OrgRow(
        id=org.id,
        name=org.name,
        status=org.status.value,
        country=org.country,
        city=org.city,
        phone=org.phone,
        address=org.address,
        created_at=org.created_at,
        approved_at=org.approved_at,
        contacts=[Contact(name=u.full_name, email=u.email, phone=u.phone) for u in users],
        classes=int(classes),
        children=int(children),
        price_list=(price_list.name if price_list else None),
    )


@router.get("/organizations", dependencies=[Depends(require_permission("organizations.view"))])
async def organizations(db: SessionDep, status: OrgStatus | None = None) -> list[OrgRow]:
    q = select(Organization).order_by(Organization.created_at.desc())
    if status is not None:
        q = q.where(Organization.status == status)
    return [await _org_row(db, org) for org in (await db.execute(q.limit(300))).scalars()]


class DecisionIn(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


async def _decide(
    db: SessionDep, admin: AdminUser, org_id: uuid.UUID, to: OrgStatus, reason: str | None
) -> OrgRow:
    org = await db.get(Organization, org_id)
    if org is None:
        raise ApiError("not_found", 404)
    before = org.status
    org.status = to
    org.approved_at = datetime.now(UTC) if to == OrgStatus.approved else org.approved_at
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action=f"organization.{to.value}",
            entity_type="organization",
            entity_id=str(org.id),
            data={"from": before.value, "reason": reason},
        )
    )
    await db.commit()
    return await _org_row(db, org)


@router.post("/organizations/{org_id}/approve", dependencies=[Depends(require_permission("organizations"))])
async def approve_org(org_id: uuid.UUID, body: DecisionIn, admin: AdminUser, db: SessionDep) -> OrgRow:
    return await _decide(db, admin, org_id, OrgStatus.approved, body.reason)


@router.post("/organizations/{org_id}/reject", dependencies=[Depends(require_permission("organizations"))])
async def reject_org(org_id: uuid.UUID, body: DecisionIn, admin: AdminUser, db: SessionDep) -> OrgRow:
    return await _decide(db, admin, org_id, OrgStatus.rejected, body.reason)


# ---- class books and their print bundles ------------------------------------------------------------------


class CoverageRow(BaseModel):
    child_id: uuid.UUID
    name: str
    book_id: uuid.UUID
    status: str
    appearances: int
    recognized: int
    unrecognized_pages: list[int]
    flags: list[str]
    files: bool


class BundleFile(BaseModel):
    name: str  # {school}-{class}-{child}.pdf, …-cover.pdf, …-print.pdf
    path: str  # the download path under this API


class ClassBookRow(BaseModel):
    id: uuid.UUID
    school: str
    classroom: str
    status: str
    line: str
    copies: int
    approved: int  # passed our print approval
    in_review: int
    order_code: str | None
    order_status: str | None
    print_batch: str | None
    cost_usd: Decimal
    updated_at: datetime
    combined: bool


async def _copies(db: SessionDep, cb: ClassBook) -> list[tuple[Book, Child]]:
    rows = (
        await db.execute(
            select(Book, Child)
            .join(Child, Child.id == Book.child_id)
            .where(Book.generation["class_book_id"].astext == str(cb.id))
            .order_by(Child.first_name)
        )
    ).all()
    return [(b, c) for b, c in rows]


async def _row(db: SessionDep, cb: ClassBook) -> ClassBookRow:
    org = await db.get(Organization, cb.organization_id)
    room = await db.get(Classroom, cb.classroom_id)
    order = await db.get(Order, cb.order_id) if cb.order_id else None
    batch = await db.get(PrintBatch, order.print_batch_id) if order and order.print_batch_id else None
    copies = await _copies(db, cb)
    return ClassBookRow(
        id=cb.id,
        school=org.name if org else "",
        classroom=room.name if room else "",
        status=cb.status.value,
        line=cb.line,
        copies=len(copies),
        approved=sum(b.status in (BookStatus.approved, BookStatus.printed) for b, _ in copies),
        in_review=sum(b.status == BookStatus.in_review for b, _ in copies),
        order_code=order.code if order else None,
        order_status=order.status.value if order else None,
        print_batch=batch.status.value if batch else None,
        cost_usd=cb.cost_usd or Decimal("0"),
        updated_at=cb.updated_at,
        combined=bool((cb.bundle or {}).get("combined_key")),
    )


@router.get("/class-books", dependencies=[Depends(require_permission("books.view"))])
async def class_books(db: SessionDep) -> list[ClassBookRow]:
    rows = (await db.execute(select(ClassBook).order_by(ClassBook.updated_at.desc()).limit(200))).scalars()
    return [await _row(db, cb) for cb in rows]


class ClassBookDetail(BaseModel):
    book: ClassBookRow
    coverage: list[CoverageRow]
    files: list[BundleFile]
    min_appearances: int


def _names(cb: ClassBook) -> dict[str, str]:
    """child id → file stem, as the print files were rendered."""
    return {str(c["child_id"]): str(c["stem"]) for c in (cb.bundle or {}).get("copies", [])}


async def _class_book(db: SessionDep, class_book_id: uuid.UUID) -> ClassBook:
    cb = await db.get(ClassBook, class_book_id)
    if cb is None:
        raise ApiError("not_found", 404)
    return cb


@router.get("/class-books/{class_book_id}", dependencies=[Depends(require_permission("books.view"))])
async def class_book(class_book_id: uuid.UUID, db: SessionDep) -> ClassBookDetail:
    """Per-child coverage for the human review (Addendum 1 §2) and the class's print bundle."""
    cb = await _class_book(db, class_book_id)
    stems = _names(cb)
    base = f"/api/admin/portal/class-books/{cb.id}/files"
    coverage, files = [], []
    if (cb.bundle or {}).get("combined_key"):
        files.append(
            BundleFile(name=f"{cb.bundle.get('stem') or 'class'}-print.pdf", path=f"{base}/combined")
        )
    for book, child in await _copies(db, cb):
        summary: dict[str, Any] = book.qa_summary or {}
        coverage.append(
            CoverageRow(
                child_id=child.id,
                name=child.first_name,
                book_id=book.id,
                status=book.status.value,
                appearances=int(summary.get("appearances", 0)),
                recognized=int(summary.get("recognized", 0)),
                unrecognized_pages=list(summary.get("unrecognized_pages") or []),
                flags=list(book.flags or []),
                files=bool(book.pdf_interior_key and book.pdf_cover_key),
            )
        )
        stem = stems.get(str(child.id))
        if stem and book.pdf_interior_key and book.pdf_cover_key:
            files.append(BundleFile(name=f"{stem}.pdf", path=f"{base}/{child.id}-interior"))
            files.append(BundleFile(name=f"{stem}-cover.pdf", path=f"{base}/{child.id}-cover"))
    return ClassBookDetail(
        book=await _row(db, cb), coverage=coverage, files=files, min_appearances=cb.min_appearances
    )


def _download(storage: StorageDep, key: str | None, name: str) -> Response:
    if not key:
        raise ApiError("not_found", 404)
    try:
        data = storage.get(key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    ascii_name = name.encode("ascii", "ignore").decode() or "class-book.pdf"
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/class-books/{class_book_id}/files/{file}", dependencies=[Depends(require_permission("print"))])
async def bundle_file(class_book_id: uuid.UUID, file: str, db: SessionDep, storage: StorageDep) -> Response:
    """One file of the class's print bundle: `combined`, or `{child_id}-interior` / `{child_id}-cover`."""
    cb = await _class_book(db, class_book_id)
    if file == "combined":
        return _download(
            storage, (cb.bundle or {}).get("combined_key"), f"{cb.bundle.get('stem') or 'class'}-print.pdf"
        )
    child_id, _, kind = file.rpartition("-")
    stem = _names(cb).get(child_id)
    if kind not in ("interior", "cover") or stem is None:
        raise ApiError("not_found", 404)
    book = next((b for b, c in await _copies(db, cb) if str(c.id) == child_id), None)
    if book is None:
        raise ApiError("not_found", 404)
    if kind == "interior":
        return _download(storage, book.pdf_interior_key, f"{stem}.pdf")
    return _download(storage, book.pdf_cover_key, f"{stem}-cover.pdf")


class BulkOut(BaseModel):
    approved: int
    not_ready: list[str]  # children whose copy can't pass the print approval yet
    detail: ClassBookDetail


@router.post(
    "/class-books/{class_book_id}/approve", dependencies=[Depends(require_permission("books.review"))]
)
async def approve_copies(class_book_id: uuid.UUID, admin: AdminUser, db: SessionDep) -> BulkOut:
    """Print approval for every copy the school approved, through the review queue's own approval (the same
    preflight and file checks, the same audit entry per book)."""
    cb = await _class_book(db, class_book_id)
    approved, waiting = 0, []
    for book, child in await _copies(db, cb):
        if book.status != BookStatus.in_review:
            continue
        try:
            await admin_books.approve(book.id, admin, db)
            approved += 1
        except ApiError:
            waiting.append(child.first_name)
    return BulkOut(approved=approved, not_ready=waiting, detail=await class_book(class_book_id, db))
