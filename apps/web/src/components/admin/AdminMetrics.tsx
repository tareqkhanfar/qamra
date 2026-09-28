"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { api, errorText } from "@/lib/api";

type ThemeRow = {
  slug: string;
  title: string;
  books: number;
  avg_cost: number;
  avg_page_cost: number;
  redraw_rate: number;
  fallback_rate: number;
  needs_review_rate: number;
  budget_stops: number;
};
type Metrics = {
  days: number;
  books: number;
  avg_cost_per_book: number | null;
  avg_cost_per_page: number | null;
  target_usd: number;
  cap_usd: number;
  within_cap_ratio: number | null;
  themes: ThemeRow[];
  by_step: Record<string, number>;
  daily: { date: string; usd: number }[];
};

const STEP_COLORS = [
  "bg-night-900",
  "bg-night-500",
  "bg-amber-500",
  "bg-lav-300",
  "bg-sage-300",
  "bg-coral-300",
  "bg-night-100",
];
const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);
const money = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? "—" : `$${v.toFixed(digits)}`;

/** Cost dashboard (design: AdminMetrics; Addendum 3 §2.6). */
export function AdminMetrics() {
  const t = useTranslations("metrics");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [days, setDays] = useState(30);
  const [data, setData] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const res = await api<Metrics>(`/api/admin/metrics?days=${days}`);
      if (res.ok) setData(res.data);
      else setError(errorText(res.error, locale, te("unknown")));
    })();
  }, [days, locale, te]);

  const steps = Object.entries(data?.by_step ?? {}).sort((a, b) => b[1] - a[1]);
  const stepTotal = steps.reduce((s, [, v]) => s + v, 0) || 1;
  const maxDay = Math.max(0.0001, ...(data?.daily ?? []).map((d) => d.usd));
  const stepLabel = (k: string) => (t.has(`steps.${k}`) ? t(`steps.${k}`) : k);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <label className="flex items-center gap-2 text-small">
          {t("period")}
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="min-h-11 rounded-md border border-line bg-paper-raised px-3"
          >
            {[7, 30, 90].map((n) => (
              <option key={n} value={n}>
                {t("days", { n })}
              </option>
            ))}
          </select>
        </label>
      </header>
      {error && <Alert>{error}</Alert>}
      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              { label: t("books"), value: String(data.books) },
              {
                label: t("perBook"),
                value: money(data.avg_cost_per_book),
                note: t("target", { target: money(data.target_usd), cap: money(data.cap_usd) }),
                bad: (data.avg_cost_per_book ?? 0) > data.cap_usd,
              },
              { label: t("perPage"), value: money(data.avg_cost_per_page, 3) },
              { label: t("withinCap"), value: pct(data.within_cap_ratio) },
            ].map((c) => (
              <div key={c.label} className="rounded-xl border border-line bg-paper-raised p-5">
                <div className="text-small text-ink-muted">{c.label}</div>
                <div
                  dir="ltr"
                  className={`text-h1 font-bold rtl:text-right ${c.bad ? "text-danger" : "text-night-900"}`}
                >
                  {c.value}
                </div>
                {c.note && <div className="text-caption text-ink-muted">{c.note}</div>}
              </div>
            ))}
          </div>

          {data.books === 0 && <p className="text-ink-muted">{t("noData")}</p>}

          <section className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-5">
            <h2 className="text-h3 text-night-900">{t("byTheme")}</h2>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-small">
                <thead className="text-ink-muted">
                  <tr className="border-b border-line text-start">
                    {[
                      t("theme"),
                      t("books"),
                      t("avgCost"),
                      t("pageCost"),
                      t("redrawRate"),
                      t("fallbackRate"),
                      t("reviewRate"),
                      t("budgetStops"),
                    ].map((h) => (
                      <th key={h} className="py-2 text-start font-semibold">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.themes.map((th) => (
                    <tr key={th.slug} className="border-b border-line/60">
                      <td className="py-2 font-semibold text-night-900">
                        {th.title}
                        {th.redraw_rate > 0.2 && (
                          <div className="text-caption font-normal text-warning">{t("improve")}</div>
                        )}
                      </td>
                      <td>{th.books}</td>
                      <td dir="ltr" className="rtl:text-right">
                        {money(th.avg_cost)}
                      </td>
                      <td dir="ltr" className="rtl:text-right">
                        {money(th.avg_page_cost, 3)}
                      </td>
                      <td className={th.redraw_rate > 0.2 ? "font-bold text-warning" : ""}>{pct(th.redraw_rate)}</td>
                      <td>{pct(th.fallback_rate)}</td>
                      <td>{pct(th.needs_review_rate)}</td>
                      <td>{th.budget_stops}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-5">
              <h2 className="text-h3 text-night-900">{t("byStep")}</h2>
              <div className="flex h-8 overflow-hidden rounded-full bg-paper-sunk">
                {steps.map(([k, v], i) => (
                  <div
                    key={k}
                    className={STEP_COLORS[i % STEP_COLORS.length]}
                    style={{ width: `${(v / stepTotal) * 100}%` }}
                  />
                ))}
              </div>
              <ul className="flex flex-col gap-1 text-small">
                {steps.map(([k, v], i) => (
                  <li key={k} className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <span className={`size-3 rounded-sm ${STEP_COLORS[i % STEP_COLORS.length]}`} />
                      {stepLabel(k)}
                    </span>
                    <span dir="ltr">{money(v, 3)}</span>
                  </li>
                ))}
              </ul>
            </section>
            <section className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-5">
              <h2 className="text-h3 text-night-900">{t("daily")}</h2>
              <div className="flex h-40 items-end gap-1">
                {data.daily.map((d) => (
                  <div
                    key={d.date}
                    title={`${d.date}: $${d.usd.toFixed(2)}`}
                    className="flex-1 rounded-t-sm bg-night-900"
                    style={{ height: `${Math.max(4, (d.usd / maxDay) * 100)}%` }}
                  />
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
