from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    ChildPhoto,
    Companion,
    CompanionType,
    Gender,
    Locale,
    PhotoStatus,
    Theme,
    User,
)
from qamra_core.settings import CoreSettings
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.maintenance import cleanup_expired_media, ping, release_stalled

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
SETTINGS = CoreSettings(_env_file=None)  # type: ignore[call-arg]


def _child(db: Session) -> Child:
    parent = User(email="p@example.com", full_name="P")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="سليم", gender=Gender.m, birth_year=2020)
    db.add(child)
    db.flush()
    return child


def test_expired_photos_are_deleted_from_storage_and_marked(db: Session, storage: ObjectStorage) -> None:
    child = _child(db)
    due_key, later_key = f"children/{child.id}/photos/due.jpg", f"children/{child.id}/photos/later.jpg"
    for key in (due_key, later_key):
        storage.put(key, b"photo", "image/jpeg")
    due = ChildPhoto(
        child_id=child.id,
        storage_key=due_key,
        status=PhotoStatus.accepted,
        delete_after=NOW - timedelta(minutes=1),
    )
    later = ChildPhoto(
        child_id=child.id,
        storage_key=later_key,
        status=PhotoStatus.accepted,
        delete_after=NOW + timedelta(hours=3),
    )
    db.add_all([due, later])
    db.commit()

    summary = cleanup_expired_media(db, storage, SETTINGS, now=NOW)

    assert summary.photos_deleted == 1
    assert not storage.exists(due_key) and storage.exists(later_key)
    db.refresh(due)
    assert due.status == PhotoStatus.deleted and due.storage_key is None and due.deleted_at == NOW
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "photo.auto_deleted")).one()
    assert audit.entity_id == str(due.id) and audit.data == {}
    # idempotent
    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW).photos_deleted == 0


def test_original_drawing_deleted_cleaned_version_kept(db: Session, storage: ObjectStorage) -> None:
    child = _child(db)
    drawing, cleaned = f"children/{child.id}/drawings/orig.jpg", f"children/{child.id}/drawings/clean.png"
    storage.put(drawing, b"d", "image/jpeg")
    storage.put(cleaned, b"c", "image/png")
    comp = Companion(
        child_id=child.id,
        name="بوبو",
        type_hint=CompanionType.creature,
        drawing_key=drawing,
        cleaned_key=cleaned,
        drawing_delete_after=NOW - timedelta(seconds=1),
    )
    db.add(comp)
    db.commit()

    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW).drawings_deleted == 1
    assert not storage.exists(drawing) and storage.exists(cleaned)
    db.refresh(comp)
    assert comp.drawing_key is None and comp.cleaned_key == cleaned


def test_abandoned_drafts_deleted_after_30_days(db: Session, storage: ObjectStorage) -> None:
    child = _child(db)
    theme = Theme(slug="t", title_ar="ت", title_en="T", age_min=3, age_max=7, definition={})
    db.add(theme)
    db.flush()
    old = Book(child_id=child.id, theme_id=theme.id, theme_version=1, language=Locale.ar, art_style="w")
    fresh = Book(child_id=child.id, theme_id=theme.id, theme_version=1, language=Locale.ar, art_style="w")
    ordered = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=1,
        language=Locale.ar,
        art_style="w",
        status=BookStatus.ordered,
    )
    db.add_all([old, fresh, ordered])
    db.flush()
    db.execute(
        update(Book).where(Book.id.in_([old.id, ordered.id])).values(updated_at=NOW - timedelta(days=31))
    )
    db.execute(update(Book).where(Book.id == fresh.id).values(updated_at=NOW - timedelta(days=2)))
    storage.put(f"children/{child.id}/books/{old.id}/page-1.png", b"x", "image/png")
    db.commit()

    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW).drafts_deleted == 1
    remaining = set(db.scalars(select(Book.id)).all())
    assert remaining == {fresh.id, ordered.id}
    assert not storage.exists(f"children/{child.id}/books/{old.id}/page-1.png")


def test_stalled_work_is_released_unless_a_job_is_still_pending(db: Session) -> None:
    """A book or character left `generating` by a dead job becomes `failed` after 2 hours; one whose job still
    waits in the queue (a long class batch) or whose order item has a pending job is left alone."""
    child = _child(db)
    theme = Theme(slug="t", title_ar="ت", title_en="T", age_min=3, age_max=7, definition={})
    db.add(theme)
    db.flush()

    def book(**generation: str) -> Book:
        b = Book(
            child_id=child.id,
            theme_id=theme.id,
            theme_version=1,
            language=Locale.ar,
            art_style="3d",
            status=BookStatus.generating,
            generation=generation,
        )
        db.add(b)
        return b

    dead, queued, fresh = book(), book(), book()
    dead_family, queued_family = (
        book(line="family", order_item_id="4c1d5a8e-0000-4000-8000-000000000001"),
        book(line="family", order_item_id="4c1d5a8e-0000-4000-8000-000000000002"),
    )
    stuck = Character(child_id=child.id, art_style="3d", status=CharacterStatus.generating)
    db.add(stuck)
    db.flush()
    old = [dead.id, queued.id, dead_family.id, queued_family.id]
    db.execute(update(Book).where(Book.id.in_(old)).values(updated_at=NOW - timedelta(hours=3)))
    db.execute(update(Book).where(Book.id == fresh.id).values(updated_at=NOW - timedelta(minutes=30)))
    db.execute(update(Character).where(Character.id == stuck.id).values(updated_at=NOW - timedelta(hours=3)))
    db.commit()

    pending = {str(queued.id), "4c1d5a8e-0000-4000-8000-000000000002"}
    assert release_stalled(db, pending, now=NOW) == 3
    for b in (dead, queued, fresh, dead_family, queued_family, stuck):
        db.refresh(b)
    assert dead.status == BookStatus.failed and dead.error and "stalled" in dead.error
    assert dead_family.status == BookStatus.failed
    assert BookStatus.generating == queued.status == fresh.status == queued_family.status
    assert stuck.status == CharacterStatus.failed
    assert release_stalled(db, pending, now=NOW) == 0  # idempotent


def test_ping() -> None:
    assert ping() == "pong"


def test_cron_config_registers_cleanup() -> None:
    from fakeredis import FakeRedis
    from rq.cron import CronScheduler

    scheduler = CronScheduler(connection=FakeRedis())
    scheduler.load_config_from_file("qamra_worker.cron_config")
    jobs = {j.func_name: j for j in scheduler.get_jobs()}  # the studio's scheduled publish runs there too
    job = jobs["qamra_worker.jobs.maintenance.run_cleanup"]
    assert job.interval == 900 and job.queue_name == "maintenance"
    assert "qamra_worker.jobs.studio.run_scheduled_publish" in jobs
