import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { QuizFlow } from "@/components/shop/QuizFlow";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("quiz"), getLocale()]);
  return pageMetadata({ path: "/quiz", locale, title: t("title"), description: t("metaDescription") });
}

/** Addendum 9 Quiz: «أي كتاب يناسب طفلي؟». */
export default function QuizPage() {
  return <QuizFlow />;
}
