"""What a book's «عن قمرة» page and back cover print (`qamra_pdf.imprint`), for every render job.

The code is the book's own (`Book.code`, `qamra_core.book_codes`); the contacts are the admin's «التواصل
والمعلومات» settings (the owner's numbers, info@qamra.app, the Facebook and Instagram pages), with the
owner's values when a setting is empty; the month is the month the book was created.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from sqlalchemy.orm import Session

from qamra_core.db.models import Book, Child, Gender
from qamra_pdf.imprint import Contact, Imprint, product_name
from qamra_worker.settings import get_settings

DEFAULT = Contact()


def contact_from(values: dict[str, Any], domain: str) -> Contact:
    def pick(key: str, fallback: str) -> str:
        value = values.get(key)
        return str(value).strip() if value and str(value).strip() else fallback

    return Contact(
        phone=pick("support_phone", DEFAULT.phone),
        whatsapp=pick("support_whatsapp", DEFAULT.whatsapp),
        email=pick("support_email", DEFAULT.email),
        domain=domain or DEFAULT.domain,
        facebook=pick("facebook_url", DEFAULT.facebook),
        instagram=pick("instagram_url", DEFAULT.instagram),
    )


def contact(db: Session) -> Contact:
    from qamra_worker.jobs.books import resolved_settings  # the jobs import this module

    try:
        values = dict(resolved_settings(db).values)
    except Exception:  # settings that cannot be read never stop a book: the owner's values
        values = {}
    return contact_from(values, get_settings().brand_domain)


def book_imprint(
    db: Session,
    book: Book,
    child: Child,
    *,
    line: str,
    part: str = "",
    lang: Literal["ar", "en"] = "ar",
) -> Imprint:
    """The imprint of `book` (`line`: the store's product line, `part`: its volume, stage or story title)."""
    made = book.created_at.date() if book.created_at else date.today()
    return Imprint(
        code=book.code,
        child_name=child.first_name,
        gender="f" if child.gender == Gender.f else "m",
        product=product_name(line, lang),
        part=part,
        lang=lang,
        made_on=made,
        contact=contact(db),
    )
