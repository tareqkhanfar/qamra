"""The illustrated-family add-on (Addendum 7 §7), behind its setting: consent for each person before their
photo, one clear face, private storage, a drawing job with the approved providers, approval that schedules
the photo's deletion, at most four people and four drawings each, and «forget this person» at once."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from api_helpers import register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.family_members import CONSENT_VERSION, JOB
from qamra_api.seed_store import seed_store
from qamra_core.db.models import AppSetting, Child, FamilyMember, FamilyMemberStatus, Gender
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


async def test_a_family_member_drawn_from_a_consented_photo(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    parent = await register(client, email="mom@example.com")
    child = Child(
        guardian_user_id=uuid.UUID(parent["id"]), first_name="ليان", gender=Gender.f, birth_year=2021
    )
    adb.add(child)
    await adb.commit()
    base = f"/api/create/children/{child.id}/family"
    grandma = {"relation": "grandmother", "name": "أم خليل", "scarf": True}
    off = await client.post(base, json=grandma)
    assert off.status_code == 409 and off.json()["error"]["code"] == "family_characters_off"  # off by default
    adb.add(AppSetting(key="family_characters_enabled", value=True))
    await adb.commit()

    member = (await client.post(base, json=grandma)).json()
    assert member["adult"] and member["scarf"] and member["status"] == "draft" and not member["consented"]
    url = f"/api/create/family/{member['id']}"
    photo = {"photo": ("gm.png", FACE.read_bytes(), "image/png")}
    assert (await client.post(f"{url}/photo", files=photo)).json()["error"]["code"] == "consent_required"
    stale = await client.post(f"{url}/consent", json={"accept": True, "version": "old"})
    assert stale.status_code == 409
    assert (await client.post(f"{url}/consent", json={"accept": True, "version": CONSENT_VERSION})).json()[
        "consented"
    ]
    r = await client.post(f"{url}/photo", files=photo)
    assert r.status_code == 200 and r.json()["has_photo"], r.text
    row = await adb.get(FamilyMember, uuid.UUID(member["id"]))
    assert (
        row is not None
        and row.consent_ip
        and row.photo_key == f"children/{child.id}/family/{row.id}/photo.jpg"
    )
    assert (
        storage.exists(row.photo_key) and row.photo_delete_after is None
    )  # kept until the drawing is approved

    drawn = (await client.post(f"{url}/draw", json={"style": "watercolor"})).json()
    assert drawn["status"] == "generating" and drawn["drawings_left"] == 3
    jobs = [(j.func_name, tuple(j.args)) for j in Queue("generation", connection=app.state.rq_redis).jobs]
    assert (JOB, (member["id"],)) in jobs
    assert (await client.post(f"{url}/approve")).status_code == 409  # nothing drawn yet

    # the worker drew it (tests/worker: jobs.family_members); the parent approves
    await adb.refresh(row)
    row.sheet_key, row.status = f"children/{child.id}/family/{row.id}/sheet-1.png", FamilyMemberStatus.ready
    storage.put(row.sheet_key, b"\x89PNG sheet", "image/png")
    await adb.commit()
    assert (await client.get(f"{url}/image")).content == b"\x89PNG sheet"
    approved = (await client.post(f"{url}/approve")).json()
    assert approved["approved"] and approved["status"] == "approved"
    await adb.refresh(row)
    assert row.photo_delete_after is not None
    assert row.photo_delete_after - datetime.now(UTC) <= timedelta(hours=24)  # CLAUDE.md §3.1

    others = [{"relation": r} for r in ("father", "brother", "sister")]
    for body in others:
        assert (await client.post(base, json=body)).status_code == 201
    assert (await client.post(base, json={"relation": "baby"})).status_code == 422  # four at most
    listed = (await client.get(base)).json()
    assert len(listed) == 4 and listed[2]["adult"] is False  # a brother is a child unless the parent says so

    assert (await client.delete(url)).status_code == 204  # «forget this person»: files and record at once
    assert not storage.exists(row.sheet_key or "") and not storage.exists(row.photo_key or "")
    assert (await client.get(f"{url}/image")).status_code == 404
    await register(client, email="other@example.com")  # another parent never reaches this family
    assert (await client.get(base)).status_code == 404
