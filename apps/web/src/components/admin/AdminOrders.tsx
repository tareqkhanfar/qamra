"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { money, type Currency } from "@/lib/store";

type Row = {
  id: string;
  code: string;
  status: string;
  created_at: string;
  customer: string;
  phone: string | null;
  city: string | null;
  items: number;
  currency: Currency;
  total: string;
  cost_ils: string;
  source: string;
  gift?: boolean;
};
type List = { orders: Row[]; total: number; counts: Record<string, number> };
type Item = {
  id: string;
  sku: string | null;
  title: { name_ar?: string; name_en?: string; options?: Record<string, string> };
  child_name: string | null;
  theme: string | null;
  quantity: number;
  unit_price: string;
  discount: string;
  addons: { slug: string; qty: number; included?: boolean; name_ar?: string; name_en?: string }[];
};
type Event = {
  kind: string;
  from_status: string | null;
  to_status: string | null;
  note: string | null;
  data: Record<string, unknown>;
  actor: string | null;
  at: string;
};
type Detail = {
  id: string;
  code: string;
  status: string;
  next_statuses: string[];
  created_at: string;
  currency: Currency;
  subtotal: string;
  discount: string;
  delivery_fee: string;
  total: string;
  cost_ils: string;
  shipping: Record<string, string | null>;
  items: Item[];
  events: Event[];
  invoice: { number: string; ready: boolean } | null;
  messages: Record<string, string>;
  revenue_ils: string;
  margin_pct: string | null;
  margin_floor_pct: number;
  gift?: boolean; // Addendum 9
  gift_message?: string | null;
};

const STATUSES = [
  "new",
  "confirmed",
  "generating",
  "review",
  "printing",
  "shipped",
  "delivered",
  "reprint",
  "cancelled",
];
const TONE: Record<string, string> = {
  new: "bg-amber-100 text-amber-700",
  cancelled: "bg-paper-sunk text-ink-muted",
  delivered: "bg-success-bg text-success",
  reprint: "bg-danger-bg text-danger",
};

