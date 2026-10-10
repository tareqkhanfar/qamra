"""The theme editor's fixes (owner, 2026-10-09: «محرر الثيمات … مش شايفه شغال»):

- a theme's own pages and words can be read for editing without any Classic template, and a «قريبًا» story
  says it has no pages (no broken screen);
- the theme list says which stories are «قريبًا» and how many pages each has (nothing to translate without);
- the page editor previews each Arabic form with a sample child of its gender (a boy's name for the boy's
  form, a girl's for the girl's), for a theme and for a template;
- the e2e fixtures of the studio's browser test: staff with roles, and a template drawn with placeholders.
"""

import copy
import uuid

import pytest
from api_helpers import make_admin, register
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed import upsert_themes
from qamra_api.settings import ApiSettings
from qamra_api.theme_versions import apply_definition
from qamra_core.db.classic import ClassicTemplate, ClassicTemplatePage, TemplateStatus
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.store import ArtStyle

SLUG = "new-sibling"  # its sample child is a girl, Salma


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(
        _env_file=None,
        env="test",
        cookie_secure=False,
        log_json=False,  # type: ignore[call-arg]
        web_base_url="http://testserver",
        login_max_attempts=5,
        login_ip_max_attempts=20,
        settings_cache_seconds=0,
        e2e_fixtures=True,  # the studio's browser-test fixtures are tested here too
    )


async def _theme(adb: AsyncSession, slug: str = SLUG) -> ThemeRow:
    await upsert_themes(adb)
    return (await adb.execute(select(ThemeRow).where(ThemeRow.slug == slug))).scalar_one()


async def _coming_soon(adb: AsyncSession, base: ThemeRow) -> ThemeRow:
    """A «قريبًا» story: its catalog card only, no cover and no pages yet."""
    definition = copy.deepcopy(base.definition)
    definition.update(slug="e2e-soon", version=1, cover=None, pages=[])
    definition["catalog"]["status"] = "coming_soon"
    row = ThemeRow(slug="e2e-soon", definition=definition)
    apply_definition(row, definition)
    adb.add(row)
    await adb.commit()
    return row


async def test_a_theme_s_pages_are_editable_without_a_template(
    client: AsyncClient, adb: AsyncSession
) -> None:
    theme = await _theme(adb)
    await make_admin(client, adb, roles=("reviewer",))  # reading needs themes.view only
    r = await client.get(f"/api/admin/studio/themes/{SLUG}/texts")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["available"] is True and body["gender"] is None and body["editing"] is None
    assert body["live_version"] == theme.version and body["theme_title"]["ar"] == "ضيفنا الصغير"
    assert [p["beat"] for p in body["pages"]] == list(range(len(theme.definition["pages"]) + 1))
    assert body["names"] == {"m": {"ar": "يوسف", "en": "Yousef"}, "f": {"ar": "سلمى", "en": "Salma"}}
    cover, page2 = body["pages"][0], body["pages"][2]
    assert cover["layout"] == "cover" and cover["current"]["ar"] == theme.definition["title_ar"]
    source = theme.definition["pages"][1]
    assert page2["pinned"] == page2["current"] == {"ar": source["text_ar"], "en": source["text_en"]}
    assert page2["layout"] == source.get("layout", "full") and page2["vowelized"] is None
    areas = {None, "top", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right"}
    assert {p["area"] for p in body["pages"]} <= areas
    assert (await client.get("/api/admin/studio/themes/nope/texts")).status_code == 404
    offered = [o["slug"] for o in (await client.get("/api/admin/studio/templates")).json()["themes"]]
    assert SLUG in offered and "custom" not in offered  # the custom story's base has no Classic line

    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="editor@example.com", roles=("editor",))
    r = await client.put(f"/api/admin/themes/{SLUG}/pages/2/text", json={"text_en": "{name} drew a moon."})
    assert r.status_code == 200, r.text
    page2 = (await client.get(f"/api/admin/studio/themes/{SLUG}/texts")).json()["pages"][2]
    assert page2["current"]["en"] == "{name} drew a moon." and page2["pinned"]["en"] == source["text_en"]
    assert (await client.get(f"/api/admin/studio/themes/{SLUG}/texts")).json()["editing"] == {
        "version": theme.version + 1,
        "status": "draft",
    }


