"""Every customer email ends with how to reach us: the email, WhatsApp and the phone (the owner's numbers)."""

from typing import Any

from qamra_worker.jobs.notify import base_values
from qamra_worker.notify.templates import render

BASE = "https://qamra.test"
SETTINGS = {
    "support_email": "info@qamra.app",
    "support_whatsapp": "+972595870228",
    "support_phone": "+970595870228",
}
LTR, POP = "\u2066", "\u2069"  # the isolates around each number


def _values(lang: str, settings: dict[str, Any]) -> dict[str, Any]:
    order = {"name": "أم سلمى", "code": "QM-1", "total": "139 ₪", "track_url": BASE}
    return {**base_values(settings, lang), **order}


def test_the_footer_has_the_email_whatsapp_and_phone_with_the_numbers_left_to_right() -> None:
    ar = render("order_placed", "ar", _values("ar", SETTINGS))
    whatsapp, phone = f"{LTR}+972 59 587 0228{POP}", f"{LTR}+970 59 587 0228{POP}"
    contact = f"للمساعدة: info@qamra.app · واتساب {whatsapp} · هاتف {phone}"
    assert contact in ar.text and contact in ar.html
    en = render("order_placed", "en", _values("en", SETTINGS))
    assert f"Need help? info@qamra.app · WhatsApp {whatsapp} · Phone {phone}" in en.text


def test_only_what_the_admin_set_is_shown() -> None:
    out = render(
        "order_placed", "ar", _values("ar", {"support_email": "", "support_whatsapp": "+972595870228"})
    )
    assert f"للمساعدة: واتساب {LTR}+972 59 587 0228{POP}" in out.text
    assert "هاتف" not in out.text
    bare = render("order_placed", "en", _values("en", {}))
    assert "Need help?" not in bare.text
