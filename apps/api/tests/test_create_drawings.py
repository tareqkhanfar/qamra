"""Every drawing of the child is kept and choosable, and «ما الذي لا يشبهه؟» takes the parent's own words
(Tareq, 2026-10-10): a redraw never hides the earlier drawings, the parent can go back to one in any style,
and the one approved last is the child's character for every later book."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from api_helpers import register
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_core.db.models import AuditLog, Book, Character, CharacterStatus
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
CHILD = {"name": "آدم", "gender": "m", "age": 5}
WORKBOOK = "islamic-v1-softcover"  # an activity book that asks no English name


async def _child(client: AsyncClient) -> str:
    """A child with the guardian's consent and a photo, ready to be drawn."""
    r = await client.post("/api/create/children", json=CHILD)
    assert r.status_code == 201, r.text
    child_id: str = r.json()["id"]
    consent = {"accept": True, "version": CONSENT_VERSION}
    assert (await client.post(f"/api/create/children/{child_id}/consent", json=consent)).status_code == 200
    photo = [("photos", ("kid.png", FACE.read_bytes(), "image/png"))]
    assert (await client.post(f"/api/create/children/{child_id}/photos", files=photo)).status_code == 200
    return child_id


async def _draw(client: AsyncClient, child_id: str, **body: Any) -> dict[str, Any]:
    r = await client.post(f"/api/create/children/{child_id}/characters", json=body)
    assert r.status_code == 202, r.text
    out: dict[str, Any] = r.json()
    return out


async def _drawn(adb: AsyncSession, storage: ObjectStorage, character_id: str, minutes_ago: int) -> str:
    """What the worker does when the sheet is drawn; `minutes_ago` orders the drawings (one test transaction
    gives every row the same `now()`)."""
    character = await adb.get(Character, character_id)
    assert character is not None
    character.sheet_image_key = f"children/{character.child_id}/characters/{character_id}.png"
    character.status = CharacterStatus.ready
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.execute(
        update(Character)
        .where(Character.id == character.id)
        .values(created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago))
    )
    await adb.commit()
    return character.sheet_image_key


async def _approve(client: AsyncClient, character_id: str) -> dict[str, Any]:
    r = await client.post(f"/api/create/characters/{character_id}/approve")
    assert r.status_code == 200, r.text
    out: dict[str, Any] = r.json()
    return out


