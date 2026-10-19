/**
 * How to reach Qamra: the admin's public settings (Admin → الإعدادات → التواصل) with the brand's own details as the
 * fallback, and the links each one opens (a call, a WhatsApp chat with a written first message, an email with its
 * subject, the social pages).
 *
 * Pure TypeScript with no "@/" imports, so `node --test src/lib/*.test.ts` loads it (Node strips the types).
 */

export type Contact = {
  /** Calls: the owner's number (+970). */
  phone: string;
  /** WhatsApp is on +972. */
  whatsapp: string;
  email: string;
  instagram: string;
  facebook: string;
};

/** Used when the settings are missing (the API is down) or a field is empty. */
export const CONTACT_DEFAULTS: Contact = {
  phone: "+970595870228",
  whatsapp: "+972595870228",
  email: "info@qamra.app",
  instagram: "https://www.instagram.com/qamra.app/",
  facebook: "https://www.facebook.com/qamrabooks",
};

type ContactSettings = Partial<{
  support_phone: string;
  support_whatsapp: string;
  support_email: string;
  instagram_url: string;
  facebook_url: string;
}>;

const or = (value: string | null | undefined, fallback: string) => value?.trim() || fallback;

/** The admin's details, each one falling back to the brand's own. */
export function contactFrom(site: ContactSettings | null | undefined): Contact {
  return {
    phone: or(site?.support_phone, CONTACT_DEFAULTS.phone),
    whatsapp: or(site?.support_whatsapp, CONTACT_DEFAULTS.whatsapp),
    email: or(site?.support_email, CONTACT_DEFAULTS.email),
    instagram: or(site?.instagram_url, CONTACT_DEFAULTS.instagram),
    facebook: or(site?.facebook_url, CONTACT_DEFAULTS.facebook),
  };
}

/** wa.me link for a stored phone number (digits only), with the chat's first message already written. */
export const whatsappLink = (phone: string, text?: string) =>
  `https://wa.me/${phone.replace(/\D/g, "")}${text ? `?text=${encodeURIComponent(text)}` : ""}`;

/** tel: link for a stored phone number ("+970595870228"). */
export const telLink = (phone: string) => `tel:+${phone.replace(/\D/g, "")}`;

/** mailto: link with its subject (encoded as RFC 6068 asks: spaces are %20, never "+"). */
export const mailtoLink = (email: string, subject?: string) =>
  `mailto:${email.trim()}${subject ? `?subject=${encodeURIComponent(subject)}` : ""}`;

/** A stored number as people read it: "+970595870228" → "+970 59 587 0228" (Palestinian and Israeli mobiles). */
export function displayPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 12 && (digits.startsWith("970") || digits.startsWith("972")))
    return `+${digits.slice(0, 3)} ${digits.slice(3, 5)} ${digits.slice(5, 8)} ${digits.slice(8)}`;
  return phone.trim().startsWith("+") ? `+${digits}` : phone.trim();
}

/** "https://www.instagram.com/qamra.app/" → "@qamra.app"; "" when the link names no account. */
export function socialHandle(url: string): string {
  try {
    const first = new URL(url).pathname.split("/").find(Boolean);
    return first ? `@${first}` : "";
  } catch {
    return "";
  }
}

export type ContactKey = "phone" | "whatsapp" | "email" | "facebook" | "instagram";
export type ContactItem = { key: ContactKey; href: string; value: string; external: boolean };

/**
 * The contact links, in the order they are shown: the phone, WhatsApp and the email; `social` adds Facebook and
 * Instagram after them ("only": just those two). `whatsappText` and `emailSubject` write the chat's first message
 * and the email's subject (the QR page puts the book's code in both).
 */
export function contactItems(
  contact: Contact,
  {
    social = false,
    whatsappText,
    emailSubject,
  }: { social?: boolean | "only"; whatsappText?: string; emailSubject?: string } = {},
): ContactItem[] {
  const direct: ContactItem[] = [
    { key: "phone", href: telLink(contact.phone), value: displayPhone(contact.phone), external: false },
    {
      key: "whatsapp",
      href: whatsappLink(contact.whatsapp, whatsappText),
      value: displayPhone(contact.whatsapp),
      external: true,
    },
    { key: "email", href: mailtoLink(contact.email, emailSubject), value: contact.email, external: false },
  ];
  const pages: ContactItem[] = [
    { key: "facebook", href: contact.facebook, value: socialHandle(contact.facebook), external: true },
    { key: "instagram", href: contact.instagram, value: socialHandle(contact.instagram), external: true },
  ];
  if (social === "only") return pages;
  return social ? [...direct, ...pages] : direct;
}
