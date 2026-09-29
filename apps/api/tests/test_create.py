from pathlib import Path

from api_helpers import register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.create import CONSENT_VERSION, MAX_CHARACTERS
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_core.db.classic import ClassicTemplate, TemplateStatus
from qamra_core.db.models import AuditLog, Book, Character, CharacterStatus, Child, ChildPhoto, OrderItem
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.store import OrderEvent
from qamra_core.storage import ObjectNotFound, ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
CHILD = {"name": "ليان", "gender": "f", "age": 6, "hijab": True, "interests": ["الرسم"]}
CHECKOUT = {
    "name": "أم ليان",
    "phone": "+970 59 123 4567",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "حي الجنان، قرب المسجد",
    "accept_terms": True,
}


async def _child(client: AsyncClient) -> dict:  # type: ignore[type-arg]
    r = await client.post("/api/create/children", json=CHILD)
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


async def _photo(client: AsyncClient, child_id: str) -> int:
    r = await client.post(
        f"/api/create/children/{child_id}/photos",
        files=[("photos", ("kid.png", FACE.read_bytes(), "image/png"))],
    )
    return r.status_code


async def _consent(client: AsyncClient, child_id: str) -> None:
    r = await client.post(
        f"/api/create/children/{child_id}/consent", json={"accept": True, "version": CONSENT_VERSION}
    )
    assert r.status_code == 200, r.text


async def _drawn(adb: AsyncSession, storage: ObjectStorage, character_id: str, child_id: str) -> None:
    """What the worker does when the character sheet is drawn."""
    character = await adb.get(Character, character_id)
    assert character is not None
    character.sheet_image_key = f"children/{child_id}/characters/{character_id}.png"
    character.status = CharacterStatus.ready
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()


async def test_the_create_flow_needs_a_signed_in_parent(client: AsyncClient) -> None:
    assert (await client.post("/api/create/children", json=CHILD)).status_code == 401


