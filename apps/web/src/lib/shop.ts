/** The store hub (Addendum 9, Shop and Quiz): activity books, prices "from", and the quiz API. */
import { api } from "@/lib/api";
import type { CatalogProduct, Currency } from "@/lib/store";

/**
 * The activity-book lines: books made from the child's name (and their character, when they have one), with no
 * story to write. The create flow, the cart and the order summaries treat them alike (lib/flows.ts keeps the same
 * list; the API's is `store/workbooks.py` ACTIVITY). «قلبي يعرف الله» (islamic) is listed only while the catalog
 * has a volume the scholar approved (the API omits it otherwise). `colorbook`: «دفاتر التلوين والرسم».
 */
export const ACTIVITY_LINES = ["workbook", "journey", "family", "islamic", "colorbook"] as const;

/** The activity books with a page at /workbooks/[product] and a card on the activity-books hub. */
export const WORKBOOK_LINES = ["workbook", "journey", "family", "islamic"] as const;

/** «دفاتر التلوين والرسم»: its own hub at /coloring, and a page per book at /coloring/[product]. */
export const COLORING_LINES = ["colorbook"] as const;

/** The coloring and drawing books (content/store/catalog.yaml): a quiz pick names a product, not a line. */
export const COLORING_SLUGS = ["coloring-letters", "coloring-palestine", "coloring-ramadan", "sketchbook"] as const;

export function isColoringLine(line: string | null | undefined): boolean {
  return (COLORING_LINES as readonly string[]).includes(line ?? "");
}

/** An activity book's product page: /coloring/<slug> for the coloring and drawing books, else /workbooks/<slug>. */
export function productPath(product: { slug: string; line?: string | null }): string {
  const coloring = isColoringLine(product.line) || (COLORING_SLUGS as readonly string[]).includes(product.slug);
  return `${coloring ? "/coloring" : "/workbooks"}/${product.slug}`;
}

/** The activity books have their product pages (/workbooks/[product]); the cards and the quiz link there. */
export const WORKBOOK_PAGES = true;

const PRINTED = ["softcover", "hardcover", "spiral"];

/**
 * The cheapest single printed copy (a volume or a stage, not a set), else the cheapest variant; null when the
 * catalog carries no price (none set, or prices hidden from customers: the API then sends none).
 */
export function productFrom(product: CatalogProduct): number | null {
  const priced = product.variants.filter((v) => v.price !== null && v.price !== undefined);
  const single = priced.filter((v) => !Object.values(v.options).includes("set"));
  const printed = single.filter((v) => PRINTED.includes(v.options.format ?? ""));
  const pool = printed.length ? printed : single.length ? single : priced;
  return pool.length ? Math.min(...pool.map((v) => Number(v.price))) : null;
}

export type QuizPick = {
  slug: string;
  options: Record<string, string>;
  kind: "stories" | "product";
  name_ar: string;
  name_en: string;
  why_ar: string;
  why_en: string;
  from_price: string | null;
  currency: Currency;
  available: boolean;
};
export type QuizAnswer = { product: QuizPick; alternative: QuizPick };

export const quizApi = {
  answer: (age: number, goal: string, pen: string | null) =>
    api<QuizAnswer>(`/api/shop/quiz?age=${age}&goal=${goal}${pen ? `&pen=${pen}` : ""}`),
};

/** Where a quiz pick leads: the stories, or the product's page once it exists (null: not yet). */
export function pickHref(p: QuizPick): string | null {
  if (p.kind === "stories") return "/stories";
  if (!WORKBOOK_PAGES || !p.available) return null; // a product that isn't in the catalog has no page
  const q = new URLSearchParams(p.options).toString();
  return `${productPath(p)}${q ? `?${q}` : ""}`;
}
