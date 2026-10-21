"""Where each word sits in the QR clips of «رحلتي الأولى للتعلّم»: content/journey/clips/words.json.

    uv run --with faster-whisper python scripts/journey_word_times.py [--only CODE ...] [--no-bake]
    uv run --with faster-whisper python scripts/journey_word_times.py --audit [--only CODE ...]

Run offline after the clips change (no paid call: the check is a local Whisper). For every shipped clip
(content/journey/clips/<code>.mp3) it finds the spoken pieces of the item's script, in order: the script's
words and short phrases between its punctuation («كُرَة. قِطَّة. شَمْس.» → 3), or, for the sound items, each
announcement and each sound effect (`SOUNDS` in scripts/journey_sounds.py). The cuts are the clip's pauses
(the quiet stretches between the pieces); a clip whose pieces run together has no cuts and plays whole.
A sound item is cut where scripts/journey_sounds.py laid its pieces out (parts/<code>.layout.json), since
a sound effect has quiet stretches of its own (slow drum beats).

Each piece is first widened over its soft edges (a word's first and last sounds are far quieter than its
middle: `refine`), then given PRE before and POST after it, never past the middle of the pause to its
neighbour, each cut moved to the quietest 10 ms there (`place`): a segment runs from silence to silence.
Every segment is then heard alone by Whisper (large-v3-turbo, on this machine), faded at its ends as the
player plays it, and its first and last 20 ms measured: a piece is whole when it is heard as its text
(without the tashkeel; an English letter by its name: «C» is heard «see»), not clearly as another piece of
the clip, and both its ends are silent (EDGE_DB). A piece that isn't gets the whole pause on both sides,
when that is heard whole. A clip passes when no segment cuts into a sound, at most one piece is heard as
another piece (two or more mean a shifted cut) and at least 70 % of its pieces pass (a two-piece clip:
one); single syllables such as «تُ» are often not heard at all and stay in the word-by-word playback. A
shown word is offered on a tap only when its own piece passed; a shown word said only inside a longer piece
(«كلمة شَمْس») gets that piece split at its own pauses, when every part is heard whole.

A clip that passed is then baked (`bake`): silent outside its segments, faded at both ends of each, encoded
once as constant-bitrate mp3, so a browser's seek lands exactly (in a VBR mp3 it lands by the Xing table, up
to a quarter second off: the start of a word lost, or the end of the one before it heard) and no cut can
click. Each piece must still be the same waveform in the baked clip (SAME), or the clip is put back.
`--audit` checks the shipped times as they are and changes nothing (out/journey-audio/word-times-audit.json).

The player at /a/<code> uses the result to play the item word by word with a pause between the words, and to
play one word when the child taps it: `show[i]` is the piece of the clip that says the item's i-th shown word
(null when no passed piece says it alone), or a list with the piece of each part of a shown entry the clip
says part by part («أ ب ت …» → one piece per letter). The file keeps each clip's sha256 and length, so the
server serves the times only with that exact clip. A report for a person lands in
out/journey-audio/word-times.json.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from journey_sounds import SOUNDS
from journey_voices import OUT, duration_ms, ffmpeg, plain

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "content/journey/audio.yaml"
CLIPS = ROOT / "content/journey/clips"
REPORT = OUT / "word-times.json"
AUDIT = OUT / "word-times-audit.json"
BAKE_SR = 44100
BITRATE = "96k"  # the baked clips: constant bitrate, mono
SR = 16000
FRAME = 0.01  # seconds per loudness frame
QUIET_DB = -40.0  # below the clip's loudest frame: a pause
MIN_CUT = 0.15  # the shortest pause that may separate two pieces (s)
PRE = 0.12  # each piece starts up to this much before its first sound (s), never past half the pause
POST = 0.20  # and ends up to this much after its last sound (a word's tail is softer than its onset)
FADE = 0.02  # the baked fade at both ends of every piece (s): no click where the player cuts
SAME = 0.97  # a baked piece must keep this correlation with the clip before
EDGE_DB = -35.0  # a piece's first and last 20 ms must be this far under the clip's loudest frame
PASS = 0.6  # the similarity a heard piece needs
MOSTLY = 0.7  # the share of a clip's spoken pieces that must pass
# Pieces a person accepted although Whisper keeps mishearing them, for one exact clip (its sha256): «Van» was
# heard «van» in its take alone, but «Fun»/«from» inside the clip; it is one clean loud stretch of 0.82 s,
# like the other letter pages' words (0.31–0.76 s, «Yo-yo» 0.76 s), so it is one word (2026-10-17).
ACCEPTED = {("dwrtprom", "Van"): "a6abcd2aadc053c15aacf1af119097a8b65e980da23741748d242029991fcc15"}
PIECES = re.compile(r"\s*[.،,:؛؟?!]\s*")
# A letter shown alone is said by its name in the scripts («أ» → «أَلِف»).
_LETTERS = "أ ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي"
_NAMES = (
    "ألف باء تاء ثاء جيم حاء خاء دال ذال راء زاي سين شين صاد ضاد طاء ظاء عين غين"
    " فاء قاف كاف لام ميم نون هاء واو ياء"
)
LETTER_NAMES = dict(zip(_LETTERS.split(), _NAMES.split(), strict=True))
# How Whisper writes an English letter said alone.
EN_LETTERS: dict[str, set[str]] = {
    "a": {"a", "ay", "eh", "hey"},
    "b": {"b", "be", "bee"},
    "c": {"c", "see", "sea"},
    "d": {"d", "dee"},
    "e": {"e"},
    "f": {"f", "ef", "eff"},
    "g": {"g", "gee"},
    "h": {"h", "aitch", "age"},
    "i": {"i", "eye", "aye"},
    "j": {"j", "jay"},
    "k": {"k", "kay", "okay"},
    "l": {"l", "el", "elle"},
    "m": {"m", "em"},
    "n": {"n", "en"},
    "o": {"o", "oh"},
    "p": {"p", "pee", "pea"},
    "q": {"q", "queue", "cue"},
    "r": {"r", "are", "ar"},
    "s": {"s", "es", "ess"},
    "t": {"t", "tea", "tee"},
    "u": {"u", "you"},
    "v": {"v", "vee"},
    "w": {"w", "double you"},
    "x": {"x", "ex"},
    "y": {"y", "why"},
    "z": {"z", "zed", "zee"},
}


@dataclass
class Piece:
    text: str  # what is said, or the sound effect's prompt
    sound: bool = False  # a sound effect: not speech, never heard back
    group: int = -1  # sound items: which numbered sound («الصوت الأول» …) the piece belongs to
    part: str = ""  # sound items: the part's file in out/journey-audio/parts


def pieces(item: dict[str, Any]) -> list[Piece]:
    """The spoken pieces of an item's clip, in order."""
    code = str(item["code"])
    if code in SOUNDS:
        out: list[Piece] = []
        for g, (said, sounds) in enumerate(SOUNDS[code]):
            out.append(Piece(said, group=g, part=f"{code}-{g}-v"))
            out += [
                Piece(what, sound=kind == "sfx", group=g, part=f"{code}-{g}-{j}")
                for j, (kind, what, _) in enumerate(sounds)
            ]
        return out
    text = str(item["say"]).replace("«", " ").replace("»", " ")
    return [Piece(p.strip()) for p in PIECES.split(text) if p.strip()]


