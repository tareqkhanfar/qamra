"""The order flow per product (docs/plans/order-flows.md §c, chunk 12), in a real browser on a 390 px phone,
in Arabic: from the product or story page to a confirmed cash-on-delivery order and, for a file, its
download.

No AI and no paid call: the drawing asked for after the photo, the story preview and the activity books'
renders are finished by the test-only fixtures (`/api/e2e/*`, placeholder art and PDFs). Everything else is
the real site and API: the steps, «الخطوة n من N», the cart, the checkout, the order page and the download
(the worker's home copy).

- «قلبي يعرف الله» V1, new child: one tap → cart → who → consent → photo → style (every style, real samples;
  «شبه حقيقي» chosen) → character → review (6 steps; the owner brought the style step back on 2026-10-09).
- «قلبي يعرف الله», the set, child with a ready character: «ابدؤوا» → who → review (2); the card's
  «ارسموا شخصية جديدة بأسلوب آخر» adds the drawing steps (5) and taking it back removes them.
- «رحلتي الأولى», a ready 3D character, a new one in another style: who → photo → style → character →
  review (5); the cart line keeps the new character and its style.
- «دوسية التأسيس» KG1 V2: the English name asked and checked, «لؤي» traced, a Latin Arabic name refused (6).
- «دوسية التأسيس» KG2 set as PDF: who → review (2) → order → placeholder render → the download.
- «رحلتي الأولى»: stage 3 asks the English name, stage 1 doesn't (its age note warns, never blocks).
- «مغامراتي مع عائلتي»: one tap → who → family → review (3); «تعديل» keeps the family; «ابدؤوا» + skip.
- «قمرة كلاسيك» from its story page: who (no likes) → consent → photo → character → story → writing →
  format → add-ons (8).
- «قمرة سحري» from `/create`: who → type → consent → photo → style (real sample pages) → character →
  companion → story (likes) → writing → review → format → add-ons (12).
- No switched-off add-on and no black-and-white «دوسية التأسيس» anywhere.
"""

import re
from typing import Any

from e2e_flow import (
    BASE_URL,
    approve_placeholder_character,
    call,
    checkout,
    confirm,
    finish_preview,
    fits,
    give_consent,
    new_child,
    order,
    preview_book,
    query,
    step_is,
    upload_photo,
)
from playwright.sync_api import Page, expect

COMPLETE = "أكملوا بيانات الطفل"
START = "ابدؤوا كتاب طفلكم الآن"
WHO_LABEL = "الاسم كما سيُطبع في الكتاب"
NAME_EN = "الاسم بالأحرف الإنجليزية"
# what an activity book's flow never asks (the story flow it used to fall into, §0.1); the art style is asked
# again since 2026-10-09, on its own step, when a character is drawn
STORY_THINGS = (
    "أي كتاب تريدون",
    "قمرة كلاسيك",
    "قمرة سحري",
    "ماذا تحب",
    "إلى أين",
    "شيء مميز",
)
# switched off by the owner (2026-10-07): never offered, never in the catalog
INACTIVE_ADDONS = {
    "gift-box",
    "wipe-sleeve",
    "crayon-kit",
    "extra-character",
    "coloring-version",
    "cover-poster",
    "sticker-sheet",
    "audio-qr",
    "parent-guide",
    "editable-files",
    "express",
    "family-characters",
}


def no_story_things(page: Page) -> None:
    for text in STORY_THINGS:
        expect(page.get_by_text(text)).to_have_count(0)


def pick(page: Page, group: str, value: str) -> None:
    """A choice on an activity book's page (its radio groups: «المجلد», «المستوى», «الشكل»…)."""
    choices = page.get_by_role("radiogroup", name=group, exact=True)
    choices.get_by_role("radio", name=value, exact=True).click()


def to_checkout_and_order(page: Page) -> str:
    """The cart's «متابعة للعنوان والدفع», the checkout's header, then the address and cash on delivery."""
    expect(page.get_by_role("link", name=COMPLETE)).to_have_count(0)  # nothing waits for the child
    page.get_by_role("link", name="متابعة للعنوان والدفع").click()
    expect(page.get_by_text("الخطوة الأخيرة: العنوان والدفع")).to_be_visible()  # no "n of 12"
    expect(page.get_by_text(re.compile(r"من 12"))).to_have_count(0)
    fits(page)
    code: str = checkout(page)
    return code


def confirmed(page: Page, code: str) -> dict[str, Any]:
    """Staff confirm the order; its page then says so. Returns the order as the test fixture reads it."""
    assert confirm(page, code)["status"] == "confirmed"
    page.reload()
    expect(page.get_by_text("تأكّد الطلب").first).to_be_visible()
    placed: dict[str, Any] = order(page, code)
    return placed


# ---- «قلبي يعرف الله» --------------------------------------------------------------------------------------


ACTIVITY_STYLES = ("سينمائي ثلاثي الأبعاد", "مائي فاخر", "كرتون ملوّن", "شبه حقيقي")


def pick_style(page: Page, name: str, child: str) -> None:
    """The activity style step: every style the book accepts, each with a real sample picture, the chosen one
    with its gallery (the activity-book pages first); then «ارسموا شخصية …»."""
    expect(page.get_by_role("heading", name=f"كيف تحبون أن نرسم {child}؟")).to_be_visible()
    styles = page.get_by_role("radiogroup", name="أسلوب الرسم").get_by_role("radio")
    expect(styles).to_have_count(len(ACTIVITY_STYLES))  # never the black-and-white coloring
    for style, label in zip(styles.all(), ACTIVITY_STYLES, strict=True):
        expect(style).to_contain_text(label)
        expect(style.locator("img")).to_have_attribute("src", re.compile(r"^/samples/"))  # a real sample
    expect(page.get_by_text("أمّا صفحات الأنشطة نفسها فلا تتغيّر")).to_be_visible()
    styles.filter(has_text=name).click()
    gallery = page.get_by_role("region", name=f"هكذا تبدو الشخصية بأسلوب «{name}»")
    expect(gallery.get_by_role("listitem").first.locator("img")).to_have_attribute(
        "src", re.compile(r"/samples/.+/(activity-cover|character)-sm\.webp$")
    )
    fits(page)
    page.get_by_role("button", name=f"ارسموا شخصية {child}").click()


