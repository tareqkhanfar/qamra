"""The free cover (Addendum 9): the feature switch, the create flow's child, consent and photo, one cover per
account and story, the per-IP limit, the 24-hour photo rule and private images."""

import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from api_helpers import register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers import free_cover as free_cover_router
from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed import upsert_themes
from qamra_core.db.classic import (
    ClassicTemplate,
    ClassicTemplatePage,
    FreeCover,
    FreeCoverStatus,
    TemplateStatus,
)
from qamra_core.db.models import AppSetting, ChildPhoto
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


async def _switch(adb: AsyncSession, on: bool = True) -> None:
    adb.add(AppSetting(key="free_cover", value=on))
    await adb.commit()


async def _template(adb: AsyncSession, slug: str, variant: str = "girl_hijab") -> ClassicTemplate:
    theme = (await adb.execute(select(ThemeRow).where(ThemeRow.slug == slug))).scalar_one()
    t = ClassicTemplate(
        theme_id=theme.id, theme_version=theme.version, art_style="watercolor", variant=variant,
        status=TemplateStatus.live, generation={"theme_def": theme.definition},
    )  # fmt: skip
    adb.add(t)
    await adb.flush()
    adb.add(
        ClassicTemplatePage(
            template_id=t.id, beat=0, image_key="k", hero_box={"x": 0.3, "y": 0.3, "w": 0.3, "h": 0.5}
        )
    )
    await adb.commit()
    return t


async def _child(client: AsyncClient, name: str = "ليان") -> str:
    child = (
        await client.post("/api/create/children", json={"name": name, "gender": "f", "age": 5, "hijab": True})
    ).json()
    await client.post(
        f"/api/create/children/{child['id']}/consent", json={"accept": True, "version": CONSENT_VERSION}
    )
    r = await client.post(
        f"/api/create/children/{child['id']}/photos",
        files=[("photos", ("kid.png", FACE.read_bytes(), "image/png"))],
    )
    assert r.status_code == 200, r.text
    return str(child["id"])


async def test_the_switch_is_off_by_default(client: AsyncClient, adb: AsyncSession) -> None:
    await upsert_themes(adb)
    await register(client)
    child = await _child(client)
    r = await client.post("/api/free-covers", json={"child_id": child, "theme": "graduation"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "free_cover_off"


async def test_a_free_cover_from_request_to_image(
    client: AsyncClient,
    adb: AsyncSession,
    app: FastAPI,
    storage: ObjectStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await upsert_themes(adb)
    await _switch(adb)
    await register(client)
    child = await _child(client)
    body = {"child_id": child, "theme": "graduation"}
    r = await client.post("/api/free-covers", json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "classic_unavailable"  # no template yet

    await _template(adb, "graduation")
    r = await client.post("/api/free-covers", json=body)
    assert r.status_code == 202, r.text
    cover = r.json()
    assert cover["status"] == "drawing" and cover["child_name"] == "ليان" and cover["ready"] is False
    job = Queue("generation", connection=app.state.rq_redis).jobs[-1]
    assert job.func_name == "qamra_worker.jobs.free_cover.draw_free_cover" and job.args == (cover["id"],)
    photos = (
        (await adb.execute(select(ChildPhoto).where(ChildPhoto.storage_key.is_not(None)))).scalars().all()
    )
    assert photos and all(p.delete_after == p.created_at + timedelta(hours=24) for p in photos)  # 24 h rule

    again = await client.post("/api/free-covers", json=body)
    assert again.status_code == 202 and again.json()["id"] == cover["id"]  # the same cover, no new drawing
    other = await _child(client, "سلمى")
    used = await client.post("/api/free-covers", json={"child_id": other, "theme": "graduation"})
    assert used.status_code == 409 and used.json()["error"]["code"] == "free_cover_used"  # one per story

    image = await client.get(f"/api/free-covers/{cover['id']}/cover.jpg")
    assert image.status_code == 409  # still drawing
    row = await adb.get(FreeCover, uuid.UUID(cover["id"]))
    assert row is not None
    row.status, row.image_key = FreeCoverStatus.ready, f"children/{child}/free-covers/{row.id}/cover.jpg"
    await adb.commit()
    storage.put(row.image_key, b"\xff\xd8\xffjpeg", "image/jpeg")
    got = await client.get(f"/api/free-covers/{cover['id']}/cover.jpg", params={"download": True})
    assert got.status_code == 200 and got.headers["cache-control"] == "private, no-store"
    assert "attachment" in got.headers["content-disposition"]
    assert (await client.get(f"/api/free-covers/{cover['id']}")).json()["ready"] is True

    await client.post("/api/auth/logout")
    await register(client, email="someone.else@example.com")
    assert (await client.get(f"/api/free-covers/{cover['id']}")).status_code == 404  # never another parent's

    monkeypatch.setattr(free_cover_router, "PER_IP_PER_DAY", 0)
    await _template(adb, "first-day")
    stranger = await _child(client, "ريم")
    limited = await client.post("/api/free-covers", json={"child_id": stranger, "theme": "first-day"})
    assert limited.status_code == 429
