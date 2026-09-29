"""«ارسم صاحبك» (Addendum 1 §1.4): draw 2 companion options from the child's cleaned drawing, for the parent.

The drawing is reviewed first (safe, really a drawing); each option then gets a fidelity and safety check
against the drawing, and an unsafe option is dropped. Costs go to the child (a companion is drawn once and
reused by all their books, so no book's budget pays for it). A drawing that is rejected, or a round that
fails on our side, is not one of the parent's 3 free redraws.
"""

import asyncio
from typing import Any

import structlog
from sqlalchemy.orm import Session

from qamra_ai.pipeline.companion import DrawingRejected, generate_companion_options, score_fidelity
from qamra_ai.pipeline.models import CompanionSpec
from qamra_ai.pipeline.theme import load_style
from qamra_core.db.models import Companion, CompanionStatus
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_runtime
from qamra_worker.jobs.books import CostSink, resolved_settings
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.companions")

GENERATION_FAILED = {
    "code": "generation_failed",
    "ar": "تعذّر رسم الصاحب هذه المرة. حاولوا مرة أخرى، لن تُحسب من المحاولات المجانية.",
    "en": "We couldn't draw the companion this time. Try again; it won't count as a free redraw.",
}
UNSAFE = {
    "code": "companion_unsafe",
    "ar": "لم يخرج الرسم مناسبًا لكتاب أطفال. حاولوا مرة أخرى، لن تُحسب من المحاولات المجانية.",
    "en": "The drawing didn't come out right for a children's book. Try again; it won't count as a redraw.",
}


def _failed(db: Session, comp: Companion, error: dict[str, str]) -> dict[str, Any]:
    params = dict(comp.params or {})
    params["failed_rounds"] = int(params.get("failed_rounds", 0)) + 1
    params["error"] = error
    comp.params = params
    comp.status = CompanionStatus.failed
    db.commit()
    return {"status": "failed", "reason": error["code"]}


async def draw_options(
    db: Session, storage: ObjectStorage, comp: Companion, *, offline: bool | str = False
) -> dict[str, Any]:
    rt = make_runtime(ai_settings(resolved_settings(db), get_settings(), offline=offline))
    rt.on_cost = CostSink(db, None, comp.child_id)
    if not comp.cleaned_key:
        return _failed(db, comp, GENERATION_FAILED)
    style = str((comp.params or {}).get("style") or "watercolor")
    spec = CompanionSpec(
        name=comp.name,
        type_hint=comp.type_hint.value,
        type_other=comp.type_other,
        traits=comp.traits,
        from_drawing=True,
    )
    cleaned = storage.get(comp.cleaned_key)
    round_ = max(1, comp.regen_count or 1)
    try:
        result = await generate_companion_options(rt, cleaned, spec, load_style(style), round_=round_)
        checks = await asyncio.gather(*(score_fidelity(rt, cleaned, o) for o in result.options))
    except DrawingRejected as e:
        log.info("companion.drawing_rejected", companion=str(comp.id), reason=str(e)[:200])
        return _failed(
            db, comp, {"code": "drawing_rejected", "ar": e.user_message_ar, "en": e.user_message_en}
        )
    except Exception:
        db.rollback()
        log.exception("companion.failed", companion=str(comp.id))
        return _failed(db, comp, GENERATION_FAILED)
    kept = []
    for n, (image, check) in enumerate(zip(result.options, checks, strict=True), start=1):
        if not check.safe:
            continue
        key = f"children/{comp.child_id}/companions/{comp.id}/option-{round_}-{n}.png"
        storage.put(key, image.data, image.mime)
        kept.append(
            {
                "key": key,
                "round": round_,
                "provider": str(image.params.get("provider", rt.image.name)),
                "model": str(image.params.get("model", rt.image.model)),
                "fidelity": check.score,  # 1–5 vs the drawing (Addendum 1 acceptance: parents recognize it)
            }
        )
    if not kept:
        return _failed(db, comp, UNSAFE)
    comp.options = [*(comp.options or []), *kept]
    comp.description_en = result.spec.description_en
    comp.params = {**(comp.params or {}), "key_features": result.review.key_features, "error": None}
    comp.status = CompanionStatus.ready
    db.commit()
    return {"status": "ready", "options": len(kept)}


def generate_companion(companion_id: str) -> dict[str, Any]:
    """RQ entry point, enqueued by the create flow."""
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        comp = db.get(Companion, companion_id)
        if comp is None or comp.status != CompanionStatus.generating:
            return {"status": "missing"}
        return asyncio.run(draw_options(db, storage, comp))
