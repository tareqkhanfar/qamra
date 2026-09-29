"""drawing companion parent flow

Revision ID: d022f9307892
Revises: 918b650a07fc
Create Date: 2026-09-29 15:24:36.815665
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d022f9307892"
down_revision: str | None = "918b650a07fc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("draft", "generating", "ready", "approved", "failed")


def upgrade() -> None:
    op.add_column(
        "companions",
        sa.Column(
            "status",
            sa.Enum(
                *STATUSES, name="companion_status", native_enum=False, create_constraint=False, length=32
            ),
            nullable=False,
            server_default="draft",
        ),
    )
    op.create_check_constraint(
        op.f("ck_companions_companion_status"),
        "companions",
        "status IN (" + ", ".join(f"'{s}'" for s in STATUSES) + ")",
    )
    op.add_column(
        "companions",
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "companions",
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    # companions drawn before this step existed (admin sample books) are finished ones
    op.execute("UPDATE companions SET status = 'approved' WHERE sheet_key IS NOT NULL")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_companions_companion_status"), "companions", type_="check")
    op.drop_column("companions", "params")
    op.drop_column("companions", "options")
    op.drop_column("companions", "status")
