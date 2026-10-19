"""Book codes: a short, human-friendly code for every book of every product («QB-7K4M2»).

The owner tells books apart by it, e.g. two orders for two children both called يوسف. It is printed on the
book's «عن قمرة» page and small on its back cover, shown in the admin (books, approval queue, orders, print
batches, packing slips, invoices), on the parent's order page and in the emails, and the QR on the info page
opens `https://{domain}/b/{code}`.

Format: "QB-" + 5 symbols from `ALPHABET` (24 symbols: the digits 2–9 and 16 capital letters). There is no
0/O, 1/I/L, and none of the pairs a phone call or a quick glance mixes up (B/8, G/6, S/5, Z/2, Q/O, U/V), so
it is easy to read aloud and to type. 24⁵ ≈ 8 million codes; no check digit (the owner's call: optional),
a mistyped code simply finds no book.

Every code ever given out is kept in `book_codes` (a registry with no link to the book), so a code is never
reused, not even after a family deletes all its data and its books with it. A new `Book` gets its code in
the session's `before_flush` (`assign_codes`), whichever code path creates it: a random code is claimed
with `INSERT … ON CONFLICT DO NOTHING RETURNING` and a taken one is simply drawn again (`claim_code`).
"""

from __future__ import annotations

import re
import secrets
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, event, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from qamra_core.db.models import Book, BookCode, OrderItem

PREFIX = "QB-"
ALPHABET = "23456789ACDEFHJKMNPRTWXY"
LENGTH = 5
MAX_ATTEMPTS = 25  # 8 million codes: a collision is rare, 25 in a row never happens
CODE_RE = re.compile(rf"^QB-[{ALPHABET}]{{{LENGTH}}}$")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_SEPARATORS = re.compile(r"[\s\-_‐-―.·/]+")


class CodeExhausted(RuntimeError):
    """No free code was found after `MAX_ATTEMPTS` draws (never expected)."""


def generate(choice: Callable[[str], str] = secrets.choice) -> str:
    """A random code in the book format (not yet claimed)."""
    return PREFIX + "".join(choice(ALPHABET) for _ in range(LENGTH))


def is_code(text: str) -> bool:
    return bool(CODE_RE.fullmatch(text))


def normalize(text: str | None) -> str | None:
    """The code as typed by a person («qb 7k4m2», «7K4M2», «QB-٧K٤M٢») in its printed form, or None when it
    cannot be a book code. Letters the alphabet leaves out are never guessed."""
    if not text:
        return None
    raw = _SEPARATORS.sub("", text.translate(_DIGITS)).upper()
    if raw.startswith("QB") and len(raw) == len("QB") + LENGTH:
        raw = raw[2:]
    code = PREFIX + raw
    return code if is_code(code) else None


def claim_code(conn: Connection, draw: Callable[[], str] = generate) -> str:
    """A code nobody has had, recorded in the registry inside the caller's transaction."""
    for _ in range(MAX_ATTEMPTS):
        code = draw()
        if conn.dialect.name == "postgresql":
            stmt = pg_insert(BookCode).values(code=code).on_conflict_do_nothing().returning(BookCode.code)
            if conn.execute(stmt).scalar_one_or_none() == code:
                return code
            continue
        if conn.execute(BookCode.__table__.select().where(BookCode.code == code)).first() is None:
            conn.execute(insert(BookCode).values(code=code))
            return code
    raise CodeExhausted(f"no free book code after {MAX_ATTEMPTS} attempts")


# the draw `assign_codes` uses: tests swap it to force a collision
_draw: Callable[[], str] = generate


def set_draw(draw: Callable[[], str] | None) -> None:
    """Replace the random draw (tests); None restores it."""
    global _draw
    _draw = draw or generate


@event.listens_for(Session, "before_flush")
def assign_codes(session: Session, _ctx: Any, _instances: Any) -> None:
    """Every new book gets its code before it is written (all products, every code path)."""
    for obj in list(session.new):
        if isinstance(obj, Book) and not obj.code:
            obj.code = claim_code(session.connection(), _draw)


def book_url(domain: str, code: str) -> str:
    """What the info page's QR opens: Qamra's contact page for this book (apps/web `[locale]/b/[code]`)."""
    host = (domain or "qamra.app").strip().removeprefix("https://").removeprefix("http://").strip("/")
    return f"https://{host or 'qamra.app'}/b/{code}"


# ---- finding books by code, and the codes of an order's lines ----------------------------------------------


def code_filter(text: str | None) -> ColumnElement[bool] | None:
    """A filter on `Book.code` for what staff typed: the exact code when it reads as one («qb 7k4m2»,
    «7K4M2»), else a part of a code (3+ letters or digits of the alphabet, e.g. «7K4»); None otherwise."""
    code = normalize(text)
    if code:
        return Book.code == code
    raw = _SEPARATORS.sub("", (text or "").translate(_DIGITS)).upper().removeprefix("QB")
    if len(raw) >= 3 and all(c in ALPHABET for c in raw):
        return Book.code.like(f"%{raw}%")
    return None


@dataclass(frozen=True)
class BookRef:
    """One printed book of an order line, as staff and parents see it."""

    id: uuid.UUID
    code: str
    part: str  # "" for a single book, else its volume or stage ("1", "V1")
    title: str | None
    status: str


def item_books(items: Iterable[OrderItem], books: Iterable[Book]) -> dict[uuid.UUID, list[BookRef]]:
    """The books made for each line (a set's volumes in order), from books already loaded with
    `qamra_core.downloads.books_query`."""
    from qamra_core.downloads import owned_by, part_of

    loaded = list(books)
    out: dict[uuid.UUID, list[BookRef]] = {}
    for item in items:
        mine = [b for b in loaded if owned_by(b, item)]
        refs = [BookRef(b.id, b.code, part_of(item.line, b), b.title, b.status.value) for b in mine]
        out[item.id] = sorted(refs, key=lambda r: (len(r.part), r.part))
    return out
