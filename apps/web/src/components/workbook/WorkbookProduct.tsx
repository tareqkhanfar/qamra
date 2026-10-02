"use client";

/* eslint-disable @next/next/no-img-element -- static preview pages from /public (exported once by a script) */
import { useLocale, useTranslations } from "next-intl";
import { useRef, useState, type ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import { money, type CatalogProduct, type Currency } from "@/lib/store";
import {
  groups,
  initialPicks,
  previewsFor,
  resolve,
  soldAges,
  soldOptions,
  type Picks,
  type Preview,
  type PreviewScope,
} from "@/lib/workbook";
import { AddWorkbook } from "./AddWorkbook";
import { emptyFamily, FamilyDetails } from "./FamilyDetails";
import { FamilyQuoteForm } from "./FamilyQuoteForm";
import { WorkbookCover } from "./WorkbookCover";

const TONE: Record<string, string> = { workbook: "bg-night-100", journey: "bg-success-bg", family: "bg-amber-100" };

const chip = (on: boolean, off: boolean) =>
  `min-h-12 rounded-full px-4 text-[15px] font-semibold transition ${
    off
      ? "cursor-not-allowed border-[1.5px] border-dashed border-[#C9BCA3] bg-paper-sunk text-ink-muted opacity-45"
      : on
        ? "border-2 border-night-900 bg-night-900 text-paper"
        : "border-[1.5px] border-line bg-paper-raised text-night-900 hover:border-night-500"
  }`;

/**
 * Addendum 9 WorkbookProduct: one template for the three activity books. The choices come from the product's
 * variants, the price is the chosen variant's, and the book is made with the child's approved character.
 */
export function WorkbookProduct({
  product,
  currency,
  query,
  photo = null,
  familyCharacters = false,
}: {
  product: CatalogProduct;
  currency: Currency;
  query: Picks;
  photo?: ReactNode; // the book's lifestyle photo (components/site/Photo), when Tareq has added it
  familyCharacters?: boolean; // the illustrated-family add-on is switched on
}) {
  const t = useTranslations("workbook");
  const locale = useLocale();
  const [state, setState] = useState(() => resolve(product, initialPicks(product, query)));
  const [zoom, setZoom] = useState<Preview | null>(null);
  const [family, setFamily] = useState(emptyFamily); // «مغامراتي مع عائلتي»: optional, goes into the cart
  const dialog = useRef<HTMLDialogElement>(null);
  const { variant, picks } = state;
  const line = product.line;
  const name = locale === "ar" ? product.name_ar : product.name_en;
  const label = (group: string, value: string) =>
    t.has(`values.${group}.${value}`) ? t(`values.${group}.${value}`) : value.toUpperCase();
  const summary = ["level", "stage", "volume"]
    .filter((g) => picks[g])
    .map((g) =>
      g === "level"
        ? label(g, picks[g]!).split(" ·")[0]
        : picks[g] === "set"
          ? t(`summary.${g}Set`)
          : t(`summary.${g}`, { value: label(g, picks[g]!) }),
    )
    .join(" · ");
  const set = Object.values(picks).includes("set");
  const pdf = picks.format === "digital";
  const sold = soldOptions(product);
  const many = ["volume", "stage"].some((g) => (sold[g] ?? []).filter((v) => v !== "set").length > 1);
  const note = t.has(`note.${line}`)
    ? t(`note.${line}`, { set: String(set), pdf: String(pdf), many: String(many) })
    : "";
  const size = String(product.features.size ?? "").replace("x", "×");
  const binding = String(product.features.binding ?? "");
  const price = variant?.price ?? null;
  const ages = soldAges(product);
  const { pages: previews, scope } = previewsFor(product.slug, picks);
  const peekFrom = peekCaption(scope);

  /** Where the pages shown come from: "KG2, the third volume" or "the second stage" (nothing for the product). */
  function peekCaption({ level, volume, stage }: PreviewScope): string {
    const short = level ? label("level", level).split(" ·")[0]! : "";
    if (level && volume) return t("peekFrom.volume", { level: short, volume: label("volume", volume), n: volume });
    if (level) return t("peekFrom.level", { level: short });
    if (stage === "set") return t("peekFrom.allStages");
    if (stage) return t("peekFrom.stage", { stage: label("stage", stage), n: stage });
    return "";
  }

  function pick(group: string, value: string) {
    setState(resolve(product, { ...picks, [group]: value }, group));
  }

  return (
    <>
      <div className="mx-auto flex max-w-[1100px] flex-col gap-5 pt-2 pb-36 md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:gap-10 md:px-10 md:pt-10">
        <div className="flex flex-col gap-3 md:sticky md:top-28 md:self-start">
          <div className="flex h-[52px] items-center px-2 md:hidden">
            <Link
              href="/workbooks"
              aria-label={t("back")}
              className="flex size-11 items-center justify-center text-night-900"
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
          </div>
          <WorkbookCover
            tone={TONE[line] ?? "bg-night-100"}
            title={t(`cover.${line}`, { name: t("sampleName") })}
            line={summary}
            character="/workbooks/character.webp"
            binding={t.has(`binding.${binding}`) ? t(`binding.${binding}`) : null}
          />
        </div>

        <main className="flex flex-col gap-[22px] px-4 md:px-0">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2 text-caption font-semibold">
              {(ages || t.has(`ages.${line}`)) && (
                <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">
                  {ages ? t("ageRange", { min: ages[0], max: ages[1] }) : t(`ages.${line}`)}
                </span>
              )}
              {t.has(`pages.${line}`) && (
                <span className="rounded-full bg-paper-sunk px-2.5 py-1">{t(`pages.${line}`)}</span>
              )}
              {size && <span className="rounded-full bg-success-bg px-2.5 py-1 text-success">{size}</span>}
            </div>
            <h1 className="text-[32px] leading-tight text-night-900 md:text-[40px]">{name}</h1>
            <p className="text-body leading-[1.75] text-ink-muted">
              {t.has(`desc.${line}`)
                ? t(`desc.${line}`)
                : locale === "ar"
                  ? product.description_ar
                  : product.description_en}
            </p>
          </div>

          <section aria-labelledby="peek-title" className="flex flex-col gap-2.5">
            <div className="flex flex-col gap-0.5">
              <h2 id="peek-title" className="text-[20px] text-night-900">
                {t("peek")}
              </h2>
              {peekFrom && (
                <p className="text-caption text-ink-muted" aria-live="polite">
                  {peekFrom}
                </p>
              )}
            </div>
            <div
              key={previews[0]?.src ?? "none"}
              className="-mx-4 flex snap-x gap-2.5 overflow-x-auto px-4 pb-1 md:mx-0 md:px-0"
            >
              {previews.length > 0
                ? previews.map((p) => {
                    const title = locale === "ar" ? p.title_ar : p.title_en;
                    return (
                      <figure key={p.src} className="flex w-[150px] shrink-0 snap-start flex-col gap-1.5 md:w-[170px]">
                        <button
                          type="button"
                          onClick={() => {
                            setZoom(p);
                            dialog.current?.showModal();
                          }}
                          aria-label={t("zoom", { title })}
                          className="overflow-hidden rounded-[10px] border border-line bg-white"
                        >
                          <img
                            src={p.src}
                            alt=""
                            loading="lazy"
                            width={720}
                            height={1018}
                            className="aspect-[1/1.414] w-full object-cover"
                          />
                        </button>
                        <figcaption className="line-clamp-2 text-caption leading-[1.5] text-ink-muted">
                          {title}
                        </figcaption>
                      </figure>
                    );
                  })
                : (["trace", "name", "count"] as const).map((k) => (
                    <div
                      key={k}
                      className="flex h-[176px] w-[132px] shrink-0 flex-col gap-1.5 rounded-[10px] border border-line bg-white p-2.5"
                    >
                      <span className="text-[11px] font-bold text-night-900">{t(`placeholder.${k}`)}</span>
                      <span
                        aria-hidden="true"
                        className="flex grow items-center justify-center font-display text-[64px] text-night-900/25"
                      >
                        {k === "trace" ? "ب" : k === "name" ? "✎" : "٥"}
                      </span>
                    </div>
                  ))}
            </div>
          </section>

          <section className="flex flex-col gap-2.5 rounded-[20px] border border-line bg-paper-raised p-4">
            <h2 className="text-[18px] text-night-900">{t("mine.title")}</h2>
            {(t.raw(`mine.${line}`) as string[]).map((item) => (
              <div key={item} className="flex items-center gap-2.5 text-[15px]">
                <span
                  aria-hidden="true"
                  className="flex size-[22px] shrink-0 items-center justify-center rounded-full bg-success-bg text-[13px] font-extrabold text-success"
                >
                  ✓
                </span>
                {item}
              </div>
            ))}
          </section>

          {photo}

          <section className="flex flex-col gap-3.5">
            {groups(product, picks).map((g) => (
              <div key={g.name} role="radiogroup" aria-label={t(`options.${g.name}`)} className="flex flex-col gap-2">
                <h2 className="text-[17px] text-night-900">{t(`options.${g.name}`)}</h2>
                <div className="flex flex-wrap gap-2">
                  {g.values.map(({ value, available }) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={picks[g.name] === value}
                      aria-disabled={!available}
                      onClick={() => available && pick(g.name, value)}
                      className={chip(picks[g.name] === value, !available)}
                    >
                      {label(g.name, value)}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {note && <p className="text-caption leading-[1.6] text-ink-muted">{note}</p>}
          </section>

          {line === "family" && <FamilyDetails value={family} onChange={setFamily} />}

          {line === "family" && (
            <a href="#family-quote" className="text-small font-semibold text-amber-700 underline">
              {t("bulk")}
            </a>
          )}
          {line === "family" && familyCharacters && (
            <Link href="/family-characters" className="text-small font-semibold text-amber-700 underline">
              {t("familyCharacters")}
            </Link>
          )}

          <Link href="/quiz" className="flex min-h-11 items-center gap-3 rounded-[16px] bg-paper-sunk p-3.5">
            <svg
              className="size-[22px] shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#9A620A"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.5V14" />
              <path d="M12 17.2v.1" />
            </svg>
            <span className="text-small font-semibold">{t("quiz")}</span>
          </Link>

          <Link href="/kindergartens" className="flex flex-col gap-1 rounded-[20px] bg-night-900 p-4 text-paper">
            <strong className="text-body">{t(line === "family" ? "b2b.familyTitle" : "b2b.title")}</strong>
            <span className="text-small text-night-100">{t(line === "family" ? "b2b.familyBody" : "b2b.body")}</span>
          </Link>
        </main>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper/97 pt-3 pb-[max(16px,env(safe-area-inset-bottom))] backdrop-blur">
        <div className="mx-auto flex max-w-[1100px] items-center gap-3 px-4 md:px-10">
          <div className="flex flex-col">
            <span className="text-xs text-ink-muted">{summary || name}</span>
            <strong className="text-[19px]" aria-live="polite">
              {price === null ? "—" : money(price, currency, locale)}
            </strong>
          </div>
          <AddWorkbook sku={variant?.sku ?? null} family={line === "family" ? family : undefined} />
        </div>
      </div>
      {line === "family" && (
        <section className="mt-8">
          <FamilyQuoteForm />
        </section>
      )}

      <dialog
        ref={dialog}
        onClose={() => setZoom(null)}
        onClick={(e) => e.target === dialog.current && dialog.current?.close()}
        aria-label={t("zoomTitle")}
        className="m-auto max-h-[100dvh] w-full max-w-[min(100vw,760px)] bg-transparent p-2 backdrop:bg-night-950/85"
      >
        {zoom && (
          <div className="flex flex-col items-center gap-3">
            <img
              src={zoom.src}
              alt={locale === "ar" ? zoom.title_ar : zoom.title_en}
              className="max-h-[76dvh] w-auto max-w-full rounded-lg bg-white object-contain"
            />
            <p className="text-center text-small font-semibold text-paper">
              {locale === "ar" ? zoom.title_ar : zoom.title_en}
            </p>
            <button
              type="button"
              autoFocus
              onClick={() => dialog.current?.close()}
              className="min-h-11 rounded-full bg-paper px-6 font-bold text-night-900"
            >
              {t("close")}
            </button>
          </div>
        )}
      </dialog>
    </>
  );
}
