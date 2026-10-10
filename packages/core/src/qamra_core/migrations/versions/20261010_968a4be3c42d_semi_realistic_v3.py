"""«شبه حقيقي» / Semi-realistic, guide version 3: a realistic painted portrait instead of a storybook cartoon.

Revision ID: 968a4be3c42d
Revises: a58eeffa5362
Create Date: 2026-10-10

Tareq (2026-10-10): the semi-realistic samples looked like a cartoon (big eyes, outlines, flat shapes). Guide v3
(`qamra_ai/prompts/style/semi-realistic.md`) paints a realistic oil-portrait look and replaces two house-style
sections for this style only; the other styles' prompts are unchanged.

Generation reads the guide file; the `prompt` and `negative` columns keep a record of the seeded look and
negatives (as `a58eeffa5362` did for v2), and `version` says which guide drew the style's new characters. A
fresh database gets the row from the seed, which reads the same guide.

Idempotent: the upgrade touches the row only at version 2, the downgrade only at version 3.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "968a4be3c42d"
down_revision: str | None = "a58eeffa5362"
branch_labels = None
depends_on = None

SLUG = "semi-realistic"

V3: dict[str, Any] = {
    "prompt": (
        "Realistic painting in the manner of a fine-art oil portrait, carried through the whole scene and "
        "whatever pose and action it describes. Natural, true-to-age proportions: a young child's real head "
        "size for their height, natural-size eyes with real irises, lids and lashes, and a natural nose, lips "
        "and ears. The face is modeled with real tonal variation in the child's own complexion: warmer cheeks, "
        "nose and ears, cooler half-tones at the temples and jaw, and a soft, warm glow where the light falls. "
        "Hair is real hair, with its true color, texture, hairline and parting, painted in locks with fine "
        "strands catching the light. Clothes have real fabric weight and natural folds. Soft, painterly light: "
        "one warm key light, a gentle fill and a quiet rim light, with soft natural shadows that model every "
        "form. Faces and hands are softly blended, with gentle brushwork still visible; clothes and backgrounds "
        "show confident, visible brushwork, and backgrounds have real depth and atmosphere, a little softer "
        "than the figures. Likeness comes first: the face shape, eyes, eyebrows, nose, mouth, complexion, "
        "hairline and hairstyle stay so close to the reference that a parent knows their own child at a "
        "glance. Warm, gentle and dignified. Unmistakably a hand-made painting, never a photograph."
    ),
    "negative": (
        "- No cartoon, comic, anime or picture-book stylization: no enlarged heads or eyes, no tiny button "
        "noses, no faces reduced to simple circles, no drawn or ink outlines.\n"
        "- No flat or cel shading, no watercolor washes or paper grain, no 3D-render, clay, plastic or doll "
        "look.\n"
        "- No photograph or camera look: no lens blur or bokeh, no film grain, no HDR; the brushwork stays "
        "visible.\n"
        "- No uncanny or waxy faces, no glassy eyes; children look exactly their real age.\n"
        "- No clumsy hands: hands are painted carefully, with five fingers on each visible hand."
    ),
    "version": 3,
}
V2: dict[str, Any] = {
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
}

styles = sa.table(
    "art_styles",
    sa.column("slug", sa.String),
    sa.column("prompt", sa.Text),
    sa.column("negative", sa.Text),
    sa.column("version", sa.Integer),
)


def record(conn: Connection, forward: bool) -> None:
    """The row's record of the guide: v2 → v3 (forward) or back; a row in any other state is left alone."""
    source, target = (V2, V3) if forward else (V3, V2)
    stmt = styles.update().where(styles.c.slug == SLUG, styles.c.version == source["version"])
    conn.execute(stmt.values(**target))


def upgrade() -> None:
    record(op.get_bind(), forward=True)


def downgrade() -> None:
    record(op.get_bind(), forward=False)
