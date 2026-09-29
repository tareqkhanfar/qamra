"""The audio QR codes of «رحلتي الأولى للتعلّم» (Addendum 6 §4.8): a public player with no child data, audio
through signed links that expire, staff-only uploads, and the TTS fallback (off unless a provider is on)."""

from api_helpers import make_admin, register
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api import journey_audio
from qamra_core.db.audio import AudioClip
from qamra_core.db.models import AppSetting
from qamra_core.storage import ObjectStorage

WEBM = b"\x1a\x45\xdf\xa3" + bytes(range(256)) * 4
SOUNDS = "ogjmg6ob"  # stage 1, page 28: animal sounds (never read by the narrator)
WORDS = "journey:s1:p32"  # stage 1, page 32: words the narrator may read


def _code(key: str) -> str:
    from qamra_workbook.journey_book import audio_code

    return audio_code(key)


async def test_the_player_shows_the_words_until_an_item_has_audio(client: AsyncClient) -> None:
    r = await client.get(f"/api/a/{SOUNDS}")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["audio"] is None and body["source"] is None  # no error: the page shows the words
    assert body["show"] == ["بَقَرَة", "قِطَّة", "دِيك"] and body["lang"] == "ar"
    assert set(body) == {"code", "lang", "title", "show", "audio", "source"}  # nothing about any child
    for bad in ("zzzzzzzz", "ABC", "a" * 40, "abc-1234"):
        assert (await client.get(f"/api/a/{bad}")).status_code == 404


async def test_only_staff_with_the_journey_permission_upload(client: AsyncClient, adb: AsyncSession) -> None:
    form = {"data": {"duration_ms": "2400"}, "files": {"file": ("rec", WEBM, "audio/webm")}}
    assert (await client.post(f"/api/admin/journey/audio/{SOUNDS}", **form)).status_code == 401
    await register(client, email="parent.audio@example.com")
    assert (await client.post(f"/api/admin/journey/audio/{SOUNDS}", **form)).status_code == 403
    assert (await client.get("/api/admin/journey/audio?stage=1")).status_code == 403
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="support.audio@example.com", roles=("support",))
    assert (await client.post(f"/api/admin/journey/audio/{SOUNDS}", **form)).status_code == 403


async def test_staff_upload_and_replace_and_the_link_is_signed(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    await make_admin(client, adb, email="editor.audio@example.com", roles=("editor",))
    listed = (await client.get("/api/admin/journey/audio?stage=1")).json()
    item = next(i for i in listed["items"] if i["code"] == SOUNDS)
    assert item["page"] == 28 and not item["has_audio"] and item["url"].endswith(f"/a/{SOUNDS}")
    form = {"data": {"duration_ms": "2400"}, "files": {"file": ("rec", WEBM, "audio/webm")}}
    first = (await client.post(f"/api/admin/journey/audio/{SOUNDS}", **form)).json()
    assert first["has_audio"] and first["source"] == "upload" and first["duration_ms"] == 2400
    old = (await adb.get(AudioClip, SOUNDS)).storage_key  # type: ignore[union-attr]
    again = await client.post(f"/api/admin/journey/audio/{SOUNDS}", **form)
    assert again.status_code == 200
    await adb.refresh(await adb.get(AudioClip, SOUNDS))  # type: ignore[arg-type]
    clip = await adb.get(AudioClip, SOUNDS)
    assert clip is not None and clip.storage_key != old and not storage.exists(old)  # replaced, old file gone
    bad = {"data": {"duration_ms": "2400"}, "files": {"file": ("rec", b"not audio" * 40, "audio/webm")}}
    assert (await client.post(f"/api/admin/journey/audio/{SOUNDS}", **bad)).status_code == 422

    await client.post("/api/auth/logout")  # anyone with the printed QR can listen
    player = (await client.get(f"/api/a/{SOUNDS}")).json()
    assert player["source"] == "recording" and player["audio"].startswith(f"/api/a/{SOUNDS}/audio?exp=")
    played = await client.get(player["audio"])
    assert played.status_code == 200 and played.content == WEBM
    ranged = await client.get(player["audio"], headers={"Range": "bytes=0-3"})
    assert ranged.status_code == 206 and ranged.content == WEBM[:4]
    tampered = player["audio"][:-2] + ("00" if not player["audio"].endswith("00") else "11")
    assert (await client.get(tampered)).status_code == 404
    other = player["audio"].replace(f"/a/{SOUNDS}/", f"/a/{_code(WORDS)}/")  # a link is for one item only
    assert (await client.get(other)).status_code == 404


def test_signed_links_expire_within_ten_minutes() -> None:
    secret, now = "s3cret", 1_800_000_000.0
    link = journey_audio.audio_link(secret, SOUNDS, now)
    exp = int(link.split("exp=")[1].split("&")[0])
    sig = link.split("sig=")[1]
    assert exp - now == journey_audio.AUDIO_TTL_SECONDS <= 15 * 60
    assert journey_audio.link_ok(secret, SOUNDS, exp, sig, now + 60)
    assert not journey_audio.link_ok(secret, SOUNDS, exp, sig, now + journey_audio.AUDIO_TTL_SECONDS + 1)
    assert not journey_audio.link_ok("other", SOUNDS, exp, sig, now)
    assert not journey_audio.link_ok(secret, SOUNDS, int(now + 86_400), sig, now)  # a far expiry is refused


async def test_the_narrator_reads_words_once_a_provider_is_on(
    client: AsyncClient, adb: AsyncSession, storage: ObjectStorage
) -> None:
    words = _code(WORDS)
    assert (await client.get(f"/api/a/{words}")).json()["audio"] is None  # provider "none": the words only
    adb.add(AppSetting(key="tts_provider", value="fake"))
    await adb.commit()
    player = (await client.get(f"/api/a/{words}")).json()
    assert player["source"] == "narrator"
    speech = await client.get(player["audio"])
    assert speech.status_code == 200 and speech.content[:4] == b"RIFF"
    clip = await adb.get(AudioClip, words)
    assert clip is not None and clip.source == "tts:fake" and storage.exists(clip.storage_key)  # made once
    assert (await client.get(f"/api/a/{SOUNDS}")).json()["audio"] is None  # sounds are never narrated
