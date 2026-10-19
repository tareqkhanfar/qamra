/** Server-side reads of the public catalog (story worlds, prices) from the API. */
import type { SceneArt } from "@/components/art/Scene";
import { findBookByCode } from "./bookCode.ts";

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
  /** The sample child's gender: fills the title's {masc/fem} (null when there is no sample child). */
  sample_gender: "m" | "f" | null;
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

/** Examples in the site's language; English visitors see the Arabic ones until English ones exist. */
export async function examplesFor(locale: string, theme?: string) {
  const own = await getExamples(locale, theme);
  return own.length || locale === "ar" ? own : getExamples("ar", theme);
}

/** The store catalog (Addendum 4): products, variants and prices, styles, add-ons, delivery zones. */
export const getStoreCatalog = (currency: "ILS" | "JOD" = "ILS") =>
  get<import("@/lib/store").Catalog>(`/api/store/catalog?currency=${currency}`, 0);

/** Shop facts the catalog doesn't carry (Addendum 9): the class books' "from" price for the B2B banner. */
export type ShopSummary = {
  class_book_from: string | null;
  class_book_min_qty: number | null;
  currency: string;
  /** Per product: can it be ordered now (admin switch). */
  orderable?: Record<string, boolean>;
};
export async function getShopSummary(currency: "ILS" | "JOD" = "ILS"): Promise<ShopSummary | null> {
  const [summary, prices] = await Promise.all([
    get<ShopSummary>(`/api/shop/summary?currency=${currency}`),
    getPricesShown(),
  ]);
  // kept up to a minute in the data cache: a price cached before the admin hid them never shows
  return summary && !prices ? { ...summary, class_book_from: null } : summary;
}

/** Admin-managed public settings (prices, contact details, site switches). */
export type PublicSettings = {
  /**
   * «إظهار الأسعار للزبائن» (Tareq, 2026-10-16: off for now). While off the API sends customers no price, total or
   * currency (nor the price settings below), and the site shows none: see `pricesShown`.
   */
  show_prices?: boolean;
  price_digital_ils?: string;
  price_softcover_ils?: string;
  price_hardcover_ils?: string;
  delivery_fee_ils?: string;
  /** Calls (the owner's number, +970); WhatsApp is on +972. Digits with a leading "+". */
  support_phone?: string;
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
  /** The free cover (Addendum 9): «شوف غلاف طفلك خلال دقيقة», off by default. */
  free_cover?: boolean;
  family_characters_enabled?: boolean; // the illustrated-family add-on (W4), off by default
  /** A photo kept at the guardian's choice is deleted this many months after its last use (default 12). */
  kept_photo_retention_months?: number;
};

export const getPublicSettings = () => get<PublicSettings>("/api/settings/public", 0);

/**
 * May customers see prices? Only while the admin has `show_prices` on; unknown settings (the API is down) count as
 * off, so a price never shows by mistake. Client components read it with `useShowPrices()` (site/Prices.tsx).
 */
export const pricesShown = (site: Pick<PublicSettings, "show_prices"> | null | undefined): boolean =>
  site?.show_prices === true;

/**
 * A message key, or its `…NoPrice` wording while prices are hidden, when it has one: the same line without
 * prices, quotes or price comparisons («اطلبوا عرض سعر» → «تواصلوا معنا»).
 */
export const priceWording = (key: string, prices: boolean, has: (key: string) => boolean): string =>
  !prices && has(`${key}NoPrice`) ? `${key}NoPrice` : key;

/** Server components: the switch, read from the API (uncached, like the other admin settings). */
export const getPricesShown = async (): Promise<boolean> => pricesShown(await getPublicSettings());

// the contact links live in lib/contact.ts (with the brand's own details as the fallback)
export { displayPhone, telLink, whatsappLink } from "./contact.ts";

/**
 * The book a printed QR names (`/b/QB-7K4M2`): its child's first name and product, or null for a malformed or
 * unknown code (lib/bookCode.ts). Never cached; the visitor's address goes along, so the API's rate limit counts
 * each visitor and not this server.
 */
export const getBookByCode = (raw: string, visitorIp?: string | null) =>
  findBookByCode(raw, async (path) => {
    const res = await fetch(API() + path, {
      cache: "no-store",
      headers: visitorIp ? { "X-Forwarded-For": visitorIp } : undefined,
    });
    return res.ok ? res.json() : null;
  });

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
