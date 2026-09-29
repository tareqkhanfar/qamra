"""The template studio's background work (Addendum 4 §3.5).

- `translate_theme_version`: the English draft of a theme version's texts by the text model. It is queued
  only when an editor asks for it after seeing the estimate, and its cost is logged. A failed draft is marked
  failed and not retried (a retry would pay again for the same answer).
- `run_scheduled_publish` (cron, every 5 minutes): approved Classic templates whose publish date has come go
  live. A template that is no longer approved by then keeps its status, and its date is cleared.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.pipeline.theme import Theme
from qamra_ai.pipeline.translate import apply_translation, translate
from qamra_core.db.classic import ClassicTemplate, TemplateJob, TemplateStatus
from qamra_core.db.models import AuditLog, GenerationCost
from qamra_core.db.studio import ThemeVersion, ThemeVersionStatus
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_runtime
from qamra_worker.jobs.books import resolved_settings
from qamra_worker.settings import get_settings

log = structlog.get_logger()
BUSY = (TemplateJob.queued, TemplateJob.running)


def publish_due(db: Session, now: datetime | None = None) -> dict[str, list[str]]:
    """Scheduled go-lives whose time has come. A template busy drawing waits for the next run."""
    now = now or datetime.now(UTC)
    q = select(ClassicTemplate).where(
        ClassicTemplate.publish_at.is_not(None), ClassicTemplate.publish_at <= now
    )
    out: dict[str, list[str]] = {"published": [], "missed": []}
    for t in db.execute(q).scalars().all():
        if t.status == TemplateStatus.approved and t.job in BUSY:
            continue
        when, t.publish_at = t.publish_at, None
        data: dict[str, Any] = {"scheduled": when.isoformat() if when else None}
        if t.status == TemplateStatus.approved:
            t.status, t.live_at = TemplateStatus.live, now
            action, data = "classic.template_status", {**data, "from": "approved", "to": "live"}
            out["published"].append(str(t.id))
        else:
            action, data = "classic.template_schedule_missed", {**data, "status": t.status.value}
            out["missed"].append(str(t.id))
        db.add(AuditLog(action=action, entity_type="classic_template", entity_id=str(t.id), data=data))
    db.commit()
    return out


def run_scheduled_publish() -> dict[str, list[str]]:
    """RQ cron entry point."""
    context.init_process()
    with context.db_session() as db:
        out = publish_due(db)
    if out["published"] or out["missed"]:
        log.info("studio.scheduled_publish", published=len(out["published"]), missed=len(out["missed"]))
    return out


def _state(v: ThemeVersion, **state: Any) -> None:
    before = (v.meta or {}).get("translate") or {}
    v.meta = {**(v.meta or {}), "translate": {**before, **state, "at": datetime.now(UTC).isoformat()}}


def run_translation(db: Session, v: ThemeVersion) -> dict[str, Any]:
    """One text-model call → the version's English texts (it must still be a draft that follows the rules)."""
    rt = make_runtime(ai_settings(resolved_settings(db), get_settings()))
    theme = Theme.model_validate(v.definition)
    result = asyncio.run(translate(rt, theme, step=f"translate:{theme.slug}:v{v.version}"))
    for e in rt.ledger.entries:  # the cost is spent whatever happens next
        db.add(GenerationCost(step=e.step[:64], provider=e.provider, model=e.model, units=e.units,
                              usd=Decimal(str(e.usd)), estimated=e.estimated))  # fmt: skip
    cost = rt.ledger.total_usd
    _state(v, cost_usd=cost)
    db.commit()
    db.refresh(v)
    if v.status != ThemeVersionStatus.draft:
        raise ValueError("the version is no longer a draft")
    definition = apply_translation(v.definition, result)
    Theme.model_validate(definition)  # the story rules (e.g. words per page) hold for the English too
    v.definition = definition
    _state(v, state="done", cost_usd=cost, error=None)
    db.add(AuditLog(action="theme.version_translated", entity_type="theme", entity_id=str(v.theme_id),
                    data={"theme": theme.slug, "version": v.version, "cost_usd": cost}))  # fmt: skip
    db.commit()
    return {"status": "done", "cost_usd": cost}


def translate_theme_version(version_id: str) -> dict[str, Any]:
    """RQ entry point: never raises after marking the draft, so RQ does not pay for a retry."""
    context.init_process()
    with context.db_session() as db:
        v = db.get(ThemeVersion, version_id)
        if v is None:
            return {"status": "missing"}
        _state(v, state="running")
        db.commit()
        try:
            return run_translation(db, v)
        except (ValidationError, ValueError, KeyError) as e:
            error = f"{type(e).__name__}: {str(e)[:300]}"
        except Exception as e:  # the provider already retried; keep the draft usable
            log.exception("studio.translate_failed", version=version_id)
            error = f"{type(e).__name__}: {str(e)[:300]}"
        db.rollback()
        v = db.get(ThemeVersion, version_id)
        if v is not None:
            _state(v, state="failed", error=error)
            db.commit()
        return {"status": "failed", "error": error}
