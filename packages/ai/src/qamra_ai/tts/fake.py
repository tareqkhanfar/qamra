"""Offline TTS for tests and dry runs: a quiet tone whose length follows the text (no network, no cost)."""

import io
import math
import struct
import wave

from qamra_ai.cost import CostEntry
from qamra_ai.tts.base import Speech, TTSLang

RATE = 8000


class FakeTTSProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def speak(self, *, text: str, lang: TTSLang, step: str = "tts") -> Speech:
        self.calls.append({"step": step, "lang": lang, "text": text})
        ms = min(20_000, max(600, 60 * len(text.split()) * 5))
        frames = int(RATE * ms / 1000)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(
                b"".join(
                    struct.pack("<h", int(900 * math.sin(2 * math.pi * 440 * i / RATE)))
                    for i in range(frames)
                )
            )
        cost = CostEntry(step, self.name, "fake-tts-1", {"characters": len(text)}, 0.0)
        return Speech(buf.getvalue(), "audio/wav", ms, cost)
