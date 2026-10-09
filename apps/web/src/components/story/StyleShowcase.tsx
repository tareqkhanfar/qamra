"use client";

import { useLocale, useTranslations } from "next-intl";
import { useId, useState, type KeyboardEvent } from "react";
import { bookSampleCount, samplesForStyle, styleThumb, type StyleSample } from "@/lib/styleSamples";
import type { ExampleVariant } from "@/lib/examples";
import { StyleGallery } from "./StyleGallery";

export type ShowcaseStyle = { slug: string; name: string; lines: string[] };

/** «أ وب» / «a and b»; «أ، وب، وج» (every Arabic item after the first takes «و») / «a, b and c». */
export function joinWords(words: string[], locale: string): string {
  if (words.length < 2) return words[0] ?? "";
  if (locale === "ar") return [words[0], ...words.slice(1).map((w) => `و${w}`)].join(words.length === 2 ? " " : "، ");
  return `${words.slice(0, -1).join(", ")} and ${words.at(-1)}`;
}

/**
 * The art styles side by side (Tareq, 2026-10-07): a style switch that swaps a gallery of real pages at
 * once, a short line on what the style looks like, and where it is sold. With a story, its own pages come
 * first and pages borrowed from other stories say so. `tabs={false}` hides the switch when the page has its
 * own style picker (the story page's step 2) and passes the chosen style in `value`. `activity`: for an activity
 * book's style step, the sample child's activity-book pages and character sheet first, then story pages.
 */
export function StyleShowcase({
  styles,
  theme = null,
  themeNames = {},
  lineNames,
  value,
  onChange,
  look = null,
  tabs = true,
  size = "md",
  activity = false,
}: {
  styles: ShowcaseStyle[];
  theme?: string | null;
  themeNames?: Record<string, string>;
  lineNames: Partial<Record<string, string>>;
  value?: string | null;
  onChange?: (slug: string) => void;
  look?: ExampleVariant | null;
  tabs?: boolean;
  size?: "sm" | "md";
  activity?: boolean;
}) {
  const t = useTranslations("storyShowcase");
  const locale = useLocale();
  const id = useId();
  const [own, setOwn] = useState<string | null>(null);
  const shown = styles.filter((s) => samplesForStyle(s.slug, null, { activity }).length > 0);
  const current = shown.find((s) => s.slug === (value ?? own)) ?? shown[0];
  if (!current) return null;

  const pick = (slug: string) => {
    setOwn(slug);
    onChange?.(slug);
    // a tab half off a phone screen slides into view when chosen
    document
      .getElementById(`${id}-tab-${slug}`)
      ?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  };

  function onKey(e: KeyboardEvent<HTMLDivElement>) {
    const i = shown.findIndex((s) => s.slug === current?.slug);
    const forward = locale === "ar" ? "ArrowLeft" : "ArrowRight";
    const back = locale === "ar" ? "ArrowRight" : "ArrowLeft";
    let next = i;
    if (e.key === forward) next = (i + 1) % shown.length;
    else if (e.key === back) next = (i - 1 + shown.length) % shown.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = shown.length - 1;
    else return;
    e.preventDefault();
    const target = shown[next];
    if (!target) return;
    pick(target.slug);
    document.getElementById(`${id}-tab-${target.slug}`)?.focus();
  }

  const samples = samplesForStyle(current.slug, theme, { look, activity });
  const ownCount = theme ? bookSampleCount(current.slug, theme) : 0;
  const books = bookSampleCount(current.slug);
  // the chip counts story pages (not covers): this story's own when it has some, else the style's
  const pageCount = samplesForStyle(current.slug, ownCount ? theme : null, { strict: !!ownCount }).filter(
    (s) => s.kind === "page",
  ).length;
  const sold = activity
    ? []
    : ["classic", "magic"].filter((l) => current.lines.includes(l) && lineNames[l]).map((l) => lineNames[l]!);
  const story = (s: StyleSample) => (s.theme ? themeNames[s.theme] : undefined);
  const caption = (s: StyleSample): string | null => {
    if (s.kind === "companion") return t("caption.companion");
    if (s.kind === "character") return t("caption.character");
    if (s.kind === "activity") return t("caption.activity");
    const name = story(s);
    if (activity) return name ? t("caption.from", { story: name }) : null;
    if (theme && s.theme === theme) return null; // this story's own page
    return name ? t(theme ? "caption.from" : "caption.story", { story: name }) : null;
  };
  const note = activity
    ? null
    : books === 0
      ? t("note.companionOnly")
      : theme && ownCount === 0
        ? t("note.otherStories")
        : null;

  return (
    <div className="flex flex-col gap-3.5">
      {tabs && (
        <div
          role="tablist"
          aria-label={t("tabsLabel")}
          onKeyDown={onKey}
          className="-mx-4 flex [scrollbar-width:none] gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:px-0 [&::-webkit-scrollbar]:hidden"
        >
          {shown.map((s) => {
            const on = s.slug === current.slug;
            const thumb = styleThumb(s.slug, theme, look, activity ? "character" : "cover");
            return (
              <button
                key={s.slug}
                id={`${id}-tab-${s.slug}`}
                type="button"
                role="tab"
                aria-selected={on}
                aria-controls={`${id}-panel`}
                tabIndex={on ? 0 : -1}
                onClick={() => pick(s.slug)}
                className={`flex min-h-12 shrink-0 items-center gap-2 rounded-full border-[1.5px] py-1 ps-1 pe-4 text-[15px] whitespace-nowrap transition ${
                  on
                    ? "border-night-900 bg-night-900 font-semibold text-paper"
                    : "border-line bg-paper-raised text-ink hover:border-night-500"
                }`}
              >
                {thumb && (
                  // eslint-disable-next-line @next/next/no-img-element -- a 480 px static sample as a swatch
                  <img
                    src={thumb.thumb}
                    alt=""
                    width={36}
                    height={36}
                    loading="lazy"
                    className={`size-9 rounded-full bg-paper object-cover ${on ? "ring-2 ring-amber-500" : ""}`}
                  />
                )}
                {s.name}
              </button>
            );
          })}
        </div>
      )}
      <div
        id={`${id}-panel`}
        role={tabs ? "tabpanel" : undefined}
        aria-labelledby={tabs ? `${id}-tab-${current.slug}` : undefined}
        className="flex flex-col gap-3"
      >
        <div className="flex flex-col gap-1.5">
          {t.has(`styles.${current.slug}`) && (
            <p className="text-body leading-[1.7] text-ink">{t(`styles.${current.slug}`)}</p>
          )}
          {sold.length > 0 && (
            <p className="flex flex-wrap items-center gap-2 text-caption font-semibold">
              <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">
                {t("soldIn", { lines: joinWords(sold, locale) })}
              </span>
              {pageCount > 0 && (
                <span className="rounded-full bg-paper-sunk px-2.5 py-1 text-ink-muted">
                  {t("realPages", { count: pageCount })}
                </span>
              )}
            </p>
          )}
        </div>
        <StyleGallery
          samples={samples}
          caption={caption}
          label={t("galleryLabel", { style: current.name })}
          size={size}
        />
        {note && <p className="text-small leading-[1.6] text-ink-muted">{note}</p>}
      </div>
    </div>
  );
}
