"""«صوت أهلي»: the family's own voices reading the book (Addendum 1 §3, Phase 5). Used by the api and worker.

- A book has the feature when an order line for it carries the `family-voice` add-on (and the order wasn't
  cancelled). Without it, nothing is printed and nothing can be recorded.
- Real voices only: recordings are uploaded by the family; nothing here (or anywhere) clones a voice.
- Every story page gets a fixed QR link printed in the book: `https://{BRAND_DOMAIN}/v/{listen token}/{page}`.
  Voices recorded after printing play from the same link. The parent can switch listening off and on.
- Recordings live under the child's storage prefix, so «حذف بيانات الطفل» deletes them with everything else;
  their rows go with the book (ON DELETE CASCADE).
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, exists, select

from qamra_core.db.models import Order, OrderItem, OrderStatus, ShareScope, ShareToken

ADDON = "family-voice"
MAX_VOICES_PER_PAGE = 3
INVITE_DAYS = 7  # a grandparent's recording link
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_AUDIO_MS = 3 * 60 * 1000
LISTEN_TOKEN_BYTES = 15  # 20 URL-safe characters (120 bits): short, so the printed QR stays coarse
INVITE_TOKEN_BYTES = 24

# (sniffed type, file extension); MediaRecorder gives MP4/AAC on Safari, WebM/Opus or Ogg elsewhere
AUDIO_TYPES = {
    "audio/mp4": "m4a",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
}
EXT_TYPES = {ext: mime for mime, ext in AUDIO_TYPES.items()}


def addon_query(book_id: uuid.UUID) -> Select[tuple[bool]]:
    """True when a live order bought the family-voice add-on for this book."""
    return select(
        exists()
        .where(
            OrderItem.book_id == book_id,
            OrderItem.order_id == Order.id,
            Order.status != OrderStatus.cancelled,
            OrderItem.addons.contains([{"slug": ADDON}]),
        )
        .correlate(None)
    )


def listen_token_query(book_id: uuid.UUID) -> Select[ShareToken]:
    """The book's printed listening link (revoked = listening paused by the parent)."""
    return (
        select(ShareToken)
        .where(ShareToken.book_id == book_id, ShareToken.scope == ShareScope.listen)
        .order_by(ShareToken.created_at)
        .limit(1)
    )


def new_listen_token(book_id: uuid.UUID) -> ShareToken:
    """No expiry: it is printed. `revoked_at` pauses it; clearing it brings the printed codes back."""
    return ShareToken(
        book_id=book_id, token=secrets.token_urlsafe(LISTEN_TOKEN_BYTES), scope=ShareScope.listen
    )


def new_invite(
    book_id: uuid.UUID, label: str, pages: list[int] | None, now: datetime | None = None
) -> ShareToken:
    now = now or datetime.now(UTC)
    return ShareToken(
        book_id=book_id,
        token=secrets.token_urlsafe(INVITE_TOKEN_BYTES),
        scope=ShareScope.record,
        label=label,
        pages=sorted(set(pages)) if pages else None,
        expires_at=now + timedelta(days=INVITE_DAYS),
    )


def listen_base_url(domain: str, token: str) -> str:
    """`https://qamra.app/v/<token>`; each page appends `/<page>`."""
    return f"https://{domain.strip().rstrip('/')}/v/{token}"


def recording_key(
    child_id: uuid.UUID, book_id: uuid.UUID, page: int, recording_id: uuid.UUID, ext: str
) -> str:
    """Under `children/{child}/`: the child's data deletion removes every recording with one prefix delete."""
    return f"children/{child_id}/books/{book_id}/voice/{page:02d}-{recording_id}.{ext}"


def tts_key(child_id: uuid.UUID, book_id: uuid.UUID, page: int, provider: str, ext: str) -> str:
    return f"children/{child_id}/books/{book_id}/voice/tts/{provider}-{page:02d}.{ext}"


def sniff_audio(data: bytes) -> str | None:
    """The audio type from the file's first bytes (never trust the browser's claim)."""
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "audio/webm"
    if data[:4] == b"OggS":
        return "audio/ogg"
    if data[4:8] == b"ftyp":
        return "audio/mp4"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "audio/mpeg"
    return None


def clean_label(raw: str) -> str:
    """A voice name typed by the family («ماما», «ستّي أم أحمد»): trimmed, single spaces, ≤ 30 characters."""
    label = " ".join(raw.split())[:30]
    if not label or any(ch in label for ch in "<>/\\{}"):
        raise ValueError("label")
    return label
