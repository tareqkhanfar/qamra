"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { api, errorText } from "@/lib/api";

const STATUSES = ["new", "contacted", "won", "lost"] as const;

type Quote = { quantity: number; unit_price: string; total: string; unit_cost: string; margin_pct: string };
type Lead = {
  id: string;
  kind: string;
  created_at: string;
  status: "new" | "contacted" | "won" | "lost";
  org_name: string;
  city: string | null;
  contact_name: string;
  contact_role: string | null;
  phone: string;
  email: string | null;
  quantity: number | null;
  children_count: number | null;
  event_date: string | null;
  notes: string | null;
  has_logo: boolean;
  quote: Quote | null;
};

/** Staff: the organizations' requests, the logo for the back cover, the status and the price. */
export function AdminLeads() {
  const locale = useLocale();
  const t = useTranslations("adminLeads");
  const te = useTranslations("errors");
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await api<Lead[]>("/api/admin/leads");
    if (r.ok) setLeads(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }, [locale, te]);
  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function act(path: string, method: string, json?: unknown) {
    setError(null);
    const r = await api<Lead>(path, { method, json });
    if (r.ok) setLeads((all) => (all ?? []).map((l) => (l.id === r.data.id ? r.data : l)));
    else setError(errorText(r.error, locale, te("unknown")));
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-[26px] text-night-900">{t("title")}</h1>
      {error && <Alert>{error}</Alert>}
      {leads?.length === 0 && <p className="text-body text-ink-faint">{t("empty")}</p>}
      {leads?.map((l) => (
        <article key={l.id} className="flex flex-col gap-2 rounded-[18px] border border-line bg-paper-raised p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong className="text-[18px] text-night-900">{l.org_name}</strong>
            <span className="text-caption text-ink-faint">
              {l.kind === "family_quote" ? t("family") : t("demo")} ·{" "}
              {new Date(l.created_at).toLocaleDateString(locale)}
            </span>
          </div>
          <p className="text-small text-ink">
            {l.contact_name}
            {l.contact_role ? ` (${l.contact_role})` : ""} · <span dir="ltr">{l.phone}</span>
            {l.email ? (
              <>
                {" "}
                · <span dir="ltr">{l.email}</span>
              </>
            ) : null}
            {l.city ? ` · ${l.city}` : ""}
          </p>
          <p className="text-small font-bold text-night-900">
            {l.quantity
              ? `${l.quantity} ${t("copies")}`
              : l.children_count
                ? `${l.children_count} ${t("children")}`
                : ""}
            {l.event_date ? ` · ${t("by")}: ${l.event_date}` : ""}
          </p>
          {l.notes && <p className="text-small text-ink">{l.notes}</p>}
          {l.has_logo && (
            <figure className="flex items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element -- a private image behind the staff API */}
              <img src={`/api/admin/leads/${l.id}/logo`} alt={t("logo")} className="h-14 w-auto rounded bg-white p-1" />
              <figcaption className="text-caption text-ink-faint">{t("logo")}</figcaption>
            </figure>
          )}
          {l.quote && (
            <p className="rounded-[12px] bg-success-bg px-3 py-2 text-small font-bold text-success">
              {l.quote.unit_price} ₪ {t("unit")} · {t("total")} {l.quote.total} ₪ · {t("margin")} {l.quote.margin_pct}%
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={l.status}
              onChange={(e) => void act(`/api/admin/leads/${l.id}`, "PATCH", { status: e.target.value })}
              className="min-h-11 rounded-[12px] border border-line bg-white px-3 text-small"
              aria-label="status"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {t(`statuses.${s}`)}
                </option>
              ))}
            </select>
            {l.kind === "family_quote" && (
              <button
                type="button"
                onClick={() => void act(`/api/admin/leads/${l.id}/quote`, "POST")}
                className="min-h-11 rounded-full bg-night-800 px-4 text-small font-bold text-paper"
              >
                {t("price")}
              </button>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}
