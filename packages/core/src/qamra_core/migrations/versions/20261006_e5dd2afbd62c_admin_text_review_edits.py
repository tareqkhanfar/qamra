"""Admin review of every story's words before «تأكيد»: the history of staff text edits.

Revision ID: e5dd2afbd62c
Revises: 9d4f2b7c1e60
Create Date: 2026-10-06

`book_text_edits`: one row per saved change of a story book's words (a page, the title, the dedication, the
parent's message, «للأهل», the back-cover blurb): old and new text, who and when, edit or revert, and the
note kept when staff saved words the instant screen flagged. Deleted with the book (the text carries the
child's name); `audit_logs` keeps ids only. See docs/plans/admin-story-text-review.md.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5dd2afbd62c"
down_revision: str | None = "9d4f2b7c1e60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "book_text_edits",
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("field", sa.String(length=24), nullable=False),
        sa.Column("beat", sa.SmallInteger(), nullable=True),
        sa.Column("old_text", sa.Text(), nullable=True),
        sa.Column("new_text", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("screen", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_book_text_edits_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name=op.f("fk_book_text_edits_book_id_books"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_book_text_edits")),
    )
    op.create_index(op.f("ix_book_text_edits_book_id"), "book_text_edits", ["book_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_book_text_edits_book_id"), table_name="book_text_edits")
    op.drop_table("book_text_edits")
