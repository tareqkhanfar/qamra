"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses, Spinner } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { api, errorText } from "@/lib/api";
import { cartApi, money, orderPhone, type Cart, type Catalog, type CatalogZone } from "@/lib/store";

const field = "min-h-12 w-full rounded-md border border-line bg-paper-raised px-3 text-body focus:border-night-900";

/** Checkout (design: Create10): where to deliver, cash on delivery, and the order summary. */
export function CheckoutForm() {
  const t = useTranslations("store.checkout");
  const tc = useTranslations("store.cart");
  const locale = useLocale();
  const router = useRouter();
  const [cart, setCart] = useState<Cart | null>(null);
  const [zones, setZones] = useState<CatalogZone[]>([]);
  const [country, setCountry] = useState("PS");
  const [zone, setZone] = useState("");
  const [city, setCity] = useState("");
  const [form, setForm] = useState({ name: "", phone: "", address: "", notes: "" });
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void cartApi.get().then((r) => r.ok && setCart(r.data));
    void api<Catalog>("/api/store/catalog").then((r) => r.ok && setZones(r.data.zones));
  }, []);

  const countryZones = useMemo(() => zones.filter((z) => z.country === country), [zones, country]);
  const chosen = zones.find((z) => z.slug === zone);
  const name = (x: { name_ar: string; name_en: string }) => (locale === "ar" ? x.name_ar : x.name_en);

  const pickZone = async (slug: string) => {
    setZone(slug);
    setCity("");
    if (!slug) return;
    const r = await cartApi.zone(slug); // shipping and currency follow the zone
    if (r.ok) setCart(r.data);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const r = await cartApi.checkout({ ...form, zone, city, accept_terms: terms });
    setBusy(false);
    if (!r.ok) {
      setError(errorText(r.error, locale, tc("empty")));
      return;
    }
    orderPhone.set(r.data.code, form.phone);
    router.push(`/order/${r.data.code}?placed=1`);
  };

  if (!cart) return <p className="py-10 text-center text-ink-muted">…</p>;
  if (cart.items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-xl bg-paper-sunk px-6 py-14 text-center">
        <h2 className="text-h3 text-night-900">{tc("empty")}</h2>
        <Link href="/themes" className={buttonClasses("solid", "md")}>
          {tc("browse")}
        </Link>
      </div>
    );
  }
  const amount = (v: string) => money(v, cart.currency, locale);
  const discount = Number(cart.sale_discount) + Number(cart.bundle_discount) + Number(cart.coupon_discount);
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });

  return (
    <form onSubmit={submit} className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
      <div className="flex flex-col gap-5">
        <section className="flex flex-col gap-4 rounded-lg border border-line bg-paper-raised p-4">
          <h2 className="text-[20px] text-night-900">{t("where")}</h2>
          <label className="flex flex-col gap-1.5">
            <span className="font-semibold">{t("name")}</span>
            <input
              className={field}
              value={form.name}
              onChange={set("name")}
              autoComplete="name"
              required
              minLength={2}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="font-semibold">{t("phone")}</span>
            <input
              className={field}
              value={form.phone}
              onChange={set("phone")}
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              dir="ltr"
              required
            />
            <span className="text-caption text-ink-muted">{t("phoneHint")}</span>
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-1.5">
              <span className="font-semibold">{t("country")}</span>
              <select
                className={field}
                value={country}
                onChange={(e) => {
                  setCountry(e.target.value);
                  void pickZone("");
                }}
              >
                <option value="PS">{t("PS")}</option>
                <option value="JO">{t("JO")}</option>
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="font-semibold">{t("zone")}</span>
              <select className={field} value={zone} onChange={(e) => void pickZone(e.target.value)} required>
                <option value="">—</option>
                {countryZones.map((z) => (
                  <option key={z.slug} value={z.slug}>
                    {name(z)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {chosen && (
            <label className="flex flex-col gap-1.5">
              <span className="font-semibold">{t("city")}</span>
              <select className={field} value={city} onChange={(e) => setCity(e.target.value)} required>
                <option value="">{t("chooseCity")}</option>
                {chosen.cities.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="flex flex-col gap-1.5">
            <span className="font-semibold">{t("address")}</span>
            <input
              className={field}
              value={form.address}
              onChange={set("address")}
              autoComplete="street-address"
              required
              minLength={5}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="font-semibold">{t("notes")}</span>
            <textarea className={`${field} min-h-20 py-2`} value={form.notes} onChange={set("notes")} maxLength={500} />
          </label>
        </section>

        <section className="flex flex-col gap-3 rounded-lg border border-line bg-paper-raised p-4">
          <h2 className="text-[20px] text-night-900">{t("payment")}</h2>
          <label className="flex items-start gap-3 rounded-md border-2 border-night-900 p-3">
            <input type="radio" name="payment" defaultChecked className="mt-1 size-5 accent-night-900" />
            <span className="flex flex-col">
              <strong>{t("cod")}</strong>
              <span className="text-small text-ink-muted">{t("codBody")}</span>
            </span>
          </label>
          <label className="flex items-center gap-3 rounded-md border border-line p-3 text-ink-muted">
            <input type="radio" name="payment" disabled className="size-5" />
            {t("card")}
          </label>
        </section>
      </div>

      <aside className="flex flex-col gap-4 rounded-lg bg-paper-sunk p-4 lg:sticky lg:top-28">
        <h2 className="text-[18px] text-night-900">{tc("summary")}</h2>
        <ul className="flex flex-col gap-2 text-body">
          {cart.items.map((item) => (
            <li key={item.id} className="flex justify-between gap-3">
              <span>{item.child_name ? tc("bookFor", { name: item.child_name }) : name(item)}</span>
              <strong>{amount(item.total)}</strong>
            </li>
          ))}
        </ul>
        <dl className="flex flex-col gap-2 border-t border-line pt-3">
          {discount > 0 && (
            <div className="flex justify-between text-success">
              <dt>{tc("discounts")}</dt>
              <dd>{amount(String(discount))}</dd>
            </div>
          )}
          <div className="flex justify-between">
            <dt className="text-ink-muted">{tc("shipping")}</dt>
            <dd className="font-semibold">
              {cart.zone
                ? Number(cart.shipping) > 0
                  ? amount(cart.shipping)
                  : tc("freeShipping")
                : tc("shippingLater")}
            </dd>
          </div>
          <div className="flex justify-between text-[18px] font-bold text-night-900">
            <dt>{tc("total")}</dt>
            <dd>{amount(cart.total)}</dd>
          </div>
        </dl>
        {chosen && (
          <p className="text-small text-ink-muted">{t("eta", { min: chosen.eta_days[0], max: chosen.eta_days[1] })}</p>
        )}
        <label className="flex items-start gap-3 text-small">
          <input
            type="checkbox"
            className="mt-0.5 size-5 accent-night-900"
            checked={terms}
            onChange={(e) => setTerms(e.target.checked)}
            required
          />
          <span>
            {t("terms")}{" "}
            <Link href="/privacy" className="underline underline-offset-4">
              ↗
            </Link>
          </span>
        </label>
        {error && <Alert>{error}</Alert>}
        <button
          type="submit"
          disabled={busy || !terms}
          className={buttonClasses("solid", "lg", "w-full justify-center")}
        >
          {busy ? <Spinner /> : t("confirm", { total: amount(cart.total) })}
        </button>
        <Link href="/cart" className="text-center text-small underline underline-offset-4">
          {t("back")}
        </Link>
      </aside>
    </form>
  );
}
