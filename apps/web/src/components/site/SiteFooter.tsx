import { getLocale, getTranslations } from "next-intl/server";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { getPublicSettings, whatsappLink } from "@/lib/catalog";

/** Launch footer: the products, kindergartens, and the company (contact details only when the admin set them). */
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
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr]">
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
            {site?.support_whatsapp && (
              <a href={whatsappLink(site.support_whatsapp)} rel="noopener noreferrer" className={a}>
                {t("contact")} · {t("whatsapp")}
              </a>
            )}
            {site?.support_email && (
              <a href={`mailto:${site.support_email}`} className={a} dir="ltr">
                {site.support_email}
              </a>
            )}
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
          </nav>
        </div>
        <div className="flex justify-between gap-4 border-t border-line-dark pt-6 text-caption font-normal">
          <span>{t("rights", { year: new Date().getFullYear(), brand })}</span>
          {company && <span>{company}</span>}
        </div>
      </div>
    </footer>
  );
}