def test_islamic_v1_new_child(page: Page) -> None:
    """One tap V1 → «أكملوا بيانات الطفل» → a new child: who, consent, photo, the art style (every style, with
    real samples; «شبه حقيقي»), the character, the review with «أنا مسلمة صغيرة» → the same cart line, filled,
    with the chosen style → a confirmed order."""
    page.goto(f"{BASE_URL}/ar/workbooks/islamic-series")
    pick(page, "المجلد", "الأول")
    pick(page, "الشكل", "مطبوع")
    fits(page)
    page.get_by_role("button", name="أضيفوا للسلة").first.click()
    page.wait_for_url("**/cart")
    line = call(page, "GET", "/api/store/cart")["items"][0]
    assert line["sku"] == "islamic-v1-softcover" and line["needs_details"]
    expect(page.get_by_text("ينقصه: اسم الطفل وشخصيته")).to_be_visible()
    fits(page)

    page.get_by_role("link", name=COMPLETE).first.click()
    page.wait_for_url("**/create**")
    assert query(page)["product"] == "islamic-v1-softcover" and query(page)["item"] == line["id"]
    expect(page.get_by_role("heading", name="لمن هذا الكتاب؟")).to_be_visible()
    step_is(page, 1, 6)
    expect(page.get_by_label(NAME_EN)).to_have_count(0)  # «قلبي يعرف الله» prints no English name
    expect(page.get_by_text("لنكتب في الشهادة: «أنا مسلمة صغيرة» أو «أنا مسلم صغير».")).to_be_visible()
    no_story_things(page)
    new_child(page, label=WHO_LABEL, name="ضحى", gender="f", age=5)
    expect(page.get_by_text("«قلبي يعرف الله · ضحى»")).to_be_visible()  # the cover's title
    fits(page)
    page.get_by_role("button", name="متابعة").click()

    step_is(page, 2, 6)
    expect(page.get_by_role("heading", name="قبل أن نطلب صورة ضحى، هذا ما نعد به")).to_be_visible()
    fits(page)
    give_consent(page)

    step_is(page, 3, 6)
    expect(page.get_by_role("heading", name="صورة واحدة واضحة تكفي")).to_be_visible()
    expect(page.get_by_text("بعدها تختارون أسلوب الرسم، ثم نرسم شخصية ضحى")).to_be_visible()
    fits(page)
    upload_photo(page)

    step_is(page, 4, 6)  # the parent picks the style (owner, 2026-10-09)
    no_story_things(page)
    pick_style(page, "شبه حقيقي", "ضحى")

    step_is(page, 5, 6)
    character = approve_placeholder_character(page, "نعم، تشبه ضحى")
    assert call(page, "GET", f"/api/create/characters/{character}")["style"] == "semi-realistic"

    step_is(page, 6, 6)
    expect(page.get_by_role("heading", name="راجعوا كتاب ضحى")).to_be_visible()
    expect(page.get_by_text("المجلد الأول · مطبوع")).to_be_visible()
    expect(page.get_by_text("«أنا مسلمة صغيرة»")).to_be_visible()
    expect(page.get_by_text("79 ₪")).to_be_visible()
    no_story_things(page)
    # its optional add-ons, each with its picture: only the printed answers («إجابات الأنشطة مطبوعةً»)
    page.get_by_text("إضافات اختيارية").click()
    offers = page.get_by_role("button").filter(has_text="+15 ₪")
    expect(offers).to_have_count(1)
    expect(offers.locator("img")).to_have_attribute("src", "/addons/printed-parent-guide.webp")
    fits(page)
    page.get_by_role("button", name="احفظوا في السلة").click()

    page.wait_for_url("**/cart")
    cart = call(page, "GET", "/api/store/cart")
    assert [i["id"] for i in cart["items"]] == [line["id"]]  # this line, filled; not a second one
    filled = cart["items"][0]
    assert not filled["needs_details"] and filled["book_id"] is None and filled["character_id"] == character
    assert filled["style"] == "semi-realistic"  # the style the parent chose
    expect(page.get_by_text("قلبي يعرف الله · ضحى")).to_be_visible()
    expect(page.get_by_text("المجلد الأول · مطبوع")).to_be_visible()
    fits(page)
    code = to_checkout_and_order(page)

    expect(page.get_by_text("قلبي يعرف الله · ضحى")).to_be_visible()  # the order page says the same
    expect(page.get_by_text("المجلد الأول · مطبوع")).to_be_visible()
    fits(page)
    placed = confirmed(page, code)
    assert placed["skus"] == ["islamic-v1-softcover"]
    item = placed["items"][0]
    assert item["child_id"] == filled["child_id"] and item["personalization"]["character_id"] == character


