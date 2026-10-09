"""The owner's contact details (2026-10-09): the website reads them from the public settings, and the data
migration sets them whatever was saved before (the emails only while they are still the example)."""

from typing import Any

from alembic import command
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from qamra_core.migrations import alembic_config

REVISION = "6a87cac7a912"
PREVIOUS = "18342eeba4e4"
OWNER = {
    "support_phone": "+970595870228",
    "support_whatsapp": "+972595870228",
    "sales_whatsapp": "+972595870228",
    "support_email": "info@qamra.app",
    "sales_email": "info@qamra.app",
}


async def _stored(adb: AsyncSession) -> dict[str, Any]:
    query = text("SELECT key, value FROM app_settings WHERE key = ANY(:keys)")
    rows = await adb.execute(query, {"keys": list(OWNER)})
    return {key: value for key, value in rows.all()}


async def test_the_website_gets_the_owners_numbers(client: AsyncClient) -> None:
    public = (await client.get("/api/settings/public")).json()
    assert {k: public[k] for k in OWNER} == OWNER


async def test_the_migration_sets_the_numbers_and_replaces_only_example_emails(adb: AsyncSession) -> None:
    def run(session: Session, revision: str, up: bool) -> None:
        cfg = alembic_config("postgresql+psycopg://unused/x_test")
        cfg.attributes["connection"] = session.connection()
        (command.upgrade if up else command.downgrade)(cfg, revision)

    await adb.run_sync(run, PREVIOUS, False)
    assert "support_phone" not in await _stored(adb)
    await adb.execute(
        text(
            "INSERT INTO app_settings (key, value) VALUES"
            " ('support_whatsapp', '\"+970599111222\"'), ('support_email', '\"support@example.com\"'),"
            " ('sales_email', '\"sales@school.ps\"')"
            " ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        )
    )
    await adb.run_sync(run, REVISION, True)
    stored = await _stored(adb)
    assert stored == {**OWNER, "sales_email": "sales@school.ps"}  # a real address an admin saved stays
