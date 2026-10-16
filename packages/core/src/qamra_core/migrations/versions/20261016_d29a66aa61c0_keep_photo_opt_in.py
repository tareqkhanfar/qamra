"""Keep the child's photo for later books: an optional, separate choice of the guardian (owner, 2026-10-16).

Revision ID: d29a66aa61c0
Revises: 2351cdc1195c
Create Date: 2026-10-16

«اعطي خيار صلاحية للأهالي إنهم إذا بدهم يخلّو صورة ابنهم ع الموقع». Off by default; the choice is its own
consent row (`consents.scope = 'photo_keep'`, version `photo-keep-2026-10`, with time, IP and user agent):

1. `consents.withdrawn_at` (timestamptz, nullable): when the guardian turned the choice off (or the kept photo
   reached its retention and was deleted). A photo-processing consent never gets one.
2. `child_photos.last_used_at` (timestamptz, nullable): the last time a drawing or cover was made from the photo
   or it was chosen to be kept. A kept photo is deleted `kept_photo_retention_months` (admin, default 12)
   after it; None falls back to the upload time.

Schema only, nothing to backfill: no photo is kept until a guardian opts in. Downgrade drops both columns; the
choices then read as never made, so the next cleanup applies the 24-hour rule to those photos again.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "d29a66aa61c0"
down_revision: str | None = "2351cdc1195c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consents", sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_photos", sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("child_photos", "last_used_at")
    op.drop_column("consents", "withdrawn_at")
