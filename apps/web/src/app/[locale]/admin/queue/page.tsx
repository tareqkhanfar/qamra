import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminQueue } from "@/components/admin/AdminQueue";
import { AdminShell } from "@/components/admin/AdminShell";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("admin");
  return { title: t("nav.queue"), robots: { index: false, follow: false } };
}

export default function AdminQueuePage() {
  return (
    <AdminShell active="queue">
      <AdminQueue />
    </AdminShell>
  );
}
