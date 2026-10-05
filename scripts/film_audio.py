"""The brand films' soundtrack: one music bed, two sound effects and a short Arabic voiceover, mixed per film.

    uv run python scripts/film_audio.py generate [--force KEY ...] [--dry-run]  # missing sounds (fal, paid)
    uv run python scripts/film_audio.py hero                  # the home film with sound (apps/web/public)
    uv run python scripts/film_audio.py mux FILM VIDEO OUT [--music-only]  # any video, by its cue sheet
    uv run python scripts/film_audio.py check FILE ... [--wave PNG]         # stream lengths + loudness

The design, the voice lines and the cue sheets are in content/marketing/film-audio/soundtrack.yaml; the sounds
it made are kept next to it (bed.m4a, sparkle.mp3, page-turn.mp3, voice/<line>.mp3), so builds cost nothing.
`generate` makes only what is missing or whose words changed: the bed with Google Lyria 2, the effects with
ElevenLabs sound effects, the lines with ElevenLabs Multilingual v2 (all through fal, all for commercial use).
Every new line is transcribed back (ElevenLabs Scribe) and compared with its words (voice/lines.json). Spend
goes to the fal ledger (out/design-images/ledger.jsonl). The key comes from FAL_KEY or .env, never printed.

Mixing (numpy, then ffmpeg): the voice on top (−6 dB), the bed at −12 dB alone and −18 dB under a line (all
on one loudness scale; it dips just before each line and comes back after it), a sparkle when the moon or the
magic appears, a page-turn whoosh on each scene change; the music fades in and out; the whole film is set to
−14 LUFS with a true peak under −1.5 dB; AAC 48 kHz stereo (Opus in WebM). Each film also has a music-only
version (no voice).
"""

from __future__ import annotations

import argparse
import asyncio
import difflib
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "content/marketing/film-audio"
SPEC = HERE / "soundtrack.yaml"
VOICE = HERE / "voice"
LINES_JSON = VOICE / "lines.json"
LEDGER = ROOT / "out/design-images/ledger.jsonl"
FILM = ROOT / "out/video"
PUBLIC = ROOT / "apps/web/public/photos"
SR = 48000
STT = "fal-ai/elevenlabs/speech-to-text"
PRICE = {"bed": 0.10, "sfx_second": 0.002, "tts_char": 0.0001, "stt_minute": 0.03}
_TASHKEEL = re.compile(r"[ً-ْٰـ]")

Audio = np.ndarray[Any, np.dtype[np.float32]]


# ---------------------------------------------------------------------------------------------- ffmpeg


def find_ffmpeg(arg: str | None = None) -> str:
    """--ffmpeg, else $FFMPEG, else ffmpeg on PATH, else the binary that ships with imageio-ffmpeg."""
    for cand in (arg, os.environ.get("FFMPEG"), shutil.which("ffmpeg")):
        if cand:
            return cand
    try:
        import imageio_ffmpeg

        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError as exc:
        raise SystemExit("no ffmpeg: pass --ffmpeg PATH or set FFMPEG") from exc


