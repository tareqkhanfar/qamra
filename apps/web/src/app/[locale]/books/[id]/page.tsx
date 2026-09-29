import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { OwnerReader } from "@/components/reader/OwnerReader";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("reader");
  return { title: t("metaTitle"), robots: { index: false, follow: false }, referrer: "no-referrer" };
}

/** «كتبي» → the web reader for the parent's own book (full screen, no site chrome). */
export default async function BookReaderPage({ params }: Props) {
  const { id } = await params;
  return <OwnerReader id={decodeURIComponent(id)} />;
}
