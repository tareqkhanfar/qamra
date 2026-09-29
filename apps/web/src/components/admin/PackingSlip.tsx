"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api, errorText } from "@/lib/api";
import { money, type Currency } from "@/lib/store";

type Slip = {
  code: string;
  created_at: string;
  gift: boolean;
  gift_message: string | null;
  recipient: { name: string; phone: string | null; city: string | null; address: string | null; notes: string | null };
  items: {
    name_ar: string;
    name_en: string;
    book_title: string | null;
    child_name: string | null;
    format: string;
    qty: number;
    copies: number;
    addons: { slug: string; name_ar: string; name_en: string; qty: number }[];
    unit_price: string | null;
    total: string | null;
  }[];
  currency: Currency;
  prices_hidden: boolean;
  subtotal: string | null;
  discount: string | null;
  delivery_fee: string | null;
  gift_card: string | null;
  total: string | null;
  payment_method: string | null;
};

/** The packing slip of an order (Addendum 9): what goes in the parcel. A gift's slip has no price at all and
 * carries the parent's card message. Printed from the browser (A5/A4, no admin chrome). */
export function PackingSlip({ id }: { id: string }) {
  const t = useTranslations("orderPath.slip");
  const tf = useTranslations("store.formats");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [slip, setSlip] = useState<Slip | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await api<Slip>(`/api/admin/orders/${id}/packing-slip`);
      if (r.ok) setSlip(r.data);
      else setError(errorText(r.error, locale, te("unknown")));
    })();
  }, [id, locale, te]);

  if (error) return <Alert>{error}</Alert>;
  if (!slip) return <p className="text-ink-muted">…</p>;
  const name = (x: { name_ar: string; name_en: string }) => (locale === "ar" ? x.name_ar : x.name_en);
  const amount = (v: string | null) => (v === null ? "" : money(v, slip.currency, locale));
  return (
    <div className="mx-auto flex max-w-[720px] flex-col gap-5 bg-white p-6 text-ink print:max-w-none print:p-0">
      <div className="flex items-center justify-between gap-3 print:hidden">
        <Link href="/admin/orders" className="text-small underline underline-offset-4">
          {t("back")}
        </Link>
        <button type="button" onClick={() => window.print()} className={buttonClasses("solid", "sm")}>
          {t("print")}
        </button>
      </div>
      <header className="flex items-start justify-between gap-4 border-b-2 border-night-900 pb-3">
        <div className="flex flex-col gap-1">
          <Logo locale={locale} />
          <span className="text-caption text-ink-muted">{t("title")}</span>
        </div>
        <div className="flex flex-col items-end gap-1 text-small">
          <strong dir="ltr" className="text-[20px]">
            {slip.code}
          </strong>
          <span>{new Date(slip.created_at).toLocaleDateString(locale)}</span>
          {slip.gift && (
            <span className="rounded-full bg-amber-100 px-3 py-0.5 font-bold text-amber-700">{t("gift")}</span>
          )}
        </div>
      </header>

      {slip.gift && slip.gift_message && (
        <section className="rounded-2xl border-2 border-dashed border-amber-500 p-5 text-center">
          <h2 className="mb-2 text-small text-ink-muted">{t("giftMessage")}</h2>
          <p className="font-display text-[22px] leading-relaxed whitespace-pre-line text-night-900">
            {slip.gift_message}
          </p>
        </section>
      )}

      <section className="flex flex-col gap-1 text-small">
        <h2 className="font-semibold text-night-900">{t("recipient")}</h2>
        <p className="text-body font-semibold">{slip.recipient.name}</p>
        {slip.recipient.phone && (
          <p dir="ltr" className="self-start">
            {slip.recipient.phone}
          </p>
        )}
        <p>{[slip.recipient.city, slip.recipient.address].filter(Boolean).join(" — ")}</p>
        {slip.recipient.notes && <p className="text-ink-muted">{slip.recipient.notes}</p>}
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-small font-semibold text-night-900">{t("items")}</h2>
        <table className="w-full text-small">
          <tbody>
            {slip.items.map((it, i) => (
              <tr key={i} className="border-t border-line align-top">
                <td className="py-2 pe-3">
                  <strong className="block">{it.book_title ?? name(it)}</strong>
                  <span className="text-ink-muted">
                    {[name(it), tf(it.format || "digital"), it.child_name].filter(Boolean).join(" · ")}
                  </span>
                  {it.addons.length > 0 && (
                    <span className="block text-ink-muted">
                      {t("addons")}: {it.addons.map((a) => name(a) + (a.qty > 1 ? ` × ${a.qty}` : "")).join("، ")}
                    </span>
                  )}
                </td>
                <td className="py-2 pe-3 text-center whitespace-nowrap">{t("copies", { n: it.copies })}</td>
                {!slip.prices_hidden && <td className="py-2 text-end whitespace-nowrap">{amount(it.total)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {slip.prices_hidden ? (
        <p className="rounded-lg bg-paper-sunk px-3 py-2 text-small text-ink-muted print:hidden">{t("hidden")}</p>
      ) : (
        <section className="ms-auto flex w-full max-w-xs flex-col gap-1 text-small">
          <Line label={t("subtotal")} value={amount(slip.subtotal)} />
          {Number(slip.discount) > 0 && <Line label={t("discount")} value={`−${amount(slip.discount)}`} />}
          <Line label={t("delivery")} value={amount(slip.delivery_fee)} />
          {slip.gift_card && <Line label={t("giftCard")} value={`−${amount(slip.gift_card)}`} />}
          <Line label={slip.payment_method === "cod" ? t("dueCod") : t("total")} value={amount(slip.total)} strong />
        </section>
      )}
    </div>
  );
}

function Line({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-3 ${strong ? "border-t border-line pt-1 text-body font-bold" : ""}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
