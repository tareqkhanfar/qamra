"""TTS providers by name. "none" (the default) means no narration: the listen page shows the text."""

from qamra_ai.tts.base import Speech, TTSLang, TTSProvider
from qamra_ai.tts.fake import FakeTTSProvider

PROVIDERS = ("none", "fake")  # a paid provider is added here once Tareq approves one


def make_tts(name: str | None) -> TTSProvider | None:
    if name == "fake":
        return FakeTTSProvider()
    return None  # "none", empty, or a name this build doesn't have


__all__ = ["PROVIDERS", "FakeTTSProvider", "Speech", "TTSLang", "TTSProvider", "make_tts"]
