import asyncio
import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

import qamra_worker.jobs.books as books
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


def test_the_character_is_drawn_from_the_parents_framing(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every provider gets the same reference: the cut-out the parent framed (head and shoulders, turned
    upright), never the whole photo (owner, 2026-10-10)."""
    parent = User(email="dad@example.com", full_name="أبو سليم")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="سليم", gender=Gender.m, birth_year=2020)
    db.add(child)
    db.flush()
    canvas = Image.new("RGB", (2048, 1536), (150, 160, 170))  # the child far from the camera, on the right
    canvas.paste(Image.open(FIXTURE).convert("RGB"), (1348, 100))
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=92)
    key = f"children/{child.id}/photos/p1.jpg"
    storage.put(key, buf.getvalue(), "image/jpeg")
    crop = {"x": 1348 / 2048, "y": 100 / 1536, "w": 513 / 2048, "h": 540 / 1536, "rotate": 90}
    db.add(ChildPhoto(child_id=child.id, storage_key=key, status=PhotoStatus.accepted, crop=crop))
    character = Character(child_id=child.id, art_style="watercolor", status=CharacterStatus.generating)
    db.add(character)
    db.commit()
    sent: list[list[bytes]] = []
    real = books.generate_character_sheet

    async def spy(rt: Any, ai: Any, photos: list[bytes], *args: Any, **kwargs: Any) -> Any:
        sent.append(photos)
        return await real(rt, ai, photos, *args, **kwargs)

    monkeypatch.setattr(books, "generate_character_sheet", spy)
    assert asyncio.run(draw_character(db, storage, character, offline="fake")) == {"status": "ready"}
    [[reference]] = sent
    with Image.open(io.BytesIO(reference)) as im:
        assert im.size == (540, 513)  # 513 × 540 of the original, turned a quarter clockwise: the frame
    assert storage.get(key) == buf.getvalue()  # the original stays as it was uploaded
