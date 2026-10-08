"""Digital delivery (docs/plans/digital-delivery.md): the parent's PDFs.

The owner downloads a ready line; another parent gets 403; a story waits for staff to confirm its words; an
activity book waits for a clean render; a set gives every volume; printed lines give nothing but the journey's
answer key; every download is in the audit log with ids only; «حذف كل بيانات طفلي» removes the home copies.
"""

import io
import uuid
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from api_helpers import register
from fastapi import FastAPI
from httpx import AsyncClient
from pypdf import PdfWriter
from pypdf.generic import RectangleObject
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core import downloads as dl
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Child,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Theme,
)
from qamra_core.storage import ObjectStorage

MM = 72 / 25.4
PASSED = {"interior.pdf": {"passed": True}, "cover.pdf": {"passed": True}}


def print_pdf(pages: int, width_mm: float, height_mm: float, bleed_mm: float = 3.0) -> bytes:
    """A print file as the renderers write it: the page with its bleed, TrimBox inset by the bleed."""
    writer = PdfWriter()
    w, h, b = width_mm * MM, height_mm * MM, bleed_mm * MM
    for _ in range(pages):
        page = writer.add_blank_page(w, h)
        page.trimbox = RectangleObject([b, b, w - b, h - b])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class Shop:
    """Rows for one parent: their child, orders, lines and the books made for them (with print files)."""

    def __init__(self, adb: AsyncSession, storage: ObjectStorage, user_id: str, name: str = "ضحى") -> None:
        self.adb, self.storage, self.user_id, self.name = adb, storage, uuid.UUID(user_id), name
        self.child: Child | None = None
        self.theme: Theme | None = None
        self.n = 0

    async def setup(self) -> "Shop":
        self.child = Child(
            guardian_user_id=self.user_id, first_name=self.name, gender=Gender.f, birth_year=2021
        )
        self.theme = Theme(
            slug=f"t-{uuid.uuid4().hex[:8]}",
            title_ar="يوم تخرّجي",
            title_en="My graduation",
            age_min=3,
            age_max=7,
            definition={},
        )
        self.adb.add_all([self.child, self.theme])
        await self.adb.flush()
        return self

    async def order(
        self, status: OrderStatus = OrderStatus.confirmed, *, guest: bool = False, code: str | None = None
    ) -> Order:
        self.n += 1
        order = Order(
            code=code or f"QM-DL{self.n:03d}{uuid.uuid4().hex[:3].upper()}",
            user_id=None if guest else self.user_id,
            status=status,
            payment_method=PaymentMethod.cod,
            currency=Currency.ILS,
            subtotal=Decimal("29"),
            total=Decimal("29"),
            shipping={"name": "أم ضحى", "phone": "0591234567"},
            phone="0591234567",
        )
        self.adb.add(order)
        await self.adb.flush()
        return order

    async def line(
        self, order: Order, line: str, options: dict[str, str], *, sku: str, names: tuple[str, str]
    ) -> OrderItem:
        assert self.child is not None
        item = OrderItem(
            order_id=order.id,
            sku=sku,
            line=line,
            title={"name_ar": names[0], "name_en": names[1], "options": options},
            child_id=self.child.id,
            personalization={"child_name": self.name},
            quantity=1,
            unit_price=Decimal("29"),
        )
        self.adb.add(item)
        await self.adb.flush()
        return item

    async def book(
        self,
        status: BookStatus,
        *,
        item: OrderItem | None = None,
        generation: dict[str, Any] | None = None,
        title: str = "يوم تخرّج ضحى",
        flags: list[str] | None = None,
        story: bool = False,
        extras: tuple[str, ...] = (),
    ) -> Book:
        assert self.child is not None and self.theme is not None
        gen = dict(generation or {})
        if item is not None and not story:
            gen.update({"line": item.line, "order_item_id": str(item.id)})
        book = Book(
            child_id=self.child.id,
            theme_id=self.theme.id,
            theme_version=1,
            language=Locale.ar,
            art_style="3d",
            status=status,
            title=title,
            generation=gen,
            flags=flags or [],
            preflight=PASSED,
        )
        self.adb.add(book)
        await self.adb.flush()
        base = f"children/{self.child.id}/books/{book.id}/files/"
        book.pdf_interior_key, book.pdf_cover_key = base + "interior.pdf", base + "cover.pdf"
        if story:
            self.storage.put(book.pdf_interior_key, print_pdf(4, 216, 216), "application/pdf")
            self.storage.put(book.pdf_cover_key, print_pdf(1, 433.8, 216), "application/pdf")
            if item is not None:
                item.book_id = book.id
        else:
            self.storage.put(book.pdf_interior_key, print_pdf(6, 216, 286), "application/pdf")
            self.storage.put(book.pdf_cover_key, print_pdf(2, 216, 286), "application/pdf")
        files = {}
        for kind in extras:
            files[kind] = base + f"{kind}.pdf"
            self.storage.put(files[kind], print_pdf(2, 216, 286), "application/pdf")
        if files:
            book.generation = {**gen, "files": files}
        await self.adb.commit()
        return book


