"""The parent's framing of the child's photo (Tareq, 2026-10-10: «اسحب فيها يمين يسار فوق وتحت»).

Revision ID: 3d041b8fdbf1
Revises: a58eeffa5362
Create Date: 2026-10-10

On the photo step the parent drags, zooms and turns the photo until the face sits in the face-guide oval, and may
change it again after the upload or after the character is drawn. The framing is kept as numbers on the photo,
never as a second copy of the child's face:

1. `child_photos.crop` (JSONB, nullable): `{x, y, w, h}` fractions (0–1) of the stored original and `rotate`
   (0/90/180/270, clockwise). The photo check and every image-model call use that cut-out
   (`qamra_ai.pipeline.photo_crop`). None: the whole photo, as for every photo uploaded before.
2. `child_photos.crop_saved_at` (timestamptz, nullable): when the parent last moved it after the upload. A newer
   framing, like a newer photo, lets the next «ارسم من جديد» draw again instead of reusing the approved character.

Both columns go when the photo is deleted (the 24-hour job, "delete all my child's data"). Schema only, nothing
to backfill. Downgrade drops both columns (photos are then used whole again).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "3d041b8fdbf1"
down_revision: str | None = "a58eeffa5362"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("child_photos", sa.Column("crop", JSONB(), nullable=True))
    op.add_column("child_photos", sa.Column("crop_saved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("child_photos", "crop_saved_at")
    op.drop_column("child_photos", "crop")
