/** The order path of Addendum 9 (designs AddOns, Cart, Create10): types and calls. Every amount is the server's. */
import { api } from "@/lib/api";
import { ACTIVITY_LINES } from "@/lib/shop";
import type { Cart, CartItem, CatalogAddOn } from "@/lib/store";
import { summarize, type FamilyHeld, type Names, type Summary } from "@/lib/variantSummary";

export type OrderAddOn = CartItem["addons"][number] & { amount: string };
export type OrderItem = Omit<CartItem, "addons"> & {
  addons: OrderAddOn[];
  subtotal: string;
  book_id: string | null;
  child_id: string | null;
  book_title: string | null;
  book_status: string | null;
  // what an activity line prints for the child (docs/plans/order-flows.md chunk 8; optional until the API sends them)
  missing?: string[]; // the line has its child but still lacks "name_en" | "name" (a name its tracing pages can write)
  child_name_en?: string | null; // the name in English letters, where the book prints it
  family?: FamilyHeld | null; // «مغامراتي مع عائلتي»: {name, city, members}
  character_id?: string | null;
};

export type OrderCart = Omit<Cart, "items"> & {
  items: OrderItem[];
  bundle_name_ar: string | null;
  bundle_name_en: string | null;
  bundle_pct: string | null;
  gift: boolean;
  gift_message: string | null;
  gift_card: string | null;
  gift_card_amount: string;
  gift_card_problem: string | null;
};

export type AddOnOffer = {
  slug: string;
  name_ar: string;
  name_en: string;
  description_ar: string;
  description_en: string;
  badge_ar: string | null;
  badge_en: string | null;
  featured: boolean;
  price: string;
  percent: string | null;
  included: boolean;
  on: boolean;
  qty: number;
  max_qty: number;
  needs: string[];
  excludes: string[];
  locked: "needs" | "excludes" | null;
  blockers: string[];
};

export type AddOnsStep = { currency: Cart["currency"]; item: OrderItem; addons: AddOnOffer[] };

export type CrossSell = {
  child_id: string;
  child_name: string;
  gender: "m" | "f";
  character_id: string;
  style: string;
  line: "classic" | "magic";
  product: string;
  name_ar: string;
  name_en: string;
  from_price: string | null;
  currency: Cart["currency"];
};

export const GIFT_MESSAGE_MAX = 200;

export const orderApi = {
  cart: () => api<OrderCart>("/api/store/cart"),
  remove: (id: string) => api<OrderCart>(`/api/store/cart/items/${id}`, { method: "DELETE" }),
  addons: (itemId: string) => api<AddOnsStep>(`/api/store/cart/items/${itemId}/addons`),
  setAddons: (itemId: string, slugs: string[]) =>
    api<AddOnsStep>(`/api/store/cart/items/${itemId}/addons`, {
      method: "PUT",
      json: { addons: slugs.map((slug) => ({ slug })) },
    }),
  gift: (gift: boolean, message?: string) =>
    api<OrderCart>("/api/store/cart/gift", { method: "PUT", json: { gift, message } }),
  code: (code: string) => api<OrderCart>("/api/store/cart/code", { method: "PUT", json: { code } }),
  clearCoupon: () => api<OrderCart>("/api/store/cart/coupon", { method: "DELETE" }),
  clearGiftCard: () => api<OrderCart>("/api/store/cart/gift-card", { method: "DELETE" }),
  zone: (zone: string) => api<OrderCart>("/api/store/cart/zone", { method: "PUT", json: { zone } }),
  crossSell: () => api<CrossSell[]>("/api/store/cart/cross-sell"),
};

