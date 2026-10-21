/**
 * The QR audio page's playback (lib/journeyPlayback.ts): the paces, word by word with pauses, one word on a
 * tap, and the remembered pace: `npm test`.
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  DEFAULT_PACE,
  FADE_OUT_MS,
  GAP_MS,
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
  const volumes: number[] = [];
  let volume = 1;
  const media = {
    currentTime: 0,
    playbackRate: 1,
    preservesPitch: false,
    ended: false as boolean,
    paused: true,
    get volume() {
      return volume;
    },
    set volume(v: number) {
      volume = v;
      volumes.push(Math.round(v * 100) / 100);
    },
    play() {
      this.paused = false;
      log.push(`play@${Math.round(this.currentTime * 1000)}x${this.playbackRate}`);
      return Promise.resolve();
    },
    pause() {
      if (!this.paused) log.push(`stop@${Math.round(this.currentTime * 100) * 10}`); // to the 10 ms frame
      this.paused = true;
    },
  } satisfies Media & { paused: boolean };
  let now = 0;
  const frames = new Set<() => void>();
  let timers: { at: number; fn: () => void }[] = [];
  const clock: Clock = {
    now: () => now,
    every(fn) {
      frames.add(fn);
      return () => frames.delete(fn);
    },
    after(ms, fn) {
      const t = { at: now + ms, fn };
      timers.push(t);
      return () => {
        timers = timers.filter((x) => x !== t);
      };
    },
  };
  const frame = () => [...frames].forEach((fn) => frames.has(fn) && fn());
  /** Time passes by `ms` (the audio plays on when it isn't paused): frames run, then due timers. */
  const tick = (ms: number) => {
    now += ms;
    if (!media.paused) media.currentTime += (ms / 1000) * media.playbackRate;
    frame();
    for (const t of timers.filter((x) => x.at <= now)) {
      if (timers.includes(t)) {
        timers = timers.filter((x) => x !== t);
        t.fn();
      }
    }
  };
  /** Plays on until `ms` of audio (or wall time, while paused) has gone by, in 10 ms frames. */
  const run = (ms: number) => {
    for (let i = 0; i < ms / 10; i++) tick(10);
  };
  /** The audio reaches `ms` at once; a frame runs. */
  const reach = (ms: number) => {
    media.currentTime = ms / 1000;
    frame();
  };
  const states: PlayState[] = [];
  const player = new StepPlayer(media, clock, (s) => states.push(s));
  return { media, player, states, log, volumes, run, tick, reach, timers: () => timers, frames: () => frames };
}

describe("playing pieces of the clip", () => {
  it("plays each piece, stops at its end, pauses, then plays the next one", () => {
    const r = rig();
    r.player.play(wholeSteps(WORDS, "slow", "ar"));
    assert.ok(r.media.preservesPitch && r.media.playbackRate === 0.9);
    r.run(300);
    assert.equal(r.media.paused, false); // still inside the first word
    r.run(400);
    assert.equal(r.media.paused, true); // the first word is over: silence
    r.run(5000);
    assert.deepEqual(r.log, ["play@0x0.9", "stop@500", "play@900x0.9", "stop@1500", "play@1700x0.9", "stop@2300"]);
    assert.deepEqual(
      r.states.map((s) => s.segment),
      [0, null, 1, null, 2, null],
    );
    assert.equal(r.states.at(-1)?.playing, false);
    assert.equal(r.player.playing, false);
    assert.deepEqual(r.timers(), []);
    assert.equal(r.frames().size, 0);
  });

  it("never starts a piece before the one before it has stopped, and keeps the pause between them", () => {
    const r = rig();
    const order: string[] = [];
    r.player.play(wholeSteps(WORDS, "steady", "ar"));
    let stoppedAt = -1;
    for (let t = 0; t < 6000; t += 10) {
      const was = r.media.paused;
      r.tick(10);
      if (!was && r.media.paused) stoppedAt = t;
      if (was && !r.media.paused) {
        order.push(`start ${t}`);
        if (stoppedAt >= 0) assert.ok(t - stoppedAt >= 1000, `a pause of ${t - stoppedAt} ms`);
      }
    }
    assert.equal(order.length, 2); // the 2nd and 3rd words (the 1st started before the loop)
  });

  it("fades each piece in and out, and leaves the volume up when it stops", () => {
    const r = rig();
    r.player.play(wholeSteps(WORDS, "steady", "ar"));
    assert.equal(r.volumes[0], 0); // starts silent…
    r.run(30);
    assert.equal(r.media.volume, 1); // …and is at full volume after the fade in
    r.run(460);
    assert.ok(r.media.volume < 1); // fading out in the last 40 ms of the piece
    r.run(20);
    assert.equal(r.media.paused, true);
    assert.equal(r.media.volume, 1); // ready for the next piece, or the clip played whole
  });

  it("a new tap fades the sounding word out, waits a moment, then plays the new one", () => {
    const r = rig();
    const one = wordStep(WORDS, 2, "steady", "ar");
    const other = wordStep(WORDS, 0, "steady", "ar");
    assert.ok(one && other);
    r.player.play([one]);
    assert.equal(r.media.currentTime, 1.7);
    r.run(200);
    r.player.play([other]); // tapped another word mid-way
    assert.equal(r.media.paused, false); // not cut dead: it fades out first
    r.run(30);
    assert.ok(r.media.volume < 0.5);
    r.run(30);
    assert.equal(r.media.paused, true);
    assert.equal(r.media.currentTime > 1.7, true); // the old word is not sought away while it sounds
    r.run(GAP_MS + 20);
    assert.equal(r.media.paused, false);
    r.run(600);
    assert.equal(r.player.playing, false);
    assert.deepEqual(r.log, ["play@1700x1", "stop@1940", "play@0x1", "stop@500"]);
  });

  it("stops at once (a quick fade), pause included, and says so", () => {
    const r = rig();
    r.player.play(wholeSteps(WORDS, "steady", "en"));
    r.run(600);
    assert.ok(r.timers().length > 0); // in the pause between two words
    r.player.stop();
    assert.deepEqual(r.timers(), []);
    assert.equal(r.media.paused, true);
    assert.deepEqual(r.states.at(-1), { playing: false, segment: null });
    r.run(3000);
    assert.equal(r.media.paused, true); // nothing starts again
  });

  it("stops mid-word with a fade, even without frames (a hidden tab)", () => {
    const r = rig();
    r.player.play(wholeSteps(WORDS, "steady", "ar"));
    r.run(200);
    r.player.stop();
    assert.equal(r.media.paused, false);
    r.frames().clear(); // the browser runs no frames: the timer ends the fade
    r.tick(FADE_OUT_MS + 20);
    assert.equal(r.media.paused, true);
    assert.equal(r.media.volume, 1);
  });

  it("ends a piece on time when the browser runs no frames", () => {
    const r = rig();
    r.player.play(wholeSteps(WORDS, "steady", "ar"));
    r.frames().clear();
    for (let i = 0; i < 60; i++) {
      r.frames().clear();
      r.tick(10);
    }
    assert.equal(r.media.paused, true);
    assert.ok(r.media.currentTime * 1000 <= 500 + 70, `stopped at ${r.media.currentTime * 1000}`);
  });

  it("stops at the end of the clip even when the last piece runs to it", () => {
    const r = rig();
    r.player.play(wholeSteps(LETTER, "steady", "en"));
    r.run(600);
    r.run(1400);
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
