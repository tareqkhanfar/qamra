from api_helpers import register
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed import upsert_themes
from qamra_core.db.models import AuditLog, Book, Child, Gender, Lead, Locale, Theme, User

LEAD = {
    "org_name": "روضة الفراشات",
    "city": "رام الله",
    "contact_name": "أ. منى",
    "contact_role": "مديرة",
    "phone": "+970 59 123 4567",
    "children_count": 25,
    "event_date": "2027-06-20",
    "notes": "صفّان",
}


async def test_lead_is_stored_and_audited(client: AsyncClient, adb: AsyncSession) -> None:
    r = await client.post("/api/leads", json=LEAD)
    assert r.status_code == 201 and r.json() == {"ok": True}
    lead = (await adb.execute(select(Lead))).scalar_one()
    assert lead.org_name == "روضة الفراشات" and lead.children_count == 25 and lead.status == "new"
    assert (await adb.execute(select(AuditLog).where(AuditLog.action == "lead.created"))).scalar_one()


async def test_lead_validation(client: AsyncClient) -> None:
    r = await client.post("/api/leads", json={**LEAD, "phone": "call me maybe"})
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["phone"]


async def test_lead_rate_limit(client: AsyncClient) -> None:
    codes = [(await client.post("/api/leads", json=LEAD)).status_code for _ in range(6)]
    assert codes == [201] * 5 + [429]


async def test_family_lists_need_login(client: AsyncClient) -> None:
    assert (await client.get("/api/children")).status_code == 401
    assert (await client.get("/api/books")).status_code == 401


async def test_family_lists_only_own(client: AsyncClient, adb: AsyncSession) -> None:
    me = await register(client)
    await upsert_themes(adb)
    theme = (await adb.execute(select(Theme).where(Theme.slug == "first-day"))).scalar_one()
    other = User(email="other@example.com", full_name="O")
    adb.add(other)
    await adb.flush()
    mine = Child(
        guardian_user_id=__import__("uuid").UUID(me["id"]),
        first_name="ليان",
        gender=Gender.f,
        birth_year=2021,
    )
    theirs = Child(guardian_user_id=other.id, first_name="كرم", gender=Gender.m, birth_year=2020)
    adb.add_all([mine, theirs])
    await adb.flush()
    adb.add(
        Book(
            child_id=mine.id,
            theme_id=theme.id,
            theme_version=1,
            language=Locale.ar,
            art_style="watercolor",
            title="ليان في أوّل يوم بالروضة",
        )
    )
    await adb.commit()

    children = (await client.get("/api/children")).json()
    assert [c["first_name"] for c in children] == ["ليان"]
    books = (await client.get("/api/books")).json()
    assert len(books) == 1 and books[0]["theme_slug"] == "first-day" and books[0]["status"] == "draft"
