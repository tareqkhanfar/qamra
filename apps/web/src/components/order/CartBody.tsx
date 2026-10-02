"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { Alert } from "@/components/ui/Alert";
import { Link } from "@/i18n/navigation";
import type { ThemeCard } from "@/lib/catalog";
import type { Child } from "@/lib/create";
import { bundleLabel, completeHref, editHref, type CrossSell, type OrderCart, type OrderItem } from "@/lib/order";
import { money, type Catalog } from "@/lib/store";
import { BookThumb, CheckBox } from "./parts";

const pill =
  "flex min-h-11 items-center rounded-full border-[1.5px] border-line px-3.5 text-small font-semibold text-night-900";

export function CartBody(props: {
  cart: OrderCart;
  catalog: Catalog | null;
  themes: ThemeCard[];
  kids: Child[];
  offer: CrossSell | null;
  busy: boolean;
  error: string | null;
  codeError: string | null;
  message: string;
  maxMessage: number;
  onRemove: (id: string) => void;
  onGift: (on: boolean) => void;
  onMessage: (text: string) => void;
  onMessageDone: () => void;
  onCode: (code: string) => Promise<boolean>;
  onClearCoupon: () => void;
  onClearCard: () => void;
}) {
  const { cart, offer, busy } = props;
  const t = useTranslations("orderPath");
  const tc = useTranslations("store.cart");
  const locale = useLocale();
  const [code, setCode] = useState("");
  const amount = (v: string | number) => money(v, cart.currency, locale);
  const minus = (v: string) => `−${amount(v)}`;
  const bundle = locale === "ar" ? cart.bundle_name_ar : cart.bundle_name_en;
  const firstName = offer?.child_name ?? "";

  return (
    <main className="flex flex-col gap-4 px-4 pt-5 pb-[150px]">
      {props.error && <Alert>{props.error}</Alert>}
      {cart.unavailable.length > 0 && <Alert tone="info">{tc("unavailable")}</Alert>}
      {cart.items.map((item) => (
        <Line key={item.id} item={item} {...props} amount={amount} />
      ))}

      {offer && (
        <div className="flex items-center gap-3 rounded-[18px] bg-paper-sunk px-3.5 py-3">
          <div className="flex grow flex-col gap-0.5">
            <strong className="text-[15px] text-ink">{t("cross.title", { name: firstName })}</strong>
            <span className="text-caption text-ink-muted">{t("cross.body", { gender: offer.gender })}</span>
          </div>
          <Link
            href={`/create?step=story&child=${offer.child_id}&character=${offer.character_id}&line=${offer.line}&style=${offer.style}`}
            className="flex min-h-11 items-center rounded-full bg-night-900 px-3.5 text-small font-bold whitespace-nowrap text-paper"
          >
            {offer.from_price ? `+ ${money(offer.from_price, offer.currency, locale)}` : t("cross.add")}
          </Link>
        </div>
      )}

      <section className="flex flex-col gap-3 rounded-[20px] border border-line bg-paper-raised p-3.5">
        <button
          type="button"
          aria-pressed={cart.gift}
          onClick={() => props.onGift(!cart.gift)}
          disabled={busy}
          className="flex min-h-12 items-center gap-3 text-start text-ink"
        >
          <CheckBox on={cart.gift} size={28} />
          <span className="flex grow flex-col">
            <strong className="text-body">{t("gift.title")}</strong>
            <span className="text-caption text-ink-muted">{t("gift.body")}</span>
          </span>
        </button>
        {cart.gift && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="gift-msg" className="text-small font-semibold">
              {t("gift.label")}
            </label>
            <textarea
              id="gift-msg"
              rows={3}
              maxLength={props.maxMessage}
              value={props.message}
              onChange={(e) => props.onMessage(e.target.value)}
              onBlur={props.onMessageDone}
              placeholder={t("gift.placeholder", {
                name: firstName || cart.items[0]?.child_name || "",
                gender: (firstName ? offer?.gender : cart.items[0]?.child_gender) ?? "other",
              })}
              className="resize-none rounded-[14px] border-[1.5px] border-line bg-white px-3.5 py-3 text-body outline-none focus:border-night-900"
            />
            <span className="flex justify-between text-xs text-ink-muted">
              <span>{t("gift.hint", { max: props.maxMessage })}</span>
              <span dir="ltr">
                {props.message.length}/{props.maxMessage}
              </span>
            </span>
          </div>
        )}
      </section>

      <form
        className="flex gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          if (code.trim() && (await props.onCode(code.trim()))) setCode("");
        }}
      >
        <label htmlFor="code" className="sr-only">
          {t("code.label")}
        </label>
        <input
          id="code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder={t("code.placeholder")}
          autoComplete="off"
          className="min-h-[52px] min-w-0 grow rounded-[14px] border-[1.5px] border-line bg-white px-3.5 text-body outline-none focus:border-night-900"
        />
        <button
          type="submit"
          disabled={busy}
          className="min-h-[52px] rounded-[14px] bg-night-900 px-[18px] text-[15px] font-bold text-paper disabled:opacity-60"
        >
          {t("code.apply")}
        </button>
      </form>
      {props.codeError && (
        <p role="alert" className="-mt-2 text-small text-danger">
          {props.codeError}
        </p>
      )}
      {cart.coupon_code && (
        <Applied
          label={t("code.coupon", { code: cart.coupon_code })}
          problem={cart.coupon_problem ? tc(`couponProblems.${cart.coupon_problem}`) : null}
          remove={t("code.remove")}
          onRemove={props.onClearCoupon}
        />
      )}
      {cart.gift_card && (
        <Applied
          label={t("code.card", { code: cart.gift_card })}
          problem={cart.gift_card_problem ? t(`code.cardProblems.${cart.gift_card_problem}`) : null}
          remove={t("code.remove")}
          onRemove={props.onClearCard}
        />
      )}

      <section aria-label={t("cart.summary")} className="flex flex-col gap-2 px-0.5 py-1 text-[15px]">
        <Row label={t("cart.subtotal")} value={amount(cart.subtotal)} />
        {Number(cart.sale_discount) > 0 && <Row good label={t("cart.sale")} value={minus(cart.sale_discount)} />}
        {cart.bundle && (
          <Row
            good
            label={t("cart.bundle", { name: bundleLabel(bundle ?? cart.bundle), pct: Number(cart.bundle_pct ?? 0) })}
            value={minus(cart.bundle_discount)}
          />
        )}
        {cart.coupon && (
          <Row good label={t("cart.coupon", { code: cart.coupon })} value={minus(cart.coupon_discount)} />
        )}
        {Number(cart.gift_card_amount) > 0 && (
          <Row good label={t("cart.giftCard")} value={minus(cart.gift_card_amount)} />
        )}
        <Row
          muted
          label={t("cart.shipping")}
          value={
            cart.zone
              ? Number(cart.shipping) > 0
                ? amount(cart.shipping)
                : t("cart.freeShipping")
              : t("cart.shippingNext")
          }
        />
        {Number(cart.cod_fee) > 0 && <Row label={t("cart.codFee")} value={amount(cart.cod_fee)} />}
        <div className="flex justify-between border-t border-line pt-2.5 text-[18px] font-bold text-ink">
          <span>{t("cart.total")}</span>
          <span>{amount(cart.total)}</span>
        </div>
      </section>
    </main>
  );
}

