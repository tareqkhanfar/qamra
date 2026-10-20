"""«تغيير الصورة» (owner, 2026-10-19: «مش معقول خلص بس صورة واحدة وبس»): a child gets a new photo at any time,
also after the first one was approved and deleted. Only the newest original is kept (an earlier one still
stored is deleted at once), the next drawing is a new one from it (never the approved one reused), it counts
as a free drawing as usual, and every drawing says which photo it came from; the earlier drawings stay
choosable."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from api_helpers import register
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_api.settings import ApiSettings
from qamra_core.db.models import AuditLog, Character, CharacterStatus, ChildPhoto, Consent, PhotoStatus
from qamra_core.photo_keep import KEEP_SCOPE
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
CHILD = {"name": "ليان", "gender": "f", "age": 5}


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(
        _env_file=None,
        env="test",
        cookie_secure=False,
        log_json=False,  # type: ignore[call-arg]
        web_base_url="http://testserver",
        login_max_attempts=5,
        login_ip_max_attempts=20,
        settings_cache_seconds=0,
        e2e_fixtures=True,  # `/api/e2e/photos/{id}/expire`: what the 24-hour job does
    )


async def _upload(client: AsyncClient, child_id: str) -> dict[str, Any]:
    photo = [("photos", ("kid.png", FACE.read_bytes(), "image/png"))]
    r = await client.post(f"/api/create/children/{child_id}/photos", files=photo)
    assert r.status_code == 200, r.text
    out: dict[str, Any] = r.json()
    return out


async def _child(client: AsyncClient) -> str:
    await register(client)
    r = await client.post("/api/create/children", json=CHILD)
    assert r.status_code == 201, r.text
    child_id: str = r.json()["id"]
    consent = {"accept": True, "version": CONSENT_VERSION}
    assert (await client.post(f"/api/create/children/{child_id}/consent", json=consent)).status_code == 200
    return child_id


async def _drawn(adb: AsyncSession, storage: ObjectStorage, character_id: str) -> None:
    """What the worker does once the sheet is drawn."""
    character = await adb.get(Character, uuid.UUID(character_id))
    assert character is not None
    character.sheet_image_key = f"children/{character.child_id}/characters/{character_id}.png"
    character.status = CharacterStatus.ready
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()


async def _newer(adb: AsyncSession, photo_id: str) -> None:
    """The upload came after the approval (one test transaction gives every row the same `now()`)."""
    await adb.execute(
        update(ChildPhoto)
        .where(ChildPhoto.id == uuid.UUID(photo_id))
        .values(created_at=datetime.now(UTC) + timedelta(minutes=1))
    )
    await adb.commit()


async def _draw(client: AsyncClient, child_id: str) -> dict[str, Any]:
    r = await client.post(f"/api/create/children/{child_id}/characters", json={"style": "watercolor"})
    assert r.status_code == 202, r.text
    out: dict[str, Any] = r.json()
    return out


async def test_a_new_photo_after_the_first_was_deleted_draws_a_new_character(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    child_id = await _child(client)
    first_photo = (await _upload(client, child_id))["photo"]["id"]
    first = await _draw(client, child_id)
    assert first["photo_id"] == first_photo  # marked with the photo it is drawn from
    await _drawn(adb, storage, first["id"])
    assert (await client.post(f"/api/create/characters/{first['id']}/approve")).status_code == 200
    # 24 hours after the approval the original is deleted (the browser test's fixture does what the job does)
    assert (await client.post(f"/api/e2e/photos/{first_photo}/expire")).status_code == 204
    child = next(c for c in (await client.get("/api/create/children")).json() if c["id"] == child_id)
    assert child["photos"] == 0 and child["photo"] is None

    # «تغيير الصورة»: simply a new upload
    changed = await _upload(client, child_id)
    second_photo = changed["photo"]["id"]
    assert changed["photos"] == 1 and second_photo != first_photo
    await _newer(adb, second_photo)
    second = await _draw(client, child_id)
    assert second["id"] != first["id"] and second["status"] == "generating"  # never the approved one reused
    assert second["photo_id"] == second_photo
    await _drawn(adb, storage, second["id"])

    # the earlier drawing stays choosable, and each says which photo it came from
    drawings = (await client.get(f"/api/create/children/{child_id}/characters")).json()
    assert {d["id"]: d["photo_id"] for d in drawings} == {
        first["id"]: first_photo,
        second["id"]: second_photo,
    }
    again = await client.post(f"/api/create/characters/{first['id']}/approve")
    assert again.status_code == 200 and again.json()["photo_id"] == first_photo
    # the new photo is deleted on the usual clock: an approval was given, so it is due 24 hours from now
    row = await adb.get(ChildPhoto, uuid.UUID(second_photo))
    assert row is not None
    await adb.refresh(row)
    assert row.delete_after is not None and row.delete_after <= datetime.now(UTC) + timedelta(hours=25)


async def test_a_new_photo_deletes_the_earlier_original_at_once(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    child_id = await _child(client)
    first_photo = (await _upload(client, child_id))["photo"]["id"]
    row = await adb.get(ChildPhoto, uuid.UUID(first_photo))
    assert row is not None and row.storage_key
    key = row.storage_key

    second_photo = (await _upload(client, child_id))["photo"]["id"]
    assert not storage.exists(key)  # only the newest original is ever kept
    adb.expire_all()
    rows = (await adb.execute(select(ChildPhoto).where(ChildPhoto.storage_key.is_not(None)))).scalars().all()
    assert [str(p.id) for p in rows] == [second_photo]
    old = await adb.get(ChildPhoto, uuid.UUID(first_photo))
    assert old is not None and old.status == PhotoStatus.deleted and old.deleted_at and old.crop is None
    audit = (await adb.execute(select(AuditLog).where(AuditLog.action == "photo.replaced"))).scalars().one()
    assert audit.entity_id == first_photo and audit.data in ({}, None)  # which photo, never the image
    gone = await client.get(f"/api/create/photos/{first_photo}/image")
    assert gone.status_code == 410 and gone.json()["error"]["code"] == "photo_gone"


async def test_only_the_photo_consent_lets_a_photo_in(client: AsyncClient, adb: AsyncSession) -> None:
    """The «احتفظوا بالصورة» choice is not the consent to the photo itself."""
    await register(client)
    child_id = (await client.post("/api/create/children", json=CHILD)).json()["id"]
    user_id = (await client.get("/api/auth/me")).json()["id"]
    adb.add(
        Consent(
            child_id=uuid.UUID(child_id),
            guardian_user_id=uuid.UUID(user_id),
            consent_text_version="keep-2026-10",
            scope=KEEP_SCOPE,
            accepted_at=datetime.now(UTC),
        )
    )
    await adb.commit()
    photo = [("photos", ("kid.png", FACE.read_bytes(), "image/png"))]
    r = await client.post(f"/api/create/children/{child_id}/photos", files=photo)
    assert r.status_code == 409 and r.json()["error"]["code"] == "consent_required"
