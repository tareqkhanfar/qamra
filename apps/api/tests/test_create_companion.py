"""«ارسم صاحبك» through the API: upload → crop → draw → choose → the book and the cart; the free redraws, and
the photo privacy rules applied to the drawing."""

import io
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from api_helpers import register
from fastapi import FastAPI
from httpx import AsyncClient, Response
from PIL import Image
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from test_create import _child, _consent, _drawn, _photo

from qamra_api.routers.companions import MAX_ROUNDS
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_core.db.classic import ClassicTemplate, TemplateStatus
from qamra_core.db.models import AuditLog, Book, BookStatus, Companion, CompanionStatus
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.storage import ObjectStorage

FIXTURES = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures"
DRAWING = sorted((FIXTURES / "drawings").glob("drawing-*.jpg"))[0]


def _with_exif() -> bytes:
    """A phone photo of the drawing, with the camera maker and a GPS position in its EXIF."""
    with Image.open(DRAWING) as im:
        exif = Image.Exif()
        exif[0x010F] = "PhoneMaker"
        exif[0x8825] = {1: "N", 2: (31.0, 46.0, 0.0)}
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


async def _ready_child(client: AsyncClient, adb: AsyncSession, storage: ObjectStorage) -> tuple[Any, str]:
    """A consented child with an approved character: where the flow is when the companion step starts."""
    await upsert_themes(adb)
    await seed_store(adb)
    await register(client)
    child = await _child(client)
    await _consent(client, child["id"])
    assert await _photo(client, child["id"]) == 200
    r = await client.post(f"/api/create/children/{child['id']}/characters", json={"style": "watercolor"})
    character = r.json()["id"]
    await _drawn(adb, storage, character, child["id"])
    assert (await client.post(f"/api/create/characters/{character}/approve")).status_code == 200
    return child, character


async def _upload(client: AsyncClient, child_id: str, data: bytes | None = None) -> Response:
    files = {"drawing": ("drawing.jpg", data or DRAWING.read_bytes(), "image/jpeg")}
    return await client.post(f"/api/create/children/{child_id}/companions", files=files)


async def _options_drawn(adb: AsyncSession, storage: ObjectStorage, companion_id: str) -> list[str]:
    """What the worker does (apps/worker/tests/test_companion_job.py): 2 options for the parent."""
    comp = await adb.get(Companion, uuid.UUID(companion_id))
    assert comp is not None and comp.status == CompanionStatus.generating
    new = []
    for n in (1, 2):
        key = f"children/{comp.child_id}/companions/{comp.id}/option-{comp.regen_count}-{n}.png"
        storage.put(key, DRAWING.read_bytes(), "image/png")
        new.append({"key": key, "round": comp.regen_count, "provider": "fake", "model": "fake-1"})
    comp.options, comp.status = [*comp.options, *new], CompanionStatus.ready
    await adb.commit()
    return [str(o["key"]) for o in new]


async def _draw(client: AsyncClient, companion_id: str, **body: Any) -> Response:
    return await client.post(f"/api/create/companions/{companion_id}/draw", json={"name": "نونو", **body})


async def _classic_template(adb: AsyncSession, slug: str = "graduation") -> None:
    theme = (await adb.execute(select(ThemeRow).where(ThemeRow.slug == slug))).scalar_one()
    adb.add(  # a live Classic template for her look (Addendum 4 §1A)
        ClassicTemplate(
            theme_id=theme.id,
            theme_version=theme.version,
            art_style="watercolor",
            variant="girl_hijab",
            status=TemplateStatus.live,
            generation={},
        )
    )
    await adb.commit()


