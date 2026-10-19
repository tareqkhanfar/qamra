"""Book codes in the API (qamra_core.book_codes): staff find a book by its code in the books list and the
orders list, see each line's codes in the order, on the packing slip and in the print batch; the parent's
order page shows them; the public page the QR opens learns only the child's first name and the product.
"""

from api_helpers import make_admin, register
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from test_downloads import CLASSIC, WORKBOOK, Shop

from qamra_core.book_codes import CODE_RE
from qamra_core.db.models import BookStatus, OrderStatus
from qamra_core.storage import ObjectStorage


async def _yusuf(client: AsyncClient, adb: AsyncSession, storage: ObjectStorage, email: str) -> Shop:
    me = await register(client, email=email)
    return await Shop(adb, storage, me["id"], name="يوسف").setup()


async def _orders(client: AsyncClient, adb: AsyncSession, storage: ObjectStorage) -> tuple[Shop, dict]:  # type: ignore[type-arg]
    """Two children named يوسف (the owner's case), each with a book; one order also has a workbook set."""
    first = await _yusuf(client, adb, storage, "yusuf.1@example.com")
    order = await first.order(OrderStatus.printing, code="QM-CODE01")
    story_line = await first.line(
        order, "classic", {"format": "softcover"}, sku="classic-soft", names=CLASSIC
    )
    story = await first.book(BookStatus.approved, item=story_line, story=True, generation={"line": "classic"})
    set_line = await first.line(
        order, "workbook", {"level": "kg1", "volume": "set"}, sku="wb-set", names=WORKBOOK
    )
    volumes = [
        await first.book(BookStatus.approved, item=set_line, generation={"volume": v}, title=f"دوسية — {v}")
        for v in (3, 1, 2)
    ]
    await client.post("/api/auth/logout")
    second = await _yusuf(client, adb, storage, "yusuf.2@example.com")
    other = await second.order(OrderStatus.printing, code="QM-CODE02")
    other_line = await second.line(
        other, "classic", {"format": "softcover"}, sku="classic-soft", names=CLASSIC
    )
    other_book = await second.book(BookStatus.approved, item=other_line, story=True)
    await client.post("/api/auth/logout")
    return first, {
        "order": order,
        "story": story,
        "story_line": story_line,
        "set_line": set_line,
        "volumes": volumes,
        "other": other,
        "other_book": other_book,
    }


async def test_every_book_has_a_code_and_staff_find_it_by_code(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    _, made = await _orders(client, adb, storage)
    await make_admin(client, adb)
    story, other = made["story"], made["other_book"]
    assert CODE_RE.fullmatch(story.code) and story.code != other.code
    for typed in (story.code, story.code.lower(), story.code.replace("-", " "), story.code[3:]):
        found = (await client.get("/api/admin/books", params={"view": "all", "q": typed})).json()
        assert [b["code"] for b in found] == [story.code], typed
    part = (await client.get("/api/admin/books", params={"view": "all", "q": story.code[3:6]})).json()
    assert story.code in {b["code"] for b in part}
    detail = (await client.get(f"/api/admin/books/{story.id}")).json()
    assert detail["code"] == story.code
    by_name = (await client.get("/api/admin/books", params={"view": "all", "q": "يوسف"})).json()
    assert {story.code, other.code} <= {b["code"] for b in by_name}  # two يوسف: told apart by the code


async def test_orders_show_and_find_their_books_by_code(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    _, made = await _orders(client, adb, storage)
    await make_admin(client, adb)
    order, volumes = made["order"], made["volumes"]
    for code in (made["story"].code, volumes[0].code.lower()):
        rows = (await client.get("/api/admin/orders", params={"q": code})).json()["orders"]
        assert [r["code"] for r in rows] == ["QM-CODE01"], code
    rows = (await client.get("/api/admin/orders", params={"q": made["other_book"].code})).json()["orders"]
    assert [r["code"] for r in rows] == ["QM-CODE02"]

    detail = (await client.get(f"/api/admin/orders/{order.id}")).json()
    lines = {i["id"]: i for i in detail["items"]}
    story_books = lines[str(made["story_line"].id)]["books"]
    assert [b["code"] for b in story_books] == [made["story"].code] and story_books[0]["part"] == ""
    set_books = lines[str(made["set_line"].id)]["books"]
    by_volume = {str(v.generation["volume"]): v.code for v in volumes}
    assert [(b["part"], b["code"]) for b in set_books] == sorted(by_volume.items())  # volumes 1, 2, 3

    slip = (await client.get(f"/api/admin/orders/{order.id}/packing-slip")).json()
    codes = [i["book_codes"] for i in slip["items"]]
    assert [made["story"].code] in codes and [by_volume[k] for k in ("1", "2", "3")] in codes


async def test_the_parent_order_page_lists_the_codes(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    _, made = await _orders(client, adb, storage)
    r = await client.get("/api/store/orders/QM-CODE01", params={"phone": "0591234567"})
    assert r.status_code == 200, r.text
    codes = [i["book_codes"] for i in r.json()["items"]]
    assert [made["story"].code] in codes and len(next(c for c in codes if len(c) == 3)) == 3
    assert made["other_book"].code not in str(r.json())  # never another family's book


async def test_the_qr_page_learns_only_the_first_name_and_the_product(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    _, made = await _orders(client, adb, storage)
    story = made["story"]
    r = await client.get(f"/api/books/by-code/{story.code[3:].lower()}")
    assert r.status_code == 200, r.text
    assert r.json() == {
        "code": story.code,
        "child_name": "يوسف",
        "product_ar": "قمرة كلاسيك",
        "product_en": "Qamra Classic",
    }
    assert "no-store" in r.headers["cache-control"] and "noindex" in r.headers["x-robots-tag"]
    for missing in ("QB-22222", "QB-0OIL1", "hello", "QB-7K4M2-X"):
        gone = await client.get(f"/api/books/by-code/{missing}")
        assert gone.status_code == 404 and "child_name" not in gone.text, missing
    story.is_sample = True  # staff samples never answer
    await adb.commit()
    assert (await client.get(f"/api/books/by-code/{story.code}")).status_code == 404
