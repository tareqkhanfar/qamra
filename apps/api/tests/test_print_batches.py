"""Print batches end to end with the fakes: collect approved printed orders (per day, per kindergarten),
send (orders → printing, books → ordered, the printer's email with links), the printer's link, the printer's
progress (printing → done: books printed), ship (orders → shipped), and the guards on the way."""

import re
import uuid
from decimal import Decimal
from typing import Any

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import (
    Book,
    BookStatus,
    Child,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    Organization,
    PaymentMethod,
    Theme,
)
from qamra_core.db.store import OrderEvent
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.print_batches import send_batch
from qamra_worker.notify.email import FakeEmailSender

S = OrderStatus
PRINTER = {"printer_email": "orders@printer.test", "printer_link_days": 14, "support_email": ""}


class World:
    def __init__(self, adb: AsyncSession, storage: ObjectStorage, parent_id: str) -> None:
        self.adb, self.storage, self.parent = adb, storage, uuid.UUID(parent_id)
        self.child: Child | None = None
        self.theme: Theme | None = None

    async def book(self, status: BookStatus = BookStatus.approved) -> Book:
        if self.child is None:
            self.child = Child(
                guardian_user_id=self.parent, first_name="ليان", gender=Gender.f, birth_year=2021
            )
            self.theme = Theme(
                slug="batch-theme", title_ar="ت", title_en="T", age_min=3, age_max=7, definition={}
            )
            self.adb.add_all([self.child, self.theme])
            await self.adb.flush()
        assert self.theme is not None
        book = Book(
            child_id=self.child.id,
            theme_id=self.theme.id,
            theme_version=1,
            language=Locale.ar,
            art_style="watercolor",
            status=status,
            title="ليان وحارس النجوم",
        )
        self.adb.add(book)
        await self.adb.flush()
        book.pdf_interior_key = f"children/{self.child.id}/books/{book.id}/files/interior.pdf"
        book.pdf_cover_key = f"children/{self.child.id}/books/{book.id}/files/cover.pdf"
        for key in (book.pdf_interior_key, book.pdf_cover_key):
            self.storage.put(key, b"%PDF-1.7 test", "application/pdf")
        return book

    async def order(
        self,
        code: str,
        status: OrderStatus,
        items: list[tuple[Book | None, str, list[dict[str, Any]]]],
        org: Any = None,
    ) -> Order:
        order = Order(
            code=code,
            user_id=self.parent,
            organization_id=org,
            status=status,
            payment_method=PaymentMethod.cod,
            currency=Currency.ILS,
            subtotal=Decimal("119"),
            total=Decimal("139"),
            shipping={"name": "أم ليان", "city": "البيرة", "phone": "0591234567", "address": "حي الجنان"},
            phone="0591234567",
        )
        self.adb.add(order)
        await self.adb.flush()
        for book, fmt, addons in items:
            self.adb.add(
                OrderItem(
                    order_id=order.id,
                    book_id=book.id if book else None,
                    sku=f"magic-{fmt}-21",
                    title={"name_ar": "قمرة سحري", "options": {"format": fmt, "size": "21"}},
                    personalization={"child_name": "ليان"},
                    addons=addons,
                    quantity=1,
                    unit_price=Decimal("119"),
                )
            )
        await self.adb.commit()
        return order


def _jobs(app: FastAPI) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        (j.func_name.rsplit(".", 1)[-1], tuple(j.args))
        for j in Queue("default", connection=app.state.rq_redis).jobs
    ]


async def _moves(adb: AsyncSession, order: Order) -> set[tuple[str | None, str]]:
    """(from, to) of the order's status events (one transaction in tests: timestamps can't order them)."""
    events = (await adb.execute(select(OrderEvent).where(OrderEvent.order_id == order.id))).scalars()
    return {
        (e.from_status.value if e.from_status else None, e.to_status.value) for e in events if e.to_status
    }


