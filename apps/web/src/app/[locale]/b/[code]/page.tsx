import type { Metadata } from "next";
import { headers } from "next/headers";
import { getLocale, getTranslations } from "next-intl/server";
import { HelloPage } from "@/components/site/HelloPage";
import { brandName } from "@/config/brand";
import { getBookByCode } from "@/lib/catalog";

type Props = { params: Promise<{ code: string }> };

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("hello"), getLocale()]);
  const brand = brandName(locale);
  // a book's code is private: never indexed, and never sent on to the pages its links open
  return {
    title: t("title", { brand }),
    description: t("metaDescription", { brand }),
    robots: { index: false, follow: false },
    referrer: "no-referrer",
  };
}

/**
 * The QR printed in every book: `https://qamra.app/b/QB-7K4M2` (the proxy adds the language). A well-formed code is
 * looked up (lib/bookCode.ts); a malformed or unknown one shows the plain /hello page, saying nothing about books.
 */
export default async function BookCodePage({ params }: Props) {
  const [{ code }, head] = await Promise.all([params, headers()]);
  const visitor = head.get("x-forwarded-for")?.split(",")[0]?.trim() || head.get("x-real-ip");
  return <HelloPage book={await getBookByCode(code, visitor)} />;
}