async def test_every_drawing_is_kept_and_listed_newest_first(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _child(client)
    first = await _draw(client, child_id, style="3d")
    await _drawn(adb, storage, first["id"], minutes_ago=30)
    second = await _draw(client, child_id, style="3d", fixes=["hair"], note="  شعره\n  أجعد  ", redraw=True)
    await _drawn(adb, storage, second["id"], minutes_ago=20)
    other = await _draw(client, child_id, style="watercolor", redraw=True)  # another style, to compare
    await _drawn(adb, storage, other["id"], minutes_ago=10)
    failed = await _draw(client, child_id, style="3d", redraw=True)
    await adb.execute(
        update(Character).where(Character.id == failed["id"]).values(status=CharacterStatus.failed)
    )
    await adb.commit()
    drawing = await _draw(client, child_id, style="3d", redraw=True)  # still being drawn: not listed yet

    r = await client.get(f"/api/create/children/{child_id}/characters")
    assert r.status_code == 200, r.text
    listed = r.json()
    assert [d["id"] for d in listed] == [other["id"], second["id"], first["id"]]
    assert [(d["style"], d["style_name_en"], d["style_name_ar"]) for d in listed[:2]] == [
        ("watercolor", "Premium watercolor", "مائي فاخر"),
        ("3d", "Cinematic 3D", "سينمائي ثلاثي الأبعاد"),
    ]
    assert all(d["status"] == "ready" and d["approved"] is False and d["created_at"] for d in listed)
    assert drawing["id"] not in {d["id"] for d in listed}
    kept = await adb.get(Character, second["id"])
    assert kept is not None and kept.params == {"attempt": 2, "fixes": ["hair"], "note": "شعره أجعد"}
    for d in listed:  # each one through the private image route
        image = await client.get(f"/api/create/characters/{d['id']}/image")
        assert image.status_code == 200 and image.headers["cache-control"] == "private, no-store"
    # the first drawing and 3 redraws are used; the one that failed on our side is not counted
    assert (await client.get("/api/create/children")).json()[0]["redraws_left"] == 0


async def test_approving_an_earlier_drawing_makes_it_the_childs_character(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _child(client)
    first = await _draw(client, child_id, style="3d")
    await _drawn(adb, storage, first["id"], minutes_ago=20)
    first_approval = (await _approve(client, first["id"]))["approved_at"]
    second = await _draw(client, child_id, style="3d", fixes=["face"])
    await _drawn(adb, storage, second["id"], minutes_ago=10)
    await _approve(client, second["id"])
    again = await _approve(client, first["id"])  # the parent compared and went back to the first

    assert again["approved"] is True and again["approved_at"] > first_approval
    # the one approved last is reused: by the next drawing request in that style and by the activity books
    assert (await _draw(client, child_id, style="3d"))["id"] == first["id"]
    needs = await client.get("/api/shop/workbooks/needs", params={"sku": WORKBOOK, "child_id": child_id})
    assert needs.json()["character"]["reuse_id"] == first["id"]
    chars = {c["id"]: c for c in (await client.get("/api/create/children")).json()[0]["characters"]}
    assert chars[first["id"]]["approved_at"] > chars[second["id"]]["approved_at"]
    logs = (await adb.execute(select(AuditLog).where(AuditLog.action == "character.approved"))).scalars()
    assert [(log.entity_id, log.data["again"]) for log in logs] == [
        (first["id"], False),
        (second["id"], False),
        (first["id"], True),
    ]


async def test_approving_a_drawing_in_another_style_draws_the_book_in_it(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    await register(client)
    child_id = await _child(client)
    three_d = await _draw(client, child_id, style="3d")
    await _drawn(adb, storage, three_d["id"], minutes_ago=20)
    painted = await _draw(client, child_id, style="watercolor", redraw=True)
    await _drawn(adb, storage, painted["id"], minutes_ago=10)
    await _approve(client, painted["id"])  # chosen on the 3D flow's character step, after comparing

    book = await client.post(
        "/api/create/books",
        json={"child_id": child_id, "character_id": painted["id"], "theme": "graduation", "line": "magic"},
    )
    assert book.status_code == 201 and book.json()["style"] == "watercolor"
    row = await adb.get(Book, book.json()["id"])
    assert row is not None and str(row.character_id) == painted["id"]
    unapproved = await client.post(
        "/api/create/books",
        json={"child_id": child_id, "character_id": three_d["id"], "theme": "graduation", "line": "magic"},
    )
    assert unapproved.status_code == 409 and unapproved.json()["error"]["code"] == "character_not_approved"
    cart = await client.post(
        "/api/shop/workbooks/cart",
        json={"sku": WORKBOOK, "child_id": child_id, "character_id": painted["id"]},
    )
    assert cart.status_code == 201, cart.text


async def test_only_the_guardian_sees_or_chooses_the_drawings(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client, email="first@example.com")
    child_id = await _child(client)
    drawn = await _draw(client, child_id, style="3d")
    await _drawn(adb, storage, drawn["id"], minutes_ago=5)
    await client.post("/api/auth/logout")
    assert (await client.get(f"/api/create/children/{child_id}/characters")).status_code == 401
    await register(client, email="second@example.com")
    assert (await client.get(f"/api/create/children/{child_id}/characters")).status_code == 404
    assert (await client.get(f"/api/create/characters/{drawn['id']}/image")).status_code == 404
    assert (await client.post(f"/api/create/characters/{drawn['id']}/approve")).status_code == 404


async def test_the_parents_note(client: AsyncClient, adb: AsyncSession, storage: ObjectStorage) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _child(client)
    first = await _draw(client, child_id, style="3d")
    await _drawn(adb, storage, first["id"], minutes_ago=10)
    await _approve(client, first["id"])

    too_long = await client.post(
        f"/api/create/children/{child_id}/characters", json={"style": "3d", "note": "ع" * 201}
    )
    assert too_long.status_code == 422 and too_long.json()["error"]["details"]["fields"] == ["note"]
    # counted once tidied: 40 words with double spaces are 238 characters typed, 199 kept
    roomy = "  ".join(["عيون"] * 40)
    redraw = await _draw(client, child_id, style="3d", note=roomy)  # a note alone asks for a new drawing
    assert redraw["id"] != first["id"] and redraw["status"] == "generating"
    row = await adb.get(Character, redraw["id"])
    assert row is not None and row.params == {"attempt": 2, "fixes": [], "note": " ".join(["عيون"] * 40)}
    blank = await _draw(client, child_id, style="3d", note=" \n ")  # nothing written: the approved one
    assert blank["id"] == first["id"]


async def test_deleting_the_child_removes_every_kept_drawing(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _child(client)
    keys = []
    for i, style in enumerate(("3d", "watercolor", "cartoon")):
        c = await _draw(client, child_id, style=style, redraw=True, note="شعره أقصر")
        keys.append(await _drawn(adb, storage, c["id"], minutes_ago=30 - i))
    await _approve(client, (await client.get(f"/api/create/children/{child_id}/characters")).json()[1]["id"])

    assert (await client.delete(f"/api/create/children/{child_id}")).status_code == 204
    assert not any(storage.exists(k) for k in keys)
    adb.expire_all()
    assert (await adb.execute(select(Character))).scalars().all() == []
