"""Addendum 9 §3 E2E on a phone: preview → «الإضافات» → «السلة» → address and cash on delivery."""

from decimal import Decimal

from e2e_flow import BASE_URL, call, checkout, order, preview_book, to_cart
from playwright.sync_api import Page, expect


def money(page: Page, text: str) -> None:
    expect(page.get_by_text(text, exact=True).first).to_be_visible()


def test_classic_softcover_with_two_add_ons_to_a_cod_order(page: Page) -> None:
    book = preview_book(page, name="ليان", gender="f", hijab=True, line="classic", theme="olive-season")
    page.goto(f"{BASE_URL}/ar/create?step=format&child={book['child_id']}&book={book['book_id']}")
    page.get_by_text("غلاف ورقي", exact=True).click()  # Create9: the format
    page.get_by_role("button", name="متابعة للطلب").click()

    expect(page.get_by_role("heading", name="بدكم تزيدوا الفرحة؟")).to_be_visible()  # AddOns
    # only what can be made is offered (owner's decision, 2026-10-07): no gift box, no coloring version
    expect(page.get_by_role("button", name="علبة هدية")).to_have_count(0)
    expect(page.get_by_role("button", name="نسخة تلوين")).to_have_count(0)
    page.get_by_role("button", name="ترقية إلى غلاف مقوّى").click()
    page.get_by_text("إضافات أخرى").click()
    page.get_by_role("button", name="أصوات العائلة").click()
    expect(page.get_by_text("الكتاب + إضافتان")).to_be_visible()
    money(page, "114 ₪")  # 69 + 30 + 15, the server's total
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    expect(page.get_by_text("ليان في موسم الزيتون")).to_be_visible()
    expect(page.get_by_text("قمرة كلاسيك · غلاف ورقي")).to_be_visible()  # the line and the format
    expect(page.get_by_text("نسخة رقمية مجانية مع المطبوع")).to_be_visible()  # free with a printed book
    money(page, "+15 ₪")
    page.get_by_role("link", name="متابعة للعنوان والدفع").click()

    expect(page.get_by_text("الخطوة الأخيرة: العنوان والدفع")).to_be_visible()  # no "n of 12" any more
    code = checkout(page)
    placed = order(page, code)
    assert placed["skus"] == ["classic-soft-21"]
    assert {"hardcover-upgrade", "family-voice"} <= set(placed["addons"][0])
    assert Decimal(placed["total"]) == Decimal("134")  # 114 + 20 delivery to البيرة
    expect(page.get_by_text(code).first).to_be_visible()


def test_magic_hardcover_to_the_cart(page: Page) -> None:
    book = preview_book(page, name="كرم", gender="m", line="magic", theme="graduation")
    page.goto(f"{BASE_URL}/ar/create?step=format&child={book['child_id']}&book={book['book_id']}")
    page.get_by_text("غلاف مقوّى", exact=True).click()
    page.get_by_role("button", name="متابعة للطلب").click()

    expect(page.get_by_role("heading", name="بدكم تزيدوا الفرحة؟")).to_be_visible()
    expect(page.get_by_role("button", name="ترقية إلى غلاف مقوّى")).to_have_count(0)  # already hardcover
    money(page, "139 ₪")
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    expect(page.get_by_text("قمرة سحري · غلاف مقوّى")).to_be_visible()
    expect(page.get_by_text("شخصية كرم جاهزة")).to_be_visible()  # an approved character: the cross-sell
    cart = call(page, "GET", "/api/store/cart")
    assert cart["count"] == 1 and cart["items"][0]["sku"] == "magic-hard-21"


def test_the_gift_toggle_and_card_message(page: Page) -> None:
    book = preview_book(page, name="ليان", hijab=True, theme="first-day")
    to_cart(page, book, "classic-soft-21")
    page.goto(f"{BASE_URL}/ar/cart")
    saved = lambda r: "/api/store/cart/gift" in r.url and r.request.method == "PUT"  # noqa: E731
    with page.expect_response(saved):
        page.get_by_role("button", name="هذا الطلب هدية").click()
    note = page.get_by_label("رسالتكم على البطاقة")
    expect(note).to_have_attribute("maxlength", "200")
    with page.expect_response(saved):
        note.fill("كل عام وأنتِ بطلة حكايتنا يا ليان.\nمن ماما")
        note.blur()
    page.reload()  # kept by the server, not the browser
    expect(page.get_by_role("button", name="هذا الطلب هدية")).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_label("رسالتكم على البطاقة")).to_have_value(
        "كل عام وأنتِ بطلة حكايتنا يا ليان.\nمن ماما"
    )
    page.get_by_role("link", name="متابعة للعنوان والدفع").click()
    expect(page.get_by_role("heading", name="إلى أين نوصل الهدية؟")).to_be_visible()

    placed = order(page, checkout(page, name="جدة ليان"))
    assert placed["gift"] is True and placed["gift_message"] == "كل عام وأنتِ بطلة حكايتنا يا ليان.\nمن ماما"


