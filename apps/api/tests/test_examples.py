"""Public examples: only published, approved sample books of sample children are ever visible; their pages are
web-size, watermarked copies whose responses carry nothing about the child."""

import io
import uuid
from datetime import UTC, datetime, timedelta

from api_helpers import make_admin, register
from httpx import AsyncClient
from PIL import Image, ImageChops, ImageStat
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.theme import Theme as ThemeDef
from qamra_api.seed import upsert_themes
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Gender,
    Locale,
    PageStatus,
    Theme,
    User,
)
from qamra_core.storage import ObjectStorage

SHAPES = {"1:1": (1024, 1024), "3:2": (1200, 800), "16:9": (1600, 900)}


def _art(size: tuple[int, int], seed: int) -> bytes:
    """A smooth two-tone PNG, so the watermark shows up as a clear difference."""
    img = Image.linear_gradient("L").resize(size).convert("RGB")
    img = ImageChops.multiply(img, Image.new("RGB", size, (200, 150 + seed % 50, 120)))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _book(
    adb: AsyncSession,
    storage: ObjectStorage,
    *,
    slug: str = "first-day",
    name: str = "ليان",
    gender: Gender = Gender.f,
    hijab: bool = False,
    sample: bool = True,
    child_sample: bool | None = None,
    status: BookStatus = BookStatus.approved,
    public: bool = False,
) -> Book:
    """A drawn book with a page row (and stored art) for every beat of the theme's plan."""
    theme = (await adb.execute(select(Theme).where(Theme.slug == slug))).scalar_one_or_none()
    if theme is None:
        await upsert_themes(adb)
        theme = (await adb.execute(select(Theme).where(Theme.slug == slug))).scalar_one()
    owner = (await adb.execute(select(User).where(User.email == "admin@example.com"))).scalar_one()
    child = Child(
        guardian_user_id=owner.id,
        first_name=name,
        gender=gender,
        birth_year=2021,
        wears_hijab=hijab,
        is_sample=sample if child_sample is None else child_sample,
    )
    adb.add(child)
    await adb.flush()
    character = Character(child_id=child.id, art_style="watercolor", status=CharacterStatus.approved)
    adb.add(character)
    await adb.flush()
    character.sheet_image_key = f"children/{child.id}/characters/{character.id}.png"
    storage.put(character.sheet_image_key, _art((1536, 1024), 7), "image/png")
    definition = ThemeDef.model_validate(theme.definition)
    plan = plan_book(definition, "ar", companion_page=False)
    book = Book(
        child_id=child.id,
        character_id=character.id,
        theme_id=theme.id,
        theme_version=theme.version,
        language=Locale.ar,
        art_style="watercolor",
        status=status,
        is_sample=sample,
        title=f"{name} في أوّل يوم بالروضة",
        parent_message="نحبّكِ كثيرًا",
        story={"parents_lesson": "درس", "parents_questions": ["سؤال ١", "سؤال ٢"]},
        generation={"theme_def": theme.definition, **({"public_example": True} if public else {})},
    )
    adb.add(book)
    await adb.flush()
    for beat, bp in plan.beats.items():
        key = f"children/{child.id}/books/{book.id}/raw/{beat:02d}.png"
        storage.put(key, _art(SHAPES[bp.aspect], beat), "image/png")
        adb.add(
            BookPage(
                book_id=book.id,
                index=beat,
                layout=str(bp.layout),
                status=PageStatus.ok,
                image_key=key,
                text=None if beat == 0 else f"صفحة {beat} من حكاية {name}",
            )
        )
    await adb.commit()
    return book


