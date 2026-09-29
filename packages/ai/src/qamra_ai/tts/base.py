"""Text-to-speech interface (CLAUDE.md §4 "TTS: adapter interface only at first"; Addendum 1 §3 fallback).

Used only when a page has no family recording. It reads the page text in a generic narrator voice:
the interface takes no reference audio, so it can never imitate (clone) a family member's voice.
No paid provider is implemented yet: choosing one needs Tareq's approval, and the admin setting
`tts_provider` stays "none" until then (the listen page then shows the text only).
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from qamra_ai.cost import CostEntry

TTSLang = Literal["ar", "en"]


@dataclass(frozen=True)
class Speech:
    audio: bytes
    mime: str  # audio/wav, audio/mpeg…
    duration_ms: int
    cost: CostEntry


class TTSProvider(Protocol):
    name: str

    async def speak(self, *, text: str, lang: TTSLang, step: str = "tts") -> Speech: ...
