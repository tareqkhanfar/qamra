import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getLocale } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { WorkbookProduct } from "@/components/workbook/WorkbookProduct";
import { getPublicSettings, getShopSummary, getStoreCatalog } from "@/lib/catalog";
import { ACTIVITY_LINES } from "@/lib/shop";
import { PREVIEWS } from "@/lib/workbook";

type Props = { params: Promise<{ product: string }>; searchParams: Promise<Record<string, string | string[]>> };

async function load(slug: string) {
  const catalog = await getStoreCatalog();
  const product = catalog?.products.find(
    (p) => p.slug === slug && (ACTIVITY_LINES as readonly string[]).includes(p.line),
  );
  return { catalog, product };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const [{ product: slug }, locale] = await Promise.all([params, getLocale()]);
  const { product } = await load(slug);
  if (!product) return {};
  return {
    title: locale === "ar" ? product.name_ar : product.name_en,
    description: locale === "ar" ? product.description_ar : product.description_en,
  };
}

/** Addendum 9 WorkbookProduct at /workbooks/[product] (دوسية التأسيس، رحلتي الأولى، مغامراتي مع عائلتي). */
export default async function WorkbookPage({ params, searchParams }: Props) {
  const [{ product: slug }, query] = await Promise.all([params, searchParams]);
  const [{ catalog, product }, summary, site] = await Promise.all([load(slug), getShopSummary(), getPublicSettings()]);
  if (!product) notFound();
  const picks = Object.fromEntries(
    Object.entries(query).filter((e): e is [string, string] => typeof e[1] === "string"),
  );
  return (
    <PageShell>
      <WorkbookProduct
        product={product}
        currency={catalog?.currency ?? "ILS"}
        orderable={summary?.orderable?.[product.slug] ?? !["workbook", "journey"].includes(product.line)}
        previews={PREVIEWS[product.slug] ?? []}
        query={picks}
        whatsapp={site?.support_whatsapp || null}
      />
    </PageShell>
  );
}
