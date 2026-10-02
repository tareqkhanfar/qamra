"""The coloring book leaves the store (Tareq, 2026-10-02): nothing can make it yet.

Revision ID: e5b9c3d71a20
Revises: c4e8a1f20b37
Create Date: 2026-10-02

Inactive, not deleted: no page, price list, cart or checkout lists it, and old rows that point at it stay
valid. `content/store/catalog.yaml` says the same for fresh installs. The story books' «نسخة تلوين» add-on is
a different product and stays.
"""

from alembic import op

revision: str = "e5b9c3d71a20"
down_revision: str | None = "c4e8a1f20b37"
branch_labels = None
depends_on = None

PRODUCT = "(SELECT id FROM products WHERE slug = 'coloring-book')"


def upgrade() -> None:
    op.execute("UPDATE products SET active = false WHERE slug = 'coloring-book'")
    op.execute(f"UPDATE product_variants SET active = false WHERE product_id IN {PRODUCT}")  # nosec B608


def downgrade() -> None:
    op.execute("UPDATE products SET active = true WHERE slug = 'coloring-book'")
    op.execute(f"UPDATE product_variants SET active = true WHERE product_id IN {PRODUCT}")  # nosec B608
