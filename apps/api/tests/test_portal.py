"""The kindergarten portal end to end (CLAUDE.md §8 B2B, Phase 4): sign-up → our approval → a class → the
children from CSV → a parent's invite (consent, photo, character) → the class book's plan (every child ≥ 2
times) → the batch → the school's and our approvals → one order with one invoice."""

import uuid

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from portal_helpers import FACE, approved_character, browser, csv_rows, signup, worker_batch
from rq import Queue
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.invite import INVITE_CONSENT_VERSION
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Consent,
    Order,
    OrderItem,
)
from qamra_core.db.portal import ClassBook
from qamra_core.db.store import Invoice
from qamra_core.storage import ObjectStorage

KIDS = (
    "يوسف,ولد,2021,خليل يوسف,0599123456,",
    "جنى,بنت,5,منى عودة,0568220031,",
    "آدم,ولد,2020,,0597410882,",
    "سلمى,بنت,2021,سامر حمدان,,salma.dad@example.com",
    "تالا,بنت,2021,هالة منصور,0599 12,",  # a phone number too short: not imported
)


async def test_from_sign_up_to_one_order_and_one_invoice(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await upsert_themes(adb)
    await seed_store(adb)

    # sign-up: the account works, the organization waits for us
    r = await client.post("/api/portal/signup", json=signup())
    assert r.status_code == 201, r.text
    org_id = r.json()["org"]["id"]
    assert r.json()["org"]["status"] == "pending"
    blocked = await client.post("/api/portal/classes", json={"name": "صف الفراشات"})
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "org_pending"

    async with browser(app) as ops:  # our team approves it in the admin
        await make_admin(ops, adb)
        pending = (await ops.get("/api/admin/portal/organizations", params={"status": "pending"})).json()
        assert [o["id"] for o in pending] == [org_id] and pending[0]["contacts"][0]["email"].startswith(
            "sanaa"
        )
        r = await ops.post(f"/api/admin/portal/organizations/{org_id}/approve", json={})
        assert r.status_code == 200 and r.json()["status"] == "approved"
    audit = await adb.execute(select(AuditLog).where(AuditLog.action == "organization.approved"))
    assert audit.scalar_one().entity_id == org_id

    room = (
        await client.post(
            "/api/portal/classes",
            json={"name": "صف الفراشات", "teacher_name": "أ. رنا", "school_year": "2026-2027"},
        )
    ).json()
    base = f"/api/portal/classes/{room['id']}"

    # the children from the school's list: a preview with reasons, then the import
    assert (
        await client.post(f"{base}/import/preview", files={"file": ("k.xlsx", b"PK..", "application/zip")})
    ).json()["error"]["code"] == "import_format"
    r = await client.post(
        f"{base}/import/preview", files={"file": ("class.csv", csv_rows(*KIDS), "text/csv")}
    )
    assert r.status_code == 200, r.text
    preview = r.json()
    assert preview["errors"] == 1 and preview["warnings"] == 1  # Adam has no parent name
    bad = next(row for row in preview["rows"] if not row["ok"])
    assert bad["name"] == "تالا" and "رقم الجوال" in bad["errors"][0]["ar"]
    r = await client.post(f"{base}/import", json={"rows": preview["rows"]})
    assert r.status_code == 200 and r.json()["created"] == 4 and len(r.json()["skipped"]) == 1
    children = {c["name"]: c for c in r.json()["detail"]["children"]}
    assert set(children) == {"يوسف", "جنى", "آدم", "سلمى"}
    assert all(c["stage"] == "not_invited" and c["invite"]["state"] == "ready" for c in children.values())
    assert children["يوسف"]["phone"] == "0599 ••• 456"
    r = await client.post(f"{base}/invites/sent", json={"children": [c["id"] for c in children.values()]})
    assert {c["stage"] for c in r.json()["children"]} == {"invited"}

    # one story, one line for the class
    r = await client.put(
        f"{base}/book", json={"theme": "graduation", "line": "magic", "teacher_message": "أحبائي"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["theme"] == "graduation" and r.json()["min_appearances"] == 2 and r.json()["ready"] == 0

    # a parent opens their child's link, signs in, consents, uploads the photo, approves the drawing
    token = children["يوسف"]["invite"]["path"].rsplit("/", 1)[1]
    async with browser(app) as mom:
        opened = (await mom.get(f"/api/invite/{token}")).json()
        assert (
            opened["state"] == "open" and opened["child_name"] == "يوسف" and opened["school"] == "روضة القمر"
        )
        assert (await mom.post(f"/api/invite/{token}/claim")).status_code == 401  # sign in first
        await register(mom, email="yusuf.mom@example.com")
        r = await mom.post(f"/api/invite/{token}/claim")
        assert r.status_code == 200 and r.json()["state"] == "mine"
        child_id = r.json()["child"]["id"]
        photo = [("photos", ("kid.png", FACE.read_bytes(), "image/png"))]
        assert (await mom.post(f"/api/create/children/{child_id}/photos", files=photo)).status_code == 409
        stale = await mom.post(f"/api/invite/{token}/consent", json={"accept": True, "version": "old"})
        assert stale.json()["error"]["code"] == "consent_outdated"
        r = await mom.post(
            f"/api/invite/{token}/consent", json={"accept": True, "version": INVITE_CONSENT_VERSION}
        )
        assert r.json()["child"]["consent"] is True
        assert (await mom.post(f"/api/create/children/{child_id}/photos", files=photo)).status_code == 200
        r = await mom.post(f"/api/invite/{token}/character", json={})
        assert r.status_code == 202 and r.json()["style"] == "watercolor"
        character = await adb.get(Character, uuid.UUID(r.json()["id"]))
        assert character is not None
        character.sheet_image_key = f"children/{child_id}/characters/{character.id}.png"  # the worker drew it
        character.status = CharacterStatus.ready
        storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
        await adb.commit()
        assert (await mom.post(f"/api/create/characters/{character.id}/approve")).status_code == 200
    consent = (await adb.execute(select(Consent).where(Consent.child_id == uuid.UUID(child_id)))).scalar_one()
    assert consent.consent_text_version == INVITE_CONSENT_VERSION and consent.scope == "class_book"

    async with browser(app) as stranger:  # the link works for one account only
        await register(stranger, email="someone.else@example.com")
        taken = await stranger.post(f"/api/invite/{token}/claim")
        assert taken.status_code == 409 and taken.json()["error"]["code"] == "invite_claimed"

    for name in ("جنى", "آدم", "سلمى"):  # the other parents did the same
        await approved_character(adb, storage, children[name]["id"], "watercolor")

    # the teacher's board: states only, never a photo
    r = await client.get(base)
    assert {c["name"]: c["stage"] for c in r.json()["children"]}["يوسف"] == "approved"
    assert "photos/" not in r.text and "storage_key" not in r.text
    yusuf = next(c for c in r.json()["children"] if c["name"] == "يوسف")
    assert yusuf["steps"] == {
        "invited": True,
        "consent": True,
        "photo": True,
        "drawing": False,
        "approved": True,
    }

    # the plan: every child at least twice, never twice on a page, at most 3 per picture
    plan = (await client.get(f"{base}/book/plan")).json()
    assert {m["name"]: m["count"] for m in plan["members"]} == {"يوسف": 2, "جنى": 2, "آدم": 2, "سلمى": 2}
    assert all(len(p["children"]) <= min(p["slots"], 3) for p in plan["pages"])
    assert all(len({k["id"] for k in p["children"]}) == len(p["children"]) for p in plan["pages"])

    # the batch
    r = await client.post(f"{base}/book/generate")
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "generating"
    jobs = Queue("generation", connection=app.state.rq_redis).jobs
    class_book_id = jobs[-1].args[0]
    assert jobs[-1].func_name == "qamra_worker.jobs.classbooks.generate_class_book"
    assert (await client.post(f"{base}/book/generate")).json()["error"]["code"] == "class_book_busy"
    await worker_batch(adb, storage, class_book_id)

    # the school reviews and approves every copy at once, then our reviewers approve them for print
    review = (await client.get(f"{base}/book/review")).json()
    assert {c["status"] for c in review["copies"]} == {"ready"} and len(review["copies"]) == 4
    r = await client.post(f"{base}/book/approve", json={})
    assert {c["status"] for c in r.json()["copies"]} == {"approved"} and r.json()["status"] == "approved"
    async with browser(app) as ops:
        await make_admin(ops, adb, email="reviewer@example.com")
        queue = (await ops.get("/api/admin/books", params={"view": "review"})).json()
        assert len([b for b in queue if b["status"] == "in_review"]) == 4  # the admin review queue
        r = await ops.post(f"/api/admin/portal/class-books/{class_book_id}/approve")
        assert r.status_code == 200 and r.json()["approved"] == 4
        detail = r.json()["detail"]
        assert [c["appearances"] for c in detail["coverage"]] == [2, 2, 2, 2]
        assert len(detail["files"]) == 1 + 4 * 2  # the combined print file + an interior and a cover each
        combined = await ops.get(detail["files"][0]["path"])
        assert combined.status_code == 200 and "attachment" in combined.headers["content-disposition"]

    # wholesale prices from the price list, one order and one invoice for the class
    quote = (await client.get(f"{base}/order/quote")).json()
    assert quote["copies"] == 4 and quote["currency"] == "ILS" and quote["price_list"]
    assert quote["delivery"]["address"].startswith("شارع الإرسال")
    r = await client.post(f"{base}/order", json={"accept_terms": True})
    assert r.status_code == 201, r.text
    placed = r.json()
    orders = (await adb.execute(select(Order).where(Order.source == "portal"))).scalars().all()
    assert len(orders) == 1 and orders[0].code == placed["code"] and str(orders[0].organization_id) == org_id
    items = (await adb.execute(select(OrderItem).where(OrderItem.order_id == orders[0].id))).scalars().all()
    assert len(items) == 4 and all(i.book_id for i in items) and orders[0].shipping["name"] == "روضة القمر"
    invoices = (await adb.execute(select(func.count()).select_from(Invoice))).scalar_one()
    assert invoices == 1 and placed["invoice"].startswith("INV-")
    again = await client.post(f"{base}/order", json={"accept_terms": True})
    assert again.json()["error"]["code"] == "already_ordered"
    listed = (await client.get("/api/portal/orders")).json()
    assert [o["code"] for o in listed] == [placed["code"]] and listed[0]["copies"] == 4
    cb = await adb.get(ClassBook, uuid.UUID(class_book_id))
    assert cb is not None and cb.status.value == "ordered"
    books = (await adb.execute(select(Book).where(Book.status == BookStatus.approved))).scalars().all()
    assert len(books) == 4
    kids = (await adb.execute(select(func.count()).select_from(Child))).scalar_one()
    assert kids == 4
