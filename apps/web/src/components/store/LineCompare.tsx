import { getLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { money, type Catalog } from "@/lib/store";

/** Classic and Magic side by side on a story page (Addendum 4 §7): what each is, and where each starts. */
export async function LineCompare({ catalog, theme }: { catalog: Catalog | null; theme: string }) {
  const [t, tf, locale] = await Promise.all([
    getTranslations("store.compare"),
    getTranslations("store.formats"),
    getLocale(),
  ]);
  const product = (slug: string) => catalog?.products.find((p) => p.slug === slug);
  const cards = [
    { line: "classic" as const, product: product("classic-book"), best: false },
    { line: "magic" as const, product: product("magic-book"), best: true },
  ];
  return (
    <section className="flex flex-col gap-3" aria-labelledby="compare-title">
      <h2 id="compare-title" className="text-[20px] text-night-900">
        {t("title")}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {cards.map(({ line, product: p, best }) => (
          <Link
            key={line}
            href={`/create?theme=${theme}&line=${line}`}
            className={`relative flex flex-col gap-3 rounded-lg p-4 transition hover:shadow-2 ${best ? "bg-night-900 text-paper" : "border border-line bg-paper-raised text-ink"}`}
          >
            {best && (
              <span className="absolute end-4 -top-2.5 rounded-full bg-amber-500 px-2.5 py-0.5 text-caption font-bold text-night-950">
                {t("best")}
              </span>
            )}
            <div className="flex items-baseline justify-between gap-2">
              <strong className={`font-display text-[20px] ${best ? "text-amber-300" : "text-night-900"}`}>
                {locale === "ar" ? p?.name_ar : p?.name_en}
              </strong>
              {p?.from_price && (
                <span className="text-small whitespace-nowrap">
                  {t("from")} <strong>{money(p.from_price, "ILS", locale)}</strong>
                </span>
              )}
            </div>
            <p className={`text-small ${best ? "text-night-100" : "text-ink-muted"}`}>{t(`${line}.tagline`)}</p>
            <ul className="flex flex-col gap-1.5 text-small">
              {(t.raw(`${line}.points`) as string[]).map((point) => (
                <li key={point} className="flex items-start gap-2">
                  <span aria-hidden="true" className={best ? "text-amber-300" : "text-success"}>
                    ✓
                  </span>
                  {point}
                </li>
              ))}
            </ul>
            <div className="mt-auto flex flex-wrap gap-1.5 text-caption">
              {p?.variants.map((v) => (
                <span
                  key={v.sku}
                  className={`rounded-full px-2.5 py-1 ${best ? "bg-night-800 text-night-100" : "bg-paper-sunk"}`}
                >
                  {tf(v.options.format)} · {v.price ? money(v.price, "ILS", locale) : "—"}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
      <p className="text-small text-ink-muted">{t("note")}</p>
    </section>
  );
}
