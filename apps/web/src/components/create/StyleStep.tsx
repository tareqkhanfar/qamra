"use client";

import { useLocale, useTranslations } from "next-intl";
import { Fragment, useState } from "react";
import { Kid } from "@/components/art/Kid";
import { StyleShowcase } from "@/components/story/StyleShowcase";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import type { ThemeCard } from "@/lib/catalog";
import { classicStyles, classicVariant } from "@/lib/classic";
import { createApi, type Character, type Child } from "@/lib/create";
import { blockedUntilOf, drawsLeft } from "@/lib/drawLimits";
import { variantOf } from "@/lib/examples";
import type { Kind } from "@/lib/flows";
import { initialOutfit, outfitsFor } from "@/lib/outfits";
import { money, type Catalog } from "@/lib/store";
import { containedSample, styleThumb } from "@/lib/styleSamples";
import { DrawLimitNote, useNow } from "./DrawLimit";
import { Check, Frame, Lead } from "./Frame";
import { OutfitPicker, useOutfits } from "./OutfitPicker";

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
 * The art style (design Create4), then the character is drawn right away. Each card has a real picture of that
 * style as its swatch, and the chosen style opens a gallery of real pages (lib/styleSamples).
 *
 * - Stories: the chosen story's pages first. A Classic book offers only the styles that have a live template for
 *   the child's look (and for the chosen story, when there is one).
 * - Activity books (owner, 2026-10-09: the style step is back, with «شبه حقيقي»): every style the book accepts
 *   (`needs.character.styles`), the same sample child's character sheet as the swatch, and her activity-book cover
 *   and owner page first in the gallery. The style only changes the child's character: the activity pages are
 *   drawn once for everyone. The first style the child has no character in is preselected (the parent came for
 *   a new one); the API reuses an approved character in the chosen style unless a newer photo was given.
 *
 * «ماذا يلبس؟» (owner, 2026-10-20): under the styles, what the child wears in the drawing (lib/outfits), preselected
 * as in their last-approved drawing, else the default. Classic stories don't ask: their templates are drawn
 * already, so the step says the child wears the template's clothes.
 *
 * The free drawings come back with time (lib/drawLimits). With none left now, the step says when the next one comes
 * back and goes on with the child's newest drawing in the chosen style (else in another style this book can use),
 * where the parent can choose among the earlier ones; a drawing in the chosen style can always be taken instead of
 * drawing again.
 */
