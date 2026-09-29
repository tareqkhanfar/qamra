"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { catalogAdmin, type CatalogAdmin, type CouponRow, type OfferRow } from "@/lib/catalogAdmin";
import { BundleRules } from "./OrderPathAdmin";
import { ActiveToggle, MoneyInput } from "./parts";

const day = (iso: string | null) => (iso ? iso.slice(0, 10) : "—");
const input =
  "min-h-10 rounded-sm border border-line bg-white px-2 text-small outline-none focus:border-night-900 focus:ring-2 focus:ring-night-100";

/** Coupons, seasonal sales and bundles: create, switch off, adjust the discount. */
export function OffersPanel({ data, onChange }: { data: CatalogAdmin; onChange: (d: CatalogAdmin) => void }) {
  const t = useTranslations("catalogAdmin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [coupon, setCoupon] = useState({ code: "", kind: "percent", value: "", currency: "ILS", max_uses: "" });
  const [sale, setSale] = useState({
    name_ar: "",
    name_en: "",
    discount_pct: "",
    line: "",
    starts_at: "",
    ends_at: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const name = (r: { name_ar: string; name_en: string }) => (locale === "ar" ? r.name_ar : r.name_en);
  const replaceCoupon = (c: CouponRow) =>
    onChange({ ...data, coupons: data.coupons.map((x) => (x.code === c.code ? c : x)) });
  const replaceOffer = (key: "sales" | "bundles", o: OfferRow) =>
    onChange({ ...data, [key]: data[key].map((x) => (x.id === o.id ? o : x)) });

  async function addCoupon() {
    setBusy("coupon");
    setError(null);
    const r = await catalogAdmin.addCoupon({
      code: coupon.code.trim(),
      kind: coupon.kind,
      value: coupon.value.trim(),
      currency: coupon.kind === "fixed" ? coupon.currency : null,
      max_uses: coupon.max_uses.trim() ? Number(coupon.max_uses) : null,
    });
    setBusy(null);
    if (!r.ok) return setError(errorText(r.error, locale, te("unknown")));
    onChange({ ...data, coupons: [r.data, ...data.coupons] });
    setCoupon({ code: "", kind: "percent", value: "", currency: "ILS", max_uses: "" });
  }

  async function addSale() {
    setBusy("sale");
    setError(null);
    const r = await catalogAdmin.addSale({
      name_ar: sale.name_ar.trim(),
      name_en: sale.name_en.trim(),
      discount_pct: sale.discount_pct.trim(),
      lines: sale.line ? [sale.line] : [],
      starts_at: sale.starts_at ? new Date(sale.starts_at).toISOString() : null,
      ends_at: sale.ends_at ? new Date(`${sale.ends_at}T23:59:00`).toISOString() : null,
    });
    setBusy(null);
    if (!r.ok) return setError(errorText(r.error, locale, te("unknown")));
    onChange({ ...data, sales: [r.data, ...data.sales] });
    setSale({ name_ar: "", name_en: "", discount_pct: "", line: "", starts_at: "", ends_at: "" });
  }

  const lines = [...new Set(data.variants.map((v) => v.line))];
  return (
    <div className="flex flex-col gap-8">
      {error && <Alert>{error}</Alert>}

      <section className="flex flex-col gap-3">
        <h3 className="text-h3 text-night-900">{t("coupons")}</h3>
        <form
          className="flex flex-wrap items-end gap-2 rounded-lg border border-line bg-paper-raised p-3"
          onSubmit={(e) => {
            e.preventDefault();
            void addCoupon();
          }}
        >
          <input
            id="coupon-code"
            aria-label={t("couponCode")}
            placeholder={t("couponCode")}
            dir="ltr"
            value={coupon.code}
            onChange={(e) => setCoupon((c) => ({ ...c, code: e.target.value.toUpperCase() }))}
            className={`${input} w-36`}
          />
          <select
            id="coupon-kind"
            aria-label={t("couponKind")}
            value={coupon.kind}
            onChange={(e) => setCoupon((c) => ({ ...c, kind: e.target.value }))}
            className={input}
          >
            <option value="percent">{t("percent")}</option>
            <option value="fixed">{t("fixed")}</option>
          </select>
          <MoneyInput
            label={t("couponValue")}
            placeholder={coupon.kind === "percent" ? "%" : t("amount")}
            value={coupon.value}
            onChange={(e) => setCoupon((c) => ({ ...c, value: e.target.value }))}
          />
          {coupon.kind === "fixed" && (
            <select
              id="coupon-currency"
              aria-label={t("currency")}
              value={coupon.currency}
              onChange={(e) => setCoupon((c) => ({ ...c, currency: e.target.value }))}
              className={input}
            >
              <option value="ILS">₪</option>
              <option value="JOD">JD</option>
            </select>
          )}
          <MoneyInput
            label={t("maxUses")}
            placeholder={t("maxUses")}
            value={coupon.max_uses}
            onChange={(e) => setCoupon((c) => ({ ...c, max_uses: e.target.value }))}
          />
          <Button size="sm" type="submit" loading={busy === "coupon"} disabled={!coupon.code || !coupon.value}>
            {t("addCoupon")}
          </Button>
        </form>
        <ul className="flex flex-col divide-y divide-line rounded-lg border border-line bg-paper-raised">
          {data.coupons.map((c) => (
            <li key={c.code} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-small">
              <span className="flex flex-wrap items-center gap-2">
                <code dir="ltr" className="font-bold">
                  {c.code}
                </code>
                <span>
                  {c.kind === "percent"
                    ? `${Number(c.value)}%`
                    : `${Number(c.value)} ${c.currency === "JOD" ? "JD" : "₪"}`}
                </span>
                <span className="text-caption text-ink-muted">
                  {t("used", { uses: c.uses, max: c.max_uses ?? "∞" })} · {day(c.starts_at)} → {day(c.ends_at)}
                </span>
              </span>
              <ActiveToggle
                on={c.active}
                label={t("active")}
                onChange={async (v) => {
                  const r = await catalogAdmin.coupon(c.code, { active: v });
                  if (r.ok) replaceCoupon(r.data);
                }}
              />
            </li>
          ))}
          {!data.coupons.length && <li className="px-3 py-3 text-small text-ink-muted">{t("none")}</li>}
        </ul>
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="text-h3 text-night-900">{t("sales")}</h3>
        <form
          className="flex flex-wrap items-end gap-2 rounded-lg border border-line bg-paper-raised p-3"
          onSubmit={(e) => {
            e.preventDefault();
            void addSale();
          }}
        >
          <input
            id="sale-ar"
            aria-label={t("nameAr")}
            placeholder={t("nameAr")}
            value={sale.name_ar}
            onChange={(e) => setSale((s) => ({ ...s, name_ar: e.target.value }))}
            className={`${input} w-40`}
          />
          <input
            id="sale-en"
            aria-label={t("nameEn")}
            placeholder={t("nameEn")}
            dir="ltr"
            value={sale.name_en}
            onChange={(e) => setSale((s) => ({ ...s, name_en: e.target.value }))}
            className={`${input} w-40`}
          />
          <MoneyInput
            label={t("discountPct")}
            placeholder="%"
            value={sale.discount_pct}
            onChange={(e) => setSale((s) => ({ ...s, discount_pct: e.target.value }))}
          />
          <select
            id="sale-line"
            aria-label={t("line")}
            value={sale.line}
            onChange={(e) => setSale((s) => ({ ...s, line: e.target.value }))}
            className={input}
          >
            <option value="">{t("allLines")}</option>
            {lines.map((l) => (
              <option key={l} value={l}>
                {t(`lines.${l}`)}
              </option>
            ))}
          </select>
          <input
            id="sale-from"
            type="date"
            aria-label={t("from")}
            value={sale.starts_at}
            onChange={(e) => setSale((s) => ({ ...s, starts_at: e.target.value }))}
            className={input}
          />
          <input
            id="sale-to"
            type="date"
            aria-label={t("to")}
            value={sale.ends_at}
            onChange={(e) => setSale((s) => ({ ...s, ends_at: e.target.value }))}
            className={input}
          />
          <Button
            size="sm"
            type="submit"
            loading={busy === "sale"}
            disabled={!sale.name_ar || !sale.discount_pct || !sale.starts_at || !sale.ends_at}
          >
            {t("addSale")}
          </Button>
        </form>
        <OfferList
          rows={data.sales}
          name={name}
          onToggle={async (o, v) => {
            const r = await catalogAdmin.sale(o.id, { active: v });
            if (r.ok) replaceOffer("sales", r.data);
          }}
        />
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="text-h3 text-night-900">{t("bundles")}</h3>
        <BundleRules rows={data.bundles} onRow={(o) => replaceOffer("bundles", o)} />
      </section>
    </div>
  );
}

function OfferList({
  rows,
  name,
  onToggle,
}: {
  rows: OfferRow[];
  name: (r: OfferRow) => string;
  onToggle: (o: OfferRow, v: boolean) => void;
}) {
  const t = useTranslations("catalogAdmin");
  return (
    <ul className="flex flex-col divide-y divide-line rounded-lg border border-line bg-paper-raised">
      {rows.map((o) => (
        <li key={o.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-small">
          <span className="flex flex-wrap items-center gap-2">
            <strong>{name(o)}</strong>
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-caption font-bold text-amber-700">
              −{Number(o.discount_pct)}%
            </span>
            <span className="text-caption text-ink-muted">
              {o.lines.length ? o.lines.map((l) => t(`lines.${l}`)).join("، ") : t("allLines")}
              {(o.starts_at || o.ends_at) && ` · ${day(o.starts_at)} → ${day(o.ends_at)}`}
            </span>
          </span>
          <ActiveToggle on={o.active} label={t("active")} onChange={(v) => onToggle(o, v)} />
        </li>
      ))}
      {!rows.length && <li className="px-3 py-3 text-small text-ink-muted">{t("none")}</li>}
    </ul>
  );
}
