"""«قلبي يعرف الله» (Addendum 10): the product line, the scholar's review tables, the scholar role.

Revision ID: cf0e711e7919
Revises: e5b9c3d71a20
Create Date: 2026-10-03

- `products.line` may be `islamic`; `user_staff_roles.role` may be `scholar` (approves units, answers the
  `scholar_decision` points; the owner's "*" does not stand in for it).
- The review tables: units (draft → scholar_review → approved / changes_requested, reviewer name and dates),
  their history, the scholar's decisions per point, the scholar's printed name and consent to be named, and
  the volumes' preview renders.
- Data: the sticker sheet and the gift box are offered with the series too; saved quiz rules get the
  «تعليم ديني» goal (`qamra seed-store` only seeds the rules when none are saved). The product and its
  variants are inserted by `qamra seed-store` from content/store/catalog.yaml (insert-only), and the store
  lists a volume only once the scholar approved every unit of it (P0), so nothing is on sale after this
  migration.
"""

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "cf0e711e7919"
down_revision: str | None = "e5b9c3d71a20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINES_OLD = "'classic', 'magic', 'coloring', 'workbook', 'journey', 'family'"
LINES_NEW = f"{LINES_OLD}, 'islamic'"
ROLES_OLD = "'owner', 'admin', 'editor', 'reviewer', 'production', 'support'"
ROLES_NEW = f"{ROLES_OLD}, 'scholar'"
SHARED_ADDONS = "('sticker-sheet', 'gift-box')"
STATUSES = ("draft", "scholar_review", "changes_requested", "approved")

# the same rules as content/store/quiz.yaml (goal «تعليم ديني»)
RAMADAN = {
    "slug": "islamic-series",
    "options": {"volume": "R"},
    "title_ar": "كتاب رمضان والعيد",
    "title_en": "The Ramadan and Eid book",
    "why_ar": "أجواء رمضان والعيد بالقصة واللعب والأنشطة.",
    "why_en": "The spirit of Ramadan and Eid through stories, play and activities",
}
FAITH_RULES = [
    {
        "goal": "faith",
        "age_min": None,
        "age_max": 5,
        "pen": None,
        "product": {
            "slug": "islamic-series",
            "options": {"volume": "V1"},
            "title_ar": "قلبي يعرف الله — المجلد الأول",
            "title_en": "My Heart Knows Allah — volume 1",
            "why_ar": "يتعرّف إلى ربّه ونعمه ونبيّه ﷺ بالقصة واللعب، بالحب لا بالتخويف.",
            "why_en": "Meets Allah, His blessings and His Prophet ﷺ through stories and play, with love, never fear.",
        },
        "alternative": RAMADAN,
    },
    {
        "goal": "faith",
        "age_min": None,
        "age_max": None,
        "pen": None,
        "product": {
            "slug": "islamic-series",
            "options": {"volume": "V3"},
            "title_ar": "قلبي يعرف الله — المجلد الثالث",
            "title_en": "My Heart Knows Allah — volume 3",
            "why_ar": "أركان الإسلام والإيمان بأمثلة من عالمه، والصلاة كاملة.",
            "why_en": "The pillars of Islam and of faith through examples from their world, and the full prayer.",
        },
        "alternative": RAMADAN,
    },
]


