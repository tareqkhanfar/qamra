/** The order path of Addendum 9 (designs AddOns, Cart, Create10): types and calls. Every amount is the server's. */
import { api } from "@/lib/api";
import type { Cart, CartItem } from "@/lib/store";

export type OrderAddOn = CartItem["addons"][number] & { amount: string };
export type OrderItem = Omit<CartItem, "addons"> & {
  addons: OrderAddOn[];
  subtotal: string;
  book_id: string | null;
  child_id: string | null;
  book_title: string | null;
  book_status: string | null;
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

/** Where "edit" goes for a line: the add-ons step for a book, the product page for an activity book. */
export function editHref(item: OrderItem): string {
  if (item.book_id && item.child_id) {
    return `/create?step=addons&child=${item.child_id}&book=${item.book_id}`;
  }
  return ["workbook", "journey", "family"].includes(item.line) ? `/workbooks/${item.product}` : "/shop";
}
