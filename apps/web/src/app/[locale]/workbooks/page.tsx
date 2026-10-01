import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { ActivityBookCard } from "@/components/site/ActivityBookCard";
import { JsonLd } from "@/components/site/JsonLd";
import { Alert } from "@/components/ui/Alert";
import { PageShell } from "@/components/site/PageShell";
import { Photo } from "@/components/site/Photo";
import { CtaBand, SECTION, SectionHead, Steps, type Step } from "@/components/site/blocks";
import { Link } from "@/i18n/navigation";
import { getStoreCatalog } from "@/lib/catalog";
import { workbooksListJsonLd } from "@/lib/pageSeo";
import { pageMetadata } from "@/lib/seo";
import { ACTIVITY_LINES } from "@/lib/shop";
import { PREVIEWS } from "@/lib/workbook";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("workbooksHub"), getLocale()]);
  const cover = PREVIEWS["foundation-workbook"]?.[0];
  return pageMetadata({
    path: "/workbooks",
    locale,
    title: t("title"),
    description: t("lead"),
    image: cover && { url: cover.src, alt: t("title") },
  });
}

const ORDER = ["workbook", "journey", "family"];

/** The activity books hub: the three books side by side, how one is made, and the kindergarten offer. */
export default async function WorkbooksPage() {
  const [t, tn, te, catalog, locale] = await Promise.all([
    getTranslations("workbooksHub"),
    getTranslations("nav"),
    getTranslations("errors"),
    getStoreCatalog(),
    getLocale(),
  ]);
  const books = (catalog?.products ?? [])
    .filter((p) => (ACTIVITY_LINES as readonly string[]).includes(p.line))
    .sort((a, b) => ORDER.indexOf(a.line) - ORDER.indexOf(b.line));
  const currency = catalog?.currency ?? "ILS";
  const how = t.raw("how") as Step[];
  return (
    <PageShell>
      <JsonLd data={workbooksListJsonLd(books, locale)} />
      <div className={`${SECTION} flex flex-col gap-8 pt-8 pb-16 md:gap-12 md:pt-14 md:pb-24`}>
        <header className="grid items-center gap-6 lg:grid-cols-[1fr_auto]">
          <div className="flex flex-col gap-3">
            <h1 className="text-[32px] leading-tight text-night-900 md:text-[52px]">{t("title")}</h1>
            <p className="max-w-[680px] text-body text-ink-muted md:text-body-l">{t("lead")}</p>
          </div>
          <Photo
            name="books-stack"
            alt={t("photoAlt")}
            sizes="(min-width: 1024px) 280px, 100vw"
            className="hidden w-[280px] rounded-[24px] lg:block"
          />
        </header>

        {catalog === null && <Alert>{te("unknown")}</Alert>}
        <div className="grid gap-4 md:grid-cols-3 md:gap-6">
          {books.map((p) => (
            <ActivityBookCard key={p.slug} product={p} currency={currency} detailed />
          ))}
        </div>

        <section className="flex flex-col gap-6">
          <SectionHead title={t("howTitle")} />
          <Steps steps={how} />
        </section>

        <div className="grid gap-4 md:grid-cols-2 md:gap-6">
          <Link href="/kindergartens" className="flex flex-col gap-2 rounded-[24px] bg-night-950 p-6 text-paper md:p-8">
            <h2 className="text-[22px] leading-snug md:text-[26px]">{t("kgTitle")}</h2>
            <p className="text-small text-night-100 md:text-body">{t("kgBody")}</p>
            <span className="mt-2 flex min-h-11 items-center self-start rounded-full bg-amber-500 px-[18px] text-[15px] font-bold text-night-950">
              {t("kgCta")}
            </span>
          </Link>
          <Link
            href="/stories"
            className="flex flex-col gap-2 rounded-[24px] border border-line bg-paper-raised p-6 md:p-8"
          >
            <h2 className="text-[22px] leading-snug text-night-900 md:text-[26px]">{t("storiesTitle")}</h2>
            <p className="text-small text-ink-muted md:text-body">{t("storiesBody")}</p>
            <span className="mt-2 flex min-h-11 items-center self-start rounded-full border-2 border-night-900 px-[18px] text-[15px] font-bold text-night-900">
              {t("storiesCta")}
            </span>
          </Link>
        </div>
      </div>
      <CtaBand
        title={t("ctaTitle")}
        body={t("ctaBody")}
        primary={{ href: "/quiz", label: t("ctaQuiz") }}
        secondary={{ href: "/pricing", label: tn("pricing") }}
      />
      <div className="h-12 md:h-20" />
    </PageShell>
  );
}
