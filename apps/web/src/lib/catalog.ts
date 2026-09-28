/** Server-side reads of the public catalog (story worlds, prices) from the API. */
import type { SceneArt } from "@/components/art/Scene";

export type ThemeCard = {
  slug: string;
  name: string;
  tagline: string;
  age_min: number;
  age_max: number;
  pages: number;
  occasions: string[];
  tag: "popular" | "new" | "kindergarten" | null;
  status: "available" | "coming_soon";
  art: SceneArt;
};

export type ThemeDetail = ThemeCard & {
  description: string;
  values: string[];
  companion_slot: boolean;
  peek: { kind: "art" | "text"; art?: SceneArt; text?: string }[];
  sample_name: string | null;
  samples: { index: number; text: string; art: SceneArt }[];
};

export type Price = { product: "digital" | "softcover" | "hardcover"; amount: string | null; currency: "ILS" };

const API = () => process.env.API_INTERNAL_URL ?? "http://localhost:8000";

async function get<T>(path: string, revalidate = 60): Promise<T | null> {
  try {
    const res = await fetch(API() + path, { next: { revalidate } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export const getThemes = (lang: string) => get<ThemeCard[]>(`/api/themes?lang=${lang}`);
export const getTheme = (slug: string, lang: string) =>
  get<ThemeDetail>(`/api/themes/${encodeURIComponent(slug)}?lang=${lang}`);
export const getPricing = () => get<Price[]>("/api/pricing", 300);

/** Lowest configured price, or null when prices are not set yet. */
export function lowestPrice(prices: Price[] | null): string | null {
  const amounts = (prices ?? []).map((p) => p.amount).filter((a): a is string => a !== null);
  if (!amounts.length) return null;
  return formatAmount(String(Math.min(...amounts.map(Number))));
}

export function formatAmount(amount: string): string {
  const n = Number(amount);
  return Number.isInteger(n) ? String(n) : n.toFixed(2); // Latin digits for prices (design rule)
}