/** Order management (design: AdminOrders; Addendum 4 §5). */
export function AdminOrders() {
  const t = useTranslations("orders");
  const tg = useTranslations("orderPath.orders");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [list, setList] = useState<List | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [note, setNote] = useState("");
  const [reprint, setReprint] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (q.trim()) params.set("q", q.trim());
    const r = await api<List>(`/api/admin/orders?${params}`);
    if (r.ok) setList(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }, [status, q, locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  const open = async (id: string) => {
    const r = await api<Detail>(`/api/admin/orders/${id}`);
    if (r.ok) {
      setDetail(r.data);
      setReprint(new Set());
    }
  };

  // the worker renders the invoice a few seconds after confirmation: look again until it's there
  useEffect(() => {
    if (!detail?.invoice || detail.invoice.ready) return;
    const id = detail.id;
    const timer = setInterval(() => {
      void api<Detail>(`/api/admin/orders/${id}`).then((r) => r.ok && setDetail(r.data));
    }, 4000);
    return () => clearInterval(timer);
  }, [detail?.id, detail?.invoice]);

  const act = async (path: string, json: unknown) => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    const r = await api<Detail>(`/api/admin/orders/${detail.id}${path}`, { json });
    setBusy(false);
    if (r.ok) {
      setDetail(r.data);
      void load();
    } else setError(errorText(r.error, locale, te("unknown")));
  };

  const amount = (value: string, currency: Currency) => money(value, currency, locale);

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-h2 text-night-900">{t("title")}</h1>
      <div className="flex flex-wrap gap-2">
        {["", ...STATUSES].map((s) => (
          <button
            key={s || "all"}
            type="button"
            onClick={() => setStatus(s)}
            className={`min-h-10 rounded-full px-3.5 text-small font-semibold ${status === s ? "bg-night-900 text-paper" : "border border-line bg-paper-raised"}`}
          >
            {s ? t(`statuses.${s}`) : t("all")} {s && list?.counts[s] ? `(${list.counts[s]})` : ""}
          </button>
        ))}
      </div>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t("search")}
        className="min-h-11 rounded-md border border-line bg-paper-raised px-3"
      />
      {error && <Alert>{error}</Alert>}

      <div className="grid gap-5 xl:grid-cols-[1fr_440px] xl:items-start">
        <div className="overflow-hidden rounded-lg border border-line bg-paper-raised">
          {list && list.orders.length === 0 && <p className="p-6 text-center text-ink-muted">{t("empty")}</p>}
          {list?.orders.map((o) => (
            <button
              key={o.id}
              type="button"
              onClick={() => void open(o.id)}
              className={`flex w-full items-center gap-3 border-b border-line/60 p-3 text-start hover:bg-paper-sunk ${detail?.id === o.id ? "bg-night-100" : ""}`}
            >
              <span className="flex grow flex-col">
                <strong dir="ltr" className="self-start text-night-900">
                  {o.code}
                </strong>
                <span className="text-small text-ink-muted">
                  {o.customer} · {o.city ?? "—"} · {o.items} · {new Date(o.created_at).toLocaleDateString(locale)}
                  {o.gift && ` · ${tg("gift")}`}
                </span>
              </span>
              <span className="font-semibold whitespace-nowrap">{amount(o.total, o.currency)}</span>
              <span
                className={`rounded-full px-2.5 py-1 text-caption font-bold ${TONE[o.status] ?? "bg-night-100 text-night-900"}`}
              >
                {t(`statuses.${o.status}`)}
              </span>
            </button>
          ))}
        </div>

        {detail && (
          <aside className="flex flex-col gap-4 rounded-lg border border-line bg-paper-raised p-4 xl:sticky xl:top-6">
            <div className="flex items-center justify-between">
              <strong dir="ltr" className="text-[20px] text-night-900">
                {detail.code}
              </strong>
              <button type="button" onClick={() => setDetail(null)} className="text-small underline">
                {t("close")}
              </button>
            </div>

            <section className="flex flex-col gap-1 text-small">
              <h2 className="font-semibold text-night-900">{t("customer")}</h2>
              <p>{detail.shipping.name}</p>
              <p dir="ltr" className="self-start">
                {detail.shipping.phone}
              </p>
              <p>
                {detail.shipping.city} — {detail.shipping.address}
              </p>
              {detail.shipping.notes && <p className="text-ink-muted">{detail.shipping.notes}</p>}
              {detail.gift && (
                <p className="mt-1 rounded-md bg-amber-100 px-2.5 py-1.5 text-amber-700">
                  <strong>{tg("gift")}</strong>
                  {detail.gift_message && <span className="block whitespace-pre-line">{detail.gift_message}</span>}
                </p>
              )}
              <a
                href={`/${locale}/admin/orders/${detail.id}/slip`}
                target="_blank"
                rel="noopener"
                className="self-start font-semibold underline underline-offset-4"
              >
                {tg("slip")}
              </a>
            </section>

            <section className="flex flex-col gap-2">
              <h2 className="text-small font-semibold text-night-900">{t("items")}</h2>
              {detail.items.map((it) => (
                <label key={it.id} className="flex items-start gap-2 rounded-md bg-paper-sunk p-2.5 text-small">
                  {detail.next_statuses.includes("reprint") && (
                    <input
                      type="checkbox"
                      className="mt-1 size-4"
                      checked={reprint.has(it.id)}
                      onChange={(e) => {
                        const next = new Set(reprint);
                        if (e.target.checked) next.add(it.id);
                        else next.delete(it.id);
                        setReprint(next);
                      }}
                    />
                  )}
                  <span className="flex grow flex-col">
                    <strong>
                      {locale === "ar" ? it.title.name_ar : it.title.name_en}
                      {it.child_name ? ` — ${it.child_name}` : ""}
                    </strong>
                    <span className="text-ink-muted">
                      {[
                        it.title.options?.format,
                        it.theme,
                        ...it.addons.map((a) => (locale === "ar" ? a.name_ar : a.name_en) ?? a.slug),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </span>
                  <span className="font-semibold">{amount(it.unit_price, detail.currency)}</span>
                </label>
              ))}
            </section>

            <section className="flex flex-col gap-1.5 text-small">
              <h2 className="font-semibold text-night-900">{t("pricing")}</h2>
              <Line label={t("subtotal")} value={amount(detail.subtotal, detail.currency)} />
              {Number(detail.discount) > 0 && (
                <Line label={t("discount")} value={amount(detail.discount, detail.currency)} />
              )}
              <Line label={t("delivery")} value={amount(detail.delivery_fee, detail.currency)} />
              <Line label={t("total")} value={amount(detail.total, detail.currency)} strong />
              <Line label={t("cost")} value={amount(detail.cost_ils, "ILS")} />
              <MarginLine label={t("margin")} detail={detail} note={t("marginNote")} />
            </section>

            {detail.invoice && (
              <p className="text-small">
                {detail.invoice.ready ? (
                  <a
                    href={`/api/admin/orders/${detail.id}/invoice.pdf`}
                    target="_blank"
                    rel="noopener"
                    className="font-semibold underline underline-offset-4"
                  >
                    {t("invoice", { number: detail.invoice.number })}
                  </a>
                ) : (
                  t("invoicePending", { number: detail.invoice.number })
                )}
              </p>
            )}

            <section className="flex flex-wrap gap-2">
              {detail.next_statuses.map((s) => (
                <button
                  key={s}
                  type="button"
                  disabled={busy || (s === "reprint" && reprint.size === 0)}
                  onClick={() =>
                    void act("/status", { to: s, items: s === "reprint" ? [...reprint] : [], note: note || undefined })
                  }
                  className={buttonClasses(s === "cancelled" ? "danger" : "solid", "sm")}
                >
                  {t("moveTo", { status: t(`statuses.${s}`) })}
                </button>
              ))}
            </section>
            {detail.next_statuses.includes("reprint") && (
              <p className="text-caption text-ink-muted">{t("reprintItems")}</p>
            )}

            <section className="flex flex-col gap-2">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={t("note")}
                className="min-h-16 rounded-md border border-line bg-paper px-3 py-2 text-small"
                maxLength={2000}
              />
              <button
                type="button"
                disabled={busy || !note.trim()}
                onClick={() => {
                  void act("/notes", { note });
                  setNote("");
                }}
                className={buttonClasses("secondary", "sm", "self-start")}
              >
                {t("addNote")}
              </button>
            </section>

            <section className="flex flex-col gap-1.5">
              {Object.entries(detail.messages)
                .filter(([s]) => s === detail.status)
                .map(([s, href]) => (
                  <a
                    key={s}
                    href={href}
                    target="_blank"
                    rel="noopener"
                    onClick={() => void act("/messages", { template: s })}
                    className={buttonClasses("secondary", "sm", "self-start")}
                  >
                    {t("message", { status: t(`statuses.${s}`) })}
                  </a>
                ))}
            </section>

            <section className="flex flex-col gap-2 border-t border-line pt-3">
              <h2 className="text-small font-semibold text-night-900">{t("history")}</h2>
              <ol className="flex flex-col gap-2 text-small">
                {[...detail.events].reverse().map((e, i) => (
                  <li key={i} className="flex flex-col">
                    <span>
                      <strong>{t(`events.${e.kind}`)}</strong>
                      {e.to_status && ` → ${t(`statuses.${e.to_status}`)}`}
                      {e.actor && <span className="text-ink-muted"> · {t("by", nameCases(e.actor))}</span>}
                    </span>
                    {e.note && <span className="text-ink-muted">{e.note}</span>}
                    <span className="text-caption text-ink-muted">{new Date(e.at).toLocaleString(locale)}</span>
                  </li>
                ))}
              </ol>
            </section>
          </aside>
        )}
      </div>
    </div>
  );
}

function Line({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? "font-bold text-night-900" : ""}`}>
      <span className={strong ? "" : "text-ink-muted"}>{label}</span>
      <span>{value}</span>
    </div>
  );
}

function MarginLine({ label, detail, note }: { label: string; detail: Detail; note: string }) {
  const margin = detail.margin_pct === null ? null : Number(detail.margin_pct);
  const low = margin !== null && margin < detail.margin_floor_pct;
  return (
    <div className="flex flex-col gap-0.5">
      <div className={`flex justify-between font-semibold ${low ? "text-danger" : "text-success"}`}>
        <span>{label}</span>
        <span>{margin === null ? "—" : `${margin}%`}</span>
      </div>
      <span className="text-caption text-ink-muted">{note}</span>
    </div>
  );
}
