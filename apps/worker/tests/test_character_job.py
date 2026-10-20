import asyncio
import io
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

import qamra_worker.jobs.books as books
from qamra_ai.config import Settings as AISettings
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.photo_color import to_linear, to_srgb
from qamra_ai.pipeline.runtime import Runtime
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
from qamra_worker.ai import make_runtime
from qamra_worker.jobs import create as create_jobs
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
    # portrait first: the portrait is drawn before the sheet and stored next to it, under the child's prefix
    assert character.portrait_image_key == f"children/{child.id}/characters/{character.id}-portrait.png"
    assert storage.get(character.portrait_image_key)
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
    real = books.generate_character

    async def spy(rt: Any, ai: Any, photos: list[bytes], *args: Any, **kwargs: Any) -> Any:
        sent.append(photos)
        return await real(rt, ai, photos, *args, **kwargs)

    monkeypatch.setattr(books, "generate_character", spy)  # the portrait and the sheet: the same photos
    assert asyncio.run(draw_character(db, storage, character, offline="fake")) == {"status": "ready"}
    [[reference]] = sent
    with Image.open(io.BytesIO(reference)) as im:
        assert im.size == (540, 513)  # 513 × 540 of the original, turned a quarter clockwise: the frame
    assert storage.get(key) == buf.getvalue()  # the original stays as it was uploaded


def _redraw(db: Session, storage: ObjectStorage, params: dict[str, object]) -> Character:
    """A redraw the API queued for a boy, with what the parent asked for."""
    parent = User(email="dad@example.com", full_name="أبو آدم")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="آدم", gender=Gender.m, birth_year=2021)
    db.add(child)
    db.flush()
    key = f"children/{child.id}/photos/p1.jpg"
    storage.put(key, FIXTURE.read_bytes(), "image/png")
    db.add(ChildPhoto(child_id=child.id, storage_key=key, status=PhotoStatus.accepted))
    return _again(db, child.id, params)


def _again(db: Session, child_id: uuid.UUID, params: dict[str, object]) -> Character:
    character = Character(child_id=child_id, art_style="3d", status=CharacterStatus.generating, params=params)
    db.add(character)
    db.commit()
    return character


def _spy(monkeypatch: pytest.MonkeyPatch, text: object | None = None) -> list[Runtime]:
    """The runtimes the job builds (their fake image provider keeps every request); `text` replaces Claude."""
    made: list[Runtime] = []

    def make(settings: AISettings) -> Runtime:
        rt = make_runtime(settings)
        if text is not None:
            rt.text = text  # type: ignore[assignment]
        made.append(rt)
        return rt

    monkeypatch.setattr(create_jobs, "make_runtime", make)
    return made


def _prompt(rt: Runtime) -> str:
    image = getattr(rt.image, "primary", rt.image)
    assert isinstance(image, FakeImageProvider)
    return image.requests[-1].prompt


