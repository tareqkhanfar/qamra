import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { Kid } from "@/components/art/Kid";
import { BookViewer } from "@/components/book/BookViewer";
import { CoverArt } from "@/components/book/CoverArt";
import { ActivityBookCard } from "@/components/site/ActivityBookCard";
import { HomeHero } from "@/components/site/HomeHero";
import { JsonLd } from "@/components/site/JsonLd";
import { OfferCards } from "@/components/site/OfferCards";
import { Photo } from "@/components/site/Photo";
import { SiteFooter } from "@/components/site/SiteFooter";
import { StickyCta } from "@/components/site/StickyCta";
import { Arrow, CtaBand, Faq, SECTION, SectionHead, Steps, type QA, type Step } from "@/components/site/blocks";
import { Link } from "@/i18n/navigation";
import { examplesFor, getShopSummary, getStoreCatalog, getTheme } from "@/lib/catalog";
import { brandName } from "@/config/brand";
import { siteJsonLd } from "@/lib/pageSeo";
import { pageMetadata } from "@/lib/seo";
import { ACTIVITY_LINES } from "@/lib/shop";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("meta"), getLocale()]);
  return pageMetadata({
    path: "/",
    locale,
    title: t("title", { brand: brandName(locale) }),
    description: t("description"),
    bare: true,
  });
}

