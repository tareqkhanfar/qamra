import { useLocale, useTranslations } from "next-intl";
import { Scene } from "@/components/art/Scene";
import { ExampleImage } from "@/components/book/ExampleImage";
import { Link } from "@/i18n/navigation";
import { storyPages, type Example } from "@/lib/examples";
import { money, type Catalog } from "@/lib/store";
import { LINES, offer } from "@/lib/story";

/**
 * Design Shop: the two story lines side by side (Classic, Magic «مع صاحبه») with a real page each when an
 * example is published, and the price they start from.
 */
export function StoryLines({ catalog, examples }: { catalog: Catalog | null; examples: Example[] }) {
  const t = useTranslations("shop");
  const locale = useLocale();
  const currency = catalog?.currency ?? "ILS";
  const price = (n: number | null) => (n === null ? "—" : money(n, currency, locale));
  const name = (p: { name_ar: string; name_en: string }) => (locale === "ar" ? p.name_ar : p.name_en);
  const pages = storyPages(examples[0] ?? null, 6);
  const classic = offer(catalog, "classic");
  const magic = offer(catalog, "magic");
  return (
    <div className="grid grid-cols-2 gap-3 md:gap-5">
      {LINES.map((line) => {
        const o = line === "classic" ? classic : magic;
        if (!o) return null;
        const dark = line === "magic";
        const page = pages[line === "classic" ? 0 : 3] ?? pages[1];
        return (
          <Link
            key={line}
            href={`/stories?line=${line}`}
            className={`flex flex-col overflow-hidden rounded-[20px] ${dark ? "bg-night-900 text-paper" : "border border-line bg-paper-raised text-ink"}`}
          >
            <div className="relative aspect-[173/140]">
              {page ? (
                <ExampleImage
                  page={page}
                  alt=""
                  sizes="(min-width: 768px) 520px, 50vw"
                  className="absolute inset-0 size-full object-cover"
                />
              ) : dark ? (
                <Scene
                  theme="space"
                  ratio={173 / 140}
                  outfit="#A99BD6"
                  pose="wave"
                  kidScale={0.62}
                  companion="blob"
                  className="absolute inset-0"
                />
              ) : (
                <Scene
                  theme="garden"
                  ratio={173 / 140}
                  outfit="#5B6FC0"
                  skin="#C98F63"
                  hairStyle="curly"
                  kidScale={0.72}
                  className="absolute inset-0"
                />
              )}
              {dark && (
                <span className="absolute start-2.5 top-2.5 rounded-full bg-amber-500 px-2 py-0.5 text-[11px] font-bold text-night-950">
                  {t("stories.withCompanion")}
                </span>
              )}
            </div>
            <div className="flex grow flex-col gap-1 p-3 md:p-4">
              <h3 className={`text-[18px] md:text-[22px] ${dark ? "text-paper" : "text-night-900"}`}>
                {name(o.product)}
              </h3>
              <span
                className={`text-caption leading-[1.5] md:text-small ${dark ? "text-night-100" : "text-ink-muted"}`}
              >
                {t(`stories.${line}`)}
              </span>
              <span className={`mt-auto pt-1 text-caption ${dark ? "text-ink-dark-muted" : "text-ink-muted"}`}>
                {o.formats.length > 1 ? t("from") : t("stories.hardcover")}
              </span>
              <strong className={`font-display text-[20px] ${dark ? "text-amber-300" : "text-night-900"}`}>
                {price(o.from)}
              </strong>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
