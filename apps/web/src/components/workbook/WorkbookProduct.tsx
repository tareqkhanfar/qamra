"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { ArrowForward } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import type { AddonMedia, IncludedItem } from "@/lib/addonsMedia";
import { money, type CatalogAddOn, type CatalogProduct, type Currency } from "@/lib/store";
import { groups, initialPicks, isSet, partsFor, resolve, soldAges, soldOptions, type Picks } from "@/lib/workbook";
import { AddWorkbook } from "./AddWorkbook";
import { FamilyQuoteForm } from "./FamilyQuoteForm";
import { WorkbookCover } from "./WorkbookCover";
import { showcaseCopy } from "./showcase/copy";
import { Extras } from "./showcase/Extras";
import { Showcase } from "./showcase/Showcase";
import { ShowcaseDetails } from "./showcase/ShowcaseDetails";

const TONE: Record<string, string> = {
  workbook: "bg-night-100",
  journey: "bg-success-bg",
  family: "bg-amber-100",
  islamic: "bg-success-bg",
};

const chip = (on: boolean, off: boolean) =>
  `min-h-12 rounded-full px-4 text-[15px] font-semibold transition ${
    off
      ? "cursor-not-allowed border-[1.5px] border-dashed border-[#C9BCA3] bg-paper-sunk text-ink-muted opacity-45"
      : on
        ? "border-2 border-night-900 bg-night-900 text-paper"
        : "border-[1.5px] border-line bg-paper-raised text-night-900 hover:border-night-500"
  }`;

/**
 * Addendum 9 WorkbookProduct: one template for the activity books. The choices come from the product's
 * variants, the price is the chosen variant's, and the book is made with the child's approved character. The
 * pages and the details follow the picks: the cover and real pages of the level, volume or stage chosen (every
 * book of a set), and what that part teaches (owner's request, 2026-10-07). On phones the pages sit right under
 * the choices; on wide screens they stay beside them. Nothing about the child is asked here: «أضيفوا للسلة» adds
 * the book in one tap, and the order flow (`/create?product=<sku>`) asks for the child, and for «مغامراتي مع
 * عائلتي» the family, after it (order flows §c.7, chunk 11).
 */
