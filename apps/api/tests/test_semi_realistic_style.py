"""«شبه حقيقي» / Semi-realistic (owner's decisions of 2026-10-09): a fourth art style for the Magic story
books and the four activity lines, and the activity books' style step (the parent's choice is
`GET /workbooks/needs?style=`, the drawing's `POST /characters {style, sku}` and the cart line's `style`).
Not in «قمرة كلاسيك»: Classic needs pre-drawn templates per style. Migration `a58eeffa5362` brings the
retired row back."""

import importlib.util
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from alembic import command
from api_helpers import register
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_core.db.models import Character, CharacterStatus, Child, Gender
from qamra_core.migrations import MIGRATIONS_DIR, alembic_config

SEMI = "semi-realistic"
STYLES = ["3d", "watercolor", "cartoon", SEMI]  # the site's order: a parent who is not asked still gets 3D
ACTIVITY_SKUS = ("wb-kg2-v1-color-spiral", "journey-s1-spiral", "family-wireo", "islamic-v1-softcover")
REVISION, PREVIOUS = "a58eeffa5362", "6a87cac7a912"


@pytest.fixture(autouse=True)
async def _data(adb: AsyncSession) -> None:
    await upsert_themes(adb)
    await seed_store(adb)


async def _child(
    adb: AsyncSession, guardian: uuid.UUID, styles: tuple[str, ...]
) -> tuple[Child, list[Character]]:
    """A girl with approved characters in `styles`, oldest first."""
    child = Child(
        guardian_user_id=guardian, first_name="تالا", gender=Gender.f, birth_year=date.today().year - 5
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


async def _needs(client: AsyncClient, sku: str, **params: str) -> dict[str, Any]:
    r = await client.get("/api/shop/workbooks/needs", params={"sku": sku, **params})
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def _error(r: Any, status: int, code: str) -> None:
    assert r.status_code == status, r.text
    error = r.json()["error"]
    assert error["code"] == code and error["message"]["ar"] and error["message"]["en"]


async def test_the_catalog_sells_semi_realistic_in_magic_and_the_activity_books(client: AsyncClient) -> None:
    styles = {s["slug"]: s for s in (await client.get("/api/store/catalog")).json()["styles"]}
    semi = styles[SEMI]
    assert (semi["name_ar"], semi["name_en"]) == ("شبه حقيقي", "Semi-realistic")
    assert semi["lines"] == ["magic", "workbook", "journey", "family", "islamic"]
    assert "classic" not in semi["lines"]  # Classic draws from templates, and none exist in this style
    assert [s for s in styles if s != "coloring"] == STYLES


@pytest.mark.parametrize("sku", ACTIVITY_SKUS)
async def test_every_activity_book_offers_every_style(client: AsyncClient, sku: str) -> None:
    out = await _needs(client, sku)
    assert out["character"] == {"reuse_id": None, "draw_style": "3d", "styles": STYLES}
    chosen = await _needs(client, sku, style=SEMI)
    assert chosen["character"] == {"reuse_id": None, "draw_style": SEMI, "styles": STYLES}


async def test_the_chosen_style_decides_the_drawing_and_the_reuse(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = uuid.UUID((await register(client, email="tala.mom@example.com"))["id"])
    child, [watercolor, semi] = await _child(adb, me, ("watercolor", SEMI))
    sku = "islamic-v1-softcover"
    # no choice: the newest approved character the book accepts (the who card shows it)
    assert (await _needs(client, sku, child_id=str(child.id)))["character"]["reuse_id"] == str(semi.id)
    # a choice: only a character already in that style is reused, else one is drawn in it
    picked = await _needs(client, sku, child_id=str(child.id), style="watercolor")
    assert picked["character"]["reuse_id"] == str(watercolor.id)
    assert picked["character"]["draw_style"] == "watercolor"
    other = await _needs(client, sku, child_id=str(child.id), style="cartoon")
    assert other["character"] == {"reuse_id": None, "draw_style": "cartoon", "styles": STYLES}


async def test_a_style_the_book_does_not_take_is_refused(client: AsyncClient) -> None:
    for style in ("coloring", "crayon", "nope"):
        r = await client.get("/api/shop/workbooks/needs", params={"sku": ACTIVITY_SKUS[0], "style": style})
        _error(r, 422, "invalid_style")


async def test_a_semi_realistic_character_is_drawn_for_an_activity_book_never_for_classic(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = uuid.UUID((await register(client, email="tala.dad@example.com"))["id"])
    child, _ = await _child(adb, me, ())
    url = f"/api/create/children/{child.id}/characters"
    # the style passes the line check, then the drawing needs the photo like any other
    for body in ({"style": SEMI, "sku": "family-wireo"}, {"style": SEMI, "line": "magic"}):
        _error(await client.post(url, json=body), 409, "photo_required")
    _error(await client.post(url, json={"style": SEMI, "line": "classic"}), 422, "invalid_style")


async def test_the_cart_line_keeps_the_chosen_style(client: AsyncClient, adb: AsyncSession) -> None:
    me = uuid.UUID((await register(client, email="tala.aunt@example.com"))["id"])
    child, [three_d, semi] = await _child(adb, me, ("3d", SEMI))
    body = {"sku": "islamic-v1-softcover", "child_id": str(child.id)}
    r = await client.post("/api/shop/workbooks/cart", json={**body, "character_id": str(three_d.id)})
    assert r.status_code == 201, r.text
    first = r.json()["items"][-1]
    assert first["character_id"] == str(three_d.id) and first["style"] == "3d"
    r = await client.post("/api/shop/workbooks/cart", json={**body, "character_id": str(semi.id)})
    assert r.status_code == 201, r.text
    second = r.json()["items"][-1]
    assert second["character_id"] == str(semi.id) and second["style"] == SEMI


# ---- the migration ---------------------------------------------------------------------------------------


def _migration() -> ModuleType:
    [path] = (Path(MIGRATIONS_DIR) / "versions").glob(f"*_{REVISION}_*.py")
    spec = importlib.util.spec_from_file_location("semi_realistic_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _row(adb: AsyncSession) -> dict[str, Any]:
    row = (
        await adb.execute(
            text(
                "SELECT name_ar, name_en, version, lines, sort, active, likeness_min, updated_at "
                "FROM art_styles WHERE slug = :slug"
            ),
            {"slug": SEMI},
        )
    ).one()
    return dict(row._mapping)


async def test_the_migration_goes_down_and_up(adb: AsyncSession) -> None:
    """On the test's own connection (rolled back after the test): down, up, then the data step once more."""

    def run(session: Session, revision: str, up: bool) -> None:
        cfg = alembic_config("postgresql+psycopg://unused/x_test")
        cfg.attributes["connection"] = session.connection()
        (command.upgrade if up else command.downgrade)(cfg, revision)

    def again(session: Session) -> None:
        _migration().revive(session.connection(), forward=True)

    after = {
        "name_ar": "شبه حقيقي",
        "name_en": "Semi-realistic",
        "version": 2,
        "lines": ["magic", "workbook", "journey", "family", "islamic"],
        "sort": 3,
        "active": True,
        "likeness_min": 8,
    }
    assert {
        k: v for k, v in (await _row(adb)).items() if k != "updated_at"
    } == after  # the seed, from the guide
    await adb.run_sync(run, PREVIOUS, False)
    before = await _row(adb)
    assert {k: before[k] for k in ("name_ar", "version", "lines", "active", "sort")} == {
        "name_ar": "شبه واقعي",
        "version": 1,
        "lines": [],
        "active": False,
        "sort": 11,
    }
    await adb.run_sync(run, REVISION, True)
    up = await _row(adb)
    assert {k: v for k, v in up.items() if k != "updated_at"} == after
    await adb.run_sync(again)  # idempotent: a row already at version 2 is not touched
    assert await _row(adb) == up
