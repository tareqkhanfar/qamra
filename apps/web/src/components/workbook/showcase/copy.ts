/**
 * What each part of an activity book is about, for the product page's details panel: drawn from the books'
 * own content (content/workbook/curriculum, content/journey, content/family-book, content/islamic and the
 * rendered pages), Arabic first, language-reviewed. Keys are the preview export's part keys (`kg1-2`, `3`, `V1`,
 * `book`); a set has its own pitch and list and shows its parts' short lines.
 */
import type { Picks } from "@/lib/workbook";
import data from "./copy.json";

export type Line = { ar: string; en: string };
export type PartCopy = {
  short: Line; // one line, for a set's list of its books
  pitch: Line; // one warm sentence
  topics: Line[]; // what it covers
  skills: Line[]; // what the child gains
  age: Line;
  pages: number; // inside pages, as rendered
  weeks?: number;
  personal: Line[]; // what is made for the child
  included: Line[]; // what else every copy holds (never an add-on)
};
export type SetCopy = { pitch: Line; age?: Line; included: Line[] };
type ProductCopy = { parts: Record<string, PartCopy>; sets: Record<string, SetCopy> };

export type ShowcaseCopy =
  { kind: "part"; part: PartCopy } | { kind: "set"; set: SetCopy; parts: { key: string; copy: PartCopy }[] };

export const COPY = data as Record<string, ProductCopy>;

/** The set a pick names, as a key of the product's `sets`: `kg1-set`, `set` (stages, volumes), `L1`, `L2`. */
function setKey(line: string, picks: Picks): string | null {
  if (line === "workbook") return picks.volume === "set" ? `${picks.level ?? "kg2"}-set` : null;
  if (line === "journey") return picks.stage === "set" ? "set" : null;
  if (line === "islamic") return ["L1", "L2", "set"].includes(picks.volume ?? "") ? picks.volume! : null;
  return null;
}

/** The details for the picks: one part's, or a set's with its parts (`keys`, from `partKeys`). */
export function showcaseCopy(slug: string, line: string, picks: Picks, keys: string[]): ShowcaseCopy | null {
  const own = COPY[slug];
  if (!own) return null;
  const set = setKey(line, picks);
  const parts = keys.flatMap((key) => (own.parts[key] ? [{ key, copy: own.parts[key] }] : []));
  if (set && own.sets[set] && parts.length > 1) return { kind: "set", set: own.sets[set], parts };
  return parts[0] ? { kind: "part", part: parts[0].copy } : null;
}
