import io
import uuid
from decimal import Decimal
from pathlib import Path

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from PIL import Image
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed import upsert_themes
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Child,
    ChildPhoto,
    Consent,
    Gender,
    GenerationCost,
    Locale,
    PageStatus,
    Theme,
    User,
)
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


def _jobs(app: FastAPI) -> list[tuple[str, tuple[object, ...]]]:
    q = Queue("generation", connection=app.state.rq_redis)
    return [(j.func_name, j.args) for j in q.jobs]


def _blank_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (800, 800), "white").save(buf, format="PNG")
    return buf.getvalue()


async def _sample_form(client: AsyncClient, consent: bool = True, photo: bytes | None = None) -> object:
    return await client.post(
        "/api/admin/samples",
        data={
            "theme": "first-day",
            "name": "سلمى",
            "gender": "f",
            "age": "5",
            "hijab": "true",
            "consent": "true" if consent else "false",
            "message": "نحبّكِ",
            "offline": "true",
        },
        files=[("photos", ("kid.png", photo or FACE.read_bytes(), "image/png"))],
    )


async def test_sample_needs_consent_and_a_usable_photo(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await upsert_themes(adb)
    await make_admin(client, adb)
    r = await _sample_form(client, consent=False)
    assert r.status_code == 422 and r.json()["error"]["code"] == "consent_required"  # type: ignore[attr-defined]
    r = await _sample_form(client, photo=_blank_png())
    assert r.status_code == 422 and r.json()["error"]["details"]["reason"] == "no_face"  # type: ignore[attr-defined]
    assert _jobs(app) == []


async def test_sample_creates_rows_private_photo_and_a_job(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await make_admin(client, adb)
    r = await _sample_form(client)
    assert r.status_code == 201, r.text  # type: ignore[attr-defined]
    book = await adb.get(Book, uuid.UUID(r.json()["book_id"]))  # type: ignore[attr-defined]
    assert book is not None and book.is_sample and book.status == BookStatus.generating
    assert book.budget_usd == Decimal("3.00") and book.parent_message == "نحبّكِ"
    assert book.generation["offline"] == "sketch"
    child = await adb.get(Child, book.child_id)
    assert child is not None and child.wears_hijab and child.is_sample
    consent = (await adb.execute(select(Consent).where(Consent.child_id == child.id))).scalar_one()
    assert consent.consent_text_version.startswith("sample-")
    photo = (await adb.execute(select(ChildPhoto).where(ChildPhoto.child_id == child.id))).scalar_one()
    assert photo.storage_key and photo.storage_key.startswith(f"children/{child.id}/")
    stored = Image.open(io.BytesIO(storage.get(photo.storage_key)))
    assert stored.format == "JPEG" and not stored.getexif()  # re-encoded, metadata dropped
    assert _jobs(app) == [("qamra_worker.jobs.books.generate_book", (str(book.id), "final"))]


async def _seed_book(
    adb: AsyncSession, status: BookStatus = BookStatus.in_review, cost: str = "2.10", offline: bool = False
) -> Book:
    theme = (await adb.execute(select(Theme).where(Theme.slug == "first-day"))).scalar_one_or_none()
    if theme is None:
        await upsert_themes(adb)
        theme = (await adb.execute(select(Theme).where(Theme.slug == "first-day"))).scalar_one()
    owner = (await adb.execute(select(User).where(User.email == "admin@example.com"))).scalar_one()
    child = Child(
        guardian_user_id=owner.id, first_name="ليان", gender=Gender.f, birth_year=2021, is_sample=True
    )
    adb.add(child)
    await adb.flush()
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=theme.version,
        language=Locale.ar,
        art_style="watercolor",
        status=status,
        is_sample=True,
        cost_usd=Decimal(cost),
        budget_usd=Decimal("3.00"),
        title="ليان",
        generation={
            "plan": [
                {"number": 1, "kind": "title", "side": "left", "beat": None, "half": None},
                {"number": 2, "kind": "story", "side": "right", "beat": 1, "half": None},
            ],
            "mode": "final",
            **({"offline": "sketch"} if offline else {}),
        },
        preflight={"interior": {"passed": True}, "cover": {"passed": True}},
        pdf_interior_key="children/x/books/y/files/interior.pdf",
        pdf_cover_key="children/x/books/y/files/cover.pdf",
        qa_summary={"avg_likeness": 0.9, "needs_review": 1},
    )
    adb.add(book)
    await adb.flush()
    adb.add_all(
        [
            BookPage(
                book_id=book.id,
                index=0,
                status=PageStatus.ok,
                layout="cover",
                qa={"likeness": 9},
                attempts=[{"attempt": 1}],
                qa_score=Decimal("0.95"),
            ),
            BookPage(
                book_id=book.id,
                index=1,
                status=PageStatus.needs_review,
                layout="full",
                text="نص",
                original_text="نص",
                qa={"likeness": 6},
                attempts=[{"attempt": 1}, {"attempt": 2, "why": "qa"}, {"attempt": 3, "why": "qa"}],
                flags=["face", "fallback_used"],
                qa_score=Decimal("0.6"),
            ),
            GenerationCost(
                book_id=book.id,
                child_id=child.id,
                step="page:1:a1",
                provider="sketch" if offline else "fal",
                model="sketch" if offline else "fal-ai/nano-banana-2/edit",
                units={},
                usd=Decimal("0" if offline else "0.08"),
            ),
            GenerationCost(
                book_id=book.id,
                child_id=child.id,
                step="qa:1:a1",
                provider="fake" if offline else "anthropic",
                model="fake" if offline else "claude-haiku-4-5-20251001",
                units={},
                usd=Decimal("0" if offline else "0.004"),
            ),
        ]
    )
    await adb.commit()
    return book


async def test_queue_detail_and_review_actions(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    await make_admin(client, adb)
    book = await _seed_book(adb)
    cards = (await client.get("/api/admin/books?view=review")).json()
    assert [c["id"] for c in cards] == [str(book.id)] and cards[0]["needs_review"] == 1
    assert cards[0]["theme_title"] == "أوّل يوم في الروضة"  # catalog name, never a raw "{name}" template
    detail = (await client.get(f"/api/admin/books/{book.id}")).json()
    page1 = next(p for p in detail["pages"] if p["beat"] == 1)
    assert (
        page1["pages"] == [2]
        and page1["likeness"] == 6
        and page1["attempts"] == 3
        and "face" in page1["flags"]
    )
    assert detail["costs"]["page"] == 0.08 and detail["files"]["interior"]

    r = await client.patch(f"/api/admin/books/{book.id}/pages/1", json={"text": "  نصٌّ   جديد "})
    assert r.status_code == 200 and r.json()["text"] == "نصٌّ جديد"
    assert _jobs(app)[-1] == ("qamra_worker.jobs.books.rerender", (str(book.id),))
    assert (await client.post(f"/api/admin/books/{book.id}/approve")).status_code == 409  # busy re-rendering

    book.status = BookStatus.in_review
    await adb.commit()
    r = await client.post(f"/api/admin/books/{book.id}/redraw", json={"beats": [1, 1]})
    assert r.status_code == 202 and r.json()["queued"] == [1]
    assert _jobs(app)[-1] == ("qamra_worker.jobs.books.redraw", (str(book.id), [1]))

    book.status = BookStatus.in_review
    await adb.commit()
    r = await client.post(f"/api/admin/books/{book.id}/approve")
    assert r.status_code == 200 and r.json()["status"] == "approved"
    audit = (await adb.execute(select(AuditLog).where(AuditLog.action == "admin.book_approved"))).scalar_one()
    assert audit.entity_id == str(book.id)


async def test_redraw_respects_the_budget_cap(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    book = await _seed_book(adb, cost="2.97")
    r = await client.post(f"/api/admin/books/{book.id}/redraw", json={"beats": [1]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "budget_exceeded"
    assert (
        await client.post(f"/api/admin/books/{book.id}/budget", json={"budget_usd": "3.50"})
    ).status_code == 200
    assert (await client.post(f"/api/admin/books/{book.id}/redraw", json={"beats": [1]})).status_code == 202


async def test_approval_needs_passing_preflight(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    book = await _seed_book(adb)
    book.preflight = {"interior": {"passed": False}, "cover": {"passed": True}}
    await adb.commit()
    r = await client.post(f"/api/admin/books/{book.id}/approve")
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_ready"


async def test_cost_dashboard(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    await _seed_book(adb, cost="2.10")
    await _seed_book(adb, status=BookStatus.approved, cost="1.90")
    await _seed_book(adb, cost="0", offline=True)  # placeholder art: not part of the averages
    m = (await client.get("/api/admin/metrics?days=30")).json()
    assert m["books"] == 2 and m["avg_cost_per_book"] == 2.0 and m["within_cap_ratio"] == 1.0
    theme = m["themes"][0]
    assert theme["slug"] == "first-day" and theme["redraw_rate"] == 1.0 and theme["fallback_rate"] == 0.5
    assert theme["title"] == "أوّل يوم في الروضة"
    assert m["by_step"]["page"] == 0.16 and m["daily"]


async def test_parents_cannot_reach_admin_books(client: AsyncClient) -> None:
    await register(client)
    assert (await client.get("/api/admin/books")).status_code == 403
    assert (await client.get("/api/admin/metrics")).status_code == 403
