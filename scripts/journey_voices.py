"""The voices behind the activity books' QR codes (content/journey/audio.yaml), made once and checked.

    uv run python scripts/journey_voices.py [--only CODE ...] [--voice NAME] [--trial]

Words and letters: ElevenLabs Multilingual v2 through fal (commercial use; about $0.10 per 1000 characters),
read slowly for young children. The sound items (animals, house sounds, loud/quiet, fast/slow): ElevenLabs
sound effects ($0.002 a second), each announced by the same voice («الصوت الأول» …). Every clip is transcribed
back (Whisper) and compared with its script without the tashkeel; clips under the similarity bar are listed
in out/journey-audio/report.json for a person to listen to. Files land in out/journey-audio/<code>.mp3, ready
for the admin's «صوتيات الرحلة» (or the server loader). The fal key comes from FAL_KEY; it is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import fal_client
import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "content/journey/audio.yaml"
OUT = ROOT / "out/journey-audio"
LEDGER = ROOT / "out/design-images/ledger.jsonl"
TTS = "fal-ai/elevenlabs/tts/multilingual-v2"
SFX = "fal-ai/elevenlabs/sound-effects/v2"
STT = "fal-ai/whisper"
_TASHKEEL = re.compile(r"[ً-ْٰـ]")
# The sound items: what the voice says first, then the sound(s): ("sfx", English prompt, seconds) or
# ("say", words).
Part = tuple[str, str, float]
SOUNDS: dict[str, list[tuple[str, list[Part]]]] = {
    "ogjmg6ob": [
        ("الصَّوْتُ الأَوَّلُ", [("sfx", "a cow mooing once, farm, clear", 2.5)]),
        ("الصَّوْتُ الثّاني", [("sfx", "a cat meowing twice, close, clear", 2.0)]),
        ("الصَّوْتُ الثّالِثُ", [("sfx", "a rooster crowing once at dawn, clear", 3.0)]),
    ],
    "dscofnrk": [
        ("الأَوَّلُ", [("sfx", "one loud bass drum hit, strong", 1.5)]),
        ("الثّاني", [("sfx", "a small bell ringing softly and quietly", 2.0)]),
        ("الثّالِثُ", [("sfx", "a loud referee whistle blow", 1.5)]),
        ("الرّابِعُ", [("sfx", "a kitten meowing very softly and quietly", 2.0)]),
    ],
    "55ahywkt": [
        ("الأَوَّلُ", [("sfx", "a house doorbell ding-dong", 2.0)]),
        ("الثّاني", [("sfx", "a telephone ringing twice", 3.0)]),
        ("الثّالِثُ", [("sfx", "water running from a kitchen tap", 3.0)]),
    ],
    "awizj364": [
        ("الأَوَّلُ", [("sfx", "fast drum beats, quick rhythm", 3.0)]),
        ("الثّاني", [("sfx", "slow drum beats, one hit per second", 4.0)]),
        ("الثّالِثُ", [("sfx", "fast running footsteps on a wooden floor", 3.0)]),
        ("الرّابِعُ", [("sfx", "slow walking footsteps on a wooden floor", 4.0)]),
    ],
    "qzvkwkgg": [
        (
            "الأَوَّلُ",
            [("sfx", "a rooster crowing once, clear", 2.5), ("sfx", "a rooster crowing once, clear", 2.5)],
        ),
        ("الثّاني", [("sfx", "a cat meowing once, clear", 1.5), ("sfx", "a cow mooing once, clear", 2.5)]),
        ("الثّالِثُ", [("sfx", "a small hand bell ringing", 1.5), ("sfx", "a small hand bell ringing", 1.5)]),
        ("الرّابِعُ", [("sfx", "three drum hits", 1.5), ("sfx", "a short whistle blow", 1.5)]),
    ],
    "2zzmflqo": [
        ("الأَوَّلُ", [("sfx", "a cow mooing once, farm, clear", 2.5)]),
        ("الثّاني", [("sfx", "one loud bass drum hit, strong", 1.5)]),
        ("الثّالِثُ", [("say", "شَمْس", 0.0)]),
    ],
}
WORDS = re.compile(r"\s*[.،:]\s*")  # word-by-word clips: each word alone, a short pause between them


def fal_key() -> str:
    key = os.environ.get("FAL_KEY", "")
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("FAL_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        sys.exit("FAL_KEY is not set")
    return key


def plain(text: str) -> str:
    """Letters only: no tashkeel, punctuation or case, single spaces (how a transcript is compared)."""
    return " ".join(re.sub(r"[^\w\s]", " ", _TASHKEEL.sub("", text)).lower().split())


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, plain(a), plain(b)).ratio()


def log(entry: str, usd: float) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps({"id": entry, "usd": round(usd, 4)}) + "\n")


async def fetch(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120) as h:
        r = await h.get(url)
        r.raise_for_status()
        return r.content


async def speak(client: fal_client.AsyncClient, text: str, lang: str, voice: str) -> bytes:
    res = await client.subscribe(
        TTS,
        arguments={
            "text": text,
            "voice": voice,
            "language_code": lang,
            "speed": 0.85,
            "stability": 0.6,
            "similarity_boost": 0.75,
            "apply_text_normalization": "off",
        },
    )
    log(f"tts:{lang}", len(text) * 0.1 / 1000)
    return await fetch(res["audio"]["url"])


async def effect(client: fal_client.AsyncClient, prompt: str, seconds: float) -> bytes:
    res = await client.subscribe(
        SFX,
        arguments={
            "text": prompt,
            "duration_seconds": seconds,
            "prompt_influence": 0.6,
            "output_format": "mp3_44100_128",
        },
    )
    log("sfx", seconds * 0.002)
    return await fetch(res["audio"]["url"])


async def transcribe(client: fal_client.AsyncClient, data: bytes, lang: str) -> str:
    uri = "data:audio/mpeg;base64," + base64.b64encode(data).decode()
    res = await client.subscribe(
        STT, arguments={"audio_url": uri, "task": "transcribe", "language": lang, "chunk_level": "none"}
    )
    log("stt", 0.002)
    return str(res.get("text") or "")


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg  # type: ignore[import-not-found,unused-ignore]

        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError:
        return os.environ.get("FFMPEG", "ffmpeg")


def concat(parts: list[Path], out: Path, gap: float = 0.7) -> None:
    """The parts in order with a short silence between them, as one mp3."""
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(p)]
    n = len(parts)
    pads = "".join(f"[{i}:a]aresample=44100,apad=pad_dur={gap}[a{i}];" for i in range(n))
    chain = pads + "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"
    subprocess.run(
        [
            ffmpeg(),
            "-v",
            "error",
            "-y",
            *inputs,
            "-filter_complex",
            chain,
            "-map",
            "[out]",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "3",
            str(out),
        ],
        check=True,
    )


def duration_ms(path: Path) -> int:
    probe = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe)
    return round((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * 1000) if m else 0


async def one(
    client: fal_client.AsyncClient, item: dict[str, Any], voice: str, sem: asyncio.Semaphore, words: bool
) -> dict[str, Any]:
    code, lang = item["code"], item["lang"]
    out = OUT / f"{code}.mp3"
    async with sem:
        if code in SOUNDS:
            parts: list[Path] = []
            (OUT / "parts").mkdir(parents=True, exist_ok=True)
            for i, (said, sounds) in enumerate(SOUNDS[code]):
                v = OUT / "parts" / f"{code}-{i}-v.mp3"
                v.write_bytes(await speak(client, said, "ar", voice))
                parts.append(v)
                for j, (kind, what, secs) in enumerate(sounds):
                    s = OUT / "parts" / f"{code}-{i}-{j}.mp3"
                    s.write_bytes(
                        await effect(client, what, secs)
                        if kind == "sfx"
                        else await speak(client, what, "ar", voice)
                    )
                    parts.append(s)
            concat(parts, out, gap=0.6)
            return {"code": code, "kind": "sounds", "duration_ms": duration_ms(out)}
        if words:  # each word alone with a pause: clearer for a young child, and checked word by word
            pieces = [w for w in WORDS.split(item["say"]) if w.strip()]
            (OUT / "parts").mkdir(parents=True, exist_ok=True)
            paths = []
            for k, w in enumerate(pieces):
                path = OUT / "parts" / f"{code}-w{k}.mp3"
                path.write_bytes(await speak(client, w, lang, voice))
                paths.append(path)
            concat(paths, out, gap=0.55)
            data = out.read_bytes()
            heard = await transcribe(client, data, lang)
            return {
                "code": code,
                "kind": "words",
                "lang": lang,
                "say": item["say"],
                "heard": heard,
                "similarity": round(similarity(item["say"], heard), 2),
                "duration_ms": duration_ms(out),
            }
        data = await speak(client, item["say"], lang, voice)
        out.write_bytes(data)
        heard = await transcribe(client, data, lang)
        score = similarity(item["say"], heard)
        return {
            "code": code,
            "kind": "speech",
            "lang": lang,
            "say": item["say"],
            "heard": heard,
            "similarity": round(score, 2),
            "duration_ms": duration_ms(out),
        }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--voice", default="Sarah")
    ap.add_argument("--trial", action="store_true", help="two Arabic words items only, to compare voices")
    ap.add_argument("--words", action="store_true", help="speak each word alone with a pause between them")
    a = ap.parse_args()
    os.environ["FAL_KEY"] = fal_key()
    items = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["items"]
    if a.only:
        items = [i for i in items if i["code"] in a.only]
    if a.trial:
        items = [i for i in items if i["code"] in ("mntj2k77", "uoufkitt")]
    OUT.mkdir(parents=True, exist_ok=True)
    client, sem = fal_client.AsyncClient(), asyncio.Semaphore(4)
    results = await asyncio.gather(
        *(one(client, i, a.voice, sem, a.words) for i in items), return_exceptions=True
    )
    report: list[dict[str, Any]] = []
    for item, r in zip(items, results, strict=True):
        if isinstance(r, BaseException):
            report.append({"code": item["code"], "error": f"{type(r).__name__}: {str(r)[:200]}"})
        else:
            report.append(r)
    name = "trial" if a.trial else ("words" if a.words else "report")
    (OUT / f"{name}-{a.voice}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    low = [r for r in report if r.get("similarity", 1) < 0.6 or "error" in r]
    print(f"{len(report)} clips, {len(low)} to listen to")
    for r in report:
        print(r.get("code"), r.get("similarity", r.get("kind")), "|", r.get("heard", r.get("error", ""))[:80])


if __name__ == "__main__":
    asyncio.run(main())
