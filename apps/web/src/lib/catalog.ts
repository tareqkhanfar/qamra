/** Server-side reads of the public catalog (story worlds, prices) from the API. */
import type { SceneArt } from "@/components/art/Scene";

export type ThemeCard = {
  slug: string;
  name: string;
  /** The book title with a {name} slot. */
  title: string;
  tagline: string;
  age_min: number;
  age_max: number;
  pages: number;
  occasions: string[];
  tag: "popular" | "new" | "kindergarten" | null;
  status: "available" | "coming_soon";
  art: SceneArt;
  /** «قمرة كلاسيك»: art style → the looks (girl, girl_hijab, boy) with a live template; see lib/classic.ts. */
  classic?: Record<string, string[]>;
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

/** `revalidate` seconds of Next data cache; 0 = always ask the API (which keeps its own short cache). */
async function get<T>(path: string, revalidate = 60): Promise<T | null> {
  try {
    const res = await fetch(API() + path, revalidate > 0 ? { next: { revalidate } } : { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export const getThemes = (lang: string) => get<ThemeCard[]>(`/api/themes?lang=${lang}`);
export const getTheme = (slug: string, lang: string) =>
  get<ThemeDetail>(`/api/themes/${encodeURIComponent(slug)}?lang=${lang}`);
export const getPricing = () => get<Price[]>("/api/pricing", 0);
/** Published example books (real, watermarked pages); [] when none are published or the API is older. */
export const getExamples = async (lang: string, theme?: string) =>
  (await get<import("@/lib/examples").Example[]>(
    `/api/examples?lang=${lang}${theme ? `&theme=${encodeURIComponent(theme)}` : ""}`,
  )) ?? [];

/** The store catalog (Addendum 4): products, variants and prices, styles, add-ons, delivery zones. */
export const getStoreCatalog = (currency: "ILS" | "JOD" = "ILS") =>
  get<import("@/lib/store").Catalog>(`/api/store/catalog?currency=${currency}`, 0);

/** Admin-managed public settings (prices, contact details, site switches). */
export type PublicSettings = {
  price_digital_ils: string;
  price_softcover_ils: string;
  price_hardcover_ils: string;
  delivery_fee_ils: string;
  support_whatsapp: string;
  sales_whatsapp: string;
  support_email: string;
  sales_email: string;
  company_name: string;
  instagram_url: string;
  facebook_url: string;
  registration_open: boolean;
  music_enabled: boolean;
  music_volume: number;
  animations_enabled: boolean;
  google_login_enabled: boolean;
};

export const getPublicSettings = () => get<PublicSettings>("/api/settings/public", 0);

/** wa.me link for a stored phone number (digits only). */
export const whatsappLink = (phone: string) => `https://wa.me/${phone.replace(/\D/g, "")}`;

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
