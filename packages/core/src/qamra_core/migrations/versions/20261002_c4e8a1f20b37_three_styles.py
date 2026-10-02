"""The three art styles of Addendum 11 §1: «سينمائي ثلاثي الأبعاد» first, «مائي فاخر», «كرتون ملوّن» (2026-10-02).

Revision ID: c4e8a1f20b37
Revises: 3f7ceee7a4df
Create Date: 2026-10-02

Names, order and lines of the three styles. The activity books (workbook, journey, family) can now be drawn in
any of them (Tareq: 3D for the stories and the activity books). Generation reads the look and negatives from
`qamra_ai/prompts/style/<slug>.md` (version 2); the `prompt` column stays a record of the seeded text.
"""

from alembic import op

revision: str = "c4e8a1f20b37"
down_revision: str | None = "3f7ceee7a4df"
branch_labels = None
depends_on = None

ACTIVITY = '"workbook", "journey", "family"'
STYLES = {  # slug: (name_ar, name_en, lines, sort)
    "3d": ("سينمائي ثلاثي الأبعاد", "Cinematic 3D", f'["magic", {ACTIVITY}]', 0),
    "watercolor": ("مائي فاخر", "Premium watercolor", f'["magic", "classic", {ACTIVITY}]', 1),
    "cartoon": ("كرتون ملوّن", "Bright 2D cartoon", f'["magic", {ACTIVITY}]', 2),
}
BEFORE = {
    "3d": ("ثلاثي الأبعاد", "3D animated-film look", '["magic"]'),
    "watercolor": ("مائي ناعم", "Soft watercolor (the Qamra signature)", '["magic", "classic"]'),
    "cartoon": ("كرتون ملوّن", "Bright 2D cartoon", '["magic"]'),
}


def upgrade() -> None:
    for slug, (ar, en, lines, sort) in STYLES.items():
        op.execute(
            f"UPDATE art_styles SET name_ar = '{ar}', name_en = '{en}', lines = '{lines}'::jsonb, "  # nosec B608
            f"sort = {sort}, version = 2, active = true WHERE slug = '{slug}'"
        )
    # Only the three styles in the story books: coloring stays for the coloring book; semi-realistic is retired
    op.execute("""UPDATE art_styles SET lines = '["coloring"]'::jsonb, sort = 10 WHERE slug = 'coloring'""")
    op.execute("UPDATE art_styles SET lines = '[]'::jsonb, active = false, sort = 11 WHERE slug = 'semi-realistic'")


def downgrade() -> None:
    op.execute("""UPDATE art_styles SET lines = '["coloring", "magic"]'::jsonb WHERE slug = 'coloring'""")
    op.execute("""UPDATE art_styles SET lines = '["magic"]'::jsonb, active = true WHERE slug = 'semi-realistic'""")
    for slug, (ar, en, lines) in BEFORE.items():
        op.execute(
            f"UPDATE art_styles SET name_ar = '{ar}', name_en = '{en}', lines = '{lines}'::jsonb, "  # nosec B608
            f"version = 1 WHERE slug = '{slug}'"
        )
