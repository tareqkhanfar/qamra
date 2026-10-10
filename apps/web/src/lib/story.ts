/**
 * The story product (Addendum 9, StoryProduct): the book type, art style and format a parent picks, all derived
 * from the store catalog and the themes API (nothing hard-coded). Shared by the story page and the create flow.
 */
import type { ThemeCard } from "@/lib/catalog";
import type { Catalog, CatalogAddOn, CatalogProduct, CatalogStyle, CatalogVariant } from "@/lib/store";

export type Line = "classic" | "magic";
export const LINES: Line[] = ["classic", "magic"];
export const LINE_PRODUCT: Record<Line, string> = { classic: "classic-book", magic: "magic-book" };
const PRINTED = ["softcover", "hardcover", "spiral"];
const FORMAT_ORDER = ["softcover", "hardcover", "digital"];

export type Offer = {
  line: Line;
  product: CatalogProduct;
  formats: CatalogVariant[]; // priced variants, softcover → hardcover → digital
  from: number | null; // the cheapest printed copy (what the cards call "from"), else the cheapest one
  available: boolean; // false: no live Classic template for this story yet
};

export const num = (v: string | number | null | undefined) => (v === null || v === undefined ? 0 : Number(v));

function fromPrice(variants: CatalogVariant[]): number | null {
  const priced = variants.filter((v) => v.price !== null);
  const printed = priced.filter((v) => PRINTED.includes(v.options.format ?? ""));
  const pool = printed.length ? printed : priced;
  return pool.length ? Math.min(...pool.map((v) => num(v.price))) : null;
}

/** Classic needs a live template for the story; older APIs don't say, so the catalog decides. */
export function classicReady(theme: Pick<ThemeCard, "classic"> | null | undefined): boolean {
  if (!theme || theme.classic === undefined) return true;
  return Object.values(theme.classic).some((looks) => looks.length > 0);
}

export function offer(catalog: Catalog | null, line: Line, theme?: Pick<ThemeCard, "classic"> | null): Offer | null {
  const product = catalog?.products.find((p) => p.slug === LINE_PRODUCT[line]);
  if (!product) return null;
  const formats = product.variants
    .filter((v) => v.price !== null)
    .sort((a, b) => FORMAT_ORDER.indexOf(a.options.format ?? "") - FORMAT_ORDER.indexOf(b.options.format ?? ""));
  const available = formats.length > 0 && (line === "magic" || classicReady(theme));
  return { line, product, formats, from: fromPrice(formats), available };
}

export type StyleChoice = {
  style: CatalogStyle;
  available: boolean; // sellable in this line (for Classic: a live template for this story)
  looks: string[] | null; // Classic: the looks with a template (null = not known / all)
  modifier: number;
};

/** The art styles of both lines, each marked for the chosen line (design: «متوفر في سحري»). */
export function styleChoices(
  catalog: Catalog | null,
  line: Line,
  theme?: Pick<ThemeCard, "classic"> | null,
): StyleChoice[] {
  // the design's order: styles both lines sell first, then the Magic-only ones (catalog order within each)
  const rank = (s: CatalogStyle) => (s.lines.includes("classic") ? 0 : 1);
  const styles = (catalog?.styles ?? [])
    .filter((s) => s.lines.includes("classic") || s.lines.includes("magic"))
    .sort((a, b) => rank(a) - rank(b));
  return styles.map((style) => {
    const inLine = style.lines.includes(line);
    const live = line === "classic" && theme?.classic !== undefined ? (theme.classic[style.slug] ?? []) : null;
    return {
      style,
      available: inLine && (live === null || live.length > 0),
      looks: live,
      modifier: num(style.price_modifier),
    };
  });
}

/**
 * The art styles a story can be ordered in as «قمرة كلاسيك»: styles Classic sells that have a live template
 * for this story (any look). Empty: the story is «قمرة سحري» only, drawn page by page for the child.
 */
export function classicStylesFor(catalog: Catalog | null, theme?: Pick<ThemeCard, "classic"> | null): CatalogStyle[] {
  if (!offer(catalog, "classic", theme)?.available) return [];
  return styleChoices(catalog, "classic", theme)
    .filter((c) => c.available)
    .map((c) => c.style);
}

/** Where the digital copy comes free with a printed book (the `digital-copy` add-on, when it is 0 ₪). */
export function freeDigitalCopy(catalog: Catalog | null, line: Line): CatalogAddOn | null {
  const addon = catalog?.addons.find((a) => a.slug === "digital-copy");
  return addon && addon.lines.includes(line) && num(addon.price) === 0 ? addon : null;
}

export function addonFor(catalog: Catalog | null, slug: string, line: Line) {
  const a = catalog?.addons.find((x) => x.slug === slug);
  if (!a) return null;
  return { addon: a, included: a.included_lines.includes(line), offered: a.lines.includes(line) };
}

/** The parent's picks, carried in the URL to the create flow (which pre-fills them). */
export function createHref(theme: string, line: Line, style?: string | null, format?: string | null): string {
  const q = new URLSearchParams({ theme, line });
  if (style) q.set("style", style);
  if (format) q.set("format", format);
  return `/create?${q.toString()}`;
}

/** What a story "starts from": the cheapest available line's printed copy (or the line the parent chose). */
export function storyFrom(
  catalog: Catalog | null,
  theme: Pick<ThemeCard, "classic"> | null,
  line?: Line | null,
): number | null {
  const lines = line ? [line] : LINES;
  const prices = lines
    .map((l) => offer(catalog, l, theme))
    .filter((o): o is Offer => !!o && o.available && o.from !== null)
    .map((o) => o.from as number);
  return prices.length ? Math.min(...prices) : null;
}

/** One example per story for its cover (the API lists them girl, girl with hijab, boy). */
export function coversOf<T extends { theme: string }>(examples: T[]): Record<string, T> {
  const out: Record<string, T> = {};
  for (const e of examples) out[e.theme] ??= e;
  return out;
}
