"""The voices behind the printed audio QR codes of «رحلتي الأولى للتعلّم», loaded into the server's storage.

On the server, after a deploy (from /opt/qamra; the worker has the database and storage settings):

    docker compose exec worker python -m qamra_worker.journey_voices --check   # report only
    docker compose exec worker python -m qamra_worker.journey_voices           # load what is missing

The clips ship with the code: content/journey/clips/<code>.mp3 and durations.json, one per item of
content/journey/audio.yaml (a test keeps them in step). They were made once by scripts/journey_voices.py
(ElevenLabs via fal, commercial use), transcribed back and checked against their script. An item gets the
shipped clip when it has no audio, or when its generated clip differs from the shipped file; a recording a
person uploaded («صوتيات الرحلة» in the admin) is never replaced. Every load is in the audit log, and running
it again changes nothing. Without a clip an item still opens: the player shows its words.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_core.db.audio import AudioClip, clip_key
from qamra_core.db.models import AuditLog
from qamra_core.storage import ObjectNotFound, ObjectStorage

CATALOG = CONTENT_DIR / "journey" / "audio.yaml"
CLIPS = CONTENT_DIR / "journey" / "clips"
SOURCE = "tts:elevenlabs"
MIME = "audio/mpeg"


@dataclass
class Report:
    loaded: list[str] = field(default_factory=list)  # stored now (or, with --check, would be)
    current: list[str] = field(default_factory=list)  # the shipped clip is already in storage
    kept: list[str] = field(default_factory=list)  # a person's recording: never replaced
    no_clip: list[str] = field(default_factory=list)  # nothing shipped for the item (the player shows words)

    def lines(self, check: bool) -> list[str]:
        out = [
            f"{'to load' if check else 'loaded'}: {len(self.loaded)}",
            f"already in storage: {len(self.current)}",
            f"kept (recorded by people): {len(self.kept)}",
        ]
        if self.no_clip:
            out.append(f"no clip shipped (words only): {len(self.no_clip)}: {' '.join(self.no_clip)}")
        return out


def catalog_codes(path: Path = CATALOG) -> list[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [str(item["code"]) for item in raw.get("items", [])]


def _stored(storage: ObjectStorage, key: str) -> bytes | None:
    try:
        return storage.get(key)
    except ObjectNotFound:
        return None


def load_clips(
    db: Session,
    storage: ObjectStorage,
    *,
    folder: Path = CLIPS,
    catalog: Path = CATALOG,
    write: bool = True,
) -> Report:
    """Store the shipped clip of every catalog item that lacks it (see the module's docstring)."""
    durations: dict[str, int] = json.loads((folder / "durations.json").read_text(encoding="utf-8"))
    existing = {c.code: c for c in db.scalars(select(AudioClip)).all()}
    report = Report()
    for code in catalog_codes(catalog):
        clip, path = existing.get(code), folder / f"{code}.mp3"
        if clip is not None and not clip.source.startswith("tts:"):
            report.kept.append(code)
            continue
        if not path.is_file() or code not in durations:
            report.no_clip.append(code)
            continue
        data = path.read_bytes()
        if clip is not None and clip.source == SOURCE and _stored(storage, clip.storage_key) == data:
            report.current.append(code)
            continue
        report.loaded.append(code)
        if not write:
            continue
        key = clip_key(code, uuid.uuid4().hex, "mp3")
        storage.put(key, data, MIME)
        old = clip.storage_key if clip is not None else None
        if clip is None:
            clip = AudioClip(code=code, storage_key=key, mime=MIME)
            db.add(clip)
        clip.storage_key, clip.mime, clip.duration_ms, clip.source = key, MIME, durations[code], SOURCE
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
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true", help="only report what would be loaded")
    parser.add_argument("--dir", type=Path, default=CLIPS, help="the clips (default: content/journey/clips)")
    args = parser.parse_args(argv)
    from qamra_worker import context  # the server's database and storage (env / .env)

    with context.db_session() as db:
        report = load_clips(db, context.storage(), folder=args.dir, write=not args.check)
    print("\n".join(report.lines(args.check)))
    return 1 if report.no_clip or (args.check and report.loaded) else 0  # --check: 0 = all in place


if __name__ == "__main__":
    sys.exit(main())
