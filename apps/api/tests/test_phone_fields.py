"""Phone numbers typed on Arabic keyboards, and 422s that say which field is wrong (Tareq, 2026-10-16:
checkout kept answering «بعض البيانات غير صحيحة» to ٠٥٩٩… and never said which field)."""

import time
from datetime import UTC, datetime

import pyotp
import pytest
from api_helpers import complete_cart, make_admin
from httpx import AsyncClient
from portal_helpers import signup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.auth import mfa
from qamra_api.errors import error_body, field_message, validation_details
from qamra_api.portal.importer import check_row
from qamra_api.seed_store import seed_store
from qamra_core.db.models import Lead, Order, Organization, OrgStatus
from qamra_core.db.store import Coupon, CouponKind

CHECKOUT = {
    "name": "أم ليان",
    "phone": "٠٥٩١٢٣٤٥٦٧",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "ضضضضضضضضض",  # the owner's own test: long enough is enough, no "gibberish" check
    "accept_terms": True,
}
PHONE_AR = {
    "ar": "رقم الجوال غير صحيح. اكتبوه مثل 0599123456",
    "en": "This mobile number isn't valid. Write it like 0599123456",
}


@pytest.fixture(autouse=True)
async def _catalog(adb: AsyncSession) -> None:
    await seed_store(adb)


async def _checkout(client: AsyncClient, adb: AsyncSession, **body: object) -> dict:  # type: ignore[type-arg]
    r = await client.post("/api/store/cart/items", json={"sku": "classic-soft-21"})
    assert r.status_code == 201, r.text
    await complete_cart(adb)
    r = await client.post("/api/store/checkout", json={**CHECKOUT, **body})
    return {"http": r.status_code, **r.json()}


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("٠٥٩١٢٣٤٥٦٧", "0591234567"),  # Arabic-Indic
        ("۰۵۹۱۲۳۴۵۶۷", "0591234567"),  # Persian
        ("059-123 4567", "0591234567"),
        ("+970 59 123 4567", "+970591234567"),
        ("00972591234567", "+972591234567"),
        ("+٩٧٢ ٥٩ ١٢٣ ٤٥٦٧", "+972591234567"),
    ],
)
async def test_checkout_takes_arabic_digits_and_stores_one_form(
    client: AsyncClient, adb: AsyncSession, typed: str, stored: str
) -> None:
    placed = await _checkout(client, adb, phone=typed)
    assert placed["http"] == 201, placed
    order = (await adb.execute(select(Order).where(Order.code == placed["code"]))).scalar_one()
    assert order.phone == stored and order.shipping["address"] == "ضضضضضضضضض"
    # tracking finds it with the number in any of its forms
    for form in ("٠٥٩١٢٣٤٥٦٧", "+970591234567", "0591234567"):
        r = await client.get(f"/api/store/orders/{placed['code']}", params={"phone": form})
        assert r.status_code == 200, (form, r.text)


async def test_checkout_marks_each_wrong_field(client: AsyncClient, adb: AsyncSession) -> None:
    r = await _checkout(client, adb, phone="٠٥٩١٢", address="بيت", name="", accept_terms=None)
    assert r["http"] == 422
    error = r["error"]
    assert error["code"] == "invalid_input"
    assert error["details"]["fields"] == ["accept_terms", "address", "name", "phone"]  # the list, as before
    marked = error["details"]["field_errors"]
    assert marked["phone"] == PHONE_AR
    assert marked["address"]["ar"] == "اكتبوا العنوان بتفصيل أكثر (٥ أحرف على الأقل)."
    assert marked["name"]["ar"] == "اكتبوا الاسم." and marked["accept_terms"]["ar"].startswith("وافقوا")
    assert next(iter(marked)) == "name"  # in the form's order
    assert error["message"] == marked["name"]  # a page that marks nothing still says what is wrong


async def test_checkout_city_zone_and_terms_errors_name_their_field(
    client: AsyncClient, adb: AsyncSession
) -> None:
    r = await _checkout(client, adb, city="عمّان")  # not a West Bank city
    assert r["http"] == 422 and r["error"]["code"] == "unknown_city"
    assert r["error"]["details"]["fields"] == ["city"]
    assert "ليست ضمن منطقة التوصيل" in r["error"]["details"]["field_errors"]["city"]["ar"]
    r = await _checkout(client, adb, zone="amman", city="عمّان")
    assert r["http"] == 404 and r["error"]["details"]["fields"] == ["zone"]
    r = await _checkout(client, adb, accept_terms=False)
    assert r["http"] == 422 and r["error"]["code"] == "terms_required"
    assert r["error"]["details"]["field_errors"]["accept_terms"]["ar"] == r["error"]["message"]["ar"]


async def test_a_first_order_coupon_knows_the_number_in_any_form(
    client: AsyncClient, adb: AsyncSession
) -> None:
    adb.add(Coupon(code="EID10", kind=CouponKind.percent, value=10, first_order_only=True))
    await adb.commit()
    await client.post("/api/store/cart/items", json={"sku": "classic-soft-21"})
    await client.put("/api/store/cart/coupon", json={"code": "EID10"})
    await complete_cart(adb)
    r = await client.post("/api/store/checkout", json={**CHECKOUT, "phone": "0591234567"})
    assert r.status_code == 201, r.text
    await client.post("/api/store/cart/items", json={"sku": "classic-soft-21"})
    await client.put("/api/store/cart/coupon", json={"code": "EID10"})
    await complete_cart(adb)
    r = await client.post("/api/store/checkout", json={**CHECKOUT, "phone": "+٩٧٢ ٥٩١ ٢٣٤ ٥٦٧"})
    assert r.status_code == 422 and r.json()["error"]["details"]["problem"] == "first_order_only"


