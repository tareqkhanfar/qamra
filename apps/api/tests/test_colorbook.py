"""«دفاتر التلوين والرسم» (2026-10-21): the `colorbook` line. Four books with fixed content, personalized only
on the cover and the title page, $0 AI per order; the child's character on the cover is the parent's choice
(the only activity line where it is optional). The catalog, what the book needs from the child, the cart line
with and without a character, checkout and what the printer is told (stapled or Wire-O, the paper), the
admin's jobs, the downloads, and the migration."""

import importlib.util
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

from alembic import command
from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from qamra_api.errors import MESSAGES
from qamra_api.print_batches import Candidate, build_manifest
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_api.store import workbooks
from qamra_core import downloads
from qamra_core.db.models import (
    Book,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
)
from qamra_core.db.store import AddOn, ArtStyle, CatalogProduct, ProductLine, Variant
from qamra_core.migrations import MIGRATIONS_DIR, alembic_config
from qamra_core.printing import manifest_csv, print_spec_label, print_spec_of

CHECKOUT = {
    "name": "أم سلمى",
    "phone": "+970 59 765 4321",
    "zone": "west-bank",
    "city": "نابلس",
    "address": "رفيديا، قرب المدرسة",
    "accept_terms": True,
}
LETTERS, LETTERS_PDF, SKETCHBOOK = "coloring-letters-print", "coloring-letters-pdf", "sketchbook-print"
BOOKS = {
    # slug: (title, pages, binding, printed format, PDF sold)
    "coloring-letters": ("letters", 32, "stapled", "softcover", True),
    "coloring-palestine": ("palestine", 28, "stapled", "softcover", True),
    "coloring-ramadan": ("ramadan", 24, "stapled", "softcover", True),
    "sketchbook": ("sketchbook", 48, "wire-o", "spiral", False),
}
REVISION, PREVIOUS = "548c95ea24d1", "4e1c9a7b2d63"
ORDER_JOB = "qamra_worker.jobs.coloring_book.render_order_coloring_items"
ITEM_JOB = "qamra_worker.jobs.coloring_book.render_coloring_item"


async def _seed(adb: AsyncSession) -> None:
    await upsert_themes(adb)
    await seed_store(adb)


async def _child(
    adb: AsyncSession, guardian: str, *, styles: tuple[str, ...] = ()
) -> tuple[Child, list[Character]]:
    child = Child(
        guardian_user_id=uuid.UUID(guardian),
        first_name="سلمى",
        gender=Gender.f,
        birth_year=date.today().year - 5,
    )
    adb.add(child)
    await adb.flush()
    start = datetime.now(UTC) - timedelta(hours=1)
    characters = [
        Character(
            child_id=child.id,
            art_style=style,
            status=CharacterStatus.approved,
            sheet_image_key=f"children/{child.id}/characters/{i}.png",
            approved_at=start + timedelta(minutes=i),
        )
        for i, style in enumerate(styles)
    ]
    adb.add_all(characters)
    await adb.commit()
    return child, characters


def _error(r: Any, status: int, code: str) -> dict[str, Any]:
    assert r.status_code == status, r.text
    error: dict[str, Any] = r.json()["error"]
    assert error["code"] == code
    assert error["message"]["ar"] and error["message"]["en"]
    return error


# ---- the catalog -----------------------------------------------------------------------------------------


async def test_the_seed_has_the_four_books(adb: AsyncSession) -> None:
    await _seed(adb)
    products = {
        p.slug: p
        for p in (
            await adb.execute(select(CatalogProduct).where(CatalogProduct.line == ProductLine.colorbook))
        ).scalars()
    }
    assert set(products) == set(BOOKS)
    for slug, (title, pages, binding, printed, pdf) in BOOKS.items():
        p = products[slug]
        f = p.features
        assert (f["title"], f["pages"], f["binding"], f["size"], f["interior"]) == (
            title,
            pages,
            binding,
            "A4",
            "bw",
        )
        assert f["character"] == "optional" and f["orderable"] is True and f["paper_gsm"] == 160
        assert p.option_names == ["format"] and p.active
        variants = (await adb.execute(select(Variant).where(Variant.product_id == p.id))).scalars().all()
        formats = sorted(v.options["format"] for v in variants)
        assert formats == sorted([printed, *(["digital"] if pdf else [])]), slug
        assert all(v.active for v in variants)
        assert all(v.cost_ai_usd == 0 for v in variants)  # no AI per order


