"""Order flows per product (docs/plans/order-flows.md, chunk 8): editing a child, what an activity book needs
from the child (`GET /api/shop/workbooks/needs`), the workbook cart line (the character and the English name
it prints), cart edits that keep the family, add-ons by cart line, privacy, and the owner's decisions of
2026-10-07 (the black-and-white workbook and the add-ons we cannot deliver are switched off)."""

import importlib.util
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from alembic import command
from api_helpers import register
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from qamra_api.errors import MESSAGES
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import expand_variants, seed_store
from qamra_api.store import workbooks
from qamra_core.db.models import AuditLog, Character, CharacterStatus, Child, Gender, OrderItem
from qamra_core.db.store import AddOn, ArtStyle, CartItem, Variant
from qamra_core.migrations import MIGRATIONS_DIR, alembic_config
from qamra_core.printing import INSERT_LABELS, item_inserts

CHECKOUT = {
    "name": "أم ضحى",
    "phone": "+970 59 765 4321",
    "zone": "west-bank",
    "city": "نابلس",
    "address": "رفيديا، قرب المدرسة",
    "accept_terms": True,
}
FAMILY = {"name": "الخطيب", "city": "نابلس", "members": [{"relation": "mother", "name": "سارة"}]}
DAWSEYEH = "wb-kg2-v1-color-spiral"
NEW_CODES = (
    "name_en_required",
    "name_en_invalid",
    "name_not_arabic",
    "name_not_traceable",
    "character_style",
)
REVISION, PREVIOUS = "18342eeba4e4", "0c695b89fde0"
BW = [f"wb-{lvl}-{p}-bw-spiral" for lvl in ("kg1", "kg2") for p in ("v1", "v2", "v3", "set")]
# the add-ons we cannot deliver (docs/plans/order-flows.md, «Add-ons: what is deactivated»)
RETIRED = (
    "gift-box",
    "wipe-sleeve",
    "crayon-kit",
    "extra-character",
    "coloring-version",
    "cover-poster",
    "sticker-sheet",
    "audio-qr",
    "parent-guide",
    "express",
    "family-characters",
)
KEPT = (
    "hardcover-upgrade",
    "dedication-page",
    "drawing-companion",
    "family-voice",
    "extra-copy",
    "digital-copy",
    "printed-answer-key",
    "printed-parent-guide",
)


@pytest.fixture(autouse=True)
async def _data(adb: AsyncSession) -> None:
    await upsert_themes(adb)
    await seed_store(adb)


async def _me(client: AsyncClient, email: str = "duha.mom@example.com") -> uuid.UUID:
    return uuid.UUID((await register(client, email=email))["id"])


async def _child(
    adb: AsyncSession,
    guardian: uuid.UUID,
    name: str = "ضحى",
    *,
    styles: tuple[str, ...] = ("watercolor",),
    approved: bool = True,
) -> tuple[Child, list[Character]]:
    """A child with characters in `styles`, oldest first (each approved a minute after the previous one)."""
    child = Child(
        guardian_user_id=guardian, first_name=name, gender=Gender.f, birth_year=date.today().year - 5
    )
    adb.add(child)
    await adb.flush()
    start = datetime.now(UTC) - timedelta(hours=1)
    characters = [
        Character(
            child_id=child.id,
            art_style=style,
            status=CharacterStatus.approved if approved else CharacterStatus.ready,
            sheet_image_key=f"children/{child.id}/characters/{i}.png",
            approved_at=start + timedelta(minutes=i) if approved else None,
        )
        for i, style in enumerate(styles)
    ]
    adb.add_all(characters)
    await adb.commit()
    return child, characters


async def _needs(client: AsyncClient, sku: str, child: Child | None = None) -> dict[str, Any]:
    params = {"sku": sku, **({"child_id": str(child.id)} if child else {})}
    r = await client.get("/api/shop/workbooks/needs", params=params)
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def _error(r: Any, status: int, code: str) -> dict[str, Any]:
    assert r.status_code == status, r.text
    error: dict[str, Any] = r.json()["error"]
    assert error["code"] == code
    assert error["message"]["ar"] and error["message"]["en"]  # friendly, in both languages
    return error