/** The home: the promise, the four offers, a real book, how it works, why Qamra, the activity books, FAQ, CTA. */
export default async function LandingPage() {
  const locale = await getLocale();
  const [t, tm, examples, catalog, summary] = await Promise.all([
    getTranslations("landing"),
    getTranslations("meta"),
    examplesFor(locale),
    getStoreCatalog(),
    getShopSummary(),
  ]);
  const featured = examples[0] ?? null; // a published example (real pages), else the first story's sample
  const sample = await getTheme(featured?.theme ?? "first-day", locale);
  const featuredExamples = examples.filter((e) => e.theme === featured?.theme);
  const activity = (catalog?.products ?? []).filter((p) => (ACTIVITY_LINES as readonly string[]).includes(p.line));
  const currency = catalog?.currency ?? "ILS";
  const art = sample?.art ?? { scene: "night" as const };
  const how = t.raw("how") as Step[];
  const why = t.raw("why") as { title: string; body: string }[];
  const faq = t.raw("faq") as QA[];
  const howVisuals = [
    <div
      key="photo"
      className="w-[34%] rotate-[-4deg] rounded-[6px] bg-paper-raised px-2 pt-2 pb-5 shadow-[0_8px_24px_rgba(22,32,74,0.18)]"
    >
      <Kid look="photo" className="block h-auto w-full rounded-[4px]" />
    </div>,
    featured?.character ? (
      // eslint-disable-next-line @next/next/no-img-element -- the example's watermarked character sheet
      <img
        key="character"
        src={featured.character}
        alt={t("howCharacterAlt", { name: featured.child_name })}
        loading="lazy"
        className="size-full object-contain p-3"
      />
    ) : (
      <div key="character" className="w-[30%]">
        <Kid hijab hijabColor="#E9826B" outfit="#F2B33D" pose="wave" />
      </div>
    ),
    <div
      key="book"
      className="w-[46%] rotate-[3deg] overflow-hidden rounded-s-[10px] rounded-e-[4px] border-s-[6px] border-night-950 shadow-book"
    >
      <CoverArt
        example={featured}
        art={art}
        titleName={featured?.title_name ?? sample?.name ?? ""}
        titleRest={featured?.title_rest ?? ""}
        alt={featured ? t("heroRealBook", { title: featured.title }) : t("howBookAlt")}
        sizes="240px"
      />
    </div>,
  ];

  return (
    <>
      <JsonLd data={siteJsonLd(locale, tm("description"))} />
      <HomeHero featured={featured} art={art} />

      {/* WHAT WE SELL: the four offers, with real covers and the prices they start from */}
      <section className={`${SECTION} flex flex-col gap-5 py-10 md:gap-8 md:py-16`}>
        <SectionHead eyebrow={t("offersEyebrow")} title={t("offersTitle")} />
        <OfferCards catalog={catalog} examples={examples} summary={summary} />
      </section>

      {/* A REAL BOOK: flip through a published example */}
      <section id="samples" className="scroll-mt-20 bg-paper-sunk py-12 md:py-20">
        <div
          className={`${SECTION} grid grid-cols-[minmax(0,1fr)] items-start gap-6 md:gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:items-center`}
        >
          <div className="flex flex-col gap-3">
            <SectionHead
              id="samples-title"
              eyebrow={t("samplesEyebrow")}
              title={featured ? t("realBookTitle") : t("samplesTitle", { name: sample?.sample_name ?? "" })}
              lead={featured ? t("realBookLead") : t("sampleLead")}
            />
            {sample && (
              <Link
                href={`/stories/${sample.slug}`}
                className="flex min-h-12 items-center gap-1 self-start font-bold text-amber-700"
              >
                {t("openStory", { name: sample.name })} <Arrow />
              </Link>
            )}
          </div>
          <div className="w-full max-w-[560px] justify-self-center">
            <BookViewer
              examples={featuredExamples}
              fallback={sample?.samples ?? []}
              headingId="samples-title"
              titlePage={false}
              end={
                sample
                  ? {
                      title: t("viewerEndTitle"),
                      body: t("viewerEndBody"),
                      label: t("viewerEndCta"),
                      href: `/stories/${sample.slug}`,
                    }
                  : null
              }
            />
          </div>
        </div>
      </section>

      {/* HOW, in three steps */}
      <section id="how" className={`${SECTION} flex scroll-mt-24 flex-col gap-6 py-12 md:gap-10 md:py-20`}>
        <SectionHead
          eyebrow={t("howEyebrow")}
          title={t("howTitle")}
          more={{ href: "/how-it-works", label: t("howMore") }}
        />
        <Steps steps={how} visuals={howVisuals} />
      </section>

      {/* WHY QAMRA */}
      <section className="bg-night-900 py-12 text-paper md:py-20">
        <div className={`${SECTION} flex flex-col gap-6 md:gap-8`}>
          <SectionHead title={t("whyTitle")} dark />
          <ul className="grid gap-3 sm:grid-cols-2 md:gap-4 lg:grid-cols-5">
            {why.map((w, i) => (
              <li
                key={w.title}
                data-reveal
                style={{ "--d": `${i * 80}ms` } as React.CSSProperties}
                className="flex flex-col gap-1.5 rounded-[18px] bg-night-800 p-5"
              >
                <strong className="text-[17px] text-amber-300">{w.title}</strong>
                <span className="text-[15px] leading-[1.7] text-ink-dark-muted">{w.body}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* THE ACTIVITY BOOKS, with their real pages */}
      {activity.length > 0 && (
        <section className={`${SECTION} flex flex-col gap-6 py-12 md:gap-8 md:py-20`}>
          <div className="grid items-center gap-6 lg:grid-cols-[1fr_auto]">
            <SectionHead
              eyebrow={t("activityEyebrow")}
              title={t("activityTitle")}
              lead={t("activityLead")}
              more={{ href: "/workbooks", label: t("activityAll") }}
            />
            <Photo
              name="books-stack"
              alt={t("activityEyebrow")}
              sizes="200px"
              className="hidden w-[200px] rounded-[20px] lg:block"
            />
          </div>
          <div className="grid gap-4 md:grid-cols-3 md:gap-6">
            {activity.map((p) => (
              <ActivityBookCard key={p.slug} product={p} currency={currency} />
            ))}
          </div>
        </section>
      )}

      {/* FAQ, short */}
      <section
        id="faq"
        className={`${SECTION} grid scroll-mt-20 gap-6 py-12 md:py-20 lg:grid-cols-[1fr_2fr] lg:gap-16`}
      >
        <SectionHead title={t("faqTitle")} more={{ href: "/how-it-works#faq", label: t("faqMore") }} />
        <Faq items={faq} />
      </section>

      <CtaBand
        title={t("closingTitle")}
        body={t("closingBody")}
        primary={{ href: "/stories", label: t("ctaStories") }}
        secondary={{ href: "/workbooks", label: t("ctaWorkbooks") }}
      />
      <div className="h-12 md:h-20" />
      <SiteFooter />

      <StickyCta watchId="hero">
        <div className="flex items-center gap-2.5">
          <Link
            href="/stories"
            className="flex min-h-[52px] grow items-center justify-center rounded-full bg-amber-500 text-[17px] font-bold text-night-950"
          >
            {t("ctaStories")}
          </Link>
          <span className="w-[70px] text-xs leading-snug text-ink-muted">{t("stickyNote")}</span>
        </div>
      </StickyCta>
    </>
  );
}
