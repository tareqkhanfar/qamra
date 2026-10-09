"""The site's contact details are the owner's own (Tareq, 2026-10-09): calls +970, WhatsApp +972, info@qamra.app.

Revision ID: 6a87cac7a912
Revises: 18342eeba4e4
Create Date: 2026-10-09

The numbers are the owner's decision for the whole site, so they are set whatever the admin saved before:
`support_phone` (new: calls, +970 59 587 0228), `support_whatsapp` and `sales_whatsapp` (+972 59 587 0228).
The two emails become info@qamra.app only while they still hold the example placeholder; a real address an admin
saved stays. The registry's defaults (qamra_core.app_settings) carry the same values for a fresh database.
Change them later in Admin → الإعدادات → التواصل والمعلومات. Idempotent.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision: str = "6a87cac7a912"
down_revision: str | None = "18342eeba4e4"
branch_labels = None
depends_on = None

NUMBERS = {
    "support_phone": "+970595870228",
    "support_whatsapp": "+972595870228",
    "sales_whatsapp": "+972595870228",
}
EMAILS = {"support_email": "info@qamra.app", "sales_email": "info@qamra.app"}
PLACEHOLDERS = {"support_email": "support@example.com", "sales_email": "sales@example.com"}
# what the rows held before, for the downgrade (the example placeholders of the registry)
OLD_NUMBERS = {"support_whatsapp": "+970590000000", "sales_whatsapp": "+970590000001"}

settings = sa.table(
    "app_settings",
    sa.column("key", sa.String),
    sa.column("value", JSONB),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def _set(key: str, value: Any) -> None:
    stmt = insert(settings).values(key=key, value=value, updated_at=sa.func.now())
    op.execute(
        stmt.on_conflict_do_update(index_elements=["key"], set_={"value": value, "updated_at": sa.func.now()})
    )


def upgrade() -> None:
    for key, value in NUMBERS.items():
        _set(key, value)
    for key, value in EMAILS.items():
        op.execute(
            settings.update()
            .where(
                settings.c.key == key,
                settings.c.value == sa.cast(sa.literal(f'"{PLACEHOLDERS[key]}"'), JSONB),
            )
            .values(value=value, updated_at=sa.func.now())
        )


def downgrade() -> None:
    op.execute(settings.delete().where(settings.c.key == "support_phone"))
    for key, value in OLD_NUMBERS.items():
        _set(key, value)
