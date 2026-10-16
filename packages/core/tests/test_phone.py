"""Phone numbers as people type them on Arabic keyboards (Tareq, 2026-10-16: checkout kept refusing ٠٥٩٩…)."""

import pytest

from qamra_core.app_settings import REGISTRY, SettingError, validate
from qamra_core.phone import ascii_digits, normalize_phone, phone_key

LRM, RLM, NBSP = "\u200e", "\u200f", "\u00a0"


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("0599123456", "0599123456"),
        ("٠٥٩٩١٢٣٤٥٦", "0599123456"),  # Arabic-Indic digits
        ("۰۵۹۹۱۲۳۴۵۶", "0599123456"),  # Persian (Extended Arabic-Indic) digits
        ("٠٥٩٩-١٢٣-٤٥٦", "0599123456"),
        ("059 912 3456", "0599123456"),
        ("(059) 912-3456", "0599123456"),
        ("059.912.3456", "0599123456"),
        (f"059{NBSP}912 3456", "0599123456"),
        ("599123456", "0599123456"),  # the zero Excel drops comes back
        ("0569123456", "0569123456"),
        ("+970599123456", "+970599123456"),
        ("+970 59 912 3456", "+970599123456"),
        ("+972 59 912 3456", "+972599123456"),  # 970 or 972: kept as typed
        ("00970599123456", "+970599123456"),
        ("00972 59 912 3456", "+972599123456"),
        ("970599123456", "+970599123456"),
        ("٩٧٠٥٩٩١٢٣٤٥٦", "+970599123456"),
        ("+970 0599 123 456", "+970599123456"),  # the trunk zero after the country code
        (f"{LRM}+970599123456{RLM}", "+970599123456"),  # direction marks from a copy-paste
        ("970599123456+", "+970599123456"),  # the plus typed last on a right-to-left line
        ("02-2981234", "022981234"),  # a landline
        ("+970 2 298 1234", "+97022981234"),
        ("0791234567", "0791234567"),  # Jordan
        ("+962 79 123 4567", "+962791234567"),
        ("+1 415 523 8886", "+14155238886"),  # abroad
    ],
)
def test_numbers_are_accepted_and_normalized(typed: str, stored: str) -> None:
    assert normalize_phone(typed) == stored


@pytest.mark.parametrize(
    "typed",
    [
        "",
        "   ",
        "abc",
        "1234567",
        "05991234",
        "059912345678",
        "+970 12",
        "+970 1234 56789",
        "05٩٩x123456",
        "++970599",
    ],
)
def test_what_is_not_a_phone_number(typed: str) -> None:
    assert normalize_phone(typed) is None


def test_one_number_in_every_form_has_one_key() -> None:
    keys = {phone_key(p) for p in ("0599123456", "+970599123456", "+972 59 912 3456", "٠٥٩٩١٢٣٤٥٦")}
    assert keys == {"599123456"}
    assert ascii_digits("سلمى ٥ سنوات ۷") == "سلمى 5 سنوات 7"


def test_admin_phone_settings_take_arabic_digits_and_store_the_normal_form() -> None:
    d = REGISTRY["support_phone"]
    assert validate(d, "٠٥٩٥٨٧٠٢٢٨") == "0595870228"
    assert validate(d, "+970 59 587 0228") == "+970595870228"
    with pytest.raises(SettingError):
        validate(d, "12345")
