/** The child's drawings (lib/drawings.ts): which one later books reuse, which ones the character step offers. */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { lastApproved, offered, tidyNote, type DrawingLike } from "./drawings.ts";

const d = (id: string, style: string, approved_at: string | null = null): DrawingLike => ({
  id,
  style,
  approved: approved_at !== null,
  approved_at,
});

describe("lastApproved", () => {
  // in drawing order, as the API lists a child's characters
  const first = d("first", "3d", "2026-10-10T08:00:00Z");
  const second = d("second", "3d", "2026-10-10T08:05:00Z");
  const painted = d("painted", "watercolor", "2026-10-10T08:03:00Z");
  const draft = d("draft", "cartoon");

  it("is the drawing approved last, not the newest drawing", () => {
    const back = { ...first, approved_at: "2026-10-10T08:09:00Z" }; // the parent went back to the first one
    assert.equal(lastApproved([back, painted, second, draft])?.id, "first");
    assert.equal(lastApproved([first, painted, second, draft])?.id, "second");
  });

  it("only counts the drawings that fit, and never a drawing not approved", () => {
    assert.equal(lastApproved([first, painted, second], (c) => c.style === "watercolor")?.id, "painted");
    assert.equal(lastApproved([draft]), null);
    assert.equal(
      lastApproved([first, second], (c) => c.style === "cartoon"),
      null,
    );
  });

  it("falls back to the drawing order without times (an older API)", () => {
    const a = { id: "a", style: "3d", approved: true };
    const b = { id: "b", style: "3d", approved: true };
    assert.equal(lastApproved([a, b])?.id, "b");
  });
});

describe("offered", () => {
  const list = [d("new", "watercolor"), d("mid", "coloring"), d("old", "3d")];

  it("keeps the drawings this book can use, newest first, and always the current one", () => {
    assert.deepEqual(
      offered(list, "new", ["3d", "watercolor"]).map((x) => x.id),
      ["new", "old"],
    );
    assert.deepEqual(
      offered(list, "mid", ["3d"]).map((x) => x.id),
      ["mid", "old"],
    );
    assert.deepEqual(
      offered(list, "new", null).map((x) => x.id),
      ["new", "mid", "old"],
    );
  });
});

describe("tidyNote", () => {
  it("squashes the spaces as the API counts them, and sends nothing when empty", () => {
    assert.equal(tidyNote("  شعره\n  أجعد  "), "شعره أجعد");
    assert.equal(tidyNote(" \n "), undefined);
  });
});
