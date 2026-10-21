import { getLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { coloringFacts, coloringPreviews } from "@/lib/coloring";
import { productPath } from "@/lib/shop";
import type { CatalogProduct } from "@/lib/store";
import { ColoringCover } from "./ColoringCover";

/** A small card for the home's coloring row (two to a row on phones): the cover, the name, pages and binding. */
export async function ColoringMiniCard({ product }: { product: CatalogProduct }) {
  const [t, locale] = await Promise.all([getTranslations("coloring"), getLocale()]);
  const facts = coloringFacts(product);
  const name = locale === "ar" ? product.name_ar : product.name_en;
  const pagesLabel = t("pagesCount", { pages: facts.pages });
  return (
    <Link
      href={productPath(product)}
      className="flex flex-col gap-3 rounded-[20px] border border-line bg-paper-raised p-3 transition hover:-translate-y-0.5 hover:shadow-2 md:p-4"
    >
      <ColoringCover
        cover={coloringPreviews(product.slug).cover}
        title={facts.title}
        name={name}
        pagesLabel={pagesLabel}
        binding={facts.binding}
        alt=""
        sizes="(min-width: 1024px) 260px, 45vw"
      />
      <span className="flex flex-col gap-0.5">
        <strong className="font-display text-[17px] leading-tight text-night-900 md:text-[20px]">{name}</strong>
        <span className="text-caption text-ink-muted">
          {pagesLabel} · {t(`bindingShort.${facts.binding}`)}
        </span>
      </span>
    </Link>
  );
}
