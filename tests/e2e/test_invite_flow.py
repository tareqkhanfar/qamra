"""The kindergarten invite and the free cover in a real browser, with the create flow's own photo and drawing
steps (owner, 2026-10-16: the invite and the free cover get what the parent flow has): on a 390 px phone, in
Arabic, no AI (the drawings are finished with placeholder art by `/api/e2e/characters/{id}/ready`).

- The invite: consent (1 of 3) → the photo placed in the oval (2 of 3) → the drawing in the class's style,
  the portrait first («هل هذه طفلتكم؟») → a redraw with «ما الذي لا يشبهها؟» in the parent's words →
  «تعديل الصورة» and back with its note → the earlier drawing chosen from the strip and approved → done.
- The free cover: the photo is placed in the oval on this device, and the framing goes with it once the form
  is sent with the consent.
"""

import re
import uuid

from e2e_flow import BASE_URL, FACE, call, fits, step_is
from playwright.sync_api import Page, expect

FRAME = re.compile(r"^موضع الصورة")  # the draggable frame's label while the editor is open


def _drag(page: Page, dx: float, dy: float) -> None:
    box = page.get_by_label(FRAME).bounding_box()
    assert box is not None
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    for i in range(1, 11):
        page.mouse.move(x + dx * i / 10, y + dy * i / 10)
    page.mouse.up()


def _child(page: Page, name: str) -> dict:  # type: ignore[type-arg]
    return next(c for c in call(page, "GET", "/api/create/children") if c["name"] == name)  # type: ignore[no-any-return]


def _ready_newest(page: Page, name: str) -> str:
    """The drawing just asked for, finished with placeholder art (a portrait and a sheet)."""
    newest = _child(page, name)["characters"][-1]
    assert newest["status"] == "generating"
    call(page, "POST", f"/api/e2e/characters/{newest['id']}/ready")
    return str(newest["id"])


def test_the_invite_uses_the_create_flows_photo_and_drawing_steps(page: Page) -> None:
    token = call(
        page, "POST", "/api/e2e/invites", {"child_name": "سلمى", "gender": "f", "style": "watercolor"}
    )["token"]
    page.goto(f"{BASE_URL}/ar/invite/{token}")
    page.get_by_role("button", name="متابعة لكتاب سلمى").click()

    # 1 of 3: the consent for the class book
    step_is(page, 1, 3)
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="موافق، التالي").click()

    # 2 of 3: the photo, placed in the oval, never shown to the school
    step_is(page, 2, 3)
    page.locator('input[type="file"]').set_input_files(FACE)
    use = page.get_by_role("button", name="استخدموا هذه الصورة")
    expect(use).to_be_enabled()
    page.get_by_role("button", name="تعديل موضع الصورة").click()
    page.get_by_role("button", name="تصغير", exact=True).click()
    _drag(page, -20, 10)
    page.get_by_role("button", name="احفظوا الموضع").click()
    expect(page.get_by_text("حفظنا الموضع الجديد للصورة.")).to_be_visible()
    assert _child(page, "سلمى")["photo"]["crop"] is not None
    fits(page)
    use.click()

    # 3 of 3: drawn at once in the class's style; the portrait first
    step_is(page, 3, 3)
    expect(page.get_by_text("نرسم سلمى الآن…")).to_be_visible()
    first = _ready_newest(page, "سلمى")
    expect(page.get_by_text("هل هذه طفلتكم؟")).to_be_visible()
    expect(page.get_by_text("هكذا ستظهر سلمى في كتاب الصف مع أصدقائها.")).to_be_visible()
    expect(page.get_by_text("تدخل شخصيتها كتاب الصف، ولا ترى الروضة صورتها الأصلية أبدًا.")).to_be_visible()

    # a redraw with the parent's own words
    page.get_by_text("ما الذي لا يشبهها؟").click()
    page.get_by_label(re.compile("أو اكتبوا بكلماتكم")).fill("شعرها أطول قليلًا")
    page.get_by_role("button", name=re.compile("أعيدوا الرسم")).click()
    expect(page.get_by_text("نرسم سلمى الآن…").first).to_be_visible()
    second = _ready_newest(page, "سلمى")
    assert second != first
    expect(page.get_by_text("رسومات سلمى حتى الآن")).to_be_visible()

    # «تعديل الصورة»: the kept original, and back to the drawing with the note
    page.get_by_role("button", name="تعديل الصورة", exact=True).click()
    expect(page.get_by_role("heading", name="تعديل صورة سلمى")).to_be_visible()
    step_is(page, 2, 3)
    _drag(page, 15, -10)
    page.get_by_role("button", name="احفظوا الموضع").click()
    expect(
        page.get_by_text("حفظنا الموضع الجديد للصورة، وسنستخدمه حين تضغطون «أعيدوا الرسم».")
    ).to_be_visible()

    # the first drawing, chosen from the strip, is the one approved
    strip = page.get_by_role("region", name="رسومات سلمى حتى الآن")
    strip.get_by_role("button").last.click()
    page.get_by_role("button", name="نعم، تشبه سلمى").click()
    expect(page.get_by_text("شكرًا! اكتملت خطواتكم.")).to_be_visible()
    approved = [c["id"] for c in _child(page, "سلمى")["characters"] if c["approved"]]
    assert approved == [first]
    fits(page)


def _free_cover_on(page: Page) -> None:
    """The admin's `free_cover` switch, on (the page sends visitors to the stories while it is off)."""
    assert page.context.browser is not None
    staff = page.context.browser.new_context(locale="ar")
    admin = staff.new_page()
    admin.goto(f"{BASE_URL}/ar/login")
    email = f"e2e-staff-{uuid.uuid4().hex[:10]}@example.com"
    call(
        admin,
        "POST",
        "/api/auth/register",
        {"email": email, "password": "moonlight-2026", "full_name": "طاقم"},
    )
    call(admin, "POST", "/api/e2e/staff", {"roles": ["owner"]})
    call(admin, "PUT", "/api/admin/settings", {"values": {"free_cover": True}})
    staff.close()


def test_the_free_cover_places_the_photo_in_the_oval(page: Page) -> None:
    _free_cover_on(page)
    call(page, "POST", "/api/e2e/classic-templates", {"theme": "first-day", "style": "watercolor"})
    page.goto(f"{BASE_URL}/ar/free-cover")
    page.get_by_label("اسم الطفل").fill("جنى")
    page.get_by_role("radio", name="بنت").click()
    page.locator('input[type="file"]').set_input_files(FACE)
    expect(page.get_by_label(FRAME)).to_be_visible()  # the editor opens on the picked photo, on this device
    page.get_by_role("button", name="تكبير", exact=True).click()
    _drag(page, 25, -15)
    assert not any(c["name"] == "جنى" for c in call(page, "GET", "/api/create/children"))  # nothing sent yet
    page.get_by_role("checkbox", name=re.compile("^أؤكد أنني ولي أمر")).check()
    page.get_by_role("button", name="ارسموا الغلاف").click()
    page.wait_for_url(re.compile(r"/free-cover/result\?id="))
    child = _child(page, "جنى")
    assert child["consent"] and child["photo"]["crop"] is not None
