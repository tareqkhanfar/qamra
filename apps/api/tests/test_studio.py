"""The template studio (Addendum 4 §3): theme versions (draft → review → approved → live, rollback), text
edits that make a new version, the deploy seed keeping studio versions, Classic bulk actions, the English
draft (queued only on request, after an estimate), staff roles (admins only) and the audit-log viewer."""

import uuid
from datetime import UTC, datetime, timedelta

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed import upsert_themes
from qamra_core.db.classic import ClassicTemplate, ClassicTemplatePage, TemplateJob, TemplateStatus
from qamra_core.db.models import AuditLog, User
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.store import ArtStyle
from qamra_core.db.studio import ThemeVersion

BASE = "/api/admin/themes/first-day"
BOX = {"x": 0.3, "y": 0.3, "w": 0.3, "h": 0.5}
AR_2 = "{لَبِسَ/لَبِسَتْ} {name} {ملابسَه/ملابسَها} الجديدة، ومن الحقيبة همس {companion}: «أنا {معكَ/معكِ}!»"


async def _theme(adb: AsyncSession, slug: str = "first-day") -> ThemeRow:
    await upsert_themes(adb)
    return (await adb.execute(select(ThemeRow).where(ThemeRow.slug == slug))).scalar_one()


async def _actions(adb: AsyncSession, prefix: str) -> list[AuditLog]:
    q = select(AuditLog).where(AuditLog.action.startswith(prefix)).order_by(AuditLog.created_at)
    return list((await adb.execute(q)).scalars())


async def _template(adb: AsyncSession, theme: ThemeRow, status: TemplateStatus, style: str = "watercolor",
                    variant: str = "girl") -> ClassicTemplate:  # fmt: skip
    t = ClassicTemplate(theme_id=theme.id, theme_version=theme.version, art_style=style, variant=variant,
                        status=status, generation={"theme_def": theme.definition})  # fmt: skip
    adb.add(t)
    await adb.flush()
    for beat in range(3):
        key = f"classic/templates/{t.id}/{beat}.jpg"
        adb.add(ClassicTemplatePage(template_id=t.id, beat=beat, image_key=key, hero_box=BOX))
    await adb.commit()
    return t


