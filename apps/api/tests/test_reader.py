"""The web reader and share links: the owner, a share token, revoked and expired links, someone else's book,
a preview, and what a public link may show (the book only)."""

import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from api_helpers import register
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers import reader
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Child,
    Gender,
    Locale,
    SafetyStatus,
    ShareToken,
    Theme,
)
from qamra_core.storage import ObjectStorage


def _png(color: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(buf, format="PNG")
    return buf.getvalue()


async def _book(
    adb: AsyncSession, storage: ObjectStorage, user_id: str, status: BookStatus = BookStatus.in_review
) -> Book:
    child = Child(guardian_user_id=uuid.UUID(user_id), first_name="ليان", gender=Gender.f, birth_year=2021)
    theme = Theme(
        slug=f"t-{uuid.uuid4().hex[:8]}",
        title_ar="حارس النجوم",
        title_en="Star keeper",
        age_min=3,
        age_max=7,
        definition={},
    )
    adb.add_all([child, theme])
    await adb.flush()
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=1,
        created_by_user_id=uuid.UUID(user_id),
        language=Locale.ar,
        art_style="watercolor",
        status=status,
        title="ليان وحارس النجوم",
    )
    adb.add(book)
    await adb.flush()
    for beat in range(0, 5):
        key = f"children/{child.id}/books/{book.id}/raw/{beat:02d}.png"
        storage.put(key, _png("navy"), "image/png")
        adb.add(
            BookPage(
                book_id=book.id,
                index=beat,
                text=None if beat == 0 else f"صفحة {beat}",
                layout="cover" if beat == 0 else "split",
                image_key=key,
                preview_image_key=key if beat <= 2 else None,
                safety_status=SafetyStatus.failed if beat == 4 else SafetyStatus.passed,
            )
        )
    await adb.commit()
    return book


async def test_the_owner_reads_a_finished_book(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    r = await client.get(f"/api/books/{book.id}/reader")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["kind"] == "final" and data["title"] == "ليان وحارس النجوم" and data["language"] == "ar"
    assert [p["beat"] for p in data["pages"]] == [0, 1, 2, 3]  # page 4 failed the safety check: never shown
    assert data["can_share"] and data["share"] is None and data["child_name"] == "ليان"
    picture = await client.get(data["pages"][1]["image"])
    assert picture.status_code == 200 and picture.headers["content-type"] == "image/png"
    assert (await client.get(f"/api/books/{book.id}/reader/pages/4")).status_code == 404


async def test_a_preview_shows_its_drawn_pages_and_cannot_be_shared(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"], BookStatus.preview)
    data = (await client.get(f"/api/books/{book.id}/reader")).json()
    assert data["kind"] == "preview" and [p["beat"] for p in data["pages"]] == [0, 1, 2]
    assert (
        not data["can_share"]
        and (await client.get(f"/api/books/{book.id}/reader/pages/3")).status_code == 404
    )
    r = await client.post(f"/api/books/{book.id}/share", json={"days": 7})
    assert r.status_code == 409 and r.json()["error"]["code"] == "book_not_ready"


async def test_unready_and_other_peoples_books(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    owner = await register(client)
    book = await _book(adb, storage, owner["id"])
    drafting = await _book(adb, storage, owner["id"], BookStatus.generating)
    r = await client.get(f"/api/books/{drafting.id}/reader")
    assert r.status_code == 409 and r.json()["error"]["code"] == "book_not_ready"
    await client.post("/api/auth/logout")
    assert (await client.get(f"/api/books/{book.id}/reader")).status_code == 401
    await register(client, email="other.mom@example.com")
    for path in (f"/api/books/{book.id}/reader", f"/api/books/{book.id}/reader/pages/1"):
        assert (await client.get(path)).status_code == 404  # someone else's book looks like no book
    r = await client.post(f"/api/books/{book.id}/share", json={"days": 30})
    assert r.status_code == 404


async def test_share_links_show_the_book_only_until_revoked(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    r = await client.post(f"/api/books/{book.id}/share", json={"days": 7})
    assert r.status_code == 201, r.text
    share = r.json()
    token = share["token"]
    expires = datetime.fromisoformat(share["expires_at"])
    assert timedelta(days=6, hours=23) < expires - datetime.now(UTC) <= timedelta(days=7)
    assert (await client.get(f"/api/books/{book.id}/reader")).json()["share"]["token"] == token

    await client.post("/api/auth/logout")  # a relative with the link, no account
    r = await client.get(f"/api/shared/{token}")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store" and r.headers["referrer-policy"] == "no-referrer"
    data = r.json()
    assert set(data) == {"title", "language", "kind", "pages", "expires_at"}  # no ids, child or parent
    assert str(book.id) not in r.text and str(book.child_id) not in r.text
    assert [p["beat"] for p in data["pages"]] == [0, 1, 2, 3]
    assert all(p["image"].startswith(f"/api/shared/{token}/pages/") for p in data["pages"])
    picture = await client.get(data["pages"][2]["image"])
    assert picture.status_code == 200 and picture.headers["content-type"] == "image/png"
    assert (await client.get(f"/api/shared/{token}/pages/4")).status_code == 404  # failed the safety check

    # a new link replaces the old one; revoking turns the link off
    await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "moonlight-2026"}
    )
    second = (await client.post(f"/api/books/{book.id}/share", json={"days": 30})).json()
    gone = await client.get(f"/api/shared/{token}")
    assert gone.status_code == 404 and gone.json()["error"]["code"] == "share_unavailable"
    assert (await client.get(f"/api/shared/{second['token']}")).status_code == 200
    r = await client.delete(f"/api/books/{book.id}/share/{second['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/api/shared/{second['token']}")).status_code == 404
    assert (await client.get(f"/api/shared/{second['token']}/pages/1")).status_code == 404
    assert (await client.get(f"/api/books/{book.id}/reader")).json()["share"] is None


async def test_expired_unknown_and_malformed_links(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    token = (await client.post(f"/api/books/{book.id}/share", json={"days": 7})).json()["token"]
    row = (await adb.execute(select(ShareToken).where(ShareToken.token == token))).scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await adb.commit()
    for bad in (token, "x" * 32, "not a token", "a" * 10):
        r = await client.get(f"/api/shared/{bad}")
        assert r.status_code == 404 and r.json()["error"]["code"] == "share_unavailable", bad
    r = await client.post(f"/api/books/{book.id}/share", json={"days": 365})
    assert r.status_code == 422  # 7, 30 or 90 days only


async def test_shared_views_are_rate_limited(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    token = (await client.post(f"/api/books/{book.id}/share", json={"days": 7})).json()["token"]
    monkeypatch.setattr(reader, "SHARED_VIEWS_PER_IP_PER_HOUR", 2)
    codes = [(await client.get(f"/api/shared/{token}")).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
