import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { AudioPlayer } from "@/components/journey/AudioPlayer";

type Props = { params: Promise<{ code: string }> };

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("journeyAudio.player");
  return { title: t("metaTitle"), robots: { index: false, follow: false }, referrer: "no-referrer" };
}

/** A book page's printed audio QR: `https://{BRAND_DOMAIN}/a/{code}` (Addendum 6 §4.8). */
export default async function JourneyAudioPage({ params }: Props) {
  const { code } = await params;
  if (!/^[a-z2-7]{4,16}$/.test(code)) notFound();
  return <AudioPlayer code={code} />;
}