export function WorkbookProduct({
  product,
  currency,
  query,
  photo = null,
  familyCharacters = false,
  signedIn = false,
  addons = [],
  included = [],
  addonMedia = {},
}: {
  product: CatalogProduct;
  currency: Currency;
  query: Picks;
  photo?: ReactNode; // the book's lifestyle photo (components/site/Photo), when Tareq has added it
  familyCharacters?: boolean; // the illustrated-family add-on is switched on
  signedIn?: boolean; // a parent is signed in: «ابدؤوا لطفلكم الآن» opens the order flow for this book
  addons?: CatalogAddOn[]; // the catalog's active add-ons (the extras the cart offers come from these)
  included?: readonly IncludedItem[]; // what every copy comes with, with photos (lib/addonsMedia)
  addonMedia?: Readonly<Record<string, AddonMedia | undefined>>; // add-on photos (lib/addonsMedia)
}) {
  const t = useTranslations("workbook");
  const ts = useTranslations("workbookShowcase");
  const locale = useLocale();
  const [state, setState] = useState(() => resolve(product, initialPicks(product, query)));
  const { variant, picks } = state;
  const line = product.line;
  const name = locale === "ar" ? product.name_ar : product.name_en;
  // a line may name its own options (`valuesOf.<line>…`, e.g. «قلبي يعرف الله»'s volumes and sets)
  const label = (group: string, value: string) =>
    t.has(`valuesOf.${line}.${group}.${value}`)
      ? t(`valuesOf.${line}.${group}.${value}`)
      : t.has(`values.${group}.${value}`)
        ? t(`values.${group}.${value}`)
        : value.toUpperCase();
  const optionName = (group: string) =>
    t.has(`optionsOf.${line}.${group}`) ? t(`optionsOf.${line}.${group}`) : t(`options.${group}`);
  const summary = ["level", "stage", "volume"]
    .filter((g) => picks[g])
    .map((g) =>
      t.has(`summaryOf.${line}.${picks[g]}`)
        ? t(`summaryOf.${line}.${picks[g]}`)
        : g === "level"
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
  const price = variant?.price ?? null;
  const ages = soldAges(product);
  const parts = partsFor(product.slug, line, picks);
  const keys = parts.map((p) => p.key);
  const several = isSet(picks) && parts.length > 1;
  const copy = showcaseCopy(product.slug, line, picks, keys);

  /** A part's name: «KG1، الجزء الثاني», «المحطة الثانية», «المجلد الأول», the family book's own name. */
  function partName(key: string): string {
    if (line === "workbook") {
      const [level = "", volume = ""] = key.split("-");
      return ts("part.workbook", {
        level: label("level", level).split(" ·")[0]!,
        volume: label("volume", volume),
        n: volume,
      });
    }
    if (line === "journey") return ts("part.journey", { stage: label("stage", key), n: key });
    if (t.has(`summaryOf.${line}.${key}`)) return t(`summaryOf.${line}.${key}`);
    return locale === "ar" ? `«${name}»` : `“${name}”`; // the book's own title, quoted
  }

  function pick(group: string, value: string) {
    setState(resolve(product, { ...picks, [group]: value }, group));
  }

  const tone = TONE[line] ?? "bg-night-100";
  const binding = String(product.features.binding ?? "");
  const bindingLabel = t.has(`binding.${binding}`) ? t(`binding.${binding}`) : null;
  const row = "px-4 md:px-0";

  return (
    <>
      {/* phones: one column ordered back, cover, title, choices, pages, details, the rest; wide screens: the
          cover and pages stay beside the rest (the two wrappers are `contents` on phones, columns on md+) */}
      <div className="mx-auto flex max-w-[1100px] flex-col gap-5 pt-2 pb-36 md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:gap-10 md:px-10 md:pt-10">
        <div className="contents md:sticky md:top-28 md:flex md:flex-col md:gap-5 md:self-start">
          <div className="order-1 -mb-2 flex h-[52px] items-center px-2 md:hidden">
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
          {parts.length > 0 ? (
            <Showcase
              key={`${keys.join()}|${picks.interior ?? ""}|${picks.format ?? ""}`}
              parts={parts}
              partName={partName}
              caption={
                several ? ts("fromSet") : line === "family" ? ts("fromBook") : ts("from", { part: partName(keys[0]!) })
              }
              tone={tone}
              bw={picks.interior === "bw"}
              pdf={pdf}
              binding={bindingLabel}
              heroClass="order-2"
              stripClass="order-5"
            />
          ) : (
            <div className="order-2">
              <WorkbookCover
                tone={tone}
                title={t(`cover.${line}`, { name: t("sampleName") })}
                line={summary}
                character="/workbooks/character.webp"
                binding={bindingLabel}
              />
            </div>
          )}
        </div>

        <main className="contents md:flex md:flex-col md:gap-[22px]">
          <div className={`order-3 flex flex-col gap-2 ${row}`}>
            <div className="flex flex-wrap gap-2 text-caption font-semibold">
              {(ages || t.has(`ages.${line}`)) && (
                <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">
                  {ages ? t("ageRange", { min: ages[0], max: ages[1] }) : t(`ages.${line}`)}
                </span>
              )}
              {t.has(`pages.${line}`) && (
                <span className="rounded-full bg-paper-sunk px-2.5 py-1">{t(`pages.${line}`)}</span>
              )}
              {size && (
                <span dir="ltr" className="rounded-full bg-success-bg px-2.5 py-1 text-success">
                  {size}
                </span>
              )}
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

          <section className={`order-4 flex flex-col gap-3.5 ${row}`}>
            {groups(product, picks).map((g) => (
              <div key={g.name} role="radiogroup" aria-label={optionName(g.name)} className="flex flex-col gap-2">
                <h2 className="text-[17px] text-night-900">{optionName(g.name)}</h2>
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
            {line === "family" && (
              <p className="flex items-start gap-2 rounded-[14px] bg-amber-100 px-3 py-2.5 text-small leading-[1.6] text-night-900">
                <svg
                  className="mt-0.5 size-5 shrink-0"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#9A620A"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="9" cy="7" r="3" />
                  <path d="M3 20v-1a6 6 0 0 1 12 0v1" />
                  <circle cx="17.5" cy="9.5" r="2.5" />
                  <path d="M17 14.6a4.5 4.5 0 0 1 4.5 4.4v1" />
                </svg>
                {t("familyLater")}
              </p>
            )}
            {signedIn && variant && (
              <Link
                href={`/create?product=${encodeURIComponent(variant.sku)}`}
                className="flex min-h-11 items-center gap-1.5 self-start font-display text-body font-bold text-night-900 underline underline-offset-4"
              >
                {t("start")} <ArrowForward />
              </Link>
            )}
          </section>

          {copy && (
            <ShowcaseDetails
              copy={copy}
              partName={partName}
              title={
                copy.kind === "set"
                  ? ts("aboutSet", { set: summary })
                  : line === "family"
                    ? ts("aboutBook")
                    : ts("about", { part: partName(keys[0]!) })
              }
              className="order-6"
            />
          )}

          <Extras
            included={included}
            addons={addons}
            media={addonMedia}
            line={line}
            options={variant?.options ?? picks}
            pdf={pdf}
            currency={currency}
            className="order-7"
          />

          <div className={`order-8 flex flex-col gap-[22px] ${row}`}>
            {photo}

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
          </div>
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
          <AddWorkbook sku={variant?.sku ?? null} />
        </div>
      </div>
      {line === "family" && (
        <section className="mt-8">
          <FamilyQuoteForm />
        </section>
      )}
    </>
  );
}
