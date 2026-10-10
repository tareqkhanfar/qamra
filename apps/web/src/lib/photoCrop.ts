/**
 * The parent's framing of the child's photo (the photo step; owner's request of 2026-10-10): drag, zoom and turn
 * the photo until the face sits in the face-guide oval. The API keeps the framing as numbers on the photo
 * (qamra_ai/pipeline/photo_crop.py): `x, y, w, h` are fractions (0–1) of the original, then `rotate` turns the
 * cut-out clockwise. The editor works on the turned photo: a `View` is the frame's window on it, in fractions
 * of the turned photo. Pure functions, no imports: `npm test` checks them (photoCrop.test.ts).
 */

export type Rotation = 0 | 90 | 180 | 270;
/** The framing as the API stores it. */
export type PhotoCrop = { x: number; y: number; w: number; h: number; rotate: Rotation };
/** The frame's window on the turned photo (fractions of its width and height). */
export type View = { u: number; v: number; w: number; h: number; rotate: Rotation };
export type Size = { w: number; h: number };

/** The photo frame and its face-guide oval (design Create3); photo_crop.py FRAME_W × FRAME_H. */
export const FRAME = { w: 358, h: 340 } as const;
export const FRAME_ASPECT = FRAME.w / FRAME.h;
export const OVAL = { cx: 179, cy: 140, rx: 84, ry: 104 } as const;
export const MAX_ZOOM = 3;
const STORED_MAX_SIDE = 2048; // the API keeps the photo at most this size (uploads.PHOTO_MAX_SIDE)
const MIN_CROP_SIDE = 400 + 4; // photo_crop.MIN_CROP_SIDE_PX, and a little for the server's rounding

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n));
const round6 = (n: number) => Math.round(n * 1e6) / 1e6;

/** The photo's size once turned. */
export function turned(natural: Size, rotate: Rotation): Size {
  return rotate === 90 || rotate === 270 ? { w: natural.h, h: natural.w } : natural;
}

/** The window at zoom 1: the frame spans the turned photo's whole width or whole height, never leaving a gap. */
function cover(natural: Size, rotate: Rotation): Size {
  const t = turned(natural, rotate);
  const ratio = t.w / t.h;
  return ratio > FRAME_ASPECT ? { w: FRAME_ASPECT / ratio, h: 1 } : { w: 1, h: ratio / FRAME_ASPECT };
}

export function zoomOf(view: View, natural: Size): number {
  return cover(natural, view.rotate).w / view.w;
}

/**
 * How far the parent may zoom in: 3×, or less when the framed part of the photo (as the API keeps it) would get
 * too small to draw from. 1 when the photo is already small: no zoom at all.
 */
export function maxZoom(natural: Size, rotate: Rotation): number {
  const scale = Math.min(1, STORED_MAX_SIDE / Math.max(natural.w, natural.h));
  const t = turned(natural, rotate);
  const c = cover(natural, rotate);
  const shortSide = Math.min(c.w * t.w, c.h * t.h) * scale;
  return clamp(shortSide / MIN_CROP_SIDE, 1, MAX_ZOOM);
}

/** The window kept inside the photo: the frame never shows a gap. */
export function clampView(view: View): View {
  const w = Math.min(1, view.w);
  const h = Math.min(1, view.h);
  return { ...view, w, h, u: clamp(view.u, 0, 1 - w), v: clamp(view.v, 0, 1 - h) };
}

/** The window at `zoom` (within what the photo allows), centred on (cu, cv) of the turned photo when it can be. */
export function viewAt(natural: Size, rotate: Rotation, zoom = 1, cu = 0.5, cv = 0.5): View {
  const c = cover(natural, rotate);
  const z = clamp(zoom, 1, maxZoom(natural, rotate));
  const w = c.w / z;
  const h = c.h / z;
  return clampView({ u: cu - w / 2, v: cv - h / 2, w, h, rotate });
}

/** Dragged by (dx, dy) screen pixels in a frame of `frame` pixels: the photo follows the finger. */
export function pan(view: View, dx: number, dy: number, frame: Size): View {
  return clampView({ ...view, u: view.u - (dx / frame.w) * view.w, v: view.v - (dy / frame.h) * view.h });
}

