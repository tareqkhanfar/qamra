import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminShell } from "@/components/admin/AdminShell";
import { StudioTemplates } from "@/components/admin/studio/StudioTemplates";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("studio");
  return { title: t("title"), robots: { index: false, follow: false } };
}

/** The template studio (Addendum 4 §3): Classic templates per theme × art style × look, and bulk actions. */
export default function AdminStudioPage() {
  return (
    <AdminShell active="themes">
      <StudioTemplates />
    </AdminShell>
  );
}