async def test_from_the_drawing_to_the_book_and_the_classic_cart(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    child, character = await _ready_child(client, adb, storage)
    r = await _upload(client, child["id"], _with_exif())
    assert r.status_code == 201, r.text
    comp = r.json()
    assert comp["status"] == "draft" and comp["original"] and comp["redraws_left"] == MAX_ROUNDS
    row = await adb.get(Companion, uuid.UUID(comp["id"]))
    assert row is not None and row.drawing_key and row.cleaned_key
    with Image.open(io.BytesIO(storage.get(row.drawing_key))) as stored:
        assert not stored.getexif()  # no camera details, no GPS position
    assert row.drawing_delete_after and row.drawing_delete_after > datetime.now(UTC) + timedelta(days=29)

    original = await client.get(f"/api/create/companions/{comp['id']}/drawing?kind=original")
    assert original.status_code == 200 and original.headers["cache-control"] == "private, no-store"
    before = storage.get(row.cleaned_key)
    crop = await client.post(
        f"/api/create/companions/{comp['id']}/crop",
        json={"box": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}, "rotate": 90, "clean": False},
    )
    assert crop.status_code == 200 and crop.json()["rotate"] == 90 and crop.json()["box"]["w"] == 0.8
    assert storage.get(row.cleaned_key) != before
    with Image.open(io.BytesIO(storage.get(row.cleaned_key))) as cleaned, Image.open(DRAWING) as photo:
        assert cleaned.size == (round(photo.height * 0.8), round(photo.width * 0.8))  # cropped, then turned

    queue = Queue("generation", connection=app.state.rq_redis)
    draw = await _draw(client, comp["id"], name="  نونو ", traits=["kind", "funny"])
    assert draw.status_code == 202 and draw.json()["status"] == "generating"
    assert queue.jobs[-1].func_name == "qamra_worker.jobs.companions.generate_companion"
    early = await client.post(f"/api/create/companions/{comp['id']}/choose", json={"option": 0})
    assert early.status_code == 409  # still drawing
    first, second = await _options_drawn(adb, storage, comp["id"])
    shown = (await client.get(f"/api/create/companions/{comp['id']}")).json()
    assert shown["status"] == "ready" and shown["options"] == 2 and shown["traits"] == ["funny", "kind"]
    assert shown["name"] == "نونو" and shown["redraws_left"] == MAX_ROUNDS - 1
    assert (await client.get(f"/api/create/companions/{comp['id']}/options/1/image")).status_code == 200
    chosen = await client.post(f"/api/create/companions/{comp['id']}/choose", json={"option": 1})
    assert chosen.status_code == 200 and chosen.json()["approved"] is True
    assert row.sheet_key == second and not storage.exists(first) and storage.exists(second)
    left = row.drawing_delete_after - datetime.now(UTC) if row.drawing_delete_after else None
    assert left and timedelta(hours=23) < left <= timedelta(hours=24)  # approval + 24h, like the photos
    mine = (await client.get("/api/create/companions")).json()
    assert [(c["name"], c["child_name"]) for c in mine] == [("نونو", "ليان")]

    await _classic_template(adb)
    body = {"child_id": child["id"], "character_id": character, "theme": "graduation", "line": "classic"}
    book = await client.post("/api/create/books", json={**body, "companion_id": comp["id"]})
    assert book.status_code == 201, book.text
    assert book.json()["companion"] == {"id": comp["id"], "name": "نونو"}
    stored_book = await adb.get(Book, uuid.UUID(book.json()["id"]))
    assert stored_book is not None and str(stored_book.companion_id) == comp["id"]
    cart = await client.post(f"/api/create/books/{book.json()['id']}/cart", json={"sku": "classic-soft-21"})
    assert cart.status_code == 201, cart.text
    addon = {a["slug"]: a for a in cart.json()["items"][0]["addons"]}["drawing-companion"]
    assert addon["included"] is False and Decimal(addon["amount"]) == Decimal("20")  # Classic: +20₪

    magic = await client.post("/api/create/books", json={**body, "line": "magic", "companion_id": comp["id"]})
    cart = await client.post(f"/api/create/books/{magic.json()['id']}/cart", json={"sku": "magic-hard-21"})
    magic_line = next(i for i in cart.json()["items"] if i["product"] == "magic-book")
    assert all(a["slug"] != "drawing-companion" or a["included"] for a in magic_line["addons"])  # in Magic
    assert (await client.get("/api/create/companions")).json()[0]["books"] == 2  # reused in both books


