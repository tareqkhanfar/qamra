"""«قلبي يعرف الله» (Addendum 10 §3.3, §9, §10): the scholar's review gates the store.

A volume is listed and sold only while the scholar has approved every unit of it; the reviewer role decides
(the owner's "*" does not stand in for it); units move draft → scholar_review → approved / changes_requested;
the export the page engine reads carries the scholar's name only with their consent."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from rq import Queue
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.islamic import (
    IslamicReviewer,
    IslamicReviewEvent,
    IslamicReviewPreview,
    IslamicScholarDecision,
    IslamicUnitReview,
    ReviewStatus,
)
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Character,
    Child,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Theme,
    User,
)
from qamra_core.db.store import CatalogProduct, Variant
from qamra_core.islamic_review import (
    ReviewState,
    Unit,
    build_export,
    content_units,
    credit_name,
    sellable_volumes,
    volumes_of,
)
from qamra_core.storage import ObjectStorage

REVIEW = "/api/admin/islamic/review"


@pytest.fixture(autouse=True)
async def _before_the_owner_decision(adb: AsyncSession) -> None:
    """These tests start from a review with nothing decided: migration 0c695b89fde0 (the owner's decision of
    2026-10-07) approves every unit, so its rows are removed inside the test's rolled-back transaction."""
    await adb.execute(delete(IslamicReviewEvent))
    await adb.execute(delete(IslamicUnitReview))
    await adb.flush()


@asynccontextmanager
async def _client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Another browser: each staff member signs in once (2FA codes are single use)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers={"X-Qamra-Client": "test"}
    ) as c:
        yield c


def _units(volume: str) -> list[Unit]:
    return [u for u in content_units() if u.volume == volume]


async def _approve(adb: AsyncSession, volume: str, *, but: tuple[str, ...] = ()) -> None:
    """Every unit of `volume` approved by the scholar (except `but`), as the review page leaves them."""
    for u in _units(volume):
        if u.id in but:
            continue
        await adb.merge(
            IslamicUnitReview(
                unit_id=u.id,
                volume=volume,
                status=ReviewStatus.approved,
                reviewer_name="الشيخ أحمد",
                decided_at=datetime.now(UTC),
                approved_at=datetime.now(UTC),
            )
        )
    await adb.commit()


async def _skus(client: AsyncClient) -> set[str]:
    products = {p["slug"]: p for p in (await client.get("/api/store/catalog")).json()["products"]}
    return {v["sku"] for v in products.get("islamic-series", {"variants": []})["variants"]}


# ---- the rules, without a database ----------------------------------------------------------------------


def test_a_variant_stands_for_its_volumes() -> None:
    assert volumes_of("V1") == ("V1",) and volumes_of("R") == ("R",)
    assert volumes_of("L1") == ("V1", "V2") and volumes_of("L2") == ("V3", "V4", "V5")
    assert volumes_of("set") == ("V1", "V2", "V3", "V4", "V5") and volumes_of("V9") == volumes_of(None) == ()
    assert sellable_volumes("L1", {"V1", "V2", "R"}) and not sellable_volumes("L1", {"V1"})
    assert not sellable_volumes("set", {"V1", "V2", "V3", "V4"}) and not sellable_volumes("", {"V1"})


def test_every_volume_has_its_units_and_a_front_and_back_matter_unit() -> None:
    units = content_units()
    assert {u.volume for u in units} == {"V1", "V2", "V3", "V4", "V5", "R"}
    assert len([u for u in units if not u.matter]) == 43  # the proposal's 43 units
    assert [u.id for u in units if u.matter] == [f"matter-{v}" for v in ("v1", "v2", "v3", "v4", "v5", "r")]
    assert _units("R")[-1].matter and len(_units("R")) == 7


def test_the_credit_names_only_scholars_who_agreed() -> None:
    assert credit_name([("الشيخ أحمد", True)]) == "الشيخ أحمد"
    assert credit_name([("الشيخ أحمد", True), ("د. محمد", True)]) == "الشيخ أحمد ود. محمد"
    assert credit_name([("الشيخ أحمد", True), ("د. محمد", False)]) is None
    assert credit_name([]) is None