def pcm(path: Path) -> np.ndarray:
    raw = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def frame_rms(x: np.ndarray) -> np.ndarray:
    n = int(SR * FRAME)
    frames = len(x) // n
    return np.sqrt(np.mean(x[: frames * n].reshape(frames, n) ** 2, axis=1) + 1e-12)


def islands(x: np.ndarray, peak: float | None = None) -> list[tuple[float, float]]:
    """The loud stretches of a clip (s), split by every pause of at least 0.1 s; loud = within QUIET_DB of
    the clip's loudest moment (or of `peak`, for a part of a clip)."""
    rms = frame_rms(x)
    if len(rms) == 0:
        return []
    loud = 20 * np.log10(rms / (peak or rms.max())) > QUIET_DB
    runs: list[list[int]] = []
    for i, on in enumerate(loud):
        if on and (not runs or runs[-1][1] != i):
            runs.append([i, i + 1])
        elif on:
            runs[-1][1] = i + 1
    merged: list[list[int]] = []
    for r in runs:
        if merged and (r[0] - merged[-1][1]) * FRAME < 0.1:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(a * FRAME, b * FRAME) for a, b in merged if (b - a) * FRAME >= 0.04]


def frames_db(x: np.ndarray) -> np.ndarray:
    """Each 10 ms frame's level (dB) under the clip's loudest frame."""
    rms = frame_rms(x)
    return 20 * np.log10(rms / (rms.max() if len(rms) else 1.0))