ISLAMIC = ("قلبي يعرف الله", "My Heart Knows Allah")
CLASSIC = ("قمرة كلاسيك", "Qamra Classic")
JOURNEY = ("رحلتي الأولى للتعلّم", "My First Learning Journey")
WORKBOOK = ("دوسية التأسيس", "Foundation workbook")


async def _parent(client: AsyncClient, adb: AsyncSession, storage: ObjectStorage, email: str) -> Shop:
    me = await register(client, email=email)
    return await Shop(adb, storage, me["id"]).setup()


def _copy(storage: ObjectStorage, book: Book, kind: str, data: bytes = b"%PDF-1.7 home copy") -> str:
    """What the worker leaves behind (`jobs.downloads.make_copy`)."""
    etags = [storage.etag(k) for k in dl.sources_of(book, kind)]
    key = dl.home_key(book, kind, dl.version_of([e for e in etags if e]))
    storage.put(key, data, "application/pdf")
    return key


def _url(item: OrderItem, book: Book, kind: str = "book") -> str:
    return f"/api/downloads/{item.id}/files/{book.id}/{kind}"


async def test_the_owner_downloads_a_ready_digital_story(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage, app: FastAPI
) -> None:
    shop = await _parent(client, adb, storage, "duha.mom@example.com")
    order = await shop.order(code="QM-DUHA01")
    item = await shop.line(
        order, "classic", {"format": "digital", "size": "21x21"}, sku="classic-digital", names=CLASSIC
    )
    book = await shop.book(BookStatus.approved, item=item, story=True)

    r = await client.get("/api/downloads")
    assert r.status_code == 200, r.text
    [line] = r.json()
    assert (
        line["status"] == "ready"
        and line["order_code"] == "QM-DUHA01"
        and line["book_title"] == "يوم تخرّج ضحى"
    )
    assert [(f["kind"], f["book_id"], f["name"]) for f in line["files"]] == [
        ("book", str(book.id), "يوم-تخرج-ضحى.pdf")  # no تشكيل in a file name; the name is in the title
    ]

    # the first tap asks the worker for the home copy, once
    r = await client.post(_url(item, book))
    assert r.status_code == 200 and r.json() == {
        "status": "preparing",
        "name": "يوم-تخرج-ضحى.pdf",
        "url": None,
    }
    await client.post(_url(item, book))
    jobs = Queue("pdf", connection=app.state.rq_redis).jobs
    assert [(j.func_name, j.args) for j in jobs] == [
        ("qamra_worker.jobs.downloads.prepare_file", (str(book.id), "book"))
    ]
    assert (await client.get(_url(item, book))).json()["status"] == "preparing"

    _copy(storage, book, "book", b"%PDF-1.7 home")
    r = await client.post(_url(item, book))
    url = f"{_url(item, book)}/pdf?lang=ar"
    assert r.json() == {"status": "ready", "name": "يوم-تخرج-ضحى.pdf", "url": url}

    r = await client.get(url)
    assert r.status_code == 200 and r.content == b"%PDF-1.7 home"
    assert (
        r.headers["content-type"] == "application/pdf" and r.headers["cache-control"] == "private, no-store"
    )
    disposition = r.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="qamra-qm-duha01.pdf"')
    assert f"filename*=UTF-8''{quote('يوم-تخرج-ضحى.pdf')}" in disposition

    [audit] = (await adb.execute(select(AuditLog).where(AuditLog.action == "download.file"))).scalars()
    assert audit.entity_type == "order_item" and audit.entity_id == str(item.id)
    assert audit.data == {"order": str(order.id), "book": str(book.id), "kind": "book"}  # ids only
    assert "ضحى" not in str(audit.data)


