"""Classic templates in the admin (permissions, generation, from a sample book, review, locks, availability),
and Classic books in the create flow and on order confirmation."""

import uuid
from decimal import Decimal
from pathlib import Path

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.theme import Theme
from qamra_ai.pipeline.vowelize import source_hash, sources
from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_core.db.classic import ClassicTemplate, ClassicTemplatePage, TemplateJob, TemplateStatus
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
    User,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


def _queue(app: FastAPI) -> Queue:
    return Queue("generation", connection=app.state.rq_redis)


async def _theme(adb: AsyncSession, slug: str = "graduation") -> ThemeRow:
    await upsert_themes(adb)
    row = (await adb.execute(select(ThemeRow).where(ThemeRow.slug == slug))).scalar_one()
    return row


async def _drawn_template(
    adb: AsyncSession,
    theme: ThemeRow,
    variant: str = "girl_hijab",
    status: TemplateStatus = TemplateStatus.in_review,
) -> ClassicTemplate:
    """What the worker leaves behind: every page drawn, hero boxes found, the texts vowelized."""
    gender = "m" if variant == "boy" else "f"
    words = sources(Theme.model_validate(theme.definition), gender)  # type: ignore[arg-type]
    texts = {"hash": source_hash(words), "gender": gender, "texts": words.model_dump(), "kept": []}
    t = ClassicTemplate(
        theme_id=theme.id, theme_version=theme.version, art_style="watercolor", variant=variant,
        status=status, generation={"theme_def": theme.definition, "texts": texts},
    )  # fmt: skip
    adb.add(t)
    await adb.flush()
    for beat in range(18):
        hero = beat != 7
        adb.add(
            ClassicTemplatePage(
                template_id=t.id, beat=beat, image_key=f"classic/templates/{t.id}/print/{beat:02d}.jpg",
                preview_key=f"classic/templates/{t.id}/preview/{beat:02d}.jpg", has_hero=hero,
                hero_box={"x": 0.3, "y": 0.3, "w": 0.3, "h": 0.5} if hero else None,
            )
        )  # fmt: skip
    await adb.commit()
    return t


async def test_template_permissions(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    theme = await _theme(adb)
    await make_admin(client, adb, email="reviewer@example.com", roles=("reviewer",))
    assert (await client.get("/api/admin/classic/templates")).status_code == 200  # templates.view
    body = {"theme": "graduation", "variant": "boy"}
    assert (await client.post("/api/admin/classic/templates", json=body)).status_code == 403
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="editor@example.com", roles=("editor",))
    r = await client.post("/api/admin/classic/templates", json=body)
    assert r.status_code == 202, r.text
    assert r.json()["variant"] == "boy" and r.json()["job"] == "queued" and r.json()["theme"] == "graduation"
    job = _queue(app).jobs[-1]
    assert job.func_name == "qamra_worker.jobs.classic.generate_template" and job.args[0] == r.json()["id"]
    t = await adb.get(ClassicTemplate, uuid.UUID(r.json()["id"]))
    assert t is not None and t.theme_id == theme.id and t.generation["theme_def"]["slug"] == "graduation"
    assert (await client.post("/api/admin/classic/templates", json=body)).status_code == 409  # still queued
    assert (
        await client.post("/api/admin/classic/templates", json={**body, "variant": "robot"})
    ).status_code == 422


