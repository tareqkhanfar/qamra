import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getLocale, getTranslations } from "next-intl/server";
import { JsonLd } from "@/components/site/JsonLd";
import { PageShell } from "@/components/site/PageShell";
import { Photo, type PhotoName } from "@/components/site/Photo";
import { WorkbookProduct } from "@/components/workbook/WorkbookProduct";
import { getPublicSettings, getStoreCatalog } from "@/lib/catalog";
import { workbookJsonLd } from "@/lib/pageSeo";
import { pageMetadata } from "@/lib/seo";
import { ACTIVITY_LINES } from "@/lib/shop";
import { PREVIEWS } from "@/lib/workbook";

type Props = { params: Promise<{ product: string }>; searchParams: Promise<Record<string, string | string[]>> };

/** The lifestyle photo of each line (public/photos/README.md); shown under "what's yours" when the file exists. */
const PHOTO: Record<string, PhotoName> = {
  workbook: "workbook-tracing",
  journey: "journey-qr",
  family: "family-book-table",
};

async function load(slug: string) {
  const catalog = await getStoreCatalog();
  const product = catalog?.products.find(
    (p) => p.slug === slug && (ACTIVITY_LINES as readonly string[]).includes(p.line),
  );
  return { catalog, product };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const [{ product: slug }, locale, tw] = await Promise.all([params, getLocale(), getTranslations("workbook")]);
  const { product } = await load(slug);
  if (!product) return {};
  const name = locale === "ar" ? product.name_ar : product.name_en;
  const cover = PREVIEWS[slug]?.[0];
  return pageMetadata({
    path: `/workbooks/${slug}`,
    locale,
    title: name,
    description: tw.has(`desc.${product.line}`)
      ? tw(`desc.${product.line}`)
      : locale === "ar"
        ? product.description_ar
        : product.description_en,
    image: cover && { url: cover.src, alt: name },
  });
}

/** Addendum 9 WorkbookProduct at /workbooks/[product] (دوسية التأسيس، رحلتي الأولى، مغامراتي مع عائلتي). */
export default async function WorkbookPage({ params, searchParams }: Props) {
  const [{ product: slug }, query, locale] = await Promise.all([params, searchParams, getLocale()]);
  const [{ catalog, product }, site, t] = await Promise.all([
    load(slug),
    getPublicSettings(),
    getTranslations("workbook"),
  ]);
  if (!product) notFound();
  const picks = Object.fromEntries(
    Object.entries(query).filter((e): e is [string, string] => typeof e[1] === "string"),
  );
  const photo = PHOTO[product.line];
  return (
    <PageShell>
      <JsonLd
        data={workbookJsonLd(
          product,
          locale,
          catalog?.currency ?? "ILS",
          t.has(`desc.${product.line}`) ? t(`desc.${product.line}`) : undefined,
        )}
      />
      <WorkbookProduct
        product={product}
        currency={catalog?.currency ?? "ILS"}
        query={picks}
        photo={
          photo ? (
            <Photo
              name={photo}
              alt={t(`photoAlt.${product.line}`)}
              sizes="(min-width: 768px) 560px, 100vw"
              className="rounded-[20px]"
            />
          ) : null
        }
        familyCharacters={site?.family_characters_enabled ?? false}
        addons={catalog?.addons ?? []}
      />
    </PageShell>
  );
}