def floor_db(db: np.ndarray) -> float:
    """The clip's background level (dB under its loudest frame); digital silence counts as -90."""
    return float(np.percentile(np.maximum(db, -90.0), 10))


def refine(spans: list[tuple[float, float]], x: np.ndarray) -> list[tuple[float, float]]:
    """Each piece widened over its soft edges: a word's first sound (a hamza, «ث», «ف», «s») and its last
    (a fading vowel) are far quieter than its middle. An edge moves out while the frame beside it is
    clearly above the background (10 dB over it, and within 55 dB of the loudest frame), never into the
    neighbouring piece."""
    db = frames_db(x)
    thr = max(floor_db(db) + 10, -55.0)
    out: list[tuple[float, float]] = []
    for k, (s, e) in enumerate(spans):
        lo = round((out[-1][1] if out else 0.0) / FRAME)
        hi = round((spans[k + 1][0] if k + 1 < len(spans) else len(db) * FRAME) / FRAME)
        i, j = int(s / FRAME), int(np.ceil(e / FRAME))
        while i - 1 >= lo and i - 1 < len(db) and db[i - 1] > thr:
            i -= 1
        while j < min(hi, len(db)) and db[j] > thr:
            j += 1
        out.append((i * FRAME, j * FRAME))
    return out


def place(spans: list[tuple[float, float]], x: np.ndarray) -> list[tuple[float, float]]:
    """The segments the player plays: each piece with PRE before and POST after it, never past the middle
    of the pause to its neighbour, and each cut moved to the quietest 10 ms of the outer half of its margin
    (a cut in silence, not in a sound)."""
    db = frames_db(x)
    length = len(x) / SR
    out = []
    for k, (s, e) in enumerate(spans):
        before = s - spans[k - 1][1] if k else s * 2  # the clip's own start: all of it may be used
        after = spans[k + 1][0] - e if k + 1 < len(spans) else (length - e) * 2
        pre, post = min(PRE, before / 2), min(POST, after / 2)
        out.append((quietest(db, s - pre, s - pre / 2), quietest(db, e + post / 2, e + post)))
    return [(max(0.0, a), min(length, b)) for a, b in out]


def quietest(db: np.ndarray, a: float, b: float) -> float:
    """The start of the quietest frame between a and b (s), or a when the stretch is shorter than a frame."""
    i, j = max(0, int(a / FRAME)), min(len(db), int(b / FRAME))
    if j - i < 1:
        return a
    return float(i + int(np.argmin(db[i:j]))) * FRAME


def edges(x: np.ndarray, s: float, e: float) -> tuple[float, float]:
    """The level (dB under the clip's loudest frame) of a segment's first and last 20 ms."""
    peak = float(frame_rms(x).max())
    n = int(0.02 * SR)

    def lvl(y: np.ndarray) -> float:
        return float(20 * np.log10(np.sqrt(np.mean(y**2) + 1e-12) / peak)) if len(y) else -120.0

    a, b = int(s * SR), int(e * SR)
    return lvl(x[a : a + n]), lvl(x[max(a, b - n) : b])


def cut(spans: list[tuple[float, float]], n: int, length: float) -> list[tuple[float, float]] | None:
    """`n` pieces from the loud stretches: cut at the n-1 longest pauses (None when the clip has too few)."""
    if n == 0 or len(spans) < n:
        return None
    gaps = sorted(range(len(spans) - 1), key=lambda i: spans[i + 1][0] - spans[i][1], reverse=True)[: n - 1]
    if any(spans[i + 1][0] - spans[i][1] < MIN_CUT for i in gaps):
        return None
    out, start = [], 0
    for i in [*sorted(gaps), len(spans) - 1]:
        out.append((spans[start][0], spans[i][1]))
        start = i + 1
    return out


def part_cut(code: str, n: int) -> list[tuple[float, float]] | None:
    """A sound item's pieces where scripts/journey_sounds.py laid them out (parts/<code>.layout.json): exact,
    since a sound effect has quiet stretches of its own (slow drum beats). None without the layout."""
    path = OUT / "parts" / f"{code}.layout.json"
    if not path.exists():
        return None
    ms = json.loads(path.read_text(encoding="utf-8"))["pieces_ms"]
    return [(a / 1000, b / 1000) for a, b in ms] if len(ms) == n else None


