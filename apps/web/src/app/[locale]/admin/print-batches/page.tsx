import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminShell } from "@/components/admin/AdminShell";
import { AdminPrintBatches } from "@/components/admin/print/AdminPrintBatches";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("printBatches");
  return { title: t("title"), robots: { index: false, follow: false } };
}

export default function AdminPrintBatchesPage() {
  return (
    <AdminShell active="printBatches">
      <AdminPrintBatches />
    </AdminShell>
  );
}
