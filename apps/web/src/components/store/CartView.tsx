"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api, errorText } from "@/lib/api";
import { cartApi, money, type Cart, type CartItem, type Catalog, type CatalogAddOn } from "@/lib/store";

/** Add-ons offered in the cart; the others are offered at their own step of the create flow (Addendum 4 §4). */
const CART_STEPS = new Set(["checkout"]);
const AUTOMATIC = new Set(["digital-copy"]);

function offered(addon: CatalogAddOn, item: CartItem): boolean {
  if (!CART_STEPS.has(addon.step) || AUTOMATIC.has(addon.slug)) return false;
  if (!addon.lines.includes(item.line) || addon.included_lines.includes(item.line)) return false;
  return Object.entries(addon.requires).every(([option, allowed]) => allowed.includes(item.options[option] ?? ""));
}

export function CartView() {
  const t = useTranslations("store.cart");
  const tl = useTranslations("store.lines");
  const tf = useTranslations("store.formats");
  const locale = useLocale();
  const [cart, setCart] = useState<Cart | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [code, setCode] = useState("");

  const apply = useCallback(
    async (call: Promise<Awaited<ReturnType<typeof cartApi.get>>>) => {
      setBusy(true);
      const r = await call;
      setBusy(false);
      if (r.ok) {
        setCart(r.data);
        setError(null);
      } else {
        setError(errorText(r.error, locale, t("empty")));
      }
    },
    [locale, t],
  );

  useEffect(() => {
    let live = true;
    void cartApi.get().then((r) => {
      if (live && r.ok) setCart(r.data);
    });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!cart) return;
    void api<Catalog>(`/api/store/catalog?currency=${cart.currency}`).then((r) => r.ok && setCatalog(r.data));
  }, [cart?.currency]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!cart) return <p className="py-10 text-center text-ink-muted">…</p>;
  if (cart.items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-xl bg-paper-sunk px-6 py-14 text-center">
        <h2 className="text-h3 text-night-900">{t("empty")}</h2>
        <p className="text-ink-muted">{t("emptyBody")}</p>
        <Link href="/themes" className={buttonClasses("solid", "md")}>
          {t("browse")}
        </Link>
      </div>
    );
  }

  const name = (x: { name_ar: string; name_en: string }) => (locale === "ar" ? x.name_ar : x.name_en);
  const amount = (value: string) => money(value, cart.currency, locale);
  const toggle = (item: CartItem, slug: string, on: boolean) => {
    const chosen = item.addons
      .filter((a) => !a.included && !AUTOMATIC.has(a.slug))
      .map((a) => ({ slug: a.slug, qty: a.qty }));
    const next = on ? [...chosen, { slug, qty: 1 }] : chosen.filter((a) => a.slug !== slug);
    void apply(cartApi.update(item.id, { addons: next }));
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
      <div className="flex flex-col gap-4">
        {error && <Alert>{error}</Alert>}
        {cart.unavailable.length > 0 && <Alert tone="info">{t("unavailable")}</Alert>}
        {cart.items.map((item) => {
          const extras = (catalog?.addons ?? []).filter((a) => offered(a, item));
          const chosen = new Set(item.addons.map((a) => a.slug));
          return (
            <article key={item.id} className="flex flex-col gap-3 rounded-lg border border-line bg-paper-raised p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-col gap-0.5">
                  <strong className="text-[18px] text-night-900">
                    {item.child_name ? t("bookFor", { name: item.child_name }) : name(item)}
                  </strong>
                  <span className="text-small text-ink-muted">
                    {tl(item.line)} · {tf(item.options.format ?? "digital")}
                  </span>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <strong className="text-[17px]">{amount(item.total)}</strong>
                  {Number(item.discount) > 0 && (
                    <span className="text-caption text-success">{t("saved", { amount: amount(item.discount) })}</span>
                  )}
                </div>
              </div>
              {item.addons.some((a) => a.included || AUTOMATIC.has(a.slug)) && (
                <div className="flex flex-wrap gap-1.5 text-caption">
                  {item.addons
                    .filter((a) => a.included || AUTOMATIC.has(a.slug))
                    .map((a) => (
                      <span key={a.slug} className="rounded-full bg-success-bg px-2.5 py-1 font-semibold text-success">
                        {name(a)} · {a.included ? t("included") : t("free")}
                      </span>
                    ))}
                </div>
              )}
              {extras.length > 0 && (
                <details className="group border-t border-line pt-3" open={extras.some((a) => chosen.has(a.slug))}>
                  <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between font-semibold text-night-900 [&::-webkit-details-marker]:hidden">
                    {t("extras")}
                    <span aria-hidden="true" className="transition group-open:rotate-180">
                      ⌄
                    </span>
                  </summary>
                  <fieldset className="flex min-w-0 flex-col gap-1">
                    <legend className="sr-only">{t("addOns")}</legend>
                    {extras.map((a) => (
                      <label key={a.slug} className="flex min-h-11 cursor-pointer items-center gap-3">
                        <input
                          type="checkbox"
                          className="size-5 accent-night-900"
                          checked={chosen.has(a.slug)}
                          disabled={busy}
                          onChange={(e) => toggle(item, a.slug, e.target.checked)}
                        />
                        <span className="grow">{name(a)}</span>
                        <span className="text-small text-ink-muted">
                          {a.percent
                            ? t("percentOff", { n: 100 - Number(a.percent) })
                            : a.price && Number(a.price) > 0
                              ? amount(a.price)
                              : t("free")}
                        </span>
                      </label>
                    ))}
                  </fieldset>
                </details>
              )}
              <button
                type="button"
                onClick={() => void apply(cartApi.remove(item.id))}
                disabled={busy}
                className="self-start text-small font-semibold text-danger underline underline-offset-4"
              >
                {t("remove")}
              </button>
            </article>
          );
        })}
      </div>

      <aside className="flex flex-col gap-4 rounded-lg bg-paper-sunk p-4 lg:sticky lg:top-28">
        <h2 className="text-[18px] text-night-900">{t("summary")}</h2>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (code.trim()) void apply(cartApi.coupon(code.trim()));
          }}
        >
          <label className="sr-only" htmlFor="coupon">
            {t("couponLabel")}
          </label>
          <input
            id="coupon"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={t("couponLabel")}
            className="min-h-11 min-w-0 grow rounded-md border border-line bg-paper-raised px-3 uppercase"
            autoComplete="off"
          />
          <button type="submit" disabled={busy} className={buttonClasses("secondary", "sm")}>
            {t("apply")}
          </button>
        </form>
        {cart.coupon_code && cart.coupon_problem && (
          <p className="text-small text-danger" role="status">
            {t(`couponProblems.${cart.coupon_problem}`)}{" "}
            <button type="button" className="underline" onClick={() => void apply(cartApi.clearCoupon())}>
              {t("removeCoupon")}
            </button>
          </p>
        )}
        <dl className="flex flex-col gap-2 text-body">
          <Row label={t("subtotal")} value={amount(cart.subtotal)} />
          {Number(cart.sale_discount) > 0 && <Row label={t("sale")} value={amount(cart.sale_discount)} good />}
          {cart.bundle && (
            <Row
              label={`${t("bundle")} (${t.has(`bundles.${cart.bundle}`) ? t(`bundles.${cart.bundle}`) : cart.bundle})`}
              value={amount(cart.bundle_discount)}
              good
            />
          )}
          {cart.coupon && <Row label={t("coupon", { code: cart.coupon })} value={amount(cart.coupon_discount)} good />}
          <Row
            label={t("shipping")}
            value={
              cart.zone ? (Number(cart.shipping) > 0 ? amount(cart.shipping) : t("freeShipping")) : t("shippingLater")
            }
          />
          {Number(cart.cod_fee) > 0 && <Row label={t("codFee")} value={amount(cart.cod_fee)} />}
          <div className="mt-1 flex items-center justify-between border-t border-line pt-3 text-[18px] font-bold text-night-900">
            <dt>{t("total")}</dt>
            <dd>{amount(cart.total)}</dd>
          </div>
        </dl>
        <Link href="/checkout" className={buttonClasses("solid", "lg", "w-full justify-center")}>
          {t("checkout")}
        </Link>
      </aside>
    </div>
  );
}

function Row({ label, value, good = false }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-ink-muted">{label}</dt>
      <dd className={good ? "font-semibold text-success" : "font-semibold"}>{value}</dd>
    </div>
  );
}
