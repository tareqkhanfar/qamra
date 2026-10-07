"use client";

import { useLocale, useTranslations } from "next-intl";
import type { CSSProperties } from "react";
import { Kid } from "@/components/art/Kid";
import { ExampleImage } from "@/components/book/ExampleImage";
import type { ExamplePage, ExampleVariant } from "@/lib/examples";
import { money, type Currency } from "@/lib/store";
import { addonFor, num, type Line, type Offer, type StyleChoice } from "@/lib/story";
import type { Catalog, CatalogVariant } from "@/lib/store";
import { styleThumb } from "@/lib/styleSamples";

/** Design StoryProduct: each style's swatch look (a real sample image replaces it when the admin adds one). */
export const STYLE_LOOK: Record<string, { bg: string; fx: CSSProperties }> = {
  watercolor: {
    bg: "bg-[radial-gradient(circle_at_30%_30%,#CBC1EA_0,transparent_45%),#F3EAD8]",
    fx: { filter: "saturate(0.8) contrast(0.92)" },
  },
  cartoon: { bg: "bg-amber-100", fx: { filter: "saturate(1.35)" } },
  "3d": { bg: "bg-night-100", fx: { filter: "drop-shadow(0 6px 0 rgba(22,32,74,0.2)) saturate(1.2)" } },
  "semi-realistic": { bg: "bg-success-bg", fx: { filter: "contrast(1.1) saturate(0.9)" } },
  coloring: { bg: "bg-white", fx: { filter: "grayscale(1) contrast(1.6)" } },
};

const card = (on: boolean) =>
  on ? "border-[3px] border-amber-500 shadow-[0_8px_24px_rgba(242,179,61,0.25)]" : "border-[1.5px] border-line";

