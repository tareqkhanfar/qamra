"""Kindergarten portal permissions: a school admin sees only their own organization; parents and pending
schools get friendly refusals; the planner, the class photo and the B2B price lists behave."""

import uuid

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from portal_helpers import FACE, approved_character, approved_school, browser, csv_rows
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_core.db.models import AuditLog
from qamra_core.db.portal import ClassBook, ClassBookPage
from qamra_core.storage import ObjectStorage


async def _class_with_kids(client: AsyncClient, *kids: str) -> tuple[str, list[dict]]:  # type: ignore[type-arg]
    room = (await client.post("/api/portal/classes", json={"name": "صف النجوم"})).json()
    base = f"/api/portal/classes/{room['id']}"
    rows = (
        await client.post(f"{base}/import/preview", files={"file": ("c.csv", csv_rows(*kids), "text/csv")})
    ).json()
    r = await client.post(f"{base}/import", json={"rows": rows["rows"]})
    assert r.status_code == 200, r.text
    return base, r.json()["detail"]["children"]


async def test_a_school_sees_only_its_own_organization(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    await approved_school(client, adb)
    base, kids = await _class_with_kids(client, "يوسف,ولد,2021,أبو يوسف,0599123456,")
    await client.put(f"{base}/book", json={"theme": "graduation"})
    await approved_character(adb, storage, kids[0]["id"], "watercolor")
    child = kids[0]["id"]

    async with browser(app) as other:
        await approved_school(other, adb, email="head@sun-kg.example", school="روضة الشمس")
        assert (await other.get("/api/portal/me")).json()["classes"] == []
        for path in (
            base,
            f"{base}/book",
            f"{base}/book/plan",
            f"{base}/book/review",
            f"{base}/order/quote",
            f"{base}/template.csv",
            f"{base}/children/{child}/character",
        ):
            r = await other.get(path)
            assert r.status_code == 404 and r.json()["error"]["code"] == "not_found", path
        assert (await other.delete(f"{base}/children/{child}")).status_code == 404
        assert (await other.post(f"{base}/invites/sent", json={"children": [child]})).status_code == 404
        assert (await other.post(f"{base}/book/generate")).status_code == 404
        assert (await other.put(f"{base}/book", json={"theme": "graduation"})).status_code == 404
        csv = {"file": ("c.csv", csv_rows("ريم,بنت,2021,,0599000111,"), "text/csv")}
        assert (await other.post(f"{base}/import/preview", files=csv)).status_code == 404
        assert (await other.get(f"/api/create/children/{child}/photos")).status_code in (404, 405)

    async with browser(app) as parent:  # a parent account is not a school
        await register(parent, email="parent@example.com")
        r = await parent.get("/api/portal/me")
        assert r.status_code == 403 and r.json()["error"]["code"] == "not_school"
        assert (await parent.get("/api/admin/portal/organizations")).status_code == 403
    # our own school still sees its class and the approved drawing (never a photo)
    assert (await client.get(f"{base}/children/{child}/character")).status_code == 200
    assert (await client.get("/api/portal/me")).json()["classes"][0]["children"] == 1


async def test_the_planner_the_class_photo_and_redraw_limits(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    await approved_school(client, adb)
    kids = [f"{n},ولد,2021,,05991234{i:02d}," for i, n in enumerate(["أنس", "باسل", "تيم", "جود", "خالد"])]
    base, rows = await _class_with_kids(client, *kids)
    assert (await client.get(f"{base}/book/plan")).json()["error"]["code"] == "theme_required"
    await client.put(f"{base}/book", json={"theme": "graduation", "min_appearances": 3})
    for row in rows:
        await approved_character(adb, storage, row["id"], "watercolor")
    plan = (await client.get(f"{base}/book/plan")).json()
    assert {m["count"] for m in plan["members"]} == {3} and not plan["manual"]
    first = next(p for p in plan["pages"] if p["children"])
    moved = [{"index": first["index"], "children": []}]  # the teacher empties a page
    r = await client.put(f"{base}/book/plan", json={"pages": moved})
    assert r.json()["manual"] and min(m["count"] for m in r.json()["members"]) < 3
    short = await client.post(f"{base}/book/generate")
    assert short.status_code == 409 and short.json()["error"]["code"] == "coverage_low"
    too_many = [{"index": first["index"], "children": [r["id"] for r in rows]}]
    assert (await client.put(f"{base}/book/plan", json={"pages": too_many})).json()["error"][
        "code"
    ] == "invalid_plan"
    stranger = [{"index": first["index"], "children": [str(uuid.uuid4())]}]
    assert (await client.put(f"{base}/book/plan", json={"pages": stranger})).status_code == 422
    r = await client.post(f"{base}/book/plan/auto")
    assert {m["count"] for m in r.json()["members"]} == {3} and not r.json()["manual"]

    photo = {"photo": ("class.jpg", FACE.read_bytes(), "image/png")}
    r = await client.post(f"{base}/book/photo", files=photo, data={"permission": "false"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "photo_permission_required"
    r = await client.post(f"{base}/book/photo", files=photo, data={"permission": "true"})
    assert r.status_code == 200 and r.json()["class_photo"] and r.json()["class_photo_permission_at"]
    cb = (await adb.execute(select(ClassBook))).scalar_one()
    assert cb.class_photo_key and cb.class_photo_key.startswith(f"orgs/{cb.organization_id}/")
    audit = (
        await adb.execute(select(AuditLog).where(AuditLog.action == "class_photo.uploaded"))
    ).scalar_one()
    assert audit.data == {"parents_permission_confirmed": True}
    assert (await client.delete(f"{base}/book/photo")).json()["class_photo"] is False
    assert not storage.exists(cb.class_photo_key or "x")


async def test_b2b_price_lists_in_the_catalog_admin_set_the_schools_price(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)
    school = await approved_school(client, adb)
    async with browser(app) as ops:
        await make_admin(ops, adb)
        lists = (await ops.get("/api/admin/catalog/price-lists")).json()
        default = next(pl for pl in lists["lists"] if pl["organization_id"] is None)
        assert any(i["sku"] == "class-magic-hard-21" for i in default["items"])
        assert all(v["audience"] == "b2b" for v in lists["variants"])
        r = await ops.post(
            "/api/admin/catalog/price-lists",
            json={
                "name": "روضة القمر 2027",
                "organization_id": school["org"]["id"],
                "copy_from": default["id"],
            },
        )
        assert r.status_code == 201 and r.json()["organization"] == "روضة القمر"
        own = r.json()["id"]
        bad = [{"min_qty": 1, "unit_price": "40"}, {"min_qty": 1, "unit_price": "38"}]
        r = await ops.put(
            f"/api/admin/catalog/price-lists/{own}/items/class-magic-hard-21", json={"tiers": bad}
        )
        assert r.json()["error"]["code"] == "invalid_tiers"
        tiers = [{"min_qty": 10, "unit_price": "38"}, {"min_qty": 1, "unit_price": "42"}]
        r = await ops.put(
            f"/api/admin/catalog/price-lists/{own}/items/class-magic-hard-21", json={"tiers": tiers}
        )
        item = next(i for i in r.json()["items"] if i["sku"] == "class-magic-hard-21")
        assert [t["min_qty"] for t in item["tiers"]] == [1, 10] and len(item["margin_pct"]) == 2
        assert (await ops.get("/api/admin/organizations")).status_code == 404  # only /api/admin/portal/…
        orgs = (await ops.get("/api/admin/portal/organizations")).json()
        assert orgs[0]["price_list"] == "روضة القمر 2027"
    base, rows = await _class_with_kids(client, "يوسف,ولد,2021,,0599123456,", "جنى,بنت,2021,,0599123457,")
    await client.put(f"{base}/book", json={"theme": "graduation"})
    for row in rows:
        await approved_character(adb, storage, row["id"], "watercolor")
    quote = (await client.get(f"{base}/order/quote")).json()
    assert quote["price_list"] == "روضة القمر 2027" and [t["unit_price"] for t in quote["tiers"]] == [
        "42.00",
        "38.00",
    ]


async def test_deleting_a_childs_data_removes_them_from_the_class_book(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    """CLAUDE.md §3.1: the shared pictures with the child's drawn likeness and the combined file go too."""
    await upsert_themes(adb)
    await seed_store(adb)
    await approved_school(client, adb)
    base, kids = await _class_with_kids(client, "يوسف,ولد,2021,,0599123456,", "جنى,بنت,2021,,0599123457,")
    await client.put(f"{base}/book", json={"theme": "graduation"})
    token = next(k for k in kids if k["name"] == "يوسف")["invite"]["path"].rsplit("/", 1)[1]
    async with browser(app) as dad:
        await register(dad, email="yusuf.dad@example.com")
        child_id = (await dad.post(f"/api/invite/{token}/claim")).json()["child"]["id"]
        other = next(k for k in kids if k["name"] == "جنى")["id"]
        cb = (await adb.execute(select(ClassBook))).scalar_one()
        prefix = f"orgs/{cb.organization_id}/classes/{cb.classroom_id}/book"
        page = ClassBookPage(
            class_book_id=cb.id,
            index=1,
            scene_key="arrive",
            child_ids=[child_id, other],
            image_key=f"{prefix}/raw/01.png",
            print_image_key=f"{prefix}/print/01.jpg",
        )
        adb.add(page)
        cb.plan = {
            "children": [child_id, other],
            "pages": [{"index": 1, "key": "arrive", "slots": 3, "children": [child_id, other]}],
        }
        cb.bundle = {"combined_key": f"{prefix}/files/combined.pdf", "copies": [{"child_id": child_id}]}
        for key in (
            page.image_key,
            page.print_image_key,
            f"{prefix}/thumb/01.jpg",
            cb.bundle["combined_key"],
        ):
            storage.put(key, b"x", "application/octet-stream")
        await adb.commit()
        assert (await dad.delete(f"/api/create/children/{child_id}")).status_code == 204
    await adb.refresh(page)
    await adb.refresh(cb)
    assert page.image_key is None and page.child_ids == [other] and page.status.value == "pending"
    assert not storage.exists(f"{prefix}/raw/01.png") and not storage.exists(f"{prefix}/files/combined.pdf")
    assert cb.plan["children"] == [other] and cb.bundle["copies"] == [] and "child_removed" in cb.flags