async def test_print_batch_flow(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    parent = await register(client)
    w = World(adb, storage, parent["id"])
    kg = Organization(name="روضة الأمل", status="approved")
    adb.add(kg)
    await adb.flush()
    book_a, book_b, book_c, book_d = (
        await w.book(),
        await w.book(),
        await w.book(BookStatus.in_review),
        await w.book(),
    )
    a = await w.order("QM-BATCHA", S.review, [(book_a, "hardcover", [{"slug": "extra-copy", "qty": 1}])])
    b = await w.order(
        "QM-BATCHB", S.confirmed, [(book_b, "softcover", [{"slug": "hardcover-upgrade", "qty": 1}])]
    )
    c = await w.order("QM-BATCHC", S.review, [(book_c, "hardcover", [])])  # book not approved yet
    d = await w.order("QM-BATCHD", S.review, [(book_d, "hardcover", [])], org=kg.id)  # the kindergarten's
    await w.order("QM-DIGITL", S.review, [(await w.book(), "digital", [])])  # nothing to print
    await w.order("QM-NEWONE", S.new, [(await w.book(), "hardcover", [])])  # not confirmed yet
    await make_admin(client, adb, email="print@example.com", roles=("production",))

    listed = (await client.get("/api/admin/print-batches")).json()
    assert {o["code"] for o in listed["ready"]} == {"QM-BATCHA", "QM-BATCHB", "QM-BATCHD"}
    assert [o["code"] for o in listed["waiting"]] == ["QM-BATCHC"] and listed["batches"] == []
    assert listed["printer_email_set"] is False

    collected = (await client.post("/api/admin/print-batches/collect")).json()
    assert collected["ready"] == [] and len(collected["batches"]) == 2
    families = next(x for x in collected["batches"] if x["organization"] is None)
    school = next(x for x in collected["batches"] if x["organization"] == "روضة الأمل")
    assert (families["orders"], families["books"], families["copies"], families["status"]) == (
        2,
        2,
        3,
        "open",
    )
    assert families["code"].startswith("PB-") and school["orders"] == 1
    again = (await client.post("/api/admin/print-batches/collect")).json()
    assert len(again["batches"]) == 2  # nothing new to collect: no empty batches

    # send: the manifest is frozen, the orders move to printing through the allowed steps
    sent = (await client.post(f"/api/admin/print-batches/{families['id']}/send")).json()
    assert sent["status"] == "sent" and sent["actions"] == ["printing", "resend"] and sent["email"] is None
    await adb.refresh(a)
    await adb.refresh(b)
    assert a.status == b.status == S.printing
    assert (S.review.value, S.printing.value) in await _moves(adb, a)
    assert {("confirmed", "generating"), ("generating", "review"), ("review", "printing")} <= await _moves(
        adb, b
    )
    for book in (book_a, book_b):
        await adb.refresh(book)
        assert book.status == BookStatus.ordered  # «قيد الطباعة» on the parent's shelf
    detail = (await client.get(f"/api/admin/print-batches/{families['id']}")).json()
    formats = {o["code"]: (o["items"][0]["format"], o["items"][0]["copies"]) for o in detail["items"]}
    assert formats == {"QM-BATCHA": ("hardcover", 2), "QM-BATCHB": ("hardcover", 1)}  # upgrade + extra copy
    assert _jobs(app)[0] == ("send_to_printer", (families["id"],))
    assert sorted(_jobs(app)[1:]) == sorted(
        [("send_order_email", (str(a.id), "printing")), ("send_order_email", (str(b.id), "printing"))]
    )

    # the worker's job: the printer's email with one link per file
    fake = FakeEmailSender()
    result = await adb.run_sync(
        lambda s: send_batch(s, storage, fake, families["id"], "http://testserver", PRINTER)
    )
    assert result == "sent" and fake.outbox[0].to == "orders@printer.test"
    token = re.search(r"/api/printer/([A-Za-z0-9_-]+)/files/1/interior", fake.outbox[0].text)
    assert token is not None
    r = await client.get(f"/api/printer/{token[1]}/files/1/interior", follow_redirects=False)
    assert r.status_code == 302 and "X-Amz-Expires=600" in r.headers["location"]
    assert r.headers["cache-control"] == "no-store"
    csv = await client.get(f"/api/printer/{token[1]}/manifest.csv")
    assert csv.status_code == 200 and "QM-BATCHA" in csv.text and "children/" not in csv.text
    assert (
        await client.get(f"/api/printer/{token[1]}/files/9/cover", follow_redirects=False)
    ).status_code == 404
    bad = await client.get(f"/api/printer/{'x' * 43}/files/1/interior", follow_redirects=False)
    assert bad.status_code == 404 and bad.json()["error"]["code"] == "link_expired"
    assert (await client.get(f"/api/admin/print-batches/{families['id']}")).json()["email"] == "sent"

    # the printer's progress, then the parcels leave
    early = await client.post(f"/api/admin/print-batches/{families['id']}/status", json={"to": "done"})
    assert early.status_code == 409
    await client.post(f"/api/admin/print-batches/{families['id']}/status", json={"to": "printing"})
    done = (
        await client.post(f"/api/admin/print-batches/{families['id']}/status", json={"to": "done"})
    ).json()
    assert done["status"] == "done" and done["actions"] == ["ship"] and done["done_at"]
    await adb.refresh(book_a)
    assert book_a.status == BookStatus.printed
    shipped = (await client.post(f"/api/admin/print-batches/{families['id']}/ship")).json()
    assert shipped["actions"] == [] and {o["status"] for o in shipped["items"]} == {"shipped"}
    assert sorted(_jobs(app)[-2:]) == sorted(
        [("send_order_email", (str(a.id), "shipped")), ("send_order_email", (str(b.id), "shipped"))]
    )
    assert (await client.post(f"/api/admin/print-batches/{families['id']}/ship")).status_code == 409
    assert (await client.post(f"/api/admin/print-batches/{families['id']}/resend")).status_code == 409

    # the kindergarten's batch: a cancelled order blocks sending until it's taken out
    d.status = S.cancelled
    await adb.commit()
    blocked = await client.post(f"/api/admin/print-batches/{school['id']}/send")
    assert blocked.status_code == 409 and blocked.json()["error"]["details"]["orders"] == ["QM-BATCHD"]
    out = await client.delete(f"/api/admin/print-batches/{school['id']}/orders/{d.id}")
    assert out.status_code == 200 and out.json()["orders"] == 0
    empty = await client.post(f"/api/admin/print-batches/{school['id']}/send")
    assert empty.status_code == 409 and empty.json()["error"]["code"] == "batch_empty"
    await adb.refresh(c)
    assert c.print_batch_id is None and c.status == S.review  # still waiting for its book's approval


async def test_resending_replaces_the_printers_link(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    parent = await register(client)
    w = World(adb, storage, parent["id"])
    await w.order("QM-RESEND", S.review, [(await w.book(), "hardcover", [])])
    await make_admin(client, adb, roles=("owner",))
    batch = (await client.post("/api/admin/print-batches/collect")).json()["batches"][0]
    await client.post(f"/api/admin/print-batches/{batch['id']}/send")
    first, second = FakeEmailSender(), FakeEmailSender()
    await adb.run_sync(lambda s: send_batch(s, storage, first, batch["id"], "http://testserver", PRINTER))
    old = re.search(r"/api/printer/([A-Za-z0-9_-]+)/", first.outbox[0].text)
    assert old is not None
    r = await client.post(f"/api/admin/print-batches/{batch['id']}/resend")
    assert r.status_code == 200 and _jobs(app)[-1] == ("send_to_printer", (batch["id"],))
    assert (await client.get(f"/api/printer/{old[1]}/manifest.csv")).status_code == 404  # replaced at once
    await adb.run_sync(lambda s: send_batch(s, storage, second, batch["id"], "http://testserver", PRINTER))
    new = re.search(r"/api/printer/([A-Za-z0-9_-]+)/", second.outbox[0].text)
    assert new is not None and new[1] != old[1]
    assert (await client.get(f"/api/printer/{new[1]}/manifest.csv")).status_code == 200


async def test_print_batches_need_the_print_permission(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb, roles=("support",))
    assert (await client.get("/api/admin/print-batches")).status_code == 403
    assert (await client.post("/api/admin/print-batches/collect")).status_code == 403
