import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminOrganizations } from "@/components/admin/AdminOrganizations";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("portal.admin"))("title"), robots: { index: false, follow: false } };
}

export default function AdminOrganizationsPage() {
  return (
    <AdminShell active="organizations">
      <AdminOrganizations />
    </AdminShell>
  );
}