def test_islamic_set_known_child(page: Page) -> None:
    """A child whose character is approved: «ابدؤوا كتاب طفلكم الآن» → the child's card (2 steps) → review."""
    child = preview_book(page, name="ضحى", age=6)["child_id"]  # consent and an approved character, no AI
    page.goto(f"{BASE_URL}/ar/workbooks/islamic-series")
    pick(page, "المجلد", "المجلدات الخمسة")
    page.get_by_role("link", name=START).click()
    page.wait_for_url("**/create**")
    assert query(page) == {"product": "islamic-set-softcover"}

    page.get_by_role("button", name="ضحى", exact=True).click()  # «لأحد أطفالكم؟»
    step_is(page, 1, 2)  # no drawing: her character is reused
    card = page.get_by_role("region", name="ضحى · بنت · 6 سنوات")
    expect(card.get_by_text("شخصيتها جاهزة")).to_be_visible()
    expect(card.get_by_label(NAME_EN)).to_have_count(0)
    no_story_things(page)
    fits(page)
    # a new character in another style instead: a photo (hers was never kept), the style and the drawing
    card.get_by_role("button", name="ارسموا شخصية جديدة بأسلوب آخر").click()
    expect(card.get_by_text("سنرسم لها شخصية جديدة بالأسلوب الذي تختارونه.")).to_be_visible()
    expect(card.get_by_role("button", name="ترتدي الحجاب")).to_be_visible()  # the look, for the new drawing
    step_is(page, 1, 5)
    card.get_by_role("button", name="لا، استخدموا شخصيتها الجاهزة").click()
    step_is(page, 1, 2)
    page.get_by_role("button", name="نعم، الكتاب لـضحى").click()

    step_is(page, 2, 2)
    expect(page.get_by_role("heading", name="راجعوا كتاب ضحى")).to_be_visible()
    expect(page.get_by_text("المجلدات الخمسة · مطبوع")).to_be_visible()
    expect(page.get_by_text("«أنا مسلمة صغيرة»")).to_be_visible()
    expect(page.get_by_text("329 ₪")).to_be_visible()
    expect(page.get_by_text("هذا الكتاب مُعدّ لعمر")).to_have_count(0)  # 6 is in 4–8
    fits(page)
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    items = call(page, "GET", "/api/store/cart")["items"]
    assert [(i["sku"], i["child_id"], i["needs_details"]) for i in items] == [
        ("islamic-set-softcover", child, False)
    ]
    expect(page.get_by_text("المجلدات الخمسة · مطبوع")).to_be_visible()
    code = to_checkout_and_order(page)
    expect(page.get_by_text("قلبي يعرف الله · ضحى")).to_be_visible()
    placed = confirmed(page, code)
    assert placed["skus"] == ["islamic-set-softcover"] and placed["items"][0]["child_id"] == child


# ---- «دوسية التأسيس» ---------------------------------------------------------------------------------------

ARABIC_ONLY = "اكتبوا الاسم بالحروف العربية فقط، لأن طفلكم سيتتبّعه حرفًا حرفًا."
LATIN_ONLY = "اكتبوا الاسم بالأحرف الإنجليزية فقط، دون أرقام أو رموز."


def test_foundation_kg1_v2_english_name(page: Page) -> None:
    """KG1, volume 2, printed: the child step asks the name in English letters and checks both names. A name
    in Latin letters can't be traced («Luay»: refused, with the friendly message); «لؤي» (ؤ) can; an English
    name in Arabic letters is refused. The review and the cart then show the level, the volume and «Luay»."""
    page.goto(f"{BASE_URL}/ar/workbooks/foundation-workbook")
    pick(page, "المستوى", "KG1 · 4–5 سنوات")
    pick(page, "الجزء", "الثاني")
    pick(page, "الشكل", "مطبوع")
    expect(page.get_by_role("radio", name="أبيض وأسود")).to_have_count(0)  # no B&W interior is sold
    page.get_by_role("button", name="أضيفوا للسلة").first.click()
    page.wait_for_url("**/cart")
    line = call(page, "GET", "/api/store/cart")["items"][0]
    assert line["sku"] == "wb-kg1-v2-color-spiral"
    page.get_by_role("link", name=COMPLETE).first.click()
    page.wait_for_url("**/create**")

    step_is(page, 1, 6)
    expect(page.get_by_text("بالحروف العربية، فطفلكم سيتتبّعه ويكتبه في صفحات «اسمي».")).to_be_visible()
    english = page.get_by_label(NAME_EN)
    expect(english).to_have_attribute("placeholder", "مثال: Duha")
    no_story_things(page)
    new_child(page, label=WHO_LABEL, name="Luay", gender="m", age=4)
    expect(page.get_by_text(ARABIC_ONLY)).to_be_visible()  # said as it is typed
    english.fill("Luay")
    page.get_by_role("button", name="متابعة").click()
    expect(page.get_by_role("alert").filter(has_text=ARABIC_ONLY)).to_be_visible()
    step_is(page, 1, 6)  # not added

    page.get_by_label(WHO_LABEL, exact=True).fill("لؤي")
    expect(page.get_by_text(ARABIC_ONLY)).to_have_count(0)  # ؤ is traced
    expect(page.get_by_text("«دوسية لؤي»")).to_be_visible()
    english.fill("لؤي")
    page.get_by_role("button", name="متابعة").click()
    expect(page.get_by_role("alert").filter(has_text=LATIN_ONLY)).to_be_visible()
    step_is(page, 1, 6)
    english.fill("Luay")
    page.get_by_role("button", name="متابعة").click()

    step_is(page, 2, 6)
    give_consent(page)
    step_is(page, 3, 6)
    upload_photo(page)
    step_is(page, 4, 6)
    pick_style(page, "سينمائي ثلاثي الأبعاد", "لؤي")  # the default, kept
    step_is(page, 5, 6)
    approve_placeholder_character(page, "نعم، يشبه لؤي")

    step_is(page, 6, 6)
    expect(page.get_by_role("heading", name="راجعوا كتاب لؤي")).to_be_visible()
    expect(page.get_by_text("KG1 · الجزء الثاني · ملوّن · مطبوع")).to_be_visible()
    expect(page.get_by_text("Luay", exact=True)).to_be_visible()
    expect(page.get_by_text("«أحسنتَ يا لؤي!»")).to_be_visible()
    expect(page.get_by_text("هذا الكتاب مُعدّ لعمر")).to_have_count(0)  # 4 is in KG1's 4–5
    page.get_by_role("button", name="احفظوا في السلة").click()

    page.wait_for_url("**/cart")
    workbook = page.locator("article").filter(has_text="دوسية لؤي")
    expect(workbook.get_by_text("KG1 · الجزء الثاني · ملوّن · مطبوع")).to_be_visible()
    expect(workbook.get_by_text("الاسم بالإنجليزية: Luay")).to_be_visible()
    code = to_checkout_and_order(page)
    expect(page.get_by_text("دوسية لؤي")).to_be_visible()
    expect(page.get_by_text("الاسم بالإنجليزية: Luay")).to_be_visible()
    placed = confirmed(page, code)
    assert placed["skus"] == ["wb-kg1-v2-color-spiral"]
    assert placed["items"][0]["personalization"]["name_en"] == "Luay"
    kids = call(page, "GET", "/api/create/children")
    assert [(k["name"], k["name_latin"]) for k in kids] == [("لؤي", "Luay")]  # kept for the next book


