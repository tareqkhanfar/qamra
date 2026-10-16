"""Phone numbers as people type them, in one place (API forms, the school's lists, admin settings).

People in Palestine and Jordan type on Arabic keyboards: ٠٥٩٩١٢٣٤٥٦ (Arabic-Indic digits) or ۰۵۹۹۱۲۳۴۵۶
(the Persian/Urdu ones), with spaces, dashes, dots or brackets, sometimes with invisible direction marks from
a copy-paste. `normalize_phone` turns all of that into one stored form:

- local numbers keep their leading zero, digits only: 0599123456 (mobile, 05/07 + 8 digits), 022981234
  (landline, 0 + area code + 7 digits). A bare 599123456 (the zero dropped, Excel does this) gets it back;
- international numbers start with "+": 00970… and 970… become +970…, and the country code is kept as typed
  (970 and 972 are both used for the same Palestinian mobiles). A zero typed after the country code
  (+970 0599…) is dropped;
- other countries' numbers are kept in international form when they look like one (+ and 8–15 digits).

Anything else is not a phone number (None). `phone_key` is what two forms of one number share: the last
nine digits.
"""

import re

# Arabic-Indic (U+0660–0669) and Extended Arabic-Indic (U+06F0–06F9) digits → ASCII
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# what people put between the digits: spaces of every width, dashes, dots, slashes, brackets, and the
# invisible direction marks a right-to-left page adds around a number
_SEPARATORS = re.compile(r"[\s\u00a0\u2000-\u200f\u2028-\u202f\u2066-\u2069\ufeff().\-\u2010-\u2015\u2212/_]")
_LOCAL = re.compile(r"^0(?:[57]\d{8}|[2-9]\d{7})$")
# national numbers after +970 / +972 / +962 (no trunk zero): mobiles 9 digits, landlines 8
_NATIONAL = {
    "970": re.compile(r"^(?:5\d{8}|[2-9]\d{7})$"),
    "972": re.compile(r"^(?:[57]\d{8}|[2-9]\d{7})$"),
    "962": re.compile(r"^(?:7\d{8}|[2-9]\d{7})$"),
}
_INTERNATIONAL = re.compile(r"^[1-9]\d{7,14}$")


def ascii_digits(value: str) -> str:
    """Arabic-Indic and Persian digits as ASCII digits; everything else unchanged."""
    return value.translate(_DIGITS)


def normalize_phone(value: str | None) -> str | None:
    """The stored form of a phone number (see the module doc), or None when it isn't one."""
    if not value:
        return None
    text = _SEPARATORS.sub("", ascii_digits(value)).replace("＋", "+")
    if text.endswith("+") and not text.startswith("+"):  # "970599…+" from a right-to-left paste
        text = "+" + text[:-1]
    plus = text.startswith("+")
    digits = text[1:] if plus else text
    if not digits.isascii() or not digits.isdigit():
        return None
    if not plus and digits.startswith("00"):
        plus, digits = True, digits[2:]
    if plus:
        return _international(digits)
    if _LOCAL.match(digits):
        return digits
    if len(digits) == 9 and digits[0] in "57":  # the leading zero dropped: 599123456
        return "0" + digits
    if digits[:3] in _NATIONAL and len(digits) >= 11:  # 970599123456 without the +
        return _international(digits)
    return None


def _international(digits: str) -> str | None:
    country = digits[:3]
    if country in _NATIONAL:
        national = digits[3:]
        if national.startswith("0"):  # +970 0599… : the trunk zero is not dialled after the country code
            national = national[1:]
        return f"+{country}{national}" if _NATIONAL[country].match(national) else None
    return f"+{digits}" if _INTERNATIONAL.match(digits) else None


def phone_key(value: str | None) -> str:
    """The last nine digits: the same for 0599123456, +970599123456 and +972599123456."""
    digits = re.sub(r"\D", "", ascii_digits(value or ""))
    return digits[-9:]
