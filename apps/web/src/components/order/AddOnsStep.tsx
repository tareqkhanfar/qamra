"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Button";
import { useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import type { Book, Child } from "@/lib/create";
import { orderApi, toggleAddOn, type AddOnOffer, type AddOnsStep as Step } from "@/lib/order";
import { money, type Catalog } from "@/lib/store";
import { AddOnIcon, BookThumb, BottomBar, CheckBox, ctaClass, FlowHeader } from "./parts";

const on = (s: Step | null) => new Set((s?.addons ?? []).filter((a) => a.on).map((a) => a.slug));

/** «الإضافات» after the preview (design AddOns): toggles with a live total from the server, "more" folded. */
export function AddOnsStep({
  child,
  book,
  theme,
  catalog,
  back,
}: {
  child: Child;
  book: Book;
  theme: ThemeCard | null;
  catalog: Catalog | null;
  back: () => void;
}) {
  const t = useTranslations("orderPath");
  const tf = useTranslations("store.formats");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [step, setStep] = useState<Step | null>(null);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [missing, setMissing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [said, setSaid] = useState("");
  const wanted = useRef<Set<string> | null>(null);
  const running = useRef<Promise<void> | null>(null);

  useEffect(() => {
    let alive = true;
    void (async () => {
      const cart = await orderApi.cart();
      const item = cart.ok ? cart.data.items.find((i) => i.book_id === book.id) : undefined;
      if (!item) {
        if (alive) setMissing(true);
        return;
      }
      const r = await orderApi.addons(item.id);
      if (!alive) return;
      if (r.ok) {
        setStep(r.data);
        setChosen(on(r.data));
      } else setError(errorText(r.error, locale, te("unknown")));
    })();
    return () => {
      alive = false;
    };
  }, [book.id, locale, te]);

  /** Saves the latest choice; taps made while saving are sent right after (the last one wins). */
  const save = useCallback(
    (next: Set<string>) => {
      wanted.current = next;
      if (running.current || !step) return;
      const itemId = step.item.id;
      running.current = (async () => {
        setSaving(true);
        while (wanted.current) {
          const slugs = [...wanted.current];
          wanted.current = null;
          const r = await orderApi.setAddons(itemId, slugs);
          if (r.ok) {
            setStep(r.data);
            if (!wanted.current) setChosen(on(r.data));
            setError(null);
          } else setError(errorText(r.error, locale, te("unknown")));
        }
        setSaving(false);
        running.current = null;
      })();
    },
    [locale, step, te],
  );

  const name = (a: { name_ar: string; name_en: string }) => (locale === "ar" ? a.name_ar : a.name_en);
  const tap = (a: AddOnOffer) => {
    if (!step || a.locked) return;
    const next = toggleAddOn(step.addons, chosen, a.slug);
    const brought = step.addons.filter((o) => o.slug !== a.slug && next.has(o.slug) && !chosen.has(o.slug));
    const dropped = step.addons.filter((o) => o.slug !== a.slug && !next.has(o.slug) && chosen.has(o.slug));
    setSaid(
      brought.length
        ? t("addons.brought", { names: brought.map(name).join("، "), name: name(a) })
        : dropped.length
          ? t("addons.dropped", { names: dropped.map(name).join("، "), name: name(a) })
          : "",
    );
    setChosen(next);
    save(next);
  };

  async function toCart() {
    setLeaving(true);
    while (running.current) await running.current;
    router.push("/cart");
  }

  const title = book.title ?? t("bookOf", { name: child.name });
  const header = (
    <FlowHeader
      title={title}
      back={{ label: t("back"), onClick: back }}
      label={t("addons.label")}
      note={t("addons.optional")}
      moon={0.88}
    />
  );
  if (missing || error || !step) {
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

  const item = step.item;
  const amount = (v: string | number) => money(v, step.currency, locale);
  const product = catalog?.products.find((p) => p.slug === item.product);
  const style = catalog?.styles.find((s) => s.slug === item.style);
  const pages = Number(product?.features?.pages ?? 0);
  const digital = item.addons.some((a) => a.slug === "digital-copy");
  const main = step.addons.filter((a) => a.featured);
  const more = step.addons.filter((a) => !a.featured);
  const count = step.addons.filter((a) => a.on && !a.included).length;
  const label = (slug: string) => {
    const known = step.addons.find((a) => a.slug === slug) ?? catalog?.addons.find((a) => a.slug === slug);
    return known ? name(known) : slug;
  };
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
      {header}
      <main className="flex flex-col gap-4 px-4 pt-5 pb-[130px]">
        <div className="flex items-center gap-3.5 rounded-[20px] border border-line bg-paper-raised p-3">
          <BookThumb art={theme?.art ?? null} hijab={child.hijab} size={72} />
          <div className="flex grow flex-col gap-0.5">
            <strong className="text-body text-ink">
              {name(item)} · {tf(item.options.format ?? "digital")}
            </strong>
            <span className="text-caption text-ink-muted">
              {[
                style ? name(style) : null,
                pages ? t("pages", { n: pages }) : null,
                digital ? t("addons.withDigital") : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
          </div>
          <strong className="text-body whitespace-nowrap text-ink">{amount(item.unit_price)}</strong>
        </div>

        <div className="flex flex-col gap-1">
          <h1 className="text-[26px] leading-snug text-night-900">{t("addons.title")}</h1>
          <p className="text-[15px] text-ink-muted">{t("addons.lead")}</p>
        </div>

        {main.map((a) => (
          <Card key={a.slug} a={a} on={chosen.has(a.slug)} onTap={tap} amount={amount} label={label} icon />
        ))}

        {more.length > 0 && (
          <details
            className="group rounded-[18px] border border-line bg-paper-raised px-3.5"
            open={more.some((a) => chosen.has(a.slug)) || undefined}
          >
            <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between text-body font-bold text-night-900 [&::-webkit-details-marker]:hidden">
              {t("addons.more", { n: more.length })}
            </summary>
            <div className="flex flex-col gap-2.5 pb-3.5">
              {more.map((a) => (
                <Card key={a.slug} a={a} on={chosen.has(a.slug)} onTap={tap} amount={amount} label={label} />
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
          {said}
        </p>
        {error && <Alert>{error}</Alert>}
      </main>

      <BottomBar>
        <div className="flex flex-col">
          <span className="text-xs text-ink-muted">
            {count ? t("addons.countLabel", { n: count }) : t("addons.bookOnly")}
          </span>
          <strong className={`text-[19px] text-ink transition ${saving ? "opacity-50" : ""}`} aria-live="polite">
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

function Card({
  a,
  on,
  onTap,
  amount,
  label,
  icon = false,
}: {
  a: AddOnOffer;
  on: boolean;
  onTap: (a: AddOnOffer) => void;
  amount: (v: string) => string;
  label: (slug: string) => string;
  icon?: boolean;
}) {
  const t = useTranslations("orderPath");
  const ar = useLocale() === "ar";
  const badge = ar ? a.badge_ar : a.badge_en;
  const desc = ar ? a.description_ar : a.description_en;
  const names = a.blockers.map(label).join("، ");
  const reason =
    a.locked === "needs"
      ? t("addons.lockedNeeds", { names })
      : a.locked === "excludes"
        ? t("addons.lockedExcludes", { names })
        : null;
  const price = (
    <strong className="text-[15px] whitespace-nowrap">{a.included ? t("free") : `+${amount(a.price)}`}</strong>
  );
  return (
    <button
      type="button"
      onClick={() => onTap(a)}
      aria-pressed={on}
      disabled={!!a.locked}
      className={`flex w-full items-center gap-3 rounded-[18px] px-3.5 py-3 text-start text-ink transition disabled:cursor-not-allowed disabled:opacity-60 ${on ? "border-2 border-amber-500 bg-[#FFF6E0]" : "border-[1.5px] border-line bg-paper-raised"}`}
    >
      {icon && <AddOnIcon slug={a.slug} />}
      <div className="flex grow flex-col gap-0.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <strong className={icon ? "text-body" : "text-[15px]"}>{ar ? a.name_ar : a.name_en}</strong>
          {badge && (
            <span className="rounded-full bg-night-100 px-2 py-0.5 text-[11px] font-bold text-night-900">{badge}</span>
          )}
        </div>
        {desc && <span className="text-caption leading-normal text-ink-muted">{desc}</span>}
        {reason && <span className="text-caption font-semibold text-warning">{reason}</span>}
      </div>
      {icon ? (
        <div className="flex flex-col items-center gap-1.5">
          {price}
          <CheckBox on={on} />
        </div>
      ) : (
        <>
          {price}
          <CheckBox on={on} />
        </>
      )}
    </button>
  );
}
