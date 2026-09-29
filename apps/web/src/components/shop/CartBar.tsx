"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { cartApi, money, type Cart } from "@/lib/store";

/** Design Shop: the sticky cart bar (count and total from the cart API); hidden while the cart is empty. */
export function CartBar() {
  const t = useTranslations("shop");
  const locale = useLocale();
  const [cart, setCart] = useState<Cart | null>(null);
  useEffect(() => {
    let alive = true;
    void (async () => {
      const r = await cartApi.get();
      if (alive && r.ok) setCart(r.data);
    })();
    return () => {
      alive = false;
    };
  }, []);
  if (!cart || cart.count === 0) return null;
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper/97 pt-3 pb-[max(16px,env(safe-area-inset-bottom))] backdrop-blur">
      <div className="mx-auto flex max-w-[1200px] items-center gap-3 px-4 md:px-10">
        <div className="flex flex-col">
          <span className="text-xs text-ink-muted">{t("inCart", { n: cart.count })}</span>
          <strong className="text-[17px]">{money(cart.total, cart.currency, locale)}</strong>
        </div>
        <Link
          href="/cart"
          className="flex min-h-14 grow items-center justify-center rounded-full bg-night-900 px-6 text-[17px] font-bold text-paper md:max-w-[320px] md:grow-0 ltr:md:ml-auto rtl:md:mr-auto"
        >
          {t("openCart")}
        </Link>
      </div>
    </div>
  );
}