def norm(text: str) -> str:
    """Letters only (plain); folded: what Whisper mixes up (hamza seats, «ع»), a final ة/ى said «ا»."""
    t = plain(text)
    t = re.sub("[أإآع]", "ا", t)  # Whisper often writes a lone «ع» as «أ»
    return re.sub("[ةى](?=\\s|$)", "ا", t)


NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


def heard_as(piece: str, heard: str) -> float:
    """How well a heard text matches a piece (1.0 for an English letter heard by its name; Whisper writes
    numbers as digits: «2» is «two»)."""
    p = norm(piece)
    h = norm(re.sub(r"\b(10|[0-9])\b", lambda m: NUMBERS[int(m.group(1))], heard))
    if len(p) == 1 and p in EN_LETTERS:
        return 1.0 if h in EN_LETTERS[p] else 0.0
    return difflib.SequenceMatcher(None, p, h).ratio() if h else 0.0


def elsewhere(ps: list[Piece], text: str, heard: str) -> bool:
    """What was heard in a piece is clearly another piece of the clip (a shifted cut)."""
    own = heard_as(text, heard)
    return bool(heard) and any(
        not q.sound and norm(q.text) != norm(text) and heard_as(q.text, heard) >= max(0.8, own + 0.3)
        for q in ps
    )


def heard_in(words: list[tuple[str, float, float]], s: float, e: float) -> str:
    """What Whisper heard inside a piece (the words whose middle falls in it)."""
    return " ".join(w for w, a, b in words if s <= (a + b) / 2 <= e).strip()


def matches(shown: str, piece: str) -> bool:
    """A shown word is said by this piece: the same letters, or a letter («أ», «A a») by its name."""
    p, s = plain(piece), plain(shown)
    if s == p or LETTER_NAMES.get(s) == p:
        return True
    letters = set(s.split())
    return len(letters) == 1 and len(s.split()[0]) == 1 and s.split()[0] == p  # «A a» → «A»


Shown = int | None | list[int | None]


def show_map(item: dict[str, Any], ps: list[Piece], ok: list[bool]) -> list[Shown]:
    """For each shown word, the index of the piece that says it (a passed piece only). A shown entry made of
    several letters or words that the clip says one by one («أ ب ت …» on the alphabet page) gets a list: the
    piece of each of its space-separated parts."""
    show = [str(w) for w in item["show"]]
    if str(item["code"]) in SOUNDS:  # the k-th shown word is the k-th numbered sound
        groups = sorted({p.group for p in ps})
        if len(show) != len(groups):
            return [None] * len(show)
        mapped: list[Shown] = []
        for g in groups:
            first = min(i for i, p in enumerate(ps) if p.group == g)  # the announcement
            sounds = [i for i, p in enumerate(ps) if p.group == g and i != first]
            mapped.append(sounds[0] if len(sounds) == 1 and ok[sounds[0]] else None)
        return mapped
    used: set[int] = set()

    def find(w: str) -> tuple[bool, int | None]:
        exact = [i for i, p in enumerate(ps) if p.text == w]
        said = exact or [i for i, p in enumerate(ps) if matches(w, p.text)]
        found = [i for i in said if ok[i]]
        pick = next((i for i in found if i not in used), found[0] if found else None)
        if pick is not None:
            used.add(pick)
        return bool(said), pick

    out: list[Shown] = []
    for w in show:
        said, pick = find(w)
        parts = w.split()
        if said or len(parts) < 2:
            out.append(pick)
            continue
        each = [find(part) for part in parts]
        out.append([k for _, k in each] if any(s for s, _ in each) else None)
    return out


def tappable(show: list[Shown]) -> int:
    return sum(sum(k is not None for k in s) if isinstance(s, list) else s is not None for s in show)


def untappable(item: dict[str, Any], ps: list[Piece], show: list[Shown]) -> list[str]:
    """Shown words (or parts of one) that a piece of the clip says, but whose piece was not heard."""
    out = []
    for w, s in zip(item["show"], show, strict=True):
        pairs = list(zip(str(w).split(), s, strict=True)) if isinstance(s, list) else [(str(w), s)]
        out += [t for t, k in pairs if k is None and any(matches(t, p.text) for p in ps if not p.sound)]
    return out


