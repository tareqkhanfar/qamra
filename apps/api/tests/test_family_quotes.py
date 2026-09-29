"""«مغامراتي مع عائلتي» for organizations (Addendum 7 §8): a quote request with a private back-cover logo
(checked and re-encoded), staff see it, and price it from the printer's tiers only once the real prices are in
(10+ copies wait while the tiers are estimates: Tareq, 2026-09-28)."""

import io
from datetime import date, timedelta

from api_helpers import make_admin
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.models import Lead
from qamra_core.db.store import Variant
from qamra_core.storage import ObjectStorage

FORM = {
    "org_name": "روضة الأمل",
    "city": "البيرة",
    "contact_name": "أ. سلمى",
    "contact_role": "المديرة",
    "phone": "0591234567",
    "email": "info@alamal.example",
    "quantity": "40",
}


def _png(size: tuple[int, int], fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "#2E9FD6").save(buf, format=fmt)
    return buf.getvalue()


async def test_an_organization_asks_for_a_quote_with_its_logo(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await seed_store(adb)
    later = (date.today() + timedelta(days=40)).isoformat()
    r = await client.post(
        "/api/leads/family-quote",
        data={**FORM, "desired_date": later, "notes": "نريد الشعار على الغلاف الخلفي"},
        files={"logo": ("logo.png", _png((800, 400)), "image/png")},
    )
    assert r.status_code == 201, r.text
    assert r.json() == {"ok": True, "request_only": True}  # a request, never an order
    lead = (await adb.execute(select(Lead).where(Lead.kind == "family_quote"))).scalar_one()
    assert lead.details["quantity"] == 40 and lead.details["email"] == "info@alamal.example"
    assert lead.details["logo_key"] == f"leads/{lead.id}/logo.png" and lead.details["logo_px"] == [800, 400]
    assert storage.get(lead.details["logo_key"]).startswith(b"\x89PNG")  # re-encoded, kept private

    for bad_data, bad_files in (
        ({**FORM, "quantity": "5"}, None),  # fewer than 10: the store sells those
        ({**FORM, "phone": "call me"}, None),
        ({**FORM, "email": "not-an-email"}, None),
        (FORM, {"logo": ("logo.gif", _png((800, 400), "GIF"), "image/gif")}),  # PNG or JPG only
        (FORM, {"logo": ("logo.png", _png((120, 80)), "image/png")}),  # too small to print
    ):
        r = await client.post("/api/leads/family-quote", data=bad_data, files=bad_files)
        assert r.status_code == 422, (bad_data, r.text)

    # staff: the list, the logo (staff only), then the price from the tiers
    assert (await client.get("/api/admin/leads")).status_code in (401, 403)
    await make_admin(client, adb)
    [row] = (await client.get("/api/admin/leads", params={"kind": "family_quote"})).json()
    assert row["quantity"] == 40 and row["has_logo"] and row["quote"] is None
    logo = await client.get(f"/api/admin/leads/{row['id']}/logo")
    assert logo.status_code == 200 and "no-store" in logo.headers["cache-control"]

    pending = await client.post(f"/api/admin/leads/{row['id']}/quote")
    assert pending.status_code == 409 and pending.json()["error"]["code"] == "bulk_price_pending"
    variant = (await adb.execute(select(Variant).where(Variant.sku == "family-wireo"))).scalar_one()
    variant.print_cost_tiers = [
        {"min_qty": 1, "unit_ils": 28},
        {"min_qty": 10, "unit_ils": 22},
    ]  # the real quote
    await adb.commit()
    priced = (await client.post(f"/api/admin/leads/{row['id']}/quote")).json()
    quote = priced["quote"]
    assert quote["quantity"] == 40 and quote["currency"] == "ILS"
    assert float(quote["unit_price"]) > float(quote["unit_cost"]) > 22  # above the printer's price per copy
    assert float(quote["total"]) == float(quote["unit_price"]) * 40

    done = await client.patch(f"/api/admin/leads/{row['id']}", json={"status": "contacted"})
    assert done.status_code == 200 and done.json()["status"] == "contacted"
