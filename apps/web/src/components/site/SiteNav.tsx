import { cookies } from "next/headers";
import { getLocale, getTranslations } from "next-intl/server";
import { MoonMark } from "@/components/Logo";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";

type Variant = "dark" | "light";

/** Site header. `dark` sits inside the night-blue hero (landing); `light` is the paper header elsewhere. */
export async function SiteNav({ variant = "light" }: { variant?: Variant }) {
  const [t, locale, jar] = await Promise.all([getTranslations("nav"), getLocale(), cookies()]);
  const signedIn = jar.has("qamra_at");
  const dark = variant === "dark";
  const links = [
    { href: "/#how", label: t("how") },
    { href: "/themes", label: t("themes") },
    { href: "/#pricing", label: t("pricing") },
    { href: "/kindergartens", label: t("kindergartens") },
    { href: "/#faq", label: t("faq") },
  ];
  const linkColor = dark ? "text-night-100 hover:text-amber-300" : "text-night-900 hover:text-amber-700";
  return (
    <header
      className={dark ? "relative z-20" : "sticky top-0 z-30 border-b border-line bg-paper-raised/95 backdrop-blur"}
    >
      <nav
        aria-label={t("home")}
        className="mx-auto flex h-16 max-w-[1440px] items-center gap-4 px-4 md:h-[88px] md:gap-10 md:px-10 xl:px-24"
      >
        <Link href="/" className="flex shrink-0 items-center gap-2.5 rounded-full">
          <MoonMark className="size-8 md:size-10" tone={dark ? "dark" : "light"} />
          <span
            className={`font-display text-2xl font-extrabold md:text-[30px] ${dark ? "text-paper" : "text-night-900"}`}
          >
            {brandName(locale)}
          </span>
        </Link>
        <div className="hidden grow gap-7 text-body lg:flex">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className={linkColor}>
              {l.label}
            </Link>
          ))}
        </div>
        <div className="ms-auto flex items-center gap-2 lg:ms-0">
          <LocaleSwitcher label={t("switchLocale")} tone={dark ? "dark" : "light"} />
          <Link
            href={signedIn ? "/account" : "/login"}
            className={`hidden min-h-11 items-center px-2 font-semibold sm:flex ${dark ? "text-paper hover:text-amber-300" : "text-night-900 hover:text-amber-700"}`}
          >
            {signedIn ? t("account") : t("signIn")}
          </Link>
          <Link
            href="/create"
            className="hidden min-h-12 items-center rounded-full bg-amber-500 px-5 font-bold whitespace-nowrap text-night-950 hover:shadow-lamp sm:flex"
          >
            {t("start")}
          </Link>
          <details className="group relative lg:hidden">
            <summary
              aria-label={t("openMenu")}
              className={`flex size-11 cursor-pointer list-none items-center justify-center rounded-sm [&::-webkit-details-marker]:hidden ${dark ? "bg-night-800 text-paper" : "border border-line bg-paper-raised text-night-900"}`}
            >
              <svg
                className="size-[22px]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M4 7h16M4 12h16M4 17h10" />
              </svg>
            </summary>
            <div className="absolute end-0 top-14 z-40 flex w-64 flex-col gap-1 rounded-xl border border-line bg-paper-raised p-3 text-ink shadow-2">
              {links.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="flex min-h-11 items-center rounded-sm px-3 font-semibold hover:bg-paper-sunk"
                >
                  {l.label}
                </Link>
              ))}
              <Link
                href={signedIn ? "/account" : "/login"}
                className="flex min-h-11 items-center rounded-sm px-3 font-semibold hover:bg-paper-sunk"
              >
                {signedIn ? t("account") : t("signIn")}
              </Link>
              <Link
                href="/create"
                className="mt-1 flex min-h-12 items-center justify-center rounded-full bg-amber-500 font-bold text-night-950"
              >
                {t("start")}
              </Link>
            </div>
          </details>
        </div>
      </nav>
    </header>
  );
}
