"""The photo step's framing editor in a real browser (owner, 2026-10-10: «اسحب فيها يمين يسار فوق وتحت
عشان يتطابق مع الدائرة … وبعد الإرفاق وبعد الرسم»): on a 390 px phone, in Arabic, no AI.

- A child far from the camera: the API frames the photo around the face, so it lands in the oval; zooming in
  further is capped at what the photo's sharpness allows.
- «تعديل موضع الصورة»: drag, zoom, turn, the keyboard; «إلغاء» keeps the saved framing, «احفظوا الموضع» saves
  a new one (the API checks it again).
- Two children in one photo: refused, then framed to one child and accepted.
- After the drawing, «تعديل الصورة» opens the kept original (from the API after a reload), and saving goes
  back to the character step with the note that the next «أعيدوا الرسم» uses it.
- Once the original is deleted (the 24-hour job, `/api/e2e/photos/{id}/expire`), the editor says so kindly and
  takes a new photo.
"""

import re
from pathlib import Path
from typing import Any

from e2e_flow import BASE_URL, FACE, call, query
from PIL import Image
from playwright.sync_api import Page, expect

FRAME = re.compile(r"^موضع الصورة")  # the draggable frame's label while the editor is open


def _jpeg(img: Image.Image, path: Path) -> Path:
    img.save(path, format="JPEG", quality=92)
    return path


def _far(tmp: Path) -> Path:
    """A child far from the camera: the 512 px face on a 2048 × 1536 photo (too far whole)."""
    canvas = Image.new("RGB", (2048, 1536), (150, 160, 170))
    canvas.paste(Image.open(FACE).convert("RGB"), (1348, 100))
    return _jpeg(canvas, tmp / "far.jpg")


def _two(tmp: Path) -> Path:
    face = Image.open(FACE).convert("RGB").resize((1024, 1024))
    two = Image.new("RGB", (2048, 1024))
    two.paste(face, (0, 0))
    two.paste(face, (1024, 0))
    return _jpeg(two, tmp / "two.jpg")


def _photo(page: Page, child_id: str) -> dict[str, Any]:
    child = next(c for c in call(page, "GET", "/api/create/children") if c["id"] == child_id)
    return child["photo"]  # type: ignore[no-any-return]


def _drag(page: Page, dx: float, dy: float) -> None:
    box = page.get_by_label(FRAME).bounding_box()
    assert box is not None
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    for i in range(1, 11):
        page.mouse.move(x + dx * i / 10, y + dy * i / 10)
    page.mouse.up()


def test_framing_on_upload_after_upload_and_after_the_drawing(page: Page, tmp_path: Path) -> None:
    child = call(page, "POST", "/api/create/children", {"name": "ليان", "gender": "f", "age": 5})
    call(
        page,
        "POST",
        f"/api/create/children/{child['id']}/consent",
        {"accept": True, "version": "parent-2026-09"},
    )
    page.goto(f"{BASE_URL}/ar/create?step=photo&child={child['id']}&line=magic&style=3d")
    use = page.get_by_role("button", name="استخدموا هذه الصورة")

    # a far-away child: framed around the face on upload
    page.locator('input[type="file"]').set_input_files(_far(tmp_path))
    expect(use).to_be_enabled()
    first = _photo(page, child["id"])
    assert first["crop"]["x"] > 0.5 and first["crop"]["w"] < 0.3  # zoomed in on the face, on the right

    # «تعديل موضع الصورة»: zoom-in is already at the photo's limit; zoom out, drag, save
    page.get_by_role("button", name="تعديل موضع الصورة").click()
    expect(page.get_by_role("button", name="تكبير", exact=True)).to_be_disabled()
    page.get_by_role("button", name="تصغير", exact=True).click()
    page.get_by_role("button", name="تصغير", exact=True).click()
    _drag(page, -60, 30)
    page.get_by_role("button", name="احفظوا الموضع").click()
    expect(page.get_by_text("حفظنا الموضع الجديد للصورة.")).to_be_visible()
    moved = _photo(page, child["id"])
    assert moved["id"] == first["id"] and moved["crop"] != first["crop"]  # the same original, a new framing

    # the keyboard and the turn, then «إلغاء»: the saved framing stays
    page.get_by_role("button", name="تعديل موضع الصورة").click()
    page.get_by_label(FRAME).focus()
    for key in ("ArrowLeft", "ArrowUp", "+", "-"):
        page.keyboard.press(key)
    page.get_by_role("button", name="تدوير").click()
    page.get_by_role("button", name="إلغاء").click()
    assert _photo(page, child["id"])["crop"] == moved["crop"]

    # two children: refused, then framed to one
    page.locator('input[type="file"]').set_input_files(_two(tmp_path))
    expect(page.get_by_text("في الصورة أكثر من وجه")).to_be_visible()
    for _ in range(6):
        page.get_by_role("button", name="تكبير", exact=True).click()
    _drag(page, 400, 250)  # the child on the left, the whole face in the frame
    page.get_by_role("button", name="افحصوا الصورة من جديد").click()
    expect(use).to_be_enabled()
    framed = _photo(page, child["id"])
    assert framed["id"] != first["id"] and framed["crop"]["x"] + framed["crop"]["w"] <= 0.5

    # drawn (placeholder art), then «تعديل الصورة» from the character step, after a reload
    use.click()
    approve = "نعم، تشبه ليان"
    page.wait_for_url(re.compile(r"[?&]character=[0-9a-f-]{36}"))
    call(page, "POST", f"/api/e2e/characters/{query(page)['character']}/ready")
    expect(page.get_by_role("button", name=approve)).to_be_visible()
    page.get_by_role("button", name="تعديل الصورة", exact=True).click()
    page.wait_for_url(re.compile(r"edit=photo"))
    page.reload()  # another device, or a reload: the original comes from the API
    expect(page.get_by_role("heading", name="تعديل صورة ليان")).to_be_visible()
    _drag(page, -15, 10)
    page.get_by_role("button", name="احفظوا الموضع").click()
    page.wait_for_url(re.compile(r"step=character"))
    expect(
        page.get_by_text("حفظنا الموضع الجديد للصورة، وسنستخدمه حين تضغطون «أعيدوا الرسم».")
    ).to_be_visible()
    assert _photo(page, child["id"])["crop"] != framed["crop"]  # saved, and nothing redrawn by itself
    expect(page.get_by_role("button", name=approve)).to_be_visible()

    # the original deleted (24 hours after the approval): said kindly, and a new photo can be given
    call(page, "POST", f"/api/e2e/photos/{framed['id']}/expire")
    page.get_by_role("button", name="تعديل الصورة", exact=True).click()
    expect(page.get_by_text("حذفنا صورة ليان الأصلية حفاظًا على خصوصيتها")).to_be_visible()
    page.locator('input[type="file"]').set_input_files(FACE)
    expect(use).to_be_enabled()
    use.click()
    expect(page.get_by_text("حفظنا الصورة الجديدة، وسنرسم منها")).to_be_visible()
