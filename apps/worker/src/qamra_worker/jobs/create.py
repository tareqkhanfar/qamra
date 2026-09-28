"""Create-flow jobs: the child's character sheet, drawn before the parent picks a story (design Create5).

The book preview itself is `jobs.books.generate_book(book_id, "preview")`, the same pipeline as every book.
"""

import asyncio
from typing import Any

import structlog
from sqlalchemy.orm import Session

from qamra_core.db.models import Character, CharacterStatus
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_runtime
from qamra_worker.jobs.books import CostSink, _character, resolved_settings
from qamra_worker.settings import get_settings

log = structlog.get_logger()


async def draw_character(
    db: Session, storage: ObjectStorage, character: Character, *, offline: bool | str = False
) -> dict[str, Any]:
    rt = make_runtime(ai_settings(resolved_settings(db), get_settings(), offline=offline))
    rt.on_cost = CostSink(db, None, character.child_id)  # a child's character is reused by all their books
    try:
        await _character(db, storage, rt, character)
    except Exception:
        db.rollback()
        character.status = CharacterStatus.failed
        db.commit()
        log.exception("character.failed", character=str(character.id))
        raise
    return {"status": character.status.value}


def generate_character(character_id: str) -> dict[str, Any]:
    """RQ entry point, enqueued by the create flow."""
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        character = db.get(Character, character_id)
        if character is None:
            return {"status": "missing"}
        return asyncio.run(draw_character(db, storage, character))
