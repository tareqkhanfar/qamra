"""The audio behind the activity books' printed QR codes (Addendum 6 §4.8): the item catalog and signed links.

A QR on a page opens `https://{BRAND_DOMAIN}/a/{code}`, a short public player. The items (code, the words the
player shows, the script staff record) come from content/journey/audio.yaml, generated from the book's print
layers by `qamra_workbook.journey_book`; nothing in them is a child's data. Recordings stay in private storage
and reach browsers through same-origin API links signed with an HMAC that expires within 10 minutes (as the
«صوت أهلي» audio, ≤ 15 per the privacy rules); the API streams the bytes with HTTP ranges.
"""

import hashlib
import hmac
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_api.errors import MESSAGES

CATALOG = CONTENT_DIR / "journey" / "audio.yaml"
AUDIO_TTL_SECONDS = 600
CODE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz234567")

MESSAGES.update(
    {
        "audio_item_unknown": (
            "لم نجد هذا الصوت. تأكّدوا من الرمز المطبوع في الكتاب.",
            "We couldn't find this sound. Check the code printed in the book.",
        ),
    }
)


@lru_cache(maxsize=4)
def _load(path: Path, mtime: float) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(item["code"]): dict(item) for item in raw.get("items", [])}


def catalog(path: Path = CATALOG) -> dict[str, dict[str, Any]]:
    """Every audio item by code (reloaded when the file changes)."""
    if not path.exists():
        return {}
    return _load(path, path.stat().st_mtime)


def item(code: str, path: Path = CATALOG) -> dict[str, Any] | None:
    if not (4 <= len(code) <= 16) or not set(code) <= CODE_CHARS:
        return None
    return catalog(path).get(code)


def public_url(domain: str, code: str) -> str:
    """What the QR prints (`BookSpec.audio_url`)."""
    return f"https://{domain.strip().rstrip('/')}/a/{code}"


def _sig(secret: str, code: str, exp: int) -> str:
    return hmac.new(secret.encode(), f"journey-audio:{code}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def audio_link(secret: str, code: str, now: float | None = None) -> str:
    exp = int((now or time.time()) + AUDIO_TTL_SECONDS)
    return f"/api/a/{code}/audio?exp={exp}&sig={_sig(secret, code, exp)}"


def link_ok(secret: str, code: str, exp: int, sig: str, now: float | None = None) -> bool:
    fresh = 0 < exp - (now or time.time()) <= AUDIO_TTL_SECONDS
    return fresh and hmac.compare_digest(sig, _sig(secret, code, exp))
