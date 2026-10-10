/**
 * The photo framing editor's maths (lib/photoCrop.ts): the frame never shows a gap, the turn and the zoom keep the
 * spot the parent looks at, and the API gets the same part of the original that the frame shows.
 * `npm test` (node --test).
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  clampView,
  FRAME,
  FRAME_ASPECT,
  fromCrop,
  layout,
  maxZoom,
  pan,
  rotateView,
  sameCrop,
  toCrop,
  viewAt,
  zoomOf,
  zoomTo,
  type Rotation,
  type Size,
  type View,
} from "./photoCrop.ts";

const PHONE: Size = { w: 3024, h: 4032 }; // a portrait phone photo (the API keeps it at 1536 × 2048)
const WIDE: Size = { w: 2048, h: 1536 };
const near = (a: number, b: number, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, `${a} ≉ ${b}`);

/** The framed part's width ÷ height in pixels of the turned photo: always the frame's shape. */
function aspect(view: View, natural: Size): number {
  const t = view.rotate === 90 || view.rotate === 270 ? { w: natural.h, h: natural.w } : natural;
  return (view.w * t.w) / (view.h * t.h);
}

function inside(view: View) {
  assert.ok(view.u >= 0 && view.v >= 0, JSON.stringify(view));
  assert.ok(view.u + view.w <= 1 + 1e-9 && view.v + view.h <= 1 + 1e-9, JSON.stringify(view));
}

describe("the starting view", () => {
  it("covers the frame at zoom 1, centred, with the frame's shape", () => {
    for (const natural of [PHONE, WIDE, { w: 512, h: 512 }]) {
      const view = viewAt(natural, 0);
      inside(view);
      near(aspect(view, natural), FRAME_ASPECT);
      assert.ok(view.w === 1 || view.h === 1); // spans the whole width or the whole height
      near(zoomOf(view, natural), 1);
      near(view.u + view.w / 2, 0.5);
      near(view.v + view.h / 2, 0.5);
    }
  });
});

describe("dragging", () => {
  it("follows the finger and stops at the photo's edges", () => {
    const start = viewAt(WIDE, 0, 2);
    const right = pan(start, 40, 0, FRAME); // the photo moves right: the window moves left
    assert.ok(right.u < start.u);
    near(right.v, start.v);
    const far = pan(start, 10_000, -10_000, FRAME);
    near(far.u, 0);
    near(far.v, 1 - far.h);
    inside(far);
  });

  it("never leaves a gap, whatever the window asked for", () => {
    const view = clampView({ u: -0.3, v: 0.9, w: 0.5, h: 0.4, rotate: 0 });
    inside(view);
    assert.deepEqual(clampView({ u: 0, v: 0, w: 1.4, h: 1.2, rotate: 0 }), { u: 0, v: 0, w: 1, h: 1, rotate: 0 });
  });
});

describe("zooming", () => {
  it("keeps the spot under the fingers and the frame's shape", () => {
    const start = viewAt(WIDE, 0, 1.2);
    const at = { x: 0.25, y: 0.75 };
    const spot = [start.u + at.x * start.w, start.v + at.y * start.h];
    const zoomed = zoomTo(start, 2, WIDE, at);
    near(zoomOf(zoomed, WIDE), 2);
    near(zoomed.u + at.x * zoomed.w, spot[0]!);
    near(zoomed.v + at.y * zoomed.h, spot[1]!);
    near(aspect(zoomed, WIDE), FRAME_ASPECT);
  });

  it("stays between 1× and what the photo allows", () => {
    near(zoomOf(zoomTo(viewAt(WIDE, 0), 0.2, WIDE), WIDE), 1);
    near(zoomOf(zoomTo(viewAt(WIDE, 0), 9, WIDE), WIDE), 3);
    // a 512 px photo: the framed part may not go under 400 px of it, so barely any zoom
    const small = { w: 512, h: 512 };
    assert.ok(maxZoom(small, 0) > 1 && maxZoom(small, 0) < 1.25);
    assert.equal(maxZoom({ w: 400, h: 300 }, 0), 1);
    // the API keeps a big photo at 2048 px: its limit is the kept size's, not the camera's
    assert.equal(maxZoom({ w: 8000, h: 6000 }, 0), maxZoom(WIDE, 0));
    // the framed part at the limit is still big enough for the API (400 px)
    const limit = viewAt(PHONE, 0, maxZoom(PHONE, 0));
    assert.ok(limit.w * 1536 >= 400 && limit.h * 2048 >= 400);
  });
});

