"""Portrait first (owner's decision, 2026-10-10): the child's portrait in the style is stored next to the sheet,
shown to the guardian only (private, never cached), listed with every drawing, and removed with «حذف كل بيانات
الطفل»."""

from pathlib import Path

from api_helpers import register
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed_store import seed_store
from qamra_core.db.models import Character, CharacterStatus
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


async def _child(client: AsyncClient) -> str:
    r = await client.post("/api/create/children", json={"name": "علي", "gender": "m", "age": 5})
    assert r.status_code == 201, r.text
    child_id: str = r.json()["id"]
    consent = {"accept": True, "version": CONSENT_VERSION}
    assert (await client.post(f"/api/create/children/{child_id}/consent", json=consent)).status_code == 200
    photo = [("photos", ("kid.png", FACE.read_bytes(), "image/png"))]
    assert (await client.post(f"/api/create/children/{child_id}/photos", files=photo)).status_code == 200
    return child_id


async def _drawn(adb: AsyncSession, storage: ObjectStorage, character_id: str, *, portrait: bool) -> Character:
    """What the worker does: the portrait, then the sheet, both under the child's prefix."""
    character = await adb.get(Character, character_id)
    assert character is not None
    base = f"children/{character.child_id}/characters/{character_id}"
    character.sheet_image_key = f"{base}.png"
    storage.put(character.sheet_image_key, b"sheet", "image/png")
    if portrait:
        character.portrait_image_key = f"{base}-portrait.png"
        storage.put(character.portrait_image_key, b"portrait", "image/png")
    character.status = CharacterStatus.ready
    await adb.commit()
    return character


async def test_the_guardian_sees_the_portrait_first_privately(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client, email="ali.dad@example.com")
    child_id = await _child(client)
    r = await client.post(f"/api/create/children/{child_id}/characters", json={"style": "3d"})
    assert r.status_code == 202, r.text
    new_id = r.json()["id"]
    assert r.json()["has_portrait"] is False  # nothing drawn yet
    assert (await client.get(f"/api/create/characters/{new_id}/portrait")).status_code == 409
    character = await _drawn(adb, storage, new_id, portrait=True)

    status = (await client.get(f"/api/create/characters/{new_id}")).json()
    assert status["has_portrait"] is True and status["status"] == "ready"
    image = await client.get(f"/api/create/characters/{new_id}/portrait")
    assert image.status_code == 200 and image.content == b"portrait"
    assert image.headers["cache-control"] == "private, no-store" and image.headers["content-type"] == "image/png"
    [listed] = (await client.get(f"/api/create/children/{child_id}/characters")).json()
    assert listed["id"] == new_id and listed["has_portrait"] is True  # the strip's thumbnail

    older = await client.post(
        f"/api/create/children/{child_id}/characters", json={"style": "watercolor", "redraw": True}
    )
    await _drawn(adb, storage, older.json()["id"], portrait=False)  # a drawing from before: no portrait
    assert (await client.get(f"/api/create/characters/{older.json()['id']}/portrait")).status_code == 409

    await client.post("/api/auth/logout")
    await register(client, email="someone.else@example.com")  # another parent never sees it
    assert (await client.get(f"/api/create/characters/{new_id}/portrait")).status_code in (403, 404)
    assert storage.exists(str(character.portrait_image_key))


async def test_delete_all_removes_the_portrait(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client, email="ali.mom@example.com")
    child_id = await _child(client)
    r = await client.post(f"/api/create/children/{child_id}/characters", json={"style": "semi-realistic"})
    character = await _drawn(adb, storage, r.json()["id"], portrait=True)
    portrait, sheet = str(character.portrait_image_key), str(character.sheet_image_key)
    assert (await client.delete(f"/api/create/children/{child_id}")).status_code == 204
    assert not storage.exists(portrait) and not storage.exists(sheet)
