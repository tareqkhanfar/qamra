import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminReports } from "@/components/admin/AdminReports";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("admin");
  return { title: t("nav.reports"), robots: { index: false, follow: false } };
}

export default function AdminReportsPage() {
  return (
    <AdminShell active="reports">
      <AdminReports />
    </AdminShell>
  );
}
