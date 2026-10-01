"""Every volume and stage renders: KG1 1–3, KG2 3 and the sets, «رحلتي الأولى» stages 2–3 and the set (2026-10-01).

Revision ID: b7d2e91c4a05
Revises: a3c1f0b7e2d4
Create Date: 2026-10-01

Switches on the variants that a3c1f0b7e2d4 switched off; `content/store/catalog.yaml` says the same for fresh
installs (`variant_matrix.rendered`, no `active: false` on the journey).
"""

from alembic import op

revision: str = "b7d2e91c4a05"
down_revision: str | None = "a3c1f0b7e2d4"
branch_labels = None
depends_on = None

# nosec B608 on the statements below: module constants, no user input
NOW_RENDERED = (
    "sku LIKE 'wb-kg1-%' OR sku LIKE 'wb-kg2-v3-%' OR sku LIKE 'wb-kg2-set-%' "
    "OR sku LIKE 'journey-s2-%' OR sku LIKE 'journey-s3-%' OR sku LIKE 'journey-set-%'"
)


def upgrade() -> None:
    op.execute(f"UPDATE product_variants SET active = true WHERE {NOW_RENDERED}")  # nosec B608


def downgrade() -> None:
    op.execute(f"UPDATE product_variants SET active = false WHERE {NOW_RENDERED}")  # nosec B608
