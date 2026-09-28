"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { catalogAdmin, ils, type VariantRow } from "@/lib/catalogAdmin";
import { ActiveToggle, MarginBadge, MoneyInput, changed } from "./parts";

const FIELDS = [
  "price_ils",
  "price_jod",
  "cost_print_ils",
  "cost_packaging_ils",
  "cost_handling_ils",
  "cost_ai_usd",
] as const;

function Row({ row, floor, onSaved }: { row: VariantRow; floor: number; onSaved: (r: VariantRow) => void }) {
  const t = useTranslations("catalogAdmin");
  const te = useTranslations("errors");
  const tf = useTranslations("store.formats");
  const locale = useLocale();
  const [draft, setDraft] = useState<Record<string, string>>(() =>
    Object.fromEntries(FIELDS.map((f) => [f, row[f] ?? ""])),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const diff = changed(draft, row);

  async function save(patch: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    const r = await catalogAdmin.variant(row.sku, patch);
    setBusy(false);
    if (r.ok) onSaved(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }

  const options = Object.entries(row.options)
    .map(([k, v]) => (k === "format" && tf.has(v) ? tf(v) : v))
    .join(" · ");
  return (
    <tr className={`border-b border-line/60 align-top ${row.below_floor ? "bg-danger-bg/40" : ""}`}>
      <td className="px-2 py-2">
        <div className="font-semibold">{options || row.sku}</div>
        <code className="text-caption text-ink-muted" dir="ltr">
          {row.sku}
        </code>
        {row.printer_tiers && (
          <Link href="/admin/print-costs" className="mt-1 block text-caption font-semibold text-amber-700 underline">
            {row.printer_estimated ? `⚠ ${t("printerEstimated")}` : t("printerTiers")}
          </Link>
        )}
      </td>
      {FIELDS.map((f) => (
        <td key={f} className="px-1 py-2">
          <MoneyInput
            label={t(`fields.${f}`)}
            value={draft[f]}
            onChange={(e) => setDraft((d) => ({ ...d, [f]: e.target.value }))}
          />
        </td>
      ))}
      <td className="px-2 py-2 tabular-nums">{ils(row.unit_cost_ils)}</td>
      <td className="px-2 py-2 tabular-nums">{ils(row.margin_ils)}</td>
      <td className="px-2 py-2">
        <div className="flex flex-col gap-1">
          <MarginBadge value={row.margin_pct} low={row.margin_pct !== null && Number(row.margin_pct) < floor} />
          {row.margin_pct_jod !== null && (
            <span
              className={`text-caption ${Number(row.margin_pct_jod) < floor ? "font-bold text-danger" : "text-ink-muted"}`}
              dir="ltr"
            >
              JD {Number(row.margin_pct_jod)}%
            </span>
          )}
        </div>
      </td>
      <td className="px-2 py-2">
        <ActiveToggle on={row.active} label={t("active")} onChange={(v) => void save({ active: v })} />
      </td>
      <td className="px-2 py-2">
        <Button size="sm" disabled={!Object.keys(diff).length} loading={busy} onClick={() => void save(diff)}>
          {t("save")}
        </Button>
        {error && <p className="mt-1 text-caption text-danger">{error}</p>}
      </td>
    </tr>
  );
}

/** Products and their variants: prices, unit costs and the margin at list price. */
export function VariantsTable({
  rows,
  floor,
  onRow,
  onProduct,
}: {
  rows: VariantRow[];
  floor: number;
  onRow: (r: VariantRow) => void;
  onProduct: (slug: string, active: boolean) => void;
}) {
  const t = useTranslations("catalogAdmin");
  const locale = useLocale();
  const products = [...new Set(rows.map((r) => r.product))];
  return (
    <div className="flex flex-col gap-6">
      {products.map((slug) => {
        const mine = rows.filter((r) => r.product === slug);
        const first = mine[0];
        return (
          <section key={slug} className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="text-h3 text-night-900">{locale === "ar" ? first.product_ar : first.product_en}</h3>
              <span className="rounded-full bg-paper-sunk px-2.5 py-0.5 text-caption">
                {t(`lines.${first.line}`)} · {first.audience === "b2b" ? "B2B" : "B2C"}
              </span>
              <label className="flex items-center gap-2 text-small">
                <ActiveToggle
                  on={first.product_active}
                  label={t("productActive")}
                  onChange={(v) => onProduct(slug, v)}
                />
                {first.product_active ? t("onSale") : t("offSale")}
              </label>
            </div>
            <div className="overflow-x-auto rounded-lg border border-line bg-paper-raised">
              <table className="w-full min-w-[1100px] text-small">
                <thead className="bg-paper-sunk text-start text-caption text-ink-muted">
                  <tr>
                    <th className="px-2 py-2 text-start">{t("variant")}</th>
                    {(
                      [
                        "price_ils",
                        "price_jod",
                        "cost_print_ils",
                        "cost_packaging_ils",
                        "cost_handling_ils",
                        "cost_ai_usd",
                      ] as const
                    ).map((f) => (
                      <th key={f} className="px-1 py-2 text-start">
                        {t(`fields.${f}`)}
                      </th>
                    ))}
                    <th className="px-2 py-2 text-start">{t("unitCost")}</th>
                    <th className="px-2 py-2 text-start">{t("marginIls")}</th>
                    <th className="px-2 py-2 text-start">{t("marginPct")}</th>
                    <th className="px-2 py-2 text-start">{t("active")}</th>
                    <th className="px-2 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {mine.map((r) => (
                    <Row
                      key={`${r.sku}-${r.price_ils}-${r.cost_print_ils}-${r.active}`}
                      row={r}
                      floor={floor}
                      onSaved={onRow}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </div>
  );
}
