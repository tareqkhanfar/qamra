"""Privacy cleanup (CLAUDE.md §3, Addendum 1 §1): originals are deleted after approval + 24h,
abandoned drafts after 30 days. Runs every 15 minutes from `rq cron`."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.models import AuditLog, Book, BookStatus, ChildPhoto, Companion, FamilyMember, PhotoStatus
from qamra_core.settings import CoreSettings
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.maintenance")


@dataclass
class CleanupSummary:
    photos_deleted: int = 0
    drawings_deleted: int = 0
    drafts_deleted: int = 0
    family_photos_deleted: int = 0  # the illustrated-family add-on's photos, 24 h after approval


def _audit(db: Session, action: str, entity_type: str, entity_id: object) -> None:
    db.add(AuditLog(actor_user_id=None, action=action, entity_type=entity_type, entity_id=str(entity_id)))


def cleanup_expired_media(
    db: Session, storage: ObjectStorage, settings: CoreSettings, now: datetime | None = None
) -> CleanupSummary:
    now = now or datetime.now(UTC)
    summary = CleanupSummary()

    photos = db.scalars(
        select(ChildPhoto)
        .where(ChildPhoto.delete_after <= now, ChildPhoto.deleted_at.is_(None))
        .with_for_update(skip_locked=True)
    ).all()
    for photo in photos:
        if photo.storage_key:
            storage.delete(photo.storage_key)  # storage first: a crash leaves a row to retry, never a file
        photo.storage_key = None
        photo.status = PhotoStatus.deleted
        photo.deleted_at = now
        _audit(db, "photo.auto_deleted", "child_photo", photo.id)
        summary.photos_deleted += 1
    db.commit()

    companions = db.scalars(
        select(Companion)
        .where(Companion.drawing_delete_after <= now, Companion.drawing_key.is_not(None))
        .with_for_update(skip_locked=True)
    ).all()
    for comp in companions:
        if comp.drawing_key is None:  # filtered by the query; defensive for concurrent edits
            continue
        storage.delete(comp.drawing_key)
        comp.drawing_key = None
        _audit(db, "drawing.auto_deleted", "companion", comp.id)
        summary.drawings_deleted += 1
    db.commit()

    members = db.scalars(
        select(FamilyMember)
        .where(FamilyMember.photo_delete_after <= now, FamilyMember.photo_key.is_not(None))
        .with_for_update(skip_locked=True)
    ).all()
    for member in members:
        if member.photo_key:
            storage.delete(member.photo_key)  # storage first: a crash leaves a row to retry, never a file
        member.photo_key = None
        _audit(db, "family_photo.auto_deleted", "family_member", member.id)
        summary.family_photos_deleted += 1
    db.commit()

    cutoff = now - timedelta(days=settings.draft_retention_days)
    drafts = db.scalars(
        select(Book)
        .where(Book.status == BookStatus.draft, Book.updated_at < cutoff)
        .with_for_update(skip_locked=True)
    ).all()
    for book in drafts:
        storage.delete_prefix(f"children/{book.child_id}/books/{book.id}/")
        _audit(db, "book.draft_expired", "book", book.id)
        db.delete(book)
        summary.drafts_deleted += 1
    db.commit()
    return summary


def run_cleanup() -> dict[str, int]:
    """RQ entry point."""
    context.init_process()
    with context.db_session() as db:
        summary = cleanup_expired_media(db, context.storage(), get_settings())
    log.info("cleanup.done", **asdict(summary))
    return asdict(summary)


def ping() -> str:
    return "pong"
