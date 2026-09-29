"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { api, errorText } from "@/lib/api";
import { TOTAL_STEPS } from "@/lib/create";
import { bundleLabel, orderApi, type OrderCart } from "@/lib/order";
import { cartApi, money, orderPhone, type Catalog, type CatalogZone } from "@/lib/store";
import { BottomBar, ctaClass, FlowHeader } from "./parts";

const field =
  "min-h-[52px] w-full rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body outline-none focus:border-night-900";

/** «إتمام الطلب» (design Create10): where to deliver, cash on delivery, and the server's order summary. */
export function CheckoutScreen() {
  const t = useTranslations("orderPath");
  const tf = useTranslations("store.formats");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [cart, setCart] = useState<OrderCart | null>(null);
  const [zones, setZones] = useState<CatalogZone[]>([]);
  const [country, setCountry] = useState("PS");
  const [city, setCity] = useState("");
  const [form, setForm] = useState({ name: "", phone: "", address: "" });
  const [busy, setBusy] = useState(false);
  const [zoning, setZoning] = useState(false); // the city's delivery fee is on its way from the server
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void (async () => {
      const [c, store] = await Promise.all([orderApi.cart(), api<Catalog>("/api/store/catalog")]);
      if (!alive) return;
      if (c.ok) setCart((newer) => newer ?? c.data); // never over a cart a city choice already updated
      if (store.ok) setZones(store.data.zones);
    })();
    return () => {
      alive = false;
    };
  }, []);

  /** Every city of the country with its delivery zone (the zone sets the fee and the currency). */
  const cities = useMemo(
    () => zones.filter((z) => z.country === country).flatMap((z) => z.cities.map((c) => ({ city: c, zone: z }))),
    [zones, country],
  );
  const chosen = cities.find((c) => c.city === city)?.zone;

  async function pickCity(value: string) {
    setCity(value);
    const zone = cities.find((c) => c.city === value)?.zone;
    if (!zone) return;
    setZoning(true);
    const r = await orderApi.zone(zone.slug); // delivery and currency follow the city's zone
    setZoning(false);
    if (r.ok) setCart(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!chosen) return;
    setBusy(true);
    setError(null);
    const r = await cartApi.checkout({ ...form, zone: chosen.slug, city, accept_terms: true });
    if (r.ok) {
      orderPhone.set(r.data.code, form.phone);
      router.push(`/order/${r.data.code}?placed=1`);
      return;
    }
    setBusy(false);
    setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    if (r.error?.code === "gift_card_changed") {
      const fresh = await orderApi.cart(); // show the new total before the parent confirms again
      if (fresh.ok) setCart(fresh.data);
    }
  }

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });
  const header = (
    <FlowHeader
      title={t("checkout.title")}
      back={{ label: t("back"), href: "/cart" }}
      label={t("checkout.label")}
      note={t("stepOf", { n: TOTAL_STEPS - 1, total: TOTAL_STEPS })}
      moon={0.92}
      progress={(TOTAL_STEPS - 1) / TOTAL_STEPS}
    />
  );
  if (!cart || cart.items.length === 0) {
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
        {header}
        <main className="flex flex-col gap-4 px-4 py-6">
          {cart ? (
            <Link href="/shop" className={ctaClass}>
              {t("cart.toShop")}
            </Link>
          ) : (
            <p className="text-ink-muted">…</p>
          )}
        </main>
      </div>
    );
  }
  const amount = (v: string | number) => money(v, cart.currency, locale);
  const name = (x: { name_ar: string; name_en: string }) => (locale === "ar" ? x.name_ar : x.name_en);
  const discount = Number(cart.sale_discount) + Number(cart.coupon_discount);
  return (
    <form onSubmit={submit} className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
      {header}
      <main className="flex flex-col gap-5 px-4 pt-5 pb-[130px]">
        <section className="flex flex-col gap-3.5">
          <h2 className="text-[20px] text-night-900">{cart.gift ? t("checkout.whereGift") : t("checkout.where")}</h2>
          {cart.gift && <p className="-mt-2 text-small text-ink-muted">{t("checkout.giftNote")}</p>}
          <Field id="o-name" label={t("checkout.name")}>
            <input
              id="o-name"
              className={field}
              value={form.name}
              onChange={set("name")}
              autoComplete="name"
              required
              minLength={2}
            />
          </Field>
          <Field id="o-phone" label={t("checkout.phone")} hint={t("checkout.phoneHint")}>
            <input
              id="o-phone"
              className={`${field} text-right`}
              dir="ltr"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={form.phone}
              onChange={set("phone")}
              required
            />
          </Field>
          <div className="grid grid-cols-2 gap-2.5">
            <Field id="o-country" label={t("checkout.country")}>
              <select
                id="o-country"
                className={`${field} px-3`}
                value={country}
                onChange={(e) => {
                  setCountry(e.target.value);
                  setCity("");
                }}
              >
                <option value="PS">{t("checkout.PS")}</option>
                <option value="JO">{t("checkout.JO")}</option>
              </select>
            </Field>
            <Field id="o-city" label={t("checkout.city")}>
              <select
                id="o-city"
                className={`${field} px-3`}
                value={city}
                onChange={(e) => void pickCity(e.target.value)}
                required
              >
                <option value="">{t("checkout.chooseCity")}</option>
                {cities.map((c) => (
                  <option key={c.city} value={c.city}>
                    {c.city}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field id="o-addr" label={t("checkout.address")}>
            <textarea
              id="o-addr"
              rows={2}
              className={`${field} resize-none py-3`}
              placeholder={t("checkout.addressPlaceholder")}
              value={form.address}
              onChange={set("address")}
              autoComplete="street-address"
              required
              minLength={5}
            />
          </Field>
        </section>

        <section className="flex flex-col gap-2.5">
          <h2 className="text-[20px] text-night-900">{t("checkout.payment")}</h2>
          <label className="flex min-h-16 items-center gap-3 rounded-2xl border-2 border-night-900 bg-night-100 px-4 py-3">
            <input type="radio" name="pay" defaultChecked className="size-[22px] accent-night-900" />
            <span className="flex flex-col">
              <strong className="text-body">{t("checkout.cod")}</strong>
              <span className="text-caption text-ink-muted">{t("checkout.codBody")}</span>
            </span>
          </label>
          <div className="flex min-h-14 items-center rounded-2xl bg-paper-sunk px-4 py-3 text-small text-ink-muted">
            {t("checkout.card")}
          </div>
        </section>

        <section
          aria-label={t("cart.summary")}
          className="flex flex-col gap-3 rounded-[20px] border border-line bg-paper-raised p-4"
        >
          {cart.items.map((item) => (
            <div key={item.id} className="flex items-center justify-between gap-3">
              <span className="flex flex-col">
                <strong className="text-[15px] text-ink">
                  {item.book_title ?? (item.child_name ? t("bookFor", { name: item.child_name }) : name(item))}
                </strong>
                <span className="text-caption text-ink-muted">
                  {name(item)} · {tf(item.options.format ?? "digital")}
                  {item.addons.some((a) => !a.included && Number(a.amount) > 0)
                    ? ` · ${t("checkout.withAddons", { n: item.addons.filter((a) => Number(a.amount) > 0).length })}`
                    : ""}
                </span>
              </span>
              <span className="text-[15px] whitespace-nowrap">{amount(item.subtotal)}</span>
            </div>
          ))}
          <div className="flex flex-col gap-2 border-t border-dashed border-line pt-3 text-[15px]">
            {cart.bundle && Number(cart.bundle_discount) > 0 && (
              <Row
                good
                label={t("cart.bundle", {
                  name: bundleLabel((locale === "ar" ? cart.bundle_name_ar : cart.bundle_name_en) ?? cart.bundle),
                  pct: Number(cart.bundle_pct ?? 0),
                })}
                value={`−${amount(cart.bundle_discount)}`}
              />
            )}
            {discount > 0 && <Row good label={t("checkout.discounts")} value={`−${amount(discount)}`} />}
            {Number(cart.gift_card_amount) > 0 && (
              <Row good label={t("cart.giftCard")} value={`−${amount(cart.gift_card_amount)}`} />
            )}
            <Row
              label={city ? t("checkout.deliveryTo", { city }) : t("cart.shipping")}
              value={
                zoning
                  ? "…"
                  : cart.zone
                    ? Number(cart.shipping) + Number(cart.cod_fee) > 0
                      ? amount(Number(cart.shipping) + Number(cart.cod_fee))
                      : t("cart.freeShipping")
                    : t("checkout.chooseCityFirst")
              }
            />
            <div className="flex justify-between text-[17px] font-bold text-ink">
              <span>{t("cart.total")}</span>
              <span>{amount(cart.total)}</span>
            </div>
          </div>
          {chosen && (
            <span className="text-caption text-ink-muted">
              {t("checkout.eta", { min: chosen.eta_days[0], max: chosen.eta_days[1] })}
            </span>
          )}
        </section>
        {error && <Alert>{error}</Alert>}
      </main>

      <BottomBar column>
        <button type="submit" disabled={busy || zoning || !chosen || !cart.zone} className={ctaClass}>
          {busy ? <Spinner /> : t("checkout.confirm", { total: amount(cart.total) })}
        </button>
        <span className="text-center text-xs text-ink-muted">
          {t("checkout.terms")}{" "}
          <Link href="/privacy" className="text-amber-700 underline">
            {t("checkout.termsLink")}
          </Link>
        </span>
      </BottomBar>
    </form>
  );
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-small font-semibold">
        {label}
      </label>
      {children}
      {hint && <span className="text-xs text-ink-muted">{hint}</span>}
    </div>
  );
}

function Row({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className={`flex justify-between gap-3 ${good ? "font-semibold text-success" : "text-ink"}`}>
      <span>{label}</span>
      <span className="text-end">{value}</span>
    </div>
  );
}
