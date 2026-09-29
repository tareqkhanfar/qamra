"""Audio for the printed QR codes of the activity books (Addendum 6 §4.8): one row per audio item that has a
recording. The items themselves (their code, the words the player shows, the script staff record) live in the
book's content (content/journey/audio.yaml); a row here is the recording staff uploaded for an item, or the
narrator's TTS fallback made once. Files sit in private storage under `audio/`: shop content, never a
child's data, so the public player at /a/{code} can play them through short-lived signed links.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from qamra_core.db.base import Base, TimestampMixin


class AudioClip(TimestampMixin, Base):
    __tablename__ = "audio_clips"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)  # the QR's item code
    product: Mapped[str] = mapped_column(String(32), default="journey")
    storage_key: Mapped[str] = mapped_column(String(300))
    mime: Mapped[str] = mapped_column(String(40))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="upload")  # upload | tts:<provider>
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


def clip_key(code: str, clip_id: str, ext: str) -> str:
    """Private storage key of an item's recording (a new key per upload, so a replaced file never lingers)."""
    return f"audio/journey/{code}/{clip_id}.{ext}"
