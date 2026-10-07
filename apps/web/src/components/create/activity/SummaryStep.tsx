"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { ItemAddOns } from "@/components/order/AddOnsStep";
import { Alert } from "@/components/ui/Alert";
import { ArrowForward, Button } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { characterImage, type Child, type FamilyPayload } from "@/lib/create";
import { money, type CatalogProduct, type CatalogVariant, type Currency } from "@/lib/store";
import { partsFor } from "@/lib/workbook";
import { arabic } from "../EditChild";
import { Frame, Lead } from "../Frame";
import { AgeCheck } from "./AgeCheck";

/** «KG2 · الجزء الأول · ملوّن · مطبوع»: the variant as the product page names it (its `workbook.*` labels). */
function useVariantLine(product: CatalogProduct, variant: CatalogVariant): string {
  const t = useTranslations("workbook");
  const line = product.line as string;
  const picks = variant.options;
  const label = (group: string, value: string) =>
    t.has(`valuesOf.${line}.${group}.${value}`)
      ? t(`valuesOf.${line}.${group}.${value}`)
      : t.has(`values.${group}.${value}`)
        ? t(`values.${group}.${value}`)
        : value.toUpperCase();
  const parts = ["level", "stage", "volume"]
    .filter((g) => picks[g])
    .map((g) =>
      t.has(`summaryOf.${line}.${picks[g]}`)
        ? t(`summaryOf.${line}.${picks[g]}`)
        : g === "level"
          ? label(g, picks[g]!).split(" ·")[0]!
          : picks[g] === "set"
            ? t(`summary.${g}Set`)
            : t(`summary.${g}`, { value: label(g, picks[g]!) }),
    );
  for (const g of ["interior", "format"]) if (picks[g]) parts.push(label(g, picks[g]!));
  return parts.join(" · ");
}

/** One row of the review: what it is, what will be printed, and «تغيير» where it can change. */
function Row({ label, children, action }: { label: string; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-center gap-3 border-b border-line py-3.5 last:border-b-0">
      <div className="flex min-w-0 grow flex-col gap-0.5">
        <dt className="text-caption text-ink-muted">{label}</dt>
        <dd className="text-body font-semibold break-words text-night-900">{children}</dd>
      </div>
      {action}
    </div>
  );
}

const changeClass =
  "min-h-11 shrink-0 content-center rounded-full px-3 text-small font-bold text-night-900 underline underline-offset-4 hover:bg-paper-sunk";

/**
 * The activity book's review step (§c.8): what will be printed, before the cart. The book and its variant, the
 * name as printed (and in English letters), how the book speaks to the child, the character, the family, the
 * price, and a non-blocking age check; then «أضيفوا للسلة» (or «احفظوا في السلة» for a line added in one tap).
 */
