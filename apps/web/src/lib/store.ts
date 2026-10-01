/** The store (Addendum 4): catalog types, the cart API and money formatting. */
import { api } from "@/lib/api";
import { formatAmount } from "@/lib/catalog";

export type Currency = "ILS" | "JOD";

export type CatalogVariant = { sku: string; options: Record<string, string>; price: string | null };
export type CatalogProduct = {
  slug: string;
  line: "classic" | "magic" | "coloring" | "workbook" | "journey" | "family";
  name_ar: string;
  name_en: string;
  description_ar: string;
  description_en: string;
  option_names: string[];
  features: Record<string, unknown>;
  min_qty: number;
  variants: CatalogVariant[];
  from_price: string | null;
};
export type CatalogStyle = {
  slug: string;
  name_ar: string;
  name_en: string;
  lines: string[];
  price_modifier: string;
  sample_images: string[];
};
export type CatalogAddOn = {
  slug: string;
  name_ar: string;
  name_en: string;
  description_ar: string;
  description_en: string;
  image: string | null;
  price: string | null;
  percent: string | null;
  lines: string[];
  included_lines: string[];
  requires: Record<string, string[]>;
  excludes: string[];
  max_qty: number;
  step: string;
};
export type CatalogZone = {
  slug: string;
  name_ar: string;
  name_en: string;
  country: string;
  currency: Currency;
  cities: string[];
  fee: string;
  free_over: string | null;
  cod_fee: string;
  eta_days: [number, number];
};
export type Catalog = {
  currency: Currency;
  products: CatalogProduct[];
  styles: CatalogStyle[];
  addons: CatalogAddOn[];
  zones: CatalogZone[];
};

export type CartAddOn = { slug: string; name_ar: string; name_en: string; qty: number; included: boolean };
export type CartItem = {
  id: string;
  sku: string;
  product: string;
  line: string;
  name_ar: string;
  name_en: string;
  options: Record<string, string>;
  style: string | null;
  theme: string | null;
  qty: number;
  addons: CartAddOn[];
  child_name: string | null;
  child_gender: "m" | "f" | null;
  unit_price: string;
  base: string;
  addons_total: string;
  discount: string;
  total: string;
};
export type Cart = {
  currency: Currency;
  count: number;
  items: CartItem[];
  unavailable: string[];
  subtotal: string;
  sale_discount: string;
  bundle: string | null;
  bundle_discount: string;
  coupon: string | null;
  coupon_code: string | null;
  coupon_problem: string | null;
  coupon_discount: string;
  zone: string | null;
  shipping: string;
  cod_fee: string;
  total: string;
  notes: string[];
};
export type AddOnChoice = { slug: string; qty?: number };
export type CheckoutInput = {
  name: string;
  phone: string;
  zone: string;
  city: string;
  address: string;
  notes?: string;
  accept_terms: boolean;
};
export type Placed = { code: string; status: string; currency: Currency; total: string; eta_days: [number, number] };
export type Tracked = {
  code: string;
  status: string;
  currency: Currency;
  total: string;
  placed_at: string;
  items: { name_ar: string; name_en: string; qty: number; child_name: string | null }[];
  events: { status: string; at: string }[];
  city: string | null;
};

export const ORDER_STEPS = ["new", "confirmed", "generating", "review", "printing", "shipped", "delivered"] as const;

export const cartApi = {
  get: () => api<Cart>("/api/store/cart"),
  update: (id: string, patch: { qty?: number; addons?: AddOnChoice[] }) =>
    api<Cart>(`/api/store/cart/items/${id}`, { method: "PATCH", json: patch }),
  remove: (id: string) => api<Cart>(`/api/store/cart/items/${id}`, { method: "DELETE" }),
  coupon: (code: string) => api<Cart>("/api/store/cart/coupon", { method: "PUT", json: { code } }),
  clearCoupon: () => api<Cart>("/api/store/cart/coupon", { method: "DELETE" }),
  zone: (zone: string) => api<Cart>("/api/store/cart/zone", { method: "PUT", json: { zone } }),
  checkout: (input: CheckoutInput) => api<Placed>("/api/store/checkout", { json: input }),
  track: (code: string, phone: string) =>
    api<Tracked>(`/api/store/orders/${encodeURIComponent(code)}?phone=${encodeURIComponent(phone)}`),
};

/** "69 ₪" / "13 د.أ" (Latin digits for prices, as the design does). */
export function money(amount: string | number, currency: Currency, locale: string): string {
  const value = formatAmount(String(amount));
  if (currency === "JOD") return locale === "ar" ? `${value} د.أ` : `${value} JD`;
  return `${value} ₪`;
}

/** The phone an order was placed with, kept for this tab only so the order page can show its status. */
export const orderPhone = {
  set(code: string, phone: string) {
    try {
      sessionStorage.setItem(`qamra-order-${code}`, phone);
    } catch {
      /* private mode: the tracking form asks for it instead */
    }
  },
  get(code: string): string | null {
    try {
      return sessionStorage.getItem(`qamra-order-${code}`);
    } catch {
      return null;
    }
  },
};