def test_every_new_error_has_a_friendly_message_in_both_languages() -> None:
    for code in NEW_CODES:
        ar, en = MESSAGES[code]
        assert ar.strip() and en.strip() and ar != en


# ---- PATCH /api/create/children/{id} ----------------------------------------------------------------------


async def test_the_guardian_fixes_the_child_and_the_character_stays(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    child, [character] = await _child(adb, me, name="ضحي")
    approved_at = character.approved_at
    r = await client.patch(
        f"/api/create/children/{child.id}",
        json={
            "name": "  ضحى  ",
            "age": 4,
            "name_latin": " Duha ",
            "interests": ["الرسم"],
            "note": "تحب القطط",
        },
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["name"] == "ضحى" and out["age"] == 4 and out["name_latin"] == "Duha"
    assert out["interests"] == ["الرسم", "تحب القطط"] and out["gender"] == "f"
    assert [c["id"] for c in out["characters"]] == [str(character.id)] and out["characters"][0]["approved"]
    await adb.refresh(character)
    assert character.approved_at == approved_at and character.art_style == "watercolor"  # not touched
    log = (await adb.execute(select(AuditLog).where(AuditLog.action == "child.updated"))).scalar_one()
    assert log.entity_id == str(child.id) and log.actor_user_id == me
    assert sorted(log.data["fields"]) == ["age", "interests", "name", "name_latin"]
    assert "ضحى" not in str(log.data) and "Duha" not in str(log.data)  # which fields, never their values

    r = await client.patch(f"/api/create/children/{child.id}", json={"gender": "m", "name_latin": ""})
    assert r.status_code == 200 and r.json()["name_latin"] is None and r.json()["hijab"] is False
    listed = (await client.get("/api/create/children")).json()
    assert listed[0]["name_latin"] is None and listed[0]["interests"] == ["الرسم", "تحب القطط"]


async def test_a_child_edit_is_checked(client: AsyncClient, adb: AsyncSession) -> None:
    me = await _me(client)
    child, _ = await _child(adb, me)
    url = f"/api/create/children/{child.id}"
    for bad in (
        {"age": 11},
        {"age": 1},
        {"name": "   "},
        {"name": "x" * 41},
        {"gender": "x"},
        {"photo": "x"},
    ):
        assert (await client.patch(url, json=bad)).status_code == 422, bad
    _error(await client.patch(url, json={"age": 1}), 422, "invalid_input")
    for latin in ("ضحى", "Duha2", "Du@ha", "-Duha", "D" * 41):
        error = _error(await client.patch(url, json={"name_latin": latin}), 422, "name_en_invalid")
        assert error["details"]["fields"] == ["name_latin"]
    for latin in ("Duha", "Abd Allah", "O'Neil", "Nour-Al Huda"):
        assert (await client.patch(url, json={"name_latin": latin})).json()["name_latin"] == latin
    assert (await adb.execute(select(AuditLog).where(AuditLog.action == "child.updated"))).scalars().all()


async def test_only_the_guardian_edits_a_child(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    me = await _me(client)
    child, _ = await _child(adb, me)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers={"X-Qamra-Client": "test"}
    ) as stranger:
        assert (await stranger.patch(f"/api/create/children/{child.id}", json={"age": 6})).status_code == 401
        await register(stranger, email="other.mom@example.com")
        r = await stranger.patch(f"/api/create/children/{child.id}", json={"name": "سلمى"})
        _error(r, 404, "not_found")
    await adb.refresh(child)
    assert child.first_name == "ضحى"


async def test_a_fixed_name_reaches_the_activity_lines_in_the_cart(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    child, _ = await _child(adb, me, name="ضحي")
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": DAWSEYEH, "child_id": str(child.id), "name_en": "Doha"}
    )
    assert r.status_code == 201, r.text
    r = await client.patch(f"/api/create/children/{child.id}", json={"name": "ضحى", "name_latin": "Duha"})
    assert r.status_code == 200
    line = (await client.get("/api/store/cart")).json()["items"][0]
    assert line["child_name"] == "ضحى" and line["child_name_en"] == "Duha"


# ---- GET /api/shop/workbooks/needs ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sku", "line", "name_en", "family", "traces", "ages"),
    [
        (DAWSEYEH, "workbook", True, False, True, [5, 6]),
        ("wb-kg1-set-color-digital", "workbook", True, False, True, [4, 5]),
        ("journey-s1-spiral", "journey", False, False, True, [3, 4]),
        ("journey-s2-digital", "journey", True, False, True, [4, 5]),
        ("journey-s3-spiral", "journey", True, False, True, [5, 6]),
        ("journey-set-spiral", "journey", True, False, True, [3, 6]),
        ("family-wireo", "family", False, True, False, [3, 7]),
        ("islamic-v1-softcover", "islamic", False, False, False, [4, 6]),
        ("islamic-v3-digital", "islamic", False, False, False, [6, 8]),
        ("islamic-r-softcover", "islamic", False, False, False, [4, 8]),
        ("islamic-set-softcover", "islamic", False, False, False, [4, 8]),
    ],
)
async def test_what_each_activity_book_asks(
    client: AsyncClient, sku: str, line: str, name_en: bool, family: bool, traces: bool, ages: list[int]
) -> None:
    out = await _needs(client, sku)  # without a child: the product's facts, signed in or not
    assert out["line"] == line and out["sku"] == sku and out["child"] is None
    assert out["asks"] == {"name_en": name_en, "family": family}
    assert out["traces_name"] is traces and out["ages"] == ages
    # no style question: a new character is drawn in 3D, and any approved 3D/watercolor/cartoon one is reused
    assert out["character"] == {
        "reuse_id": None,
        "draw_style": "3d",
        "styles": ["3d", "watercolor", "cartoon"],
    }


async def test_needs_refuses_what_is_not_an_activity_book_on_sale(client: AsyncClient) -> None:
    for sku in ("classic-soft-21", "nope", "wb-kg2-v1-bw-spiral", "wb-kg1-set-bw-spiral"):
        _error(await client.get("/api/shop/workbooks/needs", params={"sku": sku}), 404, "unknown_product")
    assert (await client.get("/api/shop/workbooks/needs")).status_code == 422


async def test_needs_reuses_the_newest_character_the_book_accepts(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    child, [old, newer, coloring] = await _child(adb, me, styles=("watercolor", "3d", "coloring"))
    out = await _needs(client, "islamic-v1-softcover", child)
    assert out["character"]["reuse_id"] == str(newer.id)  # the newest, never the (newer still) coloring one
    assert out["child"] == {
        "id": str(child.id),
        "name": "ضحى",
        "name_traceable": True,
        "name_problem": None,
        "name_latin": None,
    }
    only_coloring, _ = await _child(adb, me, name="لين", styles=("coloring",))
    assert (await _needs(client, DAWSEYEH, only_coloring))["character"]["reuse_id"] is None
    drafting, _ = await _child(adb, me, name="نور", approved=False)
    assert (await _needs(client, "journey-s1-spiral", drafting))["character"]["reuse_id"] is None
    assert old.id != newer.id and coloring.art_style == "coloring"


async def test_needs_says_whether_the_name_can_be_traced(client: AsyncClient, adb: AsyncSession) -> None:
    me = await _me(client)
    adam, _ = await _child(adb, me, name="Adam")
    out = await _needs(client, DAWSEYEH, adam)
    assert out["child"]["name_traceable"] is False and out["child"]["name_problem"] == "not_arabic"
    assert (await _needs(client, "islamic-v1-softcover", adam))["child"][
        "name_traceable"
    ] is True  # not traced
    rua, _ = await _child(adb, me, name="رؤى")
    engine = workbooks.tracing_engine()  # chunk 9 teaches the tracing pages ؤ and ئ
    out = await _needs(client, "journey-s1-spiral", rua)
    assert out["child"]["name_traceable"] is engine
    assert out["child"]["name_problem"] == (None if engine else "not_traceable")
    vivi, _ = await _child(adb, me, name="ڤيڤي")  # an Arabic-script letter the hand doesn't have
    out = await _needs(client, "journey-s2-spiral", vivi)
    assert out["child"]["name_traceable"] is False and out["child"]["name_problem"] == "not_traceable"
    voweled, _ = await _child(adb, me, name="نُور الهُدى")
    assert (await _needs(client, DAWSEYEH, voweled))["child"]["name_traceable"] is True


async def test_needs_shows_only_my_children(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    me = await _me(client)
    child, _ = await _child(adb, me)
    await client.patch(f"/api/create/children/{child.id}", json={"name_latin": "Duha"})
    assert (await _needs(client, DAWSEYEH, child))["child"]["name_latin"] == "Duha"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers={"X-Qamra-Client": "test"}
    ) as stranger:
        params = {"sku": DAWSEYEH, "child_id": str(child.id)}
        _error(await stranger.get("/api/shop/workbooks/needs", params=params), 401, "not_authenticated")
        await register(stranger, email="other.mom@example.com")
        _error(await stranger.get("/api/shop/workbooks/needs", params=params), 404, "not_found")


# ---- POST /api/shop/workbooks/cart -------------------------------------------------------------------------


async def test_the_workbook_line_carries_the_character_and_the_english_name(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    child, [watercolor, cartoon] = await _child(adb, me, styles=("watercolor", "cartoon"))
    body = {"sku": DAWSEYEH, "child_id": str(child.id)}
    error = _error(await client.post("/api/shop/workbooks/cart", json=body), 422, "name_en_required")
    assert error["details"]["fields"] == ["name_en"]
    _error(
        await client.post("/api/shop/workbooks/cart", json={**body, "name_en": "دعاء"}),
        422,
        "name_en_invalid",
    )
    assert (await client.get("/api/store/cart")).json()["count"] == 0

    r = await client.post(
        "/api/shop/workbooks/cart", json={**body, "name_en": "Duha", "character_id": str(watercolor.id)}
    )
    assert r.status_code == 201, r.text
    line = r.json()["items"][0]
    assert line["child_name_en"] == "Duha" and line["character_id"] == str(watercolor.id)
    assert line["missing"] == [] and not line["needs_details"] and line["family"] is None
    await adb.refresh(child)
    assert child.name_latin == "Duha"  # saved for the next book

    r = await client.post(
        "/api/shop/workbooks/cart", json=body
    )  # the saved English name, the newest character
    assert r.status_code == 201, r.text
    second = r.json()["items"][1]
    assert second["child_name_en"] == "Duha" and second["character_id"] == str(cartoon.id)
    r = await client.post(
        "/api/shop/workbooks/cart", json={**body, "sku": "journey-s1-spiral", "name_en": "Doha"}
    )
    stage1 = r.json()["items"][2]
    assert stage1["child_name_en"] is None  # stage 1 prints no English name; the child keeps the new spelling
    await adb.refresh(child)
    assert child.name_latin == "Doha"

    assert (await client.post("/api/store/checkout", json=CHECKOUT)).status_code == 201
    items = (await adb.execute(select(OrderItem).where(OrderItem.sku == DAWSEYEH))).scalars().all()
    assert {i.personalization["name_en"] for i in items} == {"Duha"}
    assert {i.personalization["character_id"] for i in items} == {str(watercolor.id), str(cartoon.id)}


async def test_the_character_must_be_the_childs_approved_one_in_an_accepted_style(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    child, [coloring] = await _child(adb, me, styles=("coloring",))
    _, [unapproved] = await _child(adb, me, name="لين", approved=False)
    body = {"sku": "islamic-v1-softcover", "child_id": str(child.id)}
    _error(await client.post("/api/shop/workbooks/cart", json=body), 409, "character_not_approved")
    r = await client.post("/api/shop/workbooks/cart", json={**body, "character_id": str(coloring.id)})
    _error(r, 409, "character_style")
    r = await client.post("/api/shop/workbooks/cart", json={**body, "character_id": str(unapproved.id)})
    _error(r, 404, "not_found")  # another child's character, even the parent's own
    own_unapproved = Character(child_id=child.id, art_style="3d", status=CharacterStatus.ready)
    adb.add(own_unapproved)
    await adb.commit()
    r = await client.post("/api/shop/workbooks/cart", json={**body, "character_id": str(own_unapproved.id)})
    _error(r, 409, "character_not_approved")
    r = await client.post("/api/shop/workbooks/cart", json={**body, "character_id": str(uuid.uuid4())})
    _error(r, 404, "not_found")


async def test_a_name_the_tracing_pages_cannot_write_is_refused_where_it_is_traced(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    adam, _ = await _child(adb, me, name="Adam")
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "journey-s1-spiral", "child_id": str(adam.id)}
    )
    error = _error(r, 422, "name_not_arabic")
    assert error["details"]["fields"] == ["name"]
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "islamic-v1-softcover", "child_id": str(adam.id)}
    )
    assert r.status_code == 201, r.text  # the Islamic books print the name, they don't trace it
    vivi, _ = await _child(adb, me, name="ڤيڤي")
    r = await client.post("/api/shop/workbooks/cart", json={"sku": DAWSEYEH, "child_id": str(vivi.id)})
    _error(r, 422, "name_not_traceable")
    rua, _ = await _child(adb, me, name="رؤى")
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "journey-s1-spiral", "child_id": str(rua.id)}
    )
    if workbooks.tracing_engine():
        assert r.status_code == 201, r.text  # chunk 9: ؤ and ئ are traced
    else:
        _error(r, 422, "name_not_traceable")


