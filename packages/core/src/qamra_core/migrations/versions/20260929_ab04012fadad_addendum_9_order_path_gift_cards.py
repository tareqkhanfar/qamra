"""Addendum 9 order path: gift cards, the gift order and its card message, add-on dependencies and display,
and the «الكتاب الثاني −15%» bundle rule.

Hand-edited: server defaults for existing rows, the bundle-kind CHECK constraint, the seeded two-books bundle
moved to the new rule (only while it still has its seeded values), and the add-ons step's display data
(featured, badges, and descriptions where they are still empty).

Revision ID: ab04012fadad
Revises: e6b4b0230d6a
Create Date: 2026-09-29 10:14:21.663858
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ab04012fadad"
down_revision: str | None = "e6b4b0230d6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS_OLD = "'min_items', 'siblings'"
KINDS_NEW = "'min_items', 'siblings', 'cheapest'"
FEATURED = "('hardcover-upgrade', 'gift-box', 'extra-copy', 'drawing-companion', 'coloring-version')"
BADGES = {
    "hardcover-upgrade": ("الأكثر اختياراً", "Most chosen"),
    "extra-copy": ("توفير", "Save"),
    "drawing-companion": ("مميّز", "Special"),
}
DESCRIPTIONS = {
    "hardcover-upgrade": ("يدوم سنوات، والأنسب للهدايا", "Lasts for years, the best choice for a gift"),
    "gift-box": ("جاهز للإهداء، ونكتب رسالتك على البطاقة", "Ready to give, with your message on the card"),
    "extra-copy": ("نفس الكتاب بنص السعر تقريباً", "The same book at about half the price"),
    "drawing-companion": (
        "رسمة طفلك تتحوّل لشخصية ترافقه في كل الصفحات",
        "Your child's drawing becomes a companion on every page",
    ),
    "coloring-version": (
        "نفس الصفحات بالأبيض والأسود ليلوّنها طفلك",
        "The same pages in black and white, for your child to color",
    ),
    "dedication-page": ("سطرين منك بأول الكتاب", "A few lines from you at the start of the book"),
    "family-voice": (
        "سجّل القصة بصوتك، وتسمعها بمسح الرمز",
        "Record the story in your voice, and play it by scanning the code",
    ),
    "cover-poster": ("غلاف الكتاب بحجم كبير لغرفة طفلك", "The book's cover, big, for your child's room"),
    "express": ("حسب توفر المطبعة", "Subject to the printer's availability"),
}


def upgrade() -> None:
    op.create_table(
        "gift_cards",
        sa.Column("code", sa.String(length=24), nullable=False),
        sa.Column(
            "currency",
            sa.Enum(
                "ILS", "JOD", name="gift_card_currency", native_enum=False, create_constraint=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("balance", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("currency IN ('ILS', 'JOD')", name=op.f("ck_gift_cards_gift_card_currency")),
        sa.CheckConstraint("balance >= 0 AND balance <= amount", name=op.f("ck_gift_cards_balance_range")),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_gift_cards_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gift_cards")),
        sa.UniqueConstraint("code", name=op.f("uq_gift_cards_code")),
    )
    op.create_table(
        "gift_card_redemptions",
        sa.Column("gift_card_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["gift_card_id"],
            ["gift_cards.id"],
            name=op.f("fk_gift_card_redemptions_gift_card_id_gift_cards"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_gift_card_redemptions_order_id_orders"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gift_card_redemptions")),
    )
    op.create_index(
        op.f("ix_gift_card_redemptions_gift_card_id"), "gift_card_redemptions", ["gift_card_id"], unique=False
    )
    op.create_index(
        op.f("ix_gift_card_redemptions_order_id"), "gift_card_redemptions", ["order_id"], unique=False
    )
    op.add_column(
        "addons",
        sa.Column(
            "needs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("addons", sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("addons", sa.Column("badge_ar", sa.String(length=40), nullable=True))
    op.add_column("addons", sa.Column("badge_en", sa.String(length=40), nullable=True))
    op.add_column("carts", sa.Column("gift_card_code", sa.String(length=24), nullable=True))
    op.add_column("carts", sa.Column("gift", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("carts", sa.Column("gift_message", sa.String(length=200), nullable=True))
    op.add_column("orders", sa.Column("gift", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("orders", sa.Column("gift_message", sa.String(length=200), nullable=True))

    # «الكتاب الثاني −15%» (Addendum 9 §1.4): the seeded 2-books bundle now discounts only the cheaper book
    op.drop_constraint(op.f("ck_bundles_bundle_kind"), "bundles", type_="check")
    op.create_check_constraint(op.f("ck_bundles_bundle_kind"), "bundles", f"kind IN ({KINDS_NEW})")
    op.execute(
        "UPDATE bundles SET kind = 'cheapest', name_ar = 'الكتاب الثاني −15%', name_en = 'Second book −15%' "
        "WHERE slug = 'two-books' AND kind = 'min_items' AND min_items = 2 AND discount_pct = 15"
    )
    # the add-ons step (design AddOns): the open list, the badges, and descriptions not written yet
    op.execute(f"UPDATE addons SET featured = true WHERE slug IN {FEATURED}")
    rows = sa.table(
        "addons",
        sa.column("slug", sa.String),
        sa.column("badge_ar", sa.String),
        sa.column("badge_en", sa.String),
        sa.column("description_ar", sa.Text),
        sa.column("description_en", sa.Text),
    )
    for slug, (ar, en) in BADGES.items():
        op.execute(
            rows.update()
            .where(rows.c.slug == slug, rows.c.badge_ar.is_(None))
            .values(badge_ar=ar, badge_en=en)
        )
    for slug, (ar, en) in DESCRIPTIONS.items():
        op.execute(
            rows.update()
            .where(rows.c.slug == slug, rows.c.description_ar == "")
            .values(description_ar=ar, description_en=en)
        )


def downgrade() -> None:
    op.execute(
        "UPDATE bundles SET kind = 'min_items', name_ar = 'كتابان أو أكثر −15%', name_en = '2+ books −15%' "
        "WHERE slug = 'two-books' AND kind = 'cheapest'"
    )
    op.execute("DELETE FROM bundles WHERE kind = 'cheapest'")
    op.drop_constraint(op.f("ck_bundles_bundle_kind"), "bundles", type_="check")
    op.create_check_constraint(op.f("ck_bundles_bundle_kind"), "bundles", f"kind IN ({KINDS_OLD})")
    op.drop_column("orders", "gift_message")
    op.drop_column("orders", "gift")
    op.drop_column("carts", "gift_message")
    op.drop_column("carts", "gift")
    op.drop_column("carts", "gift_card_code")
    op.drop_column("addons", "badge_en")
    op.drop_column("addons", "badge_ar")
    op.drop_column("addons", "featured")
    op.drop_column("addons", "needs")
    op.drop_index(op.f("ix_gift_card_redemptions_order_id"), table_name="gift_card_redemptions")
    op.drop_index(op.f("ix_gift_card_redemptions_gift_card_id"), table_name="gift_card_redemptions")
    op.drop_table("gift_card_redemptions")
    op.drop_table("gift_cards")