def test_foundation_digital_set_download(page: Page) -> None:
    """KG2, the three volumes as PDF, for a child whose character is ready: the card asks the English name
    (2 steps). After the order is confirmed and its books "rendered" (placeholder PDFs, no engine), the order
    page lists every volume's files, and «تنزيل PDF» downloads the home copy the worker cut."""
    preview_book(page, name="ليان", age=5)
    page.goto(f"{BASE_URL}/ar/workbooks/foundation-workbook")
    pick(page, "المستوى", "KG2 · 5–6 سنوات")
    pick(page, "الجزء", "الثلاثة معًا")
    pick(page, "الشكل", "PDF للطباعة بالبيت")
    page.get_by_role("link", name=START).click()
    page.wait_for_url("**/create**")
    assert query(page) == {"product": "wb-kg2-set-color-digital"}

    page.get_by_role("button", name="ليان", exact=True).click()
    step_is(page, 1, 2)
    card = page.get_by_role("region", name="ليان · بنت · 5 سنوات")
    expect(card.get_by_text("شخصيتها جاهزة")).to_be_visible()
    page.get_by_role("button", name="نعم، الكتاب لـليان").click()
    expect(card.get_by_text(LATIN_ONLY)).to_be_visible()  # the book prints it: asked before going on
    card.get_by_label(NAME_EN).fill("Layan")
    page.get_by_role("button", name="نعم، الكتاب لـليان").click()

    step_is(page, 2, 2)
    expect(
        page.get_by_text("هذا ما سنضعه في ملف PDF. تأكدوا من الاسم والتفاصيل قبل الانتقال إلى السلة.")
    ).to_be_visible()
    expect(page.get_by_text("KG2 · الأجزاء الثلاثة · ملوّن · PDF للطباعة بالبيت")).to_be_visible()
    expect(page.get_by_text("Layan", exact=True)).to_be_visible()
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    line = page.locator("article").filter(has_text="دوسية ليان")
    expect(line.get_by_text("KG2 · الأجزاء الثلاثة · ملوّن · ملف PDF")).to_be_visible()
    expect(line.get_by_text("الاسم بالإنجليزية: Layan")).to_be_visible()
    expect(line.get_by_text("تنزّلون الملف من صفحة الطلب أو من حسابكم حين يصبح جاهزًا.")).to_be_visible()
    code = to_checkout_and_order(page)
    expect(page.get_by_text("دوسية ليان")).to_be_visible()
    # not confirmed and not made yet: the line says we'll email (no download button)
    expect(
        page.get_by_text("ما زلنا نجهّز الملف، وسنخبركم بالبريد الإلكتروني حين يصبح جاهزًا للتنزيل.")
    ).to_be_visible()
    expect(page.get_by_role("button", name=re.compile("^تنزيل PDF"))).to_have_count(0)

    made = confirm(page, code, render=True)["books"]
    assert sorted((b["part"], tuple(b["files"])) for b in made) == [
        (v, ("book", "answer-key")) for v in ("1", "2", "3")
    ]
    page.reload()
    expect(page.get_by_text("تأكّد الطلب").first).to_be_visible()
    buttons = page.get_by_role("button", name=re.compile("^تنزيل PDF: "))
    expect(buttons).to_have_count(6)  # three volumes, each the book and its answer key
    for volume in ("الجزء الأول", "الجزء الثاني", "الجزء الثالث"):
        expect(page.get_by_text(f"{volume} · الكتاب مع غلافه")).to_be_visible()
        expect(page.get_by_text(f"{volume} · مفتاح الإجابات")).to_be_visible()
    fits(page)

    page.get_by_role("button", name="تنزيل PDF: الجزء الأول · الكتاب مع غلافه").click()
    ready = page.get_by_role("link", name="الملف جاهز، نزّلوه الآن")  # the worker made the home copy
    again = page.get_by_role("link", name="لم يبدأ التنزيل؟ اضغطوا هنا")  # it existed: the download started
    expect(ready.or_(again)).to_be_visible()
    with page.expect_download() as info:
        (ready if ready.count() else again).click()
    download = info.value
    assert download.suggested_filename.endswith(".pdf"), download.suggested_filename
    assert "KG2" in download.suggested_filename and "ليان" in download.suggested_filename
    with open(download.path(), "rb") as f:
        assert f.read(5) == b"%PDF-"

    # the account page lists the same line under «ملفات للتنزيل»
    page.goto(f"{BASE_URL}/ar/account#downloads")
    downloads = page.locator("#downloads")
    expect(downloads.get_by_text("دوسية ليان")).to_be_visible()
    expect(downloads.get_by_role("button", name=re.compile("^تنزيل PDF: "))).to_have_count(6)