async def test_the_islamic_line_fills_like_an_activity_book(client: AsyncClient, adb: AsyncSession) -> None:
    line = (await client.post("/api/store/cart/items", json={"sku": "islamic-v2-softcover"})).json()["items"][
        0
    ]
    me = await _me(client)
    child, [character] = await _child(adb, me, styles=("3d",))
    r = await client.post(
        "/api/shop/workbooks/cart",
        json={"sku": "islamic-v2-softcover", "child_id": str(child.id), "item_id": line["id"]},
    )
    assert r.status_code == 201, r.text
    filled = r.json()["items"][0]
    assert filled["id"] == line["id"] and filled["line"] == "islamic" and not filled["needs_details"]
    assert filled["character_id"] == str(character.id) and filled["child_name_en"] is None


async def test_the_family_given_on_the_page_survives_the_flow_and_cart_edits(
    client: AsyncClient, adb: AsyncSession
) -> None:
    r = await client.post("/api/store/cart/items", json={"sku": "family-wireo", "family": FAMILY})
    line = r.json()["items"][0]
    assert line["family"]["name"] == "الخطيب" and line["needs_details"]
    me = await _me(client)
    child, [character] = await _child(adb, me)
    r = await client.post(
        "/api/shop/workbooks/cart",
        json={"sku": "family-wireo", "child_id": str(child.id), "item_id": line["id"]},
    )
    assert r.status_code == 201, r.text
    filled = r.json()["items"][0]
    assert filled["family"]["city"] == "نابلس" and filled["family"]["members"][0]["role"] == "ماما"

    r = await client.patch(
        f"/api/store/cart/items/{line['id']}", json={"qty": 2, "personalization": {"child_name": "ضحى"}}
    )
    assert r.status_code == 200, r.text
    row = await adb.get(CartItem, uuid.UUID(line["id"]))
    assert row is not None
    await adb.refresh(row)
    assert row.qty == 2 and row.personalization["family"]["name"] == "الخطيب"
    assert row.personalization["character_id"] == str(character.id)

    # the family step sends a new family for the same line: it replaces the one from the page
    new = {"name": "", "city": "رام الله", "members": [{"relation": "father", "name": "محمود"}]}
    r = await client.post(
        "/api/shop/workbooks/cart",
        json={"sku": "family-wireo", "child_id": str(child.id), "item_id": line["id"], "family": new},
    )
    assert r.json()["items"][0]["family"]["city"] == "رام الله"