/** Zoomed to `zoom` around a point of the frame (fractions; the centre by default), which stays under the finger. */
export function zoomTo(view: View, zoom: number, natural: Size, at = { x: 0.5, y: 0.5 }): View {
  const c = cover(natural, view.rotate);
  const z = clamp(zoom, 1, maxZoom(natural, view.rotate));
  const pu = view.u + at.x * view.w;
  const pv = view.v + at.y * view.h;
  const w = c.w / z;
  const h = c.h / z;
  return clampView({ ...view, w, h, u: pu - at.x * w, v: pv - at.y * h });
}

/** A point of the original (fractions) on the photo turned clockwise by `r`. */
function toTurned(p: number, q: number, r: Rotation): [number, number] {
  if (r === 90) return [1 - q, p];
  if (r === 180) return [1 - p, 1 - q];
  if (r === 270) return [q, 1 - p];
  return [p, q];
}

/** A point of the turned photo back on the original. */
function toOriginal(u: number, v: number, r: Rotation): [number, number] {
  if (r === 90) return [v, 1 - u];
  if (r === 180) return [1 - u, 1 - v];
  if (r === 270) return [1 - v, u];
  return [u, v];
}

/** The window as the API stores it: the same part of the original, and the turn. */
export function toCrop(view: View): PhotoCrop {
  const [p0, q0] = toOriginal(view.u, view.v, view.rotate);
  const [p1, q1] = toOriginal(view.u + view.w, view.v + view.h, view.rotate);
  const x = round6(Math.min(p0, p1));
  const y = round6(Math.min(q0, q1));
  const w = Math.min(round6(Math.abs(p1 - p0)), 1 - x);
  const h = Math.min(round6(Math.abs(q1 - q0)), 1 - y);
  return { x, y, w: round6(w), h: round6(h), rotate: view.rotate };
}

/** A stored framing as the editor's window. */
export function fromCrop(crop: PhotoCrop): View {
  const [u0, v0] = toTurned(crop.x, crop.y, crop.rotate);
  const [u1, v1] = toTurned(crop.x + crop.w, crop.y + crop.h, crop.rotate);
  const u = Math.min(u0, u1);
  const v = Math.min(v0, v1);
  return clampView({ u, v, w: Math.abs(u1 - u0), h: Math.abs(v1 - v0), rotate: crop.rotate });
}

/** Turned a quarter clockwise, with the same spot of the photo in the middle and the same zoom when it fits. */
export function rotateView(view: View, natural: Size): View {
  const [p, q] = toOriginal(view.u + view.w / 2, view.v + view.h / 2, view.rotate);
  const rotate = ((view.rotate + 90) % 360) as Rotation;
  const [cu, cv] = toTurned(p, q, rotate);
  return viewAt(natural, rotate, zoomOf(view, natural), cu, cv);
}

/** Whether two framings are the same to the eye (a ten-thousandth of the photo). */
export function sameCrop(a: PhotoCrop | null, b: PhotoCrop | null): boolean {
  if (!a || !b) return a === b;
  const near = (m: number, n: number) => Math.abs(m - n) < 1e-4;
  return a.rotate === b.rotate && near(a.x, b.x) && near(a.y, b.y) && near(a.w, b.w) && near(a.h, b.h);
}

/**
 * Where the photo's <img> goes in a frame of `frame` pixels: its box before turning (pixels, from the frame's
 * top-left corner) and the turn around its centre, so the window fills the frame exactly.
 */
export function layout(
  view: View,
  natural: Size,
  frame: Size,
): { left: number; top: number; width: number; height: number; rotate: Rotation } {
  const t = turned(natural, view.rotate);
  const scale = frame.w / (view.w * t.w); // frame pixels per photo pixel
  const boxW = t.w * scale;
  const boxH = t.h * scale;
  const cx = -view.u * boxW + boxW / 2;
  const cy = -view.v * boxH + boxH / 2;
  const width = natural.w * scale;
  const height = natural.h * scale;
  return { left: cx - width / 2, top: cy - height / 2, width, height, rotate: view.rotate };
}
