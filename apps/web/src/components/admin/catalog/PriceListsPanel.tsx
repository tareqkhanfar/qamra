"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, errorText, type ApiResult } from "@/lib/api";
import type { VariantRow } from "@/lib/catalogAdmin";

type Tier = { min_qty: number; unit_price: string };
type Item = {
  sku: string;
  product_ar: string;
  product_en: string;
  tiers: Tier[];
  retail: string | null;
  unit_cost_ils: string;
  margin_pct: (string | null)[];
  below_floor: boolean;
};
type PriceList = {
  id: string;
  name: string;
  currency: "ILS" | "JOD";
  organization_id: string | null;
  organization: string | null;
  active: boolean;
  items: Item[];
};
type Data = { lists: PriceList[]; variants: VariantRow[]; organizations: { id: string; name: string }[] };
const BASE = "/api/admin/catalog/price-lists";

/** B2B price lists (Addendum 4 §5): wholesale tiers per variant, a default list and one per kindergarten. */
export function PriceListsPanel() {
  const t = useTranslations("portal.priceLists");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", organization_id: "", currency: "ILS", copy: true });

  useEffect(() => {
    void (async () => {
      const r = await api<Data>(BASE);
      if (r.ok) setData(r.data);
      else setError(errorText(r.error, locale, te("unknown")));
    })();
  }, [locale, te]);

  async function change(run: () => Promise<ApiResult<PriceList>>) {
    setError(null);
    const r = await run();
    if (r.ok)
      setData(
        (d) =>
          d && {
            ...d,
            lists: d.lists.some((l) => l.id === r.data.id)
              ? d.lists.map((l) => (l.id === r.data.id ? r.data : l))
              : [...d.lists, r.data],
          },
      );
    else setError(errorText(r.error, locale, te("unknown")));
  }

  if (!data) return error ? <Alert>{error}</Alert> : <p className="text-ink-muted">{t("loading")}</p>;
  const fallback = data.lists.find((l) => l.organization_id === null && l.currency === draft.currency);
  return (
    <div className="flex flex-col gap-5">
      <p className="max-w-3xl text-body text-ink-muted">{t("intro")}</p>
      {error && <Alert>{error}</Alert>}
      {data.lists.map((pl) => (
        <ListCard key={pl.id} list={pl} variants={data.variants} onChange={change} />
      ))}
      <form
        className="flex flex-col gap-3 rounded-lg border border-dashed border-line p-4"
        onSubmit={(e) => {
          e.preventDefault();
          void change(() =>
            api<PriceList>(BASE, {
              json: {
                name: draft.name,
                currency: draft.currency,
                organization_id: draft.organization_id || null,
                copy_from: draft.copy && fallback ? fallback.id : null,
              },
            }),
          );
        }}
      >
        <strong>{t("new")}</strong>
        <div className="grid gap-3 md:grid-cols-3">
          <input
            aria-label={t("name")}
            placeholder={t("name")}
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            required
            minLength={2}
            className="min-h-11 rounded-sm border border-line bg-paper-raised px-3"
          />
          <select
            aria-label={t("organization")}
            value={draft.organization_id}
            onChange={(e) => setDraft({ ...draft, organization_id: e.target.value })}
            className="min-h-11 rounded-sm border border-line bg-paper-raised px-3"
          >
            <option value="">{t("defaultList")}</option>
            {data.organizations.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
          <select
            aria-label={t("currency")}
            value={draft.currency}
            onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
            className="min-h-11 rounded-sm border border-line bg-paper-raised px-3"
          >
            <option value="ILS">₪ ILS</option>
            <option value="JOD">JD</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-small">
          <input
            type="checkbox"
            checked={draft.copy}
            onChange={(e) => setDraft({ ...draft, copy: e.target.checked })}
            className="size-5 accent-night-900"
          />
          {t("copyDefault")}
        </label>
        <Button type="submit" size="sm" className="self-start">
          {t("create")}
        </Button>
      </form>
    </div>
  );
}

function ListCard({
  list,
  variants,
  onChange,
}: {
  list: PriceList;
  variants: VariantRow[];
  onChange: (run: () => Promise<ApiResult<PriceList>>) => Promise<void>;
}) {
  const t = useTranslations("portal.priceLists");
  const locale = useLocale();
  const [adding, setAdding] = useState("");
  const unpriced = variants.filter((v) => !list.items.some((i) => i.sku === v.sku));
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-line bg-paper-raised p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-col">
          <strong className="text-body-l">{list.name}</strong>
          <span className="text-caption text-ink-muted">
            {list.organization ?? t("defaultList")} · {list.currency}
          </span>
        </div>
        <label className="flex items-center gap-2 text-small">
          <input
            type="checkbox"
            checked={list.active}
            onChange={(e) =>
              void onChange(() =>
                api<PriceList>(`${BASE}/${list.id}`, { method: "PATCH", json: { active: e.target.checked } }),
              )
            }
            className="size-5 accent-night-900"
          />
          {t("active")}
        </label>
      </div>
      {list.items.map((item) => (
        <ItemRow key={item.sku} list={list} item={item} onChange={onChange} />
      ))}
      {unpriced.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label={t("addVariant")}
            value={adding}
            onChange={(e) => setAdding(e.target.value)}
            className="min-h-11 rounded-sm border border-line bg-paper px-3 text-small"
          >
            <option value="">{t("addVariant")}</option>
            {unpriced.map((v) => (
              <option key={v.sku} value={v.sku}>
                {locale === "ar" ? v.product_ar : v.product_en} ({v.sku})
              </option>
            ))}
          </select>
          <Button
            size="sm"
            variant="secondary"
            disabled={!adding}
            onClick={() =>
              void onChange(() =>
                api<PriceList>(`${BASE}/${list.id}/items/${adding}`, {
                  method: "PUT",
                  json: { tiers: [{ min_qty: 1, unit_price: "1.00" }] },
                }),
              )
            }
          >
            {t("add")}
          </Button>
        </div>
      )}
    </section>
  );
}

