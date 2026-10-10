"""Privacy cleanup (CLAUDE.md §3, Addendum 1 §1): originals are deleted after approval + 24h,
abandoned drafts after 30 days. Runs every 15 minutes from `rq cron`.

It also releases stalled work: a book or character left `generating` for 2 hours with no job waiting, running
or scheduled for it (the worker was restarted or ran out of memory mid-job) becomes `failed`, so the admin's
«أعيدوا التوليد» and the parent's «حاولوا مرة أخرى» work again instead of a spinner that never ends."""

import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

import structlog
from redis import Redis
from rq import get_current_job
from rq.job import Job
from rq.queue import Queue
from rq.registry import DeferredJobRegistry, ScheduledJobRegistry, StartedJobRegistry
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Character,
    CharacterStatus,
    ChildPhoto,
    Companion,
    FamilyMember,
    OrderItem,
    PhotoStatus,
)
from qamra_core.settings import CoreSettings
from qamra_core.storage import ObjectStorage
from qamra_worker import context
from qamra_worker.queues import ALL
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.maintenance")


@dataclass
class CleanupSummary:
    photos_deleted: int = 0
    drawings_deleted: int = 0
    drafts_deleted: int = 0
    family_photos_deleted: int = 0  # the illustrated-family add-on's photos, 24 h after approval
    stalled_released: int = 0  # books and characters left `generating` by a job that died


STALLED_AFTER = timedelta(hours=2)  # longer than any job's timeout (1 h) plus its retries' waits
STALLED_ERROR = (
    "stalled: no result after 2 hours and no job left for it (the worker restarted or ran out of memory)"
)


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
        photo.crop = None  # the framing goes with the photo it framed
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


def pending_job_args(conn: Redis) -> set[str]:
    """Every argument of a job that is waiting, running, deferred or scheduled for a retry, on every queue."""
    ids: set[str] = set()
    for name in ALL:
        queue = Queue(name, connection=conn)
        ids.update(queue.get_job_ids())
        for registry in (StartedJobRegistry, ScheduledJobRegistry, DeferredJobRegistry):
            ids.update(registry(queue=queue).get_job_ids())
    return {
        str(a) for job in Job.fetch_many(sorted(ids), connection=conn) if job is not None for a in job.args
    }


def release_stalled(db: Session, pending: set[str], now: datetime | None = None) -> int:
    """Books and characters `generating` for 2 hours that no pending job names (by their id, order item or
    order) become `failed`. A long queue (a class of 30) is never cut: its jobs are still pending."""
    cutoff = (now or datetime.now(UTC)) - STALLED_AFTER
    released = 0
    for book in db.scalars(
        select(Book)
        .where(Book.status == BookStatus.generating, Book.updated_at < cutoff)
        .with_for_update(skip_locked=True)
    ).all():
        keys = {str(book.id)}
        item_id = (book.generation or {}).get("order_item_id")
        if item_id:
            keys.add(str(item_id))
            item = db.get(OrderItem, uuid.UUID(str(item_id)))
            if item is not None:
                keys.add(str(item.order_id))
        if keys & pending:
            continue
        book.status, book.error = BookStatus.failed, STALLED_ERROR
        _audit(db, "book.stalled", "book", book.id)
        released += 1
    for character in db.scalars(
        select(Character)
        .where(Character.status == CharacterStatus.generating, Character.updated_at < cutoff)
        .with_for_update(skip_locked=True)
    ).all():
        if str(character.id) in pending:
            continue
        character.status = CharacterStatus.failed
        _audit(db, "character.stalled", "character", character.id)
        released += 1
    db.commit()
    return released


def run_cleanup() -> dict[str, int]:
    """RQ entry point."""
    context.init_process()
    with context.db_session() as db:
        summary = cleanup_expired_media(db, context.storage(), get_settings())
        job = get_current_job()
        if job is not None:  # needs the queue to know what is still pending; never guessed without it
            summary.stalled_released = release_stalled(db, pending_job_args(job.connection))
    log.info("cleanup.done", **asdict(summary))
    return asdict(summary)


def ping() -> str:
    return "pong"