async def test_from_child_to_cart(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    await register(client)
    child = await _child(client)
    assert child["consent"] is False and child["redraws_left"] == MAX_CHARACTERS

    assert await _photo(client, child["id"]) == 409  # no photo before the guardian's consent
    stale = await client.post(
        f"/api/create/children/{child['id']}/consent", json={"accept": True, "version": "old"}
    )
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "consent_outdated"
    await _consent(client, child["id"])
    assert await _photo(client, child["id"]) == 200
    assert await _photo(client, child["id"]) == 200  # "change the photo": the first one is deleted
    kept = (await adb.execute(select(ChildPhoto).where(ChildPhoto.storage_key.is_not(None)))).scalars().all()
    assert len(kept) == 1

    queue = Queue("generation", connection=app.state.rq_redis)
    r = await client.post(f"/api/create/children/{child['id']}/characters", json={"style": "watercolor"})
    assert r.status_code == 202 and queue.jobs[-1].func_name == "qamra_worker.jobs.create.generate_character"
    character_id = r.json()["id"]
    early = await client.post(f"/api/create/characters/{character_id}/approve")
    assert early.status_code == 409  # still drawing

    await _drawn(adb, storage, character_id, child["id"])
    redraw = await client.post(
        f"/api/create/children/{child['id']}/characters",
        json={"style": "watercolor", "fixes": ["age", "skin"]},
    )
    again = await adb.get(Character, redraw.json()["id"])
    assert again is not None and again.params == {"attempt": 2, "fixes": ["age", "skin"]}  # for the prompt
    image = await client.get(f"/api/create/characters/{character_id}/image")
    assert image.status_code == 200 and image.headers["cache-control"] == "private, no-store"
    approved = (await client.post(f"/api/create/characters/{character_id}/approve")).json()
    assert approved["approved"] is True
    adb.expire_all()
    stored = select(ChildPhoto).where(ChildPhoto.storage_key.is_not(None))
    photos = (await adb.execute(stored)).scalars().all()
    assert photos and all(p.delete_after is not None for p in photos)  # originals now have a deletion time

    magic = await client.post(
        "/api/create/books",
        json={"child_id": child["id"], "character_id": character_id, "theme": "graduation", "line": "magic"},
    )
    assert magic.status_code == 201 and magic.json()["preview"] is True
    assert (
        queue.jobs[-1].func_name == "qamra_worker.jobs.books.generate_book"
        and queue.jobs[-1].args[1] == "preview"
    )
    classic = await client.post(
        "/api/create/books",
        json={
            "child_id": child["id"],
            "character_id": character_id,
            "theme": "graduation",
            "line": "classic",
        },
    )
    # no live Classic template for this story and look yet: a clear answer, never a dead draft
    assert classic.status_code == 409 and classic.json()["error"]["code"] == "classic_unavailable"

    wrong = await client.post(f"/api/create/books/{magic.json()['id']}/cart", json={"sku": "classic-soft-21"})
    assert wrong.status_code == 404  # a Magic book is sold as Magic
    cart = await client.post(
        f"/api/create/books/{magic.json()['id']}/cart",
        json={"sku": "magic-hard-21", "addons": [{"slug": "gift-box"}]},
    )
    assert cart.status_code == 201, cart.text
    item = cart.json()["items"][0]
    assert item["child_name"] == "ليان" and item["theme"] == "graduation" and item["style"] == "watercolor"


async def test_one_parent_never_reaches_another_parents_child(client: AsyncClient) -> None:
    await register(client, email="first@example.com")
    child = await _child(client)
    await client.post("/api/auth/logout")
    await register(client, email="second@example.com")
    assert (
        await client.post(
            f"/api/create/children/{child['id']}/consent", json={"accept": True, "version": CONSENT_VERSION}
        )
    ).status_code == 404
    assert (await client.get("/api/create/children")).json() == []
    assert (await client.delete(f"/api/create/children/{child['id']}")).status_code == 404


async def test_deleting_a_child_removes_their_data_and_keeps_the_order_without_it(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    await register(client)
    child = await _child(client)
    await _consent(client, child["id"])
    assert await _photo(client, child["id"]) == 200
    character_id = (
        await client.post(f"/api/create/children/{child['id']}/characters", json={"style": "watercolor"})
    ).json()["id"]
    await _drawn(adb, storage, character_id, child["id"])
    await client.post(f"/api/create/characters/{character_id}/approve")
    graduation = (await adb.execute(select(ThemeRow).where(ThemeRow.slug == "graduation"))).scalar_one()
    adb.add(  # a live Classic template for her look (Addendum 4 §1A)
        ClassicTemplate(
            theme_id=graduation.id,
            theme_version=graduation.version,
            art_style="watercolor",
            variant="girl_hijab",
            status=TemplateStatus.live,
            generation={},
        )
    )
    await adb.commit()
    book = await client.post(
        "/api/create/books",
        json={
            "child_id": child["id"],
            "character_id": character_id,
            "theme": "graduation",
            "line": "classic",
        },
    )
    await client.post(f"/api/create/books/{book.json()['id']}/cart", json={"sku": "classic-soft-21"})
    assert (await client.post("/api/store/checkout", json=CHECKOUT)).status_code == 201
    await client.post(f"/api/create/books/{book.json()['id']}/cart", json={"sku": "classic-digital"})

    assert (await client.delete(f"/api/create/children/{child['id']}")).status_code == 204
    adb.expire_all()
    assert await adb.get(Child, child["id"]) is None
    assert (await adb.execute(select(Book))).scalars().all() == []
    assert (await adb.execute(select(ChildPhoto))).scalars().all() == []
    try:
        storage.get(f"children/{child['id']}/characters/{character_id}.png")
        raise AssertionError("the character sheet is still stored")
    except ObjectNotFound:
        pass
    item = (await adb.execute(select(OrderItem))).scalar_one()
    assert item.child_id is None and "child_name" not in item.personalization
    note = (await adb.execute(select(OrderEvent).where(OrderEvent.kind == "note"))).scalar_one()
    assert note.order_id == item.order_id  # the team stops making that book
    assert (await client.get("/api/store/cart")).json()["items"] == []
    log = (await adb.execute(select(AuditLog).where(AuditLog.action == "child.deleted"))).scalar_one()
    assert log.entity_id == child["id"] and "ليان" not in str(log.data)
