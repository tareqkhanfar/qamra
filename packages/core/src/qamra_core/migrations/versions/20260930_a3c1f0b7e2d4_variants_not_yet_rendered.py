"""Only the volumes that render are sold (Tareq, 2026-09-30).

Revision ID: a3c1f0b7e2d4
Revises: 17230ee0e47c
Create Date: 2026-09-30

Every product is on sale, but a volume or stage that does not render yet must be neither listed nor sold,
and the site never says it is "coming". Today: «دوسية التأسيس» KG2 volumes 1 and 2, «رحلتي الأولى» stage 1,
and the family book. The seed is insert-only, so the existing variant rows are switched off here (the
same rule as `content/store/catalog.yaml`: `variant_matrix.rendered` and the journey's `active: false`).

To switch a volume on when it lands: Admin → الكتالوج → the variant's «active», or
`UPDATE product_variants SET active = true WHERE sku LIKE 'wb-kg1-%'` (likewise `wb-kg2-v3-%`,
`wb-kg2-set-%` once all three KG2 volumes render, `journey-s2-%`, `journey-s3-%`, `journey-set-%`).
"""

from alembic import op

revision: str = "a3c1f0b7e2d4"
down_revision: str | None = "17230ee0e47c"
branch_labels = None
depends_on = None

# nosec B608 on the statements below: module constants, no user input
NOT_RENDERED = (
    "sku LIKE 'wb-kg1-%' OR sku LIKE 'wb-kg2-v3-%' OR sku LIKE 'wb-kg2-set-%' "
    "OR sku LIKE 'journey-s2-%' OR sku LIKE 'journey-s3-%' OR sku LIKE 'journey-set-%'"
)


def upgrade() -> None:
    op.execute(f"UPDATE product_variants SET active = false WHERE {NOT_RENDERED}")  # nosec B608


def downgrade() -> None:
    op.execute(f"UPDATE product_variants SET active = true WHERE {NOT_RENDERED}")  # nosec B608
