import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { FreeCoverForm } from "@/components/freecover/FreeCoverForm";
import { FreeCoverShell } from "@/components/freecover/FreeCoverShell";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { getPublicSettings } from "@/lib/catalog";

type Props = { searchParams: Promise<{ theme?: string }> };

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("freeCover"))("formTitle"), robots: { index: false } };
}

/** «شوف غلاف طفلك خلال دقيقة» (Addendum 9): shown only while the admin's `free_cover` switch is on. */
export default async function FreeCoverPage({ searchParams }: Props) {
  const [query, site, t] = await Promise.all([searchParams, getPublicSettings(), getTranslations("freeCover")]);
  return (
    <FreeCoverShell>
      {site?.free_cover ? (
        <Suspense>
          <FreeCoverForm initialTheme={query.theme ?? null} />
        </Suspense>
      ) : (
        <div className="flex flex-col items-start gap-4 px-4 py-12">
          <p className="text-body text-ink-muted">{t("off")}</p>
          <Link href="/stories" className={buttonClasses("secondary", "md")}>
            {t("browse")}
          </Link>
        </div>
      )}
    </FreeCoverShell>
  );
}