function ItemRow({
  list,
  item,
  onChange,
}: {
  list: PriceList;
  item: Item;
  onChange: (run: () => Promise<ApiResult<PriceList>>) => Promise<void>;
}) {
  const t = useTranslations("portal.priceLists");
  const locale = useLocale();
  const [tiers, setTiers] = useState<Tier[]>(item.tiers);
  const url = `${BASE}/${list.id}/items/${item.sku}`;
  const set = (i: number, patch: Partial<Tier>) => setTiers((l) => l.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  return (
    <div className={`flex flex-col gap-2 rounded-md border p-3 ${item.below_floor ? "border-danger" : "border-line"}`}>
      <div className="flex flex-wrap justify-between gap-2 text-small">
        <strong>
          {locale === "ar" ? item.product_ar : item.product_en}{" "}
          <span className="font-normal text-ink-muted" dir="ltr">
            {item.sku}
          </span>
        </strong>
        <span className="text-ink-muted">
          {t("retailCost", { retail: item.retail ?? "—", cost: item.unit_cost_ils })}
        </span>
      </div>
      {tiers.map((tier, i) => (
        <div key={i} className="flex flex-wrap items-center gap-2 text-small">
          <label className="flex items-center gap-1">
            {t("from")}
            <input
              type="number"
              min={1}
              value={tier.min_qty}
              onChange={(e) => set(i, { min_qty: Number(e.target.value) })}
              className="min-h-10 w-20 rounded-sm border border-line px-2"
            />
          </label>
          <label className="flex items-center gap-1">
            {t("price")}
            <input
              type="number"
              min={0.01}
              step="0.01"
              value={tier.unit_price}
              onChange={(e) => set(i, { unit_price: e.target.value })}
              className="min-h-10 w-24 rounded-sm border border-line px-2"
            />
          </label>
          {item.margin_pct[i] !== undefined && (
            <span className={Number(item.margin_pct[i]) < 0 || item.below_floor ? "text-danger" : "text-success"}>
              {t("margin", { pct: item.margin_pct[i] ?? "—" })}
            </span>
          )}
          <button
            type="button"
            aria-label={t("removeTier")}
            onClick={() => setTiers((l) => l.filter((_, j) => j !== i))}
            className="size-9 text-ink-muted"
            disabled={tiers.length === 1}
          >
            ×
          </button>
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            setTiers((l) => [
              ...l,
              { min_qty: (l.at(-1)?.min_qty ?? 0) + 10, unit_price: l.at(-1)?.unit_price ?? "1.00" },
            ])
          }
        >
          {t("addTier")}
        </Button>
        <Button size="sm" onClick={() => void onChange(() => api<PriceList>(url, { method: "PUT", json: { tiers } }))}>
          {t("save")}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => void onChange(() => api<PriceList>(url, { method: "DELETE" }))}
        >
          {t("removeItem")}
        </Button>
      </div>
    </div>
  );
}