async def test_kindergarten_forms_take_arabic_digits(client: AsyncClient, adb: AsyncSession) -> None:
    lead = {
        "org_name": "روضة الفراشات",
        "contact_name": "أ. منى",
        "phone": "۰۵۹۹ ۱۲۳ ۴۵۶",
        "children_count": "٢٥",
    }
    r = await client.post("/api/leads", json=lead)
    assert r.status_code == 201, r.text
    stored = (await adb.execute(select(Lead))).scalar_one()
    assert stored.phone == "0599123456" and stored.children_count == 25

    form = {"org_name": "روضة الأمل", "contact_name": "أ. سلمى", "phone": "٠٥٩٨-٧٦٥-٤٣٢", "quantity": "٤٠"}
    r = await client.post("/api/leads/family-quote", data=form)
    assert r.status_code == 201, r.text
    quote = (await adb.execute(select(Lead).where(Lead.kind == "family_quote"))).scalar_one()
    assert quote.phone == "0598765432" and quote.details["quantity"] == 40
    r = await client.post("/api/leads/family-quote", data={**form, "phone": "123"})
    assert r.status_code == 422 and r.json()["error"]["details"]["field_errors"] == {"phone": PHONE_AR}
    r = await client.post("/api/leads/family-quote", data={**form, "quantity": "3"})
    marked = r.json()["error"]["details"]["field_errors"]
    assert r.status_code == 422 and marked["quantity"]["ar"] == "العدد يجب أن يكون 10 على الأقل."

    r = await client.post("/api/portal/signup", json={**signup(), "phone": "+٩٧٠ ٥٩ ١١١ ٢٢٢٢"})
    assert r.status_code == 201, r.text
    org = (await adb.execute(select(Organization))).scalar_one()
    assert org.phone == "+970591112222"
    org.status, org.approved_at = OrgStatus.approved, datetime.now(UTC)
    await adb.commit()
    r = await client.patch("/api/portal/org", json={"phone": "٠٥٩٩"})
    assert r.status_code == 422 and r.json()["error"]["details"]["field_errors"]["phone"] == PHONE_AR
    r = await client.patch("/api/portal/org", json={"phone": "٠٢-٢٩٨١٢٣٤"})  # a landline
    assert r.status_code == 200 and r.json()["org"]["phone"] == "022981234"


async def test_the_school_list_takes_arabic_digits_and_excel_numbers() -> None:
    base = {"name": "جنى", "gender": "بنت", "age": "5"}
    assert check_row({**base, "phone": "٠٥٩٩-١٢٣-٤٥٦"}, 2, today=2026).phone == "0599123456"
    assert check_row({**base, "phone": "599123456"}, 2, today=2026).phone == "0599123456"  # Excel's number
    row = check_row({**base, "phone": "٠٥٩٩"}, 2, today=2026)
    assert not row.ok and "رقم الجوال" in row.errors[0]["ar"]


async def test_admin_settings_take_arabic_digits_and_mark_a_wrong_number(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await make_admin(client, adb)
    r = await client.put("/api/admin/settings", json={"values": {"support_phone": "+٩٧٠ ٥٩ ٥٨٧ ٠٢٢٨"}})
    assert r.status_code == 200, r.text
    contact = next(g for g in r.json()["groups"] if g["id"] == "contact")
    assert next(s for s in contact["settings"] if s["key"] == "support_phone")["value"] == "+970595870228"
    r = await client.put("/api/admin/settings", json={"values": {"support_whatsapp": "٥٩٥"}})
    assert r.status_code == 422 and r.json()["error"]["details"]["field_errors"] == {
        "support_whatsapp": PHONE_AR
    }


async def test_sign_up_marks_its_fields(client: AsyncClient) -> None:
    r = await client.post("/api/auth/register", json={"email": "x", "password": "short", "full_name": " "})
    marked = r.json()["error"]["details"]["field_errors"]
    assert r.status_code == 422 and set(marked) == {"email", "full_name"}
    assert marked["email"]["ar"].startswith("البريد الإلكتروني غير صحيح")
    r = await client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "short", "full_name": "أم سلمى"}
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "weak_password"
    assert r.json()["error"]["details"]["fields"] == ["password"]


def test_two_factor_codes_typed_in_arabic_digits() -> None:
    secret = pyotp.random_base32()
    now = time.time()
    code = pyotp.TOTP(secret).at(now)
    arabic = code.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
    assert mfa.match_step(secret, arabic, None, now) is not None


def test_messages_by_field_and_kind() -> None:
    errors = [
        {"type": "missing", "loc": ("body", "phone")},
        {"type": "string_too_short", "loc": ("body", "address"), "input": "بيت", "ctx": {"min_length": 5}},
        {"type": "less_than_equal", "loc": ("body", "items", 0, "qty"), "input": 99, "ctx": {"le": 50}},
        {"type": "string_too_long", "loc": ("body", "notes"), "input": "x" * 600},
        {"type": "json_invalid", "loc": ("body",)},  # not about a field
    ]
    details = validation_details(errors)
    assert details["fields"] == ["address", "items.0.qty", "notes", "phone"]
    assert details["field_errors"]["phone"]["ar"] == "اكتبوا رقم الجوال."
    assert details["field_errors"]["items.0.qty"]["en"] == "The number can't be more than 50."
    assert details["field_errors"]["notes"] == field_message("notes", "too_long")
    # a 422 without field messages keeps the generic text, as before
    assert error_body("invalid_input", {"fields": ["x"]})["error"]["message"]["ar"].startswith("بعض البيانات")
