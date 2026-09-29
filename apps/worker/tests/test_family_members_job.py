"""The illustrated-family add-on's worker side: a family member's sheet drawn with the fake providers (no paid
AI in tests) from their consented photo, and the photo deleted by the cleanup job once its time is up."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from qamra_core.db.models import Child, FamilyMember, FamilyMemberStatus, Gender, User
from qamra_core.settings import CoreSettings
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.family_members import draw_member
from qamra_worker.jobs.maintenance import cleanup_expired_media

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


def _member(db: Session, storage: ObjectStorage, *, consented: bool = True) -> FamilyMember:
    parent = User(email="mom@example.com", full_name="P")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="ليان", gender=Gender.f, birth_year=2021)
    db.add(child)
    db.flush()
    member = FamilyMember(
        child_id=child.id,
        guardian_user_id=parent.id,
        relation="grandmother",
        first_name="أم خليل",
        adult=True,
        scarf=True,
        consent_version="family-member-2026-09",
        consented_at=datetime.now(UTC) if consented else None,
        art_style="watercolor",
        status=FamilyMemberStatus.generating,
        regen_count=1,
        params={},
    )
    db.add(member)
    db.flush()
    member.photo_key = f"children/{child.id}/family/{member.id}/photo.jpg"
    storage.put(member.photo_key, FACE.read_bytes(), "image/png")
    db.commit()
    return member


async def test_a_member_is_drawn_from_their_consented_photo(db: Session, storage: ObjectStorage) -> None:
    member = _member(db, storage)
    result = await draw_member(db, storage, member, offline="fake")
    assert result == {"status": "ready"} and member.status == FamilyMemberStatus.ready
    assert member.sheet_key == f"children/{member.child_id}/family/{member.id}/sheet-1.png"
    assert storage.exists(member.sheet_key) and member.provider and member.params["attempt"] == 1
    unconsented = _member_without_consent(db, storage)
    with pytest.raises(ValueError, match="consented photo"):
        await draw_member(db, storage, unconsented, offline="fake")


def _member_without_consent(db: Session, storage: ObjectStorage) -> FamilyMember:
    member = FamilyMember(
        child_id=db.query(Child).first().id,  # type: ignore[union-attr]
        guardian_user_id=db.query(User).first().id,  # type: ignore[union-attr]
        relation="father",
        first_name="",
        adult=True,
        scarf=False,
        status=FamilyMemberStatus.draft,
        regen_count=0,
        params={},
        photo_key="x",
    )
    db.add(member)
    db.commit()
    return member


def test_the_photo_is_deleted_after_approval(db: Session, storage: ObjectStorage) -> None:
    member = _member(db, storage)
    photo = member.photo_key or ""
    member.approved_at = datetime.now(UTC) - timedelta(hours=25)
    member.photo_delete_after = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    summary = cleanup_expired_media(db, storage, CoreSettings(_env_file=None))  # type: ignore[call-arg]
    assert summary.family_photos_deleted == 1 and not storage.exists(photo)
    db.refresh(member)
    assert member.photo_key is None
