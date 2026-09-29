import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminShell } from "@/components/admin/AdminShell";
import { StaffRoles } from "@/components/admin/studio/StaffRoles";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("studio.staff");
  return { title: t("title"), robots: { index: false, follow: false } };
}

/** Staff and their roles (Addendum 4 §3.6). */
export default function AdminStaffPage() {
  return (
    <AdminShell active="staff">
      <StaffRoles />
    </AdminShell>
  );
}