async def test_another_parent_gets_403(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    shop = await _parent(client, adb, storage, "owner@example.com")
    item = await shop.line(
        await shop.order(),
        "islamic",
        {"volume": "V1", "format": "digital"},
        sku="islamic-v1-digital",
        names=ISLAMIC,
    )
    book = await shop.book(
        BookStatus.in_review, item=item, generation={"volume": "V1"}, extras=("answer-key",)
    )
    _copy(storage, book, "book")
    await client.post("/api/auth/logout")
    await register(client, email="someone.else@example.com")

    assert (await client.get("/api/downloads")).json() == []
    for path in (f"/api/downloads/{item.id}", _url(item, book), f"{_url(item, book)}/pdf"):
        r = await client.get(path)
        assert r.status_code == 403, path
        assert r.json()["error"]["code"] == "download_not_yours"
        assert "حساب آخر" in r.json()["error"]["message"]["ar"]
    assert (await client.post(_url(item, book))).status_code == 403
    assert (await client.get(f"/api/downloads/{uuid.uuid4()}")).status_code == 404
    await client.post("/api/auth/logout")
    assert (await client.get(f"{_url(item, book)}/pdf")).status_code == 401


async def test_an_activity_book_waits_for_a_clean_render(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    shop = await _parent(client, adb, storage, "wait@example.com")
    item = await shop.line(
        await shop.order(),
        "islamic",
        {"volume": "V2", "format": "digital"},
        sku="islamic-v2-digital",
        names=ISLAMIC,
    )
    book = await shop.book(
        BookStatus.in_review, item=item, generation={"volume": "V2"}, flags=["preflight_failed"]
    )
    [line] = (await client.get("/api/downloads")).json()
    assert line["status"] == "preparing" and line["files"] == [] and line["parts_total"] == 1
    r = await client.post(_url(item, book))
    assert r.status_code == 409 and r.json()["error"]["code"] == "download_not_ready"
    assert r.json()["error"]["message"]["en"].startswith("We're still preparing this file")

    book.flags = []  # the render passed: ready without waiting for the print approval
    await adb.commit()
    [line] = (await client.get("/api/downloads")).json()
    assert line["status"] == "ready" and [f["name"] for f in line["files"]] == [
        "قلبي-يعرف-الله-المجلد-2-ضحى.pdf"
    ]

    book.status = BookStatus.generating  # the admin's retry renders it again
    await adb.commit()
    assert (await client.get("/api/downloads")).json()[0]["status"] == "preparing"


async def test_a_story_waits_for_staff_to_confirm_its_words(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    shop = await _parent(client, adb, storage, "story@example.com")
    item = await shop.line(
        await shop.order(),
        "classic",
        {"format": "digital", "size": "21x21"},
        sku="classic-digital",
        names=CLASSIC,
    )
    book = await shop.book(BookStatus.in_review, item=item, story=True)  # files rendered, words not confirmed
    _copy(storage, book, "book")
    [line] = (await client.get("/api/downloads")).json()
    assert line["status"] == "preparing" and line["files"] == []
    for r in (await client.post(_url(item, book)), await client.get(f"{_url(item, book)}/pdf")):
        assert r.status_code == 409 and r.json()["error"]["code"] == "download_not_ready"

    book.status = BookStatus.approved  # «تأكيد النص واعتماد الكتاب»
    await adb.commit()
    assert (await client.get(f"{_url(item, book)}/pdf")).status_code == 200


async def test_a_set_gives_every_volume(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    shop = await _parent(client, adb, storage, "set@example.com")
    options = {"level": "kg1", "volume": "set", "interior": "color", "format": "digital"}
    item = await shop.line(
        await shop.order(), "workbook", options, sku="wb-kg1-set-color-digital", names=WORKBOOK
    )
    books = []
    for volume in (1, 2):
        books.append(
            await shop.book(
                BookStatus.in_review,
                item=item,
                generation={"level": "kg1", "volume": volume},
                extras=("answer-key",),
            )
        )
    [line] = (await client.get("/api/downloads")).json()
    assert (line["status"], line["parts_ready"], line["parts_total"]) == ("preparing", 2, 3)
    assert len(line["files"]) == 4  # the two volumes made so far, each with its answer key

    books.append(
        await shop.book(
            BookStatus.approved, item=item, generation={"level": "kg1", "volume": 3}, extras=("answer-key",)
        )
    )
    [line] = (await client.get("/api/downloads")).json()
    assert line["status"] == "ready" and line["parts_ready"] == 3
    assert [(f["part"], f["kind"], f["name"]) for f in line["files"]] == [
        ("1", "book", "دوسية-التأسيس-KG1-الجزء-1-ضحى.pdf"),
        ("1", "answer-key", "مفتاح-الإجابات-دوسية-التأسيس-KG1-الجزء-1-ضحى.pdf"),
        ("2", "book", "دوسية-التأسيس-KG1-الجزء-2-ضحى.pdf"),
        ("2", "answer-key", "مفتاح-الإجابات-دوسية-التأسيس-KG1-الجزء-2-ضحى.pdf"),
        ("3", "book", "دوسية-التأسيس-KG1-الجزء-3-ضحى.pdf"),
        ("3", "answer-key", "مفتاح-الإجابات-دوسية-التأسيس-KG1-الجزء-3-ضحى.pdf"),
    ]
    r = await client.get(f"/api/downloads/{item.id}?lang=en")
    assert r.json()["files"][1]["name"] == "Answer-key-Foundation-workbook-KG1-Volume-1-ضحى.pdf"
    _copy(storage, books[2], "answer-key", b"%PDF answers")
    r = await client.get(f"{_url(item, books[2], 'answer-key')}/pdf")
    assert r.status_code == 200 and r.content == b"%PDF answers"
    assert 'filename="qamra-qm-' in r.headers["content-disposition"]
    assert "-kg1-3-answer-key.pdf" in r.headers["content-disposition"]


async def test_digital_and_printed_lines(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    shop = await _parent(client, adb, storage, "printed@example.com")
    order = await shop.order(OrderStatus.printing)
    hardcover = await shop.line(
        order, "classic", {"format": "softcover"}, sku="classic-soft-21", names=CLASSIC
    )
    await shop.book(BookStatus.approved, item=hardcover, story=True)
    printed = await shop.line(
        order, "journey", {"stage": "2", "format": "spiral"}, sku="journey-s2-spiral", names=JOURNEY
    )
    pbook = await shop.book(
        BookStatus.approved, item=printed, generation={"stage": 2}, extras=("answer-key",)
    )
    digital = await shop.line(
        order, "journey", {"stage": "3", "format": "digital"}, sku="journey-s3-digital", names=JOURNEY
    )
    await shop.book(BookStatus.in_review, item=digital, generation={"stage": 3}, extras=("answer-key",))

    lines = {line["item_id"]: line for line in (await client.get("/api/downloads")).json()}
    assert set(lines) == {str(printed.id), str(digital.id)}  # a printed story gives no file
    assert [f["kind"] for f in lines[str(printed.id)]["files"]] == ["answer-key"]  # Addendum 6 §5, free
    assert [f["kind"] for f in lines[str(digital.id)]["files"]] == ["book", "answer-key"]
    assert (await client.get(f"/api/downloads/{hardcover.id}")).status_code == 404
    r = await client.post(_url(printed, pbook, "book"))  # the printed book itself is never a download
    assert r.status_code == 404


async def test_which_orders_list_their_lines(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    shop = await _parent(client, adb, storage, "orders@example.com")
    options = {"volume": "V1", "format": "digital"}
    placed = await shop.line(
        await shop.order(OrderStatus.new), "islamic", options, sku="islamic-v1-digital", names=ISLAMIC
    )
    cancelled = await shop.line(
        await shop.order(OrderStatus.cancelled), "islamic", options, sku="islamic-v1-digital", names=ISLAMIC
    )
    guest = await shop.line(
        await shop.order(guest=True), "islamic", options, sku="islamic-v1-digital", names=ISLAMIC
    )
    await shop.book(BookStatus.in_review, item=guest, generation={"volume": "V1"})
    lines = {line["item_id"]: line for line in (await client.get("/api/downloads")).json()}
    assert str(cancelled.id) not in lines
    assert lines[str(placed.id)]["status"] == "preparing"  # waits for the order's confirmation
    assert lines[str(guest.id)]["status"] == "ready"  # checked out signed out: still the child's parent
    one = (await client.get(f"/api/downloads?order={lines[str(guest.id)]['order_code'].lower()}")).json()
    assert [line["item_id"] for line in one] == [str(guest.id)]
    assert (await client.get(f"/api/downloads/{cancelled.id}")).status_code == 404


async def test_a_failed_copy_can_be_asked_for_again(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage, app: FastAPI
) -> None:
    shop = await _parent(client, adb, storage, "retry@example.com")
    item = await shop.line(
        await shop.order(),
        "islamic",
        {"volume": "V3", "format": "digital"},
        sku="islamic-v3-digital",
        names=ISLAMIC,
    )
    book = await shop.book(BookStatus.approved, item=item, generation={"volume": "V3"})
    assert (await client.post(_url(item, book))).json()["status"] == "preparing"
    etags = [storage.etag(k) for k in dl.sources_of(book, "book")]
    version = dl.version_of([e for e in etags if e])
    redis = app.state.redis
    await redis.delete(dl.state_key(book.id, "book", version, "prep"))  # what the worker does on a failure
    await redis.set(dl.state_key(book.id, "book", version, "failed"), "1")
    assert (await client.get(_url(item, book))).json()["status"] == "failed"
    assert (await client.post(_url(item, book))).json()["status"] == "preparing"
    assert len(Queue("pdf", connection=app.state.rq_redis).jobs) == 2


async def test_the_order_page_gets_each_line_id(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    shop = await _parent(client, adb, storage, "track@example.com")
    order = await shop.order(code="QM-TRACK1")
    digital = await shop.line(
        order, "islamic", {"volume": "V1", "format": "digital"}, sku="islamic-v1-digital", names=ISLAMIC
    )
    printed = await shop.line(
        order, "islamic", {"volume": "V1", "format": "softcover"}, sku="islamic-v1-softcover", names=ISLAMIC
    )
    await adb.commit()
    r = await client.get("/api/store/orders/QM-TRACK1", params={"phone": "0591234567"})
    assert r.status_code == 200, r.text
    got = {i["id"]: i["downloadable"] for i in r.json()["items"]}
    assert got == {str(digital.id): True, str(printed.id): False}


async def test_deleting_the_child_removes_the_home_copies(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    shop = await _parent(client, adb, storage, "delete@example.com")
    item = await shop.line(
        await shop.order(),
        "classic",
        {"format": "digital", "size": "21x21"},
        sku="classic-digital",
        names=CLASSIC,
    )
    book = await shop.book(BookStatus.approved, item=item, story=True)
    key = _copy(storage, book, "book")
    assert key.startswith(f"children/{book.child_id}/books/{book.id}/home/book/")
    assert shop.child is not None
    r = await client.delete(f"/api/create/children/{shop.child.id}")
    assert r.status_code == 204, r.text
    assert not storage.exists(key) and not storage.exists(book.pdf_interior_key or "")
    assert (await client.get("/api/downloads")).json() == []
    assert (await client.get(f"/api/downloads/{item.id}")).status_code == 404
