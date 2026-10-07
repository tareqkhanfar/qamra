"use client";

/* eslint-disable @next/next/no-img-element -- the add-ons' small static photos from /public (lib/addonsMedia) */
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { useFlowFrame } from "@/components/create/Frame";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Button";
import { useRouter } from "@/i18n/navigation";
import { addonMedia, includedItems } from "@/lib/addonsMedia";
import { errorText } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import type { Book, Child } from "@/lib/create";
import { lineSummary, orderApi, toggleAddOn, type AddOnOffer, type AddOnsStep as Step } from "@/lib/order";
import { money, type Catalog } from "@/lib/store";
import { LineText } from "./LineSummary";
import { AddOnIcon, BookThumb, BottomBar, CheckBox, ctaClass, FlowHeader } from "./parts";

const on = (s: Step | null) => new Set((s?.addons ?? []).filter((a) => a.on).map((a) => a.slug));

/**
 * The add-ons of one cart line, by its id (`/api/store/cart/items/{id}/addons`): a story after its preview, an
 * activity book from the cart or its review step. The server offers only the active add-ons that fit the line
 * and its format; the taps are saved as they come, the last one winning.
 */
function useItemAddOns(itemId: string | null, onSaved?: (step: Step) => void) {
  const t = useTranslations("orderPath");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [step, setStep] = useState<Step | null>(null);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [said, setSaid] = useState("");
  const wanted = useRef<Set<string> | null>(null);
  const running = useRef<Promise<void> | null>(null);
  const saved = useRef(onSaved);
  useEffect(() => {
    saved.current = onSaved;
  }, [onSaved]);

  useEffect(() => {
    if (!itemId) return;
    let alive = true;
    void (async () => {
      const r = await orderApi.addons(itemId);
      if (!alive) return;
      if (r.ok) {
        setStep(r.data);
        setChosen(on(r.data));
      } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    })();
    return () => {
      alive = false;
    };
  }, [itemId, locale, te]);

  /** Saves the latest choice; taps made while saving are sent right after (the last one wins). */
  const save = useCallback(
    (next: Set<string>) => {
      wanted.current = next;
      if (running.current || !step) return;
      const id = step.item.id;
      running.current = (async () => {
        setSaving(true);
        while (wanted.current) {
          const slugs = [...wanted.current];
          wanted.current = null;
          const r = await orderApi.setAddons(id, slugs);
          if (r.ok) {
            setStep(r.data);
            if (!wanted.current) setChosen(on(r.data));
            setError(null);
            saved.current?.(r.data);
          } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
        }
        setSaving(false);
        running.current = null;
      })();
    },
    [locale, step, te],
  );

  const name = (a: { name_ar: string; name_en: string }) => (locale === "ar" ? a.name_ar : a.name_en);
  const comma = locale === "ar" ? "، " : ", ";
  const tap = (a: AddOnOffer) => {
    if (!step || a.locked) return;
    const next = toggleAddOn(step.addons, chosen, a.slug);
    const brought = step.addons.filter((o) => o.slug !== a.slug && next.has(o.slug) && !chosen.has(o.slug));
    const dropped = step.addons.filter((o) => o.slug !== a.slug && !next.has(o.slug) && chosen.has(o.slug));
    setSaid(
      brought.length
        ? t("addons.brought", { names: brought.map(name).join(comma), name: name(a) })
        : dropped.length
          ? t("addons.dropped", { names: dropped.map(name).join(comma), name: name(a) })
          : "",
    );
    setChosen(next);
    save(next);
  };

  /** Waits for the taps still being saved (before leaving the screen). */
  const flush = async () => {
    while (running.current) await running.current;
  };

  return { step, chosen, saving, error, said, tap, flush };
}

/**
 * The add-ons of a cart line, on their own: the cart (under each line) and the activity books' review step
 * (docs/plans/order-flows.md §c.8) show them by the line's id. `onSaved` gets the line after every change (the
 * cart then refreshes its totals). Nothing to offer: nothing shown, except what comes with the book.
 */
export function ItemAddOns({
  itemId,
  onSaved,
  className = "",
}: {
  itemId: string;
  onSaved?: (step: Step) => void;
  className?: string;
}) {
  const t = useTranslations("orderPath");
  const locale = useLocale();
  const s = useItemAddOns(itemId, onSaved);
  if (!s.step) {
    return s.error ? (
      <Alert>{s.error}</Alert>
    ) : (
      <p role="status" className="flex items-center gap-2 py-3 text-small text-ink-muted">
        <Spinner /> {t("loading")}
      </p>
    );
  }
  const step = s.step;
  const amount = (v: string | number) => money(v, step.currency, locale);
  return (
    <div className={`flex flex-col gap-2.5 ${className}`}>
      <WithTheBook product={step.item.product} />
      {step.addons.length === 0 && <p className="text-small text-ink-muted">{t("addons.none")}</p>}
      {step.addons.map((a) => (
        <Card key={a.slug} a={a} on={s.chosen.has(a.slug)} onTap={s.tap} amount={amount} offers={step.addons} />
      ))}
      <p aria-live="polite" className="text-caption text-ink-muted empty:hidden">
        {s.said}
      </p>
      {s.error && <Alert>{s.error}</Alert>}
    </div>
  );
}

