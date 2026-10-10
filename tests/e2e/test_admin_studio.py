"""The template studio in the admin (Addendum 4 §3; owner, 2026-10-09: «محرر الثيمات … مش شايفه شغال»).

- The theme editor («محرر الثيمات»): a theme's pages with their words, edited for a boy, a girl and in
  English into a new draft, previewed for a sample child of each gender, then the draft goes to review, is
  approved and published, and the previous version is rolled back; a new draft is discarded; the English
  draft shows its estimate and stops there (no model call).
- A Classic template (placeholder art from `/api/e2e/studio-templates`): approval is refused while a hero page
  has no hero box; the box is added, moved and saved; the template is approved (its pages lock), published
  and taken off sale, then published and copied to another style in bulk from the list.
- «قالب جديد»: the paid drawing asks first (dismissed here, nothing is made); the dry run (placeholder
  pictures, no AI) makes the template and opens its editor.
- Roles: an editor edits words; an admin without the themes permission gets a clear message.

No AI and no paid call (docs/e2e.md): staff sign in through `/api/e2e/staff`, the template's pages are
placeholders, and the only template job the test queues is a dry run, removed again at the end.
"""

import re
import uuid
from collections.abc import Iterator

import pytest
from e2e_flow import BASE_URL, call, fits
from playwright.sync_api import Browser, Dialog, Page, expect

THEME = "new-sibling"  # «ضيفنا الصغير»: its sample child is a girl, Salma; the house boy is Yousef
TEMPLATE = {"theme": THEME, "style": "cartoon", "variant": "boy", "missing_box": 2}
DRY_RUN = {"theme": "graduation", "style": "cartoon", "variant": "girl_hijab"}


def as_staff(page: Page, *roles: str) -> None:
    """The signed-in test user becomes staff with `roles`, two-step verification passed."""
    call(page, "POST", "/api/e2e/staff", {"roles": list(roles) or ["owner"]})


def watch(page: Page) -> list[str]:
    """Script errors and server errors (5xx) while the test runs; 4xx answers are part of some steps."""
    problems: list[str] = []
    page.on("pageerror", lambda e: problems.append(f"script error: {e}"))
    page.on("response", lambda r: problems.append(f"{r.status} {r.url}") if r.status >= 500 else None)
    return problems


def no_raw_keys(page: Page) -> None:
    """The Arabic screen shows words, never message keys or machine flags (e.g. «studio.x», «no_hero_box»)."""
    text = page.locator("main").inner_text()
    leftovers = re.findall(r"\b[a-z]+(?:_[a-z]+)+\b|\bstudio\.[a-zA-Z.]+", text)
    assert not leftovers, f"raw keys on the screen: {leftovers}"


def close_open_version(page: Page, slug: str) -> None:
    """A run stopped halfway may have left a version open: back to draft, then discarded."""
    theme = call(page, "GET", f"/api/admin/themes/{slug}")
    if theme["open"]:
        version = theme["open"]["version"]
        if theme["open"]["status"] != "draft":
            call(page, "POST", f"/api/admin/themes/{slug}/versions/{version}/status", {"to": "draft"})
        call(page, "DELETE", f"/api/admin/themes/{slug}/versions/{version}")


@pytest.fixture
def desk(browser: Browser) -> Iterator[Page]:
    """A desktop (1280 px, Arabic) signed in as a new user, for the template editor's boxes."""
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="ar")
    context.set_default_timeout(30_000)
    page = context.new_page()
    page.goto(f"{BASE_URL}/ar/login")
    call(page, "POST", "/api/e2e/rate-limits/reset")
    email = f"e2e-{uuid.uuid4().hex[:10]}@example.com"
    call(
        page,
        "POST",
        "/api/auth/register",
        {"email": email, "password": "moonlight-2026", "full_name": "أم ليان"},
    )
    yield page
    context.close()


