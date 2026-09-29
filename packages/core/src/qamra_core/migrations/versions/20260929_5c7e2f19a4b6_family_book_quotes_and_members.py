"""family book: quote details on leads, illustrated family members

Revision ID: 5c7e2f19a4b6
Revises: d022f9307892
Create Date: 2026-09-29 18:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5c7e2f19a4b6"
down_revision: str | None = "d022f9307892"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("draft", "generating", "ready", "approved", "failed")


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")
        ),
    )
    op.create_table(
        "family_members",
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("guardian_user_id", sa.Uuid(), nullable=False),
        sa.Column("relation", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=40), nullable=False),
        sa.Column("adult", sa.Boolean(), nullable=False),
        sa.Column("scarf", sa.Boolean(), nullable=False),
        sa.Column("consent_version", sa.String(length=32), nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_ip", sa.String(length=45), nullable=True),
        sa.Column("photo_key", sa.String(length=300), nullable=True),
        sa.Column("photo_delete_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("art_style", sa.String(length=32), nullable=True),
        sa.Column("sheet_key", sa.String(length=300), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                *STATUSES, name="family_member_status", native_enum=False, create_constraint=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("regen_count", sa.SmallInteger(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{s}'" for s in STATUSES) + ")",
            name=op.f("ck_family_members_family_member_status"),
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name=op.f("fk_family_members_child_id_children"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["guardian_user_id"],
            ["users.id"],
            name=op.f("fk_family_members_guardian_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_family_members")),
    )
    op.create_index(op.f("ix_family_members_child_id"), "family_members", ["child_id"], unique=False)
    op.create_index(
        op.f("ix_family_members_photo_delete_after"), "family_members", ["photo_delete_after"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_family_members_photo_delete_after"), table_name="family_members")
    op.drop_index(op.f("ix_family_members_child_id"), table_name="family_members")
    op.drop_table("family_members")
    op.drop_column("leads", "details")
