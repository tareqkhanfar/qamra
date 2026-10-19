from datetime import UTC, datetime, timedelta
from decimal import Decimal

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
    Consent,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PhotoStatus,
    Theme,
    User,
)
from qamra_core.photo_keep import KEEP_CONSENT_VERSION, KEEP_SCOPE, add_months
from qamra_core.settings import CoreSettings
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.maintenance import cleanup_expired_media, ping, release_stalled

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
SETTINGS = CoreSettings(_env_file=None)  # type: ignore[call-arg]


def _child(db: Session) -> Child:
    return _child_named(db, "p@example.com")


def _child_named(db: Session, email: str) -> Child:
    parent = User(email=email, full_name="P")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="سليم", gender=Gender.m, birth_year=2020)
    db.add(child)
    db.flush()
    return child


def _keep(db: Session, child: Child, *, withdrawn: datetime | None = None) -> Consent:
    """The guardian's choice to keep the photo for later books (qamra_core.photo_keep)."""
    consent = Consent(
        child_id=child.id,
        guardian_user_id=child.guardian_user_id,
        consent_text_version=KEEP_CONSENT_VERSION,
        scope=KEEP_SCOPE,
        withdrawn_at=withdrawn,
    )
    db.add(consent)
    db.flush()
    return consent


def test_expired_photos_are_deleted_from_storage_and_marked(db: Session, storage: ObjectStorage) -> None:
    """The 24-hour rule (CLAUDE.md §3.1) while the keep choice is off (never made, or taken back)."""
    child = _child(db)
    _keep(db, child, withdrawn=NOW - timedelta(hours=1))  # taken back: the usual rule again
    due_key, later_key = f"children/{child.id}/photos/due.jpg", f"children/{child.id}/photos/later.jpg"
    for key in (due_key, later_key):
        storage.put(key, b"photo", "image/jpeg")
    due = ChildPhoto(
        child_id=child.id,
        storage_key=due_key,
        status=PhotoStatus.accepted,
        delete_after=NOW - timedelta(minutes=1),
        crop={"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5, "rotate": 0},  # the parent's framing goes with it
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
    assert due.crop is None
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "photo.auto_deleted")).one()
    assert audit.entity_id == str(due.id) and audit.data == {}
    # idempotent
    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW).photos_deleted == 0


def test_photos_never_approved_are_deleted_after_30_days(db: Session, storage: ObjectStorage) -> None:
    """No approval, no deletion date: it goes with the abandoned drafts unless an open order needs it."""
    abandoned, recent, ordered = (
        _child(db),
        _child_named(db, "b@example.com"),
        _child_named(db, "c@example.com"),
    )
    keys = {}
    for child in (abandoned, recent, ordered):
        key = f"children/{child.id}/photos/p.jpg"
        storage.put(key, b"photo", "image/jpeg")
        db.add(ChildPhoto(child_id=child.id, storage_key=key, status=PhotoStatus.accepted))
        keys[child.id] = key
    db.flush()
    order = Order(
        code="QM-TEST01",
        status=OrderStatus.new,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("0"),
        total=Decimal("0"),
    )
    db.add(order)
    db.flush()
    db.add(OrderItem(order_id=order.id, child_id=ordered.id, unit_price=Decimal("0")))
    db.execute(
        update(ChildPhoto)
        .where(ChildPhoto.child_id.in_([abandoned.id, ordered.id]))
        .values(updated_at=NOW - timedelta(days=31))
    )
    db.execute(
        update(ChildPhoto).where(ChildPhoto.child_id == recent.id).values(updated_at=NOW - timedelta(days=2))
    )
    db.commit()

    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW).photos_deleted == 1
    assert not storage.exists(keys[abandoned.id])
    assert storage.exists(keys[recent.id]) and storage.exists(keys[ordered.id])

    order.status = OrderStatus.cancelled  # the order no longer needs it
    db.commit()
    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW).photos_deleted == 1
    assert not storage.exists(keys[ordered.id]) and storage.exists(keys[recent.id])


