"""«صوت أهلي»: the owner's recordings, a grandparent's link (open, expired, revoked, other pages), the listen
page behind the printed QR, signed audio, the TTS fallback switch, and deleting the child's data."""

import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from api_helpers import register
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api import voice_common
from qamra_core.db.models import (
    AppSetting,
    Book,
    BookPage,
    BookStatus,
    Child,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Recording,
    SafetyStatus,
    ShareScope,
    ShareToken,
    Theme,
)
from qamra_core.storage import ObjectStorage

WEBM = b"\x1a\x45\xdf\xa3" + bytes(range(256)) * 4
MP4 = b"\x00\x00\x00\x18ftypM4A " + bytes(range(256)) * 4


async def _book(
    adb: AsyncSession, storage: ObjectStorage, user_id: str, *, addon: bool = True, cancelled: bool = False
) -> Book:
    child = Child(guardian_user_id=uuid.UUID(user_id), first_name="ليان", gender=Gender.f, birth_year=2021)
    theme = Theme(
        slug=f"t-{uuid.uuid4().hex[:8]}",
        title_ar="حارس النجوم",
        title_en="Star keeper",
        age_min=3,
        age_max=7,
        definition={},
    )
    adb.add_all([child, theme])
    await adb.flush()
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=1,
        created_by_user_id=uuid.UUID(user_id),
        language=Locale.ar,
        art_style="watercolor",
        status=BookStatus.in_review,
        title="ليان وحارس النجوم",
    )
    adb.add(book)
    await adb.flush()
    for beat in range(0, 5):
        key = f"children/{child.id}/books/{book.id}/raw/{beat:02d}.png"
        storage.put(key, b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/png")
        adb.add(
            BookPage(
                book_id=book.id,
                index=beat,
                text=None if beat == 0 else f"صفحة {beat}",
                image_key=key,
                safety_status=SafetyStatus.failed if beat == 4 else SafetyStatus.passed,
            )
        )
    order = Order(
        code=f"QM-{uuid.uuid4().hex[:6].upper()}",
        user_id=uuid.UUID(user_id),
        status=OrderStatus.cancelled if cancelled else OrderStatus.confirmed,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("154"),
        total=Decimal("154"),
    )
    adb.add(order)
    await adb.flush()
    addons = [{"slug": "family-voice", "qty": 1, "unit_price": "15.00"}] if addon else []
    adb.add(
        OrderItem(order_id=order.id, book_id=book.id, addons=addons, quantity=1, unit_price=Decimal("139"))
    )
    await adb.commit()
    return book


async def _record(client: AsyncClient, book: Book, beat: int, name: str, data: bytes = WEBM, ms: int = 4000):
    return await client.post(
        f"/api/books/{book.id}/voice/pages/{beat}",
        data={"voice": name, "duration_ms": str(ms)},
        files={"file": ("rec", data, "audio/webm")},
    )


async def test_the_parent_records_listens_and_records_again(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    r = await client.get(f"/api/books/{book.id}/voice")
    assert r.status_code == 200, r.text
    data = r.json()
    assert [p["beat"] for p in data["pages"]] == [1, 2, 3]  # page 4 failed the safety check
    assert (
        data["listen_url"].startswith("https://qamra.app/v/")
        and data["listening"]
        and data["max_voices"] == 3
    )
    r = await _record(client, book, 1, "  ماما ")
    assert r.status_code == 201, r.text
    [rec] = r.json()["pages"][0]["recordings"]
    assert rec["voice"] == "ماما" and rec["duration_ms"] == 4000 and not rec["by_invite"]
    audio = await client.get(rec["audio"])
    assert (
        audio.status_code == 200 and audio.content == WEBM and audio.headers["content-type"] == "audio/webm"
    )
    part = await client.get(rec["audio"], headers={"Range": "bytes=0-3"})
    assert (
        part.status_code == 206
        and part.content == WEBM[:4]
        and part.headers["content-range"].endswith("/1028")
    )
    first_key = (await adb.execute(select(Recording.storage_key))).scalar_one()
    assert first_key.startswith(f"children/{book.child_id}/books/{book.id}/voice/01-") and first_key.endswith(
        ".webm"
    )

    r = await _record(client, book, 1, "ماما", MP4, 5000)  # re-record: the same voice, a new file
    [rec] = r.json()["pages"][0]["recordings"]
    assert rec["duration_ms"] == 5000 and r.json()["voices"] == ["ماما"]
    assert not storage.exists(first_key)
    assert (await client.get(rec["audio"])).headers["content-type"] == "audio/mp4"

    r = await client.delete(f"/api/books/{book.id}/voice/recordings/{rec['id']}")
    assert r.status_code == 200 and r.json()["pages"][0]["recordings"] == []
    assert (await adb.execute(select(Recording))).first() is None


async def test_three_voices_per_page_and_clean_input(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    for name in ("ماما", "بابا", "ستّي"):
        assert (await _record(client, book, 2, name)).status_code == 201
    r = await _record(client, book, 2, "سيدي")
    assert r.status_code == 409 and r.json()["error"]["code"] == "voice_limit"
    assert (await _record(client, book, 3, "سيدي")).status_code == 201  # another page has room
    assert (await _record(client, book, 2, "ماما", b"not audio at all" * 20)).json()["error"]["code"] == (
        "invalid_audio"
    )
    assert (await _record(client, book, 2, "ماما", ms=4 * 60 * 1000)).json()["error"][
        "code"
    ] == "audio_too_long"
    assert (await _record(client, book, 2, "   ")).json()["error"]["code"] == "invalid_label"
    assert (await _record(client, book, 4, "ماما")).status_code == 404  # not a readable page
    assert (await _record(client, book, 0, "ماما")).status_code == 404  # the cover


async def test_no_add_on_no_voice_and_other_parents_books(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    plain = await _book(adb, storage, me["id"], addon=False)
    r = await client.get(f"/api/books/{plain.id}/voice")
    assert r.status_code == 403 and r.json()["error"]["code"] == "voice_not_included"
    cancelled = await _book(adb, storage, me["id"], cancelled=True)
    assert (await client.get(f"/api/books/{cancelled.id}/voice")).status_code == 403
    mine = await _book(adb, storage, me["id"])
    rec = (await _record(client, mine, 1, "ماما")).json()["pages"][0]["recordings"][0]

    await client.post("/api/auth/logout")
    await register(client, email="other@example.com")
    assert (await client.get(f"/api/books/{mine.id}/voice")).status_code == 404
    assert (await _record(client, mine, 1, "بابا")).status_code == 404
    theirs = await _book(adb, storage, (await client.get("/api/auth/me")).json()["id"])
    r = await client.delete(f"/api/books/{theirs.id}/voice/recordings/{rec['id']}")
    assert r.status_code == 404  # a recording of another book


async def test_a_grandparents_link(client: AsyncClient, adb: AsyncSession, storage: ObjectStorage) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    r = await client.post(f"/api/books/{book.id}/voice/invites", json={"label": "ستّي", "pages": [1, 2]})
    assert r.status_code == 201, r.text
    invite = r.json()
    token = invite["path"].removeprefix("/r/")
    assert invite["active"] and invite["opened_at"] is None and invite["total"] == 2
    assert invite["expires_at"] and datetime.fromisoformat(invite["expires_at"]) > datetime.now(
        UTC
    ) + timedelta(days=6)
    await client.post("/api/auth/logout")  # the grandparent has no account

    r = await client.get(f"/api/voice/invites/{token}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert (
        data["label"] == "ستّي"
        and data["child_name"] == "ليان"
        and [p["beat"] for p in data["pages"]] == [1, 2]
    )
    assert "id" not in data and "book_id" not in data  # nothing that identifies the family
    up = await client.post(
        f"/api/voice/invites/{token}/pages/2",
        data={"duration_ms": "3000"},
        files={"file": ("r", WEBM, "audio/webm")},
    )
    assert up.status_code == 201, up.text
    assert (await client.get(up.json()["pages"][1]["audio"])).content == WEBM
    other = await client.post(
        f"/api/voice/invites/{token}/pages/3", data={"duration_ms": "3000"}, files={"file": ("r", WEBM, "a")}
    )
    assert other.status_code == 404  # a page the invite doesn't cover

    await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "moonlight-2026"}
    )
    owner = (await client.get(f"/api/books/{book.id}/voice")).json()
    [inv] = owner["invites"]
    assert inv["opened_at"] and inv["recorded"] == 1 and inv["total"] == 2
    rec = owner["pages"][1]["recordings"][0]
    assert rec["voice"] == "ستّي" and rec["by_invite"]

    r = await client.delete(f"/api/books/{book.id}/voice/invites/{inv['id']}")
    assert r.status_code == 204
    r = await client.get(f"/api/voice/invites/{token}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "invite_unavailable"


async def test_expired_and_unknown_invites(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    invite = (await client.post(f"/api/books/{book.id}/voice/invites", json={"label": "سيدي"})).json()
    token = invite["path"].removeprefix("/r/")
    assert invite["pages"] is None and invite["total"] == 3
    row = (await adb.execute(select(ShareToken).where(ShareToken.token == token))).scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await adb.commit()
    assert (await client.get(f"/api/voice/invites/{token}")).status_code == 404
    up = await client.post(
        f"/api/voice/invites/{token}/pages/1", data={"duration_ms": "3000"}, files={"file": ("r", WEBM, "a")}
    )
    assert up.status_code == 404 and up.json()["error"]["code"] == "invite_unavailable"
    assert (await client.get("/api/voice/invites/not-a-real-token-at-all")).status_code == 404
    listen = (await client.get(f"/api/books/{book.id}/voice")).json()["listen_url"].rsplit("/", 1)[1]
    assert (await client.get(f"/api/voice/invites/{listen}")).status_code == 404  # a listen link can't record


async def test_the_listen_page_behind_the_printed_qr(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    for name in ("ماما", "ستّي"):
        await _record(client, book, 1, name)
    token = (await client.get(f"/api/books/{book.id}/voice")).json()["listen_url"].rsplit("/", 1)[1]
    await client.post("/api/auth/logout")

    start = (await client.get(f"/api/voice/listen/{token}")).json()
    assert start == {"first": 1, "language": "ar"}
    r = await client.get(f"/api/voice/listen/{token}/1")
    assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex"
    page = r.json()
    assert sorted(v["label"] for v in page["voices"]) == ["ستّي", "ماما"] and page["narrator"] is None
    assert (page["number"], page["total"], page["prev"], page["next"]) == (1, 3, None, 2)
    assert (await client.get(page["image"])).status_code == 200
    assert (await client.get(page["voices"][0]["audio"])).content == WEBM
    silent = (await client.get(f"/api/voice/listen/{token}/2")).json()
    assert silent["voices"] == [] and silent["narrator"] is None and silent["text"] == "صفحة 2"
    assert (await client.get(f"/api/voice/listen/{token}/2/narrator")).status_code == 404  # no provider on
    assert (await client.get(f"/api/voice/listen/{token}/4")).status_code == 404

    adb.add(AppSetting(key="tts_provider", value="fake"))
    await adb.commit()
    narrated = (await client.get(f"/api/voice/listen/{token}/2")).json()
    speech = await client.get(narrated["narrator"])
    assert speech.status_code == 200 and speech.content[:4] == b"RIFF"
    assert storage.exists(f"children/{book.child_id}/books/{book.id}/voice/tts/fake-02.wav")

    await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "moonlight-2026"}
    )
    assert (await client.put(f"/api/books/{book.id}/voice/listening", json={"on": False})).json()[
        "listening"
    ] is False
    r = await client.get(f"/api/voice/listen/{token}/1")
    assert r.status_code == 404 and r.json()["error"]["code"] == "listen_unavailable"
    await client.put(f"/api/books/{book.id}/voice/listening", json={"on": True})
    assert (
        await client.get(f"/api/voice/listen/{token}/1")
    ).status_code == 200  # the printed codes work again


async def test_audio_links_are_signed_and_expire(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    rec = (await _record(client, book, 1, "ماما")).json()["pages"][0]["recordings"][0]
    assert (await client.get(rec["audio"][:-4] + "0000")).status_code == 404
    rid = uuid.UUID(rec["id"])
    exp = int(time.time()) + 60
    good = voice_common._sig("x" * 32, rid, exp)
    assert voice_common.audio_ok("x" * 32, rid, exp, good)
    assert not voice_common.audio_ok("x" * 32, rid, exp, good, now=exp + 1)  # expired
    assert not voice_common.audio_ok("x" * 32, rid, exp + 3600, voice_common._sig("x" * 32, rid, exp + 3600))
    assert voice_common.AUDIO_TTL_SECONDS <= 900  # the privacy rules: ≤ 15 minutes


async def test_deleting_the_child_deletes_the_recordings(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    me = await register(client)
    book = await _book(adb, storage, me["id"])
    await _record(client, book, 1, "ماما")
    await client.post(f"/api/books/{book.id}/voice/invites", json={"label": "ستّي"})
    key = (await adb.execute(select(Recording.storage_key))).scalar_one()
    assert storage.exists(key)
    r = await client.delete(f"/api/create/children/{book.child_id}")
    assert r.status_code == 204, r.text
    assert not storage.exists(key)
    assert (await adb.execute(select(Recording))).first() is None
    assert (
        await adb.execute(select(ShareToken).where(ShareToken.scope == ShareScope.record))
    ).first() is None


def test_link_tokens_stay_out_of_the_request_log() -> None:
    from qamra_api.logging import safe_path

    assert safe_path("/api/voice/listen/lqn98STtT10rWGkiEtwB/3") == "/api/voice/listen/…/3"
    assert (
        safe_path("/api/voice/invites/abcdefghijklmnopqrstuvwxyz12/pages/2") == "/api/voice/invites/…/pages/2"
    )
    assert safe_path("/api/shared/tok123456789012345678901") == "/api/shared/…"
    book = "/api/books/1c8e5ce2-d628-48e2-b116-dcbfa5b4ee13/voice"
    assert safe_path(book) == book  # ids stay: they are useless without the parent's session
