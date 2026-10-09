import { getLocale, getTranslations } from "next-intl/server";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { getPublicSettings } from "@/lib/catalog";
import { ContactLinks } from "./ContactLinks";

/**
 * Launch footer: the products, kindergartens, the company, how to reach us (phone, WhatsApp, email from the
 * admin settings), and the copyright line at the very bottom of every page.
 */
export async function SiteFooter() {
  const [t, locale, site] = await Promise.all([getTranslations("footer"), getLocale(), getPublicSettings()]);
  const brand = brandName(locale);
  const company = site?.company_name;
  const col = "flex flex-col gap-2.5 text-[15px]";
  const a = "text-ink-dark-muted hover:text-amber-300";
  const products = [
    { href: "/stories", label: t("stories") },
    { href: "/workbooks/foundation-workbook", label: t("foundation") },
    { href: "/workbooks/learning-journey", label: t("journey") },
    { href: "/workbooks/family-adventures", label: t("family") },
    { href: "/workbooks/islamic-series", label: t("islamic") },
    { href: "/shop", label: t("allBooks") },
  ];
  const kg = [
    { href: "/kindergartens", label: t("gradBooks") },
    { href: "/kindergartens#demo", label: t("quote") },
    { href: "/login?next=/portal", label: t("portal") },
  ];
  const about = [
    { href: "/how-it-works", label: t("how") },
    { href: "/pricing", label: t("pricing") },
    { href: "/privacy", label: t("privacy") },
  ];
  return (
    <footer className="bg-night-950 text-ink-dark-muted">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-10 px-4 pt-16 pb-28 md:px-10 md:pb-10 xl:px-24">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1.5fr]">
          <div className="flex flex-col gap-3">
            <span className="font-display text-[32px] font-extrabold text-paper">{brand}</span>
            <p className="max-w-[340px] text-[15px] leading-7">{t("about")}</p>
          </div>
          <nav aria-label={t("products")} className={col}>
            <strong className="text-paper">{t("products")}</strong>
            {products.map((l) => (
              <Link key={l.href} href={l.href} className={a}>
                {l.label}
              </Link>
            ))}
          </nav>
          <nav aria-label={t("forKg")} className={col}>
            <strong className="text-paper">{t("forKg")}</strong>
            {kg.map((l) => (
              <Link key={l.href} href={l.href} className={a}>
                {l.label}
              </Link>
            ))}
          </nav>
          <nav aria-label={brand} className={col}>
            <strong className="text-paper">{brand}</strong>
            {about.map((l) => (
              <Link key={l.href} href={l.href} className={a}>
                {l.label}
              </Link>
            ))}
          </nav>
          <div className={col}>
            <strong className="text-paper">{t("contact")}</strong>
            <ContactLinks tone="dark" />
            {site?.instagram_url && (
              <a href={site.instagram_url} rel="noopener noreferrer" target="_blank" className={a}>
                Instagram
              </a>
            )}
            {site?.facebook_url && (
              <a href={site.facebook_url} rel="noopener noreferrer" target="_blank" className={a}>
                Facebook
              </a>
            )}
          </div>
        </div>
        <div className="flex flex-wrap justify-between gap-x-4 gap-y-1 border-t border-line-dark pt-6 text-caption font-normal">
          <span>{t("rights", { year: String(new Date().getFullYear()), brand })}</span>
          {company && <span>{company}</span>}
        </div>
      </div>
    </footer>
  );
}
