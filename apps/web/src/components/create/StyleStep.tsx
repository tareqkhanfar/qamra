"use client";

import { useLocale, useTranslations } from "next-intl";
import { Fragment, useState } from "react";
import { Kid } from "@/components/art/Kid";
import { StyleShowcase } from "@/components/story/StyleShowcase";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import { classicStyles, classicVariant } from "@/lib/classic";
import { createApi, type Character, type Child, type Line } from "@/lib/create";
import { variantOf } from "@/lib/examples";
import { money, type Catalog } from "@/lib/store";
import { styleThumb } from "@/lib/styleSamples";
import { Check, Frame, Lead } from "./Frame";

/** How a style's card hints at its look when there is no real page in that style yet. */
const LOOK: Record<string, { bg: string; fx: string }> = {
  watercolor: {
    bg: "bg-[radial-gradient(circle_at_30%_30%,#CBC1EA_0,transparent_45%),radial-gradient(circle_at_70%_60%,#FCEFD2_0,transparent_50%),#F3EAD8]",
    fx: "saturate-[0.85]",
  },
  cartoon: { bg: "bg-[#E4E8F7]", fx: "saturate-[1.3] contrast-[1.1]" },
  "3d": {
    bg: "bg-[radial-gradient(circle_at_50%_35%,#FFFDF8_0,#DDEFE3_70%)]",
    fx: "drop-shadow-[0_8px_0_rgba(22,32,74,0.18)]",
  },
  "semi-realistic": { bg: "bg-[#F3EAD8]", fx: "saturate-[0.9] contrast-[1.05]" },
  coloring: { bg: "bg-white", fx: "grayscale contrast-[1.6]" },
};

/**
 * Step 5 (design Create4), stories only: the art style, then the character is drawn right away. Each card has a
 * real page of that style as its swatch, and the chosen style opens a gallery of real pages (the chosen story's
 * first; lib/styleSamples). A Classic book offers only the styles that have a live template for the child's
 * look (and for the chosen story, when there is one). Activity books never show this step: their character is
 * drawn in the product's own style (owner decision, 2026-10-07).
 */
