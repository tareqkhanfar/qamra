"""Book codes («QB-7K4M2»): every book of every product has one, printed in the book and shown everywhere.

Revision ID: 8c3f5a1d7e42
Revises: 5b7e2c9d4f10
Create Date: 2026-10-19

The owner (2026-10-19) tells two orders for two children of the same name apart by a code printed on the book's
«عن قمرة» page and on its back cover (`qamra_core.book_codes`).

- `book_codes`: every code ever given out, with no link to the book, so a code is never reused (a family may
  delete its books);
- `books.code`: the book's code, unique and required. Existing books get one here (oldest first), drawn the
  same way new books are;
- the site's Facebook and Instagram links become the owner's pages (facebook.com/qamrabooks, @qamra.app)
  where the admin left them empty; a link an admin saved stays.

Down drops the codes (they cannot be kept without the column) and empties the two links it set.
"""

import secrets
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.engine import Connection

revision: str = "8c3f5a1d7e42"
down_revision: str | None = "5b7e2c9d4f10"
branch_labels = None
depends_on = None

# the format of qamra_core.book_codes (copied: a migration never imports code that may change)
PREFIX = "QB-"
ALPHABET = "23456789ACDEFHJKMNPRTWXY"
LENGTH = 5
LINKS = {
    "facebook_url": "https://www.facebook.com/qamrabooks",
    "instagram_url": "https://www.instagram.com/qamra.app/",
}

settings = sa.table(
    "app_settings",
    sa.column("key", sa.String),
    sa.column("value", JSONB),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def _draw() -> str:
    return PREFIX + "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def backfill(conn: Connection) -> int:
    """A code for every book without one (oldest first), each recorded in the registry. Returns how many."""
    ids: list[Any] = list(
        conn.execute(sa.text("SELECT id FROM books WHERE code IS NULL ORDER BY created_at, id")).scalars()
    )
    taken = set(conn.execute(sa.text("SELECT code FROM book_codes")).scalars())
    for book_id in ids:
        code = _draw()
        while code in taken:
            code = _draw()
        taken.add(code)
        conn.execute(sa.text("INSERT INTO book_codes (code) VALUES (:code)"), {"code": code})
        conn.execute(sa.text("UPDATE books SET code = :code WHERE id = :id"), {"code": code, "id": book_id})
    return len(ids)


def upgrade() -> None:
    op.create_table(
        "book_codes",
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_book_codes")),
    )
    op.add_column("books", sa.Column("code", sa.String(length=12), nullable=True))
    backfill(op.get_bind())
    op.alter_column("books", "code", existing_type=sa.String(length=12), nullable=False)
    op.create_unique_constraint(op.f("uq_books_code"), "books", ["code"])

    for key, value in LINKS.items():
        stmt = insert(settings).values(key=key, value=value, updated_at=sa.func.now())
        op.execute(
            stmt.on_conflict_do_update(
                index_elements=["key"],
                set_={"value": value, "updated_at": sa.func.now()},
                where=settings.c.value == sa.cast(sa.literal('""'), JSONB),
            )
        )


def downgrade() -> None:
    for key, value in LINKS.items():
        op.execute(
            settings.delete().where(
                settings.c.key == key, settings.c.value == sa.cast(sa.literal(f'"{value}"'), JSONB)
            )
        )
    op.drop_constraint(op.f("uq_books_code"), "books", type_="unique")
    op.drop_column("books", "code")
    op.drop_table("book_codes")
