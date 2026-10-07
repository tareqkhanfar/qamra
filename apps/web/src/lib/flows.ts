/**
 * The order flow per product (docs/plans/order-flows.md §c): the product decides the steps, in order, for this
 * child. There is no single wizard with skips: `stepsFor()` lists only the steps that apply, `resumeAt()` is
 * where a reload or a link resumes, `canShow()` gates a step named in the URL, and `progress()` is the real
 * «الخطوة n من N».
 *
 * Pure TypeScript with no "@/" imports, so `node --test src/lib/*.test.ts` loads it (Node strips the types).
 */

export type Kind = "story" | "activity";
export type StepId =
  | "child"
  | "line"
  | "consent"
  | "photo"
  | "style"
  | "character"
  | "companion"
  | "story"
  | "writing"
  | "review"
  | "format"
  | "addons"
  | "family"
  | "summary";

/** Every step, in the order a flow shows them; each flow keeps the ones it needs. */
export const ALL_STEPS: readonly StepId[] = [
  "child",
  "line",
  "consent",
  "photo",
  "style",
  "character",
  "companion",
  "family",
  "story",
  "writing",
  "review",
  "format",
  "addons",
  "summary",
];

/**
 * The activity-book lines (dawseyeh, journey, family, «قلبي يعرف الله»). The same values as `ACTIVITY_LINES`
 * in lib/shop.ts and the API's `store/workbooks.py` ACTIVITY; flows.test.ts checks that lib/shop.ts agrees.
 */
export const ACTIVITY_LINES = ["workbook", "journey", "family", "islamic"] as const;
export type ActivityLine = (typeof ACTIVITY_LINES)[number];

/** The activity books whose pages have the child trace their own Arabic name («اسمي»). */
export const TRACING_LINES: readonly ActivityLine[] = ["workbook", "journey"];

/**
 * The optional steps a flow pins once it decides them (the URL's `plan`), so that passing a step never drops it
 * from the count: `line` when the parent picks the story type inside the flow; the drawing steps once the child
 * (and, for a story, the type) is known; `reuse` when that decision is "no drawing, a ready character".
 */
export type PlanToken = "line" | "consent" | "photo" | "style" | "character" | "reuse";
const PLAN_TOKENS: readonly PlanToken[] = ["line", "consent", "photo", "style", "character", "reuse"];
const DRAWING: readonly PlanToken[] = ["consent", "photo", "style", "character", "reuse"];
/** The drawing steps: both steps and plan words. */
type DrawStep = "consent" | "photo" | "style" | "character";

export type FlowState = {
  kind: Kind;
  /** classic | magic | workbook | journey | family | islamic; null: a story whose type is not chosen yet. */
  productLine: string | null;
  /** The child the book is for (null: not chosen yet). */
  child: { consent: boolean; photos: number } | null;
  /** The server's "needs" answer (activity) / an approved character in the wanted style (story). */
  reusable: boolean;
  /** The character in the URL: drawn in this flow, or the one reused. */
  character: { approved: boolean } | null;
  /** The story book in the URL (stories only). */
  book: { status: string; line: "classic" | "magic" } | null;
  /** Story: the style is fixed by the story page or the type has a single option, so no style step. */
  stylePreset: boolean;
  /** The catalog offers the drawn companion («ارسم صاحبك») for this line. */
  companionOffered: boolean;
  /** The product needs the family step («مغامراتي مع عائلتي»). */
  asksFamily: boolean;
  /** The optional steps pinned by the flow (the URL's `plan`); null or empty: derive them from the facts. */
  plan?: readonly PlanToken[] | null;
};

export function isActivityLine(line: string | null | undefined): line is ActivityLine {
  return !!line && (ACTIVITY_LINES as readonly string[]).includes(line);
}

export function kindOf(productLine: string | null): Kind {
  return isActivityLine(productLine) ? "activity" : "story";
}

/** Whether the line's book has the child trace their Arabic name (so the name must be in Arabic letters). */
export function tracesName(line: string | null): boolean {
  return isActivityLine(line) && TRACING_LINES.includes(line);
}

