import { useLocale, useTranslations } from "next-intl";
import { CoverArt } from "@/components/book/CoverArt";
import { Link } from "@/i18n/navigation";
import { Arrow } from "./blocks";
import type { ThemeCard } from "@/lib/catalog";
import type { Example } from "@/lib/examples";
import { money, type Currency } from "@/lib/store";
import { styleThumb } from "@/lib/styleSamples";
import { themeArt } from "@/lib/themeArt";

/**
 * A story in the shop's card style (Addendum 9): its real cover when an example is published (else the
 * illustrated placeholder with the same title treatment), age and pages, and the price it starts from.
 * Only stories on sale are ever passed here (the site lists nothing that can't be ordered).
 */
export function StoryCard({
  theme,
  example,
  from,
  currency = "ILS",
  line,
  priority = false,
  styles = [],
  classic,
}: {
  theme: ThemeCard;
  example: Example | null;
  from: number | null;
  currency?: Currency;
  line?: string | null;
  priority?: boolean;
  /** The art styles this story can be drawn in (catalog order): a small real sample of each. */
  styles?: { slug: string; name: string }[];
  /** The styles it is sold in as «قمرة كلاسيك» ([] = «قمرة سحري» only; undefined = not shown). */
  classic?: string[];
}) {
  const t = useTranslations("themes");
  const ts = useTranslations("storyShowcase");
  const tc = useTranslations("common");
  const locale = useLocale();
  // the placeholder cover carries the story's name; a real cover the example's own title
  const [name, rest] = example ? [example.title_name, example.title_rest] : [theme.name, ""];
  const body = (
    <>
      <div className="relative">
        <CoverArt
          example={example}
          art={theme.art}
          picture={themeArt(theme.slug)}
          titleName={name}
          titleRest={rest}
          alt={example ? t("coverAlt", { name: theme.name }) : t("placeholderAlt", { name: theme.name })}
          sizes="(min-width: 1024px) 360px, (min-width: 640px) 45vw, 50vw"
          priority={priority}
        />
        {example ? (
          <span className="absolute start-2.5 bottom-2.5 rounded-full bg-night-950/75 px-2.5 py-1 text-[11px] font-semibold text-paper">
            {t("realPages")}
          </span>
        ) : null}
      </div>
      <div className="flex grow flex-col gap-1.5 p-3 md:p-4">
        <span className="text-caption font-semibold text-ink-muted">
          {tc("ages", { min: theme.age_min, max: theme.age_max })} · {tc("pages", { count: theme.pages })}
        </span>
        <h3 className="text-[18px] leading-tight text-night-900 md:text-[21px]">{theme.name}</h3>
        {classic && (
          <span
            title={classic.length ? t("classicIn", { styles: classic.join(locale === "ar" ? "، " : ", ") }) : undefined}
            className={`self-start rounded-full px-2.5 py-0.5 text-[12px] font-bold ${classic.length ? "bg-night-100 text-night-900" : "bg-night-900 text-amber-300"}`}
          >
            {classic.length ? t("bothLines") : t("magicOnly")}
          </span>
        )}
        <p className="line-clamp-2 text-caption leading-[1.5] text-ink-muted md:text-small">{theme.tagline}</p>
        {styles.length > 1 && (
          <span className="flex items-center gap-2 pt-0.5" title={styles.map((s) => s.name).join(" · ")}>
            <span className="flex -space-x-2 rtl:space-x-reverse" aria-hidden="true">
              {styles.map((s) => {
                const thumb = styleThumb(s.slug, theme.slug);
                return thumb ? (
                  // eslint-disable-next-line @next/next/no-img-element -- a 480 px static sample as a swatch
                  <img
                    key={s.slug}
                    src={thumb.thumb}
                    alt=""
                    width={24}
                    height={24}
                    loading="lazy"
                    className="size-6 rounded-full border-2 border-paper-raised bg-paper object-cover"
                  />
                ) : null;
              })}
            </span>
            <span className="text-caption font-semibold text-ink-muted">
              {ts("styleCount", { count: styles.length })}
            </span>
          </span>
        )}
        <div className="mt-auto flex flex-wrap items-baseline justify-between gap-x-2 pt-1">
          {from !== null && (
            <strong className="font-display text-[18px] text-night-900">
              {t("from", { price: money(from, currency, locale) })}
            </strong>
          )}
          <span className="text-small font-bold text-amber-700">
            {t("choose")} <Arrow />
          </span>
        </div>
      </div>
    </>
  );
  const shell = "flex h-full flex-col overflow-hidden rounded-[20px] border border-line bg-paper-raised text-ink";
  return (
    <Link
      href={`/stories/${theme.slug}${line ? `?line=${line}` : ""}`}
      className={`${shell} transition hover:-translate-y-0.5 hover:shadow-2`}
    >
      {body}
    </Link>
  );
}
