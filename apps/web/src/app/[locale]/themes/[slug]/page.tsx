import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getLocale, getTranslations } from "next-intl/server";
import { Scene, fromArt } from "@/components/art/Scene";
import { PageShell } from "@/components/site/PageShell";
import { Link } from "@/i18n/navigation";
import { formatAmount, getPricing, getTheme, lowestPrice } from "@/lib/catalog";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const theme = await getTheme(slug, await getLocale());
  return theme ? { title: theme.name, description: theme.tagline } : {};
}

export default async function ThemeDetailPage({ params }: Props) {
  const { slug } = await params;
  const locale = await getLocale();
  const [t, tc, theme, prices] = await Promise.all([
    getTranslations("themeDetail"),
    getTranslations("common"),
    getTheme(slug, locale),
    getPricing(),
  ]);
  if (!theme) notFound();
  const soon = theme.status === "coming_soon";
  const from = lowestPrice(prices);
  const occasion = theme.occasions[0];

  const cta = soon ? (
    <Link
      href="/themes"
      className="flex min-h-14 grow items-center justify-center rounded-full border-2 border-night-900 px-6 text-[17px] font-bold text-night-900"
    >
      {t("browse")}
    </Link>
  ) : (
    <Link
      href={`/create?theme=${theme.slug}`}
      className="flex min-h-14 grow items-center justify-center rounded-full bg-amber-500 px-6 text-[17px] font-bold text-night-950 hover:shadow-lamp"
    >
      {t("make")}
    </Link>
  );

  return (
    <PageShell>
      <div className="mx-auto max-w-[1200px] pb-28 md:px-10 md:pt-10 md:pb-24 lg:grid lg:grid-cols-[1fr_1.05fr] lg:gap-12">
        {/* hero illustration */}
        <div className="relative lg:sticky lg:top-28 lg:self-start">
          <Scene {...fromArt(theme.art)} ratio={390 / 360} kidScale={0.62} className="md:rounded-2xl" />
          <div className="absolute inset-x-4 top-3 flex justify-between md:hidden">
            <Link
              href="/themes"
              aria-label={tc("back")}
              className="flex size-11 items-center justify-center rounded-full bg-paper/90"
            >
              <svg
                className="size-[22px] ltr:-scale-x-100"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#16204A"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M5 12h14" />
                <path d="M13 6l6 6-6 6" />
              </svg>
            </Link>
          </div>
        </div>

        <div className="relative -mt-6 flex flex-col gap-4 rounded-t-[24px] bg-paper px-4 pt-6 md:mt-6 md:rounded-none md:px-0 lg:mt-0">
          <div className="flex flex-wrap gap-2 text-caption">
            <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">
              {tc("ages", { min: theme.age_min, max: theme.age_max })}
            </span>
            <span className="rounded-full bg-paper-sunk px-2.5 py-1">{tc("pages", { count: theme.pages })}</span>
            {occasion && (
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-amber-700">
                {tc(`occasions.${occasion}`)}
              </span>
            )}
            {soon && <span className="rounded-full bg-lav-300 px-2.5 py-1 text-night-900">{tc("comingSoon")}</span>}
          </div>
          <h1 className="text-[34px] leading-tight text-night-900 md:text-[44px]">{theme.name}</h1>
          <p className="text-body leading-[1.75] text-ink-muted md:text-body-l">{theme.description}</p>

          {theme.values.length > 0 && (
            <div className="flex flex-col gap-2.5 rounded-lg border border-line bg-paper-raised p-4">
              <h2 className="text-[18px] text-night-900">{t("learns")}</h2>
              <div className="flex flex-wrap gap-2 text-small">
                {theme.values.map((v) => (
                  <span key={v} className="rounded-full bg-success-bg px-3 py-1.5 font-semibold text-success">
                    {v}
                  </span>
                ))}
              </div>
            </div>
          )}

          {soon ? (
            <div className="flex flex-col gap-2 rounded-lg bg-paper-sunk p-5">
              <h2 className="text-[20px] text-night-900">{t("soonTitle")}</h2>
              <p className="text-body text-ink-muted">{t("soonBody")}</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <h2 className="text-[20px] text-night-900">{t("peek")}</h2>
                <span className="text-caption font-normal text-ink-muted">
                  {t("peekCount", { n: theme.peek.length, total: theme.pages })}
                </span>
              </div>
              <div className="-mx-4 flex gap-2.5 overflow-x-auto px-4 pb-1 md:mx-0 md:px-0">
                {theme.peek.map((p, i) =>
                  p.kind === "text" ? (
                    <div
                      key={i}
                      className="flex size-[150px] shrink-0 items-center overflow-hidden rounded-sm border border-line bg-paper-raised p-3.5 font-display text-[14px] leading-[1.7] font-semibold"
                    >
                      {p.text}
                    </div>
                  ) : (
                    <div key={i} className="w-[150px] shrink-0 overflow-hidden rounded-sm">
                      {p.art && <Scene {...fromArt(p.art)} ratio={1} kidScale={p.art.kid_scale ?? 0.6} />}
                    </div>
                  ),
                )}
              </div>

              <h2 className="text-[20px] text-night-900">{t("formats")}</h2>
              <div className="flex flex-col gap-2">
                {(["hardcover", "softcover", "digital"] as const).map((key, i) => {
                  const amount = prices?.find((p) => p.product === key)?.amount ?? null;
                  return (
                    <div
                      key={key}
                      className={`flex min-h-14 items-center justify-between rounded-md px-4 ${i === 0 ? "bg-night-900 text-paper" : "border border-line bg-paper-raised"}`}
                    >
                      <span className="font-semibold">{tc(`products.${key}`)}</span>
                      <strong>{amount ? `${formatAmount(amount)} ₪` : tc("priceTbd")}</strong>
                    </div>
                  );
                })}
              </div>
              <p className="text-small text-ink-muted">{t("formatsNote")}</p>
            </>
          )}

          <div className="flex items-center gap-3 rounded-md bg-paper-sunk p-3.5">
            <svg
              className="size-6 shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2E7A52"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
            <span className="text-small">{tc("privacyNote")}</span>
          </div>

          <div className="hidden items-center gap-4 pt-2 md:flex">
            {!soon && (
              <div className="flex flex-col">
                <span className="text-caption font-normal text-ink-muted">{t("from")}</span>
                <strong className="text-[17px]">{from ? `${from} ₪` : tc("priceTbd")}</strong>
              </div>
            )}
            {cta}
          </div>
        </div>
      </div>

      {/* mobile sticky CTA */}
      <div className="fixed inset-x-0 bottom-0 z-40 flex items-center gap-3 border-t border-line bg-paper/95 px-4 pt-3 pb-[max(16px,env(safe-area-inset-bottom))] md:hidden">
        {!soon && (
          <div className="flex flex-col">
            <span className="text-xs text-ink-muted">{t("from")}</span>
            <strong className="text-[17px]">{from ? `${from} ₪` : tc("priceTbd")}</strong>
          </div>
        )}
        {cta}
      </div>
    </PageShell>
  );
}
