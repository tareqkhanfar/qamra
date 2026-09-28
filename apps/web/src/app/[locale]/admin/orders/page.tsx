import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminOrders } from "@/components/admin/AdminOrders";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("admin");
  return { title: t("nav.orders"), robots: { index: false, follow: false } };
}

export default function AdminOrdersPage() {
  return (
    <AdminShell active="orders">
      <AdminOrders />
    </AdminShell>
  );
}