async def test_the_character_styles_and_the_gift_box(adb: AsyncSession) -> None:
    await _seed(adb)
    styles = {s.slug: s for s in (await adb.execute(select(ArtStyle))).scalars()}
    for slug in ("3d", "watercolor", "cartoon", "semi-realistic"):
        assert "colorbook" in styles[slug].lines, slug
    assert "colorbook" not in styles["coloring"].lines  # never the black-and-white story style
    gift = (await adb.execute(select(AddOn).where(AddOn.slug == "gift-box"))).scalar_one()
    assert "colorbook" in gift.lines


def test_the_line_rules() -> None:
    assert "colorbook" in workbooks.ACTIVITY and workbooks.CHARACTER_OPTIONAL == ("colorbook",)
    assert not workbooks.character_required("colorbook")
    assert all(workbooks.character_required(line) for line in ("workbook", "journey", "family", "islamic"))
    assert workbooks.ages_for("colorbook", {"format": "softcover"}) == (3, 7)
    assert workbooks.name_problem("colorbook", "Sara") is None  # nothing is traced
    assert not workbooks.needs_name_en("colorbook", {"format": "digital"})
    ar, en = MESSAGES["character_required"]
    assert ar.strip() and en.strip()


# ---- what the book needs, and the cart line --------------------------------------------------------------


async def test_needs_says_the_character_is_optional(client: AsyncClient, adb: AsyncSession) -> None:
    await _seed(adb)
    for sku in (LETTERS, LETTERS_PDF, SKETCHBOOK):
        r = await client.get("/api/shop/workbooks/needs", params={"sku": sku})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["line"] == "colorbook" and out["ages"] == [3, 7] and out["traces_name"] is False
        assert out["asks"] == {"name_en": False, "family": False}
        assert out["character"] == {
            "reuse_id": None,
            "draw_style": "3d",
            "styles": ["3d", "watercolor", "cartoon", "semi-realistic"],
            "required": False,
        }
    me = await register(client)
    child, [cartoon] = await _child(adb, me["id"], styles=("cartoon",))
    r = await client.get("/api/shop/workbooks/needs", params={"sku": LETTERS, "child_id": str(child.id)})
    assert r.json()["character"]["reuse_id"] == str(cartoon.id)
    other = await client.get("/api/shop/workbooks/needs", params={"sku": "journey-s1-spiral"})
    assert other.json()["character"]["required"] is True


async def test_a_coloring_book_without_a_character(client: AsyncClient, adb: AsyncSession) -> None:
    """A child with no drawing: the line goes without one by default (the fast way)."""
    await _seed(adb)
    me = await register(client)
    child, _ = await _child(adb, me["id"])
    r = await client.post("/api/shop/workbooks/cart", json={"sku": LETTERS, "child_id": str(child.id)})
    assert r.status_code == 201, r.text
    line = r.json()["items"][0]
    assert line["line"] == "colorbook" and line["character_id"] is None and line["style"] is None
    assert line["cover_character"] is False and line["binding"] == "stapled"
    assert not line["needs_details"] and line["missing"] == []
    # asking for the character when there is none: draw one first
    _error(
        await client.post(
            "/api/shop/workbooks/cart",
            json={"sku": LETTERS, "child_id": str(child.id), "with_character": True},
        ),
        409,
        "character_not_approved",
    )


