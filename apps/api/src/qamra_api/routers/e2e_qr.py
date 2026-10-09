"""Test-only fixtures for the printed QR codes' end-to-end test (tests/e2e/test_qr_codes.py), mounted with the
other `/api/e2e/*` fixtures (only when `E2E_FIXTURES=true`, never in prod). No AI, no paid call:

- `POST /api/e2e/journey-audio/{code}`: the item's reviewed clip, from the clips that ship with the code
  (content/journey/clips), as the server's loader `qamra_worker.journey_voices` stores it; an item that
  already has audio keeps it;
- `POST /api/e2e/books/{book_id}/family-voice`: the parent's own book as ordered with «أصوات العائلة» (a
  confirmed cash-on-delivery order with the add-on), its story pages given a line of text, so its printed
  codes open their listen pages.
"""

import json
import uuid
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_api.deps import CurrentUser, SessionDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.journey_audio import item
from qamra_core import voice
from qamra_core.db.audio import AudioClip, clip_key
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Child,
    Currency,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    SafetyStatus,
)

router = APIRouter(prefix="/api/e2e", tags=["e2e"])
CLIPS = CONTENT_DIR / "journey" / "clips"


class ClipOut(BaseModel):
    code: str
    loaded: bool  # false: the item already had audio


@router.post("/journey-audio/{code}")
async def journey_clip(code: str, user: CurrentUser, db: SessionDep, storage: StorageDep) -> ClipOut:
    path = CLIPS / f"{code}.mp3"
    if item(code) is None or not path.is_file():
        raise ApiError("audio_item_unknown", 404)
    if await db.get(AudioClip, code) is not None:
        return ClipOut(code=code, loaded=False)
    durations = json.loads((CLIPS / "durations.json").read_text(encoding="utf-8"))
    key = clip_key(code, uuid.uuid4().hex, "mp3")
    storage.put(key, path.read_bytes(), "audio/mpeg")
    clip = AudioClip(code=code, storage_key=key, mime="audio/mpeg", duration_ms=int(durations[code]))
    clip.source = "tts:elevenlabs"
    db.add(clip)
    await db.commit()
    return ClipOut(code=code, loaded=True)


class VoiceOrderOut(BaseModel):
    order_code: str
    beats: list[int]


@router.post("/books/{book_id}/family-voice")
async def family_voice_order(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> VoiceOrderOut:
    book = await db.get(Book, book_id)
    child = await db.get(Child, book.child_id) if book is not None else None
    if book is None or child is None or child.guardian_user_id != user.id:
        raise ApiError("not_found", 404)
    pages = (
        (await db.execute(select(BookPage).where(BookPage.book_id == book.id).order_by(BookPage.index)))
        .scalars()
        .all()
    )
    beats = []
    for page in pages:
        if page.index > 0:
            page.text = page.text or f"نَصٌّ تَجْرِيبِيٌّ لِلصَّفْحَةِ {page.index}."
            page.safety_status = SafetyStatus.passed
            beats.append(page.index)
    book.status = BookStatus.in_review
    order = Order(
        code=f"QM-E2E{uuid.uuid4().hex[:5].upper()}",
        user_id=user.id,
        status=OrderStatus.confirmed,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("154"),
        total=Decimal("154"),
    )
    db.add(order)
    await db.flush()
    addon = {"slug": voice.ADDON, "qty": 1, "unit_price": "15.00"}
    db.add(
        OrderItem(order_id=order.id, book_id=book.id, addons=[addon], quantity=1, unit_price=Decimal("139"))
    )
    await db.commit()
    return VoiceOrderOut(order_code=order.code, beats=beats)
