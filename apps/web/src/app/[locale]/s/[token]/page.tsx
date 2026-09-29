import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { SharedReader } from "@/components/reader/SharedReader";

type Props = { params: Promise<{ token: string }> };

/** Never indexed, and the link's token never leaks to other sites through the Referer header. */
export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("reader");
  return {
    title: t("shared.metaTitle"),
    robots: { index: false, follow: false, nocache: true, googleBot: { index: false, follow: false } },
    referrer: "no-referrer",
  };
}

/** A share link: the book only (no account, no personal data beyond the book itself). */
export default async function SharedBookPage({ params }: Props) {
  const { token } = await params;
  return <SharedReader token={decodeURIComponent(token)} />;
}