def test_the_export_says_which_volumes_are_approved_and_by_whom() -> None:
    scholar = uuid.uuid4()
    units = (Unit("u-a", "R", "أ"), Unit("u-b", "R", "ب"), Unit("u-c", "V1", "ج"))
    day = datetime(2026, 10, 3, 9, tzinfo=UTC)
    rows = {
        uid: IslamicUnitReview(
            unit_id=uid,
            volume="R",
            status=ReviewStatus.approved,
            reviewer_user_id=scholar,
            reviewer_name="الشيخ أحمد",
            approved_at=day,
        )
        for uid in ("u-a", "u-b")
    }
    profile = IslamicReviewer(user_id=scholar, name_ar="الشيخ أحمد بن علي", may_be_named=False)
    state = ReviewState(rows=rows, reviewers={scholar: profile})
    data = build_export(state, units)
    assert data["version"] == 1 and data["volumes"]["R"]["approved"] is True
    assert data["volumes"]["R"]["approved_on"] == "2026-10-03" and data["volumes"]["R"]["units"] == [
        "u-a",
        "u-b",
    ]
    assert data["volumes"]["R"]["credit_name"] is None  # not without the scholar's consent
    assert data["volumes"]["V1"] == {
        "approved": False,
        "units": ["u-c"],
        "approved_on": None,
        "credit_name": None,
    }
    assert data["units"]["u-c"]["status"] == "draft" and data["units"]["u-a"]["reviewer"] == "الشيخ أحمد"
    profile.may_be_named = True
    assert build_export(state, units)["volumes"]["R"]["credit_name"] == "الشيخ أحمد بن علي"


# ---- the store ---------------------------------------------------------------------------------------------