export function StyleStep({
  kind = "story",
  child,
  line,
  sku = null,
  accepted = null,
  catalog,
  themes,
  theme,
  initial,
  title,
  back,
  onDrawing,
}: {
  kind?: Kind;
  child: Child;
  /** The book's line: classic | magic, or the activity line (workbook, journey, family, islamic). */
  line: string;
  /** Activity books: the variant, so the API checks that the book accepts the style. */
  sku?: string | null;
  /** Activity books: the styles the book accepts, in the site's order (the server's `needs`). */
  accepted?: string[] | null;
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
  const activity = kind === "activity";
  const who = nameCases(child.name);
  const ready = classicStyles(themes, classicVariant(child), theme);
  const styles = (catalog?.styles ?? []).filter((s) =>
    activity
      ? s.lines.includes(line) && s.slug !== "coloring" && (!accepted || accepted.includes(s.slug))
      : s.lines.includes(line) && (line !== "classic" || ready.has(s.slug)),
  );
  const noClassic = line === "classic" && catalog !== null && themes.length > 0 && styles.length === 0;
  // the styles the child already has an approved character in: an activity book preselects another one
  const drawn = new Set(child.characters.filter((c) => c.approved).map((c) => c.style));
  const firstNew = styles.find((s) => !drawn.has(s.slug))?.slug;
  const [style, setStyle] = useState<string>(
    initial && styles.some((s) => s.slug === initial)
      ? initial
      : ((activity ? firstNew : null) ?? styles[0]?.slug ?? "watercolor"),
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // the API said none are left until then (the child's own count may be older)
  const [blockedUntil, setBlockedUntil] = useState<string | null>(null);
  const now = useNow();
  const look = variantOf(child);
  const themeNames = Object.fromEntries(themes.map((th) => [th.slug, th.name]));
  const nameOf = (s: { name_ar: string; name_en: string }) => (locale === "ar" ? s.name_ar : s.name_en);
  const places = t(t.has(`character.places.${line}`) ? `character.places.${line}` : "character.places.other");
  const outfitCatalog = useOutfits();
  const offered = outfitsFor(outfitCatalog, child.gender, line);
  const [picked, setPicked] = useState<string | null>(null);
  const outfit = picked ?? initialOutfit(offered, outfitCatalog?.default ?? "classic", child.characters);

  async function draw() {
    setBusy(true);
    setError(null);
    const r = await createApi.draw(
      child.id,
      style,
      [],
      activity ? sku : null,
      undefined,
      offered.length ? outfit : null,
    );
    setBusy(false);
    if (r.ok) return onDrawing(r.data);
    const until = blockedUntilOf(r.error);
    if (until)
      setBlockedUntil(until); // the line below says when, in the parent's own clock
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  // the child's drawings that came out, newest first (the API lists them in drawing order)
  const done = child.characters.filter((c) => c.status === "ready" || c.status === "approved").reverse();
  const sameStyle = done.find((c) => c.style === style) ?? null;
  const earlier = sameStyle ?? done.find((c) => styles.some((s) => s.slug === c.style)) ?? null;
  const left = drawsLeft(child, now, blockedUntil);
  const out = left <= 0;

  return (
    <Frame
      title={title ?? t("bookOf", who)}
      label={t("steps.style")}
      back={back}
      footer={
        out && earlier ? (
          <Button onClick={() => onDrawing(earlier)} size="lg" className="grow">
            {t("style.useEarlier", who)}
          </Button>
        ) : (
          <div className="flex grow flex-col gap-2">
            <Button onClick={draw} loading={busy} size="lg" disabled={!styles.length || out}>
              {t("style.cta", who)}
            </Button>
            {sameStyle && (
              <Button variant="secondary" onClick={() => onDrawing(sameStyle)} disabled={busy}>
                {t("style.useEarlier", who)}
              </Button>
            )}
          </div>
        )
      }
    >
      <Lead
        title={t("style.title", who)}
        body={activity ? t("style.bodyActivity", { ...who, places }) : t("style.body")}
      />
      {noClassic && (
        <div className="flex flex-col gap-3">
          <Alert>{tc("noStyle", { ...who, gender: child.gender })}</Alert>
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
          const swatch = activity ? styleThumb(s.slug, null, look, "character") : styleThumb(s.slug, theme, look);
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
                  className={`relative flex size-[96px] shrink-0 items-end justify-center overflow-hidden rounded-2xl ${swatch ? "bg-paper-sunk" : art.bg}`}
                >
                  {swatch?.kind === "character" ? (
                    // the sheet is three full figures side by side: show the front view, head to hips
                    // eslint-disable-next-line @next/next/no-img-element -- a 480 px static sample sheet as a swatch
                    <img
                      src={swatch.thumb}
                      alt=""
                      width={229}
                      height={154}
                      loading="lazy"
                      className="absolute top-0 left-[7px] h-[154px] w-auto max-w-none"
                    />
                  ) : swatch ? (
                    // eslint-disable-next-line @next/next/no-img-element -- a 480 px static sample page as a swatch
                    <img
                      src={swatch.thumb}
                      alt=""
                      width={96}
                      height={96}
                      loading="lazy"
                      className={`size-full ${containedSample(swatch) ? "object-contain p-1.5" : "object-cover"}`}
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
                  aria-label={ts(activity ? "stepGalleryActivity" : "stepGallery", { style: nameOf(s) })}
                  className="-mt-1 mb-2 flex flex-col gap-2 rounded-3xl bg-paper-sunk p-3"
                >
                  <h3 className="text-body font-semibold text-night-900">
                    {ts(activity ? "stepGalleryActivity" : "stepGallery", { style: nameOf(s) })}
                  </h3>
                  <StyleShowcase
                    styles={[{ slug: s.slug, name: nameOf(s), lines: s.lines }]}
                    theme={activity ? null : theme}
                    themeNames={themeNames}
                    lineNames={{}}
                    value={s.slug}
                    look={look}
                    tabs={false}
                    size="sm"
                    activity={activity}
                  />
                </section>
              )}
            </Fragment>
          );
        })}
      </div>
      {styles.length > 0 && offered.length > 0 && (
        <OutfitPicker child={child} outfits={offered} value={outfit} onChange={setPicked} />
      )}
      {styles.length > 0 && line === "classic" && (
        <p className="rounded-2xl bg-paper-sunk p-4 text-small text-ink">
          {t("outfit.classic", { ...who, gender: child.gender })}
        </p>
      )}
      {styles.length > 0 && <p className="rounded-2xl bg-paper-sunk p-4 text-small text-ink">{t("style.next", who)}</p>}
      {styles.length > 0 && !child.redraws_unlimited && !out && child.redraws_total ? (
        <p className="text-small text-ink-muted">{t("drawLimit.left", { left, total: child.redraws_total })}</p>
      ) : null}
      {out && (
        <DrawLimitNote child={child} now={now} resetAt={blockedUntil ?? child.redraws_reset_at} earlier={!!earlier} />
      )}
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