async def test_three_free_redraws_and_a_failed_round_is_not_one(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    child, _ = await _ready_child(client, adb, storage)
    comp = (await _upload(client, child["id"])).json()
    assert (await _draw(client, comp["id"], name=" ")).status_code == 422  # a name is needed
    for n in range(MAX_ROUNDS):
        r = await _draw(client, comp["id"], type="other", type_other="تنين صغير")
        assert r.status_code == 202, (n, r.text)
        assert (await _draw(client, comp["id"])).status_code == 409  # one drawing at a time
        if n == 1:  # this round failed on our side: the worker marks it, it is not counted
            row = await adb.get(Companion, uuid.UUID(comp["id"]))
            assert row is not None
            row.status, row.params = CompanionStatus.failed, {**row.params, "failed_rounds": 1}
            await adb.commit()
            assert (await client.get(f"/api/create/companions/{comp['id']}")).json()["redraws_left"] == 3
            assert (await _draw(client, comp["id"])).status_code == 202
        await _options_drawn(adb, storage, comp["id"])
    shown = (await client.get(f"/api/create/companions/{comp['id']}")).json()
    assert shown["redraws_left"] == 0 and shown["type"] == "other" and shown["type_other"] == "تنين صغير"
    last = await _draw(client, comp["id"])
    assert last.status_code == 429 and last.json()["error"]["code"] == "redraws_used"
    options = (await adb.get(Companion, uuid.UUID(comp["id"]))).options  # type: ignore[union-attr]
    assert sorted({o["round"] for o in options}) == [1, 3, 4, 5]  # round 2 failed; the rest wait for a choice
    chosen = await client.post(f"/api/create/companions/{comp['id']}/choose", json={"option": 0})
    assert chosen.status_code == 200  # the latest round's option


async def test_the_drawing_follows_the_photo_privacy_rules(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await register(client, email="first@example.com")
    other_child = await _child(client)
    assert (await _upload(client, other_child["id"])).status_code == 409  # consent first
    await client.post("/api/auth/logout")
    child, character = await _ready_child(client, adb, storage)
    comp = (await _upload(client, child["id"])).json()
    assert (await _upload(client, other_child["id"])).status_code == 404  # someone else's child
    bad = {"box": {"x": 0.5, "y": 0, "w": 0.8, "h": 1}}  # leaves the photo
    assert (await client.post(f"/api/create/companions/{comp['id']}/crop", json=bad)).status_code == 422

    body = {"child_id": child["id"], "character_id": character, "theme": "graduation", "line": "magic"}
    draft = await client.post("/api/create/books", json={**body, "companion_id": comp["id"]})
    assert draft.status_code == 409 and draft.json()["error"]["code"] == "companion_not_approved"
    await _draw(client, comp["id"])
    await _options_drawn(adb, storage, comp["id"])
    await client.post(f"/api/create/companions/{comp['id']}/choose", json={"option": 0})
    book = await client.post("/api/create/books", json={**body, "companion_id": comp["id"]})
    in_use = await client.delete(f"/api/create/companions/{comp['id']}")
    assert in_use.status_code == 409 and in_use.json()["error"]["code"] == "companion_in_use"

    await client.post("/api/auth/logout")
    await register(client, email="stranger@example.com")
    assert (await client.get(f"/api/create/companions/{comp['id']}")).status_code == 404
    assert (await client.get(f"/api/create/companions/{comp['id']}/image")).status_code == 404
    assert (await client.get("/api/create/companions")).json() == []
    await client.post("/api/auth/logout")
    await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "moonlight-2026"}
    )

    row = await adb.get(Book, uuid.UUID(book.json()["id"]))
    assert row is not None
    row.status = BookStatus.printed  # the book is done: the parent may now delete the drawing
    await adb.commit()
    prefix = f"children/{child['id']}/companions/{comp['id']}/"
    assert (await client.delete(f"/api/create/companions/{comp['id']}")).status_code == 204
    assert not storage.client.list_objects_v2(Bucket=storage.bucket, Prefix=prefix).get("Contents")
    assert (await adb.get(Companion, uuid.UUID(comp["id"]))) is None
    await adb.refresh(row)
    assert row.companion_id is None
    log = (await adb.execute(select(AuditLog).where(AuditLog.action == "companion.deleted"))).scalar_one()
    assert "نونو" not in str(log.data)


async def test_deleting_the_child_removes_the_drawings_now(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    child, _ = await _ready_child(client, adb, storage)
    comp = (await _upload(client, child["id"])).json()
    await _draw(client, comp["id"])
    await _options_drawn(adb, storage, comp["id"])
    prefix = f"children/{child['id']}/companions/"
    assert storage.client.list_objects_v2(Bucket=storage.bucket, Prefix=prefix).get("Contents")
    assert (await client.delete(f"/api/create/children/{child['id']}")).status_code == 204
    assert not storage.client.list_objects_v2(Bucket=storage.bucket, Prefix=prefix).get("Contents")
    adb.expire_all()
    assert (await adb.execute(select(Companion))).scalars().all() == []


async def test_a_rejected_drawing_needs_a_new_photo_not_a_redraw(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    child, _ = await _ready_child(client, adb, storage)
    comp = (await _upload(client, child["id"])).json()
    await _draw(client, comp["id"])
    row = await adb.get(Companion, uuid.UUID(comp["id"]))
    assert row is not None
    error = {"code": "drawing_rejected", "ar": "…", "en": "…"}  # what the worker writes after the review
    row.status, row.params = CompanionStatus.failed, {**row.params, "failed_rounds": 1, "error": error}
    await adb.commit()
    shown = (await client.get(f"/api/create/companions/{comp['id']}")).json()
    assert shown["error"]["code"] == "drawing_rejected" and shown["redraws_left"] == MAX_ROUNDS
    again = await _draw(client, comp["id"])
    assert again.status_code == 422 and again.json()["error"]["code"] == "invalid_drawing"
