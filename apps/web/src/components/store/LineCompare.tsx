"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { joinWords } from "@/components/story/StyleShowcase";
import { AddonList, extraAddons, includedAddons, type AddonMedia } from "@/components/story/AddonList";
import { SampleLightbox } from "@/components/story/SampleLightbox";
import { Link } from "@/i18n/navigation";
import { money, type Catalog } from "@/lib/store";
import { LINES, createHref, offer, type Line } from "@/lib/story";
import { sampleAlt, samplesForStyle, styleThumb, type StyleSample } from "@/lib/styleSamples";

/**
 * A page to stand for a line in a style: a story page (not a cover), the same moment as `scene` if drawn,
 * else whatever the style has (the companion's sheet when no book page is published in it).
 */
function pageIn(style: string, theme: string | null, scene?: string): StyleSample | null {
  const all = samplesForStyle(style, theme);
  const pages = all.filter((s) => s.kind === "page");
  return pages.find((s) => s.scene === scene) ?? pages[0] ?? all[0] ?? null;
}

/**
 * «قمرة كلاسيك» and «قمرة سحري» side by side (Addendum 4 §7: "clear sample pages so the difference is
 * obvious"), with a style switch: each card shows a real page in the chosen style, or, when its line doesn't
 * sell that style, its own style and a note. Prices, styles, what is included and delivery all come from the
 * catalog. With `theme` the buttons start that story's free preview; without, they open the stories.
 */
