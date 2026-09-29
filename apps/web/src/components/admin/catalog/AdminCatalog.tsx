"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { errorText } from "@/lib/api";
import { catalogAdmin, pct, type CatalogAdmin } from "@/lib/catalogAdmin";
import { AddOnsTable } from "./AddOnsTable";
import { OffersPanel } from "./OffersPanel";
import { PriceSimulator } from "./PriceSimulator";
import { VariantsTable } from "./VariantsTable";
import { QuizRules } from "./QuizRules";
import { PriceListsPanel } from "./PriceListsPanel";
import { ZonesTable } from "./ZonesTable";

const TABS = ["products", "addons", "zones", "offers", "simulator", "quiz", "priceLists"] as const;
type Tab = (typeof TABS)[number];

/** Catalog admin (Addendum 4 step 5): prices, costs and margins, offers, and the price simulator. */
export function AdminCatalog() {
  const t = useTranslations("catalogAdmin");
  const tq = useTranslations("quiz.admin");
  const tpl = useTranslations("portal.priceLists");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [data, setData] = useState<CatalogAdmin | null>(null);
  const [tab, setTab] = useState<Tab>("products");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await catalogAdmin.load();
      if (r.ok) setData(r.data);
      else setError(errorText(r.error, locale, te("unknown")));
    })();
  }, [locale, te]);

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <p className="text-ink-muted">{t("loading")}</p>;
  const floor = Number(data.rates.margin_floor_pct);
  const low = data.variants.filter((v) => v.below_floor).length + data.addons.filter((a) => a.below_floor).length;

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-2">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <p className="max-w-3xl text-body text-ink-muted">
          {t("intro", {
            floor: pct(data.rates.margin_floor_pct),
            usd: Number(data.rates.usd_ils),
            jod: Number(data.rates.jod_ils),
          })}
        </p>
        {low > 0 && <Alert>{t("lowCount", { n: low, floor: pct(data.rates.margin_floor_pct) })}</Alert>}
      </header>
      <div role="tablist" className="flex gap-1 overflow-x-auto border-b border-line">
        {TABS.map((id) => (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`min-h-11 border-b-[3px] px-3.5 whitespace-nowrap ${tab === id ? "border-amber-500 font-bold text-night-900" : "border-transparent text-ink-muted"}`}
          >
            {id === "quiz" ? tq("tab") : id === "priceLists" ? tpl("tab") : t(`tabs.${id}`)}
          </button>
        ))}
      </div>
      {tab === "products" && (
        <VariantsTable
          rows={data.variants}
          floor={floor}
          onRow={(r) => setData({ ...data, variants: data.variants.map((v) => (v.sku === r.sku ? r : v)) })}
          onProduct={async (slug, active) => {
            const r = await catalogAdmin.product(slug, active);
            if (r.ok)
              setData({
                ...data,
                variants: data.variants.map((v) => (v.product === slug ? { ...v, product_active: active } : v)),
              });
          }}
        />
      )}
      {tab === "addons" && (
        <AddOnsTable
          rows={data.addons}
          floor={floor}
          onRow={(r) => setData({ ...data, addons: data.addons.map((a) => (a.slug === r.slug ? r : a)) })}
        />
      )}
      {tab === "zones" && (
        <ZonesTable
          rows={data.zones}
          onRow={(r) => setData({ ...data, zones: data.zones.map((z) => (z.slug === r.slug ? r : z)) })}
        />
      )}
      {tab === "offers" && <OffersPanel data={data} onChange={setData} />}
      {tab === "simulator" && <PriceSimulator data={data} />}
      {tab === "priceLists" && <PriceListsPanel />}
      {tab === "quiz" && (
        <QuizRules
          products={[
            ...new Map(data.variants.map((v) => [v.product, locale === "ar" ? v.product_ar : v.product_en])),
          ].map(([slug, name]) => ({ slug, name }))}
        />
      )}
    </div>
  );
}
