"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { catalogAdmin, ils, pct, type CatalogAdmin, type SimResult } from "@/lib/catalogAdmin";
import { MarginBadge } from "./parts";

type Line = { sku: string; qty: string; addons: string[] };
const input =
  "min-h-10 rounded-sm border border-line bg-white px-2 text-small outline-none focus:border-night-900 focus:ring-2 focus:ring-night-100";

/** "What if": a basket through the store's own pricing engine, with our cost and margin. */
export function PriceSimulator({ data }: { data: CatalogAdmin }) {
  const t = useTranslations("catalogAdmin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [lines, setLines] = useState<Line[]>([{ sku: data.variants[0]?.sku ?? "", qty: "1", addons: [] }]);
  const [zone, setZone] = useState("");
  const [coupon, setCoupon] = useState("");
  const [currency, setCurrency] = useState<"ILS" | "JOD">("ILS");
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const addonsFor = (sku: string) => {
    const line = data.variants.find((v) => v.sku === sku)?.line;
    return data.addons.filter((a) => a.active && line && a.lines.includes(line));
  };

  async function run() {
    setBusy(true);
    setError(null);
    const r = await catalogAdmin.simulate({
      currency,
      zone: zone || null,
      coupon: coupon.trim() || null,
      items: lines
        .filter((l) => l.sku)
        .map((l) => ({ sku: l.sku, qty: Math.max(1, Number(l.qty) || 1), addons: l.addons.map((slug) => ({ slug })) })),
    });
    setBusy(false);
    if (r.ok) setResult(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }

  const money = (v: string) => (result?.currency === "JOD" ? `${Number(v)} JD` : ils(v));
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]">
      <form
        className="flex flex-col gap-3 rounded-lg border border-line bg-paper-raised p-4"
        onSubmit={(e) => {
          e.preventDefault();
          void run();
        }}
      >
        {lines.map((l, i) => (
          <fieldset key={i} className="flex flex-col gap-2 border-b border-line pb-3">
            <legend className="sr-only">{t("line")}</legend>
            <div className="flex flex-wrap gap-2">
              <select
                id={`sim-sku-${i}`}
                aria-label={t("variant")}
                value={l.sku}
                onChange={(e) =>
                  setLines((ls) => ls.map((x, j) => (j === i ? { ...x, sku: e.target.value, addons: [] } : x)))
                }
                className={`${input} min-w-0 grow`}
              >
                {data.variants.map((v) => (
                  <option key={v.sku} value={v.sku}>
                    {(locale === "ar" ? v.product_ar : v.product_en) + " · " + Object.values(v.options).join(" · ")}
                  </option>
                ))}
              </select>
              <input
                id={`sim-qty-${i}`}
                aria-label={t("qty")}
                inputMode="numeric"
                dir="ltr"
                value={l.qty}
                onChange={(e) => setLines((ls) => ls.map((x, j) => (j === i ? { ...x, qty: e.target.value } : x)))}
                className={`${input} w-16`}
              />
              {lines.length > 1 && (
                <button
                  type="button"
                  aria-label={t("remove")}
                  onClick={() => setLines((ls) => ls.filter((_, j) => j !== i))}
                  className="size-10 rounded-full hover:bg-paper-sunk"
                >
                  ✕
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {addonsFor(l.sku).map((a) => (
                <label key={a.slug} className="flex items-center gap-1.5 text-caption">
                  <input
                    type="checkbox"
                    checked={l.addons.includes(a.slug)}
                    onChange={(e) =>
                      setLines((ls) =>
                        ls.map((x, j) =>
                          j === i
                            ? {
                                ...x,
                                addons: e.target.checked ? [...x.addons, a.slug] : x.addons.filter((s) => s !== a.slug),
                              }
                            : x,
                        ),
                      )
                    }
                  />
                  {locale === "ar" ? a.name_ar : a.name_en}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="self-start"
          onClick={() => setLines((ls) => [...ls, { sku: data.variants[0]?.sku ?? "", qty: "1", addons: [] }])}
        >
          {t("addLine")}
        </Button>
        <div className="flex flex-wrap gap-2">
          <select
            id="sim-currency"
            aria-label={t("currency")}
            value={currency}
            onChange={(e) => setCurrency(e.target.value as "ILS" | "JOD")}
            className={input}
          >
            <option value="ILS">₪</option>
            <option value="JOD">JD</option>
          </select>
          <select
            id="sim-zone"
            aria-label={t("zone")}
            value={zone}
            onChange={(e) => setZone(e.target.value)}
            className={input}
          >
            <option value="">{t("noDelivery")}</option>
            {data.zones
              .filter((z) => z.currency === currency)
              .map((z) => (
                <option key={z.slug} value={z.slug}>
                  {locale === "ar" ? z.name_ar : z.name_en}
                </option>
              ))}
          </select>
          <input
            id="sim-coupon"
            aria-label={t("couponCode")}
            placeholder={t("couponCode")}
            dir="ltr"
            value={coupon}
            onChange={(e) => setCoupon(e.target.value.toUpperCase())}
            className={`${input} w-32`}
          />
        </div>
        <Button type="submit" loading={busy} className="self-start">
          {t("simulate")}
        </Button>
        {error && <Alert>{error}</Alert>}
      </form>

      {result && (
        <section
          className="flex flex-col gap-2 rounded-lg border border-line bg-paper-raised p-4 text-small"
          aria-live="polite"
        >
          <h3 className="text-body font-bold">{t("result")}</h3>
          {result.lines.map((l, i) => (
            <div key={i} className="flex justify-between gap-2">
              <span dir="ltr">
                {l.sku} × {l.qty}
              </span>
              <span className="tabular-nums">{money(l.total)}</span>
            </div>
          ))}
          <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 border-t border-line pt-2 tabular-nums">
            <dt>{t("subtotal")}</dt>
            <dd>{money(result.subtotal)}</dd>
            <dt>{t("discount")}</dt>
            <dd>{money(result.discount)}</dd>
            <dt>{t("shipping")}</dt>
            <dd>{money(result.shipping)}</dd>
            <dt>{t("codFee")}</dt>
            <dd>{money(result.cod_fee)}</dd>
            <dt className="font-bold">{t("total")}</dt>
            <dd className="font-bold">{money(result.total)}</dd>
            <dt>{t("ourCost")}</dt>
            <dd>{ils(result.cost_ils)}</dd>
            <dt>{t("marginIls")}</dt>
            <dd>{ils(result.margin_ils)}</dd>
            <dt>{t("marginPct")}</dt>
            <dd>
              <MarginBadge value={result.margin_pct} low={result.below_floor} />
            </dd>
          </dl>
          {result.below_floor && <Alert>{t("belowFloorBasket", { floor: pct(data.rates.margin_floor_pct) })}</Alert>}
          {result.notes.map((n) => (
            <p key={n} className="text-caption text-ink-muted" dir="ltr">
              {n}
            </p>
          ))}
        </section>
      )}
    </div>
  );
}
