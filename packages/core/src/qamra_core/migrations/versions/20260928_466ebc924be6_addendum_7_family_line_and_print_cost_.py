"""Addendum 7: the family book's product line, and the printer's cost tiers per variant.

Hand-edited: a server default for existing variants, the product-line CHECK constraint, and the shared
add-ons (extra sticker sheet, crayon kit, gift box) offered with the family book too.

Revision ID: 466ebc924be6
Revises: 65d890e21316
Create Date: 2026-09-28 18:22:38.732424
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "466ebc924be6"
down_revision: str | None = "65d890e21316"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINES_OLD = "'classic', 'magic', 'coloring', 'workbook', 'journey'"
LINES_NEW = "'classic', 'magic', 'coloring', 'workbook', 'journey', 'family'"
SHARED_ADDONS = "('sticker-sheet', 'crayon-kit', 'gift-box')"


def upgrade() -> None:
    op.add_column(
        "product_variants",
        sa.Column(
            "print_cost_tiers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.drop_constraint(op.f("ck_products_product_line"), "products", type_="check")
    op.create_check_constraint(op.f("ck_products_product_line"), "products", f"line IN ({LINES_NEW})")
    op.execute(
        f"UPDATE addons SET lines = lines || '[\"family\"]'::jsonb "
        f"WHERE slug IN {SHARED_ADDONS} AND NOT lines @> '[\"family\"]'::jsonb"
    )


def downgrade() -> None:
    op.execute(f"UPDATE addons SET lines = lines - 'family' WHERE slug IN {SHARED_ADDONS}")
    op.execute("DELETE FROM products WHERE line = 'family'")
    op.drop_constraint(op.f("ck_products_product_line"), "products", type_="check")
    op.create_check_constraint(op.f("ck_products_product_line"), "products", f"line IN ({LINES_OLD})")
    op.drop_column("product_variants", "print_cost_tiers")
