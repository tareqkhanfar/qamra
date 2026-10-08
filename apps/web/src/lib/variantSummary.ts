/**
 * What a cart or order line will print, in a few words (docs/plans/order-flows.md §c.9): the cart, the checkout
 * and the order page say the same thing about every line.
 *
 * - An activity book: the cover's title with the child's name («دوسية ضحى»), the variant («KG2 · الجزء الأول ·
 *   ملوّن · مطبوع»), the name in English letters where the book prints it, and the family of «مغامراتي مع عائلتي».
 * - A story: the book's title, the line (قمرة كلاسيك / قمرة سحري), the format and the art style, the story itself
 *   when the title doesn't say it, and «إهداء ✓».
 *
 * Pure TypeScript with no "@/" imports, so `node --test src/lib/*.test.ts` loads it. It returns message keys
 * under `orderPath.line` (with their values and a fallback text for a value we have no words for yet) or plain
 * text: names that are data (products, stories, styles, the child's own names). The caller says whether the line
 * is an activity book (`lib/order.ts`, from the one list `ACTIVITY_LINES`).
 */

export type Kind = "story" | "activity";

/** A message under `orderPath.line`, or text that is shown as it is. */
export type Part = { key: string; values?: Record<string, string | number>; fallback?: string } | { text: string };

/** «مغامراتي مع عائلتي»: the family as the line holds it (API `family`: {name, city, members}). */
export type FamilyHeld = {
  name?: string | null;
  city?: string | null;
  members?: readonly { relation?: string | null; role?: string | null; name?: string | null }[] | null;
};

/** The fields of a cart line (or an order's line) the summary reads; every one may be missing. */
export type LineInput = {
  line?: string | null;
  options?: Readonly<Record<string, string>> | null;
  child_name?: string | null;
  child_name_en?: string | null;
  family?: FamilyHeld | null;
  book_title?: string | null;
  addons?: readonly { slug: string }[] | null;
  dedication?: boolean | null;
};

/** The names that are data, already in the page's language. */
export type Names = { product: string; theme?: string | null; style?: string | null };

export type FamilyFact = { name: string; city: string; members: { relation: string; name: string }[] };

export type Summary = {
  kind: Kind;
  title: Part;
  details: Part[]; // one line, joined with « · »
  facts: Part[]; // one short line each
  family: FamilyFact | null; // the family book only, once the line has its child
};

/** The order a variant's options are read in, whatever order the catalog keeps them. */
const OPTIONS = ["level", "volume", "stage", "interior", "format"] as const;

const DEDICATION = "dedication-page";
const DIGITAL = "digital"; // a file, not a printed book: downloaded from the order page or the account once made

export function summarize(item: LineInput, kind: Kind, names: Names): Summary {
  return kind === "activity" ? activity(item, names) : story(item, names);
}

function activity(item: LineInput, names: Names): Summary {
  const line = item.line ?? "";
  const child = clean(item.child_name);
  const options = item.options ?? {};
  const title: Part = child
    ? { key: `title.${line}`, values: { name: child }, fallback: names.product }
    : { text: names.product };
  const details: Part[] = OPTIONS.filter((o) => options[o]).map((o) => {
    const value = options[o];
    return o === "format"
      ? { key: `activityFormat.${value}`, fallback: value }
      : { key: `${line}.${o}.${value}`, fallback: value };
  });
  const facts: Part[] = [];
  const latin = clean(item.child_name_en);
  if (latin) facts.push({ key: "nameEn", values: { name: latin } });
  if (options.format === DIGITAL) facts.push({ key: "download" });
  return { kind: "activity", title, details, facts, family: line === "family" ? familyOf(item, child) : null };
}

function story(item: LineInput, names: Names): Summary {
  const child = clean(item.child_name);
  const book = clean(item.book_title);
  const theme = clean(names.theme);
  const options = item.options ?? {};
  const title: Part = book
    ? { text: book }
    : child
      ? { key: "title.story", values: { name: child } }
      : { text: theme || names.product };
  const details: Part[] = [{ text: names.product }];
  if (options.format) details.push({ key: `format.${options.format}`, fallback: options.format });
  if (clean(names.style)) details.push({ text: clean(names.style) });
  const facts: Part[] = [];
  // the story, unless the title already is it (a line still waiting for its child shows the story as its title)
  if (theme && (book || child)) facts.push({ key: "story", values: { name: theme } });
  if (item.dedication || (item.addons ?? []).some((a) => a.slug === DEDICATION)) facts.push({ key: "dedication" });
  if (options.format === DIGITAL) facts.push({ key: "download" });
  return { kind: "story", title, details, facts, family: null };
}

/** The family the book prints, once the line has its child (before that, nothing is decided yet). */
function familyOf(item: LineInput, child: string): FamilyFact | null {
  if (!child) return null;
  const held = item.family ?? {};
  return {
    name: clean(held.name) || child, // the book prints «عائلة {child}» when the family name is empty
    city: clean(held.city),
    members: (held.members ?? []).map((m) => ({ relation: clean(m.relation) || "other", name: clean(m.name) })),
  };
}

function clean(value: string | null | undefined): string {
  return (value ?? "").trim();
}