def row(p: Piece, s: float, e: float, heard: str) -> dict[str, Any]:
    score = 1.0 if p.sound else heard_as(p.text, heard)
    return {
        "text": p.text,
        "ms": [round(s * 1000), round(e * 1000)],
        "heard": heard,
        "score": round(score, 2),
    }


def same(x: np.ndarray, y: np.ndarray, s: float, e: float) -> float:
    """How alike two decodes of a clip are inside a segment (correlation, 1.0 = the same waveform), the
    outer FADE at each end left out (baking fades it on purpose)."""
    a, b = int((s + FADE) * SR), int((e - FADE) * SR)
    u, v = x[a:b], y[a : a + len(x[a:b])]
    n = min(len(u), len(v))
    if n == 0:
        return 1.0
    u, v = u[:n], v[:n]
    return float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12))


def pcm44(path: Path) -> np.ndarray:
    raw = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(BAKE_SR), "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def bake(path: Path, spans: list[tuple[float, float]]) -> str:
    """The clip made exactly what the player cuts: silence outside its segments, a FADE at both ends of each
    (a cut never clicks), encoded once as constant-bitrate mp3 (a browser seeks a CBR mp3 exactly; a VBR one
    only roughly, by up to a few hundred ms). Refused when anything audible lies outside the segments (40 dB
    under the loudest moment); skipped when the clip is already so. Returns what happened."""
    x = pcm44(path)
    env = np.zeros(len(x), dtype=np.float32)
    n = int(FADE * BAKE_SR)
    for s, e in spans:
        a, b = int(s * BAKE_SR), min(len(x), int(e * BAKE_SR))
        env[a:b] = 1.0
        k = min(n, (b - a) // 2)
        env[a : a + k] = np.linspace(0.0, 1.0, k)
        env[b - k : b] = np.linspace(1.0, 0.0, k)
    outside = np.abs(x[env == 0])
    peak = float(np.max(np.abs(x)))
    loudest_out = float(outside.max()) if len(outside) else 0.0
    if loudest_out < 1e-4:
        return "already"
    # 10 ms frames outside the segments within 40 dB of the loudest moment: a lone click of a frame or
    # three (a lip noise, a word's last breath) is silenced; anything longer is a sound and stays.
    hop = BAKE_SR // 100
    k = len(x) // hop
    level = np.sqrt(np.mean((x[: k * hop] * (env[: k * hop] == 0)).reshape(k, hop) ** 2, axis=1))
    loud = 20 * np.log10(level / peak + 1e-12) > -40
    longest = max((len(r) for r in "".join("1" if v else "0" for v in loud).split("0")), default=0)
    if longest >= 6:
        return f"refused: a sound of {longest * 10} ms outside the segments"
    wav = OUT / "baked" / f"{path.stem}.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(BAKE_SR)
        w.writeframes((np.clip(x * env, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run(
        [ffmpeg(), "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", BITRATE, str(path)],
        check=True,
    )
    return "baked"


def expected(item: dict[str, Any], n: int) -> list[Piece] | None:
    """The pieces of an item as a words.json entry of `n` segments has them (a piece split at its words
    when a shown word is said only inside it)."""
    ps = pieces(item)
    for w in map(str, item["show"]):
        if len(ps) >= n:
            break
        k = next(
            (
                i
                for i, p in enumerate(ps)
                if not p.sound and len(p.text.split()) > 1 and any(matches(w, t) for t in p.text.split())
            ),
            -1,
        )
        if k >= 0:
            ps[k : k + 1] = [Piece(t) for t in ps[k].text.split()]
    return ps if len(ps) == n else None


def main() -> None:
    from faster_whisper import WhisperModel  # local, free; installed by `uv run --with faster-whisper`

    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument(
        "--audit", action="store_true", help="check the shipped times as they are; change nothing"
    )
    ap.add_argument("--no-bake", action="store_true", help="leave the clips as they are")
    a = ap.parse_args()
    items = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["items"]
    durations: dict[str, int] = json.loads((CLIPS / "durations.json").read_text(encoding="utf-8"))
    target = CLIPS / "words.json"
    data: dict[str, Any] = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    times: dict[str, Any] = data.get("items", {})
    workers = max(1, min(4, (os.cpu_count() or 4) // 3))  # clips heard side by side
    model = WhisperModel(
        a.model,
        device="cpu",
        compute_type="int8",
        cpu_threads=max(1, (os.cpu_count() or 4) // workers),
        num_workers=workers,
    )

    def listen(audio: np.ndarray, lang: str) -> list[tuple[str, float, float]]:
        segs, _ = model.transcribe(audio, language=lang, word_timestamps=True, beam_size=5, vad_filter=False)
        return [(w.word, w.start, w.end) for s in segs for w in (s.words or [])]

    def alone(x: np.ndarray, lang: str, s: float, e: float) -> str:
        """What Whisper hears in a segment played on its own, as the player plays it (faded at both ends)."""
        seg = x[int(s * SR) : int(e * SR)].copy()
        k = min(int(FADE * SR), len(seg) // 2)
        if k:
            seg[:k] *= np.linspace(0.0, 1.0, k)
            seg[-k:] *= np.linspace(1.0, 0.0, k)
        quiet = np.zeros(int(0.3 * SR), dtype=np.float32)
        return " ".join(w for w, *_ in listen(np.concatenate([quiet, seg, quiet]), lang)).strip()

    def judge(
        ps: list[Piece],
        p: Piece,
        x: np.ndarray,
        lang: str,
        s: float,
        e: float,
        core: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        """A segment heard alone and its edges measured: whole = heard as itself, quiet at both ends. A short
        word in a long stretch of silence sets Whisper making words up («kite» heard «Here you go»): then its
        loud core alone (`core`, with 40 ms around it) is heard, and since the segment holds the core and is
        silent at both ends, it holds the whole word."""
        first, last = edges(x, s, e)
        heard = "" if p.sound else alone(x, lang, s, e)
        heard_ok = p.sound or (heard_as(p.text, heard) >= PASS and not elsewhere(ps, p.text, heard))
        if not heard_ok and core:
            inner = alone(x, lang, max(s, core[0] - 0.04), min(e, core[1] + 0.04))
            if heard_as(p.text, inner) >= PASS and not elsewhere(ps, p.text, inner):
                heard, heard_ok = inner, True
        quiet = first <= EDGE_DB and last <= EDGE_DB
        return {
            "heard": heard,
            "ok": bool(heard_ok and quiet),
            "heard_ok": bool(heard_ok),
            "quiet": quiet,
            "edges_db": [round(first), round(last)],
        }

    if a.audit:

        def audit_one(item: dict[str, Any]) -> dict[str, Any] | None:
            code, lang = str(item["code"]), str(item["lang"])
            entry = times.get(code)
            if (a.only and code not in a.only) or not entry:
                return None
            x = pcm(CLIPS / f"{code}.mp3")
            segs = [(s0 / 1000, e0 / 1000) for s0, e0 in entry["segments"]]
            ps = expected(item, len(segs)) or [Piece(f"#{k}") for k in range(len(segs))]
            found_rows: list[dict[str, Any]] = []
            for k, (p, (s, e)) in enumerate(zip(ps, segs, strict=True)):
                loud = islands(x[int(s * SR) : int(e * SR)], float(frame_rms(x).max()))
                core = (s + loud[0][0], s + loud[-1][1]) if loud else None
                j = judge(ps, p, x, lang, s, e, core)
                if not j["ok"] and not p.sound:  # heard whole when given the whole pause around it?
                    gs = (segs[k - 1][1] + s) / 2 if k else 0.0
                    ge = (e + segs[k + 1][0]) / 2 if k + 1 < len(segs) else len(x) / SR
                    j["wider"] = alone(x, lang, gs, ge)
                    j["cut"] = heard_as(p.text, j["wider"]) >= PASS and not j["heard_ok"]
                found_rows.append({"text": p.text, "ms": [round(s * 1000), round(e * 1000)], **j})
            bad = [r for r in found_rows if not r["ok"]]
            issues = "; ".join(
                f"{r['text']}: heard «{r['heard']}» edges {r['edges_db']}" + (" CUT" if r.get("cut") else "")
                for r in bad
            )
            print(code, "ok" if not bad else "ISSUES " + issues, flush=True)
            return {"code": code, "result": "ok" if not bad else "issues", "pieces": found_rows}

        with ThreadPoolExecutor(workers) as pool:
            audit = [r for r in pool.map(audit_one, items) if r]
        if a.only and AUDIT.exists():  # a part of the clips: the others' earlier results stay
            done = {r["code"] for r in audit}
            kept = json.loads(AUDIT.read_text(encoding="utf-8"))
            audit = [r for r in kept if r["code"] not in done] + audit
        AUDIT.parent.mkdir(parents=True, exist_ok=True)
        AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
        good = sum(r["result"] == "ok" for r in audit)
        print(f"{good}/{len(audit)} clips ok; report: {AUDIT.relative_to(ROOT)}")
        return

    old = json.loads(REPORT.read_text(encoding="utf-8")) if a.only and REPORT.exists() else []
    report: list[dict[str, Any]] = [r for r in old if r["code"] not in a.only]
    Result = tuple[dict[str, Any] | None, dict[str, Any] | None, int | None]

    def one(item: dict[str, Any]) -> Result:
        """One clip: its report entry, its times (None: it plays whole), its new length (baked)."""
        code, lang = str(item["code"]), str(item["lang"])
        path = CLIPS / f"{code}.mp3"
        if (a.only and code not in a.only) or not path.exists():
            return None, None, None
        x = pcm(path)
        ps = pieces(item)
        if code in SOUNDS:
            raw = part_cut(code, len(ps))
        else:
            found = cut(islands(x), len(ps), len(x) / SR)
            raw = refine(found, x) if found else None
        if raw is None:
            print(code, "whole (no clean cut)", flush=True)
            return {"code": code, "result": "whole", "why": "no clean cut between the pieces"}, None, None
        spans = place(raw, x)
        rows: list[dict[str, Any]] = []
        widened: list[str] = []
        for k, p in enumerate(ps):
            s, e = spans[k]
            j = judge(ps, p, x, lang, s, e, raw[k])
            if not j["ok"] and not p.sound:
                # Not heard whole, or cut in a sound: the whole pause around it (to the middle of each).
                gs = (raw[k - 1][1] + raw[k][0]) / 2 if k else 0.0
                ge = (raw[k][1] + raw[k + 1][0]) / 2 if k + 1 < len(raw) else len(x) / SR
                wide = judge(ps, p, x, lang, gs, ge)
                if wide["ok"] or (wide["heard_ok"] and not j["heard_ok"]):
                    spans[k], j = (gs, ge), wide
                    widened.append(p.text)
            rows.append({**row(p, *spans[k], j["heard"]), "edges_db": j["edges_db"], "whole": j["ok"]})
        # A piece Whisper can't name alone («حاء» heard «ها») but whose segment is silent at both ends (so
        # nothing of it is cut) counts when the whole clip, heard at once, says it inside that segment.
        unsure = [k for k, (p, r) in enumerate(zip(ps, rows, strict=True)) if not p.sound and not r["whole"]]
        if unsure and all(max(rows[k]["edges_db"]) <= EDGE_DB for k in unsure):
            words = listen(x, lang)
            for k in unsure:
                said = heard_in(words, *spans[k])
                if heard_as(ps[k].text, said) >= PASS and not elsewhere(ps, ps[k].text, said):
                    rows[k] = {
                        **row(ps[k], *spans[k], said),
                        "edges_db": rows[k]["edges_db"],
                        "whole": True,
                        "heard_alone": rows[k]["heard"],
                        "score_alone": rows[k]["score"],
                    }
        # A shown word said only inside a longer piece («كلمة شَمْس»): split that piece at its own pauses
        # when every part is heard back alone, whole.
        peak = float(frame_rms(x).max())
        for w in map(str, item["show"]):
            if code in SOUNDS or any(matches(w, p.text) for p in ps if not p.sound):
                continue
            k = next(
                (i for i, p in enumerate(ps) if not p.sound and any(matches(w, t) for t in p.text.split())),
                -1,
            )
            if k < 0 or len(ps[k].text.split()) < 2:
                continue
            s, e = spans[k]
            tokens = ps[k].text.split()
            sub = x[int(s * SR) : int(e * SR)]
            inner = cut(islands(sub, peak), len(tokens), e - s)
            if inner is None:
                continue
            parts = [(s + a0, s + b0) for a0, b0 in place(refine(inner, sub), sub)]
            judged = [judge(ps, Piece(t), x, lang, a0, b0) for t, (a0, b0) in zip(tokens, parts, strict=True)]
            if all(jj["ok"] for jj in judged):
                ps[k : k + 1] = [Piece(t) for t in tokens]
                spans[k : k + 1] = parts
                rows[k : k + 1] = [
                    {**row(Piece(t), a0, b0, jj["heard"]), "edges_db": jj["edges_db"], "whole": True}
                    for t, (a0, b0), jj in zip(tokens, parts, judged, strict=True)
                ]
        # A piece heard as another piece of the clip, clearly better than as itself: not offered on a tap.
        # Two or more such pieces mean a shifted cut (one alone is Whisper mixing up «قاف» and «كاف»).
        confused = [not p.sound and elsewhere(ps, p.text, r["heard"]) for p, r in zip(ps, rows, strict=True)]
        shifted = [r["text"] for r, c in zip(rows, confused, strict=True) if c]
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        ok = [
            p.sound or (r["score"] >= PASS and not c and r["whole"]) or ACCEPTED.get((code, p.text)) == sha
            for p, r, c in zip(ps, rows, confused, strict=True)
        ]
        show = show_map(item, ps, ok)
        speech = [o for p, o in zip(ps, ok, strict=True) if not p.sound]
        # Most pieces heard; a two-piece clip («R. Rabbit.») is anchored by one heard piece.
        mostly = sum(speech) >= (1 if len(speech) <= 2 else MOSTLY * len(speech))
        # Shown words that a piece of the clip says but that piece was not heard: not offered on a tap.
        missing = untappable(item, ps, show)
        cut_in_sound = [r["text"] for r in rows if max(r["edges_db"]) > EDGE_DB]
        passed = len(shifted) < 2 and mostly and not cut_in_sound
        baked, length = "", durations.get(code, round(len(x) / SR * 1000))
        if passed and not a.no_bake:
            backup = path.read_bytes()
            baked = bake(path, spans)
            if baked == "baked":  # the shipped clip changed: every piece must still be the same sound
                y = pcm(path)
                # Lost: a piece that now cuts into a sound, or whose audio changed beyond the one re-encode
                # (the waveform inside its segment, against the clip before; Whisper alone wavers on the
                # same audio, «تاء» heard «تا» once and «تاء» the next time, so it is not asked again).
                lost = [
                    p.text
                    for p, (s0, e0) in zip(ps, spans, strict=True)
                    if max(edges(y, s0, e0)) > EDGE_DB or same(x, y, s0, e0) < SAME
                ]
                if lost:
                    path.write_bytes(backup)
                    baked = f"undone: {lost} changed in the baked clip"
                else:
                    length = duration_ms(path)
                    sha = hashlib.sha256(path.read_bytes()).hexdigest()
        why = "; ".join(
            ([f"heard as another piece: {shifted}"] if shifted else [])
            + ([f"only {sum(speech)}/{len(speech)} pieces heard"] if not mostly else [])
            + ([f"shown words not tappable: {missing}"] if missing else [])
            + ([f"cut inside a sound: {cut_in_sound}"] if cut_in_sound else [])
            + ([f"widened to the pauses: {widened}"] if widened else [])
            + ([baked] if baked and baked != "already" else [])
        )
        entry = {
            "code": code,
            "result": "words" if passed else "failed",
            "why": why,
            "pieces": rows,
            "show": show,
        }
        print(code, ("ok " + why) if passed else f"FAILED ({why})", tappable(show), "tappable", flush=True)
        if not passed:
            return entry, None, None
        return (
            entry,
            {
                "sha256": sha,
                "duration_ms": length,
                "segments": [[a0, min(b0, length)] for a0, b0 in (r["ms"] for r in rows)],  # inside the clip
                "show": show,
            },
            length if baked == "baked" else None,
        )

    with ThreadPoolExecutor(workers) as pool:
        for item, (entry, timed, length) in zip(items, pool.map(one, items), strict=True):
            if entry is None:
                continue
            code = str(item["code"])
            report.append(entry)
            times.pop(code, None)
            if timed:
                times[code] = timed
            if length:
                durations[code] = length
    (CLIPS / "durations.json").write_text(
        json.dumps(durations, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    order = [str(i["code"]) for i in items]
    out = {
        "about": "scripts/journey_word_times.py: each clip's pieces (ms) and the piece of every shown word",
        "items": {c: times[c] for c in order if c in times},
    }
    text = json.dumps(out, ensure_ascii=False, indent=1)
    flat = re.sub(
        r"\[\s+([-\d,\snul]+?)\s+\]",
        lambda m: "[" + ", ".join(m.group(1).split()).replace(",,", ",") + "]",
        text,
    )
    target.write_text(flat + "\n", encoding="utf-8")  # one line per list of numbers
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out['items'])} clips with word times; report: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
