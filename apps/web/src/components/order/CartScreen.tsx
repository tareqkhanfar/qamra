"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Link } from "@/i18n/navigation";
import { api, errorText, type ApiResult } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import { createApi, type Child } from "@/lib/create";
import { completeHref, GIFT_MESSAGE_MAX, lineSummary, orderApi, type CrossSell, type OrderCart } from "@/lib/order";
import type { Catalog } from "@/lib/store";
import { CartBody } from "./CartBody";
import { useSummaryText } from "./LineSummary";
import { BottomBar, ctaClass, FlowHeader } from "./parts";

/** «السلة» (design Cart): the books with their add-on lines, the gift and its card message, one field for a
 * discount code or a gift card, the character cross-sell, and the server's totals. */
export function CartScreen() {
  const t = useTranslations("orderPath");
  const tc = useTranslations("store.cart");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [cart, setCart] = useState<OrderCart | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [themes, setThemes] = useState<ThemeCard[]>([]);
  const [kids, setKids] = useState<Child[]>([]);
  const [offers, setOffers] = useState<CrossSell[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeError, setCodeError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const text = useSummaryText();

  const refreshOffers = useCallback(async () => {
    const r = await orderApi.crossSell();
    setOffers(r.ok ? r.data : []);
  }, []);

  useEffect(() => {
    let alive = true;
    void (async () => {
      const [c, worlds, children] = await Promise.all([
        orderApi.cart(),
        api<ThemeCard[]>(`/api/themes?lang=${locale}`),
        createApi.children(), // signed-in parents: the look of each child on the book thumbnails
      ]);
      if (!alive) return;
      if (!c.ok) return setError(errorText(c.error, locale, te("unknown")));
      setCart((newer) => newer ?? c.data); // a change made meanwhile wins
      setMessage(c.data.gift_message ?? "");
      if (worlds.ok) setThemes(worlds.data);
      if (children.ok) setKids(children.data);
      const [store] = await Promise.all([
        api<Catalog>(`/api/store/catalog?currency=${c.data.currency}`),
        refreshOffers(),
      ]);
      if (alive && store.ok) setCatalog(store.data);
    })();
    return () => {
      alive = false;
    };
  }, [locale, refreshOffers, te]);

  /** Every change goes through the server; the cart shown is always the one it returns. */
  async function apply(call: Promise<ApiResult<OrderCart>>, onError = setError): Promise<boolean> {
    setBusy(true);
    const r = await call;
    setBusy(false);
    if (r.ok) {
      setCart(r.data);
      onError(null);
      return true;
    }
    onError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    return false;
  }

  const saveMessage = (text: string) => void apply(orderApi.gift(true, text));
  const typeMessage = (text: string) => {
    setMessage(text);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => saveMessage(text), 700);
  };

  const header = (n: number) => (
    <FlowHeader title={t("cart.title", { n })} back={{ label: t("cart.backToShop"), href: "/shop" }} />
  );
  if (!cart) {
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
        {header(0)}
        <main className="px-4 py-6">{error ? <Alert>{error}</Alert> : <p className="text-ink-muted">…</p>}</main>
      </div>
    );
  }
  if (cart.items.length === 0) {
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
        {header(0)}
        <main className="flex flex-col items-center gap-4 px-6 py-14 text-center">
          <h1 className="text-h3 text-night-900">{tc("empty")}</h1>
          <p className="text-ink-muted">{tc("emptyBody")}</p>
          <Link href="/shop" className={`${ctaClass} max-w-xs`}>
            {t("cart.toShop")}
          </Link>
        </main>
      </div>
    );
  }

  // a line added in one tap waits for the child: the bar leads there before the address and payment
  const waiting = cart.items.find((i) => i.needs_details);
  const waitingName = waiting
    ? text(
        lineSummary(waiting, {
          product: locale === "ar" ? waiting.name_ar : waiting.name_en,
          theme: themes.find((th) => th.slug === waiting.theme)?.name,
        }).title,
      )
    : "";

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
      {header(cart.count)}
      <CartBody
        cart={cart}
        catalog={catalog}
        themes={themes}
        kids={kids}
        offer={offers[0] ?? null}
        busy={busy}
        error={error}
        codeError={codeError}
        message={message}
        maxMessage={GIFT_MESSAGE_MAX}
        onRemove={async (id) => {
          if (await apply(orderApi.remove(id))) void refreshOffers();
        }}
        onAddOns={async () => {
          const r = await orderApi.cart(); // the line's add-ons are saved: the totals, discounts and delivery again
          if (r.ok) setCart(r.data);
        }}
        onGift={(on) => void apply(orderApi.gift(on, on ? message : undefined))}
        onMessage={typeMessage}
        onMessageDone={() => {
          if (timer.current) clearTimeout(timer.current);
          if ((cart.gift_message ?? "") !== message.trim()) saveMessage(message);
        }}
        onCode={(code) => apply(orderApi.code(code), setCodeError)}
        onClearCoupon={() => void apply(orderApi.clearCoupon())}
        onClearCard={() => void apply(orderApi.clearGiftCard())}
      />
      <BottomBar column>
        {waiting ? (
          <>
            <span className="text-center text-small font-semibold text-ink">
              {t("cart.completeFirst", { name: waitingName })}
            </span>
            <Link href={completeHref(waiting)} className={ctaClass}>
              {t("cart.complete")}
            </Link>
          </>
        ) : (
          <Link href="/checkout" className={ctaClass}>
            {t("cart.next")}
          </Link>
        )}
        <span className="text-center text-xs text-ink-muted">{t("cart.codNote")}</span>
      </BottomBar>
    </div>
  );
}
