import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { QuizFlow } from "@/components/shop/QuizFlow";
import { getShopSummary } from "@/lib/catalog";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("quiz"), getLocale()]);
  return pageMetadata({ path: "/quiz", locale, title: t("title"), description: t("metaDescription") });
}

/** Addendum 9 Quiz: «أي كتاب يناسب طفلي؟». */
export default async function QuizPage() {
  const summary = await getShopSummary();
  // «قلبي يعرف الله» is in the summary only while a volume the scholar approved is on sale (Addendum 10 §9)
  return <QuizFlow faith={summary?.orderable?.["islamic-series"] === true} />;
}