def test_the_parents_note_is_rewritten_and_drawn_into_the_redraw(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    made = _spy(monkeypatch)
    character = _redraw(db, storage, {"attempt": 2, "fixes": ["hair"], "note": "شعره أجعد وأغمق"})

    assert asyncio.run(draw_character(db, storage, character, offline="fake")) == {"status": "ready"}
    prompt = _prompt(made[0])
    assert "- Hair: match the photo" in prompt and "- Appearance: شعره أجعد وأغمق" in prompt
    params = character.params
    assert params["note"] == "شعره أجعد وأغمق" and params["note_outcome"] == "used"
    assert params["note_instruction"] == "Appearance: شعره أجعد وأغمق" and params["fixes"] == ["hair"]
    steps = db.scalars(select(GenerationCost.step).where(GenerationCost.child_id == character.child_id))
    # the note's reading, the likeness notes, the portrait and the sheet are costed to the child
    assert set(steps) == {"character:feedback", "character:likeness", "portrait:2", "character:2"}
    image = getattr(made[0].image, "primary", made[0].image)
    assert isinstance(image, FakeImageProvider)
    portrait_prompt = image.requests[0].prompt  # the portrait is drawn first, with the same fixes and note
    assert image.requests[0].step == "portrait:2" and "- Appearance: شعره أجعد وأغمق" in portrait_prompt


def test_a_failed_text_step_or_a_screened_note_leaves_the_chips_alone(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Down:
        name = "down"

        async def structured(self, **_: object) -> object:
            raise TimeoutError("down")

    made = _spy(monkeypatch, Down())
    character = _redraw(db, storage, {"attempt": 3, "fixes": ["age"], "note": "عيونه أوسع"})
    assert asyncio.run(draw_character(db, storage, character, offline="fake")) == {"status": "ready"}
    prompt = _prompt(made[0])
    assert (
        "Age: the child looked older than" in prompt and "عيونه" not in prompt and "Appearance" not in prompt
    )
    assert character.params["note_outcome"] == "failed" and "note_instruction" not in character.params
    # the likeness notes failed too: drawn without them
    assert character.params["likeness_notes_outcome"] == "failed" and "likeness_notes" not in character.params
    assert "WHAT THIS CHILD LOOKS LIKE" not in prompt

    screened = _again(db, character.child_id, {"attempt": 4, "note": "رقمنا 0599123456"})
    assert asyncio.run(draw_character(db, storage, screened, offline="fake")) == {"status": "ready"}
    assert screened.params["note_outcome"] == "screened"
    assert "0599" not in _prompt(made[-1]) and "did not look like" not in _prompt(made[-1])


def test_the_likeness_notes_are_read_once_kept_and_drawn_into_both_steps(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before drawing, the text model describes how the child looks from the photo (2026-10-19); the notes go
    into the portrait and the sheet, stay on the character, and a retried job doesn't ask again."""
    made = _spy(monkeypatch)
    character = _redraw(db, storage, {"attempt": 1})
    assert asyncio.run(draw_character(db, storage, character, offline="fake")) == {"status": "ready"}
    notes = character.params["likeness_notes"]
    assert character.params["likeness_notes_outcome"] == "used" and notes["skin"] == "light olive"
    image = getattr(made[0].image, "primary", made[0].image)
    assert isinstance(image, FakeImageProvider)
    assert len(image.requests) == 2
    for req in image.requests:  # the portrait, then the sheet
        assert "- Hair: dark brown, short, swept up at the front" in req.prompt
        assert "- Skin tone: light olive" in req.prompt
    calls = [c for c in made[0].text.calls if c["schema"] == "LikenessNotes"]  # type: ignore[attr-defined]
    assert [c["step"] for c in calls] == ["character:likeness"]
    steps = set(db.scalars(select(GenerationCost.step).where(GenerationCost.child_id == character.child_id)))
    assert "character:likeness" in steps

    # a retried job: the notes saved before drawing are reused, not asked again
    character.status, character.sheet_image_key = CharacterStatus.generating, None
    db.commit()
    assert asyncio.run(draw_character(db, storage, character, offline="fake")) == {"status": "ready"}
    assert not [c for c in made[-1].text.calls if c["schema"] == "LikenessNotes"]  # type: ignore[attr-defined]
    assert "- Skin tone: light olive" in _prompt(made[-1])


def test_the_reference_has_its_light_made_neutral_and_the_original_stays(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A photo under yellow street light reaches the image model with its light made neutral (2026-10-19)."""
    parent = User(email="dad@example.com", full_name="أبو علي")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="علي", gender=Gender.m, birth_year=2021)
    db.add(child)
    db.flush()
    rgb = np.asarray(Image.open(FIXTURE).convert("RGB"), dtype=np.float64) / 255.0
    lit = to_srgb(to_linear(rgb) * np.array([1.0, 0.78, 0.42]))  # sodium street light
    buf = io.BytesIO()
    Image.fromarray((lit * 255).round().astype(np.uint8)).save(buf, format="PNG")
    key = f"children/{child.id}/photos/p1.png"
    storage.put(key, buf.getvalue(), "image/png")
    db.add(ChildPhoto(child_id=child.id, storage_key=key, status=PhotoStatus.accepted))
    character = Character(child_id=child.id, art_style="watercolor", status=CharacterStatus.generating)
    db.add(character)
    db.commit()
    sent: list[list[bytes]] = []
    real = books.generate_character

    async def spy(rt: Any, ai: Any, photos: list[bytes], *args: Any, **kwargs: Any) -> Any:
        sent.append(photos)
        return await real(rt, ai, photos, *args, **kwargs)

    monkeypatch.setattr(books, "generate_character", spy)
    assert asyncio.run(draw_character(db, storage, character, offline="fake")) == {"status": "ready"}
    [[reference]] = sent

    def blue_over_red(data: bytes) -> float:
        px = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.float64)
        return float(px[..., 2].mean() / px[..., 0].mean())

    assert blue_over_red(reference) > blue_over_red(buf.getvalue()) * 1.15  # much less yellow
    assert storage.get(key) == buf.getvalue()  # the stored original is never changed


def test_the_newest_photo_goes_first_and_the_drawing_records_it(
    db: Session, storage: ObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """«تغيير الصورة» (owner, 2026-10-19): the newest photo goes first, and the drawing records the photo it
    came from (the API set the newest one when it was asked for; the worker writes the one it really used)."""
    parent = User(email="mom@example.com", full_name="أم ليان")
    db.add(parent)
    db.flush()
    child = Child(guardian_user_id=parent.id, first_name="ليان", gender=Gender.f, birth_year=2020)
    db.add(child)
    db.flush()
    wide = Image.new("RGB", (900, 900), (150, 160, 170))  # an earlier photo, still stored (a race)
    wide.paste(Image.open(FIXTURE).convert("RGB"), (0, 0))
    buf = io.BytesIO()
    wide.save(buf, format="JPEG", quality=92)
    old_key, new_key = f"children/{child.id}/photos/old.jpg", f"children/{child.id}/photos/new.jpg"
    storage.put(old_key, buf.getvalue(), "image/jpeg")
    storage.put(new_key, FIXTURE.read_bytes(), "image/png")
    old = ChildPhoto(
        child_id=child.id,
        storage_key=old_key,
        status=PhotoStatus.accepted,
        created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    new = ChildPhoto(child_id=child.id, storage_key=new_key, status=PhotoStatus.accepted)
    db.add_all([old, new])
    db.flush()
    character = _again(db, child.id, {"attempt": 3, "fixes": [], "photo_id": str(old.id)})
    sent: list[list[bytes]] = []
    real = books.generate_character

    async def spy(rt: Any, ai: Any, photos: list[bytes], *args: Any, **kwargs: Any) -> Any:
        sent.append(photos)
        return await real(rt, ai, photos, *args, **kwargs)

    monkeypatch.setattr(books, "generate_character", spy)
    assert asyncio.run(draw_character(db, storage, character, offline="fake")) == {"status": "ready"}
    [photos] = sent
    assert len(photos) == 2
    with Image.open(io.BytesIO(photos[0])) as first, Image.open(FIXTURE) as fixture:
        assert first.size == fixture.size  # the new photo first
    assert character.params["photo_id"] == str(new.id) and character.params["attempt"] == 3
