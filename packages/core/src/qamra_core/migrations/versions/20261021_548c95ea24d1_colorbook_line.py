"""«دفاتر التلوين والرسم»: the `colorbook` product line (four books personalized on the cover, no AI per order).

Revision ID: 548c95ea24d1
Revises: 4e1c9a7b2d63
Create Date: 2026-10-21

- `products.line` may be `colorbook`. The dormant `coloring` line (the black-and-white story book, inactive)
  stays as it is: it is a story line, this one is an activity line.
- The character on the cover, when the family has one or has one drawn, is in one of the activity books'
  styles: the four active styles (3d, watercolor, cartoon, semi-realistic) get `colorbook` in `lines`, as their
  guide files now say (`qamra_ai/prompts/style/*.md`). Never the `coloring` style.
- The gift box (inactive today) is offered with the printed books too, like the other activity books.
- The products and their variants are inserted by `qamra seed-store` from content/store/catalog.yaml
  (insert-only), so nothing is on sale after this migration alone.

Safe to run again: a line is appended only where it is missing. Down removes the line from the styles and the
gift box, deletes the line's products (their variants and prices go with them) and restores the CHECK.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "548c95ea24d1"
down_revision: str | None = "4e1c9a7b2d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINES_OLD = "'classic', 'magic', 'coloring', 'workbook', 'journey', 'family', 'islamic'"
LINES_NEW = f"{LINES_OLD}, 'colorbook'"
STYLES = "('3d', 'watercolor', 'cartoon', 'semi-realistic')"
SHARED_ADDONS = "('gift-box')"


def upgrade() -> None:
    op.drop_constraint(op.f("ck_products_product_line"), "products", type_="check")
    op.create_check_constraint(op.f("ck_products_product_line"), "products", f"line IN ({LINES_NEW})")
    op.execute(
        "UPDATE art_styles SET lines = lines || '[\"colorbook\"]'::jsonb "  # nosec B608: module constants
        f"WHERE slug IN {STYLES} AND NOT lines @> '[\"colorbook\"]'::jsonb"
    )
    op.execute(
        "UPDATE addons SET lines = lines || '[\"colorbook\"]'::jsonb "  # nosec B608: module constants
        f"WHERE slug IN {SHARED_ADDONS} AND NOT lines @> '[\"colorbook\"]'::jsonb"
    )


def downgrade() -> None:
    op.execute(f"UPDATE addons SET lines = lines - 'colorbook' WHERE slug IN {SHARED_ADDONS}")  # nosec B608
    op.execute(f"UPDATE art_styles SET lines = lines - 'colorbook' WHERE slug IN {STYLES}")  # nosec B608
    op.execute("DELETE FROM products WHERE line = 'colorbook'")
    op.drop_constraint(op.f("ck_products_product_line"), "products", type_="check")
    op.create_check_constraint(op.f("ck_products_product_line"), "products", f"line IN ({LINES_OLD})")