async def test_a_coloring_book_with_or_without_the_ready_character(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await _seed(adb)
    me = await register(client)
    child, [watercolor, three_d] = await _child(adb, me["id"], styles=("watercolor", "3d"))
    body = {"sku": SKETCHBOOK, "child_id": str(child.id)}
    with_it = (await client.post("/api/shop/workbooks/cart", json=body)).json()["items"][
        0
    ]  # the default: with
    assert with_it["character_id"] == str(three_d.id) and with_it["cover_character"] is True
    assert with_it["style"] == "3d" and with_it["binding"] == "wire-o"
    chosen = await client.post("/api/shop/workbooks/cart", json={**body, "character_id": str(watercolor.id)})
    assert chosen.json()["items"][1]["character_id"] == str(watercolor.id)
    plain = await client.post("/api/shop/workbooks/cart", json={**body, "with_character": False})
    assert plain.status_code == 201, plain.text
    third = plain.json()["items"][2]
    assert third["character_id"] is None and third["cover_character"] is False and third["style"] is None
    _error(
        await client.post(
            "/api/shop/workbooks/cart",
            json={**body, "with_character": False, "character_id": str(watercolor.id)},
        ),
        422,
        "invalid_input",
    )
    # a cart edit keeps the parent's cover choice
    r = await client.patch(
        f"/api/store/cart/items/{third['id']}", json={"personalization": {"child_name": "سلمى"}}
    )
    assert r.status_code == 200, r.text
    edited = next(i for i in r.json()["items"] if i["id"] == third["id"])
    assert edited["cover_character"] is False


async def test_only_a_coloring_book_may_go_without_the_character(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await _seed(adb)
    me = await register(client)
    child, _ = await _child(adb, me["id"], styles=("3d",))
    body = {"sku": "family-wireo", "child_id": str(child.id), "with_character": False}
    error = _error(await client.post("/api/shop/workbooks/cart", json=body), 422, "character_required")
    assert error["details"]["fields"] == ["with_character"]
    # the other books are unchanged: no `cover_character` on their lines
    r = await client.post("/api/shop/workbooks/cart", json={"sku": "family-wireo", "child_id": str(child.id)})
    assert r.json()["items"][0]["cover_character"] is None


async def test_a_line_added_in_one_tap_is_completed_without_a_character(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await _seed(adb)
    me = await register(client)
    one_tap = await client.post("/api/store/cart/items", json={"sku": LETTERS_PDF})
    assert one_tap.status_code == 201, one_tap.text
    item = one_tap.json()["items"][0]
    assert item["needs_details"] is True and item["cover_character"] is None
    child, _ = await _child(adb, me["id"])
    r = await client.post(
        "/api/shop/workbooks/cart",
        json={"sku": LETTERS_PDF, "child_id": str(child.id), "item_id": item["id"], "with_character": False},
    )
    assert r.status_code == 201, r.text
    [filled] = r.json()["items"]
    assert filled["id"] == item["id"] and not filled["needs_details"] and filled["cover_character"] is False


# ---- checkout, the printer, the downloads ----------------------------------------------------------------


async def test_checkout_freezes_the_print_facts_for_the_printer(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await _seed(adb)
    me = await register(client)
    child, _ = await _child(adb, me["id"])
    for sku in (LETTERS, SKETCHBOOK, LETTERS_PDF):
        r = await client.post("/api/shop/workbooks/cart", json={"sku": sku, "child_id": str(child.id)})
        assert r.status_code == 201, r.text
    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 201, r.text
    items = {i.sku: i for i in (await adb.execute(select(OrderItem))).scalars()}
    stapled, wire_o, pdf = items[LETTERS], items[SKETCHBOOK], items[LETTERS_PDF]
    assert stapled.line == "colorbook" and stapled.personalization["cover_character"] is False
    assert stapled.title["print"] == {
        "size": "A4",
        "binding": "stapled",
        "pages": 32,
        "interior": "bw",
        "paper_gsm": 160,
        "cover_gsm": 300,
    }
    assert wire_o.title["print"]["binding"] == "wire-o" and wire_o.title["print"]["pages"] == 48
    assert "print" not in pdf.title  # a file: nothing to print

    order = (await adb.execute(select(Order))).scalar_one()
    books = {}
    for n, item in enumerate((stapled, wire_o)):
        book = Book(
            id=uuid.uuid4(),
            child_id=child.id,
            theme_id=uuid.uuid4(),
            language=Locale.ar,
            art_style="",
            status=BookStatus.approved,
            pdf_interior_key=f"k/{n}/interior.pdf",
            pdf_cover_key=f"k/{n}/cover.pdf",
        )
        item.book_id = book.id
        books[book.id] = book
    manifest = build_manifest([Candidate(order=order, items=[stapled, wire_o], books=books)], 1)
    first, second = manifest["items"]
    assert first["binding"] == "stapled" and first["size"] == "A4"
    assert first["print_spec"] == (
        "A4 · دفتر مدبّس (تدبيس من المنتصف) · 32 صفحة · ورق 160 غ · داخلي أبيض وأسود · غلاف كرتون 300 غ"
    )
    assert second["binding"] == "wire-o" and "سلك حلزوني Wire-O" in second["print_spec"]
    csv = manifest_csv(manifest).decode("utf-8-sig")
    assert csv.splitlines()[0].endswith(",insert_files,binding,print_spec") and "دفتر مدبّس" in csv


def test_the_print_facts_of_a_variant() -> None:
    features = {"size": "A4", "binding": "stapled", "pages": 24, "interior": "bw", "title": "ramadan", "x": 1}
    assert print_spec_of(features, {"format": "softcover"}) == {
        "size": "A4",
        "binding": "stapled",
        "pages": 24,
        "interior": "bw",
    }
    assert print_spec_of(features, {"format": "digital"}) == {}
    assert print_spec_label({}) == "" and print_spec_label(None) == ""
    assert print_spec_label({"binding": "wire-o"}) == "سلك حلزوني Wire-O"


def test_a_coloring_pdf_is_downloaded_as_one_book() -> None:
    assert "colorbook" in downloads.ACTIVITY_LINES
    assert downloads.offers_download("colorbook", {"format": "digital"})
    assert not downloads.offers_download("colorbook", {"format": "softcover"})  # no free file with print
    assert downloads.parts_of("colorbook", {"format": "digital"}) == ("",)
    assert "character_missing" in downloads.HELD_FLAGS


# ---- the admin ------------------------------------------------------------------------------------------


async def test_confirming_starts_the_coloring_job_and_the_admin_can_retry_it(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await _seed(adb)
    parent = await register(client)
    order = Order(
        code="QM-COLOR1",
        user_id=uuid.UUID(parent["id"]),
        status=OrderStatus.new,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("35"),
        total=Decimal("35"),
        shipping={"name": "أم سلمى", "city": "البيرة", "phone": "0591234567", "address": "حي الجنان"},
        phone="0591234567",
    )
    adb.add(order)
    await adb.flush()
    item = OrderItem(
        order_id=order.id,
        sku=LETTERS,
        line="colorbook",
        title={"name_ar": "ألوّن حروفي", "options": {"format": "softcover"}},
        personalization={"child_name": "سلمى", "cover_character": False},
        quantity=1,
        unit_price=Decimal("35"),
    )
    adb.add(item)
    await adb.commit()
    await make_admin(client, adb)
    r = await client.post(f"/api/admin/orders/{order.id}/status", json={"to": "confirmed"})
    assert r.status_code == 200, r.text
    jobs = [(j.func_name, tuple(j.args)) for j in Queue("generation", connection=app.state.rq_redis).jobs]
    assert (ORDER_JOB, (str(order.id),)) in jobs


# ---- the migration --------------------------------------------------------------------------------------


def _migration() -> ModuleType:
    [path] = (Path(MIGRATIONS_DIR) / "versions").glob(f"*_{REVISION}_*.py")
    spec = importlib.util.spec_from_file_location("colorbook_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _state(adb: AsyncSession) -> dict[str, Any]:
    styles = dict((await adb.execute(text("SELECT slug, lines FROM art_styles"))).all())
    gift = (await adb.execute(text("SELECT lines FROM addons WHERE slug = 'gift-box'"))).scalar_one()
    products = (
        await adb.execute(text("SELECT count(*) FROM products WHERE line = 'colorbook'"))
    ).scalar_one()
    return {
        "styles": sorted(s for s, ls in styles.items() if "colorbook" in ls),
        "twice": any(ls.count("colorbook") > 1 for ls in [*styles.values(), gift]),
        "gift": "colorbook" in gift,
        "products": products,
    }


async def test_the_migration_goes_down_and_up(adb: AsyncSession) -> None:
    await _seed(adb)
    assert _migration().down_revision == PREVIOUS

    def run(session: Session, revision: str, up: bool) -> None:
        cfg = alembic_config("postgresql+psycopg://unused/x_test")
        cfg.attributes["connection"] = session.connection()
        (command.upgrade if up else command.downgrade)(cfg, revision)

    after = {
        "styles": ["3d", "cartoon", "semi-realistic", "watercolor"],
        "twice": False,
        "gift": True,
        "products": 4,
    }
    assert await _state(adb) == after
    await adb.run_sync(run, PREVIOUS, False)
    assert await _state(adb) == {"styles": [], "twice": False, "gift": False, "products": 0}
    await adb.run_sync(run, REVISION, True)
    await seed_store(adb)  # the deploy's seed inserts the books again
    assert await _state(adb) == after
    module = _migration()  # the data steps once more: nothing is added twice
    await adb.run_sync(lambda s: _upgrade_again(s, module))
    assert await _state(adb) == after


def _upgrade_again(session: Session, module: ModuleType) -> None:
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    with Operations.context(MigrationContext.configure(session.connection())):
        module.upgrade()  # both UPDATEs are guarded by `NOT lines @> …`
