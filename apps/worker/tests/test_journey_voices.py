"""The QR voices of «رحلتي الأولى للتعلّم» ship with the code and load into storage
(qamra_worker.journey_voices): one reviewed clip per item of content/journey/audio.yaml, loaded only where
missing or stale, never over a person's recording, and a second run changes nothing."""

import json
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.audio import AudioClip, clip_key
from qamra_core.db.models import AuditLog
from qamra_core.storage import ObjectStorage
from qamra_worker.journey_voices import CLIPS, SOURCE, catalog_codes, load_clips

MP3_HEADS = (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")


def test_every_audio_item_ships_its_reviewed_clip() -> None:
    codes = catalog_codes()
    durations = json.loads((CLIPS / "durations.json").read_text(encoding="utf-8"))
    assert len(codes) == len(set(codes)) == 89
    assert set(durations) == set(codes)  # a clip for every printed code, none for a code no page prints
    assert {p.stem for p in CLIPS.glob("*.mp3")} == set(codes)
    for code in codes:
        data = (CLIPS / f"{code}.mp3").read_bytes()
        assert data.startswith(MP3_HEADS) and len(data) > 4000, code
        assert 500 <= durations[code] <= 60_000, code


def _small_folder(tmp_path: Path, codes: list[str]) -> Path:
    """Three shipped clips (the real files), so the test stays quick."""
    durations = json.loads((CLIPS / "durations.json").read_text(encoding="utf-8"))
    for code in codes:
        (tmp_path / f"{code}.mp3").write_bytes((CLIPS / f"{code}.mp3").read_bytes())
    (tmp_path / "durations.json").write_text(json.dumps({c: durations[c] for c in codes}), encoding="utf-8")
    return tmp_path


def test_the_loader_fills_what_is_missing_and_keeps_peoples_recordings(
    db: Session, storage: ObjectStorage, tmp_path: Path
) -> None:
    codes = catalog_codes()
    loaded, stale, recorded = codes[0], codes[1], codes[2]
    folder = _small_folder(tmp_path, [loaded, stale, recorded])
    stale_key = clip_key(stale, "old", "mp3")
    storage.put(stale_key, b"ID3 an older take", "audio/mpeg")
    person_key = clip_key(recorded, "upload", "webm")
    storage.put(person_key, b"\x1a\x45\xdf\xa3 a teacher's voice", "audio/webm")
    db.add_all(
        [
            AudioClip(code=stale, storage_key=stale_key, mime="audio/mpeg", duration_ms=900, source=SOURCE),
            AudioClip(
                code=recorded, storage_key=person_key, mime="audio/webm", duration_ms=1500, source="upload"
            ),
        ]
    )
    db.commit()

    check = load_clips(db, storage, folder=folder, write=False)
    assert check.loaded == [loaded, stale] and check.kept == [recorded]
    assert len(check.no_clip) == len(codes) - 3  # this folder ships three clips only
    assert db.get(AudioClip, loaded) is None  # --check writes nothing

    report = load_clips(db, storage, folder=folder)
    assert report.loaded == [loaded, stale] and report.kept == [recorded]
    for code in (loaded, stale):
        clip = db.get(AudioClip, code)
        assert clip is not None and clip.source == SOURCE and clip.mime == "audio/mpeg"
        assert storage.get(clip.storage_key) == (folder / f"{code}.mp3").read_bytes()
    assert not storage.exists(stale_key)  # the older take is gone
    person = db.get(AudioClip, recorded)
    assert person is not None and person.source == "upload" and storage.exists(person_key)
    audits = db.scalars(select(AuditLog).where(AuditLog.action == "journey.audio_generated")).all()
    assert sorted(a.entity_id for a in audits) == sorted([loaded, stale])

    again = load_clips(db, storage, folder=folder)
    assert again.loaded == [] and again.current == [loaded, stale]  # nothing changes on a second run


def test_a_narrator_clip_made_on_the_fly_is_replaced_by_the_reviewed_one(
    db: Session, storage: ObjectStorage, tmp_path: Path
) -> None:
    code = catalog_codes()[5]
    folder = _small_folder(tmp_path, [code])
    key = clip_key(code, f"tts-fake-{uuid.uuid4().hex[:6]}", "wav")
    storage.put(key, b"RIFF....WAVE", "audio/wav")
    db.add(AudioClip(code=code, storage_key=key, mime="audio/wav", duration_ms=800, source="tts:fake"))
    db.commit()
    assert load_clips(db, storage, folder=folder).loaded == [code]
    clip = db.get(AudioClip, code)
    assert clip is not None and clip.source == SOURCE and not storage.exists(key)
