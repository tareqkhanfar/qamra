/** The store hub (Addendum 9, Shop and Quiz): activity books, prices "from", and the quiz API. */
import { api } from "@/lib/api";
import type { CatalogProduct, Currency } from "@/lib/store";

/** The activity-book lines the shop lists (their product pages come later: /workbooks/[product]). */
export const ACTIVITY_LINES = ["workbook", "journey", "family"] as const;

/**
 * /workbooks/[product] is built by another part of the work (Addendum 9 §1.1). Until it exists the cards and the
 * quiz show «قريبًا» and link nowhere; flip this when the pages ship.
 */
export const WORKBOOK_PAGES = false;

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
  if (!WORKBOOK_PAGES || !p.available) return null;
  const q = new URLSearchParams(p.options).toString();
  return `/workbooks/${p.slug}${q ? `?${q}` : ""}`;
}
