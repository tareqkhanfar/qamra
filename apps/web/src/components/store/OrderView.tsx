"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses, Spinner } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { ORDER_STEPS, cartApi, money, orderPhone, type Tracked } from "@/lib/store";

const field = "min-h-12 w-full rounded-md border border-line bg-paper-raised px-3 text-body";

/** Order placed (design: Create11) and tracking (design: Tracking). */
export function OrderView({ code, placed }: { code: string; placed: boolean }) {
  const t = useTranslations("store.track");
  const tp = useTranslations("store.placed");
  const tc = useTranslations("store.cart");
  const locale = useLocale();
  const [order, setOrder] = useState<Tracked | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let live = true;
    const load = async () => {
      const phone = orderPhone.get(code);
      const r = phone ? await cartApi.track(code, phone) : null;
      if (!live) return;
      if (r?.ok) setOrder(r.data);
      else setMissing(true);
    };
    void load();
    return () => {
      live = false;
    };
  }, [code]);

  if (missing) return <TrackForm initialCode={code} />;
  if (!order) return <p className="py-10 text-center text-ink-muted">…</p>;

  const done = new Set(order.events.map((e) => e.status));
  const current = ORDER_STEPS.indexOf(order.status as (typeof ORDER_STEPS)[number]);
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6">
      {placed && (
        <div className="flex flex-col items-center gap-3 text-center">
          <MoonPhase p={1} className="size-20" />
          <h1 className="text-h2 text-night-900">{tp("title")}</h1>
          <p className="font-semibold">{tp("code", { code: order.code })}</p>
          <p className="text-ink-muted">{tp("next")}</p>
        </div>
      )}
      {!placed && <h1 className="text-h2 text-night-900">{t("title")}</h1>}
      <section className="flex flex-col gap-4 rounded-lg border border-line bg-paper-raised p-4">
        <div className="flex items-center justify-between">
          <strong className="text-[18px] text-night-900" dir="ltr">
            {order.code}
          </strong>
          <span className="rounded-full bg-amber-100 px-3 py-1 text-small font-bold text-amber-700">
            {t(`statuses.${order.status}`)}
          </span>
        </div>
        <ol className="flex flex-col gap-3">
          {ORDER_STEPS.map((step, i) => {
            const reached = done.has(step) || (current >= 0 && i <= current);
            return (
              <li key={step} className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className={`flex size-7 shrink-0 items-center justify-center rounded-full text-small font-bold ${reached ? "bg-night-900 text-paper" : "border border-line text-ink-muted"}`}
                >
                  {reached ? "✓" : i + 1}
                </span>
                <span className={reached ? "font-semibold text-night-900" : "text-ink-muted"}>
                  {t(`statuses.${step}`)}
                </span>
              </li>
            );
          })}
        </ol>
      </section>
      <section className="flex flex-col gap-2 rounded-lg bg-paper-sunk p-4 text-body">
        <h2 className="text-[17px] text-night-900">{t("items")}</h2>
        {order.items.map((item, i) => (
          <p key={i}>
            {item.child_name ? tc("bookFor", { name: item.child_name }) : locale === "ar" ? item.name_ar : item.name_en}
            {item.qty > 1 && ` ×${item.qty}`}
          </p>
        ))}
        <p className="flex justify-between border-t border-line pt-2 font-bold">
          <span>{t("total")}</span>
          <span>{money(order.total, order.currency, locale)}</span>
        </p>
      </section>
      <Link href="/" className={buttonClasses("secondary", "md", "self-center")}>
        {tp("home")}
      </Link>
    </div>
  );
}

export function TrackForm({ initialCode = "" }: { initialCode?: string }) {
  const t = useTranslations("store.track");
  const router = useRouter();
  const [code, setCode] = useState(initialCode);
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    const clean = code.trim().toUpperCase();
    const r = await cartApi.track(clean, phone);
    setBusy(false);
    if (!r.ok) {
      setError(true);
      return;
    }
    orderPhone.set(clean, phone);
    router.push(`/order/${clean}`);
    router.refresh();
  };
  return (
    <form onSubmit={submit} className="mx-auto flex max-w-md flex-col gap-4">
      <h1 className="text-h2 text-night-900">{t("title")}</h1>
      <p className="text-ink-muted">{t("intro")}</p>
      <label className="flex flex-col gap-1.5">
        <span className="font-semibold">{t("code")}</span>
        <input
          className={field}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          dir="ltr"
          required
          placeholder="QM-XXXXXX"
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="font-semibold">{t("phone")}</span>
        <input
          className={field}
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          type="tel"
          dir="ltr"
          required
        />
      </label>
      {error && <Alert>{t("notFound")}</Alert>}
      <button type="submit" disabled={busy} className={buttonClasses("solid", "lg", "justify-center")}>
        {busy ? <Spinner /> : t("find")}
      </button>
    </form>
  );
}
