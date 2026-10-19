import { getTranslations } from "next-intl/server";
import { getPublicSettings } from "@/lib/catalog";
import { contactFrom, contactItems } from "@/lib/contact";
import { ContactIcon } from "./ContactIcon";

/** A big contact tap target (at least 64px tall) and its round icon: the QR page's links. */
export const TILE =
  "flex min-h-16 items-center gap-3 rounded-lg border border-line bg-paper-raised px-4 py-3 text-ink transition hover:border-amber-500 hover:bg-amber-100/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-night-700";
export const TILE_ICON = "flex size-11 shrink-0 items-center justify-center rounded-full bg-night-100 text-night-900";

type Props = {
  /** "dark" on the night footer, "light" on the paper pages. */
  tone?: "light" | "dark";
  /** "list": label and value on a line (footer, help boxes); "tiles": big tap targets with icons (the QR page). */
  variant?: "list" | "tiles";
  /** The kindergartens page: the sales WhatsApp and email when the admin set their own. */
  sales?: boolean;
  /** Facebook and Instagram after the phone, WhatsApp and email ("only": just those two). */
  social?: boolean | "only";
  /** The WhatsApp chat's first message, already written (the QR page names the book's code). */
  whatsappText?: string;
  /** The email's subject (the QR page names the book's code). */
  emailSubject?: string;
  className?: string;
};

/**
 * How to reach us, from the admin settings (one place: Admin → الإعدادات → التواصل) with the brand's own details as
 * the fallback (lib/contact.ts): the phone for calls, the WhatsApp number, the email and the social pages, each a
 * link. A number is isolated left to right, so "+970 59 587 0228" never turns around inside an Arabic line.
 */
export async function ContactLinks({
  tone = "light",
  variant = "list",
  sales = false,
  social = false,
  whatsappText,
  emailSubject,
  className = "",
}: Props) {
  const [t, site] = await Promise.all([getTranslations("contact"), getPublicSettings()]);
  const contact = contactFrom(site);
  if (sales) {
    contact.whatsapp = site?.sales_whatsapp?.trim() || contact.whatsapp;
    contact.email = site?.sales_email?.trim() || contact.email;
  }
  const items = contactItems(contact, { social, whatsappText, emailSubject });
  const external = (i: { external: boolean }) =>
    i.external ? { target: "_blank", rel: "noopener noreferrer" } : { rel: undefined };

  if (variant === "tiles")
    return (
      <ul className={`grid gap-3 sm:grid-cols-2 ${className}`}>
        {items.map((i) => (
          <li key={i.key}>
            <a href={i.href} {...external(i)} className={TILE}>
              <span className={TILE_ICON}>
                <ContactIcon name={i.key} />
              </span>
              <span className="flex min-w-0 flex-col">
                <span className="font-bold text-night-900">{t(i.key)}</span>
                {i.value && (
                  <bdi dir="ltr" className="truncate text-small text-ink-muted">
                    {i.value}
                  </bdi>
                )}
              </span>
            </a>
          </li>
        ))}
      </ul>
    );

  const dark = tone === "dark";
  return (
    <ul className={`flex flex-col gap-2.5 ${className}`}>
      {items.map((i) => (
        <li key={i.key}>
          <a
            href={i.href}
            {...external(i)}
            className={`inline-flex flex-wrap items-baseline gap-x-1.5 ${dark ? "text-ink-dark-muted hover:text-amber-300" : "text-ink hover:text-amber-700"}`}
          >
            <span>{i.value ? `${t(i.key)}:` : t(i.key)}</span>
            {i.value && (
              <bdi dir="ltr" className={`font-semibold ${dark ? "text-paper" : "text-night-900"}`}>
                {i.value}
              </bdi>
            )}
          </a>
        </li>
      ))}
    </ul>
  );
}

/** The order and tracking pages: «عندكم سؤال عن طلبكم؟» with the same links. */
export async function ContactHelp({ className = "" }: { className?: string }) {
  const t = await getTranslations("contact");
  return (
    <aside
      aria-label={t("title")}
      className={`mx-auto flex w-full max-w-xl flex-col gap-2.5 rounded-lg border border-line bg-paper-raised p-4 text-body ${className}`}
    >
      <p className="font-bold text-night-900">{t("help")}</p>
      <ContactLinks />
    </aside>
  );
}