/** Step 1: Classic («الأكثر طلباً») and Magic («الأفخم») side by side, each with a small real page. */
export function LineCards({
  offers,
  value,
  onChange,
  currency,
  pages,
}: {
  offers: Offer[];
  value: Line;
  onChange: (l: Line) => void;
  currency: Currency;
  pages?: Partial<Record<Line, ExamplePage | undefined>>;
}) {
  const t = useTranslations("themeDetail.lines");
  const locale = useLocale();
  return (
    <div role="radiogroup" aria-label={t("label")} className="grid grid-cols-2 gap-2.5">
      {offers.map((o) => {
        const on = o.line === value;
        const dark = o.line === "magic";
        const page = pages?.[o.line];
        return (
          <button
            key={o.line}
            type="button"
            role="radio"
            aria-checked={on}
            aria-disabled={!o.available}
            onClick={() => o.available && onChange(o.line)}
            className={`flex min-h-[170px] flex-col items-start gap-1.5 overflow-hidden rounded-[20px] p-3.5 text-start transition ${dark ? "bg-night-900 text-paper" : "bg-paper-raised text-ink"} ${card(on)} ${o.available ? "" : "cursor-not-allowed opacity-60"}`}
          >
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${dark ? "bg-amber-500 text-night-950" : "bg-night-100 text-night-900"}`}
            >
              {t(`${o.line}.tag`)}
            </span>
            {page && (
              <span className="relative -mx-0.5 my-1 block aspect-[16/10] w-[calc(100%+4px)] overflow-hidden rounded-xl">
                <ExampleImage page={page} alt="" sizes="180px" className="absolute inset-0 size-full object-cover" />
              </span>
            )}
            <strong className="font-display text-[18px]">
              {locale === "ar" ? o.product.name_ar : o.product.name_en}
            </strong>
            <span className={`text-caption leading-[1.5] ${dark ? "text-night-100" : "text-ink-muted"}`}>
              {t(`${o.line}.desc`)}
            </span>
            <strong className="mt-auto text-[17px]">
              {!o.available
                ? t("unavailable")
                : o.from === null
                  ? "—"
                  : o.formats.length > 1
                    ? t("from", { price: money(o.from, currency, locale) })
                    : money(o.from, currency, locale)}
            </strong>
          </button>
        );
      })}
    </div>
  );
}

/** The chosen line's checklist: ✓ what is included, + what is an extra (with its price). */
export function LineFeatures({ items }: { items: { ok: boolean; text: string }[] }) {
  return (
    <ul className="flex flex-col gap-2 rounded-[18px] border border-line bg-paper-raised px-4 py-3.5">
      {items.map((f) => (
        <li key={f.text} className="flex items-start gap-2.5 text-[15px] leading-[1.6]">
          <span
            aria-hidden="true"
            className={`flex size-[22px] shrink-0 items-center justify-center rounded-full text-[13px] font-extrabold ${f.ok ? "bg-success-bg text-success" : "bg-amber-100 text-amber-700"}`}
          >
            {f.ok ? "✓" : "+"}
          </span>
          <span className={f.ok ? "text-ink" : "text-ink-muted"}>{f.text}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * Step 2: the art styles, each with a real sample page (a page of this story in that style when there is one,
 * public/samples via lib/styleSamples). A style the line can't sell yet is disabled («متوفر في سحري»).
 */
export function StyleCards({
  choices,
  value,
  onChange,
  line,
  currency,
  theme,
  look,
}: {
  choices: StyleChoice[];
  value: string | null;
  onChange: (slug: string) => void;
  line: Line;
  currency: Currency;
  theme?: string | null;
  look?: ExampleVariant | null;
}) {
  const t = useTranslations("themeDetail.styles");
  const tv = useTranslations("examples.variant");
  const locale = useLocale();
  return (
    <div role="radiogroup" aria-label={t("label")} className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
      {choices.map(({ style, available, looks, modifier }) => {
        const on = available && style.slug === value;
        const swatch = STYLE_LOOK[style.slug] ?? STYLE_LOOK.watercolor!;
        const sample = style.sample_images[0] ?? styleThumb(style.slug, theme, look, "page")?.thumb;
        const partial = line === "classic" && available && looks && looks.length < 3;
        const note = !available
          ? t(line === "classic" && style.lines.includes("magic") ? "onlyMagic" : "unavailable")
          : partial
            ? t("onlyLooks", { looks: looks.map((l) => tv(l)).join("، ") })
            : on
              ? t("chosen")
              : modifier > 0
                ? t("plus", { price: money(modifier, currency, locale) })
                : t("samePrice");
        return (
          <button
            key={style.slug}
            type="button"
            role="radio"
            aria-checked={on}
            aria-disabled={!available}
            onClick={() => available && onChange(style.slug)}
            className={`flex flex-col items-center gap-1.5 rounded-[18px] bg-paper-raised p-2.5 transition ${available ? card(on) : "cursor-not-allowed border-[1.5px] border-dashed border-line opacity-50"}`}
          >
            <span
              className={`flex h-[84px] w-full items-end justify-center overflow-hidden rounded-xl ${sample ? "" : swatch.bg}`}
            >
              {sample ? (
                // eslint-disable-next-line @next/next/no-img-element -- admin-provided or static style sample
                <img src={sample} alt="" loading="lazy" className="size-full object-cover" />
              ) : (
                <span style={swatch.fx} className="w-16">
                  <Kid skin="#C98F63" hairStyle="curly" outfit="#5B6FC0" className="block h-auto w-full" />
                </span>
              )}
            </span>
            <strong className="text-[15px]">{locale === "ar" ? style.name_ar : style.name_en}</strong>
            <span className="text-center text-[12px] leading-snug text-ink-muted">{note}</span>
          </button>
        );
      })}
    </div>
  );
}

/** Step 3: the formats of the chosen line, with their live prices (the style's modifier included). */
export function FormatCards({
  formats,
  value,
  onChange,
  modifier,
  currency,
  freeDigital,
  popular,
}: {
  formats: CatalogVariant[];
  value: string | null;
  onChange: (sku: string) => void;
  modifier: number;
  currency: Currency;
  freeDigital: boolean;
  popular?: string | null;
}) {
  const t = useTranslations("themeDetail.formats");
  const locale = useLocale();
  return (
    <div role="radiogroup" aria-label={t("label")} className="flex flex-col gap-2.5">
      {formats.map((v) => {
        const on = v.sku === value;
        const format = v.options.format ?? "";
        const size = (v.options.size ?? "").replace("x", "×");
        const printed = format !== "digital";
        const desc = [
          t.has(`desc.${format}`) ? t(`desc.${format}`, { size }) : "",
          printed && freeDigital ? t("withDigital") : "",
        ]
          .filter(Boolean)
          .join(" · ");
        return (
          <button
            key={v.sku}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(v.sku)}
            className={`flex min-h-[68px] items-center gap-3 rounded-[18px] px-4 py-3 text-start text-ink ${on ? "border-2 border-night-900 bg-night-100" : "border-[1.5px] border-line bg-paper-raised"}`}
          >
            <span
              aria-hidden="true"
              className={`size-[22px] shrink-0 rounded-full bg-white ${on ? "border-[7px] border-night-900" : "border-2 border-[#C9BCA3]"}`}
            />
            <span className="flex grow flex-col gap-0.5">
              <span className="flex flex-wrap items-center gap-2">
                <strong className="text-body">{t.has(`name.${format}`) ? t(`name.${format}`) : format}</strong>
                {popular === format && (
                  <span className="rounded-full bg-amber-500 px-2 py-0.5 text-[11px] font-bold text-night-950">
                    {t("popular")}
                  </span>
                )}
              </span>
              <span className="text-caption text-ink-muted">{desc}</span>
            </span>
            <strong className="text-[17px] whitespace-nowrap">
              {money(num(v.price) + modifier, currency, locale)}
            </strong>
          </button>
        );
      })}
    </div>
  );
}

/** The chosen line's checklist from the catalog: what is included (✓) and what is an extra (+ its price). */
export function LineChecklist({ line, catalog }: { line: Line; catalog: Catalog | null }) {
  const t = useTranslations("themeDetail.features");
  const locale = useLocale();
  const currency = catalog?.currency ?? "ILS";
  const companion = addonFor(catalog, "drawing-companion", line);
  const dedication = addonFor(catalog, "dedication-page", line);
  const items = [{ ok: true, text: t(`${line}.art`) }];
  if (line === "classic") items.push({ ok: true, text: t("classic.name") }, { ok: true, text: t("classic.fast") });
  if (companion?.included) items.push({ ok: true, text: t("companion") });
  if (dedication?.included) items.push({ ok: true, text: t("dedication") });
  if (line === "magic") items.push({ ok: true, text: t("magic.text") });
  if (companion && !companion.included && companion.offered && companion.addon.price)
    items.push({ ok: false, text: t("companionExtra", { price: money(companion.addon.price, currency, locale) }) });
  return <LineFeatures items={items.slice(0, 5)} />;
}
