import { getTranslations } from "next-intl/server";
import { displayPhone, getPublicSettings, telLink, whatsappLink } from "@/lib/catalog";

type Props = {
  /** "dark" on the night footer, "light" on the paper pages. */
  tone?: "light" | "dark";
  /** The kindergartens page: the sales WhatsApp and email when the admin set their own. */
  sales?: boolean;
  className?: string;
};

/**
 * How to reach us, from the admin settings (one place: Admin → الإعدادات → التواصل): the phone for calls, the
 * WhatsApp number and the email, each a link. A number is isolated left to right, so "+970 59 587 0228" never
 * turns around inside an Arabic line.
 */
export async function ContactLinks({ tone = "light", sales = false, className = "" }: Props) {
  const [t, site] = await Promise.all([getTranslations("contact"), getPublicSettings()]);
  const phone = site?.support_phone;
  const whatsapp = (sales && site?.sales_whatsapp) || site?.support_whatsapp;
  const email = (sales && site?.sales_email) || site?.support_email;
  const items = [
    phone ? { key: "phone", href: telLink(phone), label: t("phone"), value: displayPhone(phone) } : null,
    whatsapp
      ? { key: "whatsapp", href: whatsappLink(whatsapp), label: t("whatsapp"), value: displayPhone(whatsapp) }
      : null,
    email ? { key: "email", href: `mailto:${email}`, label: t("email"), value: email } : null,
  ].filter((i) => i !== null);
  if (!items.length) return null;
  const dark = tone === "dark";
  return (
    <ul className={`flex flex-col gap-2.5 ${className}`}>
      {items.map((i) => (
        <li key={i.key}>
          <a
            href={i.href}
            rel={i.key === "whatsapp" ? "noopener noreferrer" : undefined}
            className={`inline-flex flex-wrap items-baseline gap-x-1.5 ${dark ? "text-ink-dark-muted hover:text-amber-300" : "text-ink hover:text-amber-700"}`}
          >
            <span>{i.label}:</span>
            <bdi dir="ltr" className={`font-semibold ${dark ? "text-paper" : "text-night-900"}`}>
              {i.value}
            </bdi>
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