export function SummaryStep({
  child,
  product,
  variant,
  currency,
  characterId,
  nameEn,
  family,
  ages,
  itemId,
  back,
  onEditChild,
  onEditFamily,
  onNewCharacter,
  onAdd,
}: {
  child: Child;
  product: CatalogProduct;
  variant: CatalogVariant;
  currency: Currency;
  characterId: string | null;
  /** The name in English letters, when this book prints it. */
  nameEn: string | null;
  /** «مغامراتي مع عائلتي»: the family as given (null: skipped); undefined for the other books. */
  family?: FamilyPayload | null;
  ages: [number, number] | null;
  /** The cart line this flow completes (added in one tap, or opened from the cart's «تعديل»): its CTA says
   * «احفظوا في السلة», and its optional add-ons are offered here. A new line gets them in the cart. */
  itemId: string | null;
  back: () => void;
  onEditChild: () => void;
  onEditFamily?: () => void;
  onNewCharacter: () => void;
  onAdd: () => Promise<string | null>;
}) {
  const t = useTranslations("create");
  const locale = useLocale();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const line = product.line as string;
  const name = locale === "ar" ? product.name_ar : product.name_en;
  const variantLine = useVariantLine(product, variant);
  const who = { name: child.name, gender: child.gender };
  const productHref = `/workbooks/${product.slug}?${new URLSearchParams(variant.options).toString()}`;
  const cover = partsFor(product.slug, line, variant.options)[0]?.cover;
  const digital = variant.options.format === "digital";

  async function add() {
    setBusy(true);
    setError(null);
    const failed = await onAdd();
    setBusy(false);
    if (failed) setError(failed);
  }

  return (
    <Frame
      title={t("bookOf", { name: child.name })}
      label={t("steps.summary")}
      back={back}
      footer={
        <Button onClick={add} loading={busy} variant="primary" size="lg" className="grow">
          {itemId ? t("activity.summary.save") : t("activity.summary.add")} <ArrowForward />
        </Button>
      }
    >
      <Lead
        title={t("activity.summary.title", { name: child.name })}
        body={digital ? t("activity.summary.bodyDigital") : t("activity.summary.body")}
      />

      <section
        aria-label={t("activity.summary.book")}
        className="flex items-center gap-3.5 rounded-[20px] border border-line bg-paper-raised p-3"
      >
        <div className="flex h-[104px] w-[78px] shrink-0 items-center justify-center overflow-hidden rounded-[10px] bg-night-100">
          {cover && (
            // eslint-disable-next-line @next/next/no-img-element -- a small static preview from /public
            <img src={cover.sm ?? cover.src} alt="" className="size-full object-cover" decoding="async" />
          )}
        </div>
        <div className="flex min-w-0 grow flex-col gap-1">
          <span className="text-caption text-ink-muted">{t("activity.summary.book")}</span>
          <strong className="text-body-l leading-snug text-night-900">{name}</strong>
          <span className="text-small text-ink">{variantLine}</span>
        </div>
        <Link href={productHref} className={changeClass}>
          {t("activity.summary.change")}
        </Link>
      </section>

      <dl className="flex flex-col rounded-[20px] border border-line bg-paper-raised px-4">
        <Row
          label={t("activity.summary.name")}
          action={
            <button type="button" onClick={onEditChild} className={changeClass}>
              {t("activity.summary.change")}
            </button>
          }
        >
          {child.name}
        </Row>
        {nameEn !== null && (
          <Row
            label={t("activity.summary.nameEn")}
            action={
              <button type="button" onClick={onEditChild} className={changeClass}>
                {t("activity.summary.change")}
              </button>
            }
          >
            {nameEn ? (
              <span dir="ltr" lang="en">
                {nameEn}
              </span>
            ) : (
              "—"
            )}
          </Row>
        )}
        {line === "islamic" ? (
          <Row label={t("activity.summary.certificate")}>
            {t.rich("activity.summary.muslim", { ...who, ar: arabic })}
          </Row>
        ) : (
          <Row label={t("activity.summary.address", { name: child.name })}>
            {t.rich("activity.summary.praise", { ...who, ar: arabic })}
          </Row>
        )}
        <Row
          label={t("activity.summary.character")}
          action={
            <button type="button" onClick={onNewCharacter} className={changeClass}>
              {t("activity.summary.newCharacter")}
            </button>
          }
        >
          {characterId ? (
            // eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store
            <img
              src={characterImage(characterId)}
              alt={t("activity.summary.characterAlt", { name: child.name })}
              className="mt-1 h-[88px] w-[132px] rounded-xl bg-white object-contain"
            />
          ) : (
            "—"
          )}
        </Row>
        {family !== undefined && (
          <Row
            label={t("activity.summary.family")}
            action={
              onEditFamily && (
                <button type="button" onClick={onEditFamily} className={changeClass}>
                  {t("activity.summary.change")}
                </button>
              )
            }
          >
            {family ? (
              <>
                {t.rich("activity.summary.familyName", { family: family.name || child.name, ar: arabic })}
                {family.members.length > 0 && <> · {t("activity.summary.members", { count: family.members.length })}</>}
              </>
            ) : (
              t.rich("activity.summary.noFamily", { ar: arabic })
            )}
          </Row>
        )}
        <Row label={t("activity.summary.price")}>
          {variant.price !== null ? money(variant.price, currency, locale) : "—"}
        </Row>
      </dl>

      <AgeCheck name={child.name} gender={child.gender} age={child.age} ages={ages} href={productHref} />

      {itemId && (
        <details className="rounded-[20px] border border-line bg-paper-raised px-4 py-1">
          <summary className="min-h-12 cursor-pointer content-center text-body font-semibold text-night-900">
            {t("activity.summary.addons")}
          </summary>
          <ItemAddOns itemId={itemId} className="pb-3" />
        </details>
      )}

      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
