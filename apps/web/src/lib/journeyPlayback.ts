/**
 * How the QR audio page of «رحلتي الأولى للتعلّم» plays its clip (components/journey/AudioPlayer.tsx).
 *
 * A shipped clip comes with its word times (content/journey/clips/words.json, served by `GET /api/a/{code}`):
 * the clip's spoken pieces in order, and the piece that says each shown word. With them the page plays the
 * item word by word, the voice untouched and a clear pause between the words, and plays one word on a tap.
 * Without them (a person's recording, the narrator) it plays the clip whole, as recorded.
 *
 * Paces: «عادي» `natural` is the clip as recorded; `steady` (the default) plays word by word with about a
 * second between the words (a little more in English); «أبطأ» `slow` leaves longer pauses and reads a little
 * slower (rate 0.9, the pitch kept). The voice is never slowed below 0.9: slower than that smears the words.
 */

export type Lang = "ar" | "en";
export type Pace = "natural" | "steady" | "slow";
export const PACES: readonly Pace[] = ["natural", "steady", "slow"];
export const DEFAULT_PACE: Pace = "steady";

/** The piece that says a shown word (null: none says it alone), or, for a shown entry the clip says part by
 *  part («أ ب ت …»), the piece of each of its space-separated parts. */
export type Shown = number | null | (number | null)[];
/** `segments[k]` = [start_ms, end_ms] of the clip's k-th spoken piece; `show[i]` = the piece(s) of shown word i. */
export type WordTimes = { segments: [number, number][]; show: Shown[] };

/** One piece of the clip to play, then a pause before the next one. */
export type Step = { segment: number; start: number; end: number; rate: number; pauseAfter: number };

type PaceSettings = { rate: number; pause: Record<Lang, number> };
const SETTINGS: Record<Exclude<Pace, "natural">, PaceSettings> = {
  steady: { rate: 1, pause: { ar: 1000, en: 1300 } },
  slow: { rate: 0.9, pause: { ar: 1700, en: 2000 } },
};

/** The rate the voice plays at (never below 0.9) and the pause between two words (ms). */
export function paceSettings(pace: Pace, lang: Lang): { rate: number; pause: number } {
  if (pace === "natural") return { rate: 1, pause: 0 };
  const s = SETTINGS[pace];
  return { rate: s.rate, pause: s.pause[lang] };
}

/** True when the item can be played piece by piece (its times describe at least one piece). */
export function hasTimes(times: WordTimes | null | undefined): times is WordTimes {
  return !!times && times.segments.length > 0;
}

/** The whole item, piece by piece with a pause between the pieces; empty = play the clip as recorded. */
export function wholeSteps(times: WordTimes | null | undefined, pace: Pace, lang: Lang): Step[] {
  if (pace === "natural" || !hasTimes(times)) return [];
  const { rate, pause } = paceSettings(pace, lang);
  return times.segments.map(([start, end], segment, all) => ({
    segment,
    start,
    end,
    rate,
    pauseAfter: segment < all.length - 1 ? pause : 0,
  }));
}

/** The one piece that says shown word `index`, or null when no piece says it alone. */
/** Shown word `index` said part by part: how many parts (0 when it is said whole, or not at all). */
export function partCount(times: WordTimes | null | undefined, index: number): number {
  const s = times?.show[index];
  return Array.isArray(s) ? s.length : 0;
}

/** The one piece that says shown word `index` (or its part `part`), or null when no piece says it alone. */
export function wordStep(
  times: WordTimes | null | undefined,
  index: number,
  pace: Pace,
  lang: Lang,
  part?: number,
): Step | null {
  if (!hasTimes(times)) return null;
  const shown = times.show[index];
  const segment = Array.isArray(shown) ? (part === undefined ? null : shown[part]) : shown;
  if (segment == null || !times.segments[segment]) return null;
  const [start, end] = times.segments[segment];
  return { segment, start, end, rate: paceSettings(pace, lang).rate, pauseAfter: 0 };
}

/** What a piece says on the page, to light it up while it plays: `"i"` for shown word i, `"i.j"` for part j. */
export function litKeys(times: WordTimes | null | undefined, segment: number | null): string[] {
  if (!times || segment == null) return [];
  return times.show.flatMap((s, i) =>
    Array.isArray(s) ? s.flatMap((k, j) => (k === segment ? [`${i}.${j}`] : [])) : s === segment ? [`${i}`] : [],
  );
}

