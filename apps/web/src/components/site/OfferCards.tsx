/* eslint-disable @next/next/no-img-element -- static preview pages from /public (exported once by a script) */
import { getLocale, getTranslations } from "next-intl/server";
import { Scene } from "@/components/art/Scene";
import { ExampleImage } from "@/components/book/ExampleImage";
import { Link } from "@/i18n/navigation";
import type { ShopSummary } from "@/lib/catalog";
import { storyPages, type Example } from "@/lib/examples";
import { ACTIVITY_LINES, productFrom } from "@/lib/shop";
import { money, type Catalog } from "@/lib/store";
import { offer } from "@/lib/story";
import { PREVIEWS } from "@/lib/workbook";
import { Photo } from "./Photo";
import { Arrow } from "./blocks";

type Offer = {
  key: "classic" | "magic" | "workbooks" | "kg";
  href: string;
  price: string | null;
  visual: React.ReactNode;
};

/**
 * The four things Qamra sells, as cards a parent reads in seconds: a real cover or page, the name, one line, the
 * price it starts from, and where to go. Prices come from the catalog; nothing is hard-coded.
 */
export async function OfferCards({
  catalog,
  examples,
  summary,
}: {
  catalog: Catalog | null;
  examples: Example[];
  summary: ShopSummary | null;
}) {
  const [t, locale] = await Promise.all([getTranslations("landing"), getLocale()]);
  const currency = catalog?.currency ?? "ILS";
  const price = (n: number | string | null | undefined) => (n == null ? null : money(n, currency, locale));
  const classic = offer(catalog, "classic");
  const magic = offer(catalog, "magic");
  const activity = (catalog?.products ?? []).filter((p) => (ACTIVITY_LINES as readonly string[]).includes(p.line));
  const activityFrom = activity.map(productFrom).filter((n): n is number => n !== null);
  const pages = storyPages(examples[0] ?? null, 6);
  const cover = examples[0]?.pages.find((p) => p.beat === 0);
  const pageOf = (i: number) => pages[i] ?? cover ?? null;
  const covers = activity.map((p) => PREVIEWS[p.slug]?.[0]).filter((c): c is NonNullable<typeof c> => !!c);
  const page = (i: number, theme: "garden" | "space") => {
    const p = pageOf(i);
    return p ? (
      <ExampleImage
        page={p}
        alt=""
        sizes="(min-width: 1024px) 320px, 50vw"
        className="absolute inset-0 size-full object-cover"
      />
    ) : (
      <Scene
        theme={theme}
        ratio={3 / 2}
        pose="wave"
        kidScale={0.6}
        companion={theme === "space" ? "blob" : ""}
        className="absolute inset-0"
      />
    );
  };
  const offers: Offer[] = [
    { key: "classic", href: "/stories?line=classic", price: price(classic?.from), visual: page(0, "garden") },
    { key: "magic", href: "/stories?line=magic", price: price(magic?.from), visual: page(3, "space") },
    {
      key: "workbooks",
      href: "/workbooks",
      price: activityFrom.length ? price(Math.min(...activityFrom)) : null,
      visual: (
        <Photo
          name="books-stack"
          alt={t("offers.workbooks.title")}
          sizes="(min-width: 1024px) 320px, 50vw"
          className="absolute inset-0"
          fallback={
            <div className="absolute inset-0 flex items-end justify-center gap-2 bg-paper-sunk px-4 pt-4">
              {covers.map((c, i) => (
                <img
                  key={c.src}
                  src={c.src}
                  alt=""
                  width={720}
                  height={1018}
                  loading="lazy"
                  className={`w-[30%] rounded-t-[6px] object-cover object-top shadow-[0_-6px_18px_rgba(22,32,74,0.18)] ${i === 1 ? "-translate-y-2" : ""}`}
                />
              ))}
            </div>
          }
        />
      ),
    },
    {
      key: "kg",
      href: "/kindergartens",
      price: null,
      visual: (
        <Photo
          name="graduation-class"
          alt={t("offers.kg.title")}
          sizes="(min-width: 1024px) 320px, 50vw"
          className="absolute inset-0"
          fallback={
            <Scene theme="grad" ratio={3 / 2} cap hijab outfit="#A99BD6" kidScale={0.62} className="absolute inset-0" />
          }
        />
      ),
    },
  ];
  const kgPrice = summary?.class_book_from ? price(summary.class_book_from) : null;
  return (
    <div className="grid grid-cols-2 gap-3 md:gap-5 lg:grid-cols-4">
      {offers.map((o, i) => (
        <Link
          key={o.key}
          href={o.href}
          data-reveal
          style={{ "--d": `${i * 90}ms` } as React.CSSProperties}
          className="flex flex-col overflow-hidden rounded-[20px] border border-line bg-paper-raised text-ink transition hover:-translate-y-0.5 hover:shadow-2"
        >
          <div className="relative aspect-[3/2] overflow-hidden bg-paper-sunk">{o.visual}</div>
          <div className="flex grow flex-col gap-1 p-3 md:p-4">
            {o.key !== "workbooks" && o.key !== "kg" && (
              <span className="text-caption font-semibold text-ink-muted">{t("story")}</span>
            )}
            <h3 className="text-[18px] leading-tight text-night-900 md:text-[22px]">{t(`offers.${o.key}.title`)}</h3>
            <p className="text-caption leading-[1.5] text-ink-muted md:text-small">{t(`offers.${o.key}.body`)}</p>
            <div className="mt-auto flex flex-col gap-1 pt-2">
              <strong className="font-display text-[18px] text-night-900">
                {o.key === "kg"
                  ? kgPrice && t("perChild", { price: kgPrice })
                  : o.price && t("from", { price: o.price })}
              </strong>
              <span className="text-small font-bold text-amber-700">
                {t(`offers.${o.key}.cta`)} <Arrow />
              </span>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