/** «مع الكتاب»: what every copy of this product comes with (lib/addonsMedia `includedItems`), in one line. */
function WithTheBook({ product }: { product: string }) {
  const t = useTranslations("orderPath");
  const ar = useLocale() === "ar";
  const items = includedItems[product] ?? [];
  if (!items.length) return null;
  const list = items.map((i) => (ar ? i.title_ar : i.title_en)).join(ar ? "، " : ", ");
  return (
    <p className="flex items-start gap-2 rounded-2xl bg-success-bg px-3.5 py-2.5 text-small text-ink">
      <svg className="mt-0.5 size-[18px] shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M5 12l5 5L20 7" stroke="#2E7A52" strokeWidth="2.2" strokeLinecap="round" />
      </svg>
      <span>{t("addons.withBook", { items: list })}</span>
    </p>
  );
}

/** «الإضافات» after a story's preview (design AddOns): toggles with a live total from the server, "more" folded. */
export function AddOnsStep({
  child,
  book,
  item: itemId = null,
  theme,
  catalog,
  back,
}: {
  child: Child;
  book: Book;
  item?: string | null; // the cart line, when the flow knows it; else the line holding this book
  theme: ThemeCard | null;
  catalog: Catalog | null;
  back: () => void;
}) {
  const t = useTranslations("orderPath");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [found, setFound] = useState<string | null>(null); // the line holding this book, when not given
  const [missing, setMissing] = useState(false);
  const [lost, setLost] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);
  const s = useItemAddOns(itemId ?? found);
  const flow = useFlowFrame(); // inside the wizard: this story's «الخطوة n من N»

  useEffect(() => {
    if (itemId) return;
    let alive = true;
    void (async () => {
      const cart = await orderApi.cart();
      if (!alive) return;
      if (!cart.ok) return setLost(errorText(cart.error, locale, te("unknown")));
      const line = cart.data.items.find((i) => i.book_id === book.id);
      if (line) setFound(line.id);
      else setMissing(true);
    })();
    return () => {
      alive = false;
    };
  }, [book.id, itemId, locale, te]);

  async function toCart() {
    setLeaving(true);
    await s.flush();
    router.push("/cart");
  }

  const title = book.title ?? t("bookOf", { name: child.name });
  const header = (
    <FlowHeader
      title={title}
      back={{ label: t("back"), onClick: back }}
      label={t("addons.label")}
      note={flow ? `${t("stepOf", { n: flow.n, total: flow.total })} · ${t("addons.optional")}` : t("addons.optional")}
      moon={0.88}
      progress={flow ? flow.n / flow.total : undefined}
    />
  );
  const error = lost ?? (s.step ? null : s.error);
  if (missing || error || !s.step) {
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
        {header}
        <main className="flex flex-col gap-4 px-4 py-6">
          {missing ? (
            <Alert tone="info">{t("addons.missing")}</Alert>
          ) : error ? (
            <Alert>{error}</Alert>
          ) : (
            <p role="status" className="flex items-center gap-2 py-10 text-ink-muted">
              <Spinner /> {t("loading")}
            </p>
          )}
          {missing && (
            <button type="button" onClick={back} className={ctaClass}>
              {t("addons.backToFormat")}
            </button>
          )}
        </main>
      </div>
    );
  }

  const step = s.step;
  const item = step.item;
  const name = (x: { name_ar: string; name_en: string }) => (locale === "ar" ? x.name_ar : x.name_en);
  const amount = (v: string | number) => money(v, step.currency, locale);
  const product = catalog?.products.find((p) => p.slug === item.product);
  const style = catalog?.styles.find((x) => x.slug === item.style);
  const pages = Number(product?.features?.pages ?? 0);
  const digital = item.addons.some((a) => a.slug === "digital-copy");
  const main = step.addons.filter((a) => a.featured);
  const more = step.addons.filter((a) => !a.featured);
  const count = step.addons.filter((a) => a.on && !a.included).length;
  const summary = lineSummary(item, { product: name(item), theme: theme?.name, style: style ? name(style) : null });
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
      {header}
      <main className="flex flex-col gap-4 px-4 pt-5 pb-[130px]">
        <div className="flex items-center gap-3.5 rounded-[20px] border border-line bg-paper-raised p-3">
          <BookThumb art={theme?.art ?? null} hijab={child.hijab} size={72} />
          <LineText
            summary={summary}
            extra={[pages ? t("pages", { n: pages }) : null, digital ? t("addons.withDigital") : null]}
            className="grow"
          />
          <strong className="text-body whitespace-nowrap text-ink">{amount(item.unit_price)}</strong>
        </div>

        <div className="flex flex-col gap-1">
          <h1 className="text-[26px] leading-snug text-night-900">{t("addons.title")}</h1>
          <p className="text-[15px] text-ink-muted">{t("addons.lead")}</p>
        </div>
        <WithTheBook product={item.product} />

        {main.map((a) => (
          <Card key={a.slug} a={a} on={s.chosen.has(a.slug)} onTap={s.tap} amount={amount} offers={step.addons} />
        ))}

        {more.length > 0 && (
          <details
            className="group rounded-[18px] border border-line bg-paper-raised px-3.5"
            open={more.some((a) => s.chosen.has(a.slug)) || undefined}
          >
            <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between text-body font-bold text-night-900 [&::-webkit-details-marker]:hidden">
              {t("addons.more", { n: more.length })}
            </summary>
            <div className="flex flex-col gap-2.5 pb-3.5">
              {more.map((a) => (
                <Card key={a.slug} a={a} on={s.chosen.has(a.slug)} onTap={s.tap} amount={amount} offers={step.addons} />
              ))}
            </div>
          </details>
        )}

        {digital && (
          <div className="flex items-center gap-2.5 rounded-2xl bg-success-bg px-3.5 py-3 text-small text-ink">
            <svg className="size-5 shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 12l5 5L20 7" stroke="#2E7A52" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
            {t("addons.digitalIncluded")}
          </div>
        )}
        <p aria-live="polite" className="text-caption text-ink-muted empty:hidden">
          {s.said}
        </p>
        {s.error && <Alert>{s.error}</Alert>}
      </main>

      <BottomBar>
        <div className="flex flex-col">
          <span className="text-xs text-ink-muted">
            {count ? t("addons.countLabel", { n: count }) : t("addons.bookOnly")}
          </span>
          <strong className={`text-[19px] text-ink transition ${s.saving ? "opacity-50" : ""}`} aria-live="polite">
            {amount(item.subtotal)}
          </strong>
        </div>
        <button type="button" onClick={() => void toCart()} disabled={leaving} className={ctaClass}>
          {leaving ? <Spinner /> : t("addons.toCart")}
        </button>
      </BottomBar>
    </div>
  );
}

