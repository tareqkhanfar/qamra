"""Load the generated QR voices (scripts/journey_voices.py → <dir>/<code>.mp3 + durations.json) as the items'
recordings, on a server, inside the worker container (it has the database and storage settings):

    docker compose cp out/journey-audio worker:/tmp/journey-audio
    docker compose exec worker python /app/scripts/load_journey_voices.py /tmp/journey-audio

A clip a person uploaded («صوتيات الرحلة») is never replaced; earlier generated clips are. Each load is in the
audit log. The files stay in private storage, as uploads do.
"""

import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from qamra_core.db.audio import AudioClip, clip_key
from qamra_core.db.models import AuditLog
from qamra_core.db.session import make_sync_engine, make_sync_sessionmaker
from qamra_core.settings import CoreSettings
from qamra_core.storage import ObjectStorage

SOURCE = "tts:elevenlabs"


def main(folder: Path) -> None:
    settings = CoreSettings()
    storage = ObjectStorage.from_settings(settings)
    durations: dict[str, int] = json.loads((folder / "durations.json").read_text(encoding="utf-8"))
    session = make_sync_sessionmaker(make_sync_engine(settings.database_url))()
    loaded = kept = 0
    with session as db:
        existing = {c.code: c for c in db.scalars(select(AudioClip)).all()}
        for code, ms in sorted(durations.items()):
            clip = existing.get(code)
            if clip is not None and not clip.source.startswith("tts:"):
                kept += 1  # a person's recording wins
                continue
            key = clip_key(code, uuid.uuid4().hex, "mp3")
            storage.put(key, (folder / f"{code}.mp3").read_bytes(), "audio/mpeg")
            old = clip.storage_key if clip is not None else None
            if clip is None:
                clip = AudioClip(code=code, storage_key=key, mime="audio/mpeg")
                db.add(clip)
            clip.storage_key, clip.mime, clip.duration_ms, clip.source = key, "audio/mpeg", ms, SOURCE
            clip.uploaded_by_user_id = None
            db.add(
                AuditLog(
                    actor_user_id=None,
                    action="journey.audio_generated",
                    entity_type="audio",
                    entity_id=code,
                    data={"source": SOURCE, "replaced": old is not None},
                )
            )
            db.commit()
            if old and old != key:
                storage.delete(old)
            loaded += 1
    print(f"loaded {loaded}, kept {kept} recordings made by people")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