async def test_a_version_goes_through_review_live_and_back(client: AsyncClient, adb: AsyncSession) -> None:
    theme = await _theme(adb)
    await make_admin(client, adb, email="reviewer@example.com", roles=("reviewer",))
    r = await client.get(BASE)
    assert r.status_code == 200 and r.json()["live_version"] == 3 and r.json()["open"] is None
    assert [v["status"] for v in r.json()["history"]] == ["live"] and r.json()["history"][0][
        "source"
    ] == "file"
    assert (await client.post(f"{BASE}/versions", json={})).status_code == 403  # themes.view only
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="editor@example.com", roles=("editor",))

    r = await client.post(f"{BASE}/versions", json={"note": "spring edits"})
    assert r.status_code == 201, r.text
    assert r.json()["version"] == 4 and r.json()["status"] == "draft" and r.json()["base_version"] == 3
    assert r.json()["created_by"] == "أم سلمى" and r.json()["changes"] == []
    assert (await client.post(f"{BASE}/versions", json={})).json()["error"]["code"] == "version_open"
    r = await client.post(f"{BASE}/versions/4/status", json={"to": "approved"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition"
    assert (await client.post(f"{BASE}/versions/4/publish")).status_code == 409  # not approved yet
    for to in ("in_review", "approved"):
        r = await client.post(f"{BASE}/versions/4/status", json={"to": to})
        assert r.status_code == 200 and r.json()["status"] == to, r.text
    r = await client.post(f"{BASE}/versions/4/publish")
    assert r.status_code == 200 and r.json()["status"] == "live" and r.json()["published_by"] == "أم سلمى"
    await adb.refresh(theme)
    assert theme.version == 4 and theme.definition["version"] == 4
    statuses = {v.version: v.status.value for v in (await adb.execute(select(ThemeVersion))).scalars()
                if v.theme_id == theme.id}  # fmt: skip
    assert statuses == {3: "retired", 4: "live"}

    assert (await client.post(f"{BASE}/versions/4/rollback")).status_code == 409  # only a retired one
    r = await client.post(f"{BASE}/versions/3/rollback")
    assert r.status_code == 200 and r.json()["status"] == "live"
    await adb.refresh(theme)
    assert theme.version == 3 and theme.definition["version"] == 3
    history = (await client.get(BASE)).json()["history"]
    assert [(v["version"], v["status"]) for v in history] == [(4, "retired"), (3, "live")]
    logged = [
        (a.action, a.data.get("version"), a.data.get("replaced")) for a in await _actions(adb, "theme.")
    ]
    assert logged[0] == ("theme.version_created", 4, None)
    assert ("theme.version_published", 4, 3) in logged and logged[-1] == ("theme.version_rolled_back", 3, 4)


async def test_a_text_edit_makes_a_new_version(client: AsyncClient, adb: AsyncSession) -> None:
    theme = await _theme(adb)
    live_text = theme.definition["pages"][1]["text_ar"]
    await make_admin(client, adb, roles=("editor",))
    r = await client.put(f"{BASE}/pages/2/text", json={"text_ar": AR_2, "note": "shorter"})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 4 and r.json()["status"] == "draft" and r.json()["note"] == "shorter"
    assert [c["key"] for c in r.json()["changes"]] == ["page:2:text_ar"]
    await adb.refresh(theme)
    assert theme.version == 3 and theme.definition["pages"][1]["text_ar"] == live_text  # live until published
    r = await client.put(f"{BASE}/pages/2/text", json={"text_en": "{name} put on new clothes."})
    assert r.json()["version"] == 4  # the same draft: no fork, no second version
    assert {c["key"] for c in r.json()["changes"]} == {"page:2:text_ar", "page:2:text_en"}
    edits = await _actions(adb, "theme.text_edited")
    assert [(a.data["version"], a.data["page"], a.data["created"], a.data["fields"]) for a in edits] == [
        (4, 2, True, ["text_ar"]),
        (4, 2, False, ["text_en"]),
    ]
    r = await client.put(f"{BASE}/pages/2/text", json={"text_ar": "{name} {ذهب/ذهبت و} {nam}"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "theme_invalid"
    r = await client.put(f"{BASE}/pages/2/text", json={"text_ar": " ".join(["كلمة"] * 40)})
    assert r.status_code == 422 and "words" in r.json()["error"]["details"]["problems"][0]
    assert (await client.put(f"{BASE}/pages/99/text", json={"text_en": "x"})).status_code == 404

    await client.post(f"{BASE}/versions/4/status", json={"to": "in_review"})
    r = await client.put(f"{BASE}/pages/3/text", json={"text_en": "Breakfast time."})
    assert r.status_code == 409 and r.json()["error"]["code"] == "version_pending"
    await client.post(f"{BASE}/versions/4/status", json={"to": "approved"})
    await client.post(f"{BASE}/versions/4/publish")
    await adb.refresh(theme)
    assert theme.definition["pages"][1]["text_ar"] == AR_2
    r = await client.put(f"{BASE}/pages/3/text", json={"text_en": "Breakfast time, {name}!"})
    assert r.json()["version"] == 5 and r.json()["base_version"] == 4  # a new draft from the new live one
    assert (await client.delete(f"{BASE}/versions/5")).status_code == 204
    assert (await client.get(BASE)).json()["open"] is None
    assert (await _actions(adb, "theme.version_discarded"))[0].data["version"] == 5


async def test_the_deploy_seed_keeps_a_studio_version(client: AsyncClient, adb: AsyncSession) -> None:
    theme = await _theme(adb)
    await make_admin(client, adb, roles=("editor",))
    await client.put(f"{BASE}/pages/2/text", json={"text_ar": AR_2})
    for step in ("in_review", "approved"):
        await client.post(f"{BASE}/versions/4/status", json={"to": step})
    await client.post(f"{BASE}/versions/4/publish")
    assert "=first-day" in await upsert_themes(adb)  # a deploy leaves the studio's live version alone
    await adb.refresh(theme)
    assert theme.version == 4 and theme.definition["pages"][1]["text_ar"] == AR_2


async def test_stale_texts_bulk_copy_publish_and_schedule(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    theme = await _theme(adb)
    adb.add_all(
        [ArtStyle(slug=s, name_ar=s, name_en=s, prompt="p", lines=["classic"]) for s in ("watercolor", "3d")]
    )
    approved = await _template(adb, theme, TemplateStatus.approved)
    draft = await _template(adb, theme, TemplateStatus.draft, variant="boy")
    await make_admin(client, adb, roles=("editor",))
    r = await client.get("/api/admin/studio/templates", params={"theme": "first-day"})
    assert r.status_code == 200 and {s["slug"] for s in r.json()["styles"]} == {"watercolor", "3d"}
    rows = {t["variant"]: t for t in r.json()["templates"]}
    assert (
        rows["girl"]["pages_drawn"] == 3
        and rows["girl"]["pages_total"] == 18
        and not rows["girl"]["texts_stale"]
    )
    assert rows["girl"]["vowelized"] is False and rows["girl"]["status"] == "approved"
    only = await client.get("/api/admin/studio/templates", params={"status": "draft"})
    assert [t["id"] for t in only.json()["templates"]] == [str(draft.id)]

    await client.put(f"{BASE}/pages/2/text", json={"text_ar": AR_2})  # a new version, published
    for step in ("in_review", "approved"):
        await client.post(f"{BASE}/versions/4/status", json={"to": step})
    await client.post(f"{BASE}/versions/4/publish")
    row = (await client.get("/api/admin/studio/templates")).json()["templates"][0]
    assert (
        row["texts_stale"]
        and row["theme_version"] == 3
        and row["live_version"] == 4
        and not row["story_changed"]
    )
    texts = (await client.get(f"/api/admin/studio/templates/{approved.id}/texts")).json()
    assert texts["gender"] == "f" and texts["texts_stale"] and texts["pages"][2]["current"]["ar"] == AR_2
    assert texts["pages"][2]["pinned"]["ar"] != AR_2 and texts["pages"][0]["layout"] == "cover"
    r = await client.post(f"/api/admin/classic/templates/{approved.id}/texts", json={"refresh": True})
    assert r.status_code == 202 and r.json()["theme_version"] == 4  # the words follow; the art stays
    assert r.json()["status"] == "in_review"  # changed after approval: reviewed again
    approved.job = TemplateJob.idle
    approved.status = TemplateStatus.approved
    await adb.commit()

    queued = len(Queue("generation", connection=app.state.rq_redis).jobs)
    r = await client.post("/api/admin/studio/templates/copy", json={"ids": [str(approved.id)], "style": "3d"})
    assert r.status_code == 200 and len(r.json()["done"]) == 1, r.text
    copy = await adb.get(ClassicTemplate, uuid.UUID(r.json()["done"][0]))
    assert copy is not None and copy.status == TemplateStatus.draft and copy.job == TemplateJob.idle
    assert copy.art_style == "3d" and copy.variant == "girl" and copy.theme_version == 4
    assert len(Queue("generation", connection=app.state.rq_redis).jobs) == queued  # nothing drawn yet
    again = await client.post(
        "/api/admin/studio/templates/copy", json={"ids": [str(approved.id)], "style": "3d"}
    )
    assert again.json()["skipped"] == [{"id": str(approved.id), "reason": "exists"}]
    bad = await client.post(
        "/api/admin/studio/templates/copy", json={"ids": [str(approved.id)], "style": "oil"}
    )
    assert bad.status_code == 422

    when = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    body = {"ids": [str(approved.id), str(draft.id)], "publish_at": when}
    r = await client.post("/api/admin/studio/templates/schedule", json=body)
    assert r.json()["done"] == [str(approved.id)] and r.json()["skipped"][0]["reason"] == "status:draft"
    await adb.refresh(approved)
    assert approved.publish_at is not None
    past = {**body, "publish_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()}
    assert (await client.post("/api/admin/studio/templates/schedule", json=past)).status_code == 422

    r = await client.post(
        "/api/admin/studio/templates/publish", json={"ids": [str(approved.id), str(draft.id)]}
    )
    assert r.json()["done"] == [str(approved.id)] and r.json()["skipped"][0]["reason"] == "status:draft"
    await adb.refresh(approved)
    assert approved.status == TemplateStatus.live and approved.live_at and approved.publish_at is None
    r = await client.post(
        "/api/admin/studio/templates/publish", json={"ids": [str(approved.id)], "to": "approved"}
    )
    assert r.json()["done"] == [str(approved.id)]  # off sale again
    bulk = [a.data for a in await _actions(adb, "classic.template_status")]
    assert {"from": "approved", "to": "live", "bulk": True} in bulk
    assert {"from": "live", "to": "approved", "bulk": True} in bulk
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="reviewer@example.com", roles=("reviewer",))
    assert (await client.get("/api/admin/studio/templates")).status_code == 200  # templates.view
    r = await client.post("/api/admin/studio/templates/publish", json={"ids": [str(approved.id)]})
    assert r.status_code == 403


async def test_the_english_draft_is_estimated_then_queued(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await _theme(adb)
    await make_admin(client, adb, roles=("editor",))
    r = await client.get(f"{BASE}/versions/3/translate")
    assert r.status_code == 200 and r.json()["usd"] > 0 and r.json()["pages"] == 17, r.text
    assert r.json()["model"].startswith("claude-")
    queue = Queue("generation", connection=app.state.rq_redis)
    assert not queue.jobs  # an estimate calls nothing
    assert (await client.post(f"{BASE}/versions/3/translate", json={})).status_code == 422  # not confirmed
    r = await client.post(f"{BASE}/versions/3/translate", json={"confirm": True})
    assert r.status_code == 202 and r.json()["version"] == 4 and r.json()["status"] == "draft", r.text
    assert r.json()["translate"]["state"] == "queued" and r.json()["translate"]["estimate_usd"] > 0
    job = queue.jobs[-1]
    v4 = (await adb.execute(select(ThemeVersion).where(ThemeVersion.version == 4))).scalar_one()
    assert job.func_name == "qamra_worker.jobs.studio.translate_theme_version" and job.args == (str(v4.id),)
    assert (
        await client.post(f"{BASE}/versions/4/translate", json={"confirm": True})
    ).status_code == 409  # busy
    r = await client.post(f"{BASE}/versions/3/translate", json={"confirm": True})
    assert r.json()["error"]["code"] == "version_open"
    requested = await _actions(adb, "theme.translate_requested")
    assert requested[0].data["version"] == 4 and requested[0].data["estimate_usd"] > 0


async def test_only_admins_change_staff_roles(client: AsyncClient, adb: AsyncSession) -> None:
    await register(client, email="new.editor@example.com", name="سارة")
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="editor@example.com", roles=("editor",))
    assert (await client.get("/api/admin/staff")).status_code == 403
    body = {"email": "new.editor@example.com", "roles": ["editor"]}
    assert (await client.post("/api/admin/staff", json=body)).status_code == 403
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="boss@example.com", roles=("admin",))
    r = await client.get("/api/admin/staff")
    assert r.status_code == 200 and {s["email"] for s in r.json()["staff"]} == {
        "editor@example.com",
        "boss@example.com",
    }
    assert {
        "role": "editor",
        "permissions": ["books.view", "journey", "templates", "themes", "workbook"],
    } in r.json()["roles"]
    r = await client.post("/api/admin/staff", json=body)
    assert r.status_code == 201 and r.json()["roles"] == ["editor"] and r.json()["mfa"] is False, r.text
    sara = uuid.UUID(r.json()["id"])
    r = await client.put(f"/api/admin/staff/{sara}/roles", json={"roles": ["editor", "reviewer"]})
    assert r.status_code == 200 and r.json()["roles"] == ["editor", "reviewer"]
    r = await client.put(f"/api/admin/staff/{sara}/roles", json={"roles": ["owner"]})
    assert r.status_code == 403  # only an owner hands out the owner role
    me = uuid.UUID((await client.get("/api/admin/staff")).json()["me"])
    r = await client.put(f"/api/admin/staff/{me}/roles", json={"roles": ["owner"]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "self_change"
    assert (await client.put(f"/api/admin/staff/{sara}/roles", json={"roles": []})).status_code == 422
    assert (await client.delete(f"/api/admin/staff/{sara}")).status_code == 204
    user = await adb.get(User, sara)
    assert user is not None and user.role.value == "parent"
    assert (await client.put(f"/api/admin/staff/{sara}/roles", json={"roles": ["editor"]})).status_code == 404
    logged = [
        (a.action, a.data.get("role")) for a in await _actions(adb, "staff.") if a.entity_id == str(sara)
    ]
    assert logged == [
        ("staff.added", None),
        ("staff.role_granted", "editor"),
        ("staff.role_granted", "reviewer"),
        ("staff.role_revoked", "editor"),
        ("staff.role_revoked", "reviewer"),
        ("staff.removed", None),
    ]


async def test_the_audit_viewer_filters_and_pages(client: AsyncClient, adb: AsyncSession) -> None:
    actor, other = uuid.uuid4(), uuid.uuid4()
    start = datetime(2026, 3, 1, 9, tzinfo=UTC)
    for i in range(25):
        action, kind = ("theme.text_edited", "theme") if i < 20 else ("staff.added", "user")
        adb.add(AuditLog(actor_user_id=actor if i % 2 else other, action=action, entity_type=kind,
                         entity_id=f"e{i % 3}", data={"i": i},
                         created_at=start + timedelta(days=i)))  # fmt: skip
    await adb.commit()
    await make_admin(client, adb, email="editor@example.com", roles=("editor",))
    assert (await client.get("/api/admin/audit")).status_code == 403
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="boss@example.com", roles=("admin",))
    until = datetime(2026, 9, 1, tzinfo=UTC).isoformat()  # the seeded rows only (not this test's sign-ins)
    r = await client.get("/api/admin/audit", params={"until": until, "per_page": 10})
    assert r.status_code == 200 and r.json()["total"] == 25 and r.json()["pages"] == 3
    assert [i["data"]["i"] for i in r.json()["items"]] == list(range(24, 14, -1))  # newest first
    r = await client.get("/api/admin/audit", params={"until": until, "per_page": 10, "page": 3})
    assert [i["data"]["i"] for i in r.json()["items"]] == [4, 3, 2, 1, 0]
    r = await client.get("/api/admin/audit", params={"actor": str(actor), "action": "theme.", "until": until})
    assert r.json()["total"] == 10 and {i["actor"] for i in r.json()["items"]} == {str(actor)}
    r = await client.get("/api/admin/audit", params={"entity_type": "theme", "entity_id": "e1"})
    assert r.json()["total"] == 7 and all(i["entity_id"] == "e1" for i in r.json()["items"])
    since = (start + timedelta(days=20)).isoformat()
    r = await client.get("/api/admin/audit", params={"since": since, "until": until})
    assert [i["action"] for i in r.json()["items"]] == ["staff.added"] * 5
    assert set(r.json()["items"][0]) == {"id", "at", "actor", "action", "entity_type", "entity_id", "data"}
    facets = (await client.get("/api/admin/audit/facets")).json()
    assert {"theme.text_edited", "staff.added", "user.login"} <= set(facets["actions"])
    assert {"theme", "user"} <= set(facets["entity_types"])