# ---- «رحلتي الأولى» ----------------------------------------------------------------------------------------


def test_journey_stage_3_and_stage_1(page: Page) -> None:
    """Stage 3 prints the child's name in English letters: the card asks it. Stage 1 doesn't, and its age note
    (3–4, the child is 5) warns without blocking. Both lines reach one order with what each prints."""
    child = preview_book(page, name="سلمى", age=5)["child_id"]
    page.goto(f"{BASE_URL}/ar/workbooks/learning-journey")
    pick(page, "المحطة", "الثالثة")
    pick(page, "الشكل", "مطبوع")
    page.get_by_role("link", name=START).click()
    page.wait_for_url("**/create**")
    assert query(page) == {"product": "journey-s3-spiral"}
    page.get_by_role("button", name="سلمى", exact=True).click()
    step_is(page, 1, 2)
    card = page.get_by_role("region", name="سلمى · بنت · 5 سنوات")
    card.get_by_label(NAME_EN).fill("Salma")
    no_story_things(page)
    page.get_by_role("button", name="نعم، الكتاب لـسلمى").click()
    step_is(page, 2, 2)
    expect(page.get_by_text("المحطة الثالثة · مطبوع")).to_be_visible()
    expect(page.get_by_text("Salma", exact=True)).to_be_visible()
    expect(page.get_by_text("هذا الكتاب مُعدّ لعمر")).to_have_count(0)  # stage 3 is 5–6
    page.get_by_role("button", name="أضيفوا للسلة").click()
    page.wait_for_url("**/cart")

    page.goto(f"{BASE_URL}/ar/workbooks/learning-journey")
    pick(page, "المحطة", "الأولى")
    pick(page, "الشكل", "مطبوع")
    page.get_by_role("link", name=START).click()
    page.wait_for_url("**/create**")
    assert query(page) == {"product": "journey-s1-spiral"}
    page.get_by_role("button", name="سلمى", exact=True).click()
    step_is(page, 1, 2)
    expect(page.get_by_label(NAME_EN)).to_have_count(0)  # stage 1 prints no English name
    page.get_by_role("button", name="نعم، الكتاب لـسلمى").click()
    step_is(page, 2, 2)
    expect(page.get_by_text("المحطة الأولى · مطبوع")).to_be_visible()
    expect(page.get_by_text("بالإنجليزية", exact=True)).to_have_count(0)
    expect(page.get_by_text("هذا الكتاب مُعدّ لعمر 3–4 سنوات، وعمر سلمى 5 سنوات.")).to_be_visible()
    page.get_by_role("button", name="أضيفوا للسلة").click()  # a note, not a block

    page.wait_for_url("**/cart")
    stage3 = page.locator("article").filter(has_text="المحطة الثالثة")
    expect(stage3.get_by_text("رحلة سلمى الأولى")).to_be_visible()
    expect(stage3.get_by_text("الاسم بالإنجليزية: Salma")).to_be_visible()
    stage1 = page.locator("article").filter(has_text="المحطة الأولى")
    expect(stage1.get_by_text("الاسم بالإنجليزية")).to_have_count(0)
    code = to_checkout_and_order(page)
    expect(page.get_by_text("رحلة سلمى الأولى")).to_have_count(2)
    placed = confirmed(page, code)
    lines = {i["sku"]: i for i in placed["items"]}
    assert set(lines) == {"journey-s3-spiral", "journey-s1-spiral"}
    assert lines["journey-s3-spiral"]["personalization"]["name_en"] == "Salma"
    assert "name_en" not in lines["journey-s1-spiral"]["personalization"]
    assert {i["child_id"] for i in placed["items"]} == {child}


def test_journey_new_character_in_another_style(page: Page) -> None:
    """A child with a ready 3D character asks for a new one in another style (the card's «ارسموا شخصية جديدة
    بأسلوب آخر»): a new photo (hers is never kept after an approval), the style step (3D is drawn already, so
    the next style is preselected), the drawing in «شبه حقيقي», the review, and a cart line with the new
    character and its style."""
    first = preview_book(page, name="تالا", age=4, style="3d")  # an approved 3D character, no photo kept
    page.goto(f"{BASE_URL}/ar/workbooks/learning-journey")
    pick(page, "المحطة", "الأولى")
    pick(page, "الشكل", "مطبوع")
    page.get_by_role("link", name=START).click()
    page.wait_for_url("**/create**")
    page.get_by_role("button", name="تالا", exact=True).click()
    step_is(page, 1, 2)
    card = page.get_by_role("region", name="تالا · بنت · 4 سنوات")
    card.get_by_role("button", name="ارسموا شخصية جديدة بأسلوب آخر").click()
    step_is(page, 1, 5)
    fits(page)
    page.get_by_role("button", name="نعم، الكتاب لـتالا").click()

    step_is(page, 2, 5)
    upload_photo(page)
    step_is(page, 3, 5)
    styles = page.get_by_role("radiogroup", name="أسلوب الرسم").get_by_role("radio")
    expect(styles.filter(has_text="مائي فاخر")).to_have_attribute("aria-checked", "true")  # not 3D again
    pick_style(page, "شبه حقيقي", "تالا")

    step_is(page, 4, 5)
    character = approve_placeholder_character(page, "نعم، تشبه تالا")
    assert character != str(first["character_id"])
    step_is(page, 5, 5)
    expect(page.get_by_text("المحطة الأولى · مطبوع")).to_be_visible()
    no_story_things(page)
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    [line] = call(page, "GET", "/api/store/cart")["items"]
    assert (line["sku"], line["character_id"], line["style"]) == (
        "journey-s1-spiral",
        character,
        "semi-realistic",
    )
    styles_of = {c["id"]: c["style"] for c in call(page, "GET", "/api/create/children")[0]["characters"]}
    assert styles_of == {str(first["character_id"]): "3d", character: "semi-realistic"}  # both kept