/** `plan=consent,photo,character` → the tokens it pins (unknown words are ignored). */
export function parsePlan(value: string | null | undefined): PlanToken[] {
  if (!value) return [];
  return value.split(",").filter((x): x is PlanToken => (PLAN_TOKENS as readonly string[]).includes(x));
}

export function formatPlan(plan: readonly PlanToken[]): string {
  return PLAN_TOKENS.filter((x) => plan.includes(x)).join(",");
}

/** The drawing steps the facts call for now (no pin): consent, photo, style and character, or none. */
function drawingNow(s: FlowState): Set<DrawStep> {
  const out = new Set<DrawStep>();
  if (s.reusable) return out;
  if (!s.child?.consent) out.add("consent");
  if (!s.child?.photos) out.add("photo");
  if (s.kind === "story" && !s.stylePreset) out.add("style");
  out.add("character");
  return out;
}

/** Which optional steps (line and drawing) the flow includes: the pinned ones, else the facts. */
function optional(s: FlowState): Set<StepId> {
  const plan = s.plan ?? [];
  const out = new Set<StepId>();
  if (s.kind === "story" && (plan.includes("line") || s.productLine === null)) out.add("line");
  const pinned = plan.some((x) => DRAWING.includes(x));
  const drawing = pinned ? new Set(plan.filter((x): x is DrawStep => x !== "line" && x !== "reuse")) : drawingNow(s);
  for (const step of drawing) {
    if (step === "style" && s.kind !== "story") continue; // activity books never ask the art style
    out.add(step);
  }
  return out;
}

/**
 * The plan to pin when the flow leaves the child step (or, for a story, the type step): the drawing steps the
 * facts call for now, or `reuse`; plus `line` when the parent picks the story type in the flow.
 */
export function planFor(s: FlowState, lineAsked: boolean): PlanToken[] {
  const drawing: PlanToken[] = [...drawingNow(s)];
  return [...(lineAsked ? (["line"] as PlanToken[]) : []), ...(drawing.length ? drawing : (["reuse"] as PlanToken[]))];
}

/** The ordered steps of this flow, only the ones that apply. */
export function stepsFor(s: FlowState): StepId[] {
  const opt = optional(s);
  const steps = new Set<StepId>(["child"]);
  for (const step of ["line", "consent", "photo", "style", "character"] as const) if (opt.has(step)) steps.add(step);
  if (s.kind === "activity") {
    if (s.asksFamily) steps.add("family");
    steps.add("summary");
  } else {
    if (s.companionOffered) steps.add("companion");
    steps.add("story");
    steps.add("writing");
    // the page review is Magic's; while the type is unknown, count the longer flow (it only gets shorter)
    if (s.productLine === "magic" || s.productLine === null || s.book?.line === "magic") steps.add("review");
    steps.add("format");
    steps.add("addons");
  }
  return ALL_STEPS.filter((x) => steps.has(x));
}

/** After the character: the family step or the review step (activity); the companion or the story (story). */
function afterCharacter(s: FlowState): StepId {
  if (s.kind === "activity") return s.asksFamily ? "family" : "summary";
  return "story";
}

/** Where a reload or a link resumes: the furthest step the saved state allows (replaces `furthest()`). */
export function resumeAt(s: FlowState): StepId {
  if (!s.child) return "child";
  if (s.kind === "story") {
    if (s.book) {
      if (s.book.status === "generating" || s.book.status === "failed") return "writing";
      return s.book.line === "magic" && s.book.status === "preview" ? "review" : "format";
    }
    if (!s.productLine) return "line";
  }
  if (s.character) return s.character.approved ? afterCharacter(s) : "character";
  if (s.reusable) {
    // an activity book goes on with its ready character; a story needs it named in the URL first
    return s.kind === "activity" ? afterCharacter(s) : "style";
  }
  if (!s.child.consent) return "consent";
  if (!s.child.photos) return "photo";
  // a saved photo and no drawing yet: a story picks its style; an activity book draws from the photo step
  return s.kind === "story" ? "style" : "photo";
}