async def test_a_line_filled_before_the_rules_waits_for_the_english_name(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    child, [character] = await _child(adb, me)
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": DAWSEYEH, "child_id": str(child.id), "name_en": "Duha"}
    )
    line = r.json()["items"][0]
    row = await adb.get(CartItem, uuid.UUID(line["id"]))
    assert row is not None
    row.personalization = {k: v for k, v in row.personalization.items() if k != "name_en"}  # an older line
    await adb.commit()
    shown = (await client.get("/api/store/cart")).json()["items"][0]
    assert shown["needs_details"] and shown["missing"] == ["name_en"]
    error = _error(await client.post("/api/store/checkout", json=CHECKOUT), 409, "details_missing")
    assert error["details"]["items"][0]["missing"] == ["name_en"]
    r = await client.post(
        "/api/shop/workbooks/cart",
        json={
            "sku": DAWSEYEH,
            "child_id": str(child.id),
            "item_id": line["id"],
            "character_id": str(character.id),
        },
    )
    assert r.json()["items"][0]["missing"] == [] and r.json()["items"][0]["child_name_en"] == "Duha"
    assert (await client.post("/api/store/checkout", json=CHECKOUT)).status_code == 201


# ---- POST /api/create/children/{id}/characters: the style × line check ------------------------------------


