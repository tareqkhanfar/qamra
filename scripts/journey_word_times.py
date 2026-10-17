"""Where each word sits in the QR clips of «رحلتي الأولى للتعلّم»: content/journey/clips/words.json.

    uv run --with faster-whisper --with imageio-ffmpeg python scripts/journey_word_times.py [--only CODE ...]

Run once, offline, after the clips change (no paid call: the check is a local Whisper). For every shipped clip
(content/journey/clips/<code>.mp3) it finds the spoken pieces of the item's script, in order: the script's
words and short phrases between its punctuation («كُرَة. قِطَّة. شَمْس.» → 3), or, for the sound items, each
announcement and each sound effect (`SOUNDS` in scripts/journey_voices.py). The cuts are the clip's pauses
(the quiet stretches between the pieces); a clip whose pieces run together has no cuts and plays whole.
A sound item is cut where scripts/journey_voices.py joined its parts (out/journey-audio/parts), since a sound
effect has quiet stretches of its own (slow drum beats); without its parts it plays whole.

Every spoken piece is heard back by Whisper (large-v3-turbo, on this machine): first in the whole clip, then,
for a piece missed there or heard as a neighbour, alone. A piece passes when what was heard matches its text
without the tashkeel (an English letter by its name: «C» is heard «see») and not clearly another piece of the
clip. A clip passes when at most one piece is heard as another piece (two or more mean a shifted cut) and at
least 70 % of its pieces pass (a two-piece clip: one); single syllables such as «تُ» are often not heard at
all and stay in the word-by-word playback. A shown word is offered on a tap only when its own piece passed;
a shown word said only inside a longer piece («كلمة شَمْس») gets that piece split at its own pauses, when every
part is heard back alone.

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
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from journey_voices import OUT, SOUNDS, ffmpeg, plain

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "content/journey/audio.yaml"
CLIPS = ROOT / "content/journey/clips"
REPORT = OUT / "word-times.json"
SR = 16000
FRAME = 0.01  # seconds per loudness frame
QUIET_DB = -40.0  # below the clip's loudest frame: a pause
MIN_CUT = 0.15  # the shortest pause that may separate two pieces (s)
PAD = 0.12  # each piece keeps up to this much of the pause around it (s)
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


def padded(out: list[tuple[float, float]], length: float) -> list[tuple[float, float]]:
    """Each piece with up to PAD of the pause on each side (never more than half the pause)."""
    res = []
    for k, (s, e) in enumerate(out):
        before = s - (out[k - 1][1] if k else 0.0)
        after = (out[k + 1][0] if k + 1 < len(out) else length) - e
        res.append((max(0.0, s - min(PAD, before / 2)), min(length, e + min(PAD, after / 2))))
    return res


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
    return padded(out, length)


def part_cut(ps: list[Piece], x: np.ndarray) -> list[tuple[float, float]] | None:
    """A sound item cut where its parts were joined (scripts/journey_voices.py `concat`), each piece trimmed
    to its loud stretch. None without the parts, or when they don't add up to the clip."""
    files = []
    for p in ps:
        path = OUT / "parts" / f"{p.part}.mp3"
        if not path.exists() and p.part.endswith("-0"):
            path = OUT / "parts" / f"{p.part[:-2]}-s.mp3"  # the first runs named a group's only sound «-s»
        if not path.exists():
            return None
        files.append(path)
    lengths = [len(pcm(f)) / SR for f in files]
    length = len(x) / SR
    gap = (length - sum(lengths)) / len(lengths)  # concat pads every part with the same silence
    if not 0.3 <= gap <= 1.2:
        return None
    peak = float(frame_rms(x).max())
    out, t = [], 0.0
    for d in lengths:
        a, b = int(t * SR), int((t + d) * SR)
        loud = islands(x[a:b], peak)
        out.append((t + loud[0][0], t + loud[-1][1]) if loud else (t, t + d))
        t += d + gap
    return padded(out, length)


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


