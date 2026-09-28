"""The signed-in parent's children and books (account page)."""

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from qamra_core.db.models import Book, BookStatus, Child, Gender, Locale, Theme
from sqlalchemy import select

from qamra_api.deps import CurrentUser, SessionDep

router = APIRouter(prefix="/api", tags=["family"])


class ChildOut(BaseModel):
    id: uuid.UUID
    first_name: str
    gender: Gender
    birth_year: int


class BookOut(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    title: str | None
    theme_slug: str
    language: Locale
    status: BookStatus
    updated_at: datetime


@router.get("/children")
async def my_children(user: CurrentUser, db: SessionDep) -> list[ChildOut]:
    rows = (
        (await db.execute(select(Child).where(Child.guardian_user_id == user.id).order_by(Child.created_at)))
        .scalars()
        .all()
    )
    return [
        ChildOut(id=c.id, first_name=c.first_name, gender=c.gender, birth_year=c.birth_year) for c in rows
    ]


@router.get("/books")
async def my_books(user: CurrentUser, db: SessionDep) -> list[BookOut]:
    rows = (
        await db.execute(
            select(Book, Theme.slug)
            .join(Child, Child.id == Book.child_id)
            .join(Theme, Theme.id == Book.theme_id)
            .where(Child.guardian_user_id == user.id)
            .order_by(Book.updated_at.desc())
        )
    ).all()
    return [
        BookOut(
            id=b.id,
            child_id=b.child_id,
            title=b.title,
            theme_slug=slug,
            language=b.language,
            status=b.status,
            updated_at=b.updated_at,
        )
        for b, slug in rows
    ]
