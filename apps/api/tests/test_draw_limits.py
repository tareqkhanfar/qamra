"""Free character drawings come back with time (owner, 2026-10-16; qamra_api.draw_limits): 3 in every rolling
2 hours per child, at most 12 in 24 hours per child and per account, all three admin settings. A drawing that
failed on our side never counts; staff accounts are never limited, in any flow."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient, Response
from portal_helpers import approved_school, browser, csv_rows
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.draw_limits import DRAWN, Limits, allowance
from qamra_api.routers.companions import MAX_ROUNDS
from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.routers.family_members import CONSENT_VERSION as FAMILY_CONSENT
from qamra_api.routers.family_members import MAX_DRAWINGS
from qamra_api.routers.invite import INVITE_CONSENT_VERSION
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_core.db.models import (
    AppSetting,
    AuditLog,
    Character,
    CharacterStatus,
    Companion,
    CompanionStatus,
    CompanionType,
    FamilyMember,
)
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
DEFAULT = Limits(per_window=3, window_hours=2, daily_cap=12)


def ago(minutes: float) -> datetime:
    return NOW - timedelta(minutes=minutes)


# ---- the rule itself


def test_three_in_two_hours_and_each_comes_back_two_hours_after_it_was_used() -> None:
    assert allowance(NOW, DEFAULT, [], []).left == 3 and allowance(NOW, DEFAULT, [], []).reset_at is None
    used = [ago(100), ago(40), ago(5)]
    out = allowance(NOW, DEFAULT, used, used)
    assert out.left == 0 and out.reset_at == ago(100) + timedelta(hours=2)  # in 20 minutes
    later = allowance(out.reset_at, DEFAULT, used, used)
    assert later.left == 1 and later.reset_at == ago(40) + timedelta(hours=2)  # the next one back
    assert allowance(NOW + timedelta(hours=2), DEFAULT, used, used).left == 3


def test_the_daily_caps_hold_even_with_free_windows() -> None:
    # 12 drawings for this child in the last day, none in the last 2 hours: the child's cap holds
    day = [ago(130 + 60 * i) for i in range(12)]
    out = allowance(NOW, DEFAULT, day, day)
    assert out.left == 0 and out.reset_at == min(day) + timedelta(hours=24)
    # the account drew 12 for other children: this child (none drawn) waits for the account's cap too
    out = allowance(NOW, DEFAULT, [], day)
    assert out.left == 0 and out.reset_at == min(day) + timedelta(hours=24)
    # 11 in the day: one left, though the window would allow 3
    assert allowance(NOW, DEFAULT, day[:11], day[:11]).left == 1


def test_a_lower_cap_than_the_window_and_custom_settings() -> None:
    tight = Limits(per_window=5, window_hours=1, daily_cap=2)
    used = [ago(300), ago(10)]
    out = allowance(NOW, tight, used, used)
    assert out.left == 0 and out.reset_at == ago(300) + timedelta(hours=24)
    assert out.per_window == 5 and out.window_hours == 1


# ---- through the API


async def _child(client: AsyncClient, name: str = "سلمى") -> str:
    r = await client.post("/api/create/children", json={"name": name, "gender": "f", "age": 5})
    assert r.status_code == 201, r.text
    child_id: str = r.json()["id"]
    consent = {"accept": True, "version": CONSENT_VERSION}
    assert (await client.post(f"/api/create/children/{child_id}/consent", json=consent)).status_code == 200
    photo = [("photos", ("kid.png", FACE.read_bytes(), "image/png"))]
    assert (await client.post(f"/api/create/children/{child_id}/photos", files=photo)).status_code == 200
    return child_id


async def _draw(client: AsyncClient, child_id: str, **body: Any) -> Response:
    return await client.post(
        f"/api/create/children/{child_id}/characters", json={"style": "watercolor", "redraw": True, **body}
    )


async def _shown(client: AsyncClient, child_id: str) -> dict[str, Any]:
    children = (await client.get("/api/create/children")).json()
    out: dict[str, Any] = next(c for c in children if c["id"] == child_id)
    return out


async def _age(adb: AsyncSession, character_id: str, minutes: float) -> None:
    """Move a drawing (and its audit row) back in time: one test transaction gives every row one now()."""
    when = datetime.now(UTC) - timedelta(minutes=minutes)
    await adb.execute(
        update(Character).where(Character.id == uuid.UUID(character_id)).values(created_at=when)
    )
    await adb.execute(
        update(AuditLog)
        .where(AuditLog.action == DRAWN, AuditLog.entity_id == character_id)
        .values(created_at=when)
    )
    await adb.commit()


async def _setting(adb: AsyncSession, key: str, value: Any) -> None:
    adb.add(AppSetting(key=key, value=value))
    await adb.commit()


async def test_the_free_drawings_come_back_after_two_hours(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _child(client)
    shown = await _shown(client, child_id)
    assert (shown["redraws_left"], shown["redraws_total"], shown["redraws_window_hours"]) == (3, 3, 2)
    assert shown["redraws_reset_at"] is None and shown["redraws_unlimited"] is False

    ids = []
    for minutes in (100, 50, 0):
        r = await _draw(client, child_id)
        assert r.status_code == 202, r.text
        ids.append(r.json()["id"])
        await _age(adb, ids[-1], minutes)
    blocked = await _draw(client, child_id)
    assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "free_draws_used"
    reset_at = datetime.fromisoformat(blocked.json()["error"]["details"]["reset_at"])
    oldest = await adb.get(Character, uuid.UUID(ids[0]))
    assert oldest is not None and reset_at == oldest.created_at + timedelta(hours=2)
    shown = await _shown(client, child_id)
    assert shown["redraws_left"] == 0 and datetime.fromisoformat(shown["redraws_reset_at"]) == reset_at

    # the oldest one's two hours are over: one is back
    await _age(adb, ids[0], 121)
    shown = await _shown(client, child_id)
    assert shown["redraws_left"] == 1 and shown["redraws_reset_at"] is not None
    assert (await _draw(client, child_id)).status_code == 202
    assert (await _draw(client, child_id)).status_code == 429


async def test_a_drawing_that_failed_on_our_side_is_not_counted(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await seed_store(adb)
    await register(client)
    child_id = await _child(client)
    ids = [(await _draw(client, child_id)).json()["id"] for _ in range(3)]
    assert (await _shown(client, child_id))["redraws_left"] == 0
    await adb.execute(
        update(Character).where(Character.id == uuid.UUID(ids[1])).values(status=CharacterStatus.failed)
    )
    await adb.commit()
    assert (await _shown(client, child_id))["redraws_left"] == 1
    assert (await _draw(client, child_id)).status_code == 202


async def test_twelve_a_day_per_child(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await _setting(adb, "free_draws_per_window", 20)  # only the daily cap left to stop it
    await register(client)
    child_id = await _child(client)
    first = None
    for i in range(12):
        r = await _draw(client, child_id)
        assert r.status_code == 202, (i, r.text)
        first = first or r.json()["id"]
    await _age(adb, first, 600)  # ten hours ago: still in the day
    blocked = await _draw(client, child_id)
    assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "free_draws_used"
    row = await adb.get(Character, uuid.UUID(first))
    assert row is not None
    assert datetime.fromisoformat(
        blocked.json()["error"]["details"]["reset_at"]
    ) == row.created_at + timedelta(hours=24)
    await _age(adb, first, 24 * 60 + 1)
    assert (await _draw(client, child_id)).status_code == 202


async def test_the_daily_cap_is_per_account_too_and_survives_deleting_a_child(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)
    await _setting(adb, "free_draws_per_window", 20)
    await _setting(adb, "free_draws_daily_cap", 4)
    await register(client)
    one, two = await _child(client), await _child(client, "يوسف")
    for child_id in (one, one, two, two):
        assert (await _draw(client, child_id)).status_code == 202
    assert (await _shown(client, two))["redraws_left"] == 0
    assert (await _draw(client, two)).status_code == 429
    # deleting a child gives nothing back: the account's drawings are counted from its own record
    assert (await client.delete(f"/api/create/children/{one}")).status_code == 204
    three = await _child(client, "ليان")
    assert (await _shown(client, three))["redraws_left"] == 0
    assert (await _draw(client, three)).status_code == 429

    async with browser(app) as other:  # another account is not touched
        await register(other, email="another.mom@example.com")
        assert (await _draw(other, await _child(other))).status_code == 202


async def test_the_kindergarten_invite_counts_the_same_way(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    await approved_school(client, adb)
    room = (await client.post("/api/portal/classes", json={"name": "صف الفراشات"})).json()
    base = f"/api/portal/classes/{room['id']}"
    rows = (
        await client.post(
            f"{base}/import/preview",
            files={"file": ("c.csv", csv_rows("يوسف,ولد,2021,خليل يوسف,0599123456,"), "text/csv")},
        )
    ).json()["rows"]
    child = (await client.post(f"{base}/import", json={"rows": rows})).json()["detail"]["children"][0]
    token = child["invite"]["path"].rsplit("/", 1)[1]
    async with browser(app) as mom:
        await register(mom, email="yusuf.mom@example.com")
        assert (await mom.post(f"/api/invite/{token}/claim")).status_code == 200
        consent = {"accept": True, "version": INVITE_CONSENT_VERSION}
        assert (await mom.post(f"/api/invite/{token}/consent", json=consent)).status_code == 200
        photo = [("photos", ("kid.png", FACE.read_bytes(), "image/png"))]
        assert (await mom.post(f"/api/create/children/{child['id']}/photos", files=photo)).status_code == 200
        for _ in range(3):
            assert (await mom.post(f"/api/invite/{token}/character", json={})).status_code == 202
        blocked = await mom.post(f"/api/invite/{token}/character", json={"fixes": ["hair"]})
        assert blocked.status_code == 429 and blocked.json()["error"]["details"]["reset_at"]
        shown = (await mom.get(f"/api/invite/{token}")).json()["child"]
        assert shown["redraws_left"] == 0 and shown["redraws_reset_at"]


async def test_staff_are_never_limited_in_any_flow(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    """The owner tests the parent flow with his own admin account and children he drew many times before."""
    await upsert_themes(adb)
    await seed_store(adb)
    await _setting(adb, "family_characters_enabled", True)
    await make_admin(client, adb)
    child_id = await _child(client)
    for _ in range(14):  # drawn before the window existed: more than the day's cap
        adb.add(Character(child_id=uuid.UUID(child_id), art_style="watercolor", status=CharacterStatus.ready))
    await adb.commit()
    shown = await _shown(client, child_id)
    assert (
        shown["redraws_unlimited"] is True
        and shown["redraws_left"] == 3
        and shown["redraws_reset_at"] is None
    )
    for _ in range(4):
        assert (await _draw(client, child_id, fixes=["hair"])).status_code == 202

    # the approved character, then four previews in a day (a parent gets three)
    character = (await _draw(client, child_id)).json()["id"]
    row = await adb.get(Character, uuid.UUID(character))
    assert row is not None
    row.status, row.sheet_image_key = CharacterStatus.ready, f"children/{child_id}/characters/{character}.png"
    storage.put(row.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()
    assert (await client.post(f"/api/create/characters/{character}/approve")).status_code == 200
    book = {"child_id": child_id, "character_id": character, "theme": "graduation", "line": "magic"}
    for _ in range(4):
        r = await client.post("/api/create/books", json=book)
        assert r.status_code == 201, r.text

    # a companion and a family member past their free drawings
    comp = Companion(
        child_id=uuid.UUID(child_id),
        name="نونو",
        type_hint=CompanionType.animal,
        status=CompanionStatus.ready,
        cleaned_key=f"children/{child_id}/companions/x/cleaned.png",
        regen_count=MAX_ROUNDS + 2,
    )
    adb.add(comp)
    await adb.commit()
    shown_comp = (await client.get(f"/api/create/companions/{comp.id}")).json()
    assert shown_comp["redraws_left"] == MAX_ROUNDS
    r = await client.post(f"/api/create/companions/{comp.id}/draw", json={"name": "نونو"})
    assert r.status_code == 202, r.text

    member = (
        await client.post(f"/api/create/children/{child_id}/family", json={"relation": "grandmother"})
    ).json()
    url = f"/api/create/family/{member['id']}"
    assert (
        await client.post(f"{url}/consent", json={"accept": True, "version": FAMILY_CONSENT})
    ).status_code == 200
    photo = {"photo": ("gm.png", FACE.read_bytes(), "image/png")}
    assert (await client.post(f"{url}/photo", files=photo)).status_code == 200
    stored = await adb.get(FamilyMember, uuid.UUID(member["id"]))
    assert stored is not None
    stored.regen_count = MAX_DRAWINGS + 1
    await adb.commit()
    drawn = await client.post(f"{url}/draw", json={"style": "watercolor"})
    assert drawn.status_code == 202 and drawn.json()["drawings_left"] == MAX_DRAWINGS


async def test_a_parent_still_gets_the_reused_character_when_none_are_left(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    """Reusing the approved character in a style is not a drawing: it works with no free drawing left."""
    await seed_store(adb)
    await register(client)
    child_id = await _child(client)
    first = (await _draw(client, child_id)).json()["id"]
    row = await adb.get(Character, uuid.UUID(first))
    assert row is not None
    row.status, row.sheet_image_key = CharacterStatus.ready, f"children/{child_id}/characters/{first}.png"
    storage.put(row.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()
    assert (await client.post(f"/api/create/characters/{first}/approve")).status_code == 200
    for _ in range(2):
        assert (await _draw(client, child_id, fixes=["face"])).status_code == 202
    assert (await _shown(client, child_id))["redraws_left"] == 0
    reused = await client.post(f"/api/create/children/{child_id}/characters", json={"style": "watercolor"})
    assert reused.status_code == 202 and reused.json()["id"] == first
