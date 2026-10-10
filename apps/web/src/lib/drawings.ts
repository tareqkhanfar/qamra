/**
 * The child's drawings (owner, 2026-10-10): a redraw never hides the earlier ones, so the parent can compare them
 * (watercolor, 3D, …) and go back to one. The one approved last is the child's character for the next books, the
 * same rule as the API (`approved_at desc`).
 */

/** What these rules read of a character (lib/create `Character`, `Drawing`). */
export type DrawingLike = { id: string; style: string; approved: boolean; approved_at?: string | null };

/** The most the parent can write in «ما الذي لا يشبهه؟» (the API's `NOTE_MAX`). */
export const NOTE_MAX = 200;

/**
 * The child's character a book reuses: the approved one (that `fits`, e.g. in a style the book accepts) the
 * parent approved last. `list` is in drawing order (the API's), which breaks a tie or a missing time: the newer.
 */
export function lastApproved<T extends DrawingLike>(
  list: readonly T[],
  fits: (c: T) => boolean = () => true,
): T | null {
  const time = (c: T) => Date.parse(c.approved_at ?? "") || 0;
  let best: T | null = null;
  for (const c of list) {
    if (!c.approved || !fits(c)) continue;
    if (!best || time(c) >= time(best)) best = c;
  }
  return best;
}

/**
 * The drawings the character step offers (newest first, as listed): the ones in a style this book can use
 * (`usable`; null: every style), and always the drawing the step opened with.
 */
export function offered<T extends DrawingLike>(
  drawings: readonly T[],
  currentId: string,
  usable: readonly string[] | null,
): T[] {
  return drawings.filter((d) => d.id === currentId || !usable || usable.includes(d.style));
}

/** The note as sent: whitespace squashed (the API counts it so), nothing when empty. */
export function tidyNote(text: string): string | undefined {
  return text.split(/\s+/).filter(Boolean).join(" ") || undefined;
}
