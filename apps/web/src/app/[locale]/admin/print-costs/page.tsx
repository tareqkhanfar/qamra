import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminPrintCosts } from "@/components/admin/AdminPrintCosts";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("admin");
  return { title: t("nav.printCosts"), robots: { index: false, follow: false } };
}

export default function AdminPrintCostsPage() {
  return (
    <AdminShell active="printCosts">
      <AdminPrintCosts />
    </AdminShell>
  );
}