describe("the framing the API stores", () => {
  it("is the same part of the original, for every turn", () => {
    for (const rotate of [0, 90, 180, 270] as Rotation[]) {
      const view = pan(viewAt(PHONE, rotate, 2.2), 31, -17, FRAME);
      const crop = toCrop(view);
      assert.equal(crop.rotate, rotate);
      assert.ok(crop.x >= 0 && crop.y >= 0 && crop.x + crop.w <= 1 && crop.y + crop.h <= 1);
      const back = fromCrop(crop);
      for (const k of ["u", "v", "w", "h"] as const) near(back[k], view[k], 1e-5);
      // the cut-out, once turned, has the frame's shape (the API refuses anything else)
      const [cw, ch] = rotate % 180 ? [crop.h * PHONE.h, crop.w * PHONE.w] : [crop.w * PHONE.w, crop.h * PHONE.h];
      near(cw / ch, FRAME_ASPECT, 1e-3);
    }
  });

  it("turned a quarter clockwise, the right half of the turned photo is the top half of the original", () => {
    const view: View = { u: 0.5, v: 0, w: 0.5, h: 1, rotate: 90 };
    assert.deepEqual(toCrop(view), { x: 0, y: 0, w: 1, h: 0.5, rotate: 90 });
  });

  it("is compared to the eye", () => {
    const a = toCrop(viewAt(WIDE, 0, 1.5));
    assert.ok(sameCrop(a, { ...a, x: a.x + 1e-6 }));
    assert.ok(!sameCrop(a, { ...a, x: a.x + 0.01 }));
    assert.ok(!sameCrop(a, { ...a, rotate: 90 }));
    assert.ok(sameCrop(null, null) && !sameCrop(a, null));
  });
});

describe("turning", () => {
  it("keeps the spot in the middle and turns a full circle back", () => {
    let view = pan(viewAt(WIDE, 0, 1.6), -50, 30, FRAME);
    const first = toCrop(view);
    for (let i = 0; i < 4; i++) {
      view = rotateView(view, WIDE);
      inside(view);
      near(aspect(view, WIDE), FRAME_ASPECT);
    }
    assert.equal(view.rotate, 0);
    const back = toCrop(view);
    for (const k of ["x", "y", "w", "h"] as const) near(back[k], first[k], 1e-3);
  });
});

describe("the photo's place in the frame", () => {
  it("fills the frame exactly with the window", () => {
    const frame = { w: 358, h: 340 };
    const view = viewAt(WIDE, 0, 2, 0.3, 0.6);
    const box = layout(view, WIDE, frame);
    const scale = box.width / WIDE.w;
    near(box.left, -view.u * WIDE.w * scale, 1e-6);
    near(box.top, -view.v * WIDE.h * scale, 1e-6);
    near(view.w * WIDE.w * scale, frame.w, 1e-6);
    near(view.h * WIDE.h * scale, frame.h, 1e-3);
  });

  it("turns the photo around its own centre", () => {
    const frame = { w: 358, h: 340 };
    const view = viewAt(PHONE, 90);
    const box = layout(view, PHONE, frame);
    assert.equal(box.rotate, 90);
    // the turned box (height × width on screen) is centred where the window says
    const turnedLeft = box.left + box.width / 2 - box.height / 2;
    near(turnedLeft, -view.u * box.height, 1e-6);
  });
});