async def test_a_character_for_a_book_is_drawn_in_a_style_its_line_accepts(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    child, _ = await _child(adb, me, styles=())
    url = f"/api/create/children/{child.id}/characters"
    _error(
        await client.post(url, json={"style": "coloring", "sku": "islamic-v1-softcover"}),
        422,
        "invalid_style",
    )
    _error(await client.post(url, json={"style": "coloring", "line": "journey"}), 422, "invalid_style")
    _error(await client.post(url, json={"style": "3d", "sku": "nope"}), 404, "unknown_product")
    # an accepted style passes the check (and then needs the photo, like any drawing)
    _error(await client.post(url, json={"style": "3d", "sku": "islamic-v1-softcover"}), 409, "photo_required")
    _error(await client.post(url, json={"style": "watercolor", "line": "classic"}), 409, "photo_required")


# ---- add-ons by cart line, and the ones switched off -------------------------------------------------------


async def _offers(client: AsyncClient, sku: str) -> dict[str, dict[str, Any]]:
    item = (await client.post("/api/store/cart/items", json={"sku": sku})).json()["items"][-1]
    r = await client.get(f"/api/store/cart/items/{item['id']}/addons")
    assert r.status_code == 200, r.text
    return {a["slug"]: a for a in r.json()["addons"]}


async def test_activity_books_get_their_add_ons_by_cart_line(client: AsyncClient, adb: AsyncSession) -> None:
    islamic = await _offers(client, "islamic-v1-softcover")
    assert set(islamic) == {"printed-parent-guide"}  # the sticker sheet and the gift box are switched off
    assert islamic["printed-parent-guide"]["name_ar"] == "إجابات الأنشطة مطبوعةً"
    assert "printed-parent-guide" not in await _offers(client, "islamic-v1-digital")  # printed volumes only
    assert set(await _offers(client, "journey-s2-spiral")) == {"printed-answer-key"}
    assert set(await _offers(client, "journey-s2-digital")) == set()
    assert set(await _offers(client, "family-wireo")) == set()

    await adb.execute(update(AddOn).where(AddOn.slug == "wipe-sleeve").values(active=True))  # the admin
    await adb.commit()
    assert "wipe-sleeve" in await _offers(client, "journey-s2-spiral")
    assert "wipe-sleeve" not in await _offers(client, "journey-s2-digital")  # spiral only


async def test_the_store_hides_the_add_ons_we_cannot_deliver(client: AsyncClient, adb: AsyncSession) -> None:
    catalog = (await client.get("/api/store/catalog")).json()
    assert not set(RETIRED) & {a["slug"] for a in catalog["addons"]}
    assert {a["slug"] for a in catalog["addons"]} == set(KEPT)
    rows = (await adb.execute(select(AddOn).where(AddOn.slug.in_(RETIRED)))).scalars().all()
    assert len(rows) == len(RETIRED) and not any(a.active for a in rows)  # kept, switched off
    r = await client.post(
        "/api/store/cart/items", json={"sku": "classic-soft-21", "addons": [{"slug": "gift-box"}]}
    )
    _error(r, 422, "invalid_addons")

    # a line that took the gift box before it was switched off: the cart and checkout drop it, never refuse
    line = (await client.post("/api/store/cart/items", json={"sku": "journey-s1-spiral"})).json()["items"][0]
    row = await adb.get(CartItem, uuid.UUID(line["id"]))
    assert row is not None
    row.addons = [{"slug": "gift-box", "qty": 1}, {"slug": "printed-answer-key", "qty": 1}]
    await adb.commit()
    shown = (await client.get("/api/store/cart")).json()["items"][0]
    assert [a["slug"] for a in shown["addons"]] == ["printed-answer-key"]
    r = await client.patch(f"/api/store/cart/items/{line['id']}", json={"qty": 2})
    assert r.status_code == 200, r.text
    me = await _me(client)
    child, _ = await _child(adb, me)
    await client.post(
        "/api/shop/workbooks/cart",
        json={"sku": "journey-s1-spiral", "child_id": str(child.id), "item_id": line["id"]},
    )
    assert (await client.post("/api/store/checkout", json=CHECKOUT)).status_code == 201
    item = (await adb.execute(select(OrderItem))).scalar_one()
    assert [a["slug"] for a in item.addons] == ["printed-answer-key"]


def test_the_answer_key_goes_to_the_printer_only_when_bought() -> None:
    files = {"answer-key": "k/answer-key.pdf", "stickers": "k/stickers.pdf"}
    assert item_inserts(files, []) == {"stickers": "k/stickers.pdf"}  # a family book's inserts always go
    assert item_inserts(files, [{"slug": "printed-answer-key", "qty": 1}]) == files
    assert item_inserts(files, [{"slug": "printed-parent-guide", "qty": 1}]) == files
    assert INSERT_LABELS["answer-key"] == "مفتاح الإجابات (كتيّب منفصل)"


# ---- privacy -----------------------------------------------------------------------------------------------


async def test_deleting_the_child_clears_the_family_and_english_name_from_orders(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await _me(client)
    child, _ = await _child(adb, me)
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "family-wireo", "child_id": str(child.id), "family": FAMILY}
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        "/api/shop/workbooks/cart",
        json={"sku": "journey-s2-spiral", "child_id": str(child.id), "name_en": "Duha"},
    )
    assert r.status_code == 201, r.text
    placed = await client.post("/api/store/checkout", json=CHECKOUT)
    assert placed.status_code == 201, placed.text
    track = f"/api/store/orders/{placed.json()['code']}"
    tracked = {
        i["sku"]: i for i in (await client.get(track, params={"phone": CHECKOUT["phone"]})).json()["items"]
    }
    family, journey = tracked["family-wireo"], tracked["journey-s2-spiral"]  # what the cart showed, frozen
    assert family["product"] == "family-adventures" and family["line"] == "family"
    assert family["family"]["name"] == "الخطيب" and family["child_name"] == "ضحى"
    assert journey["options"] == {"stage": "2", "format": "spiral"} and journey["child_name_en"] == "Duha"
    await client.post(
        "/api/shop/workbooks/cart", json={"sku": "islamic-v1-digital", "child_id": str(child.id)}
    )

    assert (await client.delete(f"/api/create/children/{child.id}")).status_code == 204
    adb.expire_all()
    items = (await adb.execute(select(OrderItem).order_by(OrderItem.sku))).scalars().all()
    assert [i.sku for i in items] == ["family-wireo", "journey-s2-spiral"]
    for item in items:
        assert item.child_id is None
        for key in ("child_name", "family", "name_en", "character_id", "gender", "age"):
            assert key not in item.personalization, key
        assert "الخطيب" not in str(item.personalization) and "Duha" not in str(item.personalization)
        assert item.unit_price > 0 and item.quantity == 1 and item.title["name_ar"]  # the shop's record stays
    assert (await client.get("/api/store/cart")).json()["items"] == []
    for item in (await client.get(track, params={"phone": CHECKOUT["phone"]})).json()["items"]:
        assert item["family"] is None and item["child_name_en"] is None and item["child_name"] is None