def test_a_kept_photo_outlives_the_24_hours_and_the_30_days(db: Session, storage: ObjectStorage) -> None:
    """The guardian chose to keep it: neither the approval's 24 hours nor the abandoned-draft rule
    delete it."""
    approved, abandoned = _child(db), _child_named(db, "b@example.com")
    keys = {}
    for child in (approved, abandoned):
        _keep(db, child)
        keys[child.id] = f"children/{child.id}/photos/p.jpg"
        storage.put(keys[child.id], b"photo", "image/jpeg")
    db.add_all(
        [
            ChildPhoto(
                child_id=approved.id,
                storage_key=keys[approved.id],
                status=PhotoStatus.accepted,
                delete_after=NOW - timedelta(days=20),
                last_used_at=NOW - timedelta(days=21),
            ),
            ChildPhoto(child_id=abandoned.id, storage_key=keys[abandoned.id], status=PhotoStatus.accepted),
        ]
    )
    db.flush()
    db.execute(update(ChildPhoto).values(updated_at=NOW - timedelta(days=45)))
    db.commit()

    summary = cleanup_expired_media(db, storage, SETTINGS, now=NOW, kept_months=12)
    assert summary.photos_deleted == 0 and summary.kept_photos_expired == 0
    assert all(storage.exists(k) for k in keys.values())
    photo = db.scalars(select(ChildPhoto).where(ChildPhoto.child_id == abandoned.id)).one()
    assert photo.delete_after is None  # not marked as an abandoned draft either


def test_a_kept_photo_is_deleted_after_its_retention(db: Session, storage: ObjectStorage) -> None:
    """`kept_photo_retention_months` after the last use; the choice ends with the photo."""
    stale, used, fresh = _child(db), _child_named(db, "b@example.com"), _child_named(db, "c@example.com")
    consents = {c.id: _keep(db, c) for c in (stale, used, fresh)}
    photos = {}
    for child, uploaded, last in (
        (stale, NOW - timedelta(days=500), None),  # never used since the upload, 16 months ago
        (used, NOW - timedelta(days=500), NOW - timedelta(days=60)),  # a new book two months ago
        (fresh, NOW - timedelta(days=10), None),
    ):
        key = f"children/{child.id}/photos/p.jpg"
        storage.put(key, b"photo", "image/jpeg")
        photo = ChildPhoto(
            child_id=child.id,
            storage_key=key,
            status=PhotoStatus.accepted,
            delete_after=uploaded + timedelta(hours=24),
            last_used_at=last,
        )
        db.add(photo)
        db.flush()
        photo.created_at = uploaded
        photos[child.id] = photo
    db.commit()

    summary = cleanup_expired_media(db, storage, SETTINGS, now=NOW, kept_months=12)
    assert summary.kept_photos_expired == 1 and summary.photos_deleted == 0
    for p in photos.values():
        db.refresh(p)
    gone = photos[stale.id]
    assert gone.storage_key is None and gone.status == PhotoStatus.deleted and gone.deleted_at == NOW
    assert not storage.exists(f"children/{stale.id}/photos/p.jpg")
    assert photos[used.id].storage_key and photos[fresh.id].storage_key
    for consent in consents.values():
        db.refresh(consent)
    assert consents[stale.id].withdrawn_at == NOW  # a later upload asks again
    assert consents[used.id].withdrawn_at is None and consents[fresh.id].withdrawn_at is None
    actions = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.created_at)).all()]
    assert actions == ["photo.kept_expired", "photo_keep.expired"]
    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW, kept_months=12).kept_photos_expired == 0

    # the admin shortens the retention: the photo used two months ago goes too
    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW, kept_months=1).kept_photos_expired == 1
    # the admin setting is read when the caller gives none (default 12 months)
    assert cleanup_expired_media(db, storage, SETTINGS, now=add_months(NOW, 13)).kept_photos_expired == 1


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