/** Whether a step named in the URL can be shown with what is loaded (replaces `allowed()`). */
export function canShow(step: StepId, s: FlowState): boolean {
  const story = s.kind === "story";
  const child = s.child;
  const ready = s.reusable || !!s.character?.approved;
  const book = s.book;
  switch (step) {
    case "child":
      return true;
    case "line":
      return story && !!child;
    case "consent":
      return !!child;
    case "photo":
      return !!child?.consent;
    case "style":
      return story && !!child?.consent && !!s.productLine;
    case "character":
      return !!child && !!s.character;
    case "companion":
      return story && !!child && !!s.productLine && !!s.character?.approved && s.companionOffered;
    case "story":
      return story && !!child && !!s.productLine && !!s.character?.approved;
    case "writing":
      return story && !!child && !!book && (book.status === "generating" || book.status === "failed");
    case "review":
      return story && !!child && !!book && book.line === "magic" && book.status === "preview";
    case "format":
    case "addons":
      return story && !!child && !!book && book.status !== "generating" && book.status !== "failed";
    case "family":
      return !story && s.asksFamily && !!child && ready;
    case "summary":
      return !story && !!child && ready;
  }
}

/**
 * «الخطوة n من N». A step that is not in the list (e.g. a new drawing asked for from the review step) is counted
 * where it falls, so the count still reads right.
 */
export function progress(steps: readonly StepId[], step: StepId): { n: number; total: number } {
  const list = steps.includes(step) ? [...steps] : ALL_STEPS.filter((x) => x === step || steps.includes(x));
  return { n: list.indexOf(step) + 1, total: list.length };
}

/* ---- the activity books' own questions (the server's `GET /api/shop/workbooks/needs` decides; these rules
   are its mirror, used for the first paint and as the fallback until that endpoint answers) ---------------- */

/** Whether the book prints the child's name in English letters: dawseyeh always; journey stages 2, 3 and the set. */
export function asksNameEn(line: string | null, options: Record<string, string>): boolean {
  if (line === "workbook") return true;
  if (line === "journey") return ["2", "3", "set"].includes(options.stage ?? "");
  return false;
}

/** The ages a variant is made for, [min, max] (§c.3), or null when the product has none. */
export function agesFor(line: string | null, options: Record<string, string>): [number, number] | null {
  if (line === "workbook") {
    return ({ kg1: [4, 5], kg2: [5, 6] } as Record<string, [number, number]>)[options.level ?? ""] ?? null;
  }
  if (line === "journey") {
    const stages: Record<string, [number, number]> = { "1": [3, 4], "2": [4, 5], "3": [5, 6], set: [3, 6] };
    return stages[options.stage ?? ""] ?? null;
  }
  if (line === "islamic") {
    const v = options.volume ?? "";
    if (["V1", "V2", "L1"].includes(v)) return [4, 6];
    if (["V3", "V4", "V5", "L2"].includes(v)) return [6, 8];
    if (["R", "set"].includes(v)) return [4, 8];
    return null;
  }
  if (line === "family") return [3, 7];
  return null;
}

/** Whether an age falls outside the variant's range (the review step's non-blocking note). */
export function outsideAges(age: number | null | undefined, ages: [number, number] | null): boolean {
  return !!ages && typeof age === "number" && (age < ages[0] || age > ages[1]);
}

/**
 * A name the child can trace: Arabic letters only, with spaces or hyphens between the words; the tashkeel and
 * the tatweel are allowed and ignored (as `qamra_workbook.names` cleans a name before its own check).
 */
const ARABIC_WORD = "[\\u0621-\\u063A\\u0641-\\u064A\\u0671-\\u06D3]+";
const ARABIC_NAME = new RegExp(`^${ARABIC_WORD}(?:[ -]+${ARABIC_WORD})*$`);
const MARKS = new RegExp("[\\u064B-\\u0652\\u0670\\u0640]", "g"); // the tashkeel and the tatweel
export function isArabicName(name: string): boolean {
  return ARABIC_NAME.test(name.replace(MARKS, "").trim());
}

/** The child's name in English letters, as the book prints it (§d chunk 3). */
export const LATIN_NAME = /^[A-Za-z][A-Za-z' -]{0,39}$/;
export function isLatinName(name: string): boolean {
  return LATIN_NAME.test(name.trim());
}
