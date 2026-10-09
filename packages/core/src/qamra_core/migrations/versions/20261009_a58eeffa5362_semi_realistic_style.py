"""A fourth art style, «شبه حقيقي» / Semi-realistic, for the story books and the activity books (Tareq, 2026-10-09).

Revision ID: a58eeffa5362
Revises: 6a87cac7a912
Create Date: 2026-10-09

The owner asked for a painted, semi-realistic look that keeps the child's real features, for both the Magic story
books and the four activity lines. The retired `semi-realistic` row (switched off by `c4e8a1f20b37`) comes back
with guide version 2 (`qamra_ai/prompts/style/semi-realistic.md`): its new name, the look and negatives of the new
guide, the lines `magic, workbook, journey, family, islamic`, fourth in the site's order (after 3D, watercolor and
cartoon, so a parent who is not asked still gets 3D), and switched on. A row is reused rather than added so the
admin never sees two semi-realistic styles, and characters drawn in it before stay valid.

Not in «قمرة كلاسيك»: Classic pages are drawn once per theme × style × look as templates
(`classic_templates`), and none exist in this style; the Classic line lists only styles that have them.

Generation reads the look from the guide file; the `prompt` and `negative` columns keep a record of the seeded text,
as for the other styles. A fresh database gets the row from the seed (`seed_store`), which reads the same guide.

Idempotent: the upgrade touches the row only while it is still at version 1, the downgrade only at version 2.
Downgrade retires it again with its version-1 name and text.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection

revision: str = "a58eeffa5362"
down_revision: str | None = "6a87cac7a912"
branch_labels = None
depends_on = None

SLUG = "semi-realistic"

NOW: dict[str, Any] = {
    "name_ar": "شبه حقيقي",
    "name_en": "Semi-realistic",
    "prompt": (
        "A semi-realistic painted children's-book illustration, like a classic hand-painted storybook "
        "portrait: digital gouache-and-oil painting with soft, visible brushstrokes, real volume and gentle "
        "modelling of light and shadow on faces, hands and clothes, natural-size eyes with soft catchlights, "
        "and hair painted in soft, glossy clumps. Natural, true-to-age child proportions (a head only "
        "slightly larger than life, never chibi). Likeness comes first: the child's face shape, eyes, "
        "eyebrows, nose, mouth, complexion, hairline and hairstyle stay very close to the reference, so a "
        "parent knows their own child at a glance. Warm golden key light with soft shadows in the warm Qamra "
        "palette; painterly backgrounds with gentle depth, a little softer than the figures. Figures have "
        "clean, readable silhouettes shaped by light and color rather than ink outlines, so a figure on a "
        "plain background cuts out cleanly. Unmistakably a painting, never a photograph."
    ),
    "negative": (
        "- No photograph or camera look: no photographic detail, no lens blur or bokeh, no film grain, no "
        "HDR.\n"
        "- No watercolor washes or paper grain, no ink outlines, no flat cel shading: the look is painted "
        "and modelled.\n"
        "- No uncanny or waxy faces, no glassy doll eyes; children look exactly their real age.\n"
        "- No chibi or oversized heads, no oversized cartoon eyes, no anime, no 3D-render or plastic look.\n"
        "- No extra or missing fingers: hands painted simply, five fingers each. No text or lettering "
        "anywhere."
    ),
    "version": 2,
    "lines": ["magic", "workbook", "journey", "family", "islamic"],
    "sort": 3,
    "active": True,
}
BEFORE: dict[str, Any] = {
    "name_ar": "شبه واقعي",
    "name_en": "Semi-realistic painted",
    "prompt": (
        "A semi-realistic painted storybook portrait style: soft digital painting with natural proportions and "
        "gentle visible brushwork, warm natural light, and softened, idealized features that stay clearly "
        "recognizable. It reads as a classic painted illustration, never a photograph: simplified skin, soft "
        "edges, painterly backgrounds with gentle depth."
    ),
    "negative": (
        "- No photorealism, no photographic textures, no skin pores, no lens effects, no uncanny realism.\n"
        "- Children must stay clearly illustrated and age-appropriate: no adult-looking or glamorized children."
    ),
    "version": 1,
    "lines": [],
    "sort": 11,
    "active": False,
}

styles = sa.table(
    "art_styles",
    sa.column("slug", sa.String),
    sa.column("name_ar", sa.String),
    sa.column("name_en", sa.String),
    sa.column("prompt", sa.Text),
    sa.column("negative", sa.Text),
    sa.column("version", sa.Integer),
    sa.column("lines", JSONB),
    sa.column("sort", sa.SmallInteger),
    sa.column("active", sa.Boolean),
    sa.column("qa_threshold", sa.Numeric),
    sa.column("likeness_min", sa.SmallInteger),
)


def revive(conn: Connection, forward: bool) -> None:
    """The style back in the books (forward) or retired again; a row already in the target state is left alone."""
    if forward:
        stmt = styles.update().where(styles.c.slug == SLUG, styles.c.version < NOW["version"])
        conn.execute(stmt.values(**NOW, qa_threshold=0.8, likeness_min=8))
    else:
        stmt = styles.update().where(styles.c.slug == SLUG, styles.c.version == NOW["version"])
        conn.execute(stmt.values(**BEFORE))


def upgrade() -> None:
    revive(op.get_bind(), forward=True)


def downgrade() -> None:
    revive(op.get_bind(), forward=False)