# ---- the owner's decisions in the catalog and the migration ------------------------------------------------


async def test_the_black_and_white_workbook_is_hidden_not_deleted(
    client: AsyncClient, adb: AsyncSession
) -> None:
    rows = (await adb.execute(select(Variant).where(Variant.sku.in_(BW)))).scalars().all()
    assert len(rows) == 8 and not any(v.active for v in rows)
    products = {p["slug"]: p for p in (await client.get("/api/store/catalog")).json()["products"]}
    sold = {v["sku"] for v in products["foundation-workbook"]["variants"]}
    assert not sold & set(BW) and {"wb-kg1-v1-color-spiral", "wb-kg2-set-color-digital"} <= sold
    _error(await client.post("/api/store/cart/items", json={"sku": BW[0]}), 404, "unknown_product")


def test_a_matrix_row_can_be_switched_off_for_every_level() -> None:
    rows = [
        {"volume": "1", "interior": "color", "format": "spiral", "price": {"ILS": 1}},
        {"volume": "1", "interior": "bw", "format": "spiral", "active": False, "price": {"ILS": 1}},
    ]
    matrix = {"levels": ["kg1", "kg2"], "rendered": {"kg1": ["1"], "kg2": ["1"]}, "rows": rows}
    got = {v["sku"]: v["active"] for v in expand_variants({"variant_matrix": matrix})}
    assert got == {
        "wb-kg1-v1-color-spiral": True,
        "wb-kg1-v1-bw-spiral": False,
        "wb-kg2-v1-color-spiral": True,
        "wb-kg2-v1-bw-spiral": False,
    }