async def test_only_published_sample_books_are_listed(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await make_admin(client, adb)
    shown = await _book(adb, storage, public=True, hijab=True)
    await _book(adb, storage, name="سلمى")  # approved sample, not published
    await _book(adb, storage, name="يوسف", gender=Gender.m, public=True, status=BookStatus.in_review)
    # a real child's book, even with the flag forged into the database, is never public
    real = await _book(adb, storage, name="مريم", sample=False, public=True)
    mixed = await _book(adb, storage, name="هدى", child_sample=False, public=True)
    await client.post("/api/auth/logout")

    r = await client.get("/api/examples?theme=first-day&lang=ar")
    assert r.status_code == 200 and r.headers["cache-control"] == "public, max-age=60"
    examples = r.json()
    assert [e["id"] for e in examples] == [str(shown.id)]
    e = examples[0]
    assert e["theme"] == "first-day" and e["variant"] == "girl_hijab" and e["lang"] == "ar"
    assert e["line"] == "magic" and e["child_name"] == "ليان"
    assert (e["title_name"], e["title_rest"]) == ("ليان", "في أوّل يوم بالروضة")
    assert e["dedication"] == "إلى ليان… نحبّكِ كثيرًا"
    assert e["parents"] == {"lesson": "درس", "questions": ["سؤال ١", "سؤال ٢"]}
    beats = [p["beat"] for p in e["pages"]]
    assert beats[0] == 0 and beats == sorted(beats) and e["cover"] == e["pages"][0]["image"]
    assert e["pages"][0]["text"] is None and e["pages"][1]["text"] == "صفحة 1 من حكاية ليان"
    assert e["pages"][1]["numbers"] == [2] and e["page_count"] >= len(beats)
    assert {p["aspect"] for p in e["pages"]} <= {"1:1", "3:2", "16:9"}
    assert e["pages"][1]["image"].startswith(f"/api/examples/{shown.id}/pages/1/m.jpg?v=")
    assert e["character"].startswith(f"/api/examples/{shown.id}/character/m.jpg?v=")
    for leaked in (str(shown.child_id), "children/", "raw/"):
        assert leaked not in r.text  # no child id, no storage keys
    assert (await client.get("/api/examples?theme=graduation")).json() == []
    assert (await client.get("/api/examples?lang=en")).json() == []
    for hidden in (real, mixed):
        assert (await client.get(f"/api/examples/{hidden.id}/pages/1/m.jpg")).status_code == 404


async def test_publishing_is_for_approved_sample_books_only(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await make_admin(client, adb)
    real = await _book(adb, storage, name="مريم", sample=False)
    mixed = await _book(adb, storage, name="هدى", child_sample=False)
    review = await _book(adb, storage, name="يوسف", status=BookStatus.in_review)
    ok = await _book(adb, storage)
    yes = {"synthetic_child": True}
    for book in (real, mixed):
        r = await client.post(f"/api/admin/books/{book.id}/example", json=yes)
        assert r.status_code == 403 and r.json()["error"]["code"] == "example_not_sample"
    r = await client.post(f"/api/admin/books/{review.id}/example", json=yes)
    assert r.status_code == 409 and r.json()["error"]["code"] == "example_not_approved"
    r = await client.post(f"/api/admin/books/{ok.id}/example", json={})  # the admin must confirm
    assert r.status_code == 422
    r = await client.post(f"/api/admin/books/{uuid.uuid4()}/example", json=yes)
    assert r.status_code == 404
    for book in (real, mixed, review, ok):
        await adb.refresh(book)
        assert not (book.generation or {}).get("public_example")
    assert (await client.get("/api/examples")).json() == []


async def test_publish_needs_the_review_permission(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await make_admin(client, adb)  # the owner the seed helper needs
    book = await _book(adb, storage)
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="support@example.com", roles=("support",))  # signed in with 2FA
    r = await client.post(f"/api/admin/books/{book.id}/example", json={"synthetic_child": True})
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    await client.post("/api/auth/logout")
    await register(client, email="parent@example.com")
    r = await client.post(f"/api/admin/books/{book.id}/example", json={"synthetic_child": True})
    assert r.status_code == 403
    await adb.refresh(book)
    assert not (book.generation or {}).get("public_example")


async def test_publish_makes_watermarked_copies_with_no_pii_headers(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await make_admin(client, adb)
    book = await _book(adb, storage, name="يوسف", gender=Gender.m)
    r = await client.post(f"/api/admin/books/{book.id}/example", json={"synthetic_child": True})
    assert r.status_code == 200 and r.json()["public"] is True and r.json()["pages"] > 10
    audit = (
        await adb.execute(select(AuditLog).where(AuditLog.action == "admin.example_published"))
    ).scalar_one()
    assert audit.entity_id == str(book.id) and audit.data["synthetic"] is True
    prefix = f"children/{book.child_id}/books/{book.id}/example/"
    made = storage.client.list_objects_v2(Bucket=storage.bucket, Prefix=prefix)["KeyCount"]
    assert made == 2 * r.json()["pages"]  # two sizes per page, under the sample child's prefix
    detail = (await client.get(f"/api/admin/books/{book.id}")).json()
    assert detail["generation"]["public_example"] is True
    await client.post("/api/auth/logout")

    example = (await client.get("/api/examples")).json()[0]
    assert example["variant"] == "boy"
    for page, side in ((example["pages"][1], 1280), (example["pages"][0], 1280)):
        r = await client.get(page["image"])
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        assert r.headers["cache-control"] == "public, max-age=86400"
        assert "set-cookie" not in r.headers and "content-disposition" not in r.headers
        for value in r.headers.values():  # nothing about the child or where the files live
            for leaked in ("يوسف", str(book.child_id), "children/", ".png"):
                assert leaked not in value
        img = Image.open(io.BytesIO(r.content))
        assert img.format == "JPEG" and max(img.size) <= side and not img.getexif()
        small = Image.open(io.BytesIO((await client.get(page["thumb"])).content))
        assert max(small.size) <= 560
    # the mark is really there: the copy differs from the plain art, most of all in the corner tag
    art = Image.open(io.BytesIO(_art(SHAPES["1:1"], 0))).convert("RGB").resize(img.size)
    diff = ImageChops.difference(img.convert("RGB"), art).convert("L")
    w, h = img.size
    corner = diff.crop((0, round(h * 0.88), round(w * 0.2), h))
    assert corner.getextrema()[1] > 80 and ImageStat.Stat(diff).mean[0] > 1.5  # the tag, the diagonal marks
    sheet = await client.get(example["character"])
    assert sheet.status_code == 200 and sheet.headers["cache-control"] == "public, max-age=86400"


async def test_unpublish_and_review_hide_an_example(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await make_admin(client, adb)
    book = await _book(adb, storage)
    assert (
        await client.post(f"/api/admin/books/{book.id}/example", json={"synthetic_child": True})
    ).status_code == 200
    url = (await client.get("/api/examples")).json()[0]["pages"][2]["image"]
    assert (await client.get(url)).status_code == 200
    book.status = BookStatus.in_review  # e.g. a redraw after publishing: hidden until approved again
    await adb.commit()
    assert (await client.get("/api/examples")).json() == []
    assert (await client.get(url)).status_code == 404
    book.status = BookStatus.approved
    await adb.commit()
    assert len((await client.get("/api/examples")).json()) == 1
    r = await client.delete(f"/api/admin/books/{book.id}/example")
    assert r.status_code == 200 and r.json()["public"] is False
    assert (await client.get("/api/examples")).json() == []
    assert (await client.get(url)).status_code == 404
    assert (await client.get(f"/api/examples/{book.id}/pages/99/m.jpg")).status_code == 404
    actions = (await adb.execute(select(AuditLog.action).where(AuditLog.entity_id == str(book.id)))).scalars()
    assert set(actions) >= {"admin.example_published", "admin.example_unpublished"}


async def test_a_redrawn_page_gets_a_new_copy_and_url(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await make_admin(client, adb)
    book = await _book(adb, storage, public=True)
    before = (await client.get("/api/examples")).json()[0]["pages"][1]["image"]
    first = (await client.get(before)).content
    page = (
        await adb.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 1))
    ).scalar_one()
    page.image_key = f"children/{book.child_id}/books/{book.id}/raw/01-redrawn.png"
    storage.put(page.image_key, _art((1024, 1024), 33), "image/png")
    page.updated_at = datetime.now(UTC) + timedelta(seconds=5)
    await adb.commit()
    after = (await client.get("/api/examples")).json()[0]["pages"][1]["image"]
    assert after != before and after.split("?")[0] == before.split("?")[0]
    assert (await client.get(after)).content != first
