/**
 * The QR audio page's playback (lib/journeyPlayback.ts): the paces, word by word with pauses, one word on a
 * tap, and the remembered pace: `npm test`.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  DEFAULT_PACE,
  PACE_KEY,
  StepPlayer,
  browserClock,
  paceSettings,
  readPace,
  savePace,
  segmentAt,
  wholeSteps,
  litKeys,
  partCount,
  wordStep,
  type Clock,
  type Media,
  type PlayState,
  type WordTimes,
} from "./journeyPlayback.ts";

// «كُرَة. قِطَّة. شَمْس.» with the shown words in order, and «A. Apple.» showing «A a Apple».
const WORDS: WordTimes = {
  segments: [
    [0, 500],
    [900, 1500],
    [1700, 2300],
  ],
  show: [0, 1, 2],
};
const LETTER: WordTimes = {
  segments: [
    [0, 600],
    [1100, 1900],
  ],
  show: [0, 0, 1],
};

describe("paces", () => {
  it("never slows the voice below 0.9 and keeps the pauses longer in English", () => {
    for (const lang of ["ar", "en"] as const) {
      for (const pace of ["natural", "steady", "slow"] as const) {
        assert.ok(paceSettings(pace, lang).rate >= 0.9, `${pace} ${lang}`);
      }
      assert.equal(paceSettings("natural", lang).rate, 1);
      assert.equal(paceSettings("steady", lang).rate, 1);
      assert.ok(paceSettings("slow", lang).rate < 1);
      assert.ok(paceSettings("slow", lang).pause > paceSettings("steady", lang).pause);
    }
    assert.ok(paceSettings("steady", "ar").pause >= 1000);
    assert.ok(paceSettings("steady", "en").pause > paceSettings("steady", "ar").pause);
    assert.ok(paceSettings("slow", "ar").pause >= 1500 && paceSettings("slow", "en").pause <= 2000);
    assert.equal(DEFAULT_PACE, "steady");
  });

  it("plays the whole item word by word with a pause after every word but the last", () => {
    const steps = wholeSteps(WORDS, "steady", "ar");
    assert.deepEqual(
      steps.map((s) => [s.segment, s.start, s.end, s.pauseAfter, s.rate]),
      [
        [0, 0, 500, 1000, 1],
        [1, 900, 1500, 1000, 1],
        [2, 1700, 2300, 0, 1],
      ],
    );
    assert.ok(wholeSteps(WORDS, "slow", "en").every((s) => s.rate === 0.9));
  });

  it("plays the clip as recorded at the natural pace or without word times", () => {
    assert.deepEqual(wholeSteps(WORDS, "natural", "ar"), []);
    assert.deepEqual(wholeSteps(null, "steady", "ar"), []);
    assert.deepEqual(wholeSteps({ segments: [], show: [] }, "slow", "en"), []);
  });

  it("plays only the tapped word's piece, the letter's name for a letter shown twice", () => {
    assert.deepEqual(wordStep(WORDS, 1, "steady", "ar"), { segment: 1, start: 900, end: 1500, rate: 1, pauseAfter: 0 });
    assert.equal(wordStep(LETTER, 1, "slow", "en")?.segment, 0); // «a» is said as «A»
    assert.equal(wordStep(LETTER, 1, "slow", "en")?.rate, 0.9);
    assert.equal(wordStep(LETTER, 2, "natural", "en")?.start, 1100);
    assert.equal(wordStep({ segments: [[0, 400]], show: [null] }, 0, "steady", "ar"), null); // no piece: no sound
    assert.equal(wordStep(null, 0, "steady", "ar"), null);
    assert.equal(wordStep(WORDS, 9, "steady", "ar"), null);
  });

  it("plays one letter of an entry the clip says letter by letter («أ ب ت»)", () => {
    const abc: WordTimes = {
      segments: [
        [0, 700],
        [1300, 2000],
        [2600, 3300],
      ],
      show: [[0, null, 2]],
    };
    assert.equal(partCount(abc, 0), 3);
    assert.equal(partCount(WORDS, 0), 0);
    assert.equal(wordStep(abc, 0, "steady", "ar", 2)?.start, 2600);
    assert.equal(wordStep(abc, 0, "steady", "ar", 1), null); // «ت» was not heard back: no tap
    assert.equal(wordStep(abc, 0, "steady", "ar"), null); // the whole entry is no single piece
    assert.deepEqual(litKeys(abc, 2), ["0.2"]);
  });

  it("lights up the words of the piece that plays", () => {
    assert.deepEqual(litKeys(LETTER, 0), ["0", "1"]);
    assert.deepEqual(litKeys(LETTER, null), []);
    assert.equal(segmentAt(WORDS, 1000), 1);
    assert.equal(segmentAt(WORDS, 600), null); // between two words
    assert.equal(segmentAt(null, 10), null);
  });
});

describe("the remembered pace", () => {
  const memory = () => {
    const data = new Map<string, string>();
    return { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v) };
  };

  it("keeps the device's choice and falls back to the default", () => {
    const store = memory();
    assert.equal(readPace(store), "steady");
    savePace(store, "slow");
    assert.equal(store.getItem(PACE_KEY), "slow");
    assert.equal(readPace(store), "slow");
    store.setItem(PACE_KEY, "warp");
    assert.equal(readPace(store), "steady");
  });

  it("works when storage is blocked", () => {
    const blocked = {
      getItem: () => {
        throw new Error("SecurityError");
      },
      setItem: () => {
        throw new Error("SecurityError");
      },
    };
    assert.equal(readPace(blocked), "steady");
    assert.doesNotThrow(() => savePace(blocked, "slow"));
    assert.equal(readPace(null), "steady");
  });
});

/** An <audio> whose time moves only when the test says so, and a clock the test drives. */
function rig() {
  const log: string[] = [];
  const media = {
    currentTime: 0,
    playbackRate: 1,
    preservesPitch: false,
    ended: false as boolean,
    paused: true,
    play() {
      this.paused = false;
      log.push(`play@${Math.round(this.currentTime * 1000)}x${this.playbackRate}`);
      return Promise.resolve();
    },
    pause() {
      this.paused = true;
    },
  } satisfies Media & { paused: boolean };
  let frame: (() => void) | null = null;
  let timer: { ms: number; fn: () => void } | null = null;
  const clock: Clock = {
    every(fn) {
      frame = fn;
      return () => {
        if (frame === fn) frame = null;
      };
    },
    after(ms, fn) {
      const t = { ms, fn };
      timer = t;
      return () => {
        if (timer === t) timer = null;
      };
    },
  };
  const states: PlayState[] = [];
  const player = new StepPlayer(media, clock, (s) => states.push(s));
  /** The audio reaches `ms`; a frame runs. */
  const reach = (ms: number) => {
    media.currentTime = ms / 1000;
    frame?.();
  };
  /** The pause between two words ends. */
  const wait = () => {
    const t = timer;
    assert.ok(t, "a pause is running");
    timer = null;
    log.push(`pause ${t.ms}`);
    t.fn();
  };
  return { media, player, states, log, reach, wait, pending: () => timer };
}

