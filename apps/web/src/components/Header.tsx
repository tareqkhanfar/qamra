import { cookies } from "next/headers";
import { getLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { buttonClasses } from "@/components/ui/Button";
import { Logo } from "@/components/Logo";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";

export async function Header() {
  const [t, locale, jar] = await Promise.all([getTranslations("nav"), getLocale(), cookies()]);
  const signedIn = jar.has("qamra_at");
  return (
    <header className="border-line/70 bg-paper/90 sticky top-0 z-20 border-b backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4">
        <Link href="/" aria-label={t("home")} className="rounded-full">
          <Logo locale={locale} />
        </Link>
        <nav className="flex items-center gap-1 sm:gap-2">
          <LocaleSwitcher label={t("switchLocale")} />
          {signedIn ? (
            <Link href="/account" className={buttonClasses("solid", "sm")}>
              {t("account")}
            </Link>
          ) : (
            <>
              <Link href="/login" className={buttonClasses("ghost", "sm", "max-sm:hidden")}>
                {t("login")}
              </Link>
              <Link href="/register" className={buttonClasses("solid", "sm")}>
                {t("register")}
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
