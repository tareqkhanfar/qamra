from api_helpers import make_admin
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_the_gpu_card_is_off_until_a_server_is_set(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    card = (await client.get("/api/admin/self-hosted")).json()
    assert card["provider"] == "fal" and card["configured"] is False and card["health"] is None
    assert card["approved"] is False and card["recommendation"] == "no_data"


async def test_only_settings_staff_see_the_gpu_card(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb, email="print@example.com", roles=("production",))
    assert (await client.get("/api/admin/self-hosted")).status_code == 403