async def test_islamic_is_drawn_in_the_three_styles(adb: AsyncSession) -> None:
    styles = {s.slug: s for s in (await adb.execute(select(ArtStyle))).scalars()}
    for slug in ("3d", "watercolor", "cartoon"):
        assert "islamic" in styles[slug].lines
    assert "islamic" not in styles["coloring"].lines


def _migration() -> ModuleType:
    [path] = (Path(MIGRATIONS_DIR) / "versions").glob(f"*_{REVISION}_*.py")
    spec = importlib.util.spec_from_file_location("order_flows_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _state(adb: AsyncSession) -> dict[str, Any]:
    lines = dict((await adb.execute(text("SELECT slug, lines FROM art_styles"))).all())
    variants = dict((await adb.execute(text("SELECT sku, active FROM product_variants"))).all())
    addons = dict((await adb.execute(text("SELECT slug, active FROM addons"))).all())
    guide = (
        await adb.execute(text("SELECT name_ar FROM addons WHERE slug = 'printed-parent-guide'"))
    ).scalar_one()
    column = (
        await adb.execute(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'children' AND column_name = 'name_latin'"
            )
        )
    ).scalar_one()
    return {
        "islamic": sorted(s for s, ls in lines.items() if "islamic" in ls),
        "islamic_twice": any(ls.count("islamic") > 1 for ls in lines.values()),
        "bw_on": sorted(s for s in BW if variants[s]),
        "retired_on": sorted(s for s in RETIRED if addons[s]),
        "kept_on": all(addons[s] for s in KEPT) and not addons["editable-files"],
        "guide": guide,
        "colour_on": variants["wb-kg2-v1-color-spiral"],
        "column": bool(column),
    }


