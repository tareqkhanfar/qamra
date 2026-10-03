/** The store hub (Addendum 9, Shop and Quiz): activity books, prices "from", and the quiz API. */
import { api } from "@/lib/api";
import type { CatalogProduct, Currency } from "@/lib/store";

/**
 * The activity-book lines the shop lists; each has its product page at /workbooks/[product]. «قلبي يعرف الله»
 * (islamic) is listed only while the catalog has a volume the scholar approved (the API omits it otherwise).
 */
export const ACTIVITY_LINES = ["workbook", "journey", "family", "islamic"] as const;

/** The activity books have their product pages (/workbooks/[product]); the cards and the quiz link there. */
export const WORKBOOK_PAGES = true;

const PRINTED = ["softcover", "hardcover", "spiral"];

/** The cheapest single printed copy (a volume or a stage, not a set), else the cheapest variant. */
export function productFrom(product: CatalogProduct): number | null {
  const priced = product.variants.filter((v) => v.price !== null);
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
  if (!WORKBOOK_PAGES || !p.from_price) return null; // a product that isn't in the catalog has no page
  const q = new URLSearchParams(p.options).toString();
  return `/workbooks/${p.slug}${q ? `?${q}` : ""}`;
}