def test_drawings_never_approved_are_discarded_after_30_days(db: Session, storage: ObjectStorage) -> None:
    """Every redraw is kept for comparing; one the parent never approved is an abandoned draft: its picture
    and the parent's note go after 30 days, an approved drawing stays for the next books. So do the likeness
    notes read from the photo (how the child looks, in words); their outcome stays with the costs."""
    child = _child(db)
    note = {
        "attempt": 2,
        "fixes": ["hair"],
        "note": "شعره أجعد",
        "note_instruction": "Hair: curlier.",
        "likeness_notes": {"hair": "dark brown, swept up"},
        "likeness_notes_outcome": "used",
    }

    def drawing(status: CharacterStatus, approved: bool = False, **params: object) -> Character:
        c = Character(
            child_id=child.id,
            art_style="3d",
            status=status,
            approved_at=NOW - timedelta(days=40) if approved else None,
            params=dict(params),
        )
        db.add(c)
        db.flush()
        if status in (CharacterStatus.ready, CharacterStatus.approved):
            c.sheet_image_key = f"children/{child.id}/characters/{c.id}.png"
            storage.put(c.sheet_image_key, b"sheet", "image/png")
            c.portrait_image_key = f"children/{child.id}/characters/{c.id}-portrait.png"  # portrait first
            storage.put(c.portrait_image_key, b"portrait", "image/png")
        return c

    old = drawing(CharacterStatus.ready, **note)
    chosen = drawing(CharacterStatus.approved, approved=True, **note)
    failed = drawing(CharacterStatus.failed, **note)
    failed_notes_only = drawing(
        CharacterStatus.failed, likeness_notes={"hair": "x"}, likeness_notes_outcome="used"
    )
    fresh = drawing(CharacterStatus.ready, **note)
    old_key, chosen_key, fresh_key = old.sheet_image_key, chosen.sheet_image_key, fresh.sheet_image_key
    old_portrait, chosen_portrait = old.portrait_image_key, chosen.portrait_image_key
    db.execute(
        update(Character)
        .where(Character.id.in_([old.id, chosen.id, failed.id, failed_notes_only.id]))
        .values(updated_at=NOW - timedelta(days=31))
    )
    db.execute(update(Character).where(Character.id == fresh.id).values(updated_at=NOW - timedelta(days=2)))
    db.commit()

    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW).characters_discarded == 1
    for c in (old, chosen, failed, failed_notes_only, fresh):
        db.refresh(c)
    assert old.status == CharacterStatus.discarded and old.sheet_image_key is None
    assert old_key and not storage.exists(old_key)
    assert old.portrait_image_key is None and old_portrait and not storage.exists(old_portrait)  # with it
    assert chosen_portrait and storage.exists(chosen_portrait)  # an approved drawing keeps its portrait
    # the parent's words and the likeness notes are gone with the picture
    assert old.params == {"attempt": 2, "fixes": ["hair"], "likeness_notes_outcome": "used"}
    assert failed.status == CharacterStatus.failed and "note" not in failed.params  # still not a redraw
    assert "likeness_notes" not in failed.params
    assert failed_notes_only.params == {"likeness_notes_outcome": "used"}
    assert chosen.status == CharacterStatus.approved and chosen_key and storage.exists(chosen_key)
    assert chosen.params["note"] == "شعره أجعد"  # the approved drawing keeps how it was asked for
    assert chosen.params["likeness_notes"] == {"hair": "dark brown, swept up"}
    assert fresh.status == CharacterStatus.ready and fresh_key and storage.exists(fresh_key)
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "character.draft_expired")).one()
    assert audit.entity_id == str(old.id)
    assert cleanup_expired_media(db, storage, SETTINGS, now=NOW).characters_discarded == 0  # idempotent


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
