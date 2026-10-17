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

Next to the clips, words.json (scripts/journey_word_times.py) says where each word sits in a clip, so the
player can play an item word by word with pauses and play one word on a tap. The API reads it from the
content folder and serves it only with the clip it was made from (same length); this loader checks that every
entry still matches its shipped clip (sha256, length, the item's shown words) and reports the stale ones:
a stale entry fails the run and `--check` (make the times again after changing a clip).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_core.db.audio import AudioClip, clip_key
from qamra_core.db.models import AuditLog
from qamra_core.storage import ObjectNotFound, ObjectStorage

CATALOG = CONTENT_DIR / "journey" / "audio.yaml"
CLIPS = CONTENT_DIR / "journey" / "clips"
WORD_TIMES = "words.json"
SOURCE = "tts:elevenlabs"
MIME = "audio/mpeg"


@dataclass
class Report:
    loaded: list[str] = field(default_factory=list)  # stored now (or, with --check, would be)
    current: list[str] = field(default_factory=list)  # the shipped clip is already in storage
    kept: list[str] = field(default_factory=list)  # a person's recording: never replaced
    no_clip: list[str] = field(default_factory=list)  # nothing shipped for the item (the player shows words)
    timed: list[str] = field(default_factory=list)  # word times that match their shipped clip
    stale_times: list[str] = field(default_factory=list)  # word times made from another clip: not served

    def lines(self, check: bool) -> list[str]:
        out = [
            f"{'to load' if check else 'loaded'}: {len(self.loaded)}",
            f"already in storage: {len(self.current)}",
            f"kept (recorded by people): {len(self.kept)}",
        ]
        if self.no_clip:
            out.append(f"no clip shipped (words only): {len(self.no_clip)}: {' '.join(self.no_clip)}")
        out.append(f"word times (tap a word, word by word): {len(self.timed)}")
        if self.stale_times:
            out.append(f"stale word times: {len(self.stale_times)}: {' '.join(self.stale_times)}")
        return out


def catalog_items(path: Path = CATALOG) -> list[dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [dict(item) for item in raw.get("items", [])]


def catalog_codes(path: Path = CATALOG) -> list[str]:
    return [str(item["code"]) for item in catalog_items(path)]


def _times_ok(entry: dict[str, Any], clip: Path, duration_ms: int | None, shown: int) -> bool:
    """A words.json entry still describes this clip: same bytes and length, ordered pieces inside the clip,
    and one (or no) piece for each word the item shows."""
    if not clip.is_file() or duration_ms is None or entry.get("duration_ms") != duration_ms:
        return False
    if entry.get("sha256") != hashlib.sha256(clip.read_bytes()).hexdigest():
        return False
    segments, show = entry.get("segments") or [], entry.get("show") or []
    end = 0
    for seg in segments:
        if len(seg) != 2 or not (end <= seg[0] < seg[1] <= duration_ms):
            return False
        end = seg[1]
    pieces = [k for s in show for k in (s if isinstance(s, list) else [s])]  # «أ ب ت …»: a piece per part
    return len(show) == shown and all(
        k is None or (isinstance(k, int) and 0 <= k < len(segments)) for k in pieces
    )


def check_word_times(folder: Path = CLIPS, catalog: Path = CATALOG) -> tuple[list[str], list[str]]:
    """The items whose word times match their shipped clip, and the stale ones (see the docstring)."""
    path = folder / WORD_TIMES
    if not path.is_file():
        return [], []
    times: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")).get("items") or {}
    durations: dict[str, int] = json.loads((folder / "durations.json").read_text(encoding="utf-8"))
    items = {str(i["code"]): i for i in catalog_items(catalog)}
    timed: list[str] = []
    stale: list[str] = []
    for code, entry in times.items():
        item = items.get(code)
        ok = item is not None and _times_ok(
            entry, folder / f"{code}.mp3", durations.get(code), len(item.get("show") or [])
        )
        (timed if ok else stale).append(code)
    return timed, stale


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
    report.timed, report.stale_times = check_word_times(folder, catalog)
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
    failed = report.no_clip or report.stale_times or (args.check and report.loaded)
    return 1 if failed else 0  # --check: 0 = all in place


if __name__ == "__main__":
    sys.exit(main())