async def test_a_coming_soon_story_says_it_has_no_pages(client: AsyncClient, adb: AsyncSession) -> None:
    soon = await _coming_soon(adb, await _theme(adb))
    await make_admin(client, adb, roles=("editor",))
    r = await client.get(f"/api/admin/studio/themes/{soon.slug}/texts")
    assert r.status_code == 200, r.text
    assert r.json()["available"] is False and r.json()["pages"] == []
    listed = {t["slug"]: t for t in (await client.get("/api/admin/themes")).json()}
    assert (listed[soon.slug]["available"], listed[soon.slug]["pages"]) == (False, 0)
    assert listed[SLUG]["available"] is True and listed[SLUG]["pages"] > 10
    detail = (await client.get(f"/api/admin/themes/{soon.slug}")).json()
    assert detail["available"] is False and detail["pages"] == 0
    r = await client.put(f"/api/admin/themes/{soon.slug}/pages/1/text", json={"text_en": "Hello."})
    assert r.status_code == 404  # no page to edit


async def test_a_template_previews_each_form_with_a_child_of_its_gender(
    client: AsyncClient, adb: AsyncSession
) -> None:
    theme = await _theme(adb)
    t = ClassicTemplate(
        theme_id=theme.id,
        theme_version=theme.version,
        art_style="cartoon",
        variant="boy",
        status=TemplateStatus.in_review,
        generation={"theme_def": theme.definition},
    )
    adb.add(t)
    await adb.commit()
    await make_admin(client, adb, roles=("editor",))
    body = (await client.get(f"/api/admin/studio/templates/{t.id}/texts")).json()
    assert body["gender"] == "m" and body["sample"]["name_ar"] == "يوسف"  # the boy's look: a boy's name
    assert body["names"]["m"]["ar"] == "يوسف" and body["names"]["f"]["ar"] == "سلمى"
    assert body["sample"]["companion_ar"] == theme.definition["default_companion"]["name_ar"]


async def test_the_studio_e2e_fixtures(client: AsyncClient, adb: AsyncSession) -> None:
    theme = await _theme(adb)
    await register(client)
    assert (await client.get("/api/admin/themes")).status_code == 403  # a parent
    r = await client.post("/api/e2e/staff", json={"roles": ["editor"]})
    assert r.status_code == 200 and r.json()["roles"] == ["editor"], r.text
    assert (await client.get("/api/admin/themes")).status_code == 200  # staff, two-step verification passed
    assert (await client.get("/api/admin/staff")).status_code == 403  # an editor is not an admin

    body = {"theme": SLUG, "style": "cartoon", "variant": "boy", "missing_box": 2}
    r = await client.post("/api/e2e/studio-templates", json=body)
    assert r.status_code == 201, r.text
    first = r.json()["id"]
    detail = (await client.get(f"/api/admin/classic/templates/{first}")).json()
    assert detail["status"] == "in_review" and detail["texts"]["vowelized"] is True
    assert detail["pages_drawn"] == detail["pages_total"] == len(theme.definition["pages"]) + 1
    pages = {p["beat"]: p for p in detail["pages"]}
    assert pages[2]["hero_box"] is None and pages[3]["hero_box"] is not None
    assert pages[1]["status"] == "needs_review" and pages[1]["flags"] == ["frame"]
    image = await client.get(f"/api/admin/classic/templates/{first}/pages/0/image")
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"

    adb.add(ArtStyle(slug="watercolor", name_ar="مائي", name_en="Watercolor", prompt="p", lines=["classic"]))
    await adb.commit()
    r = await client.post("/api/admin/studio/templates/copy", json={"ids": [first], "style": "watercolor"})
    assert r.status_code == 200 and len(r.json()["done"]) == 1, r.text
    again = (await client.post("/api/e2e/studio-templates", json=body)).json()["id"]
    assert again != first  # made again; the copy went with the old one
    left = (await adb.execute(select(ClassicTemplate.id).where(ClassicTemplate.theme_id == theme.id))).all()
    assert [str(i) for (i,) in left] == [again]
    assert (await client.post("/api/e2e/studio-templates/clear", json=body)).status_code == 204
    gone = select(ClassicTemplatePage).where(ClassicTemplatePage.template_id == uuid.UUID(again))
    assert (await adb.execute(gone)).first() is None  # its pages too

    real = ClassicTemplate(
        theme_id=theme.id,
        theme_version=theme.version,
        art_style="cartoon",
        variant="boy",
        generation={"theme_def": theme.definition},
    )
    adb.add(real)
    await adb.commit()
    r = await client.post("/api/e2e/studio-templates", json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "template_exists"  # never a real template
