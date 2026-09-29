"""Every product is sold: no «قريبًا» in the store (Tareq, 2026-09-30).

Revision ID: 17230ee0e47c
Revises: 97b657f5bf00
Create Date: 2026-09-30

The educational books and the family book were held back for the educator's and the printer's sign-off.
Tareq reviewed every page himself and asked for the store to be complete: the products are active and
orderable. The seed is insert-only, so existing rows are updated here.
"""

from alembic import op

revision: str = "17230ee0e47c"
down_revision: str | None = "97b657f5bf00"
branch_labels = None
depends_on = None

PRODUCTS = "('foundation-workbook', 'learning-journey', 'family-adventures')"


def upgrade() -> None:
    op.execute(
        "UPDATE products SET active = true, features = features || '{\"orderable\": true}'::jsonb "
        f"WHERE slug IN {PRODUCTS}"  # nosec B608: module constants, no user input
    )


def downgrade() -> None:
    op.execute(
        "UPDATE products SET features = features || '{\"orderable\": false}'::jsonb "
        f"WHERE slug IN {PRODUCTS}"  # nosec B608: module constants, no user input
    )
