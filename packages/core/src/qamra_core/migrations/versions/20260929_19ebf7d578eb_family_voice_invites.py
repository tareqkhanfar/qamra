"""«صوت أهلي» (Phase 5): the pages a recording invite covers, and when it was first opened.

`recordings` and `share_tokens` already exist since the initial schema (Addendum 1 designed them early);
an invite for a grandparent may cover the whole book (NULL) or chosen pages, and the parent sees whether the
link was opened yet.

Revision ID: 19ebf7d578eb
Revises: ab04012fadad
Create Date: 2026-09-29 14:58:35.934982
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "19ebf7d578eb"
down_revision: str | None = "ab04012fadad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("share_tokens", sa.Column("pages", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("share_tokens", sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("share_tokens", "opened_at")
    op.drop_column("share_tokens", "pages")
