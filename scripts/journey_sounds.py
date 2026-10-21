"""The sound pages of «رحلتي الأولى للتعلّم» (the QR items with `tts: false` in content/journey/audio.yaml):
animals, house sounds, loud/quiet, fast/slow, same/different. Each clip is a voice announcing a sound
(«الأَوَّلُ» …) and then the sound itself: one clean sound per piece, nothing over it.

    uv run python scripts/journey_sounds.py generate [--only NAME ...] [--takes 3] [--cap 0.40]
    uv run python scripts/journey_sounds.py pick NAME=TAKE ...        # the take a person or the check chose
    uv run python scripts/journey_sounds.py build [--only CODE ...]   # free: no paid call

`generate` asks ElevenLabs sound effects (fal `fal-ai/elevenlabs/sound-effects/v2`, $0.002 a second,
commercial use) for a few takes of every sound of `LIBRARY`, as uncompressed PCM (no lossy step before the
final mp3), into out/journey-audio/sfx/raw. Each take is trimmed to its one sound (from just before its onset
to the end of its natural decay, at most `Sound.longest` seconds), high-passed at 40 Hz, faded in and out (no
click), and measured: its length, its peak, its noise floor, its spectrum, and whether a second sound hides in
it. The takes chosen by `pick` (out/journey-audio/sfx/picks.json) make the library.

`build` makes each sound item's clip from the shipped announcements (out/journey-audio/parts/<code>-<g>-v.mp3,
the voice of every other clip) and the library: every piece levelled by its loudest moment (EBU R128
momentary loudness: the voice and an ordinary sound at -18 LUFS, a «loud» sound 4 dB above it, a «quiet» one
9 dB below), peak-limited to -2 dBFS (no clipped sample), then laid out with clear silences (after an
announcement `AFTER_VOICE`, between two sounds of one pair `BETWEEN_SOUNDS`, before the next announcement
`BETWEEN_GROUPS`) and encoded once as constant-bitrate mp3 (a browser seeks a CBR mp3 exactly; a VBR one only
roughly). Where each piece sits is written next to the parts (out/journey-audio/parts/<code>.layout.json),
which scripts/journey_word_times.py reads to cut the clip. Fast and slow are the same drum hit or the same
two footsteps at two tempos, so the only difference a child hears is the speed.

The clips land in content/journey/clips/<code>.mp3 with their length in durations.json; then make the word
times again (scripts/journey_word_times.py --only <codes>). The fal key comes from FAL_KEY (or .env); it is
never printed. Every paid call is in the ledger (FAL_LEDGER), and a spent balance stops the run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import journey_voices as jv

ROOT = Path(__file__).resolve().parents[1]
CLIPS = ROOT / "content/journey/clips"
SFX_DIR: Path = jv.OUT / "sfx"
RAW = SFX_DIR / "raw"
PICKS = SFX_DIR / "picks.json"
PARTS: Path = jv.OUT / "parts"
SR = 44100
PRICE = 0.002  # USD a second (fal, 2026-10)


@dataclass(frozen=True)
class Sound:
    prompt: str
    seconds: float  # asked of the model
    longest: float = 2.5  # kept at most (s); a sound still ringing then fades out
    whole: bool = False  # keep every event of the take (a phone's two rings, a doorbell's two notes)
    continuous: bool = False  # running water: soft fades at both ends
    bass: bool = False  # a low sound (drum, footstep): its harmonics added, so a phone speaker plays it


NO_EXTRA = "isolated, close up, dry studio recording, silent background, no music, no voices"
LIBRARY: dict[str, Sound] = {
    "cow": Sound(f"a single cow mooing once, one long moo, {NO_EXTRA}", 2.5),
    "cat": Sound(f"a single house cat meowing once, one clear meow, {NO_EXTRA}", 1.5, longest=1.6),
    "kitten": Sound(f"a small kitten making one soft gentle meow, {NO_EXTRA}", 1.5, longest=1.4),
    "rooster": Sound(f"a single rooster crowing once, cock-a-doodle-doo, {NO_EXTRA}", 3.0, longest=2.6),
    "drum": Sound(
        f"one single hit on a tom-tom drum with a drumstick, punchy, {NO_EXTRA}", 1.5, longest=1.3, bass=True
    ),
    "bell": Sound(f"a small brass hand bell rung twice, bright clear ring, {NO_EXTRA}", 2.0, whole=True),
    "whistle": Sound(f"one short loud blow of a referee whistle, {NO_EXTRA}", 1.2, longest=1.2),
    "doorbell": Sound(f"a house doorbell chime, ding-dong, once, {NO_EXTRA}", 2.0, whole=True),
    "phone": Sound(f"a landline telephone ringing, ring ring, {NO_EXTRA}", 3.0, whole=True),
    "tap": Sound(
        f"water running from a kitchen tap into a sink, steady stream, {NO_EXTRA}",
        3.0,
        longest=2.3,
        whole=True,
        continuous=True,
    ),
    "step": Sound(
        f"one single footstep of a shoe on a wooden floor, {NO_EXTRA}", 1.0, longest=0.35, bass=True
    ),
}
# Rhythms made of one library sound (the second step take alternates with the first): (sound, hits, seconds
# between two hits).
RHYTHMS: dict[str, tuple[str, int, float]] = {
    "drum-3": ("drum", 3, 0.4),  # «طبل»: dum, dum, dum (one hit alone is hard to tell from a knock or a bang)
    "drum-fast": ("drum", 6, 0.25),  # 8 at 0.2 s ran into one rumble
    "drum-slow": ("drum", 3, 0.9),
    "steps-fast": ("step", 8, 0.24),
    "steps-slow": ("step", 4, 0.75),
}

# Loudness of a piece (dB from the voice): the loud/quiet page needs a real difference, every other sound
# stands level with the voice (see `level`).
NORMAL, LOUD, QUIET = 0.0, 4.0, -9.0
VOICE_LUFS = -18.0  # momentary maximum of every announcement and of an ordinary sound
# A phone's small speaker, roughly: nothing under ~500 Hz (two 2nd-order high-passes), little over 8 kHz. The
# announcements measure 6.5 dB quieter through it than in full range; a sound is levelled to match the voice
# there too, but never more than PHONE_HEADROOM dB above the voice in headphones.
PHONE = "highpass=f=500:poles=2,highpass=f=500:poles=2,lowpass=f=8000"
PHONE_DIFF = 6.5
PHONE_HEADROOM = 6.0
MAX_SHAVE = 2.0
LOUD_SHAVE = 4.0
LIMIT = 0.79  # sample peak after the limiter (-2 dBFS): the mp3 never clips
AFTER_VOICE = 0.45  # s of silence after an announcement
BETWEEN_SOUNDS = 0.8  # between the two sounds of a pair (same or different?)
BETWEEN_GROUPS = 1.1  # after a sound, before the next announcement
EDGE = 0.25  # silence at the start and the end of a clip
BITRATE = "96k"  # CBR, mono

# What each sound item's clip says and plays, in order: the announcement, then its sound(s): ("sfx", library
# or rhythm name, loudness from `NORMAL`/`LOUD`/`QUIET`) or ("say", words, 0). The k-th shown word of the item
# is the k-th announced group.
Part = tuple[str, str, float]
SOUNDS: dict[str, list[tuple[str, list[Part]]]] = {
    "ogjmg6ob": [  # مَنْ يُصْدِرُ هَذا الصَّوْتَ؟ بقرة، قطة، ديك
        ("الصَّوْتُ الأَوَّلُ", [("sfx", "cow", NORMAL)]),
        ("الصَّوْتُ الثّاني", [("sfx", "cat", NORMAL)]),
        ("الصَّوْتُ الثّالِثُ", [("sfx", "rooster", NORMAL)]),
    ],
    "dscofnrk": [  # عالٍ أَمْ مُنْخَفِضٌ؟ طبل عالٍ، جرس صغير بهدوء، صفّارة عالية، قطة تموء بهدوء
        ("الأَوَّلُ", [("sfx", "drum-3", LOUD)]),
        ("الثّاني", [("sfx", "bell", QUIET)]),
        ("الثّالِثُ", [("sfx", "whistle", LOUD)]),
        ("الرّابِعُ", [("sfx", "kitten", QUIET)]),
    ],
    "55ahywkt": [  # أَصْواتُ البَيْتِ: جرس الباب، رنين الهاتف، ماء الحنفية
        ("الأَوَّلُ", [("sfx", "doorbell", NORMAL)]),
        ("الثّاني", [("sfx", "phone", NORMAL)]),
        ("الثّالِثُ", [("sfx", "tap", NORMAL)]),
    ],
    "awizj364": [  # سَريعٌ أَمْ بَطيءٌ؟ طبل سريع، طبل بطيء، خطوات سريعة، خطوات بطيئة
        ("الأَوَّلُ", [("sfx", "drum-fast", NORMAL)]),
        ("الثّاني", [("sfx", "drum-slow", NORMAL)]),
        ("الثّالِثُ", [("sfx", "steps-fast", NORMAL)]),
        ("الرّابِعُ", [("sfx", "steps-slow", NORMAL)]),
    ],
    "qzvkwkgg": [  # مُتَشابِهانِ أَمْ مُخْتَلِفانِ؟ ديك/ديك، قطة/بقرة، جرس/جرس، طبل/صفّارة
        ("الأَوَّلُ", [("sfx", "rooster", NORMAL), ("sfx", "rooster", NORMAL)]),
        ("الثّاني", [("sfx", "cat", NORMAL), ("sfx", "cow", NORMAL)]),
        ("الثّالِثُ", [("sfx", "bell", NORMAL), ("sfx", "bell", NORMAL)]),
        ("الرّابِعُ", [("sfx", "drum-3", NORMAL), ("sfx", "whistle", NORMAL)]),
    ],
    "2zzmflqo": [  # ماذا تَعَلَّمْتُ؟ بقرة، طبل عالٍ، كلمة «شَمْس»
        ("الأَوَّلُ", [("sfx", "cow", NORMAL)]),
        ("الثّاني", [("sfx", "drum-3", LOUD)]),
        ("الثّالِثُ", [("say", "شَمْس", NORMAL)]),
    ],
}


# ---- audio helpers --------------------------------------------------------------------------------------


def read(path: Path, highpass: bool = False) -> np.ndarray:
    """Any audio file as mono float32 at 44.1 kHz. A raw take (`highpass`) is also repaired where the
    model's 16-bit output clipped (ffmpeg adeclip rebuilds the flattened peaks, kept above 1.0 in float) and
    high-passed at 40 Hz (no inaudible rumble)."""
    args = [jv.ffmpeg(), "-v", "error", "-i", str(path)]
    if highpass:
        args += ["-af", "aformat=sample_fmts=fltp,adeclip,highpass=f=40:poles=2"]
    raw = subprocess.run(
        [*args, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def write_wav(path: Path, x: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm16 = (np.clip(x, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm16.tobytes())


def frames_db(x: np.ndarray, frame: float = 0.01) -> np.ndarray:
    n = int(SR * frame)
    k = len(x) // n
    if k == 0:
        return np.array([-120.0])
    return 20 * np.log10(np.sqrt(np.mean(x[: k * n].reshape(k, n) ** 2, axis=1)) + 1e-9)


def runs(on: np.ndarray, merge: int) -> list[list[int]]:
    """Stretches of True frames, joined over gaps shorter than `merge` frames."""
    out: list[list[int]] = []
    for i, v in enumerate(on):
        if not v:
            continue
        if out and i - out[-1][1] <= merge:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return out


def momentary_max(x: np.ndarray, tmp: Path, through: str = "") -> float:
    """The loudest EBU R128 momentary loudness (400 ms window) of a sound, in LUFS (ffmpeg ebur128), heard
    directly or `through` a filter (`PHONE`)."""
    pad = np.zeros(int(0.4 * SR), dtype=np.float32)
    write_wav(tmp, np.concatenate([pad, x * 0.5, pad]))  # -6 dB: no sample clips in the 16-bit file
    err = subprocess.run(
        [
            jv.ffmpeg(),
            "-nostats",
            "-i",
            str(tmp),
            "-af",
            (through + "," if through else "") + "ebur128=metadata=1,ametadata=print:key=lavfi.r128.M",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stderr
    values = [float(v) for v in re.findall(r"lavfi\.r128\.M=(-?[\d.]+)", err)]
    tmp.unlink(missing_ok=True)
    if not values:
        raise RuntimeError("ffmpeg ebur128 gave no momentary loudness")
    return max(values) + 6.0206


def phone_bass(x: np.ndarray, tmp: Path) -> np.ndarray:
    """A low sound made audible on a phone speaker, which plays almost nothing under ~400 Hz: the low band's
    harmonics (soft-clipped) mixed back in at 280–2500 Hz, the rumble under 70 Hz cut, and the stick's
    attack lifted at 1.8 kHz. The ear hears the missing fundamental from its harmonics. The take is brought
    to a fixed peak first: how many harmonics the soft clip makes depends on the level it gets."""
    write_wav(tmp, x * (0.45 / float(np.max(np.abs(x)))))
    out = tmp.with_suffix(".bass.wav")
    chain = (
        "asplit[a][b];[b]lowpass=f=300,volume=10,asoftclip=type=tanh,highpass=f=280:poles=2,"
        "highpass=f=280:poles=2,lowpass=f=2500[h];[a]highpass=f=70[l];"
        "[l][h]amix=inputs=2:weights=1 1:normalize=0,equalizer=f=1800:t=q:w=1:g=6"
    )
    subprocess.run(
        [
            jv.ffmpeg(),
            "-v",
            "error",
            "-y",
            "-i",
            str(tmp),
            "-filter_complex",
            chain,
            "-c:a",
            "pcm_f32le",
            str(out),
        ],
        check=True,
    )
    y = read(out)
    tmp.unlink(missing_ok=True)
    out.unlink(missing_ok=True)
    return y


def limit(x: np.ndarray, tmp: Path) -> np.ndarray:
    """Peak-limited to `LIMIT` (ffmpeg alimiter, 3 ms look-ahead), with no level make-up."""
    if float(np.max(np.abs(x))) <= LIMIT:
        return x
    write_wav(tmp, x * 0.5)  # headroom in the 16-bit file; the limiter works on the float signal
    out = tmp.with_suffix(".lim.wav")
    subprocess.run(
        [
            jv.ffmpeg(),
            "-v",
            "error",
            "-y",
            "-i",
            str(tmp),
            "-af",
            f"volume=2.0,alimiter=limit={LIMIT}:attack=3:release=80:level=disabled",
            "-c:a",
            "pcm_f32le",
            str(out),
        ],
        check=True,
    )
    y = read(out)
    tmp.unlink(missing_ok=True)
    out.unlink(missing_ok=True)
    return np.asarray(np.clip(y, -LIMIT, LIMIT), dtype=np.float32)  # the limiter's few overshoot samples


def fade(x: np.ndarray, fade_in: float, fade_out: float) -> np.ndarray:
    y = x.copy()
    a, b = int(fade_in * SR), int(fade_out * SR)
    if a:
        y[:a] *= np.linspace(0.0, 1.0, a) ** 2
    if b:
        y[-b:] *= np.linspace(1.0, 0.0, b) ** 2
    return y


# ---- one take: trimmed to its sound, measured ------------------------------------------------------------


def trim(x: np.ndarray, sound: Sound) -> tuple[np.ndarray, dict[str, Any]]:
    """The take's sound, from just before its onset to the end of its decay (see the module docstring)."""
    db = frames_db(x)
    peak = float(db.max())
    events = runs(db > peak - 30, merge=15)  # events: louder than 30 dB under the take's loudest moment
    energy = [float(np.sum(10 ** (db[a:b] / 10))) for a, b in events]
    main = int(np.argmax(energy))
    first, last = (events[0], events[-1]) if sound.whole else (events[main], events[main])
    start = max(0, first[0] - 2)  # 20 ms before the onset
    end = last[1]
    while end < len(db) and db[end] > peak - 48:  # the natural decay
        end += 1
    longest = int(sound.longest * 100)
    cut_short = end - start > longest
    end = min(end, start + longest)
    y = x[start * 441 : end * 441]
    fade_in = 0.06 if sound.continuous else 0.004
    fade_out = 0.3 if sound.continuous or cut_short else 0.06
    y = fade(y, fade_in, min(fade_out, len(y) / SR / 3))
    # A second sound in the take, outside the kept one, at most 20 dB under it: not a clean single sound.
    others = [
        e for k, e in enumerate(events) if not sound.whole and k != main and db[e[0] : e[1]].max() > peak - 20
    ]
    info = {
        "kept_s": round(len(y) / SR, 2),
        "cut_short": cut_short,
        "other_events": len(others),
        "events_in_kept": len(runs(frames_db(y) > peak - 30, merge=15)),
        "noise_floor_db": round(float(np.percentile(db, 10)) - peak, 1),  # under the loudest moment
    }
    info.update(spectrum(y))
    return y, info