def test_theme_text_draft_preview_publish_and_rollback(page: Page) -> None:
    problems = watch(page)
    as_staff(page, "owner")
    close_open_version(page, THEME)
    theme = call(page, "GET", f"/api/admin/themes/{THEME}")
    live, draft = theme["live_version"], max(v["version"] for v in theme["history"]) + 1
    before = call(page, "GET", f"/api/admin/studio/themes/{THEME}/texts")["pages"][2]["current"]

    page.goto(f"{BASE_URL}/ar/admin/studio")  # the studio opens on its themes tab from the nav
    page.get_by_role("link", name="محرر الثيمات").first.click()
    page.wait_for_url(re.compile(r"/ar/admin/studio/themes"))
    expect(page.get_by_role("heading", level=1)).to_have_text("محرر الثيمات")
    page.get_by_label("الثيم").select_option(THEME)
    expect(page.get_by_role("heading", name="صفحات القصة")).to_be_visible()
    fits(page)

    page.get_by_role("button", name="صفحة 2", exact=True).click()
    arabic = page.get_by_label("العربية (بصيغتي الولد والبنت)")
    expect(arabic).to_have_value(before["ar"])
    arabic.fill(before["ar"] + " هَيَّا!")
    english = page.get_by_label("English", exact=True)
    english.fill(before["en"] + " Hooray!")
    forms = page.locator("dl").filter(has_text="ولد:")
    expect(forms).to_contain_text("رَسَمَ يوسف")  # each form with a child of its gender
    expect(forms).to_contain_text("رَسَمَتْ سلمى")
    page.get_by_label("ملاحظة عن التعديل (اختياري)").fill("تجربة المحرر")
    page.get_by_role("button", name="حفظ النص").click()
    expect(page.get_by_role("status").filter(has_text=f"حُفظ في المسودة v{draft}")).to_be_visible()
    expect(page.get_by_text(f"التعديلات تُحفظ في المسودة v{draft}")).to_be_visible()

    preview = page.get_by_role("group", name="خيارات المعاينة")
    preview.get_by_role("button", name="ولد", exact=True).click()
    panel = page.locator("p[lang=ar]").last
    expect(panel).to_contain_text("رَسَمَ يوسف")
    expect(panel).to_contain_text("هَيَّا!")
    preview.get_by_role("button", name="بنت", exact=True).click()
    expect(panel).to_contain_text("رَسَمَتْ سلمى")
    preview.get_by_role("button", name="English", exact=True).click()
    expect(page.locator("p[lang=en]").last).to_contain_text("Salma drew a moon and stars")
    expect(page.locator("p[lang=en]").last).to_contain_text("Hooray!")
    no_raw_keys(page)

    card = page.locator("li").filter(has=page.get_by_text(f"v{draft}", exact=True))
    expect(card).to_contain_text("مسودة")
    card.get_by_role("button", name="عرض التغييرات").click()
    expect(card).to_contain_text("صفحة 2 · عربي")
    expect(card).to_contain_text("صفحة 2 · إنجليزي")
    card.get_by_role("button", name="مسودة إنجليزية").click()  # only the estimate: no model call
    expect(card).to_contain_text("التكلفة التقديرية")
    card.get_by_role("button", name="إلغاء").click()

    page.on("dialog", lambda d: d.accept())
    card.get_by_role("button", name="إرسال للمراجعة").click()
    expect(card).to_contain_text("قيد المراجعة")
    expect(page.get_by_text(f"النسخة v{draft} قيد المراجعة أو معتمدة")).to_be_visible()  # words read-only
    card.get_by_role("button", name="اعتماد").click()
    expect(card).to_contain_text("معتمد")
    card.get_by_role("button", name="نشر هذه النسخة").click()
    expect(page.locator("h2").filter(has_text="ضيفنا الصغير").locator("..")).to_contain_text(f"v{draft}")
    texts = call(page, "GET", f"/api/admin/studio/themes/{THEME}/texts")
    assert texts["live_version"] == draft and texts["pages"][2]["pinned"]["ar"].endswith("هَيَّا!")

    previous = page.locator("li").filter(has=page.get_by_text(f"v{live}", exact=True))
    expect(previous).to_contain_text("سابقة")
    previous.get_by_role("button", name="الرجوع إلى هذه النسخة").click()
    expect(previous).to_contain_text("منشور")
    texts = call(page, "GET", f"/api/admin/studio/themes/{THEME}/texts")
    assert texts["live_version"] == live and texts["pages"][2]["pinned"] == before

    page.get_by_role("button", name="مسودة جديدة").click()  # a new draft, then discarded
    fresh = page.locator("li").filter(has=page.get_by_text(f"v{draft + 1}", exact=True))
    expect(page.get_by_text(f"التعديلات تُحفظ في المسودة v{draft + 1}")).to_be_visible()
    expect(fresh).to_contain_text("مسودة")
    fresh.get_by_role("button", name="حذف المسودة").click()
    expect(fresh).to_have_count(0)
    assert call(page, "GET", f"/api/admin/themes/{THEME}")["open"] is None
    assert not problems, problems


