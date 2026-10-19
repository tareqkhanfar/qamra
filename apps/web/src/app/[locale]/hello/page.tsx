import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { HelloPage } from "@/components/site/HelloPage";
import { brandName } from "@/config/brand";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("hello"), getLocale()]);
  const brand = brandName(locale);
  return pageMetadata({
    path: "/hello",
    locale,
    title: t("title", { brand }),
    description: t("metaDescription", { brand }),
    bare: true,
  });
}

/** Who we are and every way to reach us: the QR page (`/b/{code}`) without a book. */
export default function HelloRoute() {
  return <HelloPage book={null} />;
}
