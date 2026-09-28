/** Catalog admin (Addendum 4 step 5): the API shapes, the calls and small formatting helpers. */
import { api } from "@/lib/api";

export type Rates = { usd_ils: string; jod_ils: string; margin_floor_pct: string };
export type VariantRow = {
  sku: string;
  product: string;
  product_ar: string;
  product_en: string;
  line: string;
  audience: string;
  options: Record<string, string>;
  active: boolean;
  product_active: boolean;
  price_ils: string | null;
  price_jod: string | null;
  cost_print_ils: string;
  cost_packaging_ils: string;
  cost_handling_ils: string;
  cost_ai_usd: string;
  unit_cost_ils: string;
  margin_ils: string | null;
  margin_pct: string | null;
  margin_pct_jod: string | null;
  below_floor: boolean;
  printer_tiers: boolean;
  printer_estimated: boolean;
};
export type AddOnRow = {
  slug: string;
  name_ar: string;
  name_en: string;
  pricing: "fixed" | "percent_of_item";
  percent: string | null;
  price_ils: string | null;
  price_jod: string | null;
  cost_ils: string;
  cost_ai_usd: string;
  unit_cost_ils: string;
  margin_ils: string | null;
  margin_pct: string | null;
  below_floor: boolean;
  lines: string[];
  included_lines: string[];
  active: boolean;
};
export type ZoneRow = {
  slug: string;
  name_ar: string;
  name_en: string;
  currency: "ILS" | "JOD";
  fee: string;
  free_over: string | null;
  cod_fee: string;
  cost_ils: string;
  fee_margin_ils: string;
  active: boolean;
};
export type CouponRow = {
  code: string;
  kind: "percent" | "fixed";
  value: string;
  currency: "ILS" | "JOD" | null;
  min_subtotal: string | null;
  max_uses: number | null;
  uses: number;
  per_customer: number | null;
  first_order_only: boolean;
  lines: string[];
  starts_at: string | null;
  ends_at: string | null;
  active: boolean;
};
export type OfferRow = {
  id: string;
  kind: string;
  name_ar: string;
  name_en: string;
  discount_pct: string;
  lines: string[];
  starts_at: string | null;
  ends_at: string | null;
  active: boolean;
};
export type CatalogAdmin = {
  rates: Rates;
  variants: VariantRow[];
  addons: AddOnRow[];
  zones: ZoneRow[];
  coupons: CouponRow[];
  bundles: OfferRow[];
  sales: OfferRow[];
};
export type SimResult = {
  currency: "ILS" | "JOD";
  lines: { sku: string; qty: number; unit_price: string; total: string; cost_ils: string }[];
  subtotal: string;
  discount: string;
  shipping: string;
  cod_fee: string;
  total: string;
  total_ils: string;
  cost_ils: string;
  margin_ils: string;
  margin_pct: string | null;
  below_floor: boolean;
  notes: string[];
};

const base = "/api/admin/catalog";
export const catalogAdmin = {
  load: () => api<CatalogAdmin>(base),
  variant: (sku: string, patch: Record<string, unknown>) =>
    api<VariantRow>(`${base}/variants/${encodeURIComponent(sku)}`, { method: "PATCH", json: patch }),
  product: (slug: string, active: boolean) =>
    api<{ slug: string; active: boolean }>(`${base}/products/${encodeURIComponent(slug)}`, {
      method: "PATCH",
      json: { active },
    }),
  addon: (slug: string, patch: Record<string, unknown>) =>
    api<AddOnRow>(`${base}/addons/${encodeURIComponent(slug)}`, { method: "PATCH", json: patch }),
  zone: (slug: string, patch: Record<string, unknown>) =>
    api<ZoneRow>(`${base}/zones/${encodeURIComponent(slug)}`, { method: "PATCH", json: patch }),
  addCoupon: (coupon: Record<string, unknown>) => api<CouponRow>(`${base}/coupons`, { json: coupon }),
  coupon: (code: string, patch: Record<string, unknown>) =>
    api<CouponRow>(`${base}/coupons/${encodeURIComponent(code)}`, { method: "PATCH", json: patch }),
  addSale: (sale: Record<string, unknown>) => api<OfferRow>(`${base}/sales`, { json: sale }),
  sale: (id: string, patch: Record<string, unknown>) =>
    api<OfferRow>(`${base}/sales/${id}`, { method: "PATCH", json: patch }),
  bundle: (slug: string, patch: Record<string, unknown>) =>
    api<OfferRow>(`${base}/bundles/${encodeURIComponent(slug)}`, { method: "PATCH", json: patch }),
  simulate: (body: Record<string, unknown>) => api<SimResult>(`${base}/simulate`, { json: body }),
};

/** "12.50" → "12.5 ₪"; null → "—". Latin digits, as the other admin screens. */
export function ils(v: string | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  return `${Number.isInteger(n) ? n : n.toFixed(2)} ₪`;
}

export function pct(v: string | null | undefined): string {
  return v === null || v === undefined ? "—" : `${Number(v)}%`;
}
