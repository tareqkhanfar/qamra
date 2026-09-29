"""Shared steps for the kindergarten portal tests: a school that signed up and was approved, a class with
children, parents who accepted their invites, and what the worker leaves behind after a class batch."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import (
    Book,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Locale,
    Organization,
    OrgStatus,
)
from qamra_core.db.portal import ClassBook, ClassBookStatus
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
HEADER = "اسم الطفل,الجنس,سنة الميلاد,اسم ولي الأمر,جوال ولي الأمر,بريد ولي الأمر\n"


def signup(email: str = "sanaa@moon-kg.example", school: str = "روضة القمر") -> dict[str, str]:
    return {
        "school_name": school,
        "contact_name": "أ. سناء",
        "city": "البيرة",
        "phone": "+970 59 111 2222",
        "email": email,
        "password": "moonlight-2026",
        "address": "شارع الإرسال، قرب الحديقة",
    }


@asynccontextmanager
async def browser(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Another person on another device: their own cookies."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers={"X-Qamra-Client": "test"}
    ) as c:
        yield c


async def approved_school(client: AsyncClient, adb: AsyncSession, **kw: str) -> dict:  # type: ignore[type-arg]
    r = await client.post("/api/portal/signup", json=signup(**kw))
    assert r.status_code == 201, r.text
    org = await adb.get(Organization, uuid.UUID(r.json()["org"]["id"]))
    assert org is not None
    org.status, org.approved_at = OrgStatus.approved, datetime.now(UTC)
    await adb.commit()
    return r.json()  # type: ignore[no-any-return]


def csv_rows(*rows: str) -> bytes:
    return (HEADER + "".join(r + "\n" for r in rows)).encode("utf-8")


async def approved_character(
    adb: AsyncSession, storage: ObjectStorage, child_id: str, style: str
) -> Character:
    """Another parent went through the invite (what their own steps leave in the database)."""
    child = await adb.get(Child, uuid.UUID(child_id))
    assert child is not None
    character = Character(
        child_id=child.id, art_style=style, status=CharacterStatus.approved, approved_at=datetime.now(UTC)
    )
    adb.add(character)
    await adb.flush()
    character.sheet_image_key = f"children/{child.id}/characters/{character.id}.png"
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()
    return character


async def worker_batch(adb: AsyncSession, storage: ObjectStorage, class_book_id: str) -> None:
    """What `jobs.classbooks.generate_class_book` leaves: a copy per child with print files that passed
    preflight, waiting for the school (the real job runs in apps/worker/tests/test_classbooks.py)."""
    cb = await adb.get(ClassBook, uuid.UUID(class_book_id))
    assert cb is not None
    copies = []
    for child_id in cb.plan["children"]:
        character = (
            await adb.execute(
                select(Character).where(
                    Character.child_id == uuid.UUID(child_id), Character.status == CharacterStatus.approved
                )
            )
        ).scalar_one()
        book = Book(
            child_id=uuid.UUID(child_id),
            character_id=character.id,
            theme_id=cb.theme_id,
            theme_version=1,
            language=Locale.ar,
            art_style=cb.art_style,
            status=BookStatus.preview,
            generation={"line": "class", "class_book_id": str(cb.id)},
            preflight={"interior": {"passed": True}, "cover": {"passed": True}},
            qa_summary={"appearances": 2, "recognized": 2},
        )
        adb.add(book)
        await adb.flush()
        book.pdf_interior_key = f"children/{child_id}/books/{book.id}/files/interior.pdf"
        book.pdf_cover_key = f"children/{child_id}/books/{book.id}/files/cover.pdf"
        for key in (book.pdf_interior_key, book.pdf_cover_key):
            storage.put(key, b"%PDF-1.4 class copy", "application/pdf")
        copies.append({"child_id": child_id, "book_id": str(book.id), "stem": f"moon-kg-{child_id[:4]}"})
    cb.status = ClassBookStatus.review
    cb.bundle = {
        "combined_key": f"orgs/{cb.organization_id}/combined.pdf",
        "copies": copies,
        "stem": "moon-kg",
    }
    storage.put(cb.bundle["combined_key"], b"%PDF-1.4 combined", "application/pdf")
    await adb.commit()