async def test_the_store_lists_nothing_of_the_series_before_the_scholar_approves(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await seed_store(adb)
    product = (
        await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == "islamic-series"))
    ).scalar_one()
    assert product.active and product.line.value == "islamic"  # inserted like any product…
    assert await _skus(client) == set()  # …but not listed, not "coming", not anywhere
    products = (await client.get("/api/store/catalog")).json()["products"]
    assert "islamic-series" not in {p["slug"] for p in products}
    r = await client.post("/api/store/cart/items", json={"sku": "islamic-v1-softcover"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "unknown_product"
    assert "islamic-series" not in (await client.get("/api/shop/summary")).json()["orderable"]
    # the quiz's «تعليم ديني» never recommends it then
    answer = (await client.get("/api/shop/quiz?age=4&goal=faith")).json()
    assert answer["product"]["kind"] == "stories" and answer["product"]["available"] is True
    await _approve(adb, "R", but=("u-eid2",))  # one unit short
    assert await _skus(client) == set()


async def test_approving_every_unit_of_a_volume_puts_it_on_sale(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await seed_store(adb)
    await _approve(adb, "R")
    assert await _skus(client) == {"islamic-r-softcover", "islamic-r-digital"}  # that volume only
    assert (await client.get("/api/shop/summary")).json()["orderable"]["islamic-series"] is True
    r = await client.post("/api/store/cart/items", json={"sku": "islamic-r-softcover"})
    assert r.status_code == 201, r.text
    assert (await client.post("/api/store/cart/items", json={"sku": "islamic-v1-digital"})).status_code == 404
    answer = (await client.get("/api/shop/quiz?age=4&goal=faith")).json()  # the volume on sale, then stories
    assert answer["product"]["slug"] == "islamic-series" and answer["product"]["available"] is True
    assert Decimal(answer["product"]["from_price"]) == Decimal("79")

    await _approve(adb, "V1")
    assert {"islamic-v1-softcover", "islamic-v1-digital"} <= await _skus(client)
    assert "islamic-l1-softcover" not in await _skus(client)  # a set needs all of its volumes
    await _approve(adb, "V2")
    assert "islamic-l1-softcover" in await _skus(client) and "islamic-set-softcover" not in await _skus(
        client
    )

    # the admin can still close an approved volume, or the whole line
    await adb.execute(update(Variant).where(Variant.sku == "islamic-r-digital").values(active=False))
    await adb.commit()
    assert "islamic-r-digital" not in await _skus(client)
    product = (
        await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == "islamic-series"))
    ).scalar_one()
    product.features = {**product.features, "orderable": False}
    await adb.commit()
    r = await client.post("/api/store/cart/items", json={"sku": "islamic-v1-softcover"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_orderable"


async def test_a_unit_sent_back_takes_its_volume_off_sale(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)
    await _approve(adb, "R")
    async with _client(app) as scholar:
        await make_admin(scholar, adb, email="scholar@example.com", roles=("scholar",))
        r = await scholar.post(
            f"{REVIEW}/units/u-ram1/request-changes", json={"text": "راجعوا الصفحة", "page": 9}
        )
        assert r.status_code == 200 and r.json() == {
            "unit_id": "u-ram1",
            "status": "changes_requested",
            "volume_approved": False,
        }
    assert await _skus(client) == set()


# ---- who may do what ---------------------------------------------------------------------------------------


async def test_only_the_scholar_decides(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    await make_admin(client, adb, email="owner@example.com", roles=("owner",))
    assert (await client.get(REVIEW)).status_code == 200  # the owner sees everything…
    assert (await client.post(f"{REVIEW}/units/u-ram1/submit", json={})).status_code == 200
    r = await client.post(f"{REVIEW}/units/u-ram1/approve", json={})
    assert r.status_code == 403 and r.json()["error"]["code"] == "scholar_only"  # …but never stands in
    assert (await client.put(f"{REVIEW}/decisions/s-fasting-kids", json={"decision": "x"})).status_code == 403
    assert (
        await client.put(f"{REVIEW}/me", json={"name_ar": "أنا", "may_be_named": True})
    ).status_code == 403

    async with _client(app) as editor:
        await make_admin(editor, adb, email="editor@example.com", roles=("editor",))
        assert (await editor.post(f"{REVIEW}/units/u-ram2/submit", json={})).status_code == 200
        assert (await editor.post(f"{REVIEW}/units/u-ram2/approve", json={})).status_code == 403
        assert (await editor.post(f"{REVIEW}/units/u-ram2/notes", json={"text": "عدّلنا"})).status_code == 201
    async with _client(app) as support:
        await make_admin(support, adb, email="support@example.com", roles=("support",))
        assert (await support.get(REVIEW)).status_code == 403
        assert (await support.get(f"{REVIEW}/export")).status_code == 403
    async with _client(app) as reviewer:  # the books' reviewer reads the review, and writes nothing
        await make_admin(reviewer, adb, email="reviewer@example.com", roles=("reviewer",))
        assert (await reviewer.get(f"{REVIEW}/volumes/R")).status_code == 200
        assert (await reviewer.post(f"{REVIEW}/units/u-ram3/submit", json={})).status_code == 403
        assert (await reviewer.post(f"{REVIEW}/units/u-ram3/notes", json={"text": "x"})).status_code == 403
    async with _client(app) as scholar:
        await make_admin(scholar, adb, email="scholar@example.com", roles=("scholar",))
        assert (await scholar.post(f"{REVIEW}/units/u-ram3/submit", json={})).status_code == 403  # staff send
        assert (await scholar.post(f"{REVIEW}/units/u-ram1/approve", json={})).status_code == 200
        me = (await scholar.get(f"{REVIEW}/me")).json()
        assert me["scholar"] is True and me["can_edit"] is False


# ---- the review, unit by unit ----------------------------------------------------------------------------


async def test_a_unit_goes_through_the_review(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    await make_admin(client, adb, email="editor@example.com", roles=("editor",))
    detail = (await client.get(f"{REVIEW}/volumes/R")).json()
    unit = next(u for u in detail["units"] if u["id"] == "u-ram2")
    assert unit["status"] == "draft" and unit["pending_points"] == 1 and unit["pages"]
    assert all(p["preview"] is None for p in unit["pages"])  # no previews rendered yet
    point = next(s for s in unit["sources"] if s["question"])
    assert point["id"] == "s-fasting-kids" and point["decision"] is None
    assert any(p["sources"] for p in unit["pages"]) and detail["all_approved"] is False
    assert next(u for u in detail["units"] if u["id"] == "matter-r")["matter"] is True

    r = await client.post(f"{REVIEW}/units/u-ram2/submit", json={"text": "جاهزة"})
    assert r.status_code == 200 and r.json()["status"] == "scholar_review"
    r = await client.post(f"{REVIEW}/units/u-ram2/submit", json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "review_transition"
    assert (await client.post(f"{REVIEW}/units/u-nope/submit", json={})).status_code == 404

    async with _client(app) as scholar:
        await make_admin(scholar, adb, email="scholar@example.com", roles=("scholar",))
        r = await scholar.put(f"{REVIEW}/me", json={"name_ar": "  الشيخ   أحمد ", "may_be_named": True})
        assert r.status_code == 200 and r.json()["name_ar"] == "الشيخ أحمد"
        r = await scholar.post(f"{REVIEW}/units/u-ram2/approve", json={})
        assert r.status_code == 409 and r.json()["error"]["code"] == "decisions_pending"
        r = await scholar.put(f"{REVIEW}/decisions/s-fasting-kids", json={"decision": "صيام ساعات بلا إلزام"})
        assert r.status_code == 200 and r.json()["decided_by"] == "الشيخ أحمد"
        assert (await scholar.put(f"{REVIEW}/decisions/q-112", json={"decision": "x"})).status_code == 404
        r = await scholar.post(f"{REVIEW}/units/u-ram2/approve", json={"text": "أحسنتم"})
        assert r.status_code == 200 and r.json()["status"] == "approved"
        assert (await scholar.post(f"{REVIEW}/units/u-ram2/approve", json={})).status_code == 409
        # sending it back needs a note saying what to change
        r = await scholar.post(f"{REVIEW}/units/u-ram2/request-changes", json={"text": " "})
        assert r.status_code == 422
        r = await scholar.post(f"{REVIEW}/units/u-ram2/notes", json={"text": "ملاحظة على الصفحة", "page": 20})
        assert r.status_code == 201 and r.json()["events"][-1]["scholar"] is True

    row = await adb.get(IslamicUnitReview, "u-ram2")
    assert row is not None and row.reviewer_name == "الشيخ أحمد" and row.approved_at and row.submitted_at
    decision = await adb.get(IslamicScholarDecision, "s-fasting-kids")
    assert decision is not None and decision.question  # the point as it was asked is kept with the answer
    unit = next(u for u in (await client.get(f"{REVIEW}/volumes/R")).json()["units"] if u["id"] == "u-ram2")
    assert [e["kind"] for e in unit["events"]] == ["submitted", "approved", "note"]
    assert unit["pending_points"] == 0 and unit["reviewer_name"] == "الشيخ أحمد"
    # an approved unit whose pages changed goes back to the scholar, with a note saying what changed
    assert (await client.post(f"{REVIEW}/units/u-ram2/submit", json={})).status_code == 422
    r = await client.post(f"{REVIEW}/units/u-ram2/submit", json={"text": "غيّرنا صفحة 20"})
    assert r.status_code == 200 and r.json()["status"] == "scholar_review"
    row = await adb.get(IslamicUnitReview, "u-ram2")
    assert row is not None and row.approved_at is None
    actions = set(
        (await adb.execute(select(AuditLog.action).where(AuditLog.entity_type == "islamic_unit"))).scalars()
    )
    assert {"islamic.unit_submitted", "islamic.unit_approved"} <= actions

    overview = (await client.get(REVIEW)).json()
    assert [v["id"] for v in overview["volumes"]] == ["V1", "V2", "V3", "V4", "V5", "R"]
    assert next(v for v in overview["volumes"] if v["id"] == "R")["in_review"] == 1
    assert "s-illustrations" in {p["source_id"] for p in overview["general_points"]}  # no page cites it
    data = (await client.get(f"{REVIEW}/export")).json()
    assert data["units"]["u-ram2"]["status"] == "scholar_review"
    assert data["decisions"]["s-fasting-kids"]["decision"] == "صيام ساعات بلا إلزام"


async def test_the_review_pages_show_the_rendered_previews(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await make_admin(client, adb, email="editor@example.com", roles=("editor",))
    r = await client.post(f"{REVIEW}/volumes/R/previews")
    assert r.status_code == 202 and r.json()["status"] == "queued"
    jobs = [(j.func_name, tuple(j.args)) for j in Queue("generation", connection=app.state.rq_redis).jobs]
    run = r.json()["run_id"]
    assert ("qamra_worker.jobs.islamic_book.render_review_previews", ("R", run)) in jobs
    assert (await client.post(f"{REVIEW}/volumes/R/previews")).json()["error"]["code"] == "previews_busy"

    # what the worker leaves: one PNG per page in private storage
    keys = [f"islamic/review/R/{run}/p{n:03d}.png" for n in range(1, 72)]
    for key in keys:
        storage.put(key, b"\x89PNG-page", "image/png")
    await adb.execute(
        update(IslamicReviewPreview)
        .where(IslamicReviewPreview.volume == "R")
        .values(status="ready", pages=keys, rendered_at=datetime.now(UTC))
    )
    await adb.commit()
    detail = (await client.get(f"{REVIEW}/volumes/R")).json()
    assert detail["previews"]["status"] == "ready" and detail["pages_mismatch"] is False
    page = detail["units"][0]["pages"][0]
    assert page["preview"] == f"{REVIEW}/previews/R/{page['n']}?run={run}"
    png = await client.get(page["preview"])
    assert (
        png.status_code == 200
        and png.headers["content-type"] == "image/png"
        and png.content == b"\x89PNG-page"
    )
    assert (await client.get(f"{REVIEW}/previews/R/500")).status_code == 404
    assert (await client.get(f"{REVIEW}/previews/V9/1")).status_code == 404


# ---- orders: the worker job, and print approval ----------------------------------------------------------


async def _islamic_book(adb: AsyncSession, parent_id: str, volume: str) -> Book:
    child = Child(guardian_user_id=uuid.UUID(parent_id), first_name="آدم", gender=Gender.m, birth_year=2021)
    adb.add(child)
    await adb.flush()
    theme = (await adb.execute(select(Theme).where(Theme.slug == "islamic-series"))).scalar_one_or_none()
    if theme is None:
        theme = Theme(slug="islamic-series", title_ar="ق", title_en="x", age_min=4, age_max=8, definition={})
        adb.add(theme)
        await adb.flush()
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=1,
        language=Locale.ar,
        art_style="watercolor",
        status=BookStatus.in_review,
        title="قلبي يعرف الله",
        generation={"line": "islamic", "order_item_id": str(uuid.uuid4()), "volume": volume},
        preflight={"interior.pdf": {"passed": True}, "cover.pdf": {"passed": True}},
        pdf_interior_key="children/x/books/y/files/interior.pdf",
        pdf_cover_key="children/x/books/y/files/cover.pdf",
    )
    adb.add(book)
    await adb.commit()
    return book


async def test_print_approval_and_retry_follow_the_line(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await make_admin(client, adb)
    owner = (await adb.execute(select(User).where(User.email == "admin@example.com"))).scalar_one()
    book = await _islamic_book(adb, str(owner.id), "R")
    r = await client.post(f"/api/admin/books/{book.id}/approve")
    assert r.status_code == 409 and r.json()["error"]["code"] == "scholar_not_approved"
    await _approve(adb, "R")
    r = await client.post(f"/api/admin/books/{book.id}/approve")
    assert r.status_code == 200 and r.json()["status"] == "approved"

    retry = await _islamic_book(adb, str(owner.id), "V1")
    retry.status = BookStatus.failed
    await adb.commit()
    assert (
        await client.post(f"/api/admin/books/{retry.id}/generate", json={"mode": "final"})
    ).status_code == 202
    jobs = [(j.func_name, tuple(j.args)) for j in Queue("generation", connection=app.state.rq_redis).jobs]
    assert jobs[-1] == (
        "qamra_worker.jobs.islamic_book.render_islamic_item",
        (retry.generation["order_item_id"],),
    )


async def test_confirming_an_order_starts_its_volumes(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)
    parent = await register(client)
    order = Order(
        code="QM-ISLAMI1",
        user_id=uuid.UUID(parent["id"]),
        status=OrderStatus.new,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("79"),
        total=Decimal("79"),
        shipping={"name": "أم آدم", "city": "البيرة", "phone": "0591234567", "address": "حي الجنان"},
        phone="0591234567",
    )
    adb.add(order)
    await adb.flush()
    adb.add(
        OrderItem(
            order_id=order.id,
            sku="islamic-r-softcover",
            line="islamic",
            title={"name_ar": "قلبي يعرف الله", "options": {"volume": "R", "format": "softcover"}},
            personalization={"child_name": "آدم"},
            quantity=1,
            unit_price=Decimal("79"),
        )
    )
    await adb.commit()
    await make_admin(client, adb)
    r = await client.post(f"/api/admin/orders/{order.id}/status", json={"to": "confirmed"})
    assert r.status_code == 200, r.text
    jobs = [(j.func_name, tuple(j.args)) for j in Queue("generation", connection=app.state.rq_redis).jobs]
    assert ("qamra_worker.jobs.islamic_book.render_order_islamic_items", (str(order.id),)) in jobs


async def test_a_parent_adds_an_approved_volume_for_their_child(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await seed_store(adb)
    await _approve(adb, "R")
    me = await register(client, email="mom@example.com")
    child = Child(
        guardian_user_id=uuid.UUID(me["id"]),
        first_name="مريم",
        gender=Gender.f,
        birth_year=2021,
        wears_hijab=True,
    )
    adb.add(child)
    await adb.flush()
    adb.add(Character(child_id=child.id, art_style="watercolor", approved_at=datetime.now(UTC)))
    await adb.commit()
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "islamic-r-digital", "child_id": str(child.id)}
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "islamic-v2-digital", "child_id": str(child.id)}
    )
    assert r.status_code == 404  # not approved: not sold


# ---- the owner's decision of 2026-10-07 (migration 0c695b89fde0) ----------------------------------------


def _owner_decision() -> Any:
    import importlib.util
    from pathlib import Path

    from qamra_core import migrations

    path = next((Path(migrations.__file__).parent / "versions").glob("*_0c695b89fde0_*.py"))
    spec = importlib.util.spec_from_file_location("owner_decision", path)
    assert spec is not None and spec.loader is not None
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    return mig


def test_the_owner_decision_covers_every_review_unit() -> None:
    """The migration's unit list is exactly the review workflow's (units.yaml + each volume's matter)."""
    mig = _owner_decision()
    want: dict[str, list[str]] = {}
    for u in content_units():
        want.setdefault(u.volume, []).append(u.id)
    assert {v: list(ids) for v, ids in mig.UNITS.items()} == want


async def test_the_owner_decision_opens_the_series_without_naming_anyone(
    client: AsyncClient, adb: AsyncSession
) -> None:
    import yaml

    from qamra_api.seed_store import CATALOG
    from qamra_core.islamic_review import load_state

    mig = _owner_decision()
    await seed_store(adb)
    assert await _skus(client) == set()

    async def run(step: Any) -> None:
        await adb.run_sync(lambda s: step(s.connection()))
        adb.expire_all()

    await run(mig.approve)
    await run(mig.approve)  # idempotent
    every = {f"islamic-{v}-softcover" for v in ("v1", "v2", "v3", "v4", "v5", "r", "l1", "l2", "set")} | {
        f"islamic-{v}-digital" for v in ("v1", "v2", "v3", "v4", "v5", "r")
    }
    assert await _skus(client) == every
    rows = (await adb.execute(select(IslamicUnitReview))).scalars().all()
    assert len(rows) == len(mig.unit_ids()) and all(r.status == ReviewStatus.approved for r in rows)
    assert all(r.reviewer_name is None and r.reviewer_user_id is None and r.approved_at for r in rows)
    events = (await adb.execute(select(IslamicReviewEvent))).scalars().all()
    assert len(events) == len(rows)
    assert all(e.text == mig.NOTE and e.author_name == "—" and not e.scholar for e in events)
    export = build_export(await load_state(adb))
    assert all(v["approved"] and v["credit_name"] is None for v in export["volumes"].values())
    assert all(u["reviewer"] is None for u in export["units"].values())  # no name reaches a book

    # the public description: the seeded sentence about a scholar goes, nothing replaces it
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    entry = next(p for p in catalog["products"] if p["slug"] == mig.PRODUCT)
    product = (
        await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == mig.PRODUCT))
    ).scalar_one()
    for column, seeded, now in mig.DESCRIPTIONS:
        assert entry[column] == now
        setattr(product, column, seeded)
    product.features = {**product.features, "scholar_review": True}
    pid = product.id
    await adb.commit()
    await run(lambda c: mig.descriptions(c, forward=True))
    after = await adb.get(CatalogProduct, pid)
    assert after is not None and "scholar_review" not in after.features
    assert [getattr(after, c) for c, _, _ in mig.DESCRIPTIONS] == [n for _, _, n in mig.DESCRIPTIONS]

    await run(mig.revert)
    assert await _skus(client) == set()
    rows = (await adb.execute(select(IslamicUnitReview))).scalars().all()
    assert all(r.status == ReviewStatus.draft and r.approved_at is None for r in rows)
    assert (await adb.execute(select(IslamicReviewEvent))).scalars().all() == []
