"""«احتفظوا بالصورة» (owner, 2026-10-16): the guardian's optional, separate choice to keep the child's
photo for later books. Off by default, its own versioned consent, reused by later flows, and taken back or
deleted at any time."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from api_helpers import register
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed_store import seed_store
from qamra_core.db.models import AuditLog, Character, CharacterStatus, Child, ChildPhoto, Consent, PhotoStatus
from qamra_core.photo_keep import KEEP_CONSENT_VERSION, KEEP_SCOPE, add_months
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
CHILD = {"name": "ليان", "gender": "f", "age": 6}


async def _ready_child(client: AsyncClient, *, photo: bool = True) -> str:
    r = await client.post("/api/create/children", json=CHILD)
    assert r.status_code == 201, r.text
    child_id: str = r.json()["id"]
    r = await client.post(
        f"/api/create/children/{child_id}/consent", json={"accept": True, "version": CONSENT_VERSION}
    )
    assert r.status_code == 200, r.text
    if photo:
        r = await client.post(
            f"/api/create/children/{child_id}/photos",
            files=[("photos", ("kid.png", FACE.read_bytes(), "image/png"))],
        )
        assert r.status_code == 200, r.text
    return child_id


async def _keep(client: AsyncClient, child_id: str, on: bool, version: str | None = KEEP_CONSENT_VERSION):  # type: ignore[no-untyped-def]
    return await client.put(
        f"/api/create/children/{child_id}/photo-keep", json={"keep": on, "version": version}
    )


async def _approved(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage, child_id: str, style: str
) -> str:
    r = await client.post(f"/api/create/children/{child_id}/characters", json={"style": style})
    assert r.status_code == 202, r.text
    character_id: str = r.json()["id"]
    character = await adb.get(Character, character_id)
    assert character is not None
    character.sheet_image_key = f"children/{child_id}/characters/{character_id}.png"
    character.status = CharacterStatus.ready
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()
    assert (await client.post(f"/api/create/characters/{character_id}/approve")).status_code == 200
    return character_id


async def _photos(adb: AsyncSession, child_id: str) -> list[ChildPhoto]:
    adb.expire_all()
    rows = await adb.execute(select(ChildPhoto).where(ChildPhoto.child_id == child_id))
    return list(rows.scalars())


async def test_off_by_default_and_needs_its_own_consent(client: AsyncClient, adb: AsyncSession) -> None:
    await register(client)
    child_id = await _ready_child(client, photo=False)
    child = (await client.get("/api/create/children")).json()[0]
    assert child["photo_kept"] is False and child["consent"] is True
    state = (await client.get(f"/api/create/children/{child_id}/photo-keep")).json()
    assert state == {
        "keep": False,
        "since": None,
        "version": KEEP_CONSENT_VERSION,
        "months": 12,
        "photo": None,
    }

    stale = await _keep(client, child_id, True, "photo-keep-old")
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "consent_outdated"
    missing = await _keep(client, child_id, True, None)
    assert missing.status_code == 409 and missing.json()["error"]["code"] == "consent_outdated"
    # the photo consent comes first
    fresh = (await client.post("/api/create/children", json=CHILD)).json()["id"]
    first = await _keep(client, fresh, True)
    assert first.status_code == 409 and first.json()["error"]["code"] == "consent_required"
    kept = await adb.execute(select(Consent).where(Consent.scope == KEEP_SCOPE))
    assert kept.scalars().all() == []


async def test_opt_in_is_recorded_and_the_photo_outlives_the_approval(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _ready_child(client)
    before = datetime.now(UTC)
    r = await _keep(client, child_id, True)
    assert r.status_code == 200, r.text
    state = r.json()
    assert state["keep"] is True and state["since"] is not None and state["months"] == 12
    assert await _keep(client, child_id, True) is not None  # idempotent: no second record
    consent = (
        await adb.execute(select(Consent).where(Consent.child_id == child_id, Consent.scope == KEEP_SCOPE))
    ).scalar_one()
    assert consent.consent_text_version == KEEP_CONSENT_VERSION and consent.withdrawn_at is None
    assert consent.ip and consent.accepted_at >= before - timedelta(seconds=5)
    audit = (
        await adb.execute(
            select(AuditLog).where(
                AuditLog.action == "consent.given", AuditLog.data["scope"].astext == KEEP_SCOPE
            )
        )
    ).scalar_one()
    assert audit.data == {"version": KEEP_CONSENT_VERSION, "scope": KEEP_SCOPE, "months": 12}
    (photo,) = await _photos(adb, child_id)
    assert photo.last_used_at is not None and photo.last_used_at >= before - timedelta(seconds=5)
    deletes_at = datetime.fromisoformat(state["photo"]["deletes_at"])
    assert deletes_at == add_months(photo.last_used_at, 12)

    await _approved(client, adb, storage, child_id, "watercolor")
    (photo,) = await _photos(adb, child_id)
    assert photo.delete_after is not None  # the 24-hour date is still set; the cleanup skips it while kept
    assert (await client.get("/api/create/children")).json()[0]["photo_kept"] is True


async def test_a_later_flow_reuses_the_kept_photo(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _ready_child(client)
    assert (await _keep(client, child_id, True)).status_code == 200
    await _approved(client, adb, storage, child_id, "watercolor")
    (photo,) = await _photos(adb, child_id)
    photo.delete_after = datetime.now(UTC) - timedelta(days=40)  # long past the 24 hours
    await adb.commit()

    # a new book in another style, weeks later: the photo step shows the kept photo, no new upload
    child = (await client.get("/api/create/children")).json()[0]
    assert child["photo_kept"] is True and child["photo"]["id"] == str(photo.id)
    image = await client.get(f"/api/create/photos/{photo.id}/image")
    assert image.status_code == 200 and image.headers["cache-control"] == "private, no-store"
    drawn = await client.post(f"/api/create/children/{child_id}/characters", json={"style": "cartoon"})
    assert drawn.status_code == 202, drawn.text
    # and it can be framed again
    framed = await client.put(
        f"/api/create/photos/{photo.id}/crop", json={"x": 0, "y": 0, "w": 1, "h": 1, "rotate": 0}
    )
    assert framed.status_code in (200, 422)  # the fixture's face decides; never 410 (gone)


async def test_turning_it_off_schedules_the_deletion_within_24_hours(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _ready_child(client)
    assert (await _keep(client, child_id, True)).status_code == 200
    await _approved(client, adb, storage, child_id, "watercolor")
    (photo,) = await _photos(adb, child_id)
    photo.delete_after = datetime.now(UTC) - timedelta(days=3)
    await adb.commit()

    now = datetime.now(UTC)
    r = await _keep(client, child_id, False, None)
    assert r.status_code == 200 and r.json()["keep"] is False
    (photo,) = await _photos(adb, child_id)
    assert photo.delete_after is not None
    assert now + timedelta(hours=23) < photo.delete_after <= now + timedelta(hours=24, minutes=1)
    assert r.json()["photo"]["deletes_at"] is not None
    consent = (await adb.execute(select(Consent).where(Consent.scope == KEEP_SCOPE))).scalar_one()
    assert consent.withdrawn_at is not None
    assert (await adb.execute(select(AuditLog).where(AuditLog.action == "consent.withdrawn"))).scalar_one()
    assert (await client.get("/api/create/children")).json()[0]["photo_kept"] is False

    # on again: a new record (the old one stays withdrawn)
    assert (await _keep(client, child_id, True)).json()["keep"] is True
    rows = (await adb.execute(select(Consent).where(Consent.scope == KEEP_SCOPE))).scalars().all()
    assert len(rows) == 2 and sum(c.withdrawn_at is None for c in rows) == 1


async def test_off_before_any_approval_keeps_the_usual_rules(client: AsyncClient, adb: AsyncSession) -> None:
    await register(client)
    child_id = await _ready_child(client)
    await _keep(client, child_id, True)
    await _keep(client, child_id, False, None)
    (photo,) = await _photos(adb, child_id)
    assert photo.delete_after is None  # 24 hours after the approval, or with the abandoned drafts


async def test_delete_the_photo_now(client: AsyncClient, adb: AsyncSession, storage: ObjectStorage) -> None:
    await register(client)
    child_id = await _ready_child(client)
    await _keep(client, child_id, True)
    (photo,) = await _photos(adb, child_id)
    key = str(photo.storage_key)
    assert storage.exists(key)

    assert (await client.delete(f"/api/create/children/{child_id}/photos")).status_code == 204
    assert not storage.exists(key)
    (photo,) = await _photos(adb, child_id)
    assert photo.storage_key is None and photo.status == PhotoStatus.deleted and photo.deleted_at is not None
    state = (await client.get(f"/api/create/children/{child_id}/photo-keep")).json()
    assert state["keep"] is False and state["photo"] is None
    child = (await client.get("/api/create/children")).json()[0]
    assert child["photo"] is None and child["photo_kept"] is False and child["consent"] is True
    assert (await client.get(f"/api/create/photos/{photo.id}/image")).status_code == 410
    audit = (
        await adb.execute(select(AuditLog).where(AuditLog.action == "photo.deleted_by_guardian"))
    ).scalar_one()
    assert audit.data == {"photos": 1}


async def test_delete_all_my_childs_data_removes_the_kept_photo(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await register(client)
    child_id = await _ready_child(client)
    await _keep(client, child_id, True)
    (photo,) = await _photos(adb, child_id)
    key = str(photo.storage_key)

    assert (await client.delete(f"/api/create/children/{child_id}")).status_code == 204
    adb.expire_all()
    assert not storage.exists(key)
    assert await adb.get(Child, child_id) is None
    assert (await adb.execute(select(ChildPhoto))).scalars().all() == []
    assert (await adb.execute(select(Consent))).scalars().all() == []


async def test_only_the_guardian(client: AsyncClient) -> None:
    await register(client, email="first@example.com")
    child_id = await _ready_child(client, photo=False)
    await client.post("/api/auth/logout")
    await register(client, email="second@example.com")
    assert (await client.get(f"/api/create/children/{child_id}/photo-keep")).status_code == 404
    assert (await _keep(client, child_id, True)).status_code == 404
    assert (await client.delete(f"/api/create/children/{child_id}/photos")).status_code == 404
    await client.post("/api/auth/logout")
    assert (await _keep(client, child_id, True)).status_code == 401
