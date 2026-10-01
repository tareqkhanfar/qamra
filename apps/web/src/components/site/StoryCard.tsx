import { useLocale, useTranslations } from "next-intl";
import { CoverArt } from "@/components/book/CoverArt";
import { Link } from "@/i18n/navigation";
import { Arrow } from "./blocks";
import type { ThemeCard } from "@/lib/catalog";
import type { Example } from "@/lib/examples";
import { money, type Currency } from "@/lib/store";

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
}: {
  theme: ThemeCard;
  example: Example | null;
  from: number | null;
  currency?: Currency;
  line?: string | null;
  priority?: boolean;
}) {
  const t = useTranslations("themes");
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
        <p className="line-clamp-2 text-caption leading-[1.5] text-ink-muted md:text-small">{theme.tagline}</p>
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