def main() -> None:
    from faster_whisper import WhisperModel  # local, free; installed by `uv run --with faster-whisper`

    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--model", default="large-v3-turbo")
    a = ap.parse_args()
    items = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["items"]
    durations: dict[str, int] = json.loads((CLIPS / "durations.json").read_text(encoding="utf-8"))
    target = CLIPS / "words.json"
    data: dict[str, Any] = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    times: dict[str, Any] = data.get("items", {})
    old = json.loads(REPORT.read_text(encoding="utf-8")) if a.only and REPORT.exists() else []
    report: list[dict[str, Any]] = [r for r in old if r["code"] not in a.only]
    model = WhisperModel(a.model, device="cpu", compute_type="int8")

    def listen(audio: np.ndarray, lang: str) -> list[tuple[str, float, float]]:
        segs, _ = model.transcribe(audio, language=lang, word_timestamps=True, beam_size=5, vad_filter=False)
        return [(w.word, w.start, w.end) for s in segs for w in (s.words or [])]

    def alone(x: np.ndarray, lang: str, s: float, e: float) -> str:
        """What Whisper hears in a stretch of a clip played on its own."""
        quiet = np.zeros(int(0.3 * SR), dtype=np.float32)
        cut_out = np.concatenate([quiet, x[int(s * SR) : int(e * SR)], quiet])
        return " ".join(w for w, *_ in listen(cut_out, lang)).strip()

    for item in items:
        code, lang = str(item["code"]), str(item["lang"])
        path = CLIPS / f"{code}.mp3"
        if (a.only and code not in a.only) or not path.exists():
            continue
        x = pcm(path)
        ps = pieces(item)
        spans = part_cut(ps, x) if code in SOUNDS else cut(islands(x), len(ps), len(x) / SR)
        times.pop(code, None)
        if spans is None:
            report.append({"code": code, "result": "whole", "why": "no clean cut between the pieces"})
            print(code, "whole (no clean cut)", flush=True)
            continue
        words = listen(x, lang)
        rows: list[dict[str, Any]] = []
        for p, (s, e) in zip(ps, spans, strict=True):
            heard = "" if p.sound else heard_in(words, s, e)
            if not p.sound and (heard_as(p.text, heard) < PASS or elsewhere(ps, p.text, heard)):
                # missed in the whole clip, or heard as a neighbour (Whisper's times spread): hear it alone
                heard = alone(x, lang, s, e) or heard
            rows.append(row(p, s, e, heard))
        # A shown word said only inside a longer piece («كلمة شَمْس»): split that piece at its own pauses
        # when every part is heard back alone.
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
            inner = cut(islands(x[int(s * SR) : int(e * SR)], peak), len(tokens), e - s)
            if inner is None:
                continue
            parts = [(s + a, s + b) for a, b in inner]
            heard_parts = [alone(x, lang, a, b) for a, b in parts]
            if all(heard_as(t, h) >= PASS for t, h in zip(tokens, heard_parts, strict=True)):
                ps[k : k + 1] = [Piece(t) for t in tokens]
                spans[k : k + 1] = parts
                rows[k : k + 1] = [
                    row(Piece(t), a, b, h) for t, (a, b), h in zip(tokens, parts, heard_parts, strict=True)
                ]
        # A piece heard as another piece of the clip, clearly better than as itself: not offered on a tap.
        # Two or more such pieces mean a shifted cut (one alone is Whisper mixing up «قاف» and «كاف»).
        confused = [not p.sound and elsewhere(ps, p.text, r["heard"]) for p, r in zip(ps, rows, strict=True)]
        shifted = [r["text"] for r, c in zip(rows, confused, strict=True) if c]
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        ok = [
            p.sound or (r["score"] >= PASS and not c) or ACCEPTED.get((code, p.text)) == sha
            for p, r, c in zip(ps, rows, confused, strict=True)
        ]
        show = show_map(item, ps, ok)
        speech = [o for p, o in zip(ps, ok, strict=True) if not p.sound]
        # Most pieces heard; a two-piece clip («R. Rabbit.») is anchored by one heard piece.
        mostly = sum(speech) >= (1 if len(speech) <= 2 else MOSTLY * len(speech))
        # Shown words that a piece of the clip says but that piece was not heard: not offered on a tap.
        missing = untappable(item, ps, show)
        passed = len(shifted) < 2 and mostly
        why = "; ".join(
            ([f"heard as another piece: {shifted}"] if shifted else [])
            + ([f"only {sum(speech)}/{len(speech)} pieces heard"] if not mostly else [])
            + ([f"shown words not tappable: {missing}"] if missing else [])
        )
        report.append(
            {
                "code": code,
                "result": "words" if passed else "failed",
                "why": why,
                "pieces": rows,
                "show": show,
            }
        )
        print(
            code,
            ("ok " + why) if passed else f"FAILED ({why})",
            tappable(show),
            "tappable",
            flush=True,
        )
        if passed:
            times[code] = {
                "sha256": sha,
                "duration_ms": durations.get(code, round(len(x) / SR * 1000)),
                "segments": [r["ms"] for r in rows],
                "show": show,
            }
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
