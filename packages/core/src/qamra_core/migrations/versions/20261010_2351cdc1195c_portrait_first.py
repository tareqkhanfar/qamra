"""Portrait first: the character's portrait is stored next to its sheet; 3D, cartoon and watercolor guides v3.

Revision ID: 2351cdc1195c
Revises: 968a4be3c42d
Create Date: 2026-10-10

The owner's likeness decision (2026-10-10): the child's character is drawn as a head-and-shoulders portrait in
the style first, then the sheet from the photo and the portrait. `characters.portrait_image_key` keeps the
portrait (under the child's storage prefix, so «حذف كل بيانات الطفل» removes it with the rest; the 30-day
cleanup of unapproved drawings deletes it with the sheet). Characters drawn before have none.

The 3D, cartoon and watercolor guides moved to v3: the child keeps their own face, proportions, eye size and age
(no more "slightly large heads", "big expressive/friendly eyes"). Generation reads the guide files; the
`prompt`, `negative` and `version` columns keep a record, as `c4e8a1f20b37`, `a58eeffa5362` and `968a4be3c42d` do.
A row is touched only at the version it is moved from, so it is safe to run again; down puts v2 back.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "2351cdc1195c"
down_revision: str | None = "968a4be3c42d"
branch_labels = None
depends_on = None

RECORDS: dict[str, dict[str, dict[str, Any]]] = {
    "3d": {
        "v3": {
            "prompt": "A polished 3D animated-film look: appealing stylized rendering with soft subsurface-scattering skin, cinematic warm key light with a gentle rim light and soft volumetric glow, soft global illumination, and a shallow depth of field. Rich, saturated, warm colors; clean stylized materials (soft fabric, matte painted wood, smooth limestone); a few floating golden light particles in magical moments. The stylization is in the materials, light and simplified detail, never in the child's face: each child keeps their own face shape and proportions, eye size, nose, smile, hair, skin tone and real age, clearly recognizable. Stylized, never realistic.",
            "negative": "- No photorealism, no realistic skin pores, no uncanny realism, no glossy plastic-doll or vinyl-toy look.\n- No oversized eyes or heads, no baby face, no generic animated-film child face.\n- No dark, gritty or horror lighting. No existing film, studio, game or toy characters or their look-alikes.",
            "version": 3,
        },
        "v2": {
            "prompt": "A polished 3D animated-film look: stylized, appealing characters with slightly large heads and big expressive eyes, soft subsurface-scattering skin, cinematic warm key light with a gentle rim light and soft volumetric glow, soft global illumination, and a shallow depth of field. Rich, saturated, warm colors; clean stylized materials (soft fabric, matte painted wood, smooth limestone); a few floating golden light particles in magical moments. Children keep their real face shape, skin tone, hairstyle and features, clearly recognizable: stylized, never realistic.",
            "negative": "- No photorealism, no realistic skin pores, no uncanny realism, no glossy plastic-doll or vinyl-toy look.\n- No dark, gritty or horror lighting. No existing film, studio, game or toy characters or their look-alikes.",
            "version": 2,
        },
    },
    "cartoon": {
        "v3": {
            "prompt": "Bright, clean 2D cartoon picture-book illustration: bold flat color blocks with soft two-tone cel shading, smooth confident outlines drawn in a darker shade of each fill color, and crisp print-ready edges. A cheerful saturated palette of sky blue, sunny yellow, grass green, coral and warm cream, bright but never neon. Simple clean shapes, clear silhouettes, and backgrounds made of a few large simple shapes. The cartoon is in the line and the color, never in the child's face: each child keeps their own face shape and proportions, eye size, nose, smile, skin tone, hairstyle and real age, clearly recognizable.",
            "negative": "- No photorealism, no 3D rendering, no watercolor textures or paper grain, no pure-black heavy outlines.\n- No oversized eyes or heads, no baby face, no generic cartoon child.\n- No neon colors, no busy patterns, no anime.",
            "version": 3,
        },
        "v2": {
            "prompt": "Bright, clean 2D cartoon picture-book illustration: bold flat color blocks with soft two-tone cel shading, smooth confident outlines drawn in a darker shade of each fill color, and crisp print-ready edges. A cheerful saturated palette of sky blue, sunny yellow, grass green, coral and warm cream, bright but never neon. Simple rounded shapes, big friendly eyes, clear silhouettes, and backgrounds made of a few large simple shapes. Children keep their real face shape, skin tone and hairstyle, with slightly large heads.",
            "negative": "- No photorealism, no 3D rendering, no watercolor textures or paper grain, no pure-black heavy outlines.\n- No neon colors, no busy patterns, no anime.",
            "version": 2,
        },
    },
    "watercolor": {
        "v3": {
            "prompt": "Premium watercolor and gouache children's picture-book painting on warm textured paper: rich, saturated color with real contrast, deep indigo and violet shadows, glowing honey-gold highlights, and golden-hour or moonlit light. Soft wet edges and visible paper grain, with crisp detail on faces and hands; atmospheric depth with soft foreground framing elements (leaves, arches, lanterns). Never flat or pale. Each child keeps their own face shape and proportions, eye size, hair and real age: the softness is in the paint, never a younger or rounder face.",
            "negative": "- No photorealism, no 3D-render look, no harsh black outlines, no neon colors, no anime.\n- No flat, pale or washed-out backgrounds.\n- No baby face, no generic round-faced child, no monochrome or sepia sketch.",
            "version": 3,
        },
        "v2": {
            "prompt": "Premium watercolor and gouache children's picture-book painting on warm textured paper: rich, saturated color with real contrast, deep indigo and violet shadows, glowing honey-gold highlights, and golden-hour or moonlit light. Soft wet edges and visible paper grain, with crisp detail on faces and hands; atmospheric depth with soft foreground framing elements (leaves, arches, lanterns). Never flat or pale.",
            "negative": "- No photorealism, no 3D-render look, no harsh black outlines, no neon colors, no anime.\n- No flat, pale or washed-out backgrounds.",
            "version": 2,
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
    """Each style's record: v2 → v3 (forward) or back; a row in any other state is left alone."""
    for slug, versions in RECORDS.items():
        source, target = (versions["v2"], versions["v3"]) if forward else (versions["v3"], versions["v2"])
        stmt = styles.update().where(styles.c.slug == slug, styles.c.version == source["version"])
        conn.execute(stmt.values(**target))


def upgrade() -> None:
    op.add_column("characters", sa.Column("portrait_image_key", sa.String(300), nullable=True))
    record(op.get_bind(), forward=True)


def downgrade() -> None:
    record(op.get_bind(), forward=False)
    op.drop_column("characters", "portrait_image_key")
