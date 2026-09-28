"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";
import { ils, pct } from "@/lib/catalogAdmin";

type Row = { key: string; qty: number; revenue_ils: string; name_ar?: string };
type Report = {
  days: number;
  since: string;
  orders: number;
  revenue_ils: string;
  aov_ils: string;
  cost_ils: string;
  margin_ils: string;
  margin_pct: string | null;
  orders_below_floor: number;
  by_line: Row[];
  by_product: Row[];
  by_theme: Row[];
  by_style: { key: string; qty: number }[];
  by_addon: Row[];
  attach_rate_pct: string | null;
  preview_to_purchase: { line: string; books: number; bought: number; rate_pct: string | null }[];
  ai_cost: { day: string; usd: string }[];
  b2b: { orders: number; revenue_ils: string };
  b2c: { orders: number; revenue_ils: string };
};
const PERIODS = [7, 30, 90, 365] as const;

function Table({ title, rows, label }: { title: string; rows: Row[]; label: (key: string) => string }) {
  const t = useTranslations("reports");
  return (
    <section className="flex min-w-0 flex-col gap-2">
      <h3 className="text-body font-bold text-night-900">{title}</h3>
      <div className="overflow-x-auto rounded-lg border border-line bg-paper-raised">
        <table className="w-full text-small tabular-nums">
          <thead className="bg-paper-sunk text-caption text-ink-muted">
            <tr>
              <th className="px-3 py-2 text-start">{t("item")}</th>
              <th className="px-3 py-2 text-start">{t("qty")}</th>
              <th className="px-3 py-2 text-start">{t("revenue")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-t border-line/60">
                <td className="px-3 py-2">{r.name_ar ?? label(r.key)}</td>
                <td className="px-3 py-2">{r.qty}</td>
                <td className="px-3 py-2">{ils(r.revenue_ils)}</td>
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={3} className="px-3 py-3 text-ink-muted">
                  {t("none")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** Sales reports (Addendum 4 step 5): what sold, what it earned us, and CSV exports for Excel. */
export function AdminReports() {
  const t = useTranslations("reports");
  const tl = useTranslations("catalogAdmin.lines");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [days, setDays] = useState<number>(30);
  const [data, setData] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await api<Report>(`/api/admin/reports?days=${days}`);
      if (r.ok) setData(r.data);
      else setError(errorText(r.error, locale, te("unknown")));
    })();
  }, [days, locale, te]);

  const line = (k: string) => (tl.has(k) ? tl(k) : k);
  const maxUsd = Math.max(0.01, ...(data?.ai_cost ?? []).map((d) => Number(d.usd)));
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <div className="flex flex-wrap items-center gap-2">
          {PERIODS.map((d) => (
            <button
              key={d}
              type="button"
              aria-pressed={days === d}
              onClick={() => setDays(d)}
              className={`min-h-10 rounded-full px-3.5 text-small ${days === d ? "bg-night-900 font-bold text-paper" : "border border-line bg-paper-raised"}`}
            >
              {t("lastDays", { n: d })}
            </button>
          ))}
          <a href={`/api/admin/reports/orders.csv?days=${days}`} className={buttonClasses("secondary", "sm")}>
            {t("ordersCsv")}
          </a>
          <a href={`/api/admin/reports/items.csv?days=${days}`} className={buttonClasses("secondary", "sm")}>
            {t("itemsCsv")}
          </a>
        </div>
      </header>
      {error && <Alert>{error}</Alert>}
      {data && (
        <>
          <dl className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {[
              [t("orders"), String(data.orders)],
              [t("revenue"), ils(data.revenue_ils)],
              [t("aov"), ils(data.aov_ils)],
              [t("margin"), `${ils(data.margin_ils)} · ${pct(data.margin_pct)}`],
              [t("attach"), pct(data.attach_rate_pct)],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg border border-line bg-paper-raised p-3">
                <dt className="text-caption text-ink-muted">{k}</dt>
                <dd className="font-display text-[20px] font-bold text-night-900 tabular-nums">{v}</dd>
              </div>
            ))}
          </dl>
          {data.orders_below_floor > 0 && <Alert>{t("belowFloor", { n: data.orders_below_floor })}</Alert>}
          <div className="grid gap-6 lg:grid-cols-2">
            <Table title={t("byLine")} rows={data.by_line} label={line} />
            <Table title={t("byProduct")} rows={data.by_product} label={(k) => k} />
            <Table title={t("byTheme")} rows={data.by_theme} label={(k) => k} />
            <Table title={t("byAddon")} rows={data.by_addon} label={(k) => k} />
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <section className="flex flex-col gap-2">
              <h3 className="text-body font-bold text-night-900">{t("byStyle")}</h3>
              <ul className="flex flex-col gap-1 text-small">
                {data.by_style.map((s) => (
                  <li key={s.key} className="flex justify-between border-b border-line/60 py-1">
                    <span>{s.key}</span>
                    <span className="tabular-nums">{s.qty}</span>
                  </li>
                ))}
                {!data.by_style.length && <li className="text-ink-muted">{t("none")}</li>}
              </ul>
            </section>
            <section className="flex flex-col gap-2">
              <h3 className="text-body font-bold text-night-900">{t("funnel")}</h3>
              <ul className="flex flex-col gap-1 text-small">
                {data.preview_to_purchase.map((f) => (
                  <li key={f.line} className="flex justify-between border-b border-line/60 py-1">
                    <span>{line(f.line)}</span>
                    <span className="tabular-nums">
                      {f.bought}/{f.books} · {pct(f.rate_pct)}
                    </span>
                  </li>
                ))}
                {!data.preview_to_purchase.length && <li className="text-ink-muted">{t("none")}</li>}
              </ul>
            </section>
            <section className="flex flex-col gap-2">
              <h3 className="text-body font-bold text-night-900">{t("b2bVsB2c")}</h3>
              <ul className="flex flex-col gap-1 text-small tabular-nums">
                <li className="flex justify-between border-b border-line/60 py-1">
                  <span>{t("b2c")}</span>
                  <span>
                    {data.b2c.orders} · {ils(data.b2c.revenue_ils)}
                  </span>
                </li>
                <li className="flex justify-between border-b border-line/60 py-1">
                  <span>{t("b2b")}</span>
                  <span>
                    {data.b2b.orders} · {ils(data.b2b.revenue_ils)}
                  </span>
                </li>
              </ul>
            </section>
          </div>
          <section className="flex flex-col gap-2">
            <h3 className="text-body font-bold text-night-900">{t("aiCost")}</h3>
            <div
              className="flex h-32 items-end gap-0.5 overflow-x-auto rounded-lg border border-line bg-paper-raised p-3"
              dir="ltr"
            >
              {data.ai_cost.map((d) => (
                <div
                  key={d.day}
                  title={`${d.day}: $${Number(d.usd).toFixed(2)}`}
                  className="w-2.5 shrink-0 rounded-t bg-night-500"
                  style={{ height: `${Math.max(2, (Number(d.usd) / maxUsd) * 100)}%` }}
                />
              ))}
              {!data.ai_cost.length && <span className="text-small text-ink-muted">{t("none")}</span>}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
