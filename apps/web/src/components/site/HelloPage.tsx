import { getLocale, getTranslations } from "next-intl/server";
import { MoonPhase } from "@/components/art/MoonPhase";
import { buttonClasses } from "@/components/ui/Button";
import { brand, brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { nameCases } from "@/lib/arabicName";
import type { BookByCode } from "@/lib/bookCode";
import { getPublicSettings } from "@/lib/catalog";
import { contactFrom, whatsappLink } from "@/lib/contact";
import { ContactIcon, type ContactIconName } from "./ContactIcon";
import { ContactLinks, TILE, TILE_ICON } from "./ContactLinks";
import { PageShell } from "./PageShell";

/**
 * The page the QR printed in every book opens (`/b/QB-7K4M2`), and the same page without a book (`/hello`): who we
 * are, how to order again, and every way to reach us, each one a big tap target. With a known book it names only
 * the child's first name, the product and the code (the WhatsApp message and the email subject carry the code);
 * with any other code it is exactly the /hello page.
 */
export async function HelloPage({ book }: { book: BookByCode | null }) {
  const [t, tc, locale, site] = await Promise.all([
    getTranslations("hello"),
    getTranslations("contact"),
    getLocale(),
    getPublicSettings(),
  ]);
  const name = brandName(locale);
  const contact = contactFrom(site);
  const code = book?.code;
  const whatsappText = code ? t("whatsappBook", { brand: name, code }) : t("whatsappHello", { brand: name });
  const emailSubject = code ? t("emailBook", { brand: name, code }) : t("emailHello", { brand: name });
  const section = "flex flex-col gap-3";
  const heading = "text-h3 text-night-900";
  const siteLinks: { href: string; icon: ContactIconName; label: string; value: string }[] = [
    { href: "/", icon: "globe", label: t("home"), value: brand.domain },
    { href: "/shop", icon: "bag", label: t("allBooks"), value: `${brand.domain}/shop` },
  ];

  return (
    <PageShell>
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-10 px-4 pt-8 pb-16 md:pt-14">
        <header className="flex flex-col items-center gap-3 text-center">
          <MoonPhase p={1} className="size-16" />
          <h1 className="text-[30px] leading-tight text-night-900 md:text-h1">{t("title", { brand: name })}</h1>
          <p className="max-w-md text-body-l text-ink-muted">{t("lead", { brand: name })}</p>
        </header>

        {book && (
          <section
            aria-label={t("yourBook")}
            className="flex flex-col items-center gap-2 rounded-xl border-2 border-amber-300 bg-amber-100/50 px-4 py-5 text-center"
          >
            <ContactIcon name="book" className="size-8 text-amber-700" />
            <p className="font-display text-[24px] font-bold text-night-900">
              {locale === "ar" ? t("bookFor", nameCases(book.child_name)) : t("bookFor", { name: book.child_name })}
            </p>
            <p className="text-body text-ink">{locale === "ar" ? book.product_ar : book.product_en}</p>
            <p className="flex flex-wrap items-baseline justify-center gap-x-2 text-small text-ink-muted">
              <span>{t("bookCode")}</span>
              <bdi dir="ltr" className="font-mono text-body-l font-bold tracking-wider text-night-900">
                {book.code}
              </bdi>
            </p>
            <p className="text-small text-ink-muted">{t("thanks", { brand: name })}</p>
          </section>
        )}

        <section className={section}>
          <h2 className={heading}>{t("orderTitle")}</h2>
          <Link href="/shop" className={buttonClasses("primary", "lg", "w-full")}>
            {t("orderAnother")}
          </Link>
          {code && (
            <a
              href={whatsappLink(contact.whatsapp, t("whatsappCopy", { brand: name, code }))}
              target="_blank"
              rel="noopener noreferrer"
              className={buttonClasses("secondary", "lg", "w-full py-3 text-center whitespace-normal")}
            >
              <ContactIcon name="whatsapp" className="size-6 shrink-0" />
              {t("orderCopy")}
            </a>
          )}
        </section>

        <section className={section}>
          <h2 className={heading}>{tc("title")}</h2>
          <ContactLinks variant="tiles" whatsappText={whatsappText} emailSubject={emailSubject} />
        </section>

        <section className={section}>
          <h2 className={heading}>{t("followTitle")}</h2>
          <ContactLinks variant="tiles" social="only" />
        </section>

        <section className={section}>
          <h2 className={heading}>{t("siteTitle")}</h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {siteLinks.map((l) => (
              <li key={l.href}>
                <Link href={l.href} className={TILE}>
                  <span className={TILE_ICON}>
                    <ContactIcon name={l.icon} />
                  </span>
                  <span className="flex min-w-0 flex-col">
                    <span className="font-bold text-night-900">{l.label}</span>
                    <bdi dir="ltr" className="truncate text-small text-ink-muted">
                      {l.value}
                    </bdi>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </PageShell>
  );
}
