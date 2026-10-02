from api_helpers import complete_cart, make_admin
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.models import Order, OrderStatus
from qamra_core.db.store import Invoice

CHECKOUT = {
    "name": "أم ليان",
    "phone": "0591234567",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "حي الجنان، قرب المسجد",
    "accept_terms": True,
}


async def _place(client: AsyncClient, adb: AsyncSession) -> str:
    r = await client.post(
        "/api/store/cart/items", json={"sku": "classic-soft-21", "personalization": {"child_name": "ليان"}}
    )
    assert r.status_code == 201, r.text
    await complete_cart(adb)
    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 201, r.text
    return str(r.json()["code"])


async def test_order_lifecycle(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    await seed_store(adb)
    codes = [await _place(client, adb), await _place(client, adb)]
    await make_admin(client, adb)
    listed = (await client.get("/api/admin/orders")).json()
    assert listed["total"] == 2 and listed["counts"] == {"new": 2}
    first = next(o for o in listed["orders"] if o["code"] == codes[0])
    detail = (await client.get(f"/api/admin/orders/{first['id']}")).json()
    assert (
        detail["next_statuses"] == ["confirmed", "cancelled"] and detail["items"][0]["child_name"] == "ليان"
    )
    assert detail["messages"]["confirmed"].startswith("https://wa.me/970591234567?text=")

    wrong = await client.post(f"/api/admin/orders/{first['id']}/status", json={"to": "shipped"})
    assert wrong.status_code == 409 and wrong.json()["error"]["code"] == "invalid_transition"

    queue = Queue("generation", connection=app.state.rq_redis)
    confirmed = (
        await client.post(f"/api/admin/orders/{first['id']}/status", json={"to": "confirmed"})
    ).json()
    assert confirmed["status"] == "confirmed" and confirmed["invoice"]["number"].endswith("-00001")
    jobs = [j.func_name for j in queue.jobs]  # the invoice, then the Classic book's final drawing
    assert jobs == [
        "qamra_worker.jobs.invoices.render_invoice",
        "qamra_worker.jobs.classic.generate_classic_book",
    ]
    second = next(o for o in listed["orders"] if o["code"] == codes[1])
    other = (await client.post(f"/api/admin/orders/{second['id']}/status", json={"to": "confirmed"})).json()
    assert other["invoice"]["number"].endswith("-00002")  # numbered per year, without gaps

    note = await client.post(
        f"/api/admin/orders/{first['id']}/notes", json={"note": "اتصلت بالأم، العنوان صحيح"}
    )
    assert note.json()["events"][-1]["kind"] == "note" and note.json()["events"][-1]["actor"]

    for step in ("generating", "review", "printing", "shipped"):
        r = await client.post(f"/api/admin/orders/{first['id']}/status", json={"to": step})
        assert r.status_code == 200, r.text
    no_items = await client.post(f"/api/admin/orders/{first['id']}/status", json={"to": "reprint"})
    assert no_items.status_code == 422
    item = detail["items"][0]["id"]
    reprint = await client.post(
        f"/api/admin/orders/{first['id']}/status",
        json={"to": "reprint", "items": [item], "note": "صفحة باهتة"},
    )
    assert reprint.json()["status"] == "reprint" and reprint.json()["events"][-1]["data"]["items"] == [item]
    order = (await adb.execute(select(Order).where(Order.code == codes[0]))).scalar_one()
    await adb.refresh(order)
    assert order.status == OrderStatus.reprint
    assert len((await adb.execute(select(Invoice))).scalars().all()) == 2


async def test_production_staff_can_view_but_not_change(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await _place(client, adb)
    await make_admin(client, adb, email="print@example.com", roles=("production",))
    listed = (await client.get("/api/admin/orders")).json()
    order = listed["orders"][0]["id"]
    assert (await client.get(f"/api/admin/orders/{order}")).status_code == 200
    r = await client.post(f"/api/admin/orders/{order}/status", json={"to": "confirmed"})
    assert r.status_code == 403