export function LineCompare({
  catalog,
  theme = null,
  pages = null,
  media,
}: {
  catalog: Catalog | null;
  theme?: string | null;
  pages?: number | null;
  media?: AddonMedia;
}) {
  const t = useTranslations("storyShowcase.lines");
  const tf = useTranslations("store.formats");
  const te = useTranslations("storyShowcase.extras");
  const locale = useLocale();
  const ar = locale === "ar";
  const currency = catalog?.currency ?? "ILS";
  const name = (x: { name_ar: string; name_en: string }) => (ar ? x.name_ar : x.name_en);

  const offers = LINES.map((l) => offer(catalog, l)).filter((o) => o !== null);
  const storyStyles = (catalog?.styles ?? []).filter(
    (s) => (s.lines.includes("classic") || s.lines.includes("magic")) && samplesForStyle(s.slug).length > 0,
  );
  const both = storyStyles.find((s) => s.lines.includes("classic") && s.lines.includes("magic"));
  const [picked, setPicked] = useState<string | null>(null);
  const chosen = storyStyles.find((s) => s.slug === picked) ?? both ?? storyStyles[0];
  const [zoom, setZoom] = useState<{ list: StyleSample[]; i: number } | null>(null);
  if (!offers.length || !chosen) return null;

  const magicName = offers.find((o) => o.line === "magic")?.product;
  const zones = catalog?.zones ?? [];
  const eta = zones.flatMap((z) => z.eta_days);
  const facts = [
    pages ? t("facts.pages", { count: pages }) : null,
    t("facts.preview"),
    t("facts.cod"),
    zones.length && eta.length
      ? t("facts.delivery", {
          zones: joinWords(zones.map(name), locale),
          min: Math.min(...eta),
          max: Math.max(...eta),
        })
      : null,
  ].filter((f): f is string => !!f);

  // the Magic card shows the chosen style; the Classic card the same moment in its own style when it differs
  const magicPage = pageIn(chosen.slug, theme);
  const cards = offers.map((o) => {
    const line = o.line as Line;
    const sells = storyStyles.filter((s) => s.lines.includes(line));
    const own = sells.find((s) => s.slug === chosen.slug) ?? sells[0];
    const sample = own ? pageIn(own.slug, theme, magicPage?.scene) : null;
    const points = [
      ...(t.raw(`${line}.points`) as string[]),
      sells.length
        ? t(sells.length > 1 ? "stylesMany" : "stylesOne", { styles: joinWords(sells.map(name), locale) })
        : null,
    ].filter((p): p is string => !!p);
    const included = includedAddons(catalog, line).map(name);
    return { o, line, own, sample, points, included, other: own && own.slug !== chosen.slug };
  });

  // the extras of both lines in one list, each saying when only one line offers it or the other includes it
  const lineName = (l: string) => {
    const p = offers.find((o) => o.line === l)?.product;
    return p ? name(p) : l;
  };
  const extras = [...extraAddons(catalog, "classic"), ...extraAddons(catalog, "magic")].filter(
    (a, i, all) => all.findIndex((b) => b.slug === a.slug) === i,
  );
  const tag = (a: (typeof extras)[number]) => {
    const offered = offers.map((o) => o.line).filter((l) => extraAddons(catalog, l).some((b) => b.slug === a.slug));
    const inside = offers.map((o) => o.line).filter((l) => a.included_lines.includes(l));
    if (inside.length) return te("includedIn", { line: joinWords(inside.map(lineName), locale) });
    if (offered.length === 1 && offers.length > 1) return te("onlyIn", { line: lineName(offered[0]!) });
    return null;
  };

  return (
    <section className="flex flex-col gap-4" aria-labelledby="line-compare-title">
      <div className="flex flex-col gap-1.5">
        <h2 id="line-compare-title" className="text-[26px] text-night-900 md:text-h2">
          {t("title")}
        </h2>
        <p className="max-w-[680px] text-body leading-[1.7] text-ink-muted">{t("lead")}</p>
      </div>

      <div role="radiogroup" aria-label={t("switchLabel")} className="flex flex-wrap items-center gap-2">
        <span className="text-small font-semibold text-ink-muted">{t("switchLabel")}</span>
        {storyStyles.map((s) => {
          const on = s.slug === chosen.slug;
          const thumb = styleThumb(s.slug, theme);
          return (
            <button
              key={s.slug}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => setPicked(s.slug)}
              className={`flex min-h-11 items-center gap-2 rounded-full border-[1.5px] py-1 ps-1 pe-3.5 text-small transition ${on ? "border-night-900 bg-night-900 font-semibold text-paper" : "border-line bg-paper-raised text-ink hover:border-night-500"}`}
            >
              {thumb && (
                // eslint-disable-next-line @next/next/no-img-element -- a static sample as a swatch
                <img src={thumb.thumb} alt="" width={32} height={32} className="size-8 rounded-full object-cover" />
              )}
              {name(s)}
            </button>
          );
        })}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 md:gap-5">
        {cards.map(({ o, line, own, sample, points, included, other }) => {
          const dark = line === "magic";
          const list = own ? samplesForStyle(own.slug, theme) : [];
          return (
            <article
              key={line}
              className={`relative flex flex-col overflow-hidden rounded-[20px] ${dark ? "bg-night-900 text-paper" : "border border-line bg-paper-raised text-ink"}`}
            >
              <span
                className={`absolute end-3 top-3 z-10 rounded-full px-2.5 py-0.5 text-caption font-bold ${dark ? "bg-amber-500 text-night-950" : "bg-night-100 text-night-900"}`}
              >
                {t(dark ? "best" : "popular")}
              </span>
              {sample && (
                <button
                  type="button"
                  onClick={() =>
                    setZoom({
                      list,
                      i: Math.max(
                        0,
                        list.findIndex((s) => s.id === sample.id),
                      ),
                    })
                  }
                  aria-label={t("zoom", { page: sampleAlt(sample, locale) })}
                  className={`relative flex aspect-[4/3] w-full cursor-zoom-in sm:aspect-[16/10] items-center justify-center overflow-hidden p-4 ${dark ? "bg-night-800" : "bg-paper-sunk"}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- static sample pages in two sizes */}
                  <img
                    src={sample.thumb}
                    srcSet={`${sample.thumb} 480w, ${sample.src} 900w`}
                    sizes="(min-width: 640px) 45vw, 100vw"
                    width={sample.width}
                    height={sample.height}
                    alt=""
                    loading="lazy"
                    className={`h-full w-auto max-w-full rounded-md object-contain shadow-book ${sample.kind === "companion" ? "bg-white" : ""}`}
                  />
                  <span className="absolute start-3 bottom-3 rounded-full bg-night-950/80 px-2.5 py-1 text-caption font-semibold text-paper">
                    {own ? t("styleChip", { style: name(own) }) : null}
                  </span>
                </button>
              )}
              <div className="flex grow flex-col gap-3 p-4 md:p-5">
                {other && own && (
                  <p
                    className={`rounded-md px-3 py-2 text-caption leading-[1.5] ${dark ? "bg-night-800 text-night-100" : "bg-amber-100 text-amber-700"}`}
                  >
                    {t("onlyIn", { style: name(chosen), line: magicName ? name(magicName) : "", own: name(own) })}
                  </p>
                )}
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className={`font-display text-[22px] ${dark ? "text-amber-300" : "text-night-900"}`}>
                    {name(o.product)}
                  </h3>
                  {o.from !== null && (
                    <span className="text-small whitespace-nowrap">
                      {t.rich("from", {
                        price: money(o.from, currency, locale),
                        b: (chunks) => <strong className="text-[18px]">{chunks}</strong>,
                      })}
                    </span>
                  )}
                </div>
                <p className={`text-small ${dark ? "text-night-100" : "text-ink-muted"}`}>{t(`${line}.tagline`)}</p>
                <ul className="flex flex-col gap-1.5 text-small leading-[1.6]">
                  {points.map((point) => (
                    <li key={point} className="flex items-start gap-2">
                      <span aria-hidden="true" className={dark ? "text-amber-300" : "text-success"}>
                        ✓
                      </span>
                      {point}
                    </li>
                  ))}
                </ul>
                {included.length > 0 && (
                  <div className={`rounded-md px-3 py-2.5 ${dark ? "bg-night-800" : "bg-success-bg/60"}`}>
                    <p className={`mb-1 text-caption font-bold ${dark ? "text-amber-300" : "text-success"}`}>
                      {t("included")}
                    </p>
                    <ul className="flex flex-col gap-1 text-small leading-[1.5]">
                      {included.map((item) => (
                        <li key={item} className="flex items-start gap-2">
                          <span aria-hidden="true">✓</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="mt-auto flex flex-wrap gap-1.5 pt-1 text-caption">
                  {o.formats.map((v) => (
                    <span
                      key={v.sku}
                      className={`rounded-full px-2.5 py-1 ${dark ? "bg-night-800 text-night-100" : "bg-paper-sunk"}`}
                    >
                      {tf(v.options.format)} · {v.price ? money(v.price, currency, locale) : "—"}
                    </span>
                  ))}
                </div>
                <Link
                  href={theme ? createHref(theme, line) : `/stories?line=${line}`}
                  className={`flex min-h-12 items-center justify-center rounded-full px-5 text-body font-bold ${dark ? "bg-amber-500 text-night-950 hover:shadow-lamp" : "border-[1.5px] border-night-900 text-night-900 hover:bg-paper-sunk"}`}
                >
                  {t(theme ? "start" : "browse")}
                </Link>
              </div>
            </article>
          );
        })}
      </div>

      {facts.length > 0 && (
        <div className="rounded-[18px] bg-paper-sunk px-4 py-3.5">
          <h3 className="mb-2 text-small font-bold text-night-900">{t("facts.title")}</h3>
          <ul className="grid gap-x-6 gap-y-1.5 text-small leading-[1.6] sm:grid-cols-2">
            {facts.map((f) => (
              <li key={f} className="flex items-start gap-2">
                <span aria-hidden="true" className="text-success">
                  ✓
                </span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}
      {extras.length > 0 && (
        <div className="flex flex-col gap-2.5">
          <div className="flex flex-col gap-0.5">
            <h3 className="text-[19px] text-night-900">{te("title")}</h3>
            <p className="text-small text-ink-muted">{te("lead")}</p>
          </div>
          <AddonList addons={extras} catalog={catalog} media={media} tag={tag} initial={4} />
        </div>
      )}
      <SampleLightbox
        samples={zoom?.list ?? []}
        index={zoom?.i ?? null}
        onIndex={(i) => setZoom(i === null || !zoom ? null : { ...zoom, i })}
      />
    </section>
  );
}