function Row({ label, value, good, muted }: { label: string; value: ReactNode; good?: boolean; muted?: boolean }) {
  return (
    <div
      className={`flex justify-between gap-3 ${good ? "font-semibold text-success" : muted ? "text-ink-muted" : "text-ink"}`}
    >
      <span>{label}</span>
      <span className="text-end">{value}</span>
    </div>
  );
}

function Applied(p: { label: string; problem: string | null; remove: string; onRemove: () => void }) {
  return (
    <div className="-mt-1 flex items-center justify-between gap-3 rounded-2xl bg-paper-sunk px-3.5 py-2 text-small">
      <span className="flex flex-col">
        <strong dir="auto">{p.label}</strong>
        {p.problem && <span className="text-danger">{p.problem}</span>}
      </span>
      <button type="button" onClick={p.onRemove} className="min-h-11 px-2 font-semibold text-danger">
        {p.remove}
      </button>
    </div>
  );
}

function Line({
  item,
  catalog,
  themes,
  kids,
  busy,
  onRemove,
  amount,
}: {
  item: OrderItem;
  catalog: Catalog | null;
  themes: ThemeCard[];
  kids: Child[];
  busy: boolean;
  onRemove: (id: string) => void;
  amount: (v: string | number) => string;
}) {
  const t = useTranslations("orderPath");
  const tf = useTranslations("store.formats");
  const locale = useLocale();
  const name = (x: { name_ar: string; name_en: string }) => (locale === "ar" ? x.name_ar : x.name_en);
  const style = catalog?.styles.find((s) => s.slug === item.style);
  const theme = themes.find((th) => th.slug === item.theme);
  const kid = kids.find((k) => k.id === item.child_id);
  const title =
    item.book_title ?? (item.child_name ? t("bookFor", { name: item.child_name }) : (theme?.name ?? name(item)));
  const details = [name(item), tf(item.options.format ?? "digital"), style ? name(style) : null];
  const lines = item.addons;
  return (
    <article className="flex flex-col gap-3 rounded-[20px] border border-line bg-paper-raised p-3.5">
      <div className="flex gap-3">
        {item.book_id || theme ? (
          <BookThumb art={theme?.art ?? null} hijab={kid?.hijab} size={80} />
        ) : (
          <ActivityThumb name={item.child_name} />
        )}
        <div className="flex grow flex-col gap-0.5">
          <strong className="text-body text-ink">
            {title}
            {item.qty > 1 && <span className="text-ink-muted"> × {item.qty}</span>}
          </strong>
          <span className="text-caption text-ink-muted">{details.filter(Boolean).join(" · ")}</span>
          {item.book_status === "preview" && (
            <span className="text-caption font-semibold text-success">{t("cart.previewReady")}</span>
          )}
          {item.needs_details && (
            <span className="text-caption font-semibold text-amber-700">{t("cart.needsDetails")}</span>
          )}
        </div>
        <strong className="text-body whitespace-nowrap text-ink">{amount(item.base)}</strong>
      </div>
      {lines.length > 0 && (
        <div className="flex flex-col gap-1.5 border-t border-dashed border-line pt-2.5 text-small">
          {lines.map((a) => {
            const free = a.included || Number(a.amount) === 0;
            return (
              <div key={a.slug} className={`flex justify-between gap-3 ${free ? "text-success" : ""}`}>
                <span>
                  {name(a)}
                  {a.qty > 1 && ` × ${a.qty}`}
                </span>
                <span className="whitespace-nowrap">{free ? t("free") : `+${amount(a.amount)}`}</span>
              </div>
            );
          })}
        </div>
      )}
      <div className="flex gap-2">
        {item.needs_details ? (
          <Link
            href={completeHref(item)}
            className="flex min-h-11 items-center rounded-full bg-night-900 px-3.5 text-small font-bold text-paper"
          >
            {t("cart.complete")}
          </Link>
        ) : (
          <Link href={editHref(item)} className={pill}>
            {item.book_id ? t("cart.editAddons") : t("cart.edit")}
          </Link>
        )}
        <button
          type="button"
          onClick={() => onRemove(item.id)}
          disabled={busy}
          className="min-h-11 px-3.5 text-small font-semibold text-danger"
        >
          {t("cart.remove")}
        </button>
      </div>
    </article>
  );
}

/** An activity book's cover in the cart (design: the child's name on a night cover with the amber spine). */
function ActivityThumb({ name }: { name: string | null }) {
  return (
    <div className="flex size-20 shrink-0 items-center justify-center rounded-[10px] bg-night-100">
      <svg width="54" height="70" viewBox="0 0 96 124" aria-hidden="true">
        <rect x="1" y="1" width="94" height="122" rx="6" fill="#16204A" />
        <rect x="84" y="1" width="11" height="122" fill="#F2B33D" />
        <text x="42" y="30" textAnchor="middle" fontSize="18" fontWeight="700" fill="#FBF6EC">
          {name ?? ""}
        </text>
        <circle cx="42" cy="78" r="22" fill="#E8B98F" />
        <path d="M20 76 A22 24 0 0 1 64 76 L64 90 L20 90 Z" fill="#E9826B" />
      </svg>
    </div>
  );
}
