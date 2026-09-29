import { getLocale, getTranslations } from "next-intl/server";
import { Drawing } from "@/components/art/Drawing";
import { Kid } from "@/components/art/Kid";
import { Scene } from "@/components/art/Scene";
import { BookViewer } from "@/components/book/BookViewer";
import { CoverArt } from "@/components/book/CoverArt";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteNav } from "@/components/site/SiteNav";
import { StickyCta } from "@/components/site/StickyCta";
import { StoryLines } from "@/components/shop/StoryLines";
import { StoryCard } from "@/components/site/StoryCard";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { examplesFor, getPublicSettings, getStoreCatalog, getTheme, getThemes, whatsappLink } from "@/lib/catalog";
import { coversOf, storyFrom } from "@/lib/story";

type Card = { title: string; body: string };

const SHIELD = (
  <svg
    className="size-5 shrink-0"
    viewBox="0 0 24 24"
    fill="none"
    stroke="#7FD1A1"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
    <path d="M9 12l2 2 4-4" />
  </svg>
);

function Eyebrow({ children, dark }: { children: React.ReactNode; dark?: boolean }) {
  return <span className={`text-[15px] font-bold ${dark ? "text-amber-300" : "text-amber-700"}`}>{children}</span>;
}

export default async function LandingPage() {
  const locale = await getLocale();
  const [t, ts, themes, examples, catalog, site] = await Promise.all([
    getTranslations("landing"),
    getTranslations("shop"),
    getThemes(locale),
    examplesFor(locale),
    getStoreCatalog(),
    getPublicSettings(),
  ]);
  // the book the landing shows: a published example (real pages), else the first story's illustrated sample
  const featured = examples[0] ?? null;
  const sample = await getTheme(featured?.theme ?? "first-day", locale);
  const featuredExamples = examples.filter((e) => e.theme === featured?.theme);
  const covers = coversOf(examples);
  const brand = brandName(locale);
  const how = t.raw("how") as Card[];
  const privacy = t.raw("privacy") as Card[];
  const faq = t.raw("faq") as { q: string; a: string }[];
  const whatsapp = site?.support_whatsapp;
  const live = (themes ?? []).filter((th) => th.status === "available");
  const section = "mx-auto w-full max-w-[1440px] px-4 md:px-10 xl:px-24";

  return (
    <>
      {/* HERO */}
      <section id="hero" className="relative overflow-hidden bg-night-900 text-paper">
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          viewBox="0 0 1440 820"
          preserveAspectRatio="xMidYMid slice"
          aria-hidden="true"
        >
          <g fill="#F2B33D">
            {[
              {
                d: "M160 180 C162 194 166 198 180 200 C166 202 162 206 160 220 C158 206 154 202 140 200 C154 198 158 194 160 180 Z",
                delay: 0,
              },
              {
                d: "M700 130 C701 137 703 139 710 140 C703 141 701 143 700 150 C699 143 697 141 690 140 C697 139 699 137 700 130 Z",
                delay: 1.1,
              },
              {
                d: "M1210 300 C1211 307 1213 309 1220 310 C1213 311 1211 313 1210 320 C1209 313 1207 311 1200 310 C1207 309 1209 307 1210 300 Z",
                delay: 0.6,
              },
              {
                d: "M330 470 C331 476 333 478 339 479 C333 480 331 482 330 488 C329 482 327 480 321 479 C327 478 329 476 330 470 Z",
                delay: 1.7,
              },
            ].map((star) => (
              <path
                key={star.d}
                d={star.d}
                className="[transform-origin:center] animate-twinkle [transform-box:fill-box]"
                style={{ animationDelay: `${star.delay}s` }}
              />
            ))}
            {[
              [420, 120, 3, 0.3],
              [560, 640, 2.5, 1.4],
              [1320, 160, 3, 0.9],
              [1000, 720, 2.5, 2.1],
              [80, 560, 3, 0.5],
              [880, 200, 2, 1.8],
              [1100, 90, 2, 2.6],
              [260, 330, 2, 1.2],
              [1380, 420, 2.5, 0.2],
              [640, 300, 1.8, 2.3],
            ].map(([cx, cy, r, delay]) => (
              <circle
                key={`${cx}-${cy}`}
                cx={cx}
                cy={cy}
                r={r}
                className="[transform-origin:center] animate-twinkle [transform-box:fill-box]"
                style={{ animationDelay: `${delay}s` }}
              />
            ))}
          </g>
          <path d="M0 760 C300 700 600 740 900 760 S1300 730 1440 750 L1440 820 L0 820 Z" fill="#22306A" />
        </svg>
        <span
          aria-hidden="true"
          className="pointer-events-none absolute top-[14%] right-[18%] h-[2px] w-28 -rotate-[28deg] animate-shoot rounded-full bg-gradient-to-l from-transparent via-amber-100 to-transparent"
        />
        <span
          aria-hidden="true"
          className="pointer-events-none absolute top-[38%] left-[8%] h-[2px] w-20 -rotate-[28deg] animate-shoot rounded-full bg-gradient-to-l from-transparent via-amber-300 to-transparent [animation-delay:7.5s]"
        />
        <SiteNav variant="dark" />
        <div
          className={`${section} relative grid items-center gap-10 pt-4 pb-12 md:pt-12 md:pb-24 lg:grid-cols-[1fr_1.1fr] lg:gap-12`}
        >
          <div className="flex flex-col gap-5 md:gap-7">
            <span className="self-start rounded-full bg-night-800 px-3.5 py-2 text-small font-semibold text-amber-300">
              {t("tagline")}
            </span>
            <h1 className="text-[40px] leading-[1.18] font-extrabold md:text-[72px] md:leading-[1.12]">
              {t("title1")}
              <br />
              <span className="text-amber-500">{t("title2")}</span>
            </h1>
            <p className="max-w-[540px] text-[17px] leading-[1.75] text-night-100 md:text-[20px]">{t("lead")}</p>
            <div className="hidden items-center gap-4 md:flex">
              <Link
                href="/stories"
                className="flex min-h-[60px] animate-glow items-center gap-2.5 rounded-full bg-amber-500 px-8 text-[19px] font-bold text-night-950 transition hover:-translate-y-0.5"
              >
                {t("cta")}
                <svg
                  className="size-[22px] ltr:-scale-x-100"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M19 12H5" />
                  <path d="M11 6l-6 6 6 6" />
                </svg>
              </Link>
              <a
                href="#samples"
                className="flex min-h-[60px] items-center rounded-full border-2 border-night-500 px-6 text-[18px] font-semibold text-paper hover:bg-night-800"
              >
                {t("samplesCta")}
              </a>
            </div>
            <div className="hidden items-center gap-2.5 text-[15px] text-ink-dark-muted md:flex">
              {SHIELD}
              {t("privacyLine")}
            </div>
          </div>

          {/* photo + drawing → book */}
          <div className="flex flex-col items-center gap-3 lg:flex-row lg:justify-center lg:gap-3.5">
            <div className="flex items-center gap-5 lg:flex-col lg:gap-[18px]">
              <figure className="flex rotate-[4deg] animate-float flex-col items-center gap-2 [animation-delay:0.4s]">
                <div className="w-[108px] rounded-[6px] bg-paper-raised px-2 pt-2 pb-6 shadow-[0_8px_24px_rgba(0,0,0,0.3)] lg:w-[146px]">
                  <Kid look="photo" hijab hijabColor="#E9826B" className="block h-auto w-full rounded-[8px]" />
                </div>
                <figcaption className="text-small text-ink-dark-muted">{t("heroPhoto")}</figcaption>
              </figure>
              <span className="font-display text-[28px] font-extrabold text-amber-500 lg:hidden">+</span>
              <figure className="flex -rotate-[5deg] animate-float flex-col items-center gap-2 [animation-delay:1.3s]">
                <div className="relative w-[104px] shadow-[0_8px_24px_rgba(0,0,0,0.3)] lg:w-[140px]">
                  <Drawing variant="blob" />
                  <span
                    className="absolute -top-2 left-[31%] h-4 w-[37%] -rotate-[4deg] bg-amber-100/85"
                    aria-hidden="true"
                  />
                </div>
                <figcaption className="text-small text-ink-dark-muted">{t("heroDrawing")}</figcaption>
              </figure>
            </div>
            <svg
              className="size-[30px] lg:hidden"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#F2B33D"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 4v16" />
              <path d="M6 14l6 6 6-6" />
            </svg>
            <svg
              className="hidden h-[120px] w-20 shrink-0 lg:block ltr:-scale-x-100"
              viewBox="0 0 80 120"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M72 20 C40 30 40 60 14 60"
                stroke="#F2B33D"
                strokeWidth="3"
                strokeDasharray="3 9"
                className="animate-dash"
                strokeLinecap="round"
              />
              <path
                d="M72 100 C40 90 40 60 14 60"
                stroke="#F2B33D"
                strokeWidth="3"
                strokeDasharray="3 9"
                className="animate-dash"
                strokeLinecap="round"
              />
              <path
                d="M22 50 L10 60 L22 70"
                stroke="#F2B33D"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <figure className="flex -rotate-2 animate-float-slow flex-col items-center gap-2.5">
              {featured ? (
                <Link
                  href={`/stories/${featured.theme}`}
                  aria-label={t("heroRealBook", { title: featured.title })}
                  className="block w-[300px] overflow-hidden rounded-s-[18px] rounded-e-[6px] border-s-[12px] border-night-950 shadow-[0_16px_40px_rgba(0,0,0,0.4)] lg:w-[380px]"
                >
                  <CoverArt
                    example={featured}
                    art={sample?.art ?? { scene: "night" }}
                    titleName={featured.title_name}
                    titleRest={featured.title_rest}
                    alt={t("heroRealBook", { title: featured.title })}
                    sizes="380px"
                    priority
                  />
                </Link>
              ) : (
                <div className="relative w-[300px] overflow-hidden rounded-s-[18px] rounded-e-[6px] border-s-[12px] border-night-950 shadow-[0_16px_40px_rgba(0,0,0,0.4)] lg:w-[360px]">
                  <Scene
                    theme="night"
                    ratio={360 / 420}
                    hijab
                    hijabColor="#E9826B"
                    outfit="#F2B33D"
                    pose="wave"
                    kidScale={0.5}
                    companion="blob"
                  />
                  <div className="absolute inset-x-0 top-5 text-center font-display text-[24px] leading-tight font-extrabold text-paper lg:text-[32px]">
                    {t("heroBookTitle")}
                    <br />
                    <span className="text-[16px] text-amber-300 lg:text-[19px]">{t("heroBookSub")}</span>
                  </div>
                </div>
              )}
              <figcaption className="hidden text-small text-ink-dark-muted lg:block">{t("heroBook")}</figcaption>
            </figure>
          </div>

          <div className="flex flex-col gap-3 md:hidden">
            <Link
              href="/stories"
              className="flex min-h-14 items-center justify-center rounded-full bg-amber-500 text-[18px] font-bold text-night-950"
            >
              {t("cta")}
            </Link>
            <div className="flex items-center justify-center gap-2 text-small text-ink-dark-muted">
              {SHIELD}
              {t("privacyLine")}
            </div>
          </div>
        </div>
      </section>

      {/* A REAL BOOK: flip through a published example (or the story's illustrated sample) */}
      <section id="samples" className="scroll-mt-20 bg-paper-sunk py-12 md:py-20">
        <div
          className={`${section} grid grid-cols-[minmax(0,1fr)] items-start gap-6 md:gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]`}
        >
          <div className="flex flex-col gap-3 lg:sticky lg:top-28">
            <Eyebrow>{t("samplesEyebrow")}</Eyebrow>
            <h2 id="samples-title" className="text-[26px] text-night-900 md:text-[44px]">
              {featured ? t("realBookTitle") : t("samplesTitle", { name: sample?.sample_name ?? "" })}
            </h2>
            <p className="text-body text-ink-muted md:text-body-l">{featured ? t("realBookLead") : t("sampleLead")}</p>
            {sample && (
              <Link
                href={`/stories/${sample.slug}`}
                className="flex min-h-12 items-center gap-1 self-start font-bold text-amber-700"
              >
                {t("openStory", { name: sample.name })} <span className="inline-block rtl:-scale-x-100">→</span>
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

      {/* HOW */}
      <section
        id="how"
        className={`${section} flex scroll-mt-24 flex-col gap-8 py-12 md:items-center md:gap-12 md:py-24`}
      >
        <div className="flex flex-col gap-3 md:items-center md:text-center">
          <Eyebrow>{t("howEyebrow")}</Eyebrow>
          <h2 className="text-[30px] text-night-900 md:text-[44px]">{t("howTitle", { brand })}</h2>
        </div>
        <div className="grid w-full gap-4 md:grid-cols-3 md:gap-8">
          {how.map((s, i) => (
            <div
              key={s.title}
              data-reveal
              style={{ "--d": `${i * 120}ms` } as React.CSSProperties}
              className="flex flex-col overflow-hidden rounded-[20px] border border-line bg-paper-raised md:rounded-xl"
            >
              <div className="relative flex aspect-[16/10] items-center justify-center overflow-hidden bg-paper-sunk">
                {i === 0 && (
                  <div className="w-[34%] rotate-[-4deg] rounded-[6px] bg-paper-raised px-2 pt-2 pb-5 shadow-[0_8px_24px_rgba(22,32,74,0.18)]">
                    <Kid look="photo" className="block h-auto w-full rounded-[4px]" />
                  </div>
                )}
                {i === 1 &&
                  (featured?.character ? (
                    // eslint-disable-next-line @next/next/no-img-element -- the example's watermarked character sheet
                    <img
                      src={featured.character}
                      alt={t("howCharacterAlt", { name: featured.child_name })}
                      loading="lazy"
                      className="size-full object-contain p-3"
                    />
                  ) : (
                    <div className="w-[30%]">
                      <Kid hijab hijabColor="#E9826B" outfit="#F2B33D" pose="wave" />
                    </div>
                  ))}
                {i === 2 && (
                  <div className="w-[46%] rotate-[3deg] overflow-hidden rounded-s-[10px] rounded-e-[4px] border-s-[6px] border-night-950 shadow-book">
                    <CoverArt
                      example={featured}
                      art={sample?.art ?? { scene: "night" }}
                      titleName={featured?.title_name ?? sample?.name ?? ""}
                      titleRest={featured?.title_rest ?? ""}
                      alt={featured ? t("heroRealBook", { title: featured.title }) : t("howBookAlt")}
                      sizes="240px"
                    />
                  </div>
                )}
                <span className="absolute start-3 top-3 flex size-10 items-center justify-center rounded-[12px] bg-night-900 font-display text-xl font-extrabold text-amber-500">
                  {i + 1}
                </span>
              </div>
              <div className="flex flex-col gap-1 p-5 md:p-6">
                <h3 className="text-[19px] text-night-900 md:text-[22px]">{s.title}</h3>
                <p className="text-[15px] leading-[1.75] text-ink-muted md:text-body">{s.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* STORIES, with their real covers */}
      {live.length > 0 && (
        <section className={`${section} flex flex-col gap-6 py-12 md:gap-8 md:py-24`}>
          <div className="flex items-end justify-between gap-3">
            <div className="flex flex-col gap-2">
              <Eyebrow>{t("themesEyebrow")}</Eyebrow>
              <h2 className="text-[26px] text-night-900 md:text-[44px]">{t("themesTitle")}</h2>
            </div>
            <Link href="/stories" className="flex min-h-11 items-center gap-1 font-bold text-amber-700">
              {t("allThemes")} <span className="inline-block rtl:-scale-x-100">→</span>
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-3 md:gap-5 lg:grid-cols-3 lg:gap-7">
            {live.slice(0, 6).map((th, i) => (
              <div key={th.slug} data-reveal style={{ "--d": `${(i % 3) * 90}ms` } as React.CSSProperties}>
                <StoryCard
                  theme={th}
                  example={covers[th.slug] ?? null}
                  from={storyFrom(catalog, th)}
                  currency={catalog?.currency ?? "ILS"}
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* PRIVACY */}
      <section
        id="privacy"
        className={`${section} grid scroll-mt-20 items-center gap-8 py-12 md:py-24 lg:grid-cols-[1fr_1.4fr] lg:gap-16`}
      >
        <div className="flex flex-col gap-4 md:gap-5">
          <div className="flex size-14 items-center justify-center rounded-md bg-success-bg md:size-[72px] md:rounded-lg">
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
          </div>
          <h2 className="text-[30px] leading-tight text-night-900 md:text-[44px]">{t("privacyTitle")}</h2>
          <p className="text-body-l text-ink-muted">{t("privacyLead", { brand })}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 md:gap-5">
          {privacy.map((p, i) => (
            <div
              key={p.title}
              data-reveal
              style={{ "--d": `${i * 100}ms` } as React.CSSProperties}
              className="flex flex-col gap-2 border-b border-dashed border-line py-3 sm:rounded-lg sm:border sm:border-solid sm:bg-paper-raised sm:p-6"
            >
              <h3 className="text-[18px] text-night-900 md:text-[20px]">{p.title}</h3>
              <p className="text-[15px] leading-[1.7] text-ink-muted">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* THE TWO BOOK TYPES, as the shop shows them, with the quiz */}
      <section id="pricing" className={`${section} flex scroll-mt-20 flex-col gap-5 pb-12 md:gap-8 md:pb-24`}>
        <div className="flex items-end justify-between gap-3">
          <div className="flex flex-col gap-2">
            <Eyebrow>{t("pricingEyebrow")}</Eyebrow>
            <h2 className="text-[26px] text-night-900 md:text-[44px]">{t("linesTitle")}</h2>
            <p className="text-[15px] text-ink-muted md:text-[17px]">{t("pricingLead")}</p>
          </div>
          <Link href="/shop" className="flex min-h-11 shrink-0 items-center gap-1 font-bold text-amber-700">
            {t("allBooks")} <span className="inline-block rtl:-scale-x-100">→</span>
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-[2fr_1fr] md:gap-6">
          <StoryLines catalog={catalog} stories={live} examples={examples} />
          <Link
            href="/quiz"
            className="flex items-center gap-3.5 rounded-[20px] bg-paper-sunk p-4 md:flex-col md:items-start md:justify-center md:p-8"
          >
            <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-paper-raised">
              <svg
                className="size-[26px]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#9A620A"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.5V14" />
                <path d="M12 17.2v.1" />
              </svg>
            </span>
            <span className="flex grow flex-col gap-0.5">
              <strong className="text-[17px] text-night-900 md:text-[22px]">{ts("quiz.title")}</strong>
              <span className="text-small text-ink-muted">{ts("quiz.body")}</span>
            </span>
          </Link>
        </div>
      </section>

      {/* KINDERGARTENS */}
      <section className="mx-4 grid items-center gap-8 overflow-hidden rounded-xl bg-night-900 p-6 text-paper md:mx-10 md:rounded-[32px] md:p-16 lg:grid-cols-[1.2fr_1fr] lg:gap-12 xl:mx-24 2xl:mx-auto 2xl:max-w-[1248px]">
        <div className="flex flex-col gap-4 md:gap-5">
          <Eyebrow dark>{t("kgEyebrow")}</Eyebrow>
          <h2 className="text-[26px] leading-tight md:text-[44px]">{t("kgTitle")}</h2>
          <p className="text-[15px] leading-[1.75] text-night-100 md:text-body-l">{t("kgLead")}</p>
          <div className="flex flex-wrap gap-3 md:gap-4">
            <Link
              href="/kindergartens#demo"
              className="flex min-h-[52px] grow items-center justify-center rounded-full bg-amber-500 px-7 text-[16px] font-bold text-night-950 sm:grow-0 md:min-h-14 md:text-[17px]"
            >
              {t("kgCta")}
            </Link>
            <Link
              href="/kindergartens#flow"
              className="hidden min-h-14 items-center px-5 text-[17px] font-semibold text-paper underline underline-offset-[6px] md:flex"
            >
              {t("kgHow")}
            </Link>
          </div>
        </div>
        <div className="hidden justify-center gap-3 lg:flex">
          <div className="w-40 translate-y-3 rotate-[5deg] overflow-hidden rounded-md">
            <Scene
              theme="grad"
              ratio={160 / 200}
              cap
              outfit="#7FA38A"
              hairStyle="curly"
              skin="#8D5A3B"
              kidScale={0.8}
            />
          </div>
          <div className="z-10 w-[180px] overflow-hidden rounded-md">
            <Scene theme="grad" ratio={180 / 220} cap hijab outfit="#A99BD6" kidScale={0.8} />
          </div>
          <div className="w-40 translate-y-3 -rotate-[5deg] overflow-hidden rounded-md">
            <Scene theme="grad" ratio={160 / 200} cap outfit="#E9826B" hairStyle="long" skin="#F3CFAE" kidScale={0.8} />
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section
        id="faq"
        className={`${section} grid scroll-mt-20 gap-6 py-12 md:py-24 lg:grid-cols-[1fr_2fr] lg:gap-16`}
      >
        <div className="flex flex-col gap-3">
          <h2 className="text-[30px] text-night-900 md:text-[44px]">{t("faqTitle")}</h2>
          <p className="text-body text-ink-muted">{t("faqLead")}</p>
          {whatsapp && (
            <a href={whatsappLink(whatsapp)} className="font-bold text-amber-700" rel="noopener">
              {t("faqWhatsapp")}
            </a>
          )}
        </div>
        <div className="flex flex-col gap-3">
          {faq.map((f, i) => (
            <details
              key={f.q}
              data-reveal
              style={{ "--d": `${i * 70}ms` } as React.CSSProperties}
              open={i === 0}
              className="group rounded-lg border border-line bg-paper-raised px-4 md:px-6"
            >
              <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 text-body font-bold text-night-900 md:min-h-[60px] md:text-[18px] [&::-webkit-details-marker]:hidden">
                {f.q}
                <svg
                  className="size-5 shrink-0 text-amber-700 transition group-open:rotate-180"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </summary>
              <p className="pb-4 text-[15px] leading-[1.75] text-ink-muted md:pb-5 md:text-body">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      <SiteFooter />

      <StickyCta watchId="hero">
        <div className="flex items-center gap-2.5">
          <Link
            href="/stories"
            className="flex min-h-[52px] grow items-center justify-center rounded-full bg-amber-500 text-[17px] font-bold text-night-950"
          >
            {t("cta")}
          </Link>
          <span className="w-[70px] text-xs leading-snug text-ink-muted">{t("stickyNote")}</span>
        </div>
      </StickyCta>
    </>
  );
}
