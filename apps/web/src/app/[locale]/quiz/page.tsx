import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { QuizFlow } from "@/components/shop/QuizFlow";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("quiz");
  return { title: t("title"), description: t("metaDescription") };
}

/** Addendum 9 Quiz: «أي كتاب يناسب طفلي؟». */
export default function QuizPage() {
  return <QuizFlow />;
}
