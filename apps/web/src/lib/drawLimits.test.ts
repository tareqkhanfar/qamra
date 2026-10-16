/** The free drawings that come back with time (lib/drawLimits.ts): what is left, and when the next one is back. */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { blockedUntilOf, drawsLeft, formatClock, formatWait, refillTime, waitParts } from "./drawLimits.ts";

const NOW = Date.parse("2026-10-16T12:00:00Z");
const at = (minutes: number) => new Date(NOW + minutes * 60_000).toISOString();

describe("waitParts", () => {
  it("rounds up to the whole minute and splits hours from minutes", () => {
    assert.deepEqual(waitParts(at(80), NOW), { hours: 1, minutes: 20 });
    assert.deepEqual(waitParts(at(120), NOW), { hours: 2, minutes: 0 });
    assert.deepEqual(waitParts(new Date(NOW + 61_000), NOW), { hours: 0, minutes: 2 });
    assert.deepEqual(waitParts(new Date(NOW + 5_000), NOW), { hours: 0, minutes: 1 }); // never «0 minutes»
    assert.deepEqual(waitParts(at(-5), NOW), { hours: 0, minutes: 1 });
  });
});

describe("formatWait", () => {
  it("counts Arabic hours and minutes as they are read after «بعد»", () => {
    const ar = (hours: number, minutes: number) => formatWait({ hours, minutes }, "ar");
    assert.equal(ar(1, 0), "ساعة");
    assert.equal(ar(2, 0), "ساعتين");
    assert.equal(ar(3, 0), "3 ساعات");
    assert.equal(ar(10, 0), "10 ساعات");
    assert.equal(ar(11, 0), "11 ساعة");
    assert.equal(ar(23, 0), "23 ساعة");
    assert.equal(ar(0, 1), "دقيقة");
    assert.equal(ar(0, 2), "دقيقتين");
    assert.equal(ar(0, 5), "5 دقائق");
    assert.equal(ar(0, 45), "45 دقيقة");
    assert.equal(ar(1, 20), "ساعة و20 دقيقة");
    assert.equal(ar(2, 2), "ساعتين ودقيقتين");
    assert.equal(ar(1, 3), "ساعة و3 دقائق");
  });

  it("says English hours and minutes", () => {
    const en = (hours: number, minutes: number) => formatWait({ hours, minutes }, "en");
    assert.equal(en(1, 0), "an hour");
    assert.equal(en(2, 0), "2 hours");
    assert.equal(en(0, 1), "a minute");
    assert.equal(en(1, 1), "1 hour and 1 minute");
    assert.equal(en(0, 45), "45 minutes");
    assert.equal(en(1, 20), "1 hour and 20 minutes");
  });
});

describe("formatClock", () => {
  it("shows the time of day in the parent's language, with Latin digits", () => {
    assert.equal(formatClock("2026-10-16T13:40:00Z", "en", "Asia/Hebron"), "4:40 PM");
    assert.equal(formatClock("2026-10-16T13:40:00Z", "ar", "Asia/Hebron"), "4:40 م");
    assert.equal(formatClock("2026-10-16T06:05:00Z", "ar", "UTC"), "6:05 ص");
  });
});

describe("refillTime", () => {
  it("gives the wait and the clock, or nothing once the time is unknown or past", () => {
    assert.deepEqual(refillTime(at(80), NOW, "en", "UTC"), { time: "1 hour and 20 minutes", clock: "1:20 PM" });
    assert.deepEqual(refillTime(at(30), NOW, "ar", "UTC"), { time: "30 دقيقة", clock: "12:30 م" });
    assert.equal(refillTime(null, NOW, "ar"), null);
    assert.equal(refillTime("not a date", NOW, "ar"), null);
    assert.equal(refillTime(at(-1), NOW, "ar"), null);
  });
});

describe("drawsLeft", () => {
  it("is the API's count, and one more once the time it gave has passed", () => {
    assert.equal(drawsLeft({ redraws_left: 2 }, NOW), 2);
    assert.equal(drawsLeft({ redraws_left: 0, redraws_reset_at: at(10) }, NOW), 0);
    assert.equal(drawsLeft({ redraws_left: 0, redraws_reset_at: at(-1) }, NOW), 1);
    assert.equal(drawsLeft({ redraws_left: 0, redraws_reset_at: null }, NOW), 0);
  });

  it("is none while the API's own refusal holds, and never runs out for staff", () => {
    assert.equal(drawsLeft({ redraws_left: 2 }, NOW, at(15)), 0); // the page was older than the refusal
    assert.equal(drawsLeft({ redraws_left: 0 }, NOW, at(-1)), 1);
    assert.equal(drawsLeft({ redraws_left: 0, redraws_unlimited: true, redraws_total: 3 }, NOW, at(15)), 3);
  });
});

describe("blockedUntilOf", () => {
  it("reads the time from the API's «free_draws_used» answer only", () => {
    assert.equal(blockedUntilOf({ code: "free_draws_used", details: { reset_at: at(5) } }), at(5));
    assert.equal(blockedUntilOf({ code: "free_draws_used", details: {} }), null);
    assert.equal(blockedUntilOf({ code: "redraws_used", details: { reset_at: at(5) } }), null);
    assert.equal(blockedUntilOf(null), null);
  });
});
