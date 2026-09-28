import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { Alert } from "@/components/ui/Alert";
import { PageShell } from "@/components/site/PageShell";
import { ThemesGrid } from "@/components/site/ThemesGrid";
import { getPricing, getThemes, lowestPrice } from "@/lib/catalog";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("themes");
  return { title: t("title"), description: t("lead") };
}

export default async function ThemesPage() {
  const locale = await getLocale();
  const [t, tc, themes, prices] = await Promise.all([
    getTranslations("themes"),
    getTranslations("common"),
    getThemes(locale),
    getPricing(),
  ]);
  const occasionLabels = tc.raw("occasions") as Record<string, string>;
  return (
    <PageShell>
      <div className="mx-auto max-w-[1440px] px-4 pb-16 md:px-10 md:pb-24 xl:px-24">
        <header className="flex flex-col gap-3 pt-10 pb-8 md:pt-14">
          <h1 className="text-[36px] text-night-900 md:text-[52px]">{t("title")}</h1>
          <p className="max-w-[640px] text-body-l text-ink-muted">{t("lead")}</p>
        </header>
        {themes ? (
          <ThemesGrid
            themes={themes}
            price={lowestPrice(prices)}
            occasionLabels={occasionLabels}
            labels={{
              age: t("age"),
              all: t("all"),
              occasion: t("occasion"),
              sort: t("sort"),
              sortPopular: t("sortPopular"),
              sortAge: t("sortAge"),
              empty: t("empty"),
              reset: t("reset"),
            }}
          />
        ) : (
          <Alert>{t("unavailable")}</Alert>
        )}
      </div>
    </PageShell>
  );
}