/** An add-on's photo (lib/addonsMedia, 4:3), or its drawn icon while it has none. */
function Thumb({ slug }: { slug: string }) {
  const ar = useLocale() === "ar";
  const media = addonMedia[slug];
  if (!media) return <AddOnIcon slug={slug} />;
  return (
    <img
      src={media.src}
      alt={ar ? media.alt_ar : media.alt_en}
      width={64}
      height={48}
      loading="lazy"
      className="h-12 w-16 shrink-0 rounded-[12px] bg-paper-sunk object-cover"
    />
  );
}

function Card({
  a,
  on,
  onTap,
  amount,
  offers,
}: {
  a: AddOnOffer;
  on: boolean;
  onTap: (a: AddOnOffer) => void;
  amount: (v: string) => string;
  offers: AddOnOffer[];
}) {
  const t = useTranslations("orderPath");
  const ar = useLocale() === "ar";
  const badge = ar ? a.badge_ar : a.badge_en;
  const desc = ar ? a.description_ar : a.description_en;
  const label = (slug: string) => {
    const known = offers.find((o) => o.slug === slug);
    return known ? (ar ? known.name_ar : known.name_en) : slug;
  };
  const names = a.blockers.map(label).join(ar ? "، " : ", ");
  const reason =
    a.locked === "needs"
      ? t("addons.lockedNeeds", { names })
      : a.locked === "excludes"
        ? t("addons.lockedExcludes", { names })
        : null;
  return (
    <button
      type="button"
      onClick={() => onTap(a)}
      aria-pressed={on}
      disabled={!!a.locked}
      className={`flex w-full items-center gap-3 rounded-[18px] px-3 py-3 text-start text-ink transition disabled:cursor-not-allowed disabled:opacity-60 ${on ? "border-2 border-amber-500 bg-[#FFF6E0]" : "border-[1.5px] border-line bg-paper-raised"}`}
    >
      <Thumb slug={a.slug} />
      <div className="flex min-w-0 grow flex-col gap-0.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <strong className="text-[15px]">{ar ? a.name_ar : a.name_en}</strong>
          {badge && (
            <span className="rounded-full bg-night-100 px-2 py-0.5 text-[11px] font-bold text-night-900">{badge}</span>
          )}
        </div>
        {desc && <span className="text-caption leading-normal text-ink-muted">{desc}</span>}
        {reason && <span className="text-caption font-semibold text-warning">{reason}</span>}
      </div>
      <div className="flex shrink-0 flex-col items-center gap-1.5">
        <strong className="text-[15px] whitespace-nowrap">{a.included ? t("free") : `+${amount(a.price)}`}</strong>
        <CheckBox on={on} />
      </div>
    </button>
  );
}