def test_template_hero_box_approve_publish_and_bulk(desk: Page) -> None:
    page = desk
    problems = watch(page)
    as_staff(page, "owner")
    template = call(page, "POST", "/api/e2e/studio-templates", TEMPLATE)
    page.on("dialog", lambda d: d.accept())

    page.goto(f"{BASE_URL}/ar/admin/studio")
    expect(page.get_by_role("heading", level=1)).to_have_text("استوديو القوالب")
    group = page.locator("section").filter(has=page.get_by_role("heading", name=re.compile("ضيفنا الصغير")))
    group.get_by_role("link", name="كرتون ملوّن · ولد").click()
    page.wait_for_url(re.compile(f"/admin/studio/templates/{template['id']}"))
    expect(page.get_by_role("heading", level=1)).to_contain_text("ضيفنا الصغير · كرتون ملوّن · ولد")
    header = page.locator("main header")
    expect(header).to_contain_text("قيد المراجعة")
    expect(header).to_contain_text("صفحات للمراجعة")  # the template's flag, in words
    page.get_by_role("button", name=re.compile(r"^صفحة 1(?!\d)")).click()
    expect(page.get_by_text("تحتاج مراجعة")).to_be_visible()  # the page's own review state and check
    expect(page.get_by_text("صورة مقسومة أو بهامش")).to_be_visible()
    no_raw_keys(page)

    page.get_by_role("button", name="اعتماد (يقفل الصفحات)").click()  # page 2 has no hero box yet
    refused = page.get_by_role("alert").filter(has_text="لا يمكن الاعتماد بعد")
    expect(refused).to_contain_text("صناديق البطل ✗")

    page.get_by_role("button", name=re.compile(r"^صفحة 2(?!\d)")).click()
    page.get_by_role("button", name="إضافة صندوق البطل").click()
    hero = page.get_by_role("group", name="البطل")
    start = hero.bounding_box()
    assert start is not None
    page.mouse.move(start["x"] + start["width"] / 2, start["y"] + start["height"] / 2)
    page.mouse.down()
    page.mouse.move(start["x"] + start["width"] / 2 - 40, start["y"] + start["height"] / 2 + 20, steps=5)
    page.mouse.up()
    hero.focus()
    page.keyboard.press("Shift+ArrowRight")  # a little wider, from the keyboard
    page.get_by_role("button", name="حفظ الصندوق").click()
    expect(page.get_by_role("button", name="حفظ الصندوق")).to_be_disabled()
    saved = call(page, "GET", f"/api/admin/classic/templates/{template['id']}")
    box = next(p for p in saved["pages"] if p["beat"] == 2)["hero_box"]
    assert box is not None and box["x"] < 0.35 and box["w"] > 0.3, box  # moved left from 0.35, wider than 0.3

    page.get_by_role("button", name="اعتماد (يقفل الصفحات)").click()
    expect(header).to_contain_text("معتمد")
    expect(page.get_by_role("button", name=re.compile("^صفحة 2 🔒"))).to_be_visible()
    page.get_by_role("button", name="نشر", exact=True).click()
    expect(header).to_contain_text("منشور")
    page.get_by_role("button", name="إيقاف النشر").click()
    expect(header).to_contain_text("معتمد")
    no_raw_keys(page)

    page.get_by_role("link", name="← كل القوالب").click()
    mine = group.locator("li").filter(has=page.get_by_role("link", name="كرتون ملوّن · ولد"))
    expect(mine).to_contain_text("صفحات للمراجعة")
    mine.get_by_role("checkbox", name="تحديد كرتون ملوّن · ولد").check()
    bulk = page.get_by_role("region", name="إجراءات جماعية")
    bulk.get_by_role("button", name="نشر", exact=True).click()
    expect(page.get_by_role("status").filter(has_text="نُفّذ على 1، وتُخطّي 0")).to_be_visible()
    expect(mine).to_contain_text("منشور")
    expect(mine.get_by_role("checkbox")).to_be_checked()  # still selected: copy it to another style
    bulk.get_by_label("أسلوب الرسم").select_option("watercolor")
    bulk.get_by_role("button", name="نسخ الإعدادات في مسودة").click()
    expect(page.get_by_role("status").filter(has_text="نُفّذ على 1، وتُخطّي 0")).to_be_visible()
    copy = group.locator("li").filter(has_text="مائي فاخر · ولد")
    expect(copy).to_contain_text("مسودة")
    expect(copy).to_contain_text("0 من 18 صفحة مرسومة")
    no_raw_keys(page)
    assert not problems, problems


