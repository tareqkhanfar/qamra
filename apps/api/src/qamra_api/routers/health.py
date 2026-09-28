"""Liveness and readiness."""

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from qamra_api.deps import RedisDep, SessionDep, StorageDep

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("")
async def ready(db: SessionDep, redis: RedisDep, storage: StorageDep) -> JSONResponse:
    checks: dict[str, bool] = {}
    try:
        await db.execute(text("select 1"))
        checks["db"] = True
    except Exception:
        checks["db"] = False
    try:
        checks["redis"] = bool(await redis.ping())
    except Exception:
        checks["redis"] = False
    try:
        checks["storage"] = await asyncio.to_thread(storage.ping)
    except Exception:
        checks["storage"] = False
    ok = all(checks.values())
    return JSONResponse({"status": "ok" if ok else "degraded", **checks}, status_code=200 if ok else 503)