def _timestamps() -> list[sa.Column[Any]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.drop_constraint(op.f("ck_products_product_line"), "products", type_="check")
    op.create_check_constraint(op.f("ck_products_product_line"), "products", f"line IN ({LINES_NEW})")
    op.drop_constraint(op.f("ck_user_staff_roles_staff_role"), "user_staff_roles", type_="check")
    op.create_check_constraint(
        op.f("ck_user_staff_roles_staff_role"), "user_staff_roles", f"role IN ({ROLES_NEW})"
    )

    op.create_table(
        "islamic_unit_reviews",
        sa.Column("unit_id", sa.String(length=40), nullable=False),
        sa.Column("volume", sa.String(length=4), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *STATUSES,
                name="islamic_review_status",
                native_enum=False,
                create_constraint=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_name", sa.String(length=120), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preview_run", sa.String(length=32), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'scholar_review', 'changes_requested', 'approved')",
            name=op.f("ck_islamic_unit_reviews_islamic_review_status"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["users.id"],
            name=op.f("fk_islamic_unit_reviews_reviewer_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["users.id"],
            name=op.f("fk_islamic_unit_reviews_submitted_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("unit_id", name=op.f("pk_islamic_unit_reviews")),
    )
    op.create_index(op.f("ix_islamic_unit_reviews_volume"), "islamic_unit_reviews", ["volume"], unique=False)

    op.create_table(
        "islamic_review_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("page", sa.SmallInteger(), nullable=True),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=True),
        sa.Column("author_name", sa.String(length=120), nullable=False),
        sa.Column("scholar", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            name=op.f("fk_islamic_review_events_author_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["islamic_unit_reviews.unit_id"],
            name=op.f("fk_islamic_review_events_unit_id_islamic_unit_reviews"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_islamic_review_events")),
    )
    op.create_index(
        op.f("ix_islamic_review_events_unit_id"), "islamic_review_events", ["unit_id"], unique=False
    )

    op.create_table(
        "islamic_scholar_decisions",
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decided_by_name", sa.String(length=120), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"],
            ["users.id"],
            name=op.f("fk_islamic_scholar_decisions_decided_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("source_id", name=op.f("pk_islamic_scholar_decisions")),
    )

    op.create_table(
        "islamic_reviewers",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name_ar", sa.String(length=120), nullable=False),
        sa.Column("may_be_named", sa.Boolean(), nullable=False),
        sa.Column("named_consent_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_islamic_reviewers_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_islamic_reviewers")),
    )

    op.create_table(
        "islamic_review_previews",
        sa.Column("volume", sa.String(length=4), nullable=False),
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("pages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cover_key", sa.String(length=300), nullable=True),
        sa.Column("problems", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("rendered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name=op.f("fk_islamic_review_previews_requested_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("volume", name=op.f("pk_islamic_review_previews")),
    )

    # data: shared add-ons, and the quiz's «تعليم ديني» goal in rules the admin already saved
    op.execute(
        "UPDATE addons SET lines = lines || '[\"islamic\"]'::jsonb "  # nosec B608: module constants
        f"WHERE slug IN {SHARED_ADDONS} AND NOT lines @> '[\"islamic\"]'::jsonb"
    )
    op.get_bind().execute(
        sa.text(
            "UPDATE app_settings SET value = jsonb_set(value, '{rules}', (value -> 'rules') || CAST(:rules AS jsonb)) "
            "WHERE key = 'quiz_rules' AND jsonb_typeof(value -> 'rules') = 'array' "
            "AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(value -> 'rules') r WHERE r ->> 'goal' = 'faith')"
        ),
        {"rules": json.dumps(FAITH_RULES, ensure_ascii=False)},
    )


def downgrade() -> None:
    op.execute(
        "UPDATE app_settings SET value = jsonb_set(value, '{rules}', COALESCE(("
        "SELECT jsonb_agg(r) FROM jsonb_array_elements(value -> 'rules') r WHERE r ->> 'goal' <> 'faith'"
        "), '[]'::jsonb)) WHERE key = 'quiz_rules' AND jsonb_typeof(value -> 'rules') = 'array'"
    )
    op.execute(f"UPDATE addons SET lines = lines - 'islamic' WHERE slug IN {SHARED_ADDONS}")  # nosec B608
    op.execute("DELETE FROM addons WHERE slug = 'printed-parent-guide'")
    op.execute("DELETE FROM products WHERE line = 'islamic'")
    op.drop_table("islamic_review_previews")
    op.drop_table("islamic_reviewers")
    op.drop_table("islamic_scholar_decisions")
    op.drop_index(op.f("ix_islamic_review_events_unit_id"), table_name="islamic_review_events")
    op.drop_table("islamic_review_events")
    op.drop_index(op.f("ix_islamic_unit_reviews_volume"), table_name="islamic_unit_reviews")
    op.drop_table("islamic_unit_reviews")
    op.execute("DELETE FROM user_staff_roles WHERE role = 'scholar'")
    op.drop_constraint(op.f("ck_user_staff_roles_staff_role"), "user_staff_roles", type_="check")
    op.create_check_constraint(
        op.f("ck_user_staff_roles_staff_role"), "user_staff_roles", f"role IN ({ROLES_OLD})"
    )
    op.drop_constraint(op.f("ck_products_product_line"), "products", type_="check")
    op.create_check_constraint(op.f("ck_products_product_line"), "products", f"line IN ({LINES_OLD})")
