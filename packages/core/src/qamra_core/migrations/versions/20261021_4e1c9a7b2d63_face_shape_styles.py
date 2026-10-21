"""Cartoon and 3D, guide version 4: the child's own face shape, never a rounder, wider, younger face.

Revision ID: 4e1c9a7b2d63
Revises: 8c3f5a1d7e42
Create Date: 2026-10-21

The owner's report (2026-10-21): in the cartoon and 3D styles the child's face came out rounder, wider and
younger than his child's. Cartoon v4 (`qamra_ai/prompts/style/cartoon.md`) keeps the simple shapes for the
backgrounds and draws the child as a cartoonist's portrait of a real child, on the photo's own outline; 3D v4
(`3d.md`) makes the child a stylized 3D likeness, the head modelled on the photo, with the photo's own eyes,
instead of an "appealing" animated-film face.

Generation reads the guide files; the `prompt`, `negative` and `version` columns keep a record, as
`5b7e2c9d4f10` did for watercolor v4. A row is touched only at the version it is moved from, so it is safe to
run again; down puts v3 back.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "4e1c9a7b2d63"
down_revision: str | None = "8c3f5a1d7e42"
branch_labels = None
depends_on = None

RECORDS: dict[str, dict[str, dict[str, Any]]] = {
    "cartoon": {
        "v4": {
            "prompt": "Bright, clean 2D cartoon picture-book illustration: bold flat color blocks with crisp two-tone cel shading, smooth confident outlines drawn in a darker shade of each fill color, and crisp print-ready edges. A cheerful saturated palette of sky blue, sunny yellow, grass green, coral and warm cream, bright but never neon. Clear silhouettes, and backgrounds made of a few large simple shapes. People are drawn like a cartoonist's portrait of a real child: the outline of the head, face, jaw and chin and the places of the features follow the reference, simplified in line and color but never reshaped. Each child keeps their own face shape and proportions, eye size, nose, smile, skin tone, hairstyle and real age, clearly recognizable.",
            "negative": "- No photorealism, no 3D rendering, no watercolor textures or paper grain, no pure-black heavy outlines.\n- No oversized eyes or heads, no round, wide or chubby cartoon face, no button nose, no short chin, no baby face, no generic cartoon child.\n- No neon colors, no busy patterns, no anime.",
            "version": 4,
        },
        "v3": {
            "prompt": "Bright, clean 2D cartoon picture-book illustration: bold flat color blocks with soft two-tone cel shading, smooth confident outlines drawn in a darker shade of each fill color, and crisp print-ready edges. A cheerful saturated palette of sky blue, sunny yellow, grass green, coral and warm cream, bright but never neon. Simple clean shapes, clear silhouettes, and backgrounds made of a few large simple shapes. The cartoon is in the line and the color, never in the child's face: each child keeps their own face shape and proportions, eye size, nose, smile, skin tone, hairstyle and real age, clearly recognizable.",
            "negative": "- No photorealism, no 3D rendering, no watercolor textures or paper grain, no pure-black heavy outlines.\n- No oversized eyes or heads, no baby face, no generic cartoon child.\n- No neon colors, no busy patterns, no anime.",
            "version": 3,
        },
    },
    "3d": {
        "v4": {
            "prompt": "A polished 3D animated-film look: a stylized CG rendering with subsurface-scattering skin, cinematic warm key light with a gentle rim light and soft volumetric glow, soft global illumination, and a shallow depth of field. Rich, saturated, warm colors; clean stylized materials (soft fabric, matte painted wood, smooth limestone); a few floating golden light particles in magical moments. Each child is a stylized 3D likeness of a real child, as if the head were sculpted from the photo: the real head shape and face proportions, the jaw, chin and cheeks as they are, and the eyes at the photo's own size and shape (narrow eyes stay narrow), with simplified, smooth surfaces. The stylization is in the materials, light and simplified detail, never in the child's face: each child keeps their own face shape and proportions, eye size, nose, smile, hair and its true color, skin tone and real age, clearly recognizable. Stylized, never realistic.",
            "negative": "- No photorealism, no realistic skin pores, no uncanny realism, no glossy plastic-doll or vinyl-toy look.\n- No oversized eyes or heads, no big round animated-film eyes, no round, wide or chubby face, no puffy baby cheeks, no button nose, no short chin, no baby face, no generic animated-film child face.\n- No dark, gritty or horror lighting. No existing film, studio, game or toy characters or their look-alikes.",
            "version": 4,
        },
        "v3": {
            "prompt": "A polished 3D animated-film look: appealing stylized rendering with soft subsurface-scattering skin, cinematic warm key light with a gentle rim light and soft volumetric glow, soft global illumination, and a shallow depth of field. Rich, saturated, warm colors; clean stylized materials (soft fabric, matte painted wood, smooth limestone); a few floating golden light particles in magical moments. The stylization is in the materials, light and simplified detail, never in the child's face: each child keeps their own face shape and proportions, eye size, nose, smile, hair, skin tone and real age, clearly recognizable. Stylized, never realistic.",
            "negative": "- No photorealism, no realistic skin pores, no uncanny realism, no glossy plastic-doll or vinyl-toy look.\n- No oversized eyes or heads, no baby face, no generic animated-film child face.\n- No dark, gritty or horror lighting. No existing film, studio, game or toy characters or their look-alikes.",
            "version": 3,
        },
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
    """Each style's record: v3 → v4 (forward) or back; a row in any other state is left alone."""
    for slug, versions in RECORDS.items():
        source, target = (versions["v3"], versions["v4"]) if forward else (versions["v4"], versions["v3"])
        stmt = styles.update().where(styles.c.slug == slug, styles.c.version == source["version"])
        conn.execute(stmt.values(**target))


def upgrade() -> None:
    record(op.get_bind(), forward=True)


def downgrade() -> None:
    record(op.get_bind(), forward=False)
