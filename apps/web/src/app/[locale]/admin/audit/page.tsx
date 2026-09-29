import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminShell } from "@/components/admin/AdminShell";
import { AuditLog } from "@/components/admin/studio/AuditLog";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("studio.audit");
  return { title: t("title"), robots: { index: false, follow: false } };
}

/** The audit log: who changed what, and when. */
export default function AdminAuditPage() {
  return (
    <AdminShell active="audit">
      <AuditLog />
    </AdminShell>
  );
}