async def test_the_migration_goes_down_and_up(adb: AsyncSession) -> None:
    """On the test's own connection (rolled back after the test): down, then up again, then the data steps
    once more (idempotent)."""

    def run(session: Session, revision: str, up: bool) -> None:
        cfg = alembic_config("postgresql+psycopg://unused/x_test")
        cfg.attributes["connection"] = session.connection()
        (command.upgrade if up else command.downgrade)(cfg, revision)

    after = {
        "islamic": ["3d", "cartoon", "watercolor"],
        "islamic_twice": False,
        "bw_on": [],
        "retired_on": [],
        "kept_on": True,
        "guide": "إجابات الأنشطة مطبوعةً",
        "colour_on": True,
        "column": True,
    }
    assert await _state(adb) == after
    await adb.run_sync(run, PREVIOUS, False)
    before = await _state(adb)
    assert before == {
        **after,
        "islamic": [],
        "bw_on": sorted(BW),
        "retired_on": sorted(RETIRED),
        "guide": "دليل الأهل مطبوعًا",
        "column": False,
    }
    await adb.run_sync(run, REVISION, True)
    assert await _state(adb) == after
    assert (await adb.execute(text("SELECT version_num FROM alembic_version"))).scalar_one() == REVISION

    migration = _migration()

    def again(session: Session) -> None:
        conn = session.connection()
        migration.islamic_styles(conn, forward=True)
        migration.switch(conn, forward=True)
        migration.guide_text(conn, forward=True)

    await adb.run_sync(again)
    assert await _state(adb) == after
