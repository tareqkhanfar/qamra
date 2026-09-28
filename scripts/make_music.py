"""Render Qamra's background lullaby (original composition, rendered from code — no samples, no licensing).

Music box melody over soft pads, a gentle bass and a quiet arpeggio, in F major, 3/4 at 66 BPM,
24 bars (A–B–A′). The reverb tail is wrapped into the start so the file loops seamlessly.

  uv run --with soundfile scripts/make_music.py apps/web/public/audio/lullaby.mp3
"""

import sys
from pathlib import Path

import numpy as np

SR = 44100
BPM = 66
BEAT = 60 / BPM
BAR = 3 * BEAT


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


# ---- the score (MIDI note, beats) ------------------------------------------------------------
F, D_m, BB, C, A_m, G_m = (53, 57, 60), (50, 53, 57), (46, 50, 53), (48, 52, 55), (45, 48, 52), (43, 46, 50)
A4, BB4, C5, D5, E5, F5, G4, F4 = 69, 70, 72, 74, 76, 77, 67, 65

SECTION_A = [
    (F, [(A4, 2), (C5, 1)]),
    (D_m, [(D5, 2), (F5, 1)]),
    (BB, [(D5, 1), (C5, 1), (BB4, 1)]),
    (C, [(C5, 3)]),
    (F, [(A4, 2), (C5, 1)]),
    (A_m, [(E5, 2), (C5, 1)]),
    (BB, [(D5, 1), (C5, 1), (BB4, 1)]),
    (F, [(A4, 3)]),
]
SECTION_B = [
    (D_m, [(F5, 2), (E5, 1)]),
    (BB, [(D5, 2), (C5, 1)]),
    (F, [(C5, 1), (A4, 1), (C5, 1)]),
    (C, [(G4, 3)]),
    (D_m, [(A4, 2), (D5, 1)]),
    (G_m, [(D5, 1), (BB4, 1), (G4, 1)]),
    (C, [(E5, 2), (D5, 1)]),
    (C, [(C5, 3)]),
]
SECTION_A2 = [*SECTION_A[:-1], (F, [(F4, 3)])]
SCORE = SECTION_A + SECTION_B + SECTION_A2


# ---- instruments ------------------------------------------------------------------------------
def music_box(freq: float, dur: float, vel: float) -> np.ndarray:
    """Tuned metal tine: inharmonic partials, instant attack, long bell-like decay."""
    n = int(SR * (dur + 2.2))
    t = np.arange(n) / SR
    out = np.zeros(n)
    for ratio, amp, decay in (
        (1.0, 1.0, 1.4),
        (2.0, 0.28, 0.9),
        (2.76, 0.18, 0.55),
        (5.4, 0.07, 0.25),
        (8.93, 0.03, 0.12),
    ):
        out += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t / decay)
    attack = np.minimum(1.0, t / 0.004)
    return vel * out * attack


def pad(freqs: tuple[float, ...], dur: float, vel: float) -> np.ndarray:
    """Soft string-like pad: detuned sines, slow swell and release."""
    n = int(SR * (dur + 1.5))
    t = np.arange(n) / SR
    env = np.clip(t / 0.9, 0, 1) * np.clip((dur + 1.5 - t) / 1.5, 0, 1)
    out = np.zeros(n)
    for f in freqs:
        for detune in (-0.12, 0.0, 0.12):
            out += np.sin(2 * np.pi * (f + detune) * t + detune * 7)
    return vel * out * env / (3 * len(freqs))


def bass(freq: float, dur: float, vel: float) -> np.ndarray:
    n = int(SR * (dur + 0.8))
    t = np.arange(n) / SR
    env = np.minimum(1.0, t / 0.02) * np.exp(-t / 1.6)
    tone: np.ndarray = vel * (np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(4 * np.pi * freq * t)) * env
    return tone


def pluck(freq: float, vel: float) -> np.ndarray:
    n = int(SR * 1.4)
    t = np.arange(n) / SR
    return (
        vel
        * (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(6 * np.pi * freq * t))
        * np.exp(-t / 0.35)
        * np.minimum(1, t / 0.003)
    )


def reverb_ir(seconds: float = 2.8) -> np.ndarray:
    rng = np.random.default_rng(7)
    n = int(SR * seconds)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    kernel = np.ones(24) / 24  # soften the highs
    noise = np.convolve(noise, kernel, mode="same")
    ir = noise * np.exp(-t / (seconds / 5))
    ir[0] = 1.0
    normalized: np.ndarray = ir / np.max(np.abs(ir))
    return normalized


def add(track: np.ndarray, at: float, sound: np.ndarray) -> None:
    i = int(at * SR)
    end = min(len(track), i + len(sound))
    track[i:end] += sound[: end - i]


def render() -> np.ndarray:
    loop_len = len(SCORE) * BAR
    total = loop_len + 6.0  # room for tails, folded back below
    dry = np.zeros(int(total * SR))
    for bar_i, (chord, notes) in enumerate(SCORE):
        start = bar_i * BAR
        add(dry, start, pad(tuple(hz(m + 12) for m in chord), BAR, 0.16))
        add(dry, start, bass(hz(chord[0] - 12), BAR, 0.22))
        for beat, offset in ((1, 12), (2, 19)):  # soft arpeggio on beats 2 and 3
            add(dry, start + beat * BEAT, pluck(hz(chord[beat % 3] + offset), 0.05))
        t = start
        for midi, beats in notes:
            add(dry, t, music_box(hz(midi + 12), beats * BEAT, 0.34))
            t += beats * BEAT
    wet = np.convolve(dry, reverb_ir())[: len(dry)] * 0.022
    mix = dry * 0.8 + wet
    n = int(loop_len * SR)
    loop = mix[:n].copy()
    tail = mix[n:]
    loop[: len(tail)] += tail  # wrap tails into the start: seamless loop
    # gentle high-cut for a warm, bedtime tone
    loop = np.convolve(loop, np.ones(6) / 6, mode="same")
    normalized: np.ndarray = 0.8 * loop / np.max(np.abs(loop))
    return normalized


if __name__ == "__main__":
    import soundfile as sf

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "lullaby.mp3")
    out.parent.mkdir(parents=True, exist_ok=True)
    audio = render()
    sf.write(out, audio, SR, format="MP3", subtype="MPEG_LAYER_III")
    print(f"{out}: {len(audio) / SR:.1f}s, {out.stat().st_size / 1024:.0f} KB")
