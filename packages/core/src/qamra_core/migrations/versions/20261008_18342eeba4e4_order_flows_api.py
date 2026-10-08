"""Order flows per product (docs/plans/order-flows.md, chunk 8) and the owner's decisions of 2026-10-07.

Revision ID: 18342eeba4e4
Revises: 0c695b89fde0
Create Date: 2026-10-08

1. `children.name_latin` (String 40, nullable): the child's name in English letters, as the parent wants it
   traced on the English name page of «دوسية التأسيس» and «رحلتي الأولى» stages 2–3.
2. «قلبي يعرف الله» is an activity book like the others: `islamic` joins the `lines` of the three styles
   (3d, watercolor, cartoon), so the child's approved character in any of them is reused for it.
3. The black-and-white «دوسية التأسيس» (the 49 ₪ spiral volumes and the 129 ₪ set, both levels) are switched
   off until a black-and-white interior exists (owner's decision 1). Inactive, not deleted: old orders keep
   pointing at them, and `content/store/catalog.yaml` says the same for fresh installs. Switch them on again
   in Admin → الكتالوج once the interior renders.
4. The add-ons we cannot deliver are switched off (owner's decision, 2026-10-07; the audit is the section
   «Add-ons: what is deactivated» of docs/plans/order-flows.md): the physical extras with no stock, and every
   add-on nothing can produce yet (`RETIRED_ADDONS`; `editable-files` was off already and stays so).
   Inactive, not deleted: their prices stay, past orders keep their snapshots, and the catalog, the add-ons
   step and the cart no longer offer them (`load_catalog` reads active rows only; a cart line that still holds
   one drops it). Switch one on again in Admin → الكتالوج → الإضافات once it can be delivered.
5. «دليل الأهل مطبوعًا» says what is printed (the audit's F3): the solved activity pages in a separate booklet,
   not the parents' pages (those are inside every volume). Only where the row still holds the seeded text.

Every data step is idempotent (it only touches rows not already in the target state). Downgrade drops the
column, takes `islamic` out of the three styles' lines, switches the variants and add-ons back on and puts the
guide's seeded text back.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "18342eeba4e4"
down_revision: str | None = "0c695b89fde0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STYLES = ("3d", "watercolor", "cartoon")
LINE = "islamic"
BW_VARIANTS = tuple(
    f"wb-{level}-{part}-bw-spiral" for level in ("kg1", "kg2") for part in ("v1", "v2", "v3", "set")
)
RETIRED_ADDONS: tuple[str, ...] = (
    # physical, no stock (owner)
    "gift-box",
    "wipe-sleeve",
    "crayon-kit",
    # nothing produces them
    "extra-character",
    "coloring-version",
    "cover-poster",
    "sticker-sheet",
    "audio-qr",
    "parent-guide",
    # partial: the gap is not small (no priority production for express; the family drawings have no step)
    "express",
    "family-characters",
)
GUIDE = "printed-parent-guide"
# (column, seeded text, text now)
GUIDE_TEXT: list[tuple[str, str, str]] = [
    ("name_ar", "دليل الأهل مطبوعًا", "إجابات الأنشطة مطبوعةً"),
    ("name_en", "Printed parent guide", "Printed activity answers"),
    (
        "description_ar",
        "صفحات الأهل وإجابات الأنشطة في كتيّب منفصل",
        "إجابات أنشطة الكتاب في كتيّب منفصل للأهل",
    ),
    (
        "description_en",
        "The parents' pages and the activity answers in a separate booklet",
        "The answers to the book's activities, in a separate booklet for parents",
    ),
]

styles = sa.table("art_styles", sa.column("slug", sa.String), sa.column("lines", sa.JSON))
variants = sa.table("product_variants", sa.column("sku", sa.String), sa.column("active", sa.Boolean))
addons = sa.table(
    "addons",
    sa.column("slug", sa.String),
    sa.column("active", sa.Boolean),
    *(sa.column(col, sa.String) for col, _, _ in GUIDE_TEXT),
)


def islamic_styles(conn: Connection, forward: bool) -> None:
    """`islamic` in (or out of) the three styles' lines, once."""
    if forward:
        sql = (
            "UPDATE art_styles SET lines = lines || to_jsonb(CAST(:line AS text)) "
            "WHERE slug = ANY(:slugs) AND NOT lines ? :line"
        )
    else:
        sql = (
            "UPDATE art_styles SET lines = lines - CAST(:line AS text) "
            "WHERE slug = ANY(:slugs) AND lines ? :line"
        )
    conn.execute(sa.text(sql), {"line": LINE, "slugs": list(STYLES)})


def switch(conn: Connection, forward: bool) -> None:
    """The black-and-white variants and the add-ons we cannot deliver: off (forward) or back on."""
    on = not forward
    conn.execute(
        variants.update()
        .where(variants.c.sku.in_(BW_VARIANTS), variants.c.active.is_(not on))
        .values(active=on)
    )
    conn.execute(
        addons.update()
        .where(addons.c.slug.in_(RETIRED_ADDONS), addons.c.active.is_(not on))
        .values(active=on)
    )


def guide_text(conn: Connection, forward: bool) -> None:
    """The printed guide's name and description say what is printed; an admin's own text is left alone."""
    for column, seeded, now in GUIDE_TEXT:
        frm, to = (seeded, now) if forward else (now, seeded)
        conn.execute(
            addons.update().where(addons.c.slug == GUIDE, addons.c[column] == frm).values({column: to})
        )


def upgrade() -> None:
    op.add_column("children", sa.Column("name_latin", sa.String(length=40), nullable=True))
    conn = op.get_bind()
    islamic_styles(conn, forward=True)
    switch(conn, forward=True)
    guide_text(conn, forward=True)


def downgrade() -> None:
    conn = op.get_bind()
    guide_text(conn, forward=False)
    switch(conn, forward=False)
    islamic_styles(conn, forward=False)
    op.drop_column("children", "name_latin")
