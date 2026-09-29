"""The TTS adapter: no narrator by default (no paid provider until approved), a fake one for tests."""

import inspect
import io
import wave

from qamra_ai.tts import PROVIDERS, FakeTTSProvider, TTSProvider, make_tts
from qamra_core.app_settings import REGISTRY


def test_no_provider_by_default() -> None:
    assert REGISTRY["tts_provider"].default == "none"
    assert set(REGISTRY["tts_provider"].choices) == set(PROVIDERS) == {"none", "fake"}
    for name in (None, "", "none", "elevenlabs"):
        assert make_tts(name) is None


async def test_the_fake_narrator_speaks_offline() -> None:
    tts = make_tts("fake")
    assert isinstance(tts, FakeTTSProvider)
    speech = await tts.speak(text="كانَ يا ما كانَ في قَديمِ الزَّمان", lang="ar")
    assert speech.mime == "audio/wav" and speech.cost.usd == 0 and tts.calls[0]["lang"] == "ar"
    with wave.open(io.BytesIO(speech.audio)) as w:
        assert w.getnframes() / w.getframerate() * 1000 == speech.duration_ms


def test_the_interface_takes_no_voice_sample() -> None:
    """Real voices only: a narrator reads text; it can't be given a family member's voice to imitate."""
    assert list(inspect.signature(TTSProvider.speak).parameters) == ["self", "text", "lang", "step"]
