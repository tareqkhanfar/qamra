"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";
import { money } from "@/lib/store";

type Tier = { min_qty: number; unit_ils: string };
type Row = {
  qty: number;
  printer_ils: string;
  cost_ils: string;
  price_ils: string;
  total_ils: string;
  margin_pct: string;
};
type PrintCosts = {
  sku: string;
  product_ar: string;
  product_en: string;
  retail_ils: string | null;
  other_cost_ils: string;
  estimated: boolean;
  bulk_from: number;
  tiers: Tier[];
  table: Row[];
};
type Draft = { min_qty: string; unit_ils: string };

/** The printer's quote per run length (Addendum 7 §3.9 and §8): estimates show ⚠ until saved here. */
export function AdminPrintCosts() {
  const t = useTranslations("printCosts");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [rows, setRows] = useState<PrintCosts[] | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft[]>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ sku: string; ok: boolean; text: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await api<PrintCosts[]>("/api/admin/store/print-costs");
      if (!r.ok) {
        setError(errorText(r.error, locale, te("unknown")));
        return;
      }
      setRows(r.data);
      setDrafts(
        Object.fromEntries(
          r.data.map((p) => [p.sku, p.tiers.map((x) => ({ min_qty: String(x.min_qty), unit_ils: x.unit_ils }))]),
        ),
      );
    })();
  }, [locale, te]);

  function setTier(sku: string, i: number, field: keyof Draft, value: string) {
    setDrafts((d) => ({ ...d, [sku]: d[sku].map((x, j) => (j === i ? { ...x, [field]: value } : x)) }));
  }

  async function save(sku: string) {
    setBusy(sku);
    setNotice(null);
    const tiers = (drafts[sku] ?? [])
      .filter((x) => x.min_qty.trim() && x.unit_ils.trim())
      .map((x) => ({ min_qty: Number(x.min_qty), unit_ils: x.unit_ils.trim() }));
    const r = await api<PrintCosts>(`/api/admin/store/print-costs/${encodeURIComponent(sku)}`, {
      method: "PUT",
      json: { tiers },
    });
    setBusy(null);
    if (!r.ok) {
      const invalid = r.status === 422 && !r.error?.message;
      setNotice({ sku, ok: false, text: invalid ? t("invalid") : errorText(r.error, locale, t("invalid")) });
      return;
    }
    setRows((list) => (list ?? []).map((p) => (p.sku === sku ? r.data : p)));
    setNotice({ sku, ok: true, text: t("saved") });
  }

  if (error) return <Alert>{error}</Alert>;
  if (!rows) return <p className="text-ink-muted">{t("loading")}</p>;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <p className="max-w-3xl text-body text-ink-muted">{t("intro")}</p>
      </header>
      {rows.length === 0 && <p className="text-ink-muted">{t("empty")}</p>}
      {rows.map((p) => (
        <section key={p.sku} className="flex flex-col gap-4 rounded-xl border border-line bg-paper-raised p-4 md:p-6">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-h3 text-night-900">{locale === "ar" ? p.product_ar : p.product_en}</h2>
            <code className="text-caption text-ink-muted" dir="ltr">
              {p.sku}
            </code>
          </div>
          {p.estimated ? (
            <Alert tone="error">⚠ {t("estimated", { n: p.bulk_from })}</Alert>
          ) : (
            <Alert tone="success">{t("confirmed", { n: p.bulk_from })}</Alert>
          )}

          <div className="grid gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
            <form
              className="flex flex-col gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                void save(p.sku);
              }}
            >
              <h3 className="text-body font-bold">{t("quote")}</h3>
              <div className="grid grid-cols-[1fr_1fr_auto] items-end gap-2 text-small">
                <span className="font-semibold text-ink-muted">{t("fromCopies")}</span>
                <span className="font-semibold text-ink-muted">{t("perCopy")}</span>
                <span />
                {(drafts[p.sku] ?? []).map((x, i) => (
                  <div key={i} className="contents">
                    <input
                      id={`${p.sku}-qty-${i}`}
                      inputMode="numeric"
                      dir="ltr"
                      aria-label={t("fromCopies")}
                      value={x.min_qty}
                      onChange={(e) => setTier(p.sku, i, "min_qty", e.target.value)}
                      className="min-h-11 rounded-sm border border-line bg-white px-3 tabular-nums"
                    />
                    <input
                      id={`${p.sku}-ils-${i}`}
                      inputMode="decimal"
                      dir="ltr"
                      aria-label={t("perCopy")}
                      value={x.unit_ils}
                      onChange={(e) => setTier(p.sku, i, "unit_ils", e.target.value)}
                      className="min-h-11 rounded-sm border border-line bg-white px-3 tabular-nums"
                    />
                    <button
                      type="button"
                      aria-label={t("remove")}
                      onClick={() => setDrafts((d) => ({ ...d, [p.sku]: d[p.sku].filter((_, j) => j !== i) }))}
                      className="flex size-11 items-center justify-center rounded-full text-ink-muted hover:bg-paper-sunk"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    setDrafts((d) => ({ ...d, [p.sku]: [...(d[p.sku] ?? []), { min_qty: "", unit_ils: "" }] }))
                  }
                >
                  {t("add")}
                </Button>
                <Button type="submit" size="sm" loading={busy === p.sku}>
                  {t("save")}
                </Button>
              </div>
              <p className="text-caption text-ink-muted">{t("rules")}</p>
              {notice?.sku === p.sku && <Alert tone={notice.ok ? "success" : "error"}>{notice.text}</Alert>}
            </form>

            <div className="flex min-w-0 flex-col gap-2">
              <h3 className="text-body font-bold">{t("table")}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-small tabular-nums">
                  <thead>
                    <tr className="border-b border-line text-start text-ink-muted">
                      <th className="px-2 py-2 text-start font-semibold">{t("copies")}</th>
                      <th className="px-2 py-2 text-start font-semibold">
                        {t("printer")} {p.estimated && "⚠"}
                      </th>
                      <th className="px-2 py-2 text-start font-semibold">{t("ourCost")}</th>
                      <th className="px-2 py-2 text-start font-semibold">{t("price")}</th>
                      <th className="px-2 py-2 text-start font-semibold">{t("total")}</th>
                      <th className="px-2 py-2 text-start font-semibold">{t("margin")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.table.map((r) => (
                      <tr key={r.qty} className="border-b border-line/60">
                        <td className="px-2 py-2 font-semibold">{r.qty}</td>
                        <td className="px-2 py-2">{money(r.printer_ils, "ILS", locale)}</td>
                        <td className="px-2 py-2">{money(r.cost_ils, "ILS", locale)}</td>
                        <td className="px-2 py-2 font-semibold text-night-900">{money(r.price_ils, "ILS", locale)}</td>
                        <td className="px-2 py-2">{money(r.total_ils, "ILS", locale)}</td>
                        <td className="px-2 py-2" dir="ltr">
                          {r.margin_pct}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-caption text-ink-muted">
                {t("basis", {
                  other: money(p.other_cost_ils, "ILS", locale),
                  retail: money(p.retail_ils ?? 0, "ILS", locale),
                })}
              </p>
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}
