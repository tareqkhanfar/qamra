import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.models import (
    Character,
    CharacterStatus,
    Child,
    ChildPhoto,
    Gender,
    GenerationCost,
    PhotoStatus,
    User,
)
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.create import draw_character

FIXTURE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


def test_a_character_is_drawn_for_the_child_and_costed_to_the_child(
    db: Session, storage: ObjectStorage
) -> None:
    parent = User(email="mom@example.com", full_name="أم ليان")
    db.add(parent)
    db.flush()
    child = Child(
        guardian_user_id=parent.id, first_name="ليان", gender=Gender.f, birth_year=2020, wears_hijab=True
    )
    db.add(child)
    db.flush()
    key = f"children/{child.id}/photos/p1.jpg"
    storage.put(key, FIXTURE.read_bytes(), "image/png")
    db.add(ChildPhoto(child_id=child.id, storage_key=key, status=PhotoStatus.accepted))
    character = Character(child_id=child.id, art_style="watercolor", status=CharacterStatus.generating)
    db.add(character)
    db.commit()

    result = asyncio.run(draw_character(db, storage, character, offline="fake"))
    assert result == {"status": "ready"}
    assert character.sheet_image_key == f"children/{child.id}/characters/{character.id}.png"
    assert storage.get(character.sheet_image_key)
    costs = db.scalars(select(GenerationCost).where(GenerationCost.child_id == child.id)).all()
    assert costs and all(c.book_id is None for c in costs)  # a child's character isn't charged to a book