describe("playing pieces of the clip", () => {
  it("plays each piece, stops at its end, pauses, then plays the next one", () => {
    const r = rig();
    r.player.play(wholeSteps(WORDS, "slow", "ar"));
    assert.ok(r.media.preservesPitch && r.media.playbackRate === 0.9);
    r.reach(300);
    assert.equal(r.media.paused, false); // still inside the first word
    r.reach(500);
    assert.equal(r.media.paused, true); // the first word is over: silence
    r.wait();
    r.reach(1500);
    r.wait();
    r.reach(2300);
    assert.equal(r.pending(), null);
    assert.deepEqual(r.log, ["play@0x0.9", "pause 1700", "play@900x0.9", "pause 1700", "play@1700x0.9"]);
    assert.deepEqual(
      r.states.map((s) => s.segment),
      [0, null, 1, null, 2, null],
    );
    assert.equal(r.states.at(-1)?.playing, false);
    assert.equal(r.player.playing, false);
  });

  it("plays one word and stops, and a new tap cuts the word before it", () => {
    const r = rig();
    const one = wordStep(WORDS, 2, "steady", "ar");
    assert.ok(one);
    r.player.play([one]);
    assert.equal(r.media.currentTime, 1.7);
    r.reach(1900);
    const other = wordStep(WORDS, 0, "steady", "ar");
    assert.ok(other);
    r.player.play([other]); // tapped another word mid-way
    assert.equal(r.media.currentTime, 0);
    r.reach(2300); // the old word's end means nothing now…
    assert.equal(r.player.playing, false); // …but 2300 is past this word's end too: it stops
    assert.deepEqual(r.log, ["play@1700x1", "play@0x1"]);
  });

  it("stops at once, pause included, and says so", () => {
    const r = rig();
    r.player.play(wholeSteps(WORDS, "steady", "en"));
    r.reach(500);
    assert.ok(r.pending()); // in the pause between two words
    r.player.stop();
    assert.equal(r.pending(), null);
    assert.equal(r.media.paused, true);
    assert.deepEqual(r.states.at(-1), { playing: false, segment: null });
  });

  it("stops at the end of the clip even when the last piece runs to it", () => {
    const r = rig();
    r.player.play(wholeSteps(LETTER, "steady", "en"));
    r.reach(600);
    r.wait();
    r.media.ended = true;
    r.reach(1850);
    assert.equal(r.player.playing, false);
  });
});

describe("the browser clock", () => {
  it("never runs another frame once the loop stopped itself", () => {
    const frames: (() => void)[] = [];
    const g = globalThis as unknown as Record<string, unknown>;
    g.requestAnimationFrame = (cb: () => void) => frames.push(cb);
    g.cancelAnimationFrame = () => {};
    let calls = 0;
    let stop = () => {};
    stop = browserClock.every(() => {
      calls++;
      if (calls === 2) stop(); // a piece ended: the player stops the loop from inside it
    });
    for (let i = 0; i < 5 && frames.length > 0; i++) frames.shift()?.();
    assert.equal(calls, 2);
    assert.equal(frames.length, 0);
    delete g.requestAnimationFrame;
    delete g.cancelAnimationFrame;
  });
});
