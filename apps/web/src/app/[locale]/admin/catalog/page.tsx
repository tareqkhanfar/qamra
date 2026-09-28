import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminShell } from "@/components/admin/AdminShell";
import { AdminCatalog } from "@/components/admin/catalog/AdminCatalog";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("admin");
  return { title: t("nav.catalog"), robots: { index: false, follow: false } };
}

export default function AdminCatalogPage() {
  return (
    <AdminShell active="catalog">
      <AdminCatalog />
    </AdminShell>
  );
}
