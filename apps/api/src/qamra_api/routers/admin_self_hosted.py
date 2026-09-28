"""The self-hosted GPU option in the admin (Addendum 4 §8): is the server up, and is it worth it yet?

Switching Classic edits to our own GPU pays off only when the monthly Classic image spend on the API is
higher than the GPU server's monthly cost. The server's token is used here only to call its health check.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from qamra_ai.image.comfy import APPROVED_WORKFLOWS, health
from qamra_api import runtime_settings
from qamra_api.deps import SessionDep, SettingsDep, require_permission
from qamra_core.db.models import Book, GenerationCost

router = APIRouter(
    prefix="/api/admin/self-hosted", tags=["admin"], dependencies=[Depends(require_permission("settings"))]
)
DAYS = 30


class SelfHostedOut(BaseModel):
    provider: str  # what draws Classic edits now: fal or self_hosted
    configured: bool
    workflow: str
    approved: bool  # the workflow's model license is approved (docs/licenses.md)
    health: dict[str, Any] | None
    spend_usd: Decimal  # Classic image spend on the API over the last 30 days
    images: int
    gpu_monthly_usd: Decimal
    recommendation: Literal["no_data", "stay_on_api", "consider_gpu"]


@router.get("")
async def self_hosted(db: SessionDep, settings: SettingsDep) -> SelfHostedOut:
    values = (await runtime_settings.current(db, settings)).values
    url, workflow = str(values["self_hosted_url"] or ""), str(values["self_hosted_workflow"] or "")
    since = datetime.now(UTC) - timedelta(days=DAYS)
    spend, images = (
        await db.execute(
            select(func.coalesce(func.sum(GenerationCost.usd), 0), func.count(GenerationCost.id))
            .join(Book, Book.id == GenerationCost.book_id)
            .where(
                GenerationCost.created_at >= since,
                GenerationCost.provider != "self_hosted",
                Book.generation["line"].astext == "classic",
                ~GenerationCost.step.startswith("qa"),
                ~GenerationCost.step.startswith("story"),
            )
        )
    ).one()
    gpu = Decimal(str(values["gpu_monthly_cost_usd"]))
    recommendation: Literal["no_data", "stay_on_api", "consider_gpu"] = (
        "no_data" if not images or not gpu else "consider_gpu" if spend > gpu else "stay_on_api"
    )
    return SelfHostedOut(
        provider=str(values["classic_image_provider"]),
        configured=bool(url),
        workflow=workflow,
        approved=workflow in APPROVED_WORKFLOWS,
        health=await health(url, str(values["self_hosted_token"] or "") or None) if url else None,
        spend_usd=Decimal(str(spend)).quantize(Decimal("0.01")),
        images=int(images),
        gpu_monthly_usd=gpu,
        recommendation=recommendation,
    )
