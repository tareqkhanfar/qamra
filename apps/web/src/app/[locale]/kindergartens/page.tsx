import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { Scene } from "@/components/art/Scene";
import { MoonMark } from "@/components/Logo";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { LeadForm } from "@/components/site/LeadForm";
import { SiteFooter } from "@/components/site/SiteFooter";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { getPublicSettings, whatsappLink } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("kg");
  return { title: t("title"), description: t("lead") };
}

type Step = { title: string; body: string; who: "school" | "us" | "parents" };

const WHO_STYLE = {
  school: "bg-night-100 text-night-900",
  us: "bg-amber-500 text-night-950",
  parents: "bg-lav-300 text-night-900",
};

export default async function KindergartensPage() {
  const locale = await getLocale();
  const [t, tn, te, site] = await Promise.all([
    getTranslations("kg"),
    getTranslations("nav"),
    getTranslations("errors"),
    getPublicSettings(),
  ]);
  const tp = await getTranslations("portal"); // the kindergarten portal's sign-up (Phase 4)
  const brand = brandName(locale);
  const flow = t.raw("flow") as Step[];
  const inside = t.raw("inside") as string[];
  const trust = t.raw("trust") as { title: string; body: string }[];
  const salesWhatsapp = site?.sales_whatsapp;
  const salesEmail = site?.sales_email;
  const wrap = "mx-auto w-full max-w-[1440px] px-4 md:px-10 xl:px-24";

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-line bg-paper-raised/95 backdrop-blur">
        <nav className="mx-auto flex h-16 max-w-[1440px] items-center gap-4 px-4 md:h-[88px] md:gap-10 md:px-10 xl:px-24">
          <Link href="/" className="flex items-center gap-2.5">
            <MoonMark className="size-8 md:size-10" />
            <span className="font-display text-2xl font-extrabold text-night-900 md:text-[28px]">{brand}</span>
            <span className="rounded-full bg-night-900 px-2.5 py-1 text-xs font-bold text-paper">{t("badge")}</span>
          </Link>
          <div className="hidden grow gap-7 lg:flex">
            <a href="#flow" className="hover:text-amber-700">
              {t("navHow")}
            </a>
            <a href="#book" className="hover:text-amber-700">
              {t("navBook")}
            </a>
            <a href="#trust" className="hover:text-amber-700">
              {t("navTrust")}
            </a>
          </div>
          <div className="ms-auto flex items-center gap-2 lg:ms-0">
            <LocaleSwitcher label={tn("switchLocale")} />
            <Link href="/login?next=/portal" className="hidden min-h-11 items-center px-2 font-semibold sm:flex">
              {t("portal")}
            </Link>
            <Link href="/portal/signup" className="hidden min-h-11 items-center px-2 font-semibold lg:flex">
              {tp("signup.cta")}
            </Link>
            <a
              href="#demo"
              className="flex min-h-11 items-center rounded-full bg-amber-500 px-4 font-bold whitespace-nowrap text-night-950 md:min-h-12 md:px-5"
            >
              {t("requestShort")}
            </a>
          </div>
        </nav>
      </header>

      <main>
        {/* HERO */}
        <section className={`${wrap} grid items-center gap-10 py-12 md:py-20 lg:grid-cols-2 lg:gap-16`}>
          <div className="flex flex-col gap-5 md:gap-6">
            <span className="font-bold text-amber-700">{t("eyebrow")}</span>
            <h1 className="text-[36px] leading-[1.15] font-extrabold text-night-900 md:text-[60px]">{t("title")}</h1>
            <p className="text-body-l leading-[1.75] text-ink-muted md:text-[19px]">{t("lead")}</p>
            <div className="flex flex-wrap gap-3 md:gap-4">
              <a
                href="#demo"
                className="flex min-h-14 items-center rounded-full bg-night-900 px-8 text-[18px] font-bold text-paper md:min-h-[60px]"
              >
                {t("request")}
              </a>
              <a
                href="#book"
                className="flex min-h-14 items-center rounded-full border-2 border-night-900 px-6 text-[18px] font-bold text-night-900 md:min-h-[60px]"
              >
                {t("seeClassPage")}
              </a>
            </div>
          </div>
          <div className="relative mx-auto h-[380px] w-full max-w-[520px] md:h-[520px]">
            <div className="absolute top-5 right-5 w-[48%] rotate-[4deg] animate-float overflow-hidden rounded-lg shadow-book [animation-delay:0.6s]">
              <Scene
                theme="grad"
                ratio={280 / 340}
                cap
                hairStyle="curly"
                skin="#8D5A3B"
                outfit="#7FA38A"
                pose="wave"
                kidScale={0.8}
              />
            </div>
            <div className="absolute top-[120px] left-[28%] z-10 w-[48%] animate-float-slow overflow-hidden rounded-lg shadow-book">
              <Scene theme="grad" ratio={280 / 340} cap hijab hijabColor="#E9826B" outfit="#A99BD6" kidScale={0.8} />
            </div>
            <div className="absolute top-10 left-0 w-[40%] -rotate-[5deg] animate-float overflow-hidden rounded-lg shadow-book [animation-delay:1.5s]">
              <Scene
                theme="grad"
                ratio={220 / 270}
                cap
                hairStyle="long"
                skin="#F3CFAE"
                outfit="#E9826B"
                kidScale={0.8}
              />
            </div>
          </div>
        </section>

        {/* FLOW */}
        <section id="flow" className="scroll-mt-24 bg-night-900 py-12 text-paper md:py-20">
          <div className={`${wrap} flex flex-col gap-8 md:gap-10`}>
            <div className="flex flex-col gap-2.5">
              <span className="font-bold text-amber-300">{t("flowEyebrow")}</span>
              <h2 className="text-[30px] md:text-[44px]">{t("flowTitle")}</h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5 lg:gap-5">
              {flow.map((f, i) => (
                <div
                  key={f.title}
                  data-reveal
                  style={{ "--d": `${i * 110}ms` } as React.CSSProperties}
                  className="flex flex-col gap-2.5 rounded-lg bg-night-800 p-6"
                >
                  <span className="flex size-11 items-center justify-center rounded-[14px] bg-amber-500 font-display text-[22px] font-extrabold text-night-950">
                    {i + 1}
                  </span>
                  <h3 className="text-[20px]">{f.title}</h3>
                  <p className="text-[15px] leading-[1.7] text-ink-dark-muted">{f.body}</p>
                  <span className={`mt-auto self-start rounded-full px-2.5 py-1 text-xs font-bold ${WHO_STYLE[f.who]}`}>
                    {t(`who.${f.who}`, { brand })}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* WHAT'S INSIDE */}
        <section
          id="book"
          className={`${wrap} grid scroll-mt-24 items-center gap-10 py-12 md:py-20 lg:grid-cols-2 lg:gap-16`}
        >
          <div className="flex justify-center rounded-2xl bg-paper-sunk p-6 md:rounded-[32px] md:p-10">
            <div className="flex aspect-square w-full max-w-[440px] flex-col items-center gap-4 rounded-[8px] bg-paper-raised p-6 shadow-book md:p-8">
              <div className="flex size-16 items-center justify-center rounded-full border-2 border-dashed border-amber-700 text-center text-[11px] text-amber-700">
                {t("mockLogo")}
              </div>
              <strong className="text-center font-display text-[20px] text-night-900 md:text-[24px]">
                {t("mockName")}
              </strong>
              <div className="flex w-full grow items-center justify-center rounded-sm bg-night-100 text-small font-semibold text-info">
                {t("mockPhoto")}
              </div>
              <p className="text-center font-display text-body leading-[1.7] text-ink-muted">{t("mockNote")}</p>
            </div>
          </div>
          <div className="flex flex-col gap-5">
            <h2 className="text-[30px] text-night-900 md:text-[44px]">{t("insideTitle")}</h2>
            <ul className="flex flex-col gap-4 text-[17px] leading-[1.6]">
              {inside.map((i) => (
                <li key={i} className="flex items-start gap-3">
                  <svg
                    className="mt-1 size-5 shrink-0"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#DB9A1F"
                    strokeWidth="2.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M5 12l5 5 9-10" />
                  </svg>
                  {i}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* TRUST */}
        <section id="trust" className="scroll-mt-24 px-4 md:px-10 xl:px-24">
          <div className="mx-auto grid max-w-[1248px] gap-6 rounded-2xl border border-line bg-paper-raised p-6 md:grid-cols-3 md:gap-8 md:p-10">
            {trust.map((x) => (
              <div key={x.title} className="flex flex-col gap-2">
                <h3 className="text-[22px] text-night-900">{x.title}</h3>
                <p className="text-[15px] leading-[1.7] text-ink-muted">{x.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* DEMO FORM */}
        <section
          id="demo"
          className={`${wrap} grid scroll-mt-24 gap-8 py-12 md:py-20 lg:grid-cols-[1fr_1.2fr] lg:gap-16`}
        >
          <div className="flex flex-col gap-4">
            <h2 className="text-[30px] text-night-900 md:text-[44px]">{t("formTitle")}</h2>
            <p className="text-body-l leading-[1.75] text-ink-muted">{t("formLead")}</p>
            {(salesWhatsapp || salesEmail) && (
              <div className="mt-2 flex flex-col gap-2 text-body">
                {salesWhatsapp && (
                  <a
                    href={whatsappLink(salesWhatsapp)}
                    rel="noopener"
                    dir="ltr"
                    className="self-start font-semibold text-night-800 rtl:self-end"
                  >
                    {t("whatsapp")}: {salesWhatsapp}
                  </a>
                )}
                {salesEmail && (
                  <a href={`mailto:${salesEmail}`} className="font-semibold text-night-800">
                    {t("email")}: {salesEmail}
                  </a>
                )}
              </div>
            )}
          </div>
          <LeadForm
            labels={{
              fields: t.raw("fields") as never,
              cities: t.raw("cities") as string[],
              submit: t("submit"),
              sending: t("sending"),
              done: t("done"),
              doneAgain: t("doneAgain"),
              network: te("network"),
              unknown: te("unknown"),
            }}
          />
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
