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

    expect(page.get_by_role("heading", name="بدك تزيد الفرحة؟")).to_be_visible()  # AddOns
    page.get_by_role("button", name="علبة هدية").click()
    page.get_by_role("button", name="نسخة تلوين").click()
    expect(page.get_by_text("الكتاب + 2 إضافات")).to_be_visible()
    money(page, "109 ₪")  # 69 + 15 + 25, the server's total
    page.get_by_role("button", name="أضف للسلة").click()

    page.wait_for_url("**/cart")
    expect(page.get_by_text("ليان في موسم الزيتون")).to_be_visible()
    expect(page.get_by_text("نسخة رقمية مجانية مع المطبوع")).to_be_visible()  # free with a printed book
    money(page, "+25 ₪")
    page.get_by_role("link", name="متابعة للعنوان والدفع").click()

    code = checkout(page)
    placed = order(page, code)
    assert placed["skus"] == ["classic-soft-21"]
    assert {"gift-box", "coloring-version"} <= set(placed["addons"][0])
    assert Decimal(placed["total"]) == Decimal("129")  # 109 + 20 delivery to البيرة
    expect(page.get_by_text(code).first).to_be_visible()


def test_magic_hardcover_to_the_cart(page: Page) -> None:
    book = preview_book(page, name="كرم", gender="m", line="magic", theme="graduation")
    page.goto(f"{BASE_URL}/ar/create?step=format&child={book['child_id']}&book={book['book_id']}")
    page.get_by_text("غلاف مقوّى", exact=True).click()
    page.get_by_role("button", name="متابعة للطلب").click()

    expect(page.get_by_role("heading", name="بدك تزيد الفرحة؟")).to_be_visible()
    expect(page.get_by_role("button", name="ترقية إلى غلاف مقوّى")).to_have_count(0)  # already hardcover
    money(page, "139 ₪")
    page.get_by_role("button", name="أضف للسلة").click()

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
    note = page.get_by_label("رسالتك على البطاقة")
    expect(note).to_have_attribute("maxlength", "200")
    with page.expect_response(saved):
        note.fill("كل عام وأنتِ بطلة حكايتنا يا ليان.\nمن ماما")
        note.blur()
    page.reload()  # kept by the server, not the browser
    expect(page.get_by_role("button", name="هذا الطلب هدية")).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_label("رسالتك على البطاقة")).to_have_value(
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
