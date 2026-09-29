"""The illustrated-family add-on (Addendum 7 §7): one family member's character sheet from their photo, drawn
with the same runtime as the child's (the configured, approved providers, fakes offline) and the same cost
log. The parent approves it; the photo is then deleted by the cleanup job (`maintenance`), and the sheet is
reused by every family book of the child.
"""

import asyncio
from typing import Any

import structlog
from sqlalchemy.orm import Session

from qamra_ai.pipeline.family_member import MemberSpec, member_request
from qamra_ai.pipeline.theme import load_style
from qamra_core.db.models import FamilyMember, FamilyMemberStatus
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_runtime
from qamra_worker.jobs.books import CostSink, resolved_settings
from qamra_worker.settings import get_settings

log = structlog.get_logger()


def sheet_key(member: FamilyMember, attempt: int) -> str:
    return f"children/{member.child_id}/family/{member.id}/sheet-{attempt}.png"


async def draw_member(
    db: Session, storage: ObjectStorage, member: FamilyMember, *, offline: bool | str = False
) -> dict[str, Any]:
    if not member.photo_key or not member.consented_at:
        raise ValueError("a family member is drawn from a consented photo only")
    rt = make_runtime(ai_settings(resolved_settings(db), get_settings(), offline=offline))
    rt.on_cost = CostSink(db, None, member.child_id)  # counted with the child's characters
    attempt = member.regen_count
    try:
        sheet = await rt.draw(
            member_request(
                MemberSpec(member.relation, member.adult, member.scarf),
                [storage.get(member.photo_key)],
                load_style(member.art_style or "watercolor"),
                attempt=attempt,
            )
        )
    except Exception:
        db.rollback()
        member.status = FamilyMemberStatus.failed
        db.commit()
        log.exception("family_member.failed", member=str(member.id))
        raise
    key = sheet_key(member, attempt)
    storage.put(key, sheet.data, sheet.mime)
    member.sheet_key = key
    member.status = FamilyMemberStatus.ready
    member.provider = str(sheet.params.get("provider", rt.image.name))[:32]
    member.model = str(sheet.params.get("model", rt.image.model))[:100]
    member.params = {**(member.params or {}), "attempt": attempt}
    db.commit()
    return {"status": member.status.value}


def generate_member(member_id: str) -> dict[str, Any]:
    """RQ entry point, enqueued by `routers.family_members`."""
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        member = db.get(FamilyMember, member_id)
        if member is None:
            return {"status": "missing"}
        return asyncio.run(draw_member(db, storage, member))