# ---- «مغامراتي مع عائلتي» ----------------------------------------------------------------------------------


def family_member(page: Page, relation: str, name: str) -> None:
    page.get_by_role("button", name="+ أضيفوا فردًا من العائلة").click()
    member = page.get_by_role("group").filter(has=page.get_by_label("صلة القرابة")).last
    member.get_by_label("صلة القرابة").select_option(label=relation)
    member.get_by_label("الاسم الأول (اختياري)").fill(name)


def test_family_one_tap_and_start(page: Page) -> None:
    """The family book, on a phone: one tap → cart → «أكملوا بيانات الطفل» → the child → «من في عائلة كرم؟»
    → the review (3 steps); «تعديل» opens the same line with its family kept. Then «ابدؤوا كتاب طفلكم الآن»
    → the child → the family step skipped → the review says the missions name «أحد الكبار»."""
    child = preview_book(page, name="كرم", gender="m", age=5)["child_id"]
    page.goto(f"{BASE_URL}/ar/workbooks/family-adventures")
    expect(page.get_by_text("تضيفون أسماء العائلة بعد اختيار الطفل.")).to_be_visible()
    fits(page)
    page.get_by_role("button", name="أضيفوا للسلة").first.click()
    page.wait_for_url("**/cart")
    line = call(page, "GET", "/api/store/cart")["items"][0]
    assert line["sku"] == "family-wireo" and line["needs_details"]
    page.get_by_role("link", name=COMPLETE).first.click()
    page.wait_for_url("**/create**")

    page.get_by_role("button", name="كرم", exact=True).click()
    step_is(page, 1, 3)
    expect(page.get_by_label(WHO_LABEL)).to_have_count(0)  # a card, not the new child's form
    expect(page.get_by_role("region", name="كرم · ولد · 5 سنوات").get_by_text("شخصيته جاهزة")).to_be_visible()
    no_story_things(page)
    fits(page)
    page.get_by_role("button", name="نعم، الكتاب لـكرم").click()

    step_is(page, 2, 3)
    expect(page.get_by_role("heading", name="من في عائلة كرم؟")).to_be_visible()
    page.get_by_label("اسم العائلة").fill("الخطيب")
    page.get_by_label("المدينة").fill("نابلس")
    family_member(page, "ماما", "سلمى")
    family_member(page, "بابا", "أحمد")
    fits(page)
    page.get_by_role("button", name="متابعة").click()

    step_is(page, 3, 3)
    review = page.locator("dl > div").filter(has_text="العائلة")
    expect(review.get_by_text("عائلة الخطيب · فردان")).to_be_visible()
    fits(page)
    page.get_by_role("button", name="احفظوا في السلة").click()

    page.wait_for_url("**/cart")
    book = page.locator("article").filter(has_text="مغامرات كرم")
    expect(book.get_by_text("عائلة الخطيب: ماما سلمى، بابا أحمد")).to_be_visible()
    expect(book.get_by_text("المدينة: نابلس")).to_be_visible()
    fits(page)

    # «تعديل»: the same line's review, its family kept, and the family step prefilled from it
    book.get_by_role("link", name="تعديل", exact=True).click()
    page.wait_for_url("**/create**")
    assert query(page)["step"] == "summary" and query(page)["item"] == line["id"]
    step_is(page, 3, 3)
    review = page.locator("dl > div").filter(has_text="العائلة")
    expect(review.get_by_text("عائلة الخطيب · فردان")).to_be_visible()
    review.get_by_role("button", name="تغيير").click()
    step_is(page, 2, 3)
    expect(page.get_by_label("اسم العائلة")).to_have_value("الخطيب")
    expect(page.get_by_label("المدينة")).to_have_value("نابلس")
    expect(page.get_by_label("الاسم الأول (اختياري)")).to_have_count(2)
    expect(page.get_by_label("الاسم الأول (اختياري)").first).to_have_value("سلمى")
    page.get_by_role("button", name="متابعة").click()
    step_is(page, 3, 3)
    page.get_by_role("button", name="احفظوا في السلة").click()
    page.wait_for_url("**/cart")
    expect(book.get_by_text("عائلة الخطيب: ماما سلمى، بابا أحمد")).to_be_visible()

    # «ابدؤوا كتاب طفلكم الآن»: a second copy, the family step skipped
    page.goto(f"{BASE_URL}/ar/workbooks/family-adventures")
    page.get_by_role("link", name=START).click()
    page.wait_for_url("**/create**")
    assert query(page) == {"product": "family-wireo"}
    page.get_by_role("button", name="كرم", exact=True).click()
    step_is(page, 1, 3)
    page.get_by_role("button", name="نعم، الكتاب لـكرم").click()
    step_is(page, 2, 3)
    expect(page.get_by_label("اسم العائلة")).to_have_value("")  # a new line starts empty
    page.get_by_role("button", name="تخطّوا هذه الخطوة").click()
    step_is(page, 3, 3)
    expect(page.get_by_text("دون أسماء: نكتب «أحد الكبار» في المهمّات")).to_be_visible()
    fits(page)
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    expect(page.get_by_text("عائلة كرم، دون أسماء: نكتب «أحد الكبار» في المهمّات")).to_be_visible()
    code = to_checkout_and_order(page)
    expect(page.get_by_text("عائلة الخطيب: ماما سلمى، بابا أحمد")).to_be_visible()
    expect(page.get_by_text("عائلة كرم، دون أسماء: نكتب «أحد الكبار» في المهمّات")).to_be_visible()
    fits(page)
    placed = confirmed(page, code)
    families = sorted((i["personalization"].get("family") or {}).get("name", "") for i in placed["items"])
    assert families == ["", "الخطيب"], placed["items"]
    given = next(i for i in placed["items"] if (i["personalization"].get("family") or {}).get("name"))
    assert {i["child_id"] for i in placed["items"]} == {child}
    assert given["personalization"]["family"]["city"] == "نابلس"
    assert [(m["relation"], m["name"]) for m in given["personalization"]["family"]["members"]] == [
        ("mother", "سلمى"),
        ("father", "أحمد"),
    ]