def spectrum(x: np.ndarray) -> dict[str, Any]:
    """Where the sound's energy sits: the share under 150 Hz (a phone speaker plays almost none of it), in
    the voice band, and above 4 kHz; the strongest frequency; flatness (0 = a pure tone, 1 = noise)."""
    n = 4096
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    w = np.hanning(n)
    s = np.zeros(n // 2 + 1)
    for i in range(0, len(x) - n + 1, n // 2):
        s += np.abs(np.fft.rfft(x[i : i + n] * w)) ** 2
    f = np.fft.rfftfreq(n, 1 / SR)
    total = float(s.sum()) + 1e-12

    def share(a: float, b: float) -> float:
        return round(float(s[(f >= a) & (f < b)].sum()) / total, 3)

    band = (f > 60) & (f < 10000)
    flat = float(np.exp(np.mean(np.log(s[band] + 1e-12))) / (np.mean(s[band]) + 1e-12))
    return {
        "below_150hz": share(0, 150),
        "150hz_1k": share(150, 1000),
        "1k_4k": share(1000, 4000),
        "above_4k": share(4000, SR / 2),
        "strongest_hz": round(float(f[band][np.argmax(s[band])])),
        "flatness": round(flat, 3),
    }


def full_scale(path: Path) -> int:
    """Samples of a 16-bit take at full scale on any channel: where the model's output clipped."""
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.int32)
    return int(np.sum(np.abs(x) >= 32767))


def take_path(name: str, k: int) -> Path:
    return RAW / f"{name}-{k}.wav"


def trimmed_path(name: str, k: int) -> Path:
    return SFX_DIR / "takes" / f"{name}-{k}.wav"


def as_wav(data: bytes, path: Path) -> None:
    """fal's PCM answer (a WAV file, or bare 16-bit samples) or an mp3, stored as a WAV file."""
    if data[:4] == b"RIFF":
        path.write_bytes(data)
        return
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        tmp = path.with_suffix(".mp3")
        tmp.write_bytes(data)
        write_wav(path, read(tmp))
        tmp.unlink()
        return
    write_wav(path, np.frombuffer(data[: len(data) // 2 * 2], dtype="<i2").astype(np.float32) / 32768)


# ---- generate / pick / build -----------------------------------------------------------------------------


async def generate(names: list[str], takes: int) -> None:
    import fal_client

    os.environ["FAL_KEY"] = jv.fal_key()
    client = fal_client.AsyncClient()
    RAW.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(4)

    async def one(name: str, k: int) -> None:
        sound = LIBRARY[name]
        path = take_path(name, k)
        if path.exists():
            return
        async with sem:
            jv.budget(sound.seconds * PRICE)
            res = await jv.call(
                client,
                jv.SFX,
                {
                    "text": sound.prompt,
                    "duration_seconds": sound.seconds,
                    "prompt_influence": 0.7,
                    "output_format": "pcm_44100",
                },
            )
            jv.log(f"journey-sfx:{name}-{k}", sound.seconds * PRICE, jv.SFX)
            as_wav(await jv.fetch(res["audio"]["url"]), path)

    results = await asyncio.gather(
        *(one(n, k) for n in names for k in range(1, takes + 1)), return_exceptions=True
    )
    for r in results:
        if isinstance(r, jv.Exhausted):
            print("stopped:", r)
        elif isinstance(r, BaseException):
            print("failed:", type(r).__name__, str(r)[:200])
    print(f"spent this run: ${jv._spent:.4f}")


def measure(names: list[str]) -> dict[str, Any]:
    """Every take of the named sounds, trimmed and measured (out/journey-audio/sfx/takes.json)."""
    report: dict[str, Any] = {}
    for path in sorted(RAW.glob("*.wav")):
        name, _, k = path.stem.rpartition("-")
        if name not in names:
            continue
        x = read(path, highpass=True)
        y, info = trim(x, LIBRARY[name])
        if LIBRARY[name].bass:
            y = phone_bass(y, trimmed_path(name, int(k)).with_suffix(".tmp.wav"))
        write_wav(trimmed_path(name, int(k)), y * (0.9 / float(np.max(np.abs(y)))))  # levelled in `build`
        info["clipped_in_take"] = full_scale(path)
        report[path.stem] = info
    out = SFX_DIR / "takes.json"
    old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    old.update(report)
    out.write_text(json.dumps(old, indent=1), encoding="utf-8")
    return report


def picks() -> dict[str, list[int]]:
    data: dict[str, list[int]] = json.loads(PICKS.read_text(encoding="utf-8")) if PICKS.exists() else {}
    return data


def library_sound(name: str, tmp: Path) -> np.ndarray:
    """A library sound or a rhythm made of one, at the voice's level (before the item's loudness)."""
    chosen = picks()
    if name in RHYTHMS:
        base, hits, every = RHYTHMS[name]
        takes = [read(trimmed_path(base, k)) for k in chosen[base]]
        takes = [t * 10 ** ((VOICE_LUFS - momentary_max(t, tmp)) / 20) for t in takes]
        length = int(((hits - 1) * every) * SR) + max(len(t) for t in takes)
        y = np.zeros(length, dtype=np.float32)
        for h in range(hits):
            t = takes[h % len(takes)]
            at = int(h * every * SR)
            y[at : at + len(t)] += t
        return y
    if name not in chosen:
        sys.exit(f"no take picked for «{name}»: run `generate`, then `pick {name}=N`")
    return read(trimmed_path(name, chosen[name][0]))


def level(x: np.ndarray, offset: float, tmp: Path) -> np.ndarray:
    """At the voice's loudness plus `offset` dB, on a phone speaker as well as on headphones, peak-limited.

    The gain brings the sound's loudness through a phone speaker (`PHONE`) to the voice's there, but keeps
    its full-range loudness between the voice's (plus `offset`) and `PHONE_HEADROOM` dB above it: a low
    sound gets as loud on a phone as it may without booming in headphones, a high one is never quieter than
    the voice in headphones."""
    full, phone = momentary_max(x, tmp), momentary_max(x, tmp, PHONE)
    target = VOICE_LUFS + offset
    on_phone, in_full = target - PHONE_DIFF - phone, target - full
    if offset < 0:  # a «quiet» sound: quiet on a phone too, halfway between the two measures
        gain_db = (on_phone + in_full) / 2
    else:
        gain_db = min(max(on_phone, in_full), target + PHONE_HEADROOM - full)
    # A short hit (a drum, a step) sounds louder than its 400 ms loudness says: the limiter may shave at most
    # MAX_SHAVE dB off its peaks (more would flatten the hit into a thud), a «loud» one LOUD_SHAVE dB.
    shave = LOUD_SHAVE if offset > 0 else MAX_SHAVE
    peak_room = 20 * np.log10(LIMIT / (float(np.max(np.abs(x))) + 1e-9)) + shave
    gain_db = min(gain_db, peak_room)
    return limit((x * 10 ** (gain_db / 20)).astype(np.float32), tmp)


def build(code: str) -> dict[str, Any]:
    tmp = SFX_DIR / "tmp" / f"{code}.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    pieces: list[tuple[np.ndarray, float]] = []  # each piece and the silence after it
    groups = SOUNDS[code]
    for g, (_, sounds) in enumerate(groups):
        voice = read(PARTS / f"{code}-{g}-v.mp3")
        db = frames_db(voice)
        on = np.nonzero(db > db.max() - 50)[0]
        voice = fade(voice[max(0, on[0] - 3) * 441 : (on[-1] + 4) * 441], 0.005, 0.03)
        pieces.append((level(voice, NORMAL, tmp), AFTER_VOICE))
        for j, (kind, what, offset) in enumerate(sounds):
            if kind == "sfx":
                x = library_sound(what, tmp)
            else:  # a word in the same voice (shipped part)
                x = read(PARTS / f"{code}-{g}-{j}.mp3")
                db = frames_db(x)
                on = np.nonzero(db > db.max() - 50)[0]
                x = fade(x[max(0, on[0] - 3) * 441 : (on[-1] + 4) * 441], 0.005, 0.03)
            last = j == len(sounds) - 1
            pieces.append((level(x, offset, tmp), BETWEEN_GROUPS if last else BETWEEN_SOUNDS))
    pieces[-1] = (pieces[-1][0], EDGE)
    t = EDGE
    layout: list[list[int]] = []
    chunks = [np.zeros(int(EDGE * SR), dtype=np.float32)]
    for x, after in pieces:
        layout.append([round(t * 1000), round((t + len(x) / SR) * 1000)])
        chunks += [x, np.zeros(int(after * SR), dtype=np.float32)]
        t += len(x) / SR + int(after * SR) / SR
    clip = np.concatenate(chunks)
    wav = SFX_DIR / "built" / f"{code}.wav"
    write_wav(wav, clip)
    out = CLIPS / f"{code}.mp3"
    subprocess.run(
        [
            jv.ffmpeg(),
            "-v",
            "error",
            "-y",
            "-i",
            str(wav),
            "-ac",
            "1",
            "-ar",
            str(SR),
            "-c:a",
            "libmp3lame",
            "-b:a",
            BITRATE,
            str(out),
        ],
        check=True,
    )
    (PARTS / f"{code}.layout.json").write_text(json.dumps({"pieces_ms": layout}), encoding="utf-8")
    durations_path = CLIPS / "durations.json"
    durations = json.loads(durations_path.read_text(encoding="utf-8"))
    durations[code] = jv.duration_ms(out)
    durations_path.write_text(json.dumps(durations, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    decoded = read(out)
    return {
        "code": code,
        "duration_ms": durations[code],
        "pieces_ms": layout,
        "peak_dbfs": round(20 * float(np.log10(np.max(np.abs(decoded)) + 1e-9)), 1),
        "clipped": int(np.sum(np.abs(decoded) >= 0.999)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--only", nargs="*", default=[])
    g.add_argument("--takes", type=int, default=3)
    g.add_argument("--cap", type=float, default=0.40, help="stop before this run spends more (USD)")
    sub.add_parser("measure")
    p = sub.add_parser("pick")
    p.add_argument("choices", nargs="+", help="NAME=TAKE[,TAKE] (a rhythm alternates its takes)")
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=[])
    a = ap.parse_args()
    if a.cmd == "generate":
        names = a.only or list(LIBRARY)
        jv.CAP_USD = a.cap
        asyncio.run(generate(names, a.takes))
        print(json.dumps(measure(names), indent=1))
    elif a.cmd == "measure":
        print(json.dumps(measure(list(LIBRARY)), indent=1))
    elif a.cmd == "pick":
        chosen = picks()
        for c in a.choices:
            name, _, takes = c.partition("=")
            if name not in LIBRARY:
                sys.exit(f"unknown sound «{name}»")
            chosen[name] = [int(k) for k in takes.split(",")]
        PICKS.parent.mkdir(parents=True, exist_ok=True)
        PICKS.write_text(json.dumps(chosen, indent=1, sort_keys=True), encoding="utf-8")
    else:
        for code in a.only or list(SOUNDS):
            print(json.dumps(build(code)))


if __name__ == "__main__":
    main()
