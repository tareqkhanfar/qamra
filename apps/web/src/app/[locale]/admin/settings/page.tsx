import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminSettings } from "@/components/admin/AdminSettings";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("admin");
  return { title: t("title"), robots: { index: false, follow: false } };
}

export default function AdminSettingsPage() {
  return (
    <AdminShell active="settings">
      <AdminSettings />
    </AdminShell>
  );
}
