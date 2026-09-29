"""The printer's links (Phase 3): the batch files behind a token from the printer's email.

The token's sha256 is on the batch and expires after `printer_link_days`; resending a batch replaces it.
A file link redirects to a signed storage URL of 10 minutes (the privacy cap is 15), so a forwarded email
stops opening files once the token expires or is replaced. No page here lists personal data: the CSV has
order codes, formats, copies and file names only.
"""

import re
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from qamra_api import ratelimit
from qamra_api.auth.router import client_ip
from qamra_api.deps import RedisDep, SessionDep, StorageDep
from qamra_api.errors import ApiError
from qamra_core.db.models import PrintBatch, PrintBatchStatus
from qamra_core.printing import batch_code, manifest_csv, token_hash

router = APIRouter(prefix="/api/printer", tags=["printer"])
SIGNED_SECONDS = 600
HITS_PER_IP_PER_HOUR = 600
TOKEN = re.compile(r"^[A-Za-z0-9_-]{30,64}$")
LIVE = (PrintBatchStatus.sent, PrintBatchStatus.printing, PrintBatchStatus.done)
NO_STORE = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow",
}


async def _batch(db: SessionDep, redis: RedisDep, request: Request, token: str) -> PrintBatch:
    if await ratelimit.hit(redis, f"rl:printer:{client_ip(request)}", 3600) > HITS_PER_IP_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    if not TOKEN.match(token):
        raise ApiError("link_expired", 404)
    batch = (
        await db.execute(select(PrintBatch).where(PrintBatch.printer_token_hash == token_hash(token)))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if (
        batch is None
        or batch.status not in LIVE
        or batch.printer_token_expires_at is None
        or batch.printer_token_expires_at <= now
    ):
        raise ApiError("link_expired", 404)  # the same answer for unknown, replaced and expired links
    return batch


@router.get("/{token}/files/{n}/{kind}")
async def printer_file(
    token: str,
    n: int,
    kind: Literal["interior", "cover"],
    request: Request,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
) -> Response:
    batch = await _batch(db, redis, request, token)
    item = next((i for i in batch.manifest.get("items", []) if int(i["n"]) == n), None)
    key = item.get(f"{kind}_key") if item else None
    if not key:
        raise ApiError("not_found", 404)
    if not storage.exists(key):
        raise ApiError("not_found", 404)
    return RedirectResponse(storage.signed_get_url(key, SIGNED_SECONDS), status_code=302, headers=NO_STORE)


@router.get("/{token}/files/{n}/inserts/{name}")
async def printer_insert(
    token: str,
    n: int,
    name: str,
    request: Request,
    db: SessionDep,
    redis: RedisDep,
    storage: StorageDep,
) -> Response:
    """A family book's insert sheet (stickers or card stock), by the name the manifest lists it under."""
    batch = await _batch(db, redis, request, token)
    item = next((i for i in batch.manifest.get("items", []) if int(i["n"]) == n), None)
    key = (item.get("inserts") or {}).get(name) if item else None
    if not key or not storage.exists(key):
        raise ApiError("not_found", 404)
    return RedirectResponse(storage.signed_get_url(key, SIGNED_SECONDS), status_code=302, headers=NO_STORE)


@router.get("/{token}/manifest.csv")
async def printer_manifest(token: str, request: Request, db: SessionDep, redis: RedisDep) -> Response:
    batch = await _batch(db, redis, request, token)
    return Response(
        manifest_csv(batch.manifest),
        media_type="text/csv; charset=utf-8",
        headers={
            **NO_STORE,
            "Content-Disposition": f'attachment; filename="{batch_code(batch.id, batch.batch_date)}.csv"',
        },
    )