export function StyleStep({
  child,
  line,
  catalog,
  themes,
  theme,
  initial,
  title,
  back,
  onDrawing,
}: {
  child: Child;
  line: Line;
  catalog: Catalog | null;
  themes: ThemeCard[];
  theme: string | null;
  initial: string | null;
  title?: string; // the frame title; the wizard's FlowFrameContext wins when present
  back: () => void;
  onDrawing: (c: Character) => void;
}) {
  const t = useTranslations("create");
  const ts = useTranslations("storyShowcase");
  const tc = useTranslations("classic");
  const te = useTranslations("errors");
  const locale = useLocale();
  const ready = classicStyles(themes, classicVariant(child), theme);
  const styles = (catalog?.styles ?? []).filter(
    (s) => s.lines.includes(line) && (line !== "classic" || ready.has(s.slug)),
  );
  const noClassic = line === "classic" && catalog !== null && themes.length > 0 && styles.length === 0;
  const [style, setStyle] = useState<string>(
    initial && styles.some((s) => s.slug === initial) ? initial : (styles[0]?.slug ?? "watercolor"),
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const look = variantOf(child);
  const themeNames = Object.fromEntries(themes.map((th) => [th.slug, th.name]));
  const nameOf = (s: { name_ar: string; name_en: string }) => (locale === "ar" ? s.name_ar : s.name_en);

  async function draw() {
    setBusy(true);
    setError(null);
    const r = await createApi.draw(child.id, style);
    setBusy(false);
    if (r.ok) onDrawing(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <Frame
      title={title ?? t("bookOf", { name: child.name })}
      label={t("steps.style")}
      back={back}
      footer={
        <Button onClick={draw} loading={busy} size="lg" className="grow" disabled={!styles.length}>
          {t("style.cta", { name: child.name })}
        </Button>
      }
    >
      <Lead title={t("style.title", { name: child.name })} body={t("style.body")} />
      {noClassic && (
        <div className="flex flex-col gap-3">
          <Alert>{tc("noStyle", { name: child.name })}</Alert>
          <Button variant="secondary" onClick={back} className="self-start">
            {tc("toMagic")}
          </Button>
        </div>
      )}
      <div className="flex flex-col gap-3" role="radiogroup" aria-label={t("steps.style")}>
        {styles.map((s, i) => {
          const on = style === s.slug;
          const art = LOOK[s.slug] ?? LOOK.watercolor;
          const extra = Number(s.price_modifier) > 0;
          const swatch = styleThumb(s.slug, theme, look);
          return (
            <Fragment key={s.slug}>
              <button
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => setStyle(s.slug)}
                className={`relative flex items-center gap-3.5 rounded-3xl bg-paper-raised p-2.5 text-start transition ${on ? "border-[3px] border-amber-500 shadow-[0_8px_24px_rgba(242,179,61,0.25)]" : "border-[1.5px] border-line"}`}
              >
                <div
                  className={`flex size-[96px] shrink-0 items-end justify-center overflow-hidden rounded-2xl ${swatch ? "bg-paper-sunk" : art.bg}`}
                >
                  {swatch ? (
                    // eslint-disable-next-line @next/next/no-img-element -- a 480 px static sample page as a swatch
                    <img
                      src={swatch.thumb}
                      alt=""
                      width={96}
                      height={96}
                      loading="lazy"
                      className={`size-full ${swatch.kind === "companion" ? "object-contain p-1.5" : "object-cover"}`}
                    />
                  ) : s.sample_images[0] ? (
                    // eslint-disable-next-line @next/next/no-img-element -- admin-uploaded sample art
                    <img src={s.sample_images[0]} alt="" className="size-full object-cover" />
                  ) : (
                    <div className={art.fx}>
                      <Kid
                        hijab={child.hijab}
                        hijabColor="#E9826B"
                        outfit="#F2B33D"
                        pose="wave"
                        className="h-auto w-[78px]"
                      />
                    </div>
                  )}
                </div>
                <div className="flex grow flex-col gap-1.5 py-1">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-[20px] text-night-900">{nameOf(s)}</h2>
                    <Check on={on} />
                  </div>
                  {t.has(`style.desc.${s.slug}`) && (
                    <p className="text-small text-ink-muted">{t(`style.desc.${s.slug}`)}</p>
                  )}
                  {(i === 0 || extra) && (
                    <div className="flex flex-wrap gap-1.5">
                      {i === 0 && (
                        <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-caption font-bold text-amber-700">
                          {t("style.popular")}
                        </span>
                      )}
                      {extra && (
                        <span className="rounded-full bg-paper-sunk px-2.5 py-0.5 text-caption font-semibold">
                          {t("style.extra", { amount: money(s.price_modifier, catalog?.currency ?? "ILS", locale) })}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </button>
              {on && swatch && (
                <section
                  aria-label={ts("stepGallery", { style: nameOf(s) })}
                  className="-mt-1 mb-2 flex flex-col gap-2 rounded-3xl bg-paper-sunk p-3"
                >
                  <h3 className="text-body font-semibold text-night-900">{ts("stepGallery", { style: nameOf(s) })}</h3>
                  <StyleShowcase
                    styles={[{ slug: s.slug, name: nameOf(s), lines: s.lines }]}
                    theme={theme}
                    themeNames={themeNames}
                    lineNames={{}}
                    value={s.slug}
                    look={look}
                    tabs={false}
                    size="sm"
                  />
                </section>
              )}
            </Fragment>
          );
        })}
      </div>
      {styles.length > 0 && (
        <p className="rounded-2xl bg-paper-sunk p-4 text-small text-ink">{t("style.next", { name: child.name })}</p>
      )}
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