def test_a_sibling_bundle_with_a_coupon(page: Page) -> None:
    layan = preview_book(page, name="ليان", hijab=True, line="classic", theme="first-day")
    karam = preview_book(page, name="كرم", gender="m", line="magic", theme="graduation")
    to_cart(page, layan, "classic-soft-21")
    to_cart(page, karam, "magic-hard-21")
    code = call(page, "POST", "/api/e2e/coupons", {"kind": "percent", "value": "10"})["code"]
    page.goto(f"{BASE_URL}/ar/cart")
    expect(page.get_by_text("خصم باقة الإخوة (20%)")).to_be_visible()  # 2 children: the siblings bundle
    money(page, "−41.60 ₪")  # 20% of 69 + 139
    page.get_by_placeholder("كود خصم أو بطاقة هدية").fill(code.lower())
    page.get_by_role("button", name="تطبيق").click()
    expect(page.get_by_text(f"كود الخصم {code}").first).to_be_visible()
    money(page, "−16.64 ₪")  # 10% of what is left (166.40)
    money(page, "149.76 ₪")
    page.get_by_role("link", name="متابعة للعنوان والدفع").click()

    placed = order(page, checkout(page))
    assert Decimal(placed["discount"]) == Decimal("58.24")  # the bundle and the coupon
    assert placed["pricing"]["bundle"] == "siblings" and placed["pricing"]["coupon"] == code
    assert Decimal(placed["total"]) == Decimal("169.76")  # 149.76 + 20 delivery


def test_activity_lines_say_what_they_print_and_offer_their_add_ons(page: Page) -> None:
    """docs/plans/order-flows.md §c.9: an activity line is its cover's title with the child's name, the
    variant and the English name; its add-ons are offered under it, by its cart line (never before)."""
    child = preview_book(page, name="ضحى")["child_id"]  # consent and an approved character, no AI
    call(
        page,
        "POST",
        "/api/shop/workbooks/cart",
        {"sku": "wb-kg2-v1-color-spiral", "child_id": child, "name_en": "Duha"},
    )
    call(page, "POST", "/api/shop/workbooks/cart", {"sku": "islamic-v1-softcover", "child_id": child})
    page.goto(f"{BASE_URL}/ar/cart")

    workbook = page.locator("article").filter(has_text="دوسية ضحى")
    expect(workbook.get_by_text("KG2 · الجزء الأول · ملوّن · مطبوع")).to_be_visible()
    expect(workbook.get_by_text("الاسم بالإنجليزية: Duha")).to_be_visible()
    expect(workbook.get_by_text("إضافات لهذا الكتاب")).to_have_count(0)  # nothing it can be given today
    islamic = page.locator("article").filter(has_text="قلبي يعرف الله · ضحى")
    expect(islamic.get_by_text("المجلد الأول · مطبوع")).to_be_visible()

    islamic.get_by_text("إضافات لهذا الكتاب").click()
    guide = islamic.get_by_role("button").filter(has_text="+15 ₪")  # the printed parent guide
    with page.expect_response(lambda r: r.url.endswith("/addons") and r.request.method == "PUT"):
        guide.click()
    expect(guide).to_have_attribute("aria-pressed", "true")
    money(page, "+15 ₪")  # the line's add-on, and the cart's totals again from the server
    cart = call(page, "GET", "/api/store/cart")
    line = next(i for i in cart["items"] if i["line"] == "islamic")
    assert [a["slug"] for a in line["addons"]] == ["printed-parent-guide"]
    assert {"gift-box", "sticker-sheet", "crayon-kit"}.isdisjoint(
        a["slug"] for i in cart["items"] for a in i["addons"]
    )

    page.get_by_role("link", name="متابعة للعنوان والدفع").click()
    expect(page.get_by_text("دوسية ضحى")).to_be_visible()  # the order summary says the same
    expect(page.get_by_text("قلبي يعرف الله · ضحى")).to_be_visible()
    expect(page.get_by_text("المجلد الأول · مطبوع · مع إضافة")).to_be_visible()
