import { getTranslations } from "next-intl/server";
import { Drawing } from "@/components/art/Drawing";
import { Kid } from "@/components/art/Kid";
import { Scene, type SceneArt } from "@/components/art/Scene";
import { CoverArt } from "@/components/book/CoverArt";
import { Link } from "@/i18n/navigation";
import type { Example } from "@/lib/examples";
import { NightSky } from "./NightSky";
import { Photo } from "./Photo";
import { SiteNav } from "./SiteNav";
import { SECTION } from "./blocks";

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

/**
 * The home hero: the promise («كتب مطبوعة باسم طفلك»), the two things to do next, and a picture: the lifestyle
 * photo when Tareq has added it, else the "photo + drawing → real book" composition.
 */
export async function HomeHero({ featured, art }: { featured: Example | null; art: SceneArt }) {
  const t = await getTranslations("landing");
  const btn =
    "flex min-h-14 items-center justify-center gap-2 rounded-full px-7 text-[17px] font-bold md:min-h-[60px] md:text-[19px]";
  const composition = (
    <div className="flex flex-col items-center gap-3 lg:flex-row lg:justify-center lg:gap-3.5">
      <div className="flex items-center gap-5 lg:flex-col lg:gap-[18px]">
        <figure className="flex rotate-[4deg] animate-float flex-col items-center gap-2 [animation-delay:0.4s]">
          <div className="w-[96px] rounded-[6px] bg-paper-raised px-2 pt-2 pb-6 shadow-[0_8px_24px_rgba(0,0,0,0.3)] lg:w-[140px]">
            <Kid look="photo" hijab hijabColor="#E9826B" className="block h-auto w-full rounded-[8px]" />
          </div>
          <figcaption className="text-small text-ink-dark-muted">{t("heroPhoto")}</figcaption>
        </figure>
        <span className="font-display text-[28px] font-extrabold text-amber-500 lg:hidden">+</span>
        <figure className="flex -rotate-[5deg] animate-float flex-col items-center gap-2 [animation-delay:1.3s]">
          <div className="relative w-[92px] shadow-[0_8px_24px_rgba(0,0,0,0.3)] lg:w-[132px]">
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
        <path d="M22 50 L10 60 L22 70" stroke="#F2B33D" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <figure className="flex -rotate-2 animate-float-slow flex-col items-center gap-2.5">
        <div className="w-[280px] overflow-hidden rounded-s-[18px] rounded-e-[6px] border-s-[12px] border-night-950 shadow-[0_16px_40px_rgba(0,0,0,0.4)] lg:w-[360px]">
          {featured ? (
            <CoverArt
              example={featured}
              art={art}
              titleName={featured.title_name}
              titleRest={featured.title_rest}
              alt={t("heroRealBook", { title: featured.title })}
              sizes="360px"
              priority
            />
          ) : (
            <div className="relative">
              <Scene
                theme="night"
                ratio={1}
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
        </div>
        <figcaption className="hidden text-small text-ink-dark-muted lg:block">{t("heroBook")}</figcaption>
      </figure>
    </div>
  );
  return (
    <section id="hero" className="relative overflow-hidden bg-night-900 text-paper">
      <NightSky />
      <SiteNav variant="dark" />
      <div
        className={`${SECTION} relative grid items-center gap-10 pt-4 pb-12 md:pt-10 md:pb-20 lg:grid-cols-[1fr_1.1fr] lg:gap-12`}
      >
        <div className="flex flex-col gap-5 md:gap-7">
          <h1 className="text-[38px] leading-[1.18] font-extrabold md:text-[64px] md:leading-[1.12]">{t("title")}</h1>
          <p className="max-w-[560px] text-[17px] leading-[1.75] text-night-100 md:text-[20px]">{t("lead")}</p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
            <Link
              href="/stories"
              className={`${btn} animate-glow bg-amber-500 text-night-950 transition hover:-translate-y-0.5`}
            >
              {t("ctaStories")}
            </Link>
            <Link href="/workbooks" className={`${btn} border-2 border-night-500 text-paper hover:bg-night-800`}>
              {t("ctaWorkbooks")}
            </Link>
          </div>
          <div className="flex items-center gap-2.5 text-[15px] text-ink-dark-muted">
            {SHIELD}
            {t("privacyLine")}
          </div>
        </div>
        <Photo
          name="hero-reading"
          alt={t("heroPhotoAlt")}
          sizes="(min-width: 1024px) 720px, 100vw"
          priority
          className="rounded-[24px] shadow-[0_16px_40px_rgba(0,0,0,0.4)]"
          fallback={composition}
        />
      </div>
    </section>
  );
}
