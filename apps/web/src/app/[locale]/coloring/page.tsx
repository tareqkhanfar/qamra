import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { ColoringBookCard } from "@/components/coloring/ColoringBookCard";
import { ColoringCover } from "@/components/coloring/ColoringCover";
import { JsonLd } from "@/components/site/JsonLd";
import { PageShell } from "@/components/site/PageShell";
import { CtaBand, Faq, SECTION, SectionHead, Steps, type QA, type Step } from "@/components/site/blocks";
import { Alert } from "@/components/ui/Alert";
import { getStoreCatalog } from "@/lib/catalog";
import { coloringBooks, coloringFacts, coloringPreviews } from "@/lib/coloring";
import { coloringListJsonLd, faqJsonLd } from "@/lib/pageSeo";
import { pageMetadata } from "@/lib/seo";
import { COLORING_SLUGS } from "@/lib/shop";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("coloring"), getLocale()]);
  const cover = COLORING_SLUGS.map((s) => coloringPreviews(s).cover).find((c) => c !== null);
  return pageMetadata({
    path: "/coloring",
    locale,
    title: t("title"),
    description: t("lead"),
    image: cover ? { url: cover.src, alt: t("title") } : undefined,
  });
}

/**
 * «دفاتر التلوين والرسم»: the four books side by side, who they are for, the name (and character) on the cover,
 * the paper and printing, how to order, and the questions parents ask.
 */
export default async function ColoringHubPage() {
  const [t, te, catalog, locale] = await Promise.all([
    getTranslations("coloring"),
    getTranslations("errors"),
    getStoreCatalog(),
    getLocale(),
  ]);
  const books = coloringBooks(catalog?.products ?? []);
  const currency = catalog?.currency ?? "ILS";
  const how = t.raw("how") as Step[];
  const faq = t.raw("faq") as QA[];
  const paper = t.raw("paper") as { title: string; body: string }[];
  const fan = books.slice(0, 3);
  return (
    <PageShell>
      <JsonLd data={coloringListJsonLd(books, locale)} />
      <JsonLd data={faqJsonLd(faq, locale)} />
      <div className={`${SECTION} flex flex-col gap-10 pt-8 pb-16 md:gap-14 md:pt-14 md:pb-24`}>
        <header className="grid items-center gap-6 lg:grid-cols-[1fr_auto]">
          <div className="flex flex-col gap-3">
            <h1 className="text-[32px] leading-tight text-night-900 md:text-[52px]">{t("title")}</h1>
            <p className="max-w-[680px] text-body text-ink-muted md:text-body-l">{t("lead")}</p>
            <div className="flex flex-wrap gap-2 text-caption font-semibold">
              <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">{t("ages")}</span>
              <span dir="ltr" className="rounded-full bg-paper-sunk px-2.5 py-1">
                A4
              </span>
              <span className="rounded-full bg-success-bg px-2.5 py-1 text-success">{t("paperChip")}</span>
            </div>
          </div>
          {fan.length > 0 && (
            <div aria-hidden="true" className="relative hidden h-[260px] w-[320px] lg:block">
              {fan.map((p, i) => {
                const facts = coloringFacts(p);
                const name = locale === "ar" ? p.name_ar : p.name_en;
                return (
                  <div
                    key={p.slug}
                    className="absolute top-2 w-[150px] shadow-[0_12px_28px_rgba(22,32,74,0.2)]"
                    style={{ insetInlineStart: `${i * 80}px`, rotate: `${(i - 1) * 6}deg`, zIndex: i === 1 ? 2 : 1 }}
                  >
                    <ColoringCover
                      cover={coloringPreviews(p.slug).cover}
                      title={facts.title}
                      name={name}
                      pagesLabel={t("pagesCount", { pages: facts.pages })}
                      binding={facts.binding}
                      alt=""
                      sizes="150px"
                    />
                  </div>
                );
              })}
            </div>
          )}
        </header>

        <section id="books" aria-labelledby="books-title" className="flex scroll-mt-24 flex-col gap-5">
          <SectionHead id="books-title" title={t("booksTitle")} lead={t("booksLead")} />
          {catalog === null && <Alert>{te("unknown")}</Alert>}
          <div className="grid gap-4 sm:grid-cols-2 md:gap-6 xl:grid-cols-4">
            {books.map((p) => (
              <ColoringBookCard key={p.slug} product={p} currency={currency} detailed />
            ))}
          </div>
        </section>

        <div className="grid gap-4 md:grid-cols-2 md:gap-6">
          <section className="flex flex-col gap-2 rounded-[24px] bg-amber-100 p-6 md:p-8">
            <h2 className="text-[22px] leading-snug text-night-900 md:text-[26px]">{t("personalTitle")}</h2>
            <p className="text-small leading-[1.75] text-ink md:text-body">{t("personalBody")}</p>
          </section>
          <section className="flex flex-col gap-2 rounded-[24px] bg-night-100 p-6 md:p-8">
            <h2 className="text-[22px] leading-snug text-night-900 md:text-[26px]">{t("forTitle")}</h2>
            <p className="text-small leading-[1.75] text-ink md:text-body">{t("forBody")}</p>
          </section>
        </div>
      </div>

      <section aria-labelledby="paper-title" className="bg-night-900 py-12 text-paper md:py-20">
        <div className={`${SECTION} flex flex-col gap-6 md:gap-8`}>
          <SectionHead id="paper-title" title={t("paperTitle")} dark />
          <ul className="grid gap-3 sm:grid-cols-2 md:gap-4 lg:grid-cols-4">
            {paper.map((p) => (
              <li key={p.title} className="flex flex-col gap-1.5 rounded-[18px] bg-night-800 p-5">
                <strong className="text-[17px] text-amber-300">{p.title}</strong>
                <span className="text-[15px] leading-[1.7] text-ink-dark-muted">{p.body}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <div className={`${SECTION} flex flex-col gap-12 py-12 md:gap-20 md:py-20`}>
        <section aria-labelledby="how-title" className="flex flex-col gap-6">
          <SectionHead id="how-title" title={t("howTitle")} />
          <Steps steps={how} />
        </section>

        <section
          id="faq"
          aria-labelledby="faq-title"
          className="grid scroll-mt-24 gap-6 lg:grid-cols-[1fr_2fr] lg:gap-16"
        >
          <SectionHead id="faq-title" title={t("faqTitle")} />
          <Faq items={faq} />
        </section>
      </div>

      <CtaBand
        title={t("ctaTitle")}
        body={t("ctaBody")}
        primary={{ href: "/coloring#books", label: t("ctaBooks") }}
        secondary={{ href: "/shop", label: t("ctaAll") }}
      />
      <div className="h-12 md:h-20" />
    </PageShell>
  );
}
