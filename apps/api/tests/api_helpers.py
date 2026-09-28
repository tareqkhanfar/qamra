from httpx import AsyncClient


async def register(
    client: AsyncClient,
    email: str = "salma.mom@example.com",
    password: str = "moonlight-2026",
    name: str = "أم سلمى",
) -> dict:  # type: ignore[type-arg]
    r = await client.post(
        "/api/auth/register", json={"email": email, "password": password, "full_name": name}
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]