# ---- stories -----------------------------------------------------------------------------------------------

STORY_ADDONS = {"ترقية إلى غلاف مقوّى", "أصوات العائلة (رمز QR)", "نسخة إضافية من الكتاب نفسه"}
INACTIVE_NAMES = ("علبة هدية", "نسخة تلوين", "بوستر", "توصيل سريع", "شخصية إضافية", "ملصقات")


def only_active_addons_with_pictures(page: Page) -> set[str]:
    """The add-ons step: every offer is one that can be made, each with its picture. Returns their names."""
    expect(page.get_by_role("heading", name="بدكم تزيدوا الفرحة؟")).to_be_visible()
    page.get_by_text(re.compile(r"^إضافات أخرى")).click()  # the folded ones too
    cards = page.get_by_role("button").filter(has=page.locator("img[src^='/addons/']"))
    expect(cards.first).to_be_visible()
    offered = page.locator("button[aria-pressed]")
    assert cards.count() == offered.count(), "an add-on without its picture"
    names = {c.locator("strong").first.inner_text() for c in cards.all()}
    for text in INACTIVE_NAMES:
        expect(page.get_by_text(text)).to_have_count(0)
    return names


def test_classic_story_from_its_page(page: Page) -> None:
    """«قمرة كلاسيك» from the story page, unchanged: the child step asks no likes and no note (Classic never
    reads them), the type is known so there is no type step, the style came from the page so the character is
    drawn at once: 8 steps, ending with the add-ons (only what can be made, with pictures) and the cart."""
    call(page, "POST", "/api/e2e/classic-templates", {"theme": "first-day", "style": "watercolor"})
    page.goto(f"{BASE_URL}/ar/stories/first-day")
    classic = page.get_by_role("radio", name=re.compile("قمرة كلاسيك"))
    if classic.get_attribute("aria-disabled") == "true":  # the page's story data from before the template
        page.wait_for_timeout(1500)
        page.reload()
    expect(classic).not_to_have_attribute("aria-disabled", "true")
    classic.click()
    page.get_by_role("radio", name=re.compile("مائي فاخر")).click()
    page.get_by_role("radio", name=re.compile("غلاف ورقي")).click()
    preview = page.get_by_role("link", name="جرّبوا المعاينة أولًا")
    expect(preview).to_have_attribute("href", re.compile(r"line=classic"))
    preview.click()
    page.wait_for_url("**/create**")
    assert query(page) == {
        "theme": "first-day",
        "line": "classic",
        "style": "watercolor",
        "format": "softcover",
    }

    step_is(page, 1, 8)
    expect(page.get_by_role("heading", name="من بطل الحكاية؟")).to_be_visible()
    for text in ("ماذا تحب", "ماذا يحب", "شيء مميز", "أي كتاب تريدون"):
        expect(page.get_by_text(text)).to_have_count(0)
    new_child(page, label="اسم البطل", name="ليلى", gender="f", age=5)
    expect(page.get_by_text("سيظهر العنوان هكذا:")).to_be_visible()
    page.get_by_role("button", name="متابعة").click()

    step_is(page, 2, 8)
    give_consent(page)
    step_is(page, 3, 8)
    upload_photo(page)
    step_is(page, 4, 8)  # drawn in the style picked on the story page: no style step
    approve_placeholder_character(page, "نعم، تشبه ليلى")

    step_is(page, 5, 8)
    expect(page.get_by_role("heading", name="الحكاية التي اخترتموها لـليلى")).to_be_visible()
    expect(page.get_by_text("+5 ₪ في قمرة كلاسيك")).to_be_visible()  # the dedication's price
    expect(page.get_by_text("ماذا تحب ليلى؟")).to_have_count(0)
    page.get_by_role("button", name="اكتبوا الحكاية").click()
    step_is(page, 6, 8)
    book = finish_preview(page)

    step_is(page, 7, 8)
    expect(page.get_by_role("heading", name="كتاب ليلى في «قمرة كلاسيك»")).to_be_visible()
    page.get_by_role("button", name="متابعة للطلب").click()

    expect(page.get_by_text("الخطوة 8 من 8 · اختياري")).to_be_visible()
    assert only_active_addons_with_pictures(page) <= STORY_ADDONS
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    items = call(page, "GET", "/api/store/cart")["items"]
    assert [(i["sku"], i["book_id"]) for i in items] == [("classic-soft-21", book)]
    expect(page.get_by_text("قمرة كلاسيك · غلاف ورقي · مائي فاخر")).to_be_visible()
    code = to_checkout_and_order(page)
    expect(page.get_by_text("قمرة كلاسيك · غلاف ورقي · مائي فاخر")).to_be_visible()
    placed = confirmed(page, code)
    assert placed["skus"] == ["classic-soft-21"] and placed["items"][0]["book_id"] == book


