"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, useSyncExternalStore, type ReactNode } from "react";
import { BookViewer } from "@/components/book/BookViewer";
import { CoverArt, splitTemplate } from "@/components/book/CoverArt";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import type { ThemeDetail } from "@/lib/catalog";
import { rememberedVariant, type Example, type ExampleVariant } from "@/lib/examples";
import { cartApi, money, type Catalog } from "@/lib/store";
import { LINES, createHref, freeDigitalCopy, num, offer, styleChoices, type Line, type Offer } from "@/lib/story";
import { AddonList, extraAddons, type AddonMedia } from "./AddonList";
import { FormatCards, LineCards, LineChecklist, STYLE_LOOK, StyleCards } from "./Choices";
import { StyleShowcase } from "./StyleShowcase";

const subscribe = (cb: () => void) => {
  window.addEventListener("storage", cb);
  return () => window.removeEventListener("storage", cb);
};

/**
 * The story product page (Addendum 9, design StoryProduct): the real book first (cover, then a compact
 * flip-through), then three numbered choices (book type, art style, format) with the live price in a sticky
 * bar. «أضيفوا للسلة» puts the book in the cart in one tap (the child's details come from the cart);
 * «جرّبوا المعاينة أولًا» carries the choices to the create flow in the URL.
 */
export function StoryProduct({
  theme,
  catalog,
  examples,
  initialLine,
  themeNames = {},
  media,
  related,
}: {
  theme: ThemeDetail;
  catalog: Catalog | null;
  examples: Example[];
  initialLine: Line | null;
  /** Story names by slug, to label sample pages borrowed from other stories. */
  themeNames?: Record<string, string>;
  /** Pictures for the add-ons (the shared media list). */
  media?: AddonMedia;
  /** «قد يعجبكم أيضًا»: shown after the choices. */
  related?: ReactNode;
}) {
  const t = useTranslations("themeDetail");
  const ts = useTranslations("storyShowcase");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const currency = catalog?.currency ?? "ILS";
  const offers = LINES.map((l) => offer(catalog, l, theme)).filter((o): o is Offer => o !== null);
  const firstLine = offers.find((o) => o.available)?.line ?? "magic";
  const [pickedLine, setPickedLine] = useState<Line | null>(initialLine);
  const line = offers.find((o) => o.line === pickedLine && o.available)?.line ?? firstLine;
  const current = offers.find((o) => o.line === line) ?? null;

  const choices = styleChoices(catalog, line, theme);
  const [pickedStyle, setPickedStyle] = useState<string | null>(null);
  // default: the style of the real pages shown above, else the style both lines sell (the house style)
  const usable = choices.filter((c) => c.available);
  const style = (
    usable.find((c) => c.style.slug === pickedStyle) ??
    usable.find((c) => c.style.slug === examples[0]?.style) ??
    usable.find((c) => c.style.lines.includes("classic") && c.style.lines.includes("magic")) ??
    usable[0]
  )?.style;
  const modifier = num(style?.price_modifier);

  const [pickedFormat, setPickedFormat] = useState<string | null>(null);
  const formats = current?.formats ?? [];
  const variant =
    formats.find((v) => v.options.format === pickedFormat) ??
    formats.find((v) => v.options.format === "softcover") ??
    formats[0];
  const price = variant ? num(variant.price) + modifier : null;

  // the look shown on the cover follows the viewer's switch (and what the visitor picked before)
  const remembered = useSyncExternalStore(
    subscribe,
    () => rememberedVariant.get(),
    () => null,
  );
  const [look, setLook] = useState<ExampleVariant | null>(null);
  const example = examples.find((e) => e.variant === (look ?? remembered)) ?? examples[0] ?? null;

  const name = theme.sample_name ?? "";
  const [titleName, titleRest] = example
    ? [example.title_name, example.title_rest]
    : splitTemplate(theme.title, name || theme.name, name ? theme.sample_gender : null);

  const storyPages = (example?.pages ?? []).filter((p) => p.beat > 0 && p.layout !== "spread");
  const linePages = { classic: storyPages[0], magic: storyPages[3] ?? storyPages[1] };
  const exampleStyle = catalog?.styles.find((s) => s.slug === example?.style);
  const styleName = (s: { name_ar: string; name_en: string } | undefined) =>
    s ? (locale === "ar" ? s.name_ar : s.name_en) : "";
  const occasion = theme.occasions[0];
  const summary = [t(`lines.${line}.short`), variant ? t(`formats.name.${variant.options.format}`) : ""]
    .filter(Boolean)
    .join(" · ");

  const extras = extraAddons(catalog, line).filter((a) => {
    const formats = a.requires.format; // e.g. the hardcover upgrade only for a softcover
    return !formats || !variant?.options.format || formats.includes(variant.options.format);
  });
  const lineNames = Object.fromEntries(
    offers.map((o) => [o.line, locale === "ar" ? o.product.name_ar : o.product.name_en]),
  );

  /** The chosen book, format and story into the cart; the style only when the parent picked one. */
  async function addToCart() {
    if (!variant) return;
    setAdding(true);
    setAddError(null);
    const picked = pickedStyle && style?.slug === pickedStyle ? { style: pickedStyle } : {};
    const r = await cartApi.add({ sku: variant.sku, theme: theme.slug, ...picked });
    if (r.ok) return router.push("/cart");
    setAdding(false);
    setAddError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <>
      <div
        className={`mx-auto max-w-[1200px] lg:grid ${related ? "pb-12" : "pb-36"} lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-12 lg:px-10 lg:pt-10`}
      >
        {/* hero: the real cover when an example is published, else the theme's art in the chosen style */}
        <div className="relative lg:sticky lg:top-28 lg:self-start">
          <CoverArt
            example={example}
            art={theme.art}
            titleName={titleName}
            titleRest={titleRest}
            alt={example ? t("coverAlt", { title: example.title }) : t("placeholderCoverAlt")}
            sizes="(min-width: 1024px) 560px, 100vw"
            priority
            artStyle={example ? undefined : STYLE_LOOK[style?.slug ?? ""]?.fx}
            className="lg:rounded-s-2xl lg:rounded-e-md lg:shadow-book"
          />
          <Link
            href="/stories"
            aria-label={tc("back")}
            className="absolute start-4 top-3 flex size-11 items-center justify-center rounded-full bg-paper/90 text-night-900 lg:hidden"
          >
            <svg
              className="size-[22px] ltr:-scale-x-100"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M5 12h14" />
              <path d="M13 6l6 6-6 6" />
            </svg>
          </Link>
          <span className="absolute start-4 bottom-9 rounded-full bg-night-950/80 px-3 py-1.5 text-caption font-semibold text-paper lg:bottom-4">
            {example
              ? t("realExample", { style: styleName(exampleStyle) })
              : t("styleChip", { style: styleName(style) })}
          </span>
        </div>

        <main className="relative -mt-6 flex flex-col gap-5 rounded-t-[24px] bg-paper px-4 pt-6 lg:mt-0 lg:rounded-none lg:px-0 lg:pt-0">
          <div className="flex flex-col gap-2.5">
            <div className="flex flex-wrap gap-2 text-caption font-semibold">
              <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">
                {tc("ages", { min: theme.age_min, max: theme.age_max })}
              </span>
              <span className="rounded-full bg-paper-sunk px-2.5 py-1">{tc("pages", { count: theme.pages })}</span>
              {occasion && (
                <span className="rounded-full bg-success-bg px-2.5 py-1 text-success">
                  {tc(`occasions.${occasion}`)}
                </span>
              )}
            </div>
            <h1 className="text-[32px] leading-tight text-night-900 md:text-[40px]">{theme.name}</h1>
            <p className="text-body leading-[1.75] text-ink-muted">{theme.description}</p>
            {theme.values.length > 0 && (
              <p className="flex flex-wrap items-center gap-1.5 text-caption">
                <span className="font-semibold text-ink-muted">{ts("values")}</span>
                {theme.values.map((v) => (
                  <span key={v} className="rounded-full bg-amber-100 px-2.5 py-1 font-semibold text-amber-700">
                    {v}
                  </span>
                ))}
              </p>
            )}
          </div>

          <section aria-labelledby="browse-title" className="flex flex-col gap-2.5">
            <h2 id="browse-title" className="text-[20px] text-night-900">
              {t("browse")}
            </h2>
            <BookViewer
              examples={examples}
              variant={example?.variant ?? null}
              onVariant={setLook}
              fallback={theme.samples}
              headingId="browse-title"
              end={{
                title: t("viewerEnd.title"),
                body: t("viewerEnd.body"),
                label: t("viewerEnd.cta"),
                href: "#steps",
              }}
            />
          </section>

          <section id="steps" className="flex scroll-mt-24 flex-col gap-2.5">
            <h2 className="text-[20px] text-night-900">{t("step1")}</h2>
            <LineCards offers={offers} value={line} onChange={setPickedLine} currency={currency} pages={linePages} />
            <LineChecklist line={line} catalog={catalog} />
          </section>

          <section className="flex flex-col gap-2.5">
            <h2 className="text-[20px] text-night-900">{t("step2")}</h2>
            <StyleCards
              choices={choices}
              value={style?.slug ?? null}
              onChange={setPickedStyle}
              line={line}
              currency={currency}
              theme={theme.slug}
              look={example?.variant ?? null}
            />
            {style && (
              <div className="flex flex-col gap-2 rounded-[20px] bg-paper-sunk p-3.5 md:p-4">
                <h3 className="text-[17px] text-night-900">
                  {ts("stepGallery", { style: locale === "ar" ? style.name_ar : style.name_en })}
                </h3>
                <StyleShowcase
                  tabs={false}
                  size="sm"
                  styles={choices.map((c) => ({
                    slug: c.style.slug,
                    name: locale === "ar" ? c.style.name_ar : c.style.name_en,
                    lines: c.style.lines,
                  }))}
                  value={style.slug}
                  theme={theme.slug}
                  themeNames={{ ...themeNames, [theme.slug]: theme.name }}
                  lineNames={lineNames}
                  look={example?.variant ?? null}
                />
              </div>
            )}
          </section>

          <section className="flex flex-col gap-2.5">
            <h2 className="text-[20px] text-night-900">{t("step3")}</h2>
            <FormatCards
              formats={formats}
              value={variant?.sku ?? null}
              onChange={(sku) => setPickedFormat(formats.find((v) => v.sku === sku)?.options.format ?? null)}
              modifier={modifier}
              currency={currency}
              freeDigital={!!freeDigitalCopy(catalog, line)}
            />
            {freeDigitalCopy(catalog, line) && (
              <p className="text-caption leading-[1.6] text-ink-muted">{t("formatsNoteDigital")}</p>
            )}
          </section>

          {extras.length > 0 && (
            <section aria-labelledby="extras-title" className="flex flex-col gap-2.5">
              <div className="flex flex-col gap-0.5">
                <h2 id="extras-title" className="text-[20px] text-night-900">
                  {ts("extras.title")}
                </h2>
                <p className="text-small text-ink-muted">{ts("extras.later")}</p>
              </div>
              <AddonList addons={extras} catalog={catalog} media={media} initial={3} wide={false} />
            </section>
          )}

          <Link
            href={createHref(theme.slug, line, style?.slug, variant?.options.format)}
            className="flex min-h-12 items-center justify-center rounded-full border-[1.5px] border-night-900 px-6 text-body font-bold text-night-900 hover:bg-paper-sunk"
          >
            {t("tryPreview")}
          </Link>

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
            <span className="text-small leading-[1.6]">{t("trust")}</span>
          </div>
        </main>
      </div>
      {related && <div className="mx-auto max-w-[1200px] px-4 pb-36 lg:px-10">{related}</div>}

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper/97 pt-3 pb-[max(16px,env(safe-area-inset-bottom))] backdrop-blur">
        {addError && (
          <p role="alert" className="mx-auto mb-2 max-w-[1200px] px-4 text-small font-semibold text-danger lg:px-10">
            {addError}
          </p>
        )}
        <div className="mx-auto flex max-w-[1200px] items-center gap-3 px-4 lg:px-10">
          <div className="flex flex-col">
            <span className="text-xs text-ink-muted">{summary}</span>
            <strong className="text-[19px]" aria-live="polite">
              {price === null ? tc("priceTbd") : money(price, currency, locale)}
            </strong>
          </div>
          <button
            type="button"
            onClick={() => void addToCart()}
            disabled={adding || !variant}
            className="flex min-h-14 grow items-center justify-center rounded-full bg-amber-500 px-6 text-[17px] font-bold text-night-950 hover:shadow-lamp disabled:opacity-60 lg:max-w-[360px] lg:grow-0 lg:px-12 ltr:lg:ml-auto rtl:lg:mr-auto"
          >
            {t("addToCart")}
          </button>
        </div>
      </div>
    </>
  );
}
