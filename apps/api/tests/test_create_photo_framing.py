"""The parent's framing of the child's photo (owner, 2026-10-10): drag, zoom and turn it so the face sits in
the oval, on upload, after the upload and after the character is drawn. The original is kept once, with the
framing as numbers; the check runs on the cut-out; only the guardian sees the original, never cached, and
the privacy rules (24-hour deletion, "delete all my child's data") hold."""

import io
import json
import uuid
from pathlib import Path

import pytest
from api_helpers import register
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.photo_crop import FRAME_ASPECT
from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_api.settings import ApiSettings
from qamra_core.db.models import AuditLog, Character, CharacterStatus, ChildPhoto, PhotoStatus
from qamra_core.storage import ObjectNotFound, ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
CHILD = {"name": "ليان", "gender": "f", "age": 6, "hijab": True, "interests": ["الرسم"]}
FAR_AT = (1348, 100)  # the fixture's face on a 2048 × 1536 photo: a child far from the camera


def _far() -> bytes:
    canvas = Image.new("RGB", (2048, 1536), (150, 160, 170))
    canvas.paste(Image.open(FACE).convert("RGB"), FAR_AT)
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _around_face(width: int = 540, x: int = FAR_AT[0], y: int = FAR_AT[1]) -> dict[str, float]:
    """The parent's framing of the far photo, as the web sends it."""
    return {"x": x / 2048, "y": y / 1536, "w": width / 2048, "h": width / FRAME_ASPECT / 1536, "rotate": 0}


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
        e2e_fixtures=True,  # the browser test's `/api/e2e/photos/{id}/expire` is tested here too
    )


async def _ready_child(client: AsyncClient, email: str = "salma.mom@example.com") -> str:
    await register(client, email=email)
    r = await client.post("/api/create/children", json=CHILD)
    assert r.status_code == 201, r.text
    child_id: str = r.json()["id"]
    r = await client.post(
        f"/api/create/children/{child_id}/consent", json={"accept": True, "version": CONSENT_VERSION}
    )
    assert r.status_code == 200, r.text
    return child_id


async def _upload(client: AsyncClient, child_id: str, data: bytes, crop: object = None, n: int = 1):  # type: ignore[no-untyped-def]
    form = {} if crop is None else {"crop": crop if isinstance(crop, str) else json.dumps(crop)}
    return await client.post(
        f"/api/create/children/{child_id}/photos",
        files=[("photos", (f"kid{i}.jpg", data, "image/jpeg")) for i in range(n)],
        data=form,
    )


async def _kept(adb: AsyncSession) -> list[ChildPhoto]:
    adb.expire_all()
    return list((await adb.execute(select(ChildPhoto).where(ChildPhoto.storage_key.is_not(None)))).scalars())


