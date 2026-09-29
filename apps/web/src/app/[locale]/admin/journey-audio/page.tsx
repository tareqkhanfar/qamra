import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminJourneyAudio } from "@/components/admin/AdminJourneyAudio";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("journeyAudio.admin");
  return { title: t("title"), robots: { index: false, follow: false } };
}

export default function AdminJourneyAudioPage() {
  return (
    <AdminShell active="journeyAudio">
      <AdminJourneyAudio />
    </AdminShell>
  );
}