def test_magic_story_new_child(page: Page) -> None:
    """«قمرة سحري» from «ابدؤوا الحكاية» (`/create`): the type right after the child, the style step with real
    pages of each style, the drawn companion (skipped), and what the child likes asked on the story step
    (saved on the child): 12 steps, then the cart and the order."""
    page.goto(f"{BASE_URL}/ar/create")
    step_is(page, 1, 12)  # the type is not chosen yet: the longer flow is counted
    for text in ("ماذا تحب", "ماذا يحب", "شيء مميز"):
        expect(page.get_by_text(text)).to_have_count(0)
    new_child(page, label="اسم البطل", name="كرم", gender="m", age=5)
    page.get_by_role("button", name="متابعة").click()

    step_is(page, 2, 12)
    expect(page.get_by_role("heading", name="أي كتاب تريدون لـكرم؟")).to_be_visible()
    page.get_by_role("radio", name=re.compile("قمرة سحري")).click()
    page.get_by_role("button", name="متابعة").click()

    step_is(page, 3, 12)
    give_consent(page)
    step_is(page, 4, 12)
    upload_photo(page)

    step_is(page, 5, 12)
    expect(page.get_by_role("heading", name="كيف تحبون أن نرسم كرم؟")).to_be_visible()
    styles = page.get_by_role("radiogroup", name="أسلوب الرسم").get_by_role("radio")
    expect(styles).to_have_count(
        4
    )  # 3D, watercolor, cartoon, semi-realistic: never the black-and-white coloring
    for style in styles.all():
        expect(style.locator("img")).to_have_attribute("src", re.compile(r"^/samples/"))  # a real page
    styles.filter(has_text="سينمائي ثلاثي الأبعاد").click()
    gallery = page.get_by_role("region", name=re.compile("سينمائي ثلاثي الأبعاد"))
    expect(gallery.locator("img[src*='/samples/3d/']").first).to_be_visible()
    page.get_by_role("button", name="ارسموا شخصية كرم").click()

    step_is(page, 6, 12)
    approve_placeholder_character(page, "نعم، يشبه كرم")
    step_is(page, 7, 12)
    page.get_by_role("button", name="تخطّي — كتاب بدون صاحب").click()

    step_is(page, 8, 12)
    expect(page.get_by_role("heading", name="إلى أين يذهب كرم؟")).to_be_visible()
    likes = page.get_by_role("group", name=re.compile("ماذا يحب كرم؟"))
    expect(page.get_by_text("نضيف لمسة مما تختارونه إلى صفحة أو صفحتين من الحكاية.")).to_be_visible()
    likes.get_by_role("button", name="الفضاء").click()
    likes.get_by_role("button", name="الديناصورات").click()
    page.get_by_label(re.compile("شيء مميز عنه؟")).fill("عنده قطة اسمها لولو")
    page.get_by_role("button", name="اكتبوا الحكاية").click()

    step_is(page, 9, 12)
    book = finish_preview(page)
    step_is(page, 10, 12)
    page.get_by_role("button", name="الصفحات جاهزة").click()
    step_is(page, 11, 12)
    page.get_by_role("radio", name=re.compile("غلاف مقوّى")).click()
    page.get_by_role("button", name="متابعة للطلب").click()

    expect(page.get_by_text("الخطوة 12 من 12 · اختياري")).to_be_visible()
    only_active_addons_with_pictures(page)
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    items = call(page, "GET", "/api/store/cart")["items"]
    assert [(i["sku"], i["book_id"]) for i in items] == [("magic-hard-21", book)]
    expect(page.get_by_text("قمرة سحري · غلاف مقوّى · سينمائي ثلاثي الأبعاد")).to_be_visible()
    kids = call(page, "GET", "/api/create/children")
    assert kids[0]["interests"] == [
        "الفضاء",
        "الديناصورات",
        "عنده قطة اسمها لولو",
    ]  # the likes, then the note
    code = to_checkout_and_order(page)
    expect(page.get_by_text("قمرة سحري · غلاف مقوّى · سينمائي ثلاثي الأبعاد")).to_be_visible()
    placed = confirmed(page, code)
    assert placed["skus"] == ["magic-hard-21"] and placed["items"][0]["book_id"] == book


# ---- what is never offered ---------------------------------------------------------------------------------


def test_only_active_add_ons(page: Page) -> None:
    """The add-ons switched off by the owner (2026-10-07) and the black-and-white «دوسية التأسيس» are never
    offered: not in the catalog, not on the product page, not for any cart line."""
    catalog = call(page, "GET", "/api/store/catalog")
    assert not INACTIVE_ADDONS & {a["slug"] for a in catalog["addons"]}
    skus = [v["sku"] for p in catalog["products"] for v in p["variants"]]
    assert not [s for s in skus if "-bw-" in s], skus

    page.goto(f"{BASE_URL}/ar/workbooks/foundation-workbook")
    for level in ("KG1 · 4–5 سنوات", "KG2 · 5–6 سنوات"):
        pick(page, "المستوى", level)
        expect(page.get_by_role("radio", name="أبيض وأسود")).to_have_count(0)

    expected = {
        ("classic-soft-21", "first-day"): {"hardcover-upgrade", "family-voice", "extra-copy"},
        ("magic-hard-21", "graduation"): {"family-voice", "extra-copy"},
        ("islamic-v1-softcover", None): {"printed-parent-guide"},
        ("journey-s2-spiral", None): {"printed-answer-key"},
        ("family-wireo", None): set(),
        ("wb-kg1-v1-color-spiral", None): set(),
        ("islamic-v1-digital", None): set(),
    }
    for sku, theme in expected:
        call(page, "POST", "/api/store/cart/items", {"sku": sku, **({"theme": theme} if theme else {})})
    for item in call(page, "GET", "/api/store/cart")["items"]:
        offers = {
            a["slug"] for a in call(page, "GET", f"/api/store/cart/items/{item['id']}/addons")["addons"]
        }
        assert offers == expected[(item["sku"], item["theme"])], (item["sku"], offers)
