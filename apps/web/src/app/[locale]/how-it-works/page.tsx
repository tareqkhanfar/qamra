import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { Kid } from "@/components/art/Kid";
import { Scene } from "@/components/art/Scene";
import { JsonLd } from "@/components/site/JsonLd";
import { PageShell } from "@/components/site/PageShell";
import { Photo } from "@/components/site/Photo";
import { Arrow, CtaBand, Faq, SECTION, SectionHead, Steps, type QA, type Step } from "@/components/site/blocks";
import { Link } from "@/i18n/navigation";
import { getPublicSettings, getStoreCatalog, whatsappLink } from "@/lib/catalog";
import { faqJsonLd } from "@/lib/pageSeo";
import { pageMetadata } from "@/lib/seo";
import { money } from "@/lib/store";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("howPage"), getLocale()]);
  return pageMetadata({ path: "/how-it-works", locale, title: t("title"), description: t("lead") });
}

/** How it works: the story-book flow with the privacy promises, the activity-book flow, «صوت أهلي», the FAQ. */
export default async function HowItWorksPage() {
  const locale = await getLocale();
  const [t, catalog, site] = await Promise.all([getTranslations("howPage"), getStoreCatalog(), getPublicSettings()]);
  const currency = catalog?.currency ?? "ILS";
  const zones = (catalog?.zones ?? []).filter((z) => z.currency === currency);
  const eta = zones.length
    ? { min: Math.min(...zones.map((z) => z.eta_days[0])), max: Math.max(...zones.map((z) => z.eta_days[1])) }
    : { min: 2, max: 7 };
  const storySteps = (t.raw("storySteps") as Step[]).map((s) => ({
    title: s.title.replace("{min}", String(eta.min)).replace("{max}", String(eta.max)),
    body: s.body,
  }));
  const activitySteps = t.raw("activitySteps") as Step[];
  const privacy = t.raw("privacy") as { title: string; body: string }[];
  const faq = t.raw("faq") as QA[];
  const voice = catalog?.addons.find((a) => a.slug === "family-voice") ?? null;
  const whatsapp = site?.support_whatsapp;
  const shield = (
    <svg
      className="size-7 md:size-9"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#2E7A52"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );

  return (
    <PageShell>
      <JsonLd data={faqJsonLd(faq, locale)} />
      <div className={`${SECTION} flex flex-col gap-12 pt-8 pb-16 md:gap-20 md:pt-14 md:pb-24`}>
        <header className="grid items-center gap-6 lg:grid-cols-[1.1fr_1fr] lg:gap-12">
          <div className="flex flex-col gap-3">
            <h1 className="text-[32px] leading-tight text-night-900 md:text-[52px]">{t("title")}</h1>
            <p className="max-w-[640px] text-body text-ink-muted md:text-body-l">{t("lead")}</p>
          </div>
          <div className="hidden md:block">
            <Photo
              name="first-day"
              alt={t("photoAlt")}
              sizes="(min-width: 1024px) 600px, 100vw"
              className="rounded-[24px]"
              fallback={
                <div className="overflow-hidden rounded-[24px]">
                  <Scene
                    theme="garden"
                    ratio={3 / 2}
                    outfit="#5B6FC0"
                    skin="#C98F63"
                    hairStyle="curly"
                    pose="wave"
                    kidScale={0.62}
                  />
                </div>
              }
            />
          </div>
        </header>

        {/* THE STORY BOOK */}
        <section id="story" className="flex scroll-mt-24 flex-col gap-6">
          <SectionHead
            title={t("storyTitle")}
            lead={t("storyLead")}
            more={{ href: "/stories", label: t("ctaStories") }}
          />
          <Steps steps={storySteps} />
        </section>

        {/* PRIVACY */}
        <section
          id="privacy"
          className="grid scroll-mt-24 items-center gap-8 rounded-[24px] bg-paper-sunk p-6 md:p-10 lg:grid-cols-[1fr_1.4fr] lg:gap-16"
        >
          <div className="flex flex-col gap-4">
            <div className="flex size-14 items-center justify-center rounded-md bg-success-bg md:size-[72px]">
              {shield}
            </div>
            <h2 className="text-[28px] leading-tight text-night-900 md:text-[40px]">{t("privacyTitle")}</h2>
            <p className="text-body-l text-ink-muted">{t("privacyLead")}</p>
            <Link href="/privacy" className="font-bold text-amber-700">
              {t("privacyMore")} <Arrow />
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {privacy.map((p) => (
              <div key={p.title} className="flex flex-col gap-1.5 rounded-lg border border-line bg-paper-raised p-5">
                <h3 className="text-[18px] text-night-900">{p.title}</h3>
                <p className="text-[15px] leading-[1.7] text-ink-muted">{p.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* THE ACTIVITY BOOKS */}
        <section id="activity" className="flex scroll-mt-24 flex-col gap-6">
          <div className="grid items-center gap-6 lg:grid-cols-[1fr_auto]">
            <SectionHead
              title={t("activityTitle")}
              lead={t("activityLead")}
              more={{ href: "/workbooks", label: t("activityCta") }}
            />
            <Photo
              name="workbook-tracing"
              alt={t("activityPhotoAlt")}
              sizes="180px"
              className="hidden w-[180px] rounded-[20px] lg:block"
            />
          </div>
          <Steps steps={activitySteps} />
        </section>

        {/* «صوت أهلي» */}
        {voice && (
          <section className="grid items-center gap-6 overflow-hidden rounded-[24px] bg-night-900 text-paper lg:grid-cols-2">
            <Photo
              name="grandma-voice"
              alt={t("voicePhotoAlt")}
              sizes="(min-width: 1024px) 600px, 100vw"
              fallback={
                <Scene
                  theme="night"
                  ratio={3 / 2}
                  hijab
                  hijabColor="#E9826B"
                  outfit="#F2B33D"
                  kidScale={0.55}
                  companion="blob"
                />
              }
            />
            <div className="flex flex-col gap-3 p-6 md:p-10">
              <h2 className="text-[28px] md:text-[36px]">{t("voiceTitle")}</h2>
              <p className="text-[15px] leading-[1.75] text-night-100 md:text-body-l">{t("voiceBody")}</p>
              {voice.price !== null && (
                <strong className="font-display text-[20px] text-amber-300">
                  {t("voicePrice", { price: money(voice.price, currency, locale) })}
                </strong>
              )}
            </div>
          </section>
        )}

        {/* FAQ */}
        <section id="faq" className="grid scroll-mt-24 gap-6 lg:grid-cols-[1fr_2fr] lg:gap-16">
          <div className="flex flex-col gap-3">
            <SectionHead title={t("faqTitle")} lead={t("faqLead")} />
            {whatsapp && (
              <a href={whatsappLink(whatsapp)} className="font-bold text-amber-700" rel="noopener">
                {t("faqWhatsapp")}
              </a>
            )}
            <div className="hidden w-[40%] lg:block">
              <Kid hijab hijabColor="#E9826B" outfit="#F2B33D" pose="wave" />
            </div>
          </div>
          <Faq items={faq} />
        </section>
      </div>
      <CtaBand
        title={t("closingTitle")}
        body={t("closingBody")}
        primary={{ href: "/stories", label: t("ctaStories") }}
        secondary={{ href: "/workbooks", label: t("ctaWorkbooks") }}
      />
      <div className="h-12 md:h-20" />
    </PageShell>
  );
}
