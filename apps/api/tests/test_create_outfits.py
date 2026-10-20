"""«ماذا يلبس؟» (owner, 2026-10-20): the parent picks the outfit a character is drawn in
(content/outfits.yaml). The API lists the outfits with their swatch colours (never the prompts), checks
the id against the child and the book's line, stores it on the character, and reuses an approved drawing
only in the outfit asked for."""

from pathlib import Path
from typing import Any

from api_helpers import register
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed_store import seed_store
from qamra_core.db.models import Character, CharacterStatus
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


async def _child(client: AsyncClient, gender: str = "f") -> str:
    r = await client.post("/api/create/children", json={"name": "تالا", "gender": gender, "age": 5})
    assert r.status_code == 201, r.text
    child_id: str = r.json()["id"]
    consent = {"accept": True, "version": CONSENT_VERSION}
    assert (await client.post(f"/api/create/children/{child_id}/consent", json=consent)).status_code == 200
    photo = [("photos", ("kid.png", FACE.read_bytes(), "image/png"))]
    assert (await client.post(f"/api/create/children/{child_id}/photos", files=photo)).status_code == 200
    return child_id


async def _draw(client: AsyncClient, child_id: str, **body: Any) -> tuple[int, dict[str, Any]]:
    r = await client.post(f"/api/create/children/{child_id}/characters", json=body)
    return r.status_code, r.json()


async def _ready(adb: AsyncSession, storage: ObjectStorage, character_id: str) -> None:
    character = await adb.get(Character, character_id)
    assert character is not None
    character.sheet_image_key = f"children/{character.child_id}/characters/{character_id}.png"
    character.status = CharacterStatus.ready
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()


async def test_the_outfits_are_listed_with_their_swatches_and_no_prompts(client: AsyncClient) -> None:
    assert (await client.get("/api/create/outfits")).status_code == 401  # a signed-in parent's flow
    await register(client)
    r = await client.get("/api/create/outfits")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["default"] == "classic" and body["version"] >= 1
    girls = [o for o in body["outfits"] if "f" in o["looks"]]
    boys = [o for o in body["outfits"] if "m" in o["looks"]]
    assert len(girls) == 6 and len(boys) == 6
    classic = body["outfits"][0]
    assert (classic["id"], classic["name_ar"]) == ("classic", "الأساسي")
    assert classic["looks"]["f"]["swatch"]["shape"] == "tee" and classic["hijab_color"].startswith("#")
    assert "prompt" not in r.text and "night-blue" not in r.text


async def test_the_outfit_is_checked_stored_and_shown(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client)
    girl = await _child(client)
    status, err = await _draw(client, girl, style="3d", outfit="green-hoodie")  # a boys' outfit
    assert status == 422 and err["error"]["code"] == "invalid_outfit"
    status, err = await _draw(client, girl, style="3d", outfit="no-such-outfit")
    assert status == 422 and err["error"]["code"] == "invalid_outfit"
    status, err = await _draw(client, girl, style="3d", outfit="school", line="family")  # not on that line
    assert status == 422 and err["error"]["code"] == "invalid_outfit"
    status, err = await _draw(client, girl, style="watercolor", outfit="rose-dress", line="classic")
    assert status == 422 and err["error"]["code"] in ("invalid_outfit", "invalid_style")

    status, drawn = await _draw(client, girl, style="3d", outfit="rose-dress", line="magic")
    assert status == 202, drawn
    assert drawn["outfit"] == "rose-dress"
    row = await adb.get(Character, drawn["id"])
    assert row is not None and row.params["outfit"] == "rose-dress"
    await _ready(adb, storage, drawn["id"])
    listed = (await client.get(f"/api/create/children/{girl}/characters")).json()
    assert [d["outfit"] for d in listed] == ["rose-dress"]

    status, plain = await _draw(client, girl, style="watercolor", redraw=True)  # no outfit: the default
    assert status == 202 and plain["outfit"] == "classic"
    row = await adb.get(Character, plain["id"])
    assert row is not None and "outfit" not in row.params


async def test_an_approved_drawing_is_reused_only_in_the_outfit_asked_for(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    await register(client)
    boy = await _child(client, "m")
    status, first = await _draw(client, boy, style="3d", outfit="striped-sweater")
    assert status == 202
    await _ready(adb, storage, first["id"])
    assert (await client.post(f"/api/create/characters/{first['id']}/approve")).status_code == 200

    status, same = await _draw(client, boy, style="3d", outfit="striped-sweater")
    assert status == 202 and same["id"] == first["id"]  # reused: no new drawing
    status, any_outfit = await _draw(client, boy, style="3d")
    assert status == 202 and any_outfit["id"] == first["id"]  # no outfit asked: the approved one
    status, other = await _draw(client, boy, style="3d", outfit="tatreez")
    assert status == 202 and other["id"] != first["id"] and other["outfit"] == "tatreez"  # a new drawing
    children = (await client.get("/api/create/children")).json()
    assert children[0]["redraws_left"] == children[0]["redraws_total"] - 2  # it used a free drawing
