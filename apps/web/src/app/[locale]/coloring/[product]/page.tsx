import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { getLocale, getTranslations } from "next-intl/server";
import { ColoringProduct } from "@/components/coloring/ColoringProduct";
import { JsonLd } from "@/components/site/JsonLd";
import { PageShell } from "@/components/site/PageShell";
import { getStoreCatalog } from "@/lib/catalog";
import { coloringBooks, coloringFacts, coloringPreviews } from "@/lib/coloring";
import { coloringJsonLd } from "@/lib/pageSeo";
import { pageMetadata } from "@/lib/seo";
import { productPath } from "@/lib/shop";

type Props = { params: Promise<{ product: string }>; searchParams: Promise<Record<string, string | string[]>> };

/** Only the books of «دفاتر التلوين والرسم»: any other slug (an activity book, a story) is not found here. */
async function load(slug: string) {
  const catalog = await getStoreCatalog();
  const books = coloringBooks(catalog?.products ?? []);
  return { catalog, books, product: books.find((p) => p.slug === slug) };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const [{ product: slug }, locale, t] = await Promise.all([params, getLocale(), getTranslations("coloring")]);
  const { product } = await load(slug);
  if (!product) return {};
  const name = locale === "ar" ? product.name_ar : product.name_en;
  const { title } = coloringFacts(product);
  const cover = coloringPreviews(slug).cover;
  return pageMetadata({
    path: `/coloring/${slug}`,
    locale,
    title: name,
    description: t.has(`desc.${title}`)
      ? t(`desc.${title}`)
      : locale === "ar"
        ? product.description_ar
        : product.description_en,
    image: cover ? { url: cover.src, alt: name } : undefined,
  });
}

/** One coloring or drawing book at /coloring/[product] («ألوّن حروفي»، «ألوّن فلسطين»، «ألوّن رمضان»، «دفتري»). */
export default async function ColoringBookPage({ params, searchParams }: Props) {
  const [{ product: slug }, query, locale] = await Promise.all([params, searchParams, getLocale()]);
  const [{ catalog, books, product }, t, jar] = await Promise.all([load(slug), getTranslations("coloring"), cookies()]);
  if (!product) notFound();
  const picks = Object.fromEntries(
    Object.entries(query).filter((e): e is [string, string] => typeof e[1] === "string"),
  );
  const signedIn = jar.has("qamra_at") || jar.has("qamra_rt"); // the session cookies (httpOnly), as SiteNav reads them
  const { title } = coloringFacts(product);
  const others = books
    .filter((p) => p.slug !== slug)
    .map((p) => ({ slug: p.slug, href: productPath(p), name: locale === "ar" ? p.name_ar : p.name_en }));
  return (
    <PageShell>
      <JsonLd
        data={coloringJsonLd(
          product,
          locale,
          catalog?.currency ?? "ILS",
          t.has(`desc.${title}`) ? t(`desc.${title}`) : undefined,
        )}
      />
      <ColoringProduct
        product={product}
        currency={catalog?.currency}
        query={picks}
        signedIn={signedIn}
        others={others}
      />
    </PageShell>
  );
}