/** The piece playing at `ms` of the clip (to light the words up when the clip plays whole), or null. */
export function segmentAt(times: WordTimes | null | undefined, ms: number): number | null {
  if (!times) return null;
  const k = times.segments.findIndex(([start, end]) => ms >= start && ms < end);
  return k < 0 ? null : k;
}

// ---- the pace each device keeps ------------------------------------------------------------------------

export const PACE_KEY = "qamra.journey.pace";
type Store = Pick<Storage, "getItem" | "setItem">;

/** The pace this device chose before (the default when none, or when storage is blocked). */
export function readPace(store: Store | null | undefined): Pace {
  try {
    const v = store?.getItem(PACE_KEY);
    return PACES.includes(v as Pace) ? (v as Pace) : DEFAULT_PACE;
  } catch {
    return DEFAULT_PACE;
  }
}

export function savePace(store: Store | null | undefined, pace: Pace): void {
  try {
    store?.setItem(PACE_KEY, pace);
  } catch {
    // a private window or blocked storage: the choice lasts until the page closes
  }
}

// ---- playing pieces of one <audio> ---------------------------------------------------------------------

/** What the player needs of an <audio> element (a fake one in the tests). */
export type Media = {
  currentTime: number;
  playbackRate: number;
  preservesPitch?: boolean;
  readonly ended: boolean;
  play(): Promise<void>;
  pause(): void;
};

/** Timers (the browser's in the page, a fake clock in the tests). */
export type Clock = {
  /** Calls `fn` again and again (each frame) until the returned function is called. */
  every(fn: () => void): () => void;
  /** Calls `fn` once after `ms`, unless the returned function is called first. */
  after(ms: number, fn: () => void): () => void;
};

export type PlayState = { playing: boolean; segment: number | null };

export const browserClock: Clock = {
  every(fn) {
    let stopped = false; // `fn` may stop the loop itself: no frame after that
    let id = requestAnimationFrame(function tick() {
      fn();
      if (!stopped) id = requestAnimationFrame(tick);
    });
    return () => {
      stopped = true;
      cancelAnimationFrame(id);
    };
  },
  after(ms, fn) {
    const id = setTimeout(fn, ms);
    return () => clearTimeout(id);
  },
};

/**
 * Plays steps of one <audio>: seeks to a piece, plays it, stops at its end, waits the pause, plays the next.
 * A new `play` or a `stop` cancels what was going on. `onChange` says whether it plays and which piece.
 */
export class StepPlayer {
  private readonly media: Media;
  private readonly clock: Clock;
  private readonly onChange: (state: PlayState) => void;
  private run = 0;
  private active = false;
  private cancel: (() => void) | null = null;

  constructor(media: Media, clock: Clock, onChange: (state: PlayState) => void) {
    this.media = media;
    this.clock = clock;
    this.onChange = onChange;
  }

  get playing(): boolean {
    return this.active;
  }

  play(steps: Step[]): void {
    this.halt();
    if (steps.length === 0) return this.stop();
    const run = ++this.run;
    this.active = true;
    this.next(steps, 0, run);
  }

  /** Stops at once (the pause button, another word, leaving the page). */
  stop(): void {
    const was = this.active;
    this.halt();
    this.run++;
    this.active = false;
    if (was) this.onChange({ playing: false, segment: null });
  }

  private halt(): void {
    this.cancel?.();
    this.cancel = null;
    this.media.pause();
  }

  private next(steps: Step[], i: number, run: number): void {
    if (run !== this.run) return;
    const step = steps[i];
    const m = this.media;
    m.playbackRate = step.rate;
    m.preservesPitch = true; // a slower voice keeps its pitch
    m.currentTime = step.start / 1000;
    this.onChange({ playing: true, segment: step.segment });
    m.play().catch(() => {
      if (run === this.run) this.stop();
    });
    this.cancel = this.clock.every(() => {
      if (run !== this.run || (m.currentTime * 1000 < step.end && !m.ended)) return;
      this.cancel?.();
      this.cancel = null;
      m.pause();
      if (i + 1 >= steps.length) return this.stop();
      this.onChange({ playing: true, segment: null }); // the pause between two words
      this.cancel = this.clock.after(step.pauseAfter, () => this.next(steps, i + 1, run));
    });
  }
}