def run(ff: str, *args: str, data: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([ff, "-v", "error", "-y", *args], input=data, capture_output=True, check=True)


def decode(ff: str, path: Path, af: str | None = None) -> Audio:
    """Any audio (or a video's audio) → float32 samples, shape (n, 2), at 48 kHz; `af`: an ffmpeg filter."""
    filt = ["-af", af] if af else []
    raw = run(ff, "-i", str(path), "-vn", *filt, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-").stdout
    out: Audio = np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()
    return out


def write_wav(ff: str, samples: Audio, path: Path, af: str | None = None) -> None:
    filt = ["-af", af] if af else []
    run(
        ff,
        *("-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-"),
        *filt,
        *("-c:a", "pcm_f32le", str(path)),
        data=np.ascontiguousarray(samples, dtype="<f4").tobytes(),
    )


def measure(ff: str, path: Path) -> dict[str, float]:
    """Integrated loudness (LUFS), loudness range (LU) and true peak (dBTP) of a file's audio (EBU R128)."""
    err = subprocess.run(
        [
            ff,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stderr
    summary = err[err.rfind("Summary:") :]

    def num(label: str) -> float:
        m = re.search(rf"{label}:\s+(-?[\d.]+|-inf)", summary)
        return float(m.group(1)) if m and m.group(1) != "-inf" else float("-inf")

    return {"lufs": num("I"), "lra": num("LRA"), "true_peak": num("Peak")}


def loudness(ff: str, samples: Audio) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "x.wav"
        write_wav(ff, samples, path)
        return measure(ff, path)["lufs"]


def stream_seconds(ff: str, path: Path, kind: str) -> float:
    """How long a file's first video ("v") or audio ("a") stream really plays (decoded to the end)."""
    err = subprocess.run(
        [
            ff,
            "-hide_banner",
            "-i",
            str(path),
            "-map",
            f"0:{kind}:0",
            *(["-c", "copy"] if kind == "a" else []),
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stderr
    frames, fps = re.findall(r"frame=\s*(\d+)", err), re.search(r"([\d.]+) fps", err)
    if kind == "v" and frames and fps:  # frames × frame length (the last packet's time leaves out one frame)
        return int(frames[-1]) / float(fps.group(1))
    times = re.findall(r"time=(\d+):(\d+):([\d.]+)", err)
    if not times:
        return 0.0
    h, m, s = times[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def container_seconds(ff: str, path: Path) -> float:
    err = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not d:
        raise RuntimeError(f"cannot read {path}")
    return int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))


# ---------------------------------------------------------------------------------------------- the spec


def load_spec() -> dict[str, Any]:
    spec: dict[str, Any] = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    return spec


def cue_sheet(spec: dict[str, Any], film: str) -> list[dict[str, Any]]:
    """A film's cues, flattened (sheets reuse each other through YAML anchors)."""
    flat: list[dict[str, Any]] = []

    def walk(items: list[Any]) -> None:
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                flat.append(dict(it))

    if film not in spec["films"]:
        raise KeyError(f"soundtrack.yaml has no cue sheet for {film}")
    walk(spec["films"][film])
    return flat


def signature(spec: dict[str, Any], say: str) -> str:
    voice = json.dumps(spec["voice"], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(f"{voice}\n{say}".encode()).hexdigest()[:16]


def plain(text: str) -> str:
    """Letters only: no tashkeel, punctuation or case, single spaces (how a transcript is compared)."""
    return " ".join(re.sub(r"[^\w\s]", " ", _TASHKEEL.sub("", text)).lower().split())


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, plain(a), plain(b)).ratio()


# ---------------------------------------------------------------------------------------------- generate


def fal_key() -> str:
    key = os.environ.get("FAL_KEY", "")
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("FAL_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        sys.exit("FAL_KEY is not set")
    return key


def log(entry: str, usd: float) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps({"id": entry, "usd": round(usd, 4)}) + "\n")


def cost(spec: dict[str, Any], key: str) -> float:
    if key == "bed":
        return PRICE["bed"]
    kind, name = key.split(":", 1)
    if kind == "sfx":
        return float(spec["sfx"][name]["seconds"]) * PRICE["sfx_second"]
    return len(spec["lines"][name]["say"]) * PRICE["tts_char"] + 5 / 60 * PRICE["stt_minute"]


def missing(spec: dict[str, Any], force: list[str], only: list[str]) -> list[str]:
    """What `generate` would make: bed, sfx:<name>, line:<id> (missing, forced, or words changed); `only`
    keeps the keys that start with one of its prefixes."""
    todo: list[str] = []
    if "bed" in force or not (HERE / spec["bed"]["file"]).exists():
        todo.append("bed")
    for name, s in spec["sfx"].items():
        if f"sfx:{name}" in force or not (HERE / s["file"]).exists():
            todo.append(f"sfx:{name}")
    state = json.loads(LINES_JSON.read_text(encoding="utf-8")) if LINES_JSON.exists() else {}
    for lid, line in spec["lines"].items():
        fresh = state.get(lid, {}).get("sig") == signature(spec, line["say"])
        if f"line:{lid}" in force or not (VOICE / f"{lid}.mp3").exists() or not fresh:
            todo.append(f"line:{lid}")
    return [k for k in todo if not only or any(k.startswith(p) for p in only)]


async def generate(ff: str, force: list[str], only: list[str], max_usd: float, dry_run: bool) -> int:
    import fal_client
    import httpx

    spec = load_spec()
    todo = missing(spec, force, only)
    usd = sum(cost(spec, k) for k in todo)
    print(f"to make: {', '.join(todo) or 'nothing'}  (about ${usd:.3f})")
    if dry_run or not todo:
        return 0
    if usd > max_usd:
        print(f"that is over --max-usd {max_usd}: nothing made", file=sys.stderr)
        return 1
    os.environ["FAL_KEY"] = fal_key()
    client = fal_client.AsyncClient()

    async def fetch(url: str) -> bytes:
        async with httpx.AsyncClient(timeout=180) as h:
            r = await h.get(url)
            r.raise_for_status()
            return r.content

    if "bed" in todo:
        bed = spec["bed"]
        res = await client.subscribe(
            bed["model"],
            arguments={
                "prompt": bed["prompt"],
                "negative_prompt": bed["negative_prompt"],
                "seed": bed["seed"],
            },
        )
        log("film-audio:bed", PRICE["bed"])
        raw = ROOT / "out/film-audio/bed-raw.wav"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(await fetch(res["audio"]["url"]))
        run(
            ff,
            "-i",
            str(raw),
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-ar",
            str(SR),
            "-ac",
            "2",
            str(HERE / bed["file"]),
        )
        print(f"  bed: {container_seconds(ff, HERE / bed['file']):.1f} s")

    for name, s in spec["sfx"].items():
        if f"sfx:{name}" not in todo:
            continue
        res = await client.subscribe(
            "fal-ai/elevenlabs/sound-effects/v2",
            arguments={
                "text": s["prompt"],
                "duration_seconds": s["seconds"],
                "prompt_influence": 0.6,
                "output_format": "mp3_44100_128",
            },
        )
        log(f"film-audio:sfx:{name}", s["seconds"] * PRICE["sfx_second"])
        (HERE / s["file"]).write_bytes(await fetch(res["audio"]["url"]))
        print(f"  sfx {name}: ok")

    VOICE.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = json.loads(LINES_JSON.read_text(encoding="utf-8")) if LINES_JSON.exists() else {}
    v = spec["voice"]
    sem = asyncio.Semaphore(4)

    async def line(lid: str, say: str) -> None:
        async with sem:
            args = {
                k: v[k] for k in ("voice", "language_code", "speed", "stability", "similarity_boost", "style")
            }
            res = await client.subscribe(
                v["model"], arguments={"text": say, **args, "apply_text_normalization": "off"}
            )
            log(f"film-audio:tts:{lid}", len(say) * PRICE["tts_char"])
            path = VOICE / f"{lid}.mp3"
            path.write_bytes(await fetch(res["audio"]["url"]))
            state[lid] = {
                "sig": signature(spec, say),
                "say": say,
                "seconds": round(container_seconds(ff, path), 2),
            }

    made = [t[5:] for t in todo if t.startswith("line:")]
    await asyncio.gather(*(line(lid, spec["lines"][lid]["say"]) for lid in made))
    if made:
        await verify(ff, client, spec, made, state)
    return 0


async def verify(ff: str, client: Any, spec: dict[str, Any], lids: list[str], state: dict[str, Any]) -> None:
    """Transcribe the lines back with ElevenLabs Scribe (far better at Arabic than Whisper here): one call
    over all of them, 1.5 s of silence apart, split again by the word timings. Writes voice/lines.json."""
    gap = np.zeros((round(1.5 * SR), 2), dtype=np.float32)
    parts: list[Audio] = [gap]
    spans: list[tuple[str, float, float]] = []
    t = len(gap) / SR
    for lid in lids:
        x = trim(decode(ff, VOICE / f"{lid}.mp3"))
        spans.append((lid, t, t + len(x) / SR))
        parts += [x, gap]
        t += (len(x) + len(gap)) / SR
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "lines.mp3"
        samples = np.concatenate(parts)
        run(
            ff,
            *("-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-q:a", "2", str(path)),
            data=samples.tobytes(),
        )
        url = await client.upload(path.read_bytes(), "audio/mpeg")
    res = await client.subscribe(
        STT, arguments={"audio_url": url, "language_code": "ara", "tag_audio_events": False, "diarize": False}
    )
    log("film-audio:stt", round(t / 60 * PRICE["stt_minute"], 4))
    words = [w for w in res.get("words", []) if w.get("type", "word") == "word"]
    for lid, a, b in spans:
        heard = " ".join(w["text"] for w in words if a - 0.3 <= w["start"] <= b + 0.3)
        state.setdefault(lid, {"say": spec["lines"][lid]["say"]})
        state[lid].update(heard=heard, similarity=round(similarity(state[lid]["say"], heard), 2))
        print(f"  {lid}: {state[lid].get('seconds', '?')} s, heard «{heard}» ({state[lid]['similarity']})")
    LINES_JSON.write_text(
        json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    low = [k for k in lids if state[k]["similarity"] < 0.9]
    if low:
        print(f"listen to these (the transcript differs): {', '.join(low)}")


# ---------------------------------------------------------------------------------------------- mixing


def db(x: float) -> float:
    return float(10 ** (x / 20))


def trim(x: Audio, floor_db: float = -42.0) -> Audio:
    """A voice line without the silence around it (30 ms kept before the first word, 120 ms after it)."""
    env = np.convolve(np.abs(x).max(axis=1), np.ones(480) / 480, mode="same")
    loud = np.flatnonzero(env > db(floor_db))
    if not len(loud):
        return x
    a = max(0, loud[0] - int(0.03 * SR))
    b = min(len(x), loud[-1] + int(0.12 * SR))
    out: Audio = x[a:b]
    return out


def tighten(x: Audio, max_pause: float, floor_db: float = -40.0) -> Audio:
    """A voice line with every pause longer than `max_pause` shortened to it (cut inside the silence)."""
    env = np.convolve(np.abs(x).max(axis=1), np.ones(480) / 480, mode="same")
    quiet = np.concatenate([[False], env < db(floor_db), [False]])
    edges = np.flatnonzero(np.diff(quiet.astype(np.int8)))
    keep, at, cap = [], 0, round(max_pause * SR)
    for a, b in zip(edges[::2], edges[1::2], strict=True):
        if b - a > cap:
            keep.append(x[at : a + cap // 2])
            at = b - cap // 2
    keep.append(x[at:])
    out: Audio = np.concatenate(keep).astype(np.float32)
    return out


def steady(x: Audio, window: float, max_db: float) -> Audio:
    """The bed with its loud and quiet passages evened out: a slow gain (a `window`-second moving level, at
    most ±max_db) brings every passage to the bed's typical level; the phrasing inside a passage is kept."""
    power = (x.astype(np.float64) ** 2).mean(axis=1)
    k = round(window * SR / 2)
    c = np.concatenate([[0.0], np.cumsum(power)])
    i = np.arange(len(power))
    a, b = np.clip(i - k, 0, len(power)), np.clip(i + k, 0, len(power))
    level = 10 * np.log10((c[b] - c[a]) / np.maximum(b - a, 1) + 1e-12)
    gain = np.clip(np.median(level) - level, -max_db, max_db)
    out: Audio = (x * (10 ** (gain / 20))[:, None]).astype(np.float32)
    return out


@dataclass
class Sounds:
    """The decoded sounds, each brought to one loudness (mix.reference_lufs); the mix's dB use that scale."""

    bed: Audio
    sfx: dict[str, Audio]
    lines: dict[str, Audio] = field(default_factory=dict)


_CACHE: dict[str, Sounds] = {}


def sounds(ff: str, spec: dict[str, Any]) -> Sounds:
    if "s" in _CACHE:
        return _CACHE["s"]

    ref = spec["mix"]["reference_lufs"]

    def level(x: Audio) -> Audio:
        out: Audio = (x * db(ref - loudness(ff, x))).astype(np.float32)
        return out

    m = spec["mix"]
    bed = level(steady(decode(ff, HERE / spec["bed"]["file"]), m["bed_window"], m["bed_max_db"]))
    sfx = {name: level(trim(decode(ff, HERE / s["file"]), -50)) for name, s in spec["sfx"].items()}
    s = Sounds(bed, sfx)
    tempo = f"atempo={m['voice_tempo']}" if m["voice_tempo"] != 1 else None
    for lid in spec["lines"]:
        path = VOICE / f"{lid}.mp3"
        if path.exists():
            s.lines[lid] = level(tighten(trim(decode(ff, path, tempo)), m["voice_max_pause"]))
    _CACHE["s"] = s
    return s


def bed_for(bed: Audio, n: int, xfade: int = SR * 2) -> Audio:
    """n samples of the bed: from its start, looped with a cross-fade if the film is longer than the bed."""
    out = bed[:n].copy()
    while len(out) < n:
        ramp = np.linspace(0, 1, xfade, dtype=np.float32)[:, None]
        head = out[-xfade:] * (1 - ramp) + bed[:xfade] * ramp
        out = np.concatenate([out[:-xfade], head, bed[xfade:]])
    result: Audio = out[:n]
    return result


@dataclass
class Mix:
    samples: Audio
    warnings: list[str]
    lines: list[tuple[str, float, float]]  # (line id, start, end) in seconds


def mix(ff: str, film: str, seconds: float, starts: list[float] | None = None, voice: bool = True) -> Mix:
    """The film's soundtrack, `seconds` long. `starts`: where each part begins (for cues with `part`)."""
    spec = load_spec()
    m = spec["mix"]
    s = sounds(ff, spec)
    starts = starts or [0.0]
    n = round(seconds * SR)
    out = np.zeros((n, 2), dtype=np.float32)  # music and effects (faded in and out)
    vox = np.zeros((n, 2), dtype=np.float32)  # the voice (never faded)
    duck = np.zeros(n, dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / SR
    warnings: list[str] = []
    placed: list[tuple[str, float, float]] = []

    def put(x: Audio, at: float, gain: float, bus: Audio = out) -> None:
        i = round(at * SR)
        if i >= n:
            return
        j = min(n, i + len(x))
        bus[i:j] += x[: j - i] * gain

    for cue in sorted(cue_sheet(spec, film), key=lambda c: (c.get("part", 0), c["at"])):
        part = cue.get("part", 0)
        if part >= len(starts):
            warnings.append(f"{film}: a cue is for part {part}, the film has {len(starts)}")
            continue
        at = starts[part] + cue["at"]
        if "sfx" in cue:
            put(s.sfx[cue["sfx"]], at, db(cue.get("db", m[f"{cue['sfx']}_db"])))
        elif "line" in cue:
            lid = cue["line"]
            if lid not in s.lines:
                warnings.append(f"{film}: no voice file for «{lid}» (run generate)")
                continue
            x = s.lines[lid]
            end = at + len(x) / SR
            placed.append((lid, at, end))
            if voice:
                put(x, at, db(m["voice_db"]), vox)
            rise = (t - (at - m["duck_attack"])) / m["duck_attack"]
            fall = (end + m["duck_release"] - t) / m["duck_release"]
            duck = np.maximum(duck, np.clip(np.minimum(rise, fall), 0, 1))
    # whoosh on every change of part (the cross-fade starts at the part's start)
    for start in starts[1:]:
        put(s.sfx["whoosh"], max(0.0, start - 0.15), db(m["whoosh_db"]))
    placed.sort(key=lambda p: p[1])
    for (a_id, _, a_end), (b_id, b_start, _) in itertools.pairwise(placed):
        if a_end > b_start - 0.25:
            warnings.append(
                f"{film}: «{a_id}» ends at {a_end:.2f} s, too close to «{b_id}» at {b_start:.2f} s"
            )
    if placed and placed[-1][2] > seconds - 0.35:
        warnings.append(
            f"{film}: «{placed[-1][0]}» ends at {placed[-1][2]:.2f} s, the film at {seconds:.2f} s"
        )

    if not voice:
        duck[:] = 0.0
    gain_db = m["music_alone_db"] + (m["music_under_voice_db"] - m["music_alone_db"]) * duck
    music = bed_for(s.bed, n) * (10 ** (gain_db / 20))[:, None]
    out += music.astype(np.float32)
    fi, fo = round(m["fade_in"] * SR), min(n, round(m["fade_out"] * SR))
    out[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
    out[n - fo :] *= (np.linspace(1, 0, fo, dtype=np.float32) ** 2)[:, None]
    return Mix(out + vox, warnings, placed)


def master(ff: str, x: Audio, path: Path, spec: dict[str, Any], margin: float) -> dict[str, float]:
    """The mix at the target loudness under the true-peak ceiling (gain + limiter, up to 3 passes), as a WAV.
    The limiter stops `margin` dB under the ceiling: room for inter-sample peaks and encoder overshoot."""
    m = spec["mix"]
    ceiling = db(m["true_peak_db"] - margin)
    gain = m["target_lufs"] - loudness(ff, x)
    stats: dict[str, float] = {}
    for _ in range(3):
        af = f"volume={gain:.2f}dB,alimiter=limit={ceiling:.4f}:attack=3:release=60:level=false:latency=true"
        write_wav(ff, x, path, af)
        stats = measure(ff, path)
        if abs(stats["lufs"] - m["target_lufs"]) < 0.3:
            break
        gain += m["target_lufs"] - stats["lufs"]
    return stats


def mux(
    ff: str,
    film: str,
    video: Path,
    out: Path,
    starts: list[float] | None = None,
    voice: bool = True,
) -> dict[str, Any]:
    """`video` with the film's soundtrack → `out` (MP4: AAC; WebM: Opus). The picture is copied as it is."""
    spec = load_spec()
    seconds = container_seconds(ff, video)
    result = mix(ff, film, seconds, starts, voice)
    out.parent.mkdir(parents=True, exist_ok=True)
    webm = out.suffix == ".webm"
    codec = ["-c:a", "libopus", "-b:a", "128k"] if webm else ["-c:a", "aac", "-b:a", "160k"]
    flags = [] if webm else ["-movflags", "+faststart"]
    margin, stats = 1.0, {}
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "mix.wav"
        for _ in range(4):  # the encoder can push a peak over the ceiling: limit lower and encode again
            master(ff, result.samples, wav, spec, margin)
            run(
                ff,
                *("-i", str(video), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy"),
                *codec,
                *("-ar", str(SR), "-ac", "2"),
                *flags,
                str(out),
            )
            stats = measure(ff, out)
            if stats["true_peak"] <= spec["mix"]["true_peak_db"]:
                break
            margin += stats["true_peak"] - spec["mix"]["true_peak_db"] + 0.2
    return {"file": out, "seconds": seconds, **stats, "warnings": result.warnings, "lines": result.lines}


# ---------------------------------------------------------------------------------------------- commands


def hero(ff: str, film: Path, webm: Path, dest: Path) -> list[dict[str, Any]]:
    """The home film (out/video/qamra-film.{mp4,webm}, silent) with sound → <dest>/hero-reading.{mp4,webm};
    the music-only cut goes next to the film (out/video/qamra-film-music.mp4)."""
    results = [
        mux(ff, "hero", film, dest / "hero-reading.mp4"),
        mux(ff, "hero", webm, dest / "hero-reading.webm"),
        mux(ff, "hero", film, film.with_name(f"{film.stem}-music.mp4"), voice=False),
    ]
    return results


def check(ff: str, files: list[Path], wave: Path | None) -> None:
    for f in files:
        v, a = stream_seconds(ff, f, "v"), stream_seconds(ff, f, "a")
        if not a:
            print(f"{f}: NO AUDIO (video {v:.2f} s)")
            continue
        st = measure(ff, f)
        info = subprocess.run([ff, "-hide_banner", "-i", str(f)], capture_output=True, text=True).stderr
        codec = re.search(r"Audio: ([^\n]+)", info)
        print(
            f"{f.relative_to(ROOT) if f.is_relative_to(ROOT) else f}: video {v:.2f} s, audio {a:.2f} s, "
            f"{st['lufs']:.1f} LUFS, LRA {st['lra']:.1f} LU, true peak {st['true_peak']:.1f} dBTP"
            f" | {codec.group(1).strip() if codec else '?'}"
        )
    if wave and files:
        run(
            ff,
            "-i",
            str(files[0]),
            "-filter_complex",
            "[0:a]aformat=channel_layouts=mono,showwavespic=s=1600x360:scale=sqrt:colors=#22306A,"
            "drawgrid=w=iw/20:h=ih:color=#B0B0B0@0.7[w]",
            "-map",
            "[w]",
            "-frames:v",
            "1",
            str(wave),
        )
        print(f"waveform → {wave}")


def report(results: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for r in results:
        f = r["file"]
        name = f.relative_to(ROOT) if f.is_relative_to(ROOT) else f
        print(f"  {name}: {r['seconds']:.2f} s, {r['lufs']:.1f} LUFS, true peak {r['true_peak']:.1f} dBTP")
        warnings += r["warnings"]
    for w in dict.fromkeys(warnings):
        print(f"  warning: {w}")
    return list(dict.fromkeys(warnings))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ffmpeg", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="make the missing sounds on fal (paid)")
    g.add_argument("--force", nargs="*", default=[], help="remake: bed, sfx:<name>, line:<id>")
    g.add_argument("--only", nargs="*", default=[], help="make only these keys (prefixes: bed, sfx, line:…)")
    g.add_argument("--max-usd", type=float, default=0.6)
    g.add_argument("--dry-run", action="store_true")
    h = sub.add_parser("hero", help="the home film with sound")
    h.add_argument("--film", type=Path, default=FILM / "qamra-film.mp4")
    h.add_argument("--webm", type=Path, default=FILM / "qamra-film.webm")
    h.add_argument("--dest", type=Path, default=PUBLIC)
    m = sub.add_parser("mux", help="one video with a cue sheet's soundtrack")
    m.add_argument("film")
    m.add_argument("video", type=Path)
    m.add_argument("out", type=Path)
    m.add_argument("--starts", type=float, nargs="*", default=None, help="start of each part (s)")
    m.add_argument("--music-only", action="store_true")
    c = sub.add_parser("check", help="stream lengths and loudness")
    c.add_argument("files", type=Path, nargs="+")
    c.add_argument("--wave", type=Path, default=None, help="waveform PNG of the first file")
    a = ap.parse_args()
    ff = find_ffmpeg(a.ffmpeg)
    if a.cmd == "generate":
        return asyncio.run(generate(ff, a.force, a.only, a.max_usd, a.dry_run))
    if a.cmd == "hero":
        return 1 if report(hero(ff, a.film, a.webm, a.dest)) else 0
    if a.cmd == "mux":
        return 1 if report([mux(ff, a.film, a.video, a.out, a.starts, not a.music_only)]) else 0
    check(ff, a.files, a.wave)
    return 0


if __name__ == "__main__":
    sys.exit(main())
