"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Scene, fromArt } from "@/components/art/Scene";
import { Alert } from "@/components/ui/Alert";
import { ArrowForward, Button } from "@/components/ui/Button";
import { ExampleImage } from "@/components/book/ExampleImage";
import { FormatCards } from "@/components/story/Choices";
import { api, errorText } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import { createApi, pageImage, type Book, type Child } from "@/lib/create";
import { pickExample, storyPages, variantOf, type Example } from "@/lib/examples";
import { money, type Catalog, type CatalogAddOn, type CatalogVariant } from "@/lib/store";
import { freeDigitalCopy } from "@/lib/story";
import { Frame } from "./Frame";

const PRODUCT = { classic: "classic-book", magic: "magic-book" } as const;
const ORDER = ["hardcover", "softcover", "digital"];

function fitsVariant(addon: CatalogAddOn, variant: CatalogVariant | undefined): boolean {
  return Object.entries(addon.requires).every(([k, values]) => values.includes(variant?.options[k] ?? ""));
}

/** Step 10 (design Create9): the preview, the format and the format's extras, then the cart and checkout. */
export function FormatStep({
  child,
  book,
  theme,
  catalog,
  back,
  onAdded,
}: {
  child: Child;
  book: Book;
  theme: ThemeCard | null;
  catalog: Catalog | null;
  back: () => void;
  onAdded: () => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const currency = catalog?.currency ?? "ILS";
  const product = catalog?.products.find((p) => p.slug === PRODUCT[book.line]);
  const variants = [...(product?.variants ?? [])]
    .filter((v) => v.price !== null)
    .sort((a, b) => ORDER.indexOf(a.options.format) - ORDER.indexOf(b.options.format));
  const wanted = useSearchParams().get("format");
  const [sku, setSku] = useState(variants.find((v) => v.options.format === wanted)?.sku ?? variants[0]?.sku ?? "");
  const [examples, setExamples] = useState<Example[]>([]);
  useEffect(() => {
    let alive = true;
    void (async () => {
      const r = await api<Example[]>(`/api/examples?theme=${encodeURIComponent(book.theme)}&lang=ar`);
      if (alive && r.ok) setExamples(r.data);
    })();
    return () => {
      alive = false;
    };
  }, [book.theme]);
  const strip = storyPages(pickExample(examples, book.theme, variantOf(child)), 3, 1);
  const [extras, setExtras] = useState<string[]>([]);
  const [shown, setShown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const variant = variants.find((v) => v.sku === sku);
  const addons = (catalog?.addons ?? []).filter(
    (a) => a.step === "format" && a.lines.includes(book.line) && a.price !== null && fitsVariant(a, variant),
  );
  const chosen = addons.filter((a) => extras.includes(a.slug));
  const style = catalog?.styles.find((s) => s.slug === book.style);
  const dedication =
    book.line === "classic" && book.dedication ? catalog?.addons.find((a) => a.slug === "dedication-page") : null;
  const total =
    Number(variant?.price ?? 0) +
    Number(style?.price_modifier ?? 0) +
    chosen.reduce((sum, a) => sum + Number(a.price ?? 0), 0) +
    Number(dedication?.price ?? 0);
  const previews = book.pages.filter((p) => p.image);

  async function order() {
    setBusy(true);
    setError(null);
    const r = await createApi.toCart(
      book.id,
      sku,
      chosen.map((a) => ({ slug: a.slug })),
    );
    setBusy(false);
    if (r.ok) onAdded();
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <Frame
      title={book.title ?? t("bookOf", { name: child.name })}
      label={t("steps.format")}
      n={10}
      back={back}
      footer={
        <div className="flex grow items-center gap-3">
          <div className="flex flex-col">
            <span className="text-caption text-ink-muted">{t("format.total")}</span>
            <strong className="font-display text-[20px] text-night-900">{money(total, currency, locale)}</strong>
          </div>
          <Button variant="primary" size="lg" className="grow" onClick={order} loading={busy} disabled={!variant}>
            {t("format.cta")} <ArrowForward />
          </Button>
        </div>
      }
    >
      <h1 className="text-[26px] text-night-900">
        {book.line === "magic"
          ? t("format.title", { name: child.name })
          : t("format.classicTitle", { name: child.name })}
      </h1>

      {previews.length > 0 ? (
        <div className="flex flex-col items-center gap-2">
          <div className="relative w-full max-w-[420px] overflow-hidden rounded-2xl shadow-2">
            {/* eslint-disable-next-line @next/next/no-img-element -- private watermarked preview through the API */}
            <img
              src={pageImage(book.id, previews[shown].beat)}
              alt={previews[shown].beat === 0 ? t("review.cover") : t("review.page", { n: previews[shown].beat })}
              className="aspect-square w-full object-cover"
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label={t("format.prev")}
              onClick={() => setShown((i) => (i - 1 + previews.length) % previews.length)}
              className="flex size-11 items-center justify-center rounded-full border border-line bg-paper-raised"
            >
              <span aria-hidden="true" className="rtl:-scale-x-100">
                ‹
              </span>
            </button>
            <span className="text-caption text-ink-muted">
              {t("format.previewOf", { n: shown + 1, total: previews.length })}
            </span>
            <button
              type="button"
              aria-label={t("format.next")}
              onClick={() => setShown((i) => (i + 1) % previews.length)}
              className="flex size-11 items-center justify-center rounded-full border border-line bg-paper-raised"
            >
              <span aria-hidden="true" className="rtl:-scale-x-100">
                ›
              </span>
            </button>
          </div>
          <span className="text-caption text-ink-muted">{t("format.watermark")}</span>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {strip.length > 0 ? (
            <div className="grid grid-cols-3 gap-2">
              {strip.map((p) => (
                <div key={p.beat} className="relative aspect-square overflow-hidden rounded-xl bg-paper-sunk">
                  <ExampleImage
                    page={p}
                    alt={p.text ?? ""}
                    sizes="140px"
                    className="absolute inset-0 size-full object-cover"
                  />
                </div>
              ))}
            </div>
          ) : (
            theme && (
              <div className="overflow-hidden rounded-2xl">
                <Scene {...fromArt({ ...theme.art, hijab: child.hijab })} ratio={16 / 10} kidScale={0.6} />
              </div>
            )
          )}
          <p className="text-small text-ink-muted">
            {strip.length > 0
              ? t("format.examplePages", { name: child.name })
              : t("format.classicNote", { name: child.name })}
          </p>
        </div>
      )}

      <section aria-labelledby="formats-title" className="flex flex-col gap-2.5">
        <h2 id="formats-title" className="text-body font-semibold">
          {t("format.choose")}
        </h2>
        <FormatCards
          formats={variants}
          value={sku}
          onChange={(next) => {
            setSku(next);
            setExtras([]);
          }}
          modifier={Number(style?.price_modifier ?? 0)}
          currency={currency}
          freeDigital={!!freeDigitalCopy(catalog, book.line)}
          popular="hardcover"
        />
      </section>

      {addons.length > 0 && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-body font-semibold">{t("format.addons")}</legend>
          {addons.map((a) => (
            <label
              key={a.slug}
              className="flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-[1.5px] border-line bg-paper-raised px-4 py-2.5"
            >
              <input
                type="checkbox"
                checked={extras.includes(a.slug)}
                onChange={(e) => setExtras((l) => (e.target.checked ? [...l, a.slug] : l.filter((x) => x !== a.slug)))}
                className="size-5 accent-night-900"
              />
              <div className="flex grow flex-col">
                <span className="text-small font-semibold">{locale === "ar" ? a.name_ar : a.name_en}</span>
                {(locale === "ar" ? a.description_ar : a.description_en) && (
                  <span className="text-caption text-ink-muted">
                    {locale === "ar" ? a.description_ar : a.description_en}
                  </span>
                )}
              </div>
              <span className="text-small font-semibold whitespace-nowrap">
                +{money(a.price ?? 0, currency, locale)}
              </span>
            </label>
          ))}
        </fieldset>
      )}
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
