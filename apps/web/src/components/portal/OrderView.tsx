"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { money, portalApi, portalFiles, type OrderRow, type Quote } from "@/lib/portal";
import { usePortal } from "./PortalShell";

/** The class order (design ClassPrint, PortalOrder): wholesale tiers, one order and one invoice, delivered to
 * the school, cash on delivery. */
export function OrderView({ classId }: { classId: string }) {
  const t = useTranslations("portal.order");
  const te = useTranslations("errors");
  const locale = useLocale();
  const { me, reload } = usePortal();
  const [quote, setQuote] = useState<Quote | null>(null);
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [notes, setNotes] = useState("");
  const [accept, setAccept] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [placed, setPlaced] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [q, o] = await Promise.all([portalApi.quote(classId), portalApi.orders()]);
    if (q.ok) setQuote(q.data);
    else setError(errorText(q.error, locale, te("unknown")));
    if (o.ok) setOrders(o.data);
  }, [classId, locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function submit() {
    if (!accept) {
      setError(t("acceptRequired"));
      return;
    }
    setBusy(true);
    setError(null);
    const r = await portalApi.order(classId, notes || undefined);
    setBusy(false);
    if (r.ok) {
      setPlaced(r.data.code);
      await Promise.all([load(), reload()]);
    } else setError(errorText(r.error, locale, te("unknown")));
  }

  if (!quote) return error ? <Alert>{error}</Alert> : <div className="h-64 animate-pulse rounded-xl bg-paper-sunk" />;
  const m = (x: string | null) => money(x, quote.currency, locale);
  const unit = quote.unit_price ? Number(quote.unit_price) : null;
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
      <div className="flex flex-col gap-6">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <section className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-5">
          <h2 className="text-h3 text-night-900">{t("copies")}</h2>
          <div className="flex justify-between gap-2 text-body">
            <span>{t("perChild", { product: locale === "ar" ? quote.name_ar : quote.name_en })}</span>
            <strong>{quote.copies}</strong>
          </div>
          {quote.children.length > 0 && <p className="text-caption text-ink-muted">{quote.children.join("، ")}</p>}
        </section>
        {quote.tiers.length > 0 && (
          <section className="flex flex-col gap-3">
            <h2 className="text-h3 text-night-900">{t("tiers")}</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              {quote.tiers.map((tier, i) => {
                const next = quote.tiers[i + 1];
                const mine = unit !== null && Number(tier.unit_price) === unit && quote.copies >= tier.min_qty;
                return (
                  <div
                    key={tier.min_qty}
                    className={`relative flex flex-col gap-1 rounded-lg p-4 ${mine ? "bg-night-900 text-paper" : "border border-line bg-paper-raised"}`}
                  >
                    <span className="text-small">
                      {next
                        ? t("range", { from: tier.min_qty, to: next.min_qty - 1 })
                        : t("rangeUp", { from: tier.min_qty })}
                    </span>
                    <strong className="font-display text-h3">{m(tier.unit_price)}</strong>
                    <span className="text-caption">{t("perCopy")}</span>
                    {mine && (
                      <span className="absolute end-3 top-3 rounded-full bg-amber-500 px-2 py-0.5 text-[11px] font-bold text-night-950">
                        {t("yourTier")}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}
        <section className="flex flex-col gap-1 rounded-xl border border-line bg-paper-raised p-5">
          <h2 className="text-h3 text-night-900">{t("delivery")}</h2>
          <p className="text-body">{quote.delivery.name}</p>
          <p className="text-small text-ink-muted">
            {[quote.delivery.city, quote.delivery.address].filter(Boolean).join("، ") || t("noAddress")}
          </p>
          <p className="text-caption text-ink-muted">{t("deliveryNote")}</p>
        </section>
        {orders.length > 0 && (
          <section className="flex flex-col gap-2">
            <h2 className="text-h3 text-night-900">{t("history")}</h2>
            {orders.map((o) => (
              <div
                key={o.code}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-paper-raised px-4 py-3"
              >
                <span className="font-semibold" dir="ltr">
                  {o.code}
                </span>
                <span className="text-small">
                  {t("orderLine", { n: o.copies, total: money(o.total, o.currency, locale) })}
                </span>
                <span className="text-caption text-ink-muted">{t(`status.${o.status}`)}</span>
                {o.invoice_ready ? (
                  <a
                    href={portalFiles.invoice(o.code)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-small font-semibold underline"
                  >
                    {t("invoice", { n: o.invoice ?? "" })}
                  </a>
                ) : (
                  <span className="text-caption text-ink-muted">{t("invoicePending", { n: o.invoice ?? "" })}</span>
                )}
              </div>
            ))}
          </section>
        )}
      </div>
      <aside className="flex flex-col gap-3 self-start rounded-xl border border-line bg-paper-raised p-5 xl:sticky xl:top-6">
        <h2 className="text-h3 text-night-900">{t("summary")}</h2>
        <dl className="flex flex-col gap-2 text-small">
          <Line label={t("booksLine", { n: quote.copies, unit: m(quote.unit_price) })} value={m(quote.subtotal)} />
          <Line label={t("included")} value={t("free")} />
          {Number(quote.discount) > 0 && <Line label={t("discount")} value={`− ${m(quote.discount)}`} />}
          <Line label={t("shipping")} value={Number(quote.shipping) ? m(quote.shipping) : t("free")} />
          <Line label={t("total")} value={m(quote.total)} strong />
        </dl>
        <p className="text-caption text-ink-muted">{t("priceList", { name: quote.price_list ?? t("retail") })}</p>
        {quote.ordered || placed ? (
          <Alert tone="success">{t("placed", { code: quote.ordered ?? placed ?? "" })}</Alert>
        ) : (
          <>
            <p className="text-small">{t("cod", { school: me.org.name })}</p>
            <label htmlFor="notes" className="text-small font-semibold">
              {t("notes")}
            </label>
            <textarea
              id="notes"
              rows={2}
              maxLength={500}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="rounded-sm border border-line bg-paper p-3 text-small"
            />
            <label className="flex items-start gap-2 text-small">
              <input
                type="checkbox"
                checked={accept}
                onChange={(e) => setAccept(e.target.checked)}
                className="mt-0.5 size-5 shrink-0 accent-night-900"
              />
              {t("accept")}
            </label>
            {error && <Alert>{error}</Alert>}
            <Button variant="primary" size="lg" loading={busy} disabled={!quote.copies} onClick={() => void submit()}>
              {t("cta", { n: quote.copies })}
            </Button>
            {!quote.copies && <p className="text-caption text-ink-muted">{t("nothing")}</p>}
          </>
        )}
      </aside>
    </div>
  );
}

function Line({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-2 ${strong ? "border-t border-line pt-2 text-body font-bold" : ""}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
