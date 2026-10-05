"""We deliver to the West Bank and Jerusalem only (Tareq, 2026-10-05): the Jordan zones are switched off.

Revision ID: 9d4f2b7c1e60
Revises: cf0e711e7919
Create Date: 2026-10-05

Inactive, not deleted: Jordan may come back. `load_catalog` lists only active zones, so neither the checkout nor
the pricing page offers a Jordanian city or JOD, and `PUT /api/store/cart/zone` refuses them. The zones, their
JOD fees and every JOD price stay; old orders that point at them stay valid. `content/store/catalog.yaml` says
the same for fresh installs. Switch them on again in Admin → الكتالوج والأسعار → التوصيل. Idempotent.
"""

from alembic import op

revision: str = "9d4f2b7c1e60"
down_revision: str | None = "cf0e711e7919"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE shipping_zones SET active = false WHERE country = 'JO' AND active")


def downgrade() -> None:
    op.execute("UPDATE shipping_zones SET active = true WHERE slug IN ('amman', 'jordan-other')")
