import { getLocale, getTranslations } from "next-intl/server";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { getPublicSettings, whatsappLink } from "@/lib/catalog";

export async function SiteFooter() {
  const [t, tn, locale, site] = await Promise.all([
    getTranslations("footer"),
    getTranslations("nav"),
    getLocale(),
    getPublicSettings(),
  ]);
  const brand = brandName(locale);
  const company = site?.company_name;
  const col = "flex flex-col gap-2.5 text-[15px]";
  const a = "text-ink-dark-muted hover:text-amber-300";
  return (
    <footer className="bg-night-950 text-ink-dark-muted">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-10 px-4 pt-16 pb-28 md:px-10 md:pb-10 xl:px-24">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr]">
          <div className="flex flex-col gap-3">
            <span className="font-display text-[32px] font-extrabold text-paper">{brand}</span>
            <p className="max-w-[340px] text-[15px] leading-7">{t("about")}</p>
          </div>
          <div className={col}>
            <strong className="text-paper">{t("product")}</strong>
            <Link href="/themes" className={a}>
              {tn("themes")}
            </Link>
            <Link href="/#pricing" className={a}>
              {tn("pricing")}
            </Link>
            <Link href="/#samples" className={a}>
              {t("samples")}
            </Link>
          </div>
          <div className={col}>
            <strong className="text-paper">{t("forKg")}</strong>
            <Link href="/kindergartens" className={a}>
              {t("gradBooks")}
            </Link>
            <Link href="/kindergartens#demo" className={a}>
              {t("contact")}
            </Link>
          </div>
          <div className={col}>
            <strong className="text-paper">{t("trust")}</strong>
            {site?.support_whatsapp && (
              <a href={whatsappLink(site.support_whatsapp)} rel="noopener noreferrer" className={a}>
                {t("contact")}
              </a>
            )}
            {site?.support_email && (
              <a href={`mailto:${site.support_email}`} className={a}>
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
            <Link href="/#privacy" className={a}>
              {t("privacy")}
            </Link>
          </div>
        </div>
        <div className="flex justify-between gap-4 border-t border-line-dark pt-6 text-caption font-normal">
          <span>{t("rights", { year: new Date().getFullYear(), brand })}</span>
          {company && <span>{company}</span>}
        </div>
      </div>
    </footer>
  );
}