/** Turning an add-on on brings what it needs (transitively); turning one off drops what depends on it. */
export function toggleAddOn(offers: AddOnOffer[], on: Set<string>, slug: string): Set<string> {
  const by = new Map(offers.map((o) => [o.slug, o]));
  const needs = (s: string, seen = new Set<string>()): Set<string> => {
    if (seen.has(s)) return seen;
    seen.add(s);
    for (const n of by.get(s)?.needs ?? []) needs(n, seen);
    return seen;
  };
  const next = new Set(on);
  if (!on.has(slug)) {
    for (const s of needs(slug)) if (by.has(s)) next.add(s);
    return next;
  }
  next.delete(slug);
  let changed = true;
  while (changed) {
    changed = false;
    for (const s of [...next]) {
      if ((by.get(s)?.needs ?? []).some((n) => !next.has(n))) {
        next.delete(s);
        changed = true;
      }
    }
  }
  return next;
}

/** "باقة الإخوة −20%" → "باقة الإخوة": the cart shows the percent itself. */
export function bundleLabel(name: string): string {
  return name.replace(/\s*[−-]\s*\d+(\.\d+)?\s*%\s*$/u, "").trim();
}

/**
 * Whether a cart line is an activity book. The lines come from `ACTIVITY_LINES` (lib/shop.ts), the one list the
 * site keeps (the API's is `store/workbooks.py` ACTIVITY): a copy here once left «قلبي يعرف الله» out, and its
 * «أكملوا بيانات الطفل» ran the story flow, which the API then refused.
 */
export function isActivity(item: { line?: string | null }): boolean {
  return (ACTIVITY_LINES as readonly string[]).includes(item.line ?? "");
}

/** What a line will print, the same in the cart, the checkout and the order page (lib/variantSummary.ts). */
export function lineSummary(item: Parameters<typeof summarize>[0], names: Names): Summary {
  return summarize(item, isActivity(item) ? "activity" : "story", names);
}

/**
 * «أكملوا بيانات الطفل»: the create flow for a line that still waits, with what the product page chose. When the
 * flow ends it fills this line (`item`), and a child's approved character is reused.
 * - An activity book opens its own flow by its product (`product=<sku>`): never a story line, theme or style.
 *   A line that has its child but lacks something the book prints (the English name) opens on that child.
 * - A story keeps its line, story, style and format from the story page.
 */
export function completeHref(item: OrderItem): string {
  const q = new URLSearchParams({ item: item.id });
  if (isActivity(item)) {
    q.set("product", item.sku);
    if (item.child_id) q.set("child", item.child_id);
  } else {
    if (item.line === "classic" || item.line === "magic") q.set("line", item.line);
    if (item.theme) q.set("theme", item.theme);
    if (item.style) q.set("style", item.style);
    if (item.options.format) q.set("format", item.options.format);
  }
  return `/create?${q.toString()}`;
}

/**
 * «تعديل» on a line: an activity book opens its review step for this very line (name as printed, English name,
 * family, character), which saves back into the same line, so nothing given before is lost; a story book opens
 * its add-ons step.
 */
export function editHref(item: OrderItem): string {
  if (isActivity(item)) {
    const q = new URLSearchParams({ step: "summary", product: item.sku, item: item.id });
    if (item.child_id) q.set("child", item.child_id);
    return `/create?${q.toString()}`;
  }
  if (item.book_id && item.child_id) {
    return `/create?step=addons&child=${item.child_id}&book=${item.book_id}`;
  }
  return "/stories";
}

const AFTER_PREVIEW = ["format", "checkout"]; // the steps whose add-ons a line's add-ons step offers (API store/addons.py)
const AUTOMATIC = ["digital-copy"]; // added by the server to every printed book

/**
 * The add-ons the line's add-ons step will offer, from the catalog (active add-ons only) and the same rules as
 * the API (`store/addons.py` `managed`): the line and its format (`lines`, `requires`). The cart uses it to know
 * whether a line has any before it asks the server for the offers themselves.
 */
export function offeredAddOns(addons: CatalogAddOn[], item: Pick<OrderItem, "line" | "options">): CatalogAddOn[] {
  return addons.filter(
    (a) =>
      AFTER_PREVIEW.includes(a.step) &&
      !AUTOMATIC.includes(a.slug) &&
      (a.lines.includes(item.line) || a.included_lines.includes(item.line)) &&
      Object.entries(a.requires).every(([option, allowed]) => allowed.includes(item.options[option] ?? "")),
  );
}
