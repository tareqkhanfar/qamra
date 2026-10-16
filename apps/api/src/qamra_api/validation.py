"""Shared input checks.

Every phone field goes through `check_phone` (or the `Phone` / `OptionalPhone` types): Arabic-Indic and
Persian digits, spaces, dashes and brackets are accepted and the number is stored in one normalized form
(`qamra_core.phone`). A wrong number is a `value_error` on the field, which the 422 handler turns into
«رقم الجوال غير صحيح…» under that field (`errors.field_errors`).
"""

from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field

from qamra_core.phone import ascii_digits, normalize_phone


def check_phone(value: str) -> str:
    """The normalized number, or ValueError("empty") / ValueError("invalid phone")."""
    if not value.strip():
        raise ValueError("empty")
    phone = normalize_phone(value)
    if phone is None:
        raise ValueError("invalid phone")
    return phone


def _optional_phone(value: str | None) -> str | None:
    return check_phone(value) if value is not None and value.strip() else None


def _ascii_number(value: object) -> object:
    """«٣٠» typed on an Arabic keyboard is 30."""
    return ascii_digits(value).strip() if isinstance(value, str) else value


# raw input may carry spaces, dashes and direction marks; the stored form is at most 16 characters
Phone = Annotated[str, Field(max_length=40), AfterValidator(check_phone)]
OptionalPhone = Annotated[str | None, Field(default=None, max_length=40), AfterValidator(_optional_phone)]
# a whole number that may arrive as text with Arabic digits (multipart forms, query strings)
AsciiDigits = BeforeValidator(_ascii_number)
