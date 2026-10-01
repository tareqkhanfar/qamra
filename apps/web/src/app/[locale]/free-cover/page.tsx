import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { FreeCoverForm } from "@/components/freecover/FreeCoverForm";
import { FreeCoverShell } from "@/components/freecover/FreeCoverShell";
import { redirect } from "@/i18n/navigation";
import { getPublicSettings } from "@/lib/catalog";

type Props = { searchParams: Promise<{ theme?: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("freeCover"))("formTitle"), robots: { index: false } };
}

/**
 * «شوف غلاف طفلك خلال دقيقة» (Addendum 9): open only while the admin's `free_cover` switch is on; a link to it
 * while it's off goes to the stories (the page never says something is unavailable).
 */
export default async function FreeCoverPage({ searchParams }: Props) {
  const [query, site, locale] = await Promise.all([searchParams, getPublicSettings(), getLocale()]);
  if (!site?.free_cover) redirect({ href: "/stories", locale });
  return (
    <FreeCoverShell>
      <Suspense>
        <FreeCoverForm initialTheme={query.theme ?? null} />
      </Suspense>
    </FreeCoverShell>
  );
}