async def test_review_lock_and_publish(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage, app: FastAPI
) -> None:
    theme = await _theme(adb)
    t = await _drawn_template(adb, theme, status=TemplateStatus.draft)
    await make_admin(client, adb, roles=("editor",))
    base = f"/api/admin/classic/templates/{t.id}"
    r = await client.post(f"{base}/status", json={"to": "approved"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition"
    assert (await client.post(f"{base}/status", json={"to": "in_review"})).status_code == 200

    r = await client.patch(f"{base}/pages/3", json={"hero_box": {"x": 10, "y": 20, "w": 30, "h": 60}})
    assert r.status_code == 200 and r.json()["hero_box"] == {
        "x": 0.1,
        "y": 0.2,
        "w": 0.3,
        "h": 0.6,
    }  # percent
    bad = await client.patch(f"{base}/pages/3", json={"hero_box": {"x": 0.5, "y": 0.5, "w": 0.0, "h": 0.2}})
    assert bad.status_code == 422

    page1 = (
        await adb.execute(
            select(ClassicTemplatePage).where(
                ClassicTemplatePage.template_id == t.id, ClassicTemplatePage.beat == 1
            )
        )
    ).scalar_one()
    page1.hero_box = None
    words = t.generation["texts"]
    t.generation = {k: v for k, v in t.generation.items() if k != "texts"}  # not vowelized yet
    await adb.commit()
    r = await client.post(f"{base}/status", json={"to": "approved"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "template_incomplete"
    assert r.json()["error"]["details"] == {"drawn": 18, "total": 18, "hero_boxes": False, "texts": False}
    await client.patch(f"{base}/pages/1", json={"hero_box": {"x": 0.2, "y": 0.2, "w": 0.4, "h": 0.6}})
    queued = await client.post(f"{base}/texts", json={"refresh": True})
    assert queued.status_code == 202 and queued.json()["texts"]["vowelized"] is False
    job = _queue(app).jobs[-1]
    assert job.func_name == "qamra_worker.jobs.classic.vowelize_template" and job.args == (str(t.id), True)
    await adb.refresh(t)
    t.generation, t.job = {**t.generation, "texts": words}, TemplateJob.idle  # what the worker leaves
    await adb.commit()

    r = await client.post(f"{base}/status", json={"to": "approved"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert all(p["locked"] for p in r.json()["pages"])  # approving locks every page
    locked = await client.post(f"{base}/pages/2/regenerate")
    assert locked.status_code == 409 and locked.json()["error"]["code"] == "template_locked"
    assert (await client.post(f"{base}/status", json={"to": "live"})).json()["status"] == "live"

    listing = (await client.get("/api/themes?lang=ar")).json()
    grad = next(th for th in listing if th["slug"] == "graduation")
    assert grad["classic"] == {"watercolor": ["girl_hijab"]}  # the store offers Classic for this look only
    detail = (await client.get("/api/themes/graduation")).json()
    assert detail["classic"] == {"watercolor": ["girl_hijab"]}

    # unlocking and moving the hero box of a live template sends it back to review
    r = await client.patch(
        f"{base}/pages/2", json={"locked": False, "hero_box": {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.5}}
    )
    assert r.status_code == 200 and r.json()["locked"] is False
    refreshed = (await client.get(base)).json()
    assert refreshed["status"] == "in_review" and "changed_after_approval" in refreshed["flags"]


async def _sample_book(adb: AsyncSession, theme: ThemeRow, admin_email: str, **over: object) -> Book:
    admin = (await adb.execute(select(User).where(User.email == admin_email))).scalar_one()
    child = Child(
        guardian_user_id=admin.id, first_name="ريم", gender=Gender.f, birth_year=2020, wears_hijab=True,
        is_sample=True,
    )  # fmt: skip
    adb.add(child)
    await adb.flush()
    book = Book(
        child_id=child.id, theme_id=theme.id, theme_version=theme.version, language=Locale.ar,
        art_style="watercolor", status=BookStatus.approved, is_sample=True, pdf_interior_key="x.pdf",
        generation={"theme_def": theme.definition},
    )  # fmt: skip
    for key, value in over.items():
        setattr(book, key, value)
    adb.add(book)
    await adb.commit()
    return book


async def test_a_sample_book_becomes_a_template(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    theme = await _theme(adb, "first-day")
    await make_admin(client, adb, roles=("editor",))
    book = await _sample_book(adb, theme, "admin@example.com")
    body = {"book_id": str(book.id), "synthetic_child": True}
    r = await client.post("/api/admin/classic/templates/from-book", json=body)
    assert r.status_code == 202, r.text
    out = r.json()
    assert out["variant"] == "girl_hijab" and out["source"] == "sample_book" and out["status"] == "draft"
    job = _queue(app).jobs[-1]
    assert job.func_name == "qamra_worker.jobs.classic.template_from_book" and job.args == (
        out["id"],
        str(book.id),
    )
    busy = await client.post("/api/admin/classic/templates/from-book", json=body)
    assert busy.status_code == 409 and busy.json()["error"]["code"] == "busy"

    unconfirmed = await client.post("/api/admin/classic/templates/from-book", json={"book_id": str(book.id)})
    assert unconfirmed.status_code == 422  # the admin must confirm the child is invented
    draft = await _sample_book(adb, theme, "admin@example.com", status=BookStatus.preview)
    r = await client.post(
        "/api/admin/classic/templates/from-book", json={"book_id": str(draft.id), "synthetic_child": True}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "template_source_invalid"


async def _parent_with_character(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> tuple[str, str]:
    await register(client)
    child = (
        await client.post(
            "/api/create/children",
            json={"name": "ضحى", "gender": "f", "age": 5, "hijab": True, "interests": []},
        )
    ).json()
    await client.post(
        f"/api/create/children/{child['id']}/consent", json={"accept": True, "version": CONSENT_VERSION}
    )
    character = Character(
        child_id=uuid.UUID(child["id"]), art_style="watercolor", status=CharacterStatus.approved,
        sheet_image_key=f"children/{child['id']}/characters/c.png",
    )  # fmt: skip
    from datetime import UTC, datetime

    character.approved_at = datetime.now(UTC)
    adb.add(character)
    await adb.commit()
    storage.put(character.sheet_image_key or "", FACE.read_bytes(), "image/png")
    return child["id"], str(character.id)


async def test_classic_in_the_create_flow(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    theme = await _theme(adb, "first-day")
    await seed_store(adb)
    child_id, character_id = await _parent_with_character(client, adb, storage)
    body = {"child_id": child_id, "character_id": character_id, "theme": "first-day", "line": "classic"}
    r = await client.post("/api/create/books", json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "classic_unavailable"  # no template yet
    assert "سحري" in r.json()["error"]["message"]["ar"]

    other = await _drawn_template(adb, theme, variant="boy", status=TemplateStatus.live)
    assert (await client.post("/api/create/books", json=body)).status_code == 409  # a boy's template only
    t = await _drawn_template(adb, theme, variant="girl_hijab", status=TemplateStatus.live)
    r = await client.post("/api/create/books", json=body)
    assert r.status_code == 201, r.text
    book = r.json()
    assert book["status"] == "generating" and book["preview"] is True and book["line"] == "classic"
    job = _queue(app).jobs[-1]
    assert job.func_name == "qamra_worker.jobs.classic.generate_classic_book" and job.args[1] == "preview"
    row = await adb.get(Book, uuid.UUID(book["id"]))
    assert (
        row is not None and row.budget_usd == Decimal("0.54") and row.generation["template_id"] == str(t.id)
    )
    assert other.id != t.id


async def test_a_stuck_classic_draft_starts_when_its_template_goes_live(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    theme = await _theme(adb, "first-day")
    child_id, character_id = await _parent_with_character(client, adb, storage)
    parent = (await adb.execute(select(User).where(User.email == "salma.mom@example.com"))).scalar_one()
    old = Book(
        child_id=uuid.UUID(child_id), character_id=uuid.UUID(character_id), theme_id=theme.id,
        theme_version=theme.version, created_by_user_id=parent.id, language=Locale.ar, art_style="watercolor",
        status=BookStatus.draft, budget_usd=Decimal("3.00"), generation={"line": "classic"},
    )  # fmt: skip
    adb.add(old)
    await adb.commit()
    r = await client.get(f"/api/create/books/{old.id}")
    assert r.status_code == 200 and r.json()["status"] == "draft"  # still no template: nothing to start
    await _drawn_template(adb, theme, variant="girl_hijab", status=TemplateStatus.live)
    r = await client.get(f"/api/create/books/{old.id}")
    assert r.json()["status"] == "generating" and r.json()["preview"] is True
    job = _queue(app).jobs[-1]
    assert job.func_name == "qamra_worker.jobs.classic.generate_classic_book" and job.args == (
        str(old.id),
        "preview",
    )
    await adb.refresh(old)
    assert old.budget_usd == Decimal("0.54")  # the Magic cap it was given is replaced by the Classic one


async def test_confirming_an_order_draws_its_classic_books(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    theme = await _theme(adb)
    await make_admin(client, adb, roles=("support",))
    admin = (await adb.execute(select(User).where(User.email == "admin@example.com"))).scalar_one()
    child = Child(guardian_user_id=admin.id, first_name="آدم", gender=Gender.m, birth_year=2020)
    adb.add(child)
    await adb.flush()

    def book(status: BookStatus, line: str) -> Book:
        return Book(
            child_id=child.id, theme_id=theme.id, theme_version=theme.version, language=Locale.ar,
            art_style="watercolor", status=status, generation={"line": line},
        )  # fmt: skip

    preview, drawing, magic = (
        book(BookStatus.preview, "classic"),
        book(BookStatus.generating, "classic"),
        book(BookStatus.preview, "magic"),
    )
    adb.add_all([preview, drawing, magic])
    await adb.flush()
    order = Order(
        code="QM-CLASS1", user_id=admin.id, payment_method=PaymentMethod.cod, currency=Currency.ILS,
        subtotal=Decimal("69"), total=Decimal("69"), status=OrderStatus.new,
    )  # fmt: skip
    adb.add(order)
    await adb.flush()
    for b in (preview, drawing, magic):
        adb.add(OrderItem(order_id=order.id, book_id=b.id, unit_price=Decimal("69")))
    await adb.commit()
    r = await client.post(f"/api/admin/orders/{order.id}/status", json={"to": "confirmed"})
    assert r.status_code == 200, r.text
    classic_jobs = [
        j for j in _queue(app).jobs if j.func_name == "qamra_worker.jobs.classic.generate_classic_book"
    ]
    assert [j.args for j in classic_jobs] == [(str(preview.id), "final")]
    await adb.refresh(preview)
    await adb.refresh(drawing)
    assert preview.status == BookStatus.generating
    assert drawing.generation["final_requested"] is True  # it finishes its preview, then the whole book


async def test_classic_samples_and_invented_faces(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await _theme(adb)
    await make_admin(client, adb, roles=("reviewer",))
    r = await client.post(
        "/api/admin/classic/synthetic-faces", json={"gender": "f", "hijab": True, "seed": 3}
    )
    assert r.status_code == 202
    face = r.json()["id"]
    job = _queue(app).jobs[-1]
    assert job.func_name == "qamra_worker.jobs.classic.synthetic_face"
    assert job.args[0] == f"classic/synthetic/{face}.png" and job.args[1]["hijab"] is True
    assert (
        await client.get(f"/api/admin/classic/synthetic-faces/{face}")
    ).status_code == 409  # not drawn yet
    storage.put(f"classic/synthetic/{face}.png", FACE.read_bytes(), "image/png")
    got = await client.get(f"/api/admin/classic/synthetic-faces/{face}")
    assert got.status_code == 200 and got.content == FACE.read_bytes()
    bad = await client.post("/api/admin/classic/synthetic-faces", json={"gender": "f", "skin": "<script>"})
    assert bad.status_code == 422

    form = {
        "theme": "graduation",
        "name": "ريم",
        "gender": "f",
        "age": "5",
        "hijab": "true",
        "consent": "true",
    }
    files = [("photos", ("face.png", FACE.read_bytes(), "image/png"))]
    r = await client.post("/api/admin/classic/samples", data=form, files=files)
    assert r.status_code == 201, r.text
    book = await adb.get(Book, uuid.UUID(r.json()["book_id"]))
    assert book is not None and book.is_sample and book.generation["line"] == "classic"
    assert book.budget_usd == Decimal("0.54") and book.character_id is None
    job = _queue(app).jobs[-1]
    assert job.func_name == "qamra_worker.jobs.classic.generate_classic_book" and job.args[1] == "final"
    no_consent = await client.post(
        "/api/admin/classic/samples", data={**form, "consent": "false"}, files=files
    )
    assert no_consent.status_code == 422


async def test_a_second_book_reuses_the_approved_character(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    await _theme(adb)
    await seed_store(adb)
    child_id, character_id = await _parent_with_character(client, adb, storage)
    before = len(_queue(app).jobs)
    r = await client.post(f"/api/create/children/{child_id}/characters", json={"style": "watercolor"})
    assert r.status_code == 202 and r.json()["id"] == character_id and r.json()["approved"] is True
    assert len(_queue(app).jobs) == before  # no new drawing, no new cost
    redraw = await client.post(
        f"/api/create/children/{child_id}/characters", json={"style": "watercolor", "fixes": ["face"]}
    )
    assert redraw.status_code == 409  # a deliberate redraw needs the photo, which is gone after approval
    assert redraw.json()["error"]["code"] == "photo_required"


async def test_metrics_split_by_line(client: AsyncClient, adb: AsyncSession) -> None:
    theme = await _theme(adb)
    await make_admin(client, adb, roles=("owner",))
    admin = (await adb.execute(select(User).where(User.email == "admin@example.com"))).scalar_one()
    child = Child(guardian_user_id=admin.id, first_name="آدم", gender=Gender.m, birth_year=2020)
    adb.add(child)
    await adb.flush()

    def book(line: str, cost: str) -> Book:
        return Book(
            child_id=child.id, theme_id=theme.id, theme_version=theme.version, language=Locale.ar,
            art_style="watercolor", status=BookStatus.in_review, generation={"line": line},
            cost_usd=Decimal(cost),
        )  # fmt: skip

    classic, magic = book("classic", "0.40"), book("magic", "2.10")
    adb.add_all([classic, magic])
    await adb.flush()
    order = Order(
        code="QM-LINES1", user_id=admin.id, payment_method=PaymentMethod.cod, currency=Currency.ILS,
        subtotal=Decimal("69"), total=Decimal("69"), status=OrderStatus.new,
    )  # fmt: skip
    adb.add(order)
    await adb.flush()
    adb.add(OrderItem(order_id=order.id, book_id=classic.id, unit_price=Decimal("69")))
    await adb.commit()
    m = (await client.get("/api/admin/metrics")).json()
    assert m["books"] == 1 and m["avg_cost_per_book"] == 2.1  # Magic's own figures, judged by its cap
    assert m["lines"]["classic"]["books"] == 1 and m["lines"]["classic"]["avg_cost_per_book"] == 0.4
    assert m["lines"]["classic"]["preview_to_purchase"] == 1.0 and m["lines"]["magic"]["bought"] == 0
