import { getLocale, getTranslations } from "next-intl/server";
import { MoonPhase } from "@/components/art/MoonPhase";
import { PageShell } from "@/components/site/PageShell";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { getTheme } from "@/lib/catalog";

type Props = { searchParams: Promise<{ theme?: string }> };

/** Placeholder until the 12-step create flow lands (Phase 2). */
export default async function CreatePage({ searchParams }: Props) {
  const [{ theme: slug }, locale, t] = await Promise.all([searchParams, getLocale(), getTranslations("create")]);
  const theme = slug ? await getTheme(slug, locale) : null;
  return (
    <PageShell>
      <section className="mx-auto flex max-w-xl flex-col items-center gap-5 px-4 py-16 text-center md:py-24">
        <MoonPhase p={5 / 12} className="size-24" />
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <p className="text-body-l text-ink-muted">{t("body")}</p>
        {theme && (
          <p className="rounded-full bg-amber-100 px-4 py-2 font-semibold text-amber-700">
            {t("chosen", { name: theme.name })}
          </p>
        )}
        <Link href="/themes" className={buttonClasses("solid", "md")}>
          {t("browse")}
        </Link>
      </section>
    </PageShell>
  );
}