def test_new_template_asks_before_paying_and_makes_a_dry_run(desk: Page) -> None:
    page = desk
    problems = watch(page)
    as_staff(page, "owner")
    call(page, "POST", "/api/e2e/studio-templates/clear", DRY_RUN)
    page.goto(f"{BASE_URL}/ar/admin/studio")
    page.get_by_role("button", name="قالب جديد").click()
    form = page.locator("section").filter(has=page.get_by_role("heading", name="قالب جديد"))
    form.get_by_label("القصة").select_option(DRY_RUN["theme"])
    form.get_by_label("أسلوب الرسم").select_option(DRY_RUN["style"])
    form.get_by_label("الشكل").select_option(DRY_RUN["variant"])
    form.get_by_label("سقف التكلفة (بالدولار الأمريكي)").fill("2.5")
    expect(form).to_contain_text("تكلفة حقيقية تصل إلى")
    expect(form).to_contain_text("$2.50")

    asked: list[str] = []

    def dismiss(dialog: Dialog) -> None:
        asked.append(dialog.message)
        dialog.dismiss()

    page.once("dialog", dismiss)
    form.get_by_role("button", name="ابدؤوا الرسم").click()  # the paid drawing: dismissed, nothing is made
    expect(form).to_be_visible()
    assert asked and "بتكلفة حقيقية تصل إلى" in asked[0], asked
    listed = call(page, "GET", f"/api/admin/studio/templates?theme={DRY_RUN['theme']}")["templates"]
    assert not [t for t in listed if (t["style"], t["variant"]) == (DRY_RUN["style"], DRY_RUN["variant"])]

    form.get_by_role("checkbox", name=re.compile("تجربة بصور مؤقتة")).check()
    expect(form).to_contain_text("بلا تكلفة")
    form.get_by_role("button", name="ابدؤوا التجربة").click()  # no confirm: nothing is paid
    page.wait_for_url(re.compile(r"/ar/admin/studio/templates/[0-9a-f-]{36}$"))
    expect(page.get_by_role("heading", level=1)).to_contain_text("يوم تخرّجي · كرتون ملوّن · بنت بحجاب")
    call(page, "POST", "/api/e2e/studio-templates/clear", DRY_RUN)
    assert not problems, problems


def test_roles_an_editor_edits_and_an_admin_is_told_why_not(page: Page) -> None:
    problems = watch(page)
    as_staff(page, "editor")
    close_open_version(page, THEME)
    page.goto(f"{BASE_URL}/ar/admin/studio/themes?theme={THEME}")
    page.get_by_role("button", name="صفحة 1", exact=True).click()
    english = page.get_by_label("English", exact=True)
    english.fill(english.input_value() + " Yay!")
    page.get_by_role("button", name="حفظ النص").click()
    expect(page.get_by_role("status").filter(has_text="حُفظ في المسودة")).to_be_visible()
    close_open_version(page, THEME)

    as_staff(page, "admin")  # settings, prices, users: no themes
    page.goto(f"{BASE_URL}/ar/admin/studio/themes")
    expect(page.locator("main").get_by_role("alert")).to_have_text("ليست لديكم صلاحية لهذه الصفحة.")
    expect(page.locator("[aria-busy=true]")).to_have_count(0)
    assert not problems, problems