async def test_an_upload_keeps_the_original_once_with_its_framing(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    child_id = await _ready_child(client)
    r = await _upload(client, child_id, _far(), _around_face())
    assert r.status_code == 200, r.text
    photo = r.json()["photo"]
    assert r.json()["photos"] == 1 and photo["crop"]["w"] == round(540 / 2048, 6)  # a far face, zoomed in
    [row] = await _kept(adb)
    assert str(row.id) == photo["id"] and row.crop == photo["crop"] and row.crop_saved_at is None
    assert row.check_metrics["face_ratio"] > 0.12  # the check ran on the cut-out
    with Image.open(io.BytesIO(storage.get(str(row.storage_key)))) as stored:
        assert stored.size == (2048, 1536)  # the original, not a cropped copy


async def test_an_upload_without_framing_is_framed_around_the_face(
    client: AsyncClient, adb: AsyncSession
) -> None:
    child_id = await _ready_child(client)
    r = await _upload(client, child_id, _far())  # too far whole; fine once framed around the face
    assert r.status_code == 200, r.text
    crop = r.json()["photo"]["crop"]
    assert crop is not None and crop["x"] * 2048 <= FAR_AT[0] + 178 <= (crop["x"] + crop["w"]) * 2048
    old = FACE.read_bytes()
    assert (await _upload(client, child_id, old)).status_code == 200  # "change the photo"
    rows = (await adb.execute(select(ChildPhoto).order_by(ChildPhoto.created_at))).scalars().all()
    replaced = [p for p in rows if p.status == PhotoStatus.deleted]
    assert replaced and all(p.crop is None and p.storage_key is None for p in replaced)


async def test_the_check_runs_on_the_framed_part(client: AsyncClient, adb: AsyncSession) -> None:
    child_id = await _ready_child(client)
    empty = await _upload(client, child_id, _far(), _around_face(x=0, y=700))
    assert empty.status_code == 422
    assert empty.json()["error"]["details"]["reason"] == "no_face"  # the face is outside the frame
    tiny = await _upload(client, child_id, _far(), _around_face(width=300))
    details = tiny.json()["error"]["details"]
    assert tiny.status_code == 422 and details["reason"] == "crop_small"
    assert details["ar"].startswith("كبّرتم الصورة") and details["en"].startswith("You've zoomed in")
    assert await _kept(adb) == []  # nothing kept from a photo that failed


async def test_a_framing_that_isnt_the_frame_is_refused(client: AsyncClient, adb: AsyncSession) -> None:
    child_id = await _ready_child(client)
    strip = {"x": 0, "y": 0, "w": 0.9, "h": 0.1, "rotate": 0}
    for crop in (
        "not json",
        strip,  # not the frame's shape
        {**_around_face(), "x": 0.9},  # leaves the photo
        {**_around_face(), "rotate": 45},
        {**_around_face(), "zoom": 2},  # unknown field
    ):
        r = await _upload(client, child_id, _far(), crop)
        assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["crop"], (crop, r.text)
    two = await _upload(client, child_id, _far(), _around_face(), n=2)  # one framing frames one photo
    assert two.status_code == 422 and two.json()["error"]["details"]["fields"] == ["crop"]
    assert await _kept(adb) == []


async def test_the_framing_is_changed_after_the_upload_and_checked_again(
    client: AsyncClient, adb: AsyncSession
) -> None:
    child_id = await _ready_child(client)
    photo_id = (await _upload(client, child_id, _far())).json()["photo"]["id"]
    moved = _around_face(width=600, x=1300, y=60)
    r = await client.put(f"/api/create/photos/{photo_id}/crop", json=moved)
    assert r.status_code == 200, r.text
    assert r.json()["photo"]["crop"] == {k: round(v, 6) for k, v in moved.items()}
    [row] = await _kept(adb)
    assert row.crop_saved_at is not None
    bad = await client.put(f"/api/create/photos/{photo_id}/crop", json=_around_face(x=0, y=700))
    assert bad.status_code == 422 and bad.json()["error"]["details"]["reason"] == "no_face"
    [row] = await _kept(adb)
    assert row.crop == r.json()["photo"]["crop"]  # the framing saved before stays
    strip = await client.put(f"/api/create/photos/{photo_id}/crop", json={"x": 0, "y": 0, "w": 0.9, "h": 0.1})
    assert strip.status_code == 422 and strip.json()["error"]["details"]["fields"] == ["crop"]


async def test_the_original_is_streamed_to_the_guardian_only_never_cached_and_audited(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    child_id = await _ready_child(client)
    photo_id = (await _upload(client, child_id, FACE.read_bytes())).json()["photo"]["id"]
    r = await client.get(f"/api/create/photos/{photo_id}/image")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.headers["cache-control"] == "private, no-store"
    [row] = await _kept(adb)
    assert r.content == storage.get(str(row.storage_key))
    audit = (await adb.execute(select(AuditLog).where(AuditLog.action == "photo.viewed"))).scalars().one()
    assert audit.entity_id == photo_id and audit.data in ({}, None)  # who and which photo, never the image

    await client.post("/api/auth/logout")
    await register(client, email="other.parent@example.com")
    assert (await client.get(f"/api/create/photos/{photo_id}/image")).status_code == 404
    moved = await client.put(f"/api/create/photos/{photo_id}/crop", json=_around_face())
    assert moved.status_code == 404
    assert (await client.get(f"/api/create/photos/{uuid.uuid4()}/image")).status_code == 404
    await client.post("/api/auth/logout")
    assert (await client.get(f"/api/create/photos/{photo_id}/image")).status_code == 401


async def test_a_deleted_photo_says_so_kindly(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    child_id = await _ready_child(client)
    photo_id = (await _upload(client, child_id, FACE.read_bytes())).json()["photo"]["id"]
    [row] = await _kept(adb)
    key = str(row.storage_key)
    await client.post("/api/auth/logout")
    await register(client, email="someone.else@example.com")
    assert (await client.post(f"/api/e2e/photos/{photo_id}/expire")).status_code == 404  # only one's own
    await client.post("/api/auth/logout")
    signed = await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "moonlight-2026"}
    )
    assert signed.status_code == 200, signed.text
    # the browser test's fixture does what the 24-hour job does
    assert (await client.post(f"/api/e2e/photos/{photo_id}/expire")).status_code == 204
    assert not storage.exists(key) and await _kept(adb) == []
    gone = await adb.get(ChildPhoto, uuid.UUID(photo_id))
    assert gone is not None and gone.status == PhotoStatus.deleted and gone.crop is None and gone.deleted_at
    for r in (
        await client.get(f"/api/create/photos/{photo_id}/image"),
        await client.put(f"/api/create/photos/{photo_id}/crop", json=_around_face()),
    ):
        assert r.status_code == 410 and r.json()["error"]["code"] == "photo_gone"
        assert "حفاظًا على الخصوصية" in r.json()["error"]["message"]["ar"]
    child = next(c for c in (await client.get("/api/create/children")).json() if c["id"] == child_id)
    assert child["photo"] is None and child["photos"] == 0


async def test_deleting_the_child_removes_the_photo_and_its_framing(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    child_id = await _ready_child(client)
    photo_id = (await _upload(client, child_id, _far(), _around_face())).json()["photo"]["id"]
    [row] = await _kept(adb)
    key = str(row.storage_key)
    assert (await client.delete(f"/api/create/children/{child_id}")).status_code == 204
    adb.expire_all()
    assert (await adb.execute(select(ChildPhoto))).scalars().all() == []
    try:
        storage.get(key)
        raise AssertionError("the original photo is still stored")
    except ObjectNotFound:
        pass
    assert (await client.get(f"/api/create/photos/{photo_id}/image")).status_code == 404


async def test_a_new_framing_lets_the_next_redraw_draw_again_and_keeps_the_deletion_time(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    child_id = await _ready_child(client)
    photo_id = (await _upload(client, child_id, _far())).json()["photo"]["id"]
    first = (
        await client.post(f"/api/create/children/{child_id}/characters", json={"style": "watercolor"})
    ).json()["id"]
    character = await adb.get(Character, uuid.UUID(first))
    assert character is not None
    character.sheet_image_key = f"children/{child_id}/characters/{first}.png"
    character.status = CharacterStatus.ready
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()
    assert (await client.post(f"/api/create/characters/{first}/approve")).status_code == 200
    [row] = await _kept(adb)
    due = row.delete_after
    assert due is not None  # the 24-hour rule started with the approval

    same = await client.post(f"/api/create/children/{child_id}/characters", json={"style": "watercolor"})
    assert same.json()["id"] == first  # the approved character is reused, never redrawn for nothing
    framed = await client.put(f"/api/create/photos/{photo_id}/crop", json=_around_face())
    assert framed.status_code == 200, framed.text
    again = await client.post(f"/api/create/children/{child_id}/characters", json={"style": "watercolor"})
    assert again.status_code == 202 and again.json()["id"] != first  # the new framing is drawn
    assert again.json()["status"] == "generating"
    [row] = await _kept(adb)
    assert row.delete_after == due  # framing again never postpones the deletion
