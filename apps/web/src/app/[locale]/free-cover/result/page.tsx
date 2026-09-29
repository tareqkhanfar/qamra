import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { FreeCoverResult } from "@/components/freecover/FreeCoverResult";
import { FreeCoverShell } from "@/components/freecover/FreeCoverShell";
import { brandName } from "@/config/brand";

type Props = { searchParams: Promise<{ id?: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("freeCover"))("title"), robots: { index: false } };
}

/** Design FreeCover (Addendum 9): the drawn cover, sharing it, and the way on to the whole book. */
export default async function FreeCoverResultPage({ searchParams }: Props) {
  const [query, locale] = await Promise.all([searchParams, getLocale()]);
  return (
    <FreeCoverShell>
      <div className="px-4 pt-5 pb-36">
        {query.id ? <FreeCoverResult id={query.id} brand={brandName(locale)} /> : null}
      </div>
    </FreeCoverShell>
  );
}
