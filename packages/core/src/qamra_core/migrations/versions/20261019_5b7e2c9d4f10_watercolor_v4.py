"""«مائي فاخر» / Watercolor, guide version 4: clean, clear colour, never a sepia or amber cast.

Revision ID: 5b7e2c9d4f10
Revises: d29a66aa61c0
Create Date: 2026-10-19

The owner's live test (2026-10-19): a night photo under yellow street light gave a muddy, brownish-yellow, almost
sepia watercolor portrait and sheet. Guide v4 (`qamra_ai/prompts/style/watercolor.md`) paints on white paper with
clean, transparent washes; a warm light belongs to a scene, never to the whole picture or the child's colours;
and it adds a `## Character` line for the portrait and the sheet.

Generation reads the guide file; the `prompt`, `negative` and `version` columns keep a record, as `2351cdc1195c`
did for v3. A row is touched only at the version it is moved from, so it is safe to run again; down puts v3
back.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "5b7e2c9d4f10"
down_revision: str | None = "d29a66aa61c0"
branch_labels = None
depends_on = None

SLUG = "watercolor"

RECORDS: dict[str, dict[str, Any]] = {
    "v4": {
        "prompt": "Premium watercolor and gouache children's picture-book painting on white textured paper: clean, bright, transparent washes with clear, rich color and real contrast, deep indigo and violet shadows, and luminous highlights. The light is the scene's own (soft daylight, a golden evening or moonlight), and under it skin, hair and clothes keep their true, clear colors. Soft wet edges and visible paper grain, with crisp detail on faces and hands; atmospheric depth with soft foreground framing elements (leaves, arches, lanterns). Never flat or pale. Each child keeps their own face shape and proportions, eye size, hair and real age: the softness is in the paint, never a younger or rounder face.",
        "negative": "- No photorealism, no 3D-render look, no harsh black outlines, no neon colors, no anime.\n- No flat, pale or washed-out backgrounds.\n- No baby face, no generic round-faced child, no monochrome or sepia sketch.\n- No sepia, brown, amber or yellow cast over the whole picture, no muddy browns or grays.",
        "version": 4,
    },
    "v3": {
        "prompt": "Premium watercolor and gouache children's picture-book painting on warm textured paper: rich, saturated color with real contrast, deep indigo and violet shadows, glowing honey-gold highlights, and golden-hour or moonlit light. Soft wet edges and visible paper grain, with crisp detail on faces and hands; atmospheric depth with soft foreground framing elements (leaves, arches, lanterns). Never flat or pale. Each child keeps their own face shape and proportions, eye size, hair and real age: the softness is in the paint, never a younger or rounder face.",
        "negative": "- No photorealism, no 3D-render look, no harsh black outlines, no neon colors, no anime.\n- No flat, pale or washed-out backgrounds.\n- No baby face, no generic round-faced child, no monochrome or sepia sketch.",
        "version": 3,
    },
}

styles = sa.table(
    "art_styles",
    sa.column("slug", sa.String),
    sa.column("prompt", sa.Text),
    sa.column("negative", sa.Text),
    sa.column("version", sa.Integer),
)


def record(conn: Connection, forward: bool) -> None:
    """The watercolor row's record: v3 → v4 (forward) or back; a row in any other state is left alone."""
    source, target = (RECORDS["v3"], RECORDS["v4"]) if forward else (RECORDS["v4"], RECORDS["v3"])
    stmt = styles.update().where(styles.c.slug == SLUG, styles.c.version == source["version"])
    conn.execute(stmt.values(**target))


def upgrade() -> None:
    record(op.get_bind(), forward=True)


def downgrade() -> None:
    record(op.get_bind(), forward=False)
