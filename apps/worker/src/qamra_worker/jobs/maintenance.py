"""Privacy cleanup (CLAUDE.md §3, Addendum 1 §1): originals are deleted after approval + 24h,
abandoned drafts after 30 days (a photo whose character was never approved is one too). Runs every 15
minutes from `rq cron`.

A photo the guardian chose to keep for later books (qamra_core.photo_keep, owner 2026-10-16) is exempt
from both rules while the choice is on; it is deleted `kept_photo_retention_months` (admin setting,
default 12) after its last use, and the choice ends with it.

The child's drawings are all kept so the parent can compare them and go back to one (owner, 2026-10-10); a
drawing never approved is an abandoned draft too: after the same 30 days its picture is deleted and the row is
marked `discarded` (it still counts as one of the child's redraws). Approved drawings stay for the next books
until the parent deletes the child's data.

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
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from qamra_core.crypto import cipher_for
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Character,
    CharacterStatus,
    ChildPhoto,
    Companion,
    Consent,
    FamilyMember,
    Order,
    OrderItem,
    OrderStatus,
    PhotoStatus,
)
from qamra_core.photo_keep import KEEP_SCOPE, RETENTION_SETTING, add_months, keeps_photo
from qamra_core.settings import CoreSettings
from qamra_core.settings_store import load_sync
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
    characters_discarded: int = 0  # drawings never approved, 30 days on
    family_photos_deleted: int = 0  # the illustrated-family add-on's photos, 24 h after approval
    stalled_released: int = 0  # books and characters left `generating` by a job that died
    kept_photos_expired: int = 0  # photos kept at the guardian's choice, past their retention


NOTE_KEYS = ("note", "note_instruction")  # «ما الذي لا يشبهه؟» in the parent's words, and its rewrite
STALLED_AFTER = timedelta(hours=2)  # longer than any job's timeout (1 h) plus its retries' waits
STALLED_ERROR = (
    "stalled: no result after 2 hours and no job left for it (the worker restarted or ran out of memory)"
)


def _audit(db: Session, action: str, entity_type: str, entity_id: object) -> None:
    db.add(AuditLog(actor_user_id=None, action=action, entity_type=entity_type, entity_id=str(entity_id)))


def _delete_photo(db: Session, storage: ObjectStorage, photo: ChildPhoto, now: datetime, action: str) -> None:
    if photo.storage_key:
        storage.delete(photo.storage_key)  # storage first: a crash leaves a row to retry, never a file
    photo.storage_key = None
    photo.crop = None  # the framing goes with the photo it framed
    photo.status = PhotoStatus.deleted
    photo.deleted_at = now
    _audit(db, action, "child_photo", photo.id)


def _expire_kept_photos(db: Session, storage: ObjectStorage, now: datetime, months: int) -> int:
    """Kept photos not used for `months`: deleted, and the guardian's choice ends with the last one."""
    oldest = add_months(now, -months)
    photos = db.scalars(
        select(ChildPhoto)
        .where(
            keeps_photo(ChildPhoto.child_id),
            ChildPhoto.deleted_at.is_(None),
            ChildPhoto.storage_key.is_not(None),
            func.coalesce(ChildPhoto.last_used_at, ChildPhoto.created_at) < oldest,
        )
        .with_for_update(skip_locked=True)
    ).all()
    children = set()
    for photo in photos:
        _delete_photo(db, storage, photo, now, "photo.kept_expired")
        children.add(photo.child_id)
    db.flush()
    for child_id in children:
        left = db.scalar(
            select(func.count())
            .select_from(ChildPhoto)
            .where(ChildPhoto.child_id == child_id, ChildPhoto.storage_key.is_not(None))
        )
        if left:
            continue
        for consent in db.scalars(
            select(Consent).where(
                Consent.child_id == child_id, Consent.scope == KEEP_SCOPE, Consent.withdrawn_at.is_(None)
            )
        ):
            consent.withdrawn_at = now
            _audit(db, "photo_keep.expired", "child", child_id)
    db.commit()
    return len(photos)


def cleanup_expired_media(
    db: Session,
    storage: ObjectStorage,
    settings: CoreSettings,
    now: datetime | None = None,
    kept_months: int | None = None,
) -> CleanupSummary:
    """`kept_months`: the kept photos' retention; None reads the admin setting."""
    now = now or datetime.now(UTC)
    summary = CleanupSummary()
    cutoff = now - timedelta(days=settings.draft_retention_days)
    if kept_months is None:
        kept_months = int(load_sync(db, cipher_for(settings)).values[RETENTION_SETTING])

    # A photo whose character was never approved has no deletion date (approval sets it): after the same 30
    # days as an abandoned draft it is due now, unless an open order still needs it (Classic paints from it).
    open_order = (
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.child_id == ChildPhoto.child_id,
            Order.status.not_in([OrderStatus.delivered, OrderStatus.cancelled]),
        )
        .exists()
    )
    db.execute(
        update(ChildPhoto)
        .where(
            ChildPhoto.delete_after.is_(None),
            ChildPhoto.deleted_at.is_(None),
            ChildPhoto.updated_at < cutoff,
            ~open_order,
            ~keeps_photo(ChildPhoto.child_id),  # kept at the guardian's choice: only its own retention
        )
        .values(delete_after=now)
        .execution_options(synchronize_session=False)
    )

    photos = db.scalars(
        select(ChildPhoto)
        .where(
            ChildPhoto.delete_after <= now,
            ChildPhoto.deleted_at.is_(None),
            ~keeps_photo(ChildPhoto.child_id),  # the 24-hour rule applies only while the choice is off
        )
        .with_for_update(skip_locked=True)
    ).all()
    for photo in photos:
        _delete_photo(db, storage, photo, now, "photo.auto_deleted")
        summary.photos_deleted += 1
    db.commit()
    summary.kept_photos_expired = _expire_kept_photos(db, storage, now, kept_months)

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

    drawings = db.scalars(
        select(Character)
        .where(
            Character.approved_at.is_(None),
            Character.updated_at < cutoff,
            or_(
                Character.status == CharacterStatus.ready,
                # a failed drawing has no picture and stays failed (it is not one of the redraws), but the
                # parent's words it was asked with go after the same 30 days
                and_(Character.status == CharacterStatus.failed, Character.params.has_key("note")),
            ),
        )
        .with_for_update(skip_locked=True)
    ).all()
    for character in drawings:
        # the parent's own words go; the chips and how it was drawn stay with the costs
        character.params = {k: v for k, v in (character.params or {}).items() if k not in NOTE_KEYS}
        if character.status != CharacterStatus.ready:
            continue
        for key in (character.sheet_image_key, character.portrait_image_key):
            if key:
                storage.delete(key)  # storage first: a crash leaves a row to retry
        character.sheet_image_key = character.portrait_image_key = None
        character.status = CharacterStatus.discarded
        _audit(db, "character.draft_expired", "character", character.id)
        summary.characters_discarded += 1
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
