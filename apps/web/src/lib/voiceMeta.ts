import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

/** «صوت أهلي» pages are private: never indexed, and their tokens never leave through the Referer header. */
export async function voiceMetadata(key: "record" | "invite" | "elder" | "listen"): Promise<Metadata> {
  const t = await getTranslations("voice");
  return {
    title: t(`${key}.metaTitle`),
    robots: { index: false, follow: false, nocache: true, googleBot: { index: false, follow: false } },
    referrer: "no-referrer",
  };
}
